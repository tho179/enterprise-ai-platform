import re
import time
import logging
from typing import List, Dict, Any, Optional, Tuple
from openai import OpenAI

from app.config import settings
from app.embedding_service import fold_text
from app.retriever import VectorRetriever
from app.schemas import CitationItem, ChatMessage, AskResponse

logger = logging.getLogger(__name__)

# Từ chức năng khi chọn câu trả lời trích xuất; giữ nguyên từ chuyên môn.
_STOPWORDS = {
    "la", "cua", "co", "va", "duoc", "bao", "nhieu", "gi", "nao", "the", "nhu",
    "khi", "cho", "trong", "mot", "cac", "nhung", "nay", "do", "de", "voi",
    "hay", "hoac", "thi", "ma", "o", "ra", "vao", "len", "xuong", "roi", "da",
    "dang", "se", "toi", "ban", "minh", "tren", "duoi", "tu", "den", "ve",
    "tai", "boi", "vi", "nen", "cung", "chi", "con", "ai", "lam", "sao", "phai",
    "khong", "bi", "moi", "vay", "nhi", "rat", "qua", "hon", "nua", "day", "kia",
    "ay", "no", "ho", "chung",
}


def _content_terms(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[0-9a-z]+", fold_text(text))
        if len(token) > 1 and token not in _STOPWORDS
    }

# Ngưỡng tin cậy cho trích dẫn (cosine thuần sau khi fold). Đo thực tế trên kho
# Điều lệ: câu hỏi ngoài phạm vi rơi vào 0.28-0.42, câu hỏi khớp thật thấp nhất
# ~0.53. Ngưỡng 0.5 tách được hai vùng và không chặn oan câu hợp lệ.
CONFIDENCE_GATE = 0.5

SYSTEM_PROMPT = """Bạn là Trợ lý AI Quản lý Tri thức Doanh nghiệp. Nhiệm vụ của bạn là giải đáp thắc mắc của nhân viên dựa HOÀN TOÀN vào các đoạn ngữ cảnh trích xuất từ tài liệu nội bộ được cung cấp dưới đây.

QUY TẮC BẮT BUỘC (Chống ảo giác & Trích dẫn chính xác):
1. Chỉ trả lời dựa trên thông tin có trong ngữ cảnh. Tuyệt đối KHÔNG tự bịa đặt, suy diễn hoặc đưa ra thông tin không có trong tài liệu.
2. Nếu ngữ cảnh không có thông tin hoặc không đủ dữ liệu để trả lời, hãy trả lời trung thực: "Dựa trên các tài liệu nội bộ hiện tại, tôi chưa tìm thấy thông tin để trả lời câu hỏi này."
3. Mọi nhận định, quy định hoặc số liệu nêu ra PHẢI được gắn nhãn trích dẫn tham chiếu ở cuối câu theo định dạng [1], [2] tương ứng với mã số của đoạn tài liệu.
4. Trình bày ngắn gọn, mạch lạc, dùng ngôn ngữ tiếng Việt lịch sự, chuẩn mực doanh nghiệp."""

