import time
import logging
from typing import List, Dict, Any, Optional, Tuple
from openai import OpenAI

from app.config import settings
from app.retriever import VectorRetriever
from app.schemas import CitationItem, ChatMessage, AskResponse

logger = logging.getLogger(__name__)

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
        hits: List[Dict[str, Any]]
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
            snippet = content[:180] + "..." if len(content) > 180 else content
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
        if not hits:
            return "Dựa trên các tài liệu nội bộ hiện tại, tôi chưa tìm thấy thông tin phù hợp với câu hỏi này."

        best = hits[0]
        meta = best.get("metadata", {})
        path_str = " > ".join(meta.get("section_path", []))
        summary_intro = f"Theo quy định tại **{path_str or 'tài liệu nội bộ'}** [1]:\n\n"
        content = best.get("content", "").strip()

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

        # Step 2: Format context and citations
        context_text, citations = self._build_context_and_citations(hits)

        # Step 3: Determine generation strategy
        client, model_name = self._get_llm_client()

        answer = ""
        if client is not None and hits:
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