class RAGService:
    """
    Module M4: RAG Question Answering Service
    Orchestrates Vector Retrieval, Context Augmentation, Citation Resolution,
    and LLM Generation (Gemini / OpenAI with Extractive Fallback).
    """

    def __init__(self, retriever: Optional[VectorRetriever] = None):
        self.retriever = retriever or VectorRetriever()

    def _build_context_and_citations(
        self,
        hits: List[Dict[str, Any]],
        query: str
    ) -> Tuple[str, List[CitationItem]]:
        """
        Formats retrieved vector hits into an indexed context prompt and citation models.
        """
        context_blocks = []
        citations = []

        for idx, hit in enumerate(hits, 1):
            chunk_id = hit.get("chunk_id", f"CHUNK-{idx}")
            score = hit.get("score", 0.0)
            content = hit.get("content", "").strip()
            meta = hit.get("metadata", {})

            p_start = meta.get("page_start")
            p_end = meta.get("page_end")
            if p_start is not None and p_end is not None:
                pages_str = f"Trang {p_start}" if p_start == p_end else f"Trang {p_start} → {p_end}"
            else:
                pages_str = "Trang ?"

            section_path = meta.get("section_path", [])
            path_str = " > ".join(section_path) if section_path else "Văn bản chung"
            doc_id = meta.get("document_id")

            # Build context snippet for LLM
            block = f"[{idx}] Vị trí: {pages_str} | Phả hệ: {path_str}\nNội dung: {content}"
            context_blocks.append(block)

            # Build structured citation object
            snippet = self._focused_excerpt(query, content)
            if len(snippet) > 500:
                cut = snippet.rfind(" ", 0, 500)
                snippet = snippet[: cut if cut > 0 else 500].rstrip() + "…"
            citations.append(CitationItem(
                index=idx,
                chunk_id=chunk_id,
                score=score,
                document_id=doc_id,
                section_path=section_path,
                pages=pages_str,
                snippet=snippet
            ))

        formatted_context = "\n\n".join(context_blocks)
        return formatted_context, citations

    def _focused_excerpt(self, query: str, content: str) -> str:
        """
        Chọn (các) câu chứa từ khóa của câu hỏi để phần trích dẫn không bắt
        đầu giữa câu và không đổ nguyên đoạn 1.400 ký tự vào câu trả lời.
        """
        query_terms = _content_terms(query)
        # Dấu xuống dòng của OCR không phải ranh giới câu; chỉ tách theo dấu câu
        # rồi nén khoảng trắng để câu trả lời không bị cụt giữa dòng.
        sentences = [
            re.sub(r"\s+", " ", sentence).strip()
            for sentence in re.split(r"(?<=[.!?;])\s+", content)
            if sentence.strip()
        ]
        if not query_terms or not sentences:
            return content

        # Câu hỏi dạng "Điều 43" phải giữ đúng tiêu đề điều, không chọn câu
        # nào khác chỉ vì trùng từ "quy định".
        article = re.search(r"\bdieu\s+(\d+)\b", fold_text(query))
        if article:
            number = article.group(1)
            for index, sentence in enumerate(sentences):
                if re.search(rf"\bdieu\s+{number}\b", fold_text(sentence)):
                    end = index + 1
                    while end < len(sentences) and end <= index + 4:
                        if len(" ".join(sentences[index:end + 1])) >= 320:
                            end += 1
                            break
                        end += 1
                    return " ".join(sentences[index:end]).strip()

        scores = [
            len(query_terms & _content_terms(sentence)) / len(query_terms)
            for sentence in sentences
        ]
        best = max(range(len(sentences)), key=lambda index: scores[index])
        if scores[best] == 0:
            return content

        start = best
        end = best + 1
        # Câu đứng sau thường là phần giải thích/ngoại lệ của cùng quy định,
        # nhưng không kéo theo tiêu đề chương/điều của phần kế tiếp.
        next_is_heading = best + 1 < len(sentences) and bool(
            re.match(r"^(chuong|dieu|muc)\b", fold_text(sentences[best + 1]))
        )
        if (len(sentences[best]) < 140 or sentences[best].endswith(":")) \
                and best + 1 < len(sentences) and not next_is_heading:
            end = best + 2
        # Câu bắt đầu bằng chữ thường là phần nối tiếp -> lấy cả câu trước.
        if sentences[best][:1].islower() and best > 0:
            start = best - 1
        excerpt = " ".join(sentences[start:end])
        if sentences[start][:1].islower():
            excerpt = "… " + excerpt
        return excerpt

    def _get_llm_client(self) -> Tuple[Optional[OpenAI], str]:
        """
        Resolves available LLM client:
        Prefers Gemini (via OpenAI-compatible endpoint) or OpenAI, otherwise returns None for fallback.
        """
        gemini_key = settings.GEMINI_API_KEY.strip()
        if gemini_key and not gemini_key.startswith("your_"):
            client = OpenAI(
                api_key=gemini_key,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
            )
            return client, settings.GEMINI_MODEL

        openai_key = settings.OPENAI_API_KEY.strip()
        if openai_key and not openai_key.startswith("your_"):
            client = OpenAI(api_key=openai_key)
            return client, settings.OPENAI_MODEL

        return None, "extractive-fallback"

    def _generate_extractive_fallback(
        self,
        query: str,
        citations: List[CitationItem],
        hits: List[Dict[str, Any]]
    ) -> str:
        """
        Fallback generator when cloud LLM API keys are not yet configured or reachable.
        Synthesizes top referenced extracts with citation markers.
        """
        # citations rỗng nghĩa là bước kiểm tra tin cậy (reranker/cosine) đã
        # kết luận không đủ căn cứ -> phải từ chối, không được trích đoạn nhiễu.
        if not hits or not citations:
            return "Dựa trên các tài liệu nội bộ hiện tại, tôi chưa tìm thấy thông tin phù hợp với câu hỏi này."

        # Có thông tin tin cậy -> extractive fallback
        best = hits[0]
        meta = best.get("metadata", {})
        path_str = " > ".join(meta.get("section_path", []))
        summary_intro = f"Theo quy định tại **{path_str or 'tài liệu nội bộ'}** [1]:\n\n"
        content = self._focused_excerpt(query, best.get("content", "").strip())

        return f"{summary_intro}> {content}\n\n*(Thông tin được trích xuất trực tiếp từ tài liệu đã lập chỉ mục)*"

    def ask(
        self,
        query: str,
        top_k: int = 3,
        document_id: Optional[str] = None,
        min_score: float = 0.25,
        history: Optional[List[ChatMessage]] = None
    ) -> AskResponse:
        """
        End-to-end RAG QA workflow:
        1. Semantic retrieval from Qdrant
        2. Context indexing & citation packaging
        3. LLM generation with anti-hallucination prompt
        """
        start_time = time.time()
        cleaned_query = query.strip()

        # Step 1: Retrieve relevant chunks
        hits = self.retriever.search(
            query=cleaned_query,
            top_k=top_k,
            document_id=document_id,
            min_score=min_score
        )

        # Đoạn tốt nhất quá kém (ngoài ngưỡng tin cậy) -> trả lời trung thực là
        # không tìm thấy, không kèm trích dẫn gây hiểu nhầm, không nạp nhiễu cho LLM.
        top = hits[0] if hits else None
        article_match = bool(top and top.get("article_match"))
        rerank_score = top.get("rerank_score") if top else None
        if rerank_score is not None:
            trusted = bool(hits) and (article_match or rerank_score >= settings.RERANK_GATE)
        else:
            # Không có reranker: lùi về ngưỡng cosine đã hiệu chỉnh.
            top_vector = top.get("vector_score", 0.0) if top else 0.0
            trusted = bool(hits) and (top_vector >= CONFIDENCE_GATE or article_match)

        # Step 2: Format context and citations
        context_text, citations = self._build_context_and_citations(hits, cleaned_query) if trusted else ("", [])

        # Step 3: Determine generation strategy
        client, model_name = self._get_llm_client()

        answer = ""
        if not trusted:
            answer = self._generate_extractive_fallback(cleaned_query, citations, hits)
        elif client is not None:
            try:
                messages = [{"role": "system", "content": SYSTEM_PROMPT}]

                # Include conversation history if provided
                if history:
                    for msg in history[-4:]:  # last 4 turns
                        messages.append({"role": msg.role, "content": msg.content})

                user_prompt = f"NGỮ CẢNH TÀI LIỆU:\n{context_text}\n\nCÂU HỎI:\n{cleaned_query}"
                messages.append({"role": "user", "content": user_prompt})

                completion = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=0.2
                )
                answer = completion.choices[0].message.content.strip()
            except Exception as exc:
                logger.warning(f"Cloud LLM call failed ({exc}), reverting to extractive fallback")
                answer = self._generate_extractive_fallback(cleaned_query, citations, hits)
                model_name = f"{model_name}-fallback"
        else:
            # Không có LLM hoặc không có hits -> fallback
            answer = self._generate_extractive_fallback(cleaned_query, citations, hits)

        elapsed_ms = round((time.time() - start_time) * 1000, 2)

        return AskResponse(
            success=True,
            query=cleaned_query,
            answer=answer,
            citations=citations,
            execution_time_ms=elapsed_ms,
            model_used=model_name
        )
