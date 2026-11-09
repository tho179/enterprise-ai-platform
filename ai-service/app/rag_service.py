import json
import re
import time
import logging
from typing import List, Dict, Any, Optional, Tuple

from app.answer_policy import _answer_shape, _content_terms, select_evidence  # noqa: F401
from app.config import settings
from app.embedding_service import fold_text
from app.knowledge_graph.pipeline import rrf_fuse
from app.knowledge_graph.service import graph_search
from app.llm_client import LLM, chat_completion, parse_json_object, resolve_llm
from app.observability import StepTimer, record_timings
from app.retriever import VectorRetriever
from app.schemas import CitationItem, ChatMessage, AskResponse

logger = logging.getLogger(__name__)

# Candidates reported to the benchmark, deep enough for Recall@10.
RETRIEVAL_REPORT_DEPTH = 10

REFUSAL_TEXT = "Dựa trên các tài liệu nội bộ hiện tại, tôi chưa tìm thấy thông tin phù hợp với câu hỏi này."

SYSTEM_PROMPT = """Bạn là Trợ lý AI Quản lý Tri thức Doanh nghiệp, trả lời câu hỏi của nhân viên bằng tiếng Việt.

Các đoạn trong NGỮ CẢNH TÀI LIỆU đã được hệ thống kiểm tra là liên quan đến câu hỏi. Hãy đọc kỹ và trả lời trực tiếp bằng thông tin trong đó, kể cả khi chỉ trả lời được một phần.

Quy tắc:
1. Chỉ dùng thông tin có trong ngữ cảnh, giữ nguyên số liệu và tên riêng, không suy diễn thêm.
2. Mỗi nhận định kết thúc bằng số thứ tự đoạn nguồn, ví dụ [1] hoặc [2].
3. Trả lời ngắn gọn, lịch sự.
4. Chỉ khi ngữ cảnh hoàn toàn không nói về chủ đề được hỏi, mới trả lời: "Dựa trên các tài liệu nội bộ hiện tại, tôi chưa tìm thấy thông tin để trả lời câu hỏi này."

Ví dụ:
NGỮ CẢNH TÀI LIỆU:
[1] Vị trí: Trang 3 | Phả hệ: Điều 7
Nội dung: Thời gian thử việc không quá 60 ngày đối với công việc có trình độ cao đẳng trở lên.
CÂU HỎI:
Thời gian thử việc tối đa là bao lâu?
TRẢ LỜI:
Thời gian thử việc không quá 60 ngày đối với công việc có trình độ cao đẳng trở lên [1]."""

VERIFY_PROMPT = """Bạn là bộ kiểm định câu trả lời. Chỉ dựa vào NGỮ CẢNH, xác định mọi thông tin trong CÂU TRẢ LỜI có được ngữ cảnh hỗ trợ và có trả lời đúng CÂU HỎI hay không.
Chỉ trả về JSON: {"supported": true} hoặc {"supported": false}."""


class RAGService:
    """
    Module M4: RAG Question Answering Service
    Orchestrates Vector Retrieval, Context Augmentation, Citation Resolution,
    and LLM Generation (Gemini / OpenAI with Extractive Fallback).
    """

    def __init__(self, retriever: Optional[VectorRetriever] = None):
        self.retriever = retriever or VectorRetriever()

    @staticmethod
    def _fuse_hits(
        vector_hits: List[Dict[str, Any]],
        graph_hits: List[Dict[str, Any]],
        graph_weight: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """RRF when both sources exist; each source still works alone."""
        if vector_hits and graph_hits:
            return rrf_fuse(
                vector_hits,
                graph_hits,
                graph_weight=settings.GRAPH_RRF_WEIGHT if graph_weight is None else graph_weight,
            )
        if graph_hits:
            return sorted(graph_hits, key=lambda hit: hit.get("score", 0.0), reverse=True)
        return vector_hits

    def retrieve_hits(
        self,
        query: str,
        top_k: int = 3,
        document_id: Optional[str] = None,
        retrieval_mode: str = "hybrid_rag",
        use_reranker: bool = True,
        graph_weight: Optional[float] = None,
        allowed_roles: Optional[List[str]] = None,
        timer: Optional[StepTimer] = None,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Retrieve candidates: vector and graph -> RRF -> cross-encoder."""
        if retrieval_mode not in ("flat_rag", "graph_rag", "hybrid_rag"):
            raise ValueError(f"Unknown retrieval mode: {retrieval_mode}")

        timer = timer or StepTimer()
        cleaned_query = (query or "").strip()
        candidate_k = min(100, max(top_k * 20, 60))
        vector_hits: List[Dict[str, Any]] = []
        graph_hits: List[Dict[str, Any]] = []

        with timer.step("embed"):
            query_vector = self.retriever.embedding.embed_query(cleaned_query)

        if retrieval_mode in ("flat_rag", "hybrid_rag"):
            with timer.step("vector_search"):
                vector_hits = self.retriever.search(
                    query=cleaned_query,
                    top_k=candidate_k,
                    document_id=document_id,
                    # Không lọc cosine trước: một đoạn đúng có thể chỉ đạt 0.24
                    # nhưng khớp chính xác "cổ tức", trong khi nhiễu đạt 0.8.
                    min_score=0.0,
                    use_reranker=False,
                    query_vector=query_vector,
                    allowed_roles=allowed_roles,
                )
        if retrieval_mode in ("graph_rag", "hybrid_rag"):
            with timer.step("graph"):
                graph_hits = graph_search(
                    cleaned_query,
                    limit=max(settings.GRAPH_SEARCH_LIMIT, top_k * 4),
                    document_id=document_id,
                    source_type="upload",
                    query_vector=query_vector,
                    seed_chunk_ids=[
                        hit["chunk_id"]
                        for hit in vector_hits[: settings.GRAPH_EXPAND_SEEDS]
                        if hit.get("chunk_id")
                    ],
                    allowed_roles=allowed_roles,
                )

        hits = self._fuse_hits(vector_hits, graph_hits, graph_weight=graph_weight)
        reranker = self.retriever.reranker
        if use_reranker and reranker.enabled and hits:
            with timer.step("rerank"):
                head = reranker.rerank(cleaned_query, hits[: settings.RERANK_CANDIDATES])
                hits = head + hits[settings.RERANK_CANDIDATES:]
        logger.info(
            "Retrieval[%s]: %d vector hits, %d graph hits, %d fused",
            retrieval_mode,
            len(vector_hits),
            len(graph_hits),
            len(hits),
        )
        return hits, vector_hits, graph_hits

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
            content = (hit.get("answer_window") or hit.get("content", "")).strip()
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
            snippet = content
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

    def _verify_answer(self, llm: LLM, query: str, context: str, answer: str) -> Optional[bool]:
        """Ask the LLM whether the context supports the answer; None if unknown."""
        try:
            raw = chat_completion(
                llm,
                [
                    {"role": "system", "content": VERIFY_PROMPT},
                    {
                        "role": "user",
                        "content": f"NGỮ CẢNH:\n{context}\n\nCÂU HỎI:\n{query}\n\nCÂU TRẢ LỜI:\n{answer}",
                    },
                ],
                temperature=0.0,
                max_tokens=40,
            )
        except Exception as exc:
            logger.warning("Answer verification failed: %s", exc)
            return None
        verdict = parse_json_object(raw)
        if verdict is None or "supported" not in verdict:
            logger.warning("Verifier returned no verdict: %r", raw[:120])
            return None
        return bool(verdict["supported"])

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
            return REFUSAL_TEXT

        blocks = []
        for idx, (hit, citation) in enumerate(zip(hits, citations), 1):
            section_path = hit.get("metadata", {}).get("section_path", [])
            section = section_path[-1] if section_path else ""
            # A "Trang N" path only repeats the page number.
            location = f"{section} ({citation.pages})" if section and not section.startswith("Trang") else citation.pages
            blocks.append(
                f"Theo quy định tại **{location}** [{idx}]:\n\n"
                f"> {citation.snippet}"
            )
        return "\n\n".join(blocks) + (
            "\n\n*(Thông tin được trích xuất trực tiếp từ tài liệu đã lập chỉ mục)*"
        )

    def ask(
        self,
        query: str,
        top_k: int = 3,
        document_id: Optional[str] = None,
        min_score: float = 0.25,
        history: Optional[List[ChatMessage]] = None,
        retrieval_mode: str = "hybrid_rag",
        use_reranker: bool = True,
        include_retrieval: bool = False,
        allowed_roles: Optional[List[str]] = None,
        graph_weight: Optional[float] = None,
        use_llm: bool = True,
    ) -> AskResponse:
        """Retrieve -> select evidence -> generate -> verify, with citations."""
        start_time = time.time()
        timer = StepTimer()
        cleaned_query = query.strip()

        # Lấy nhiều ứng viên hơn top_k: câu đúng có thể nằm ngoài top 3 do OCR
        # làm lệch cosine. Bước chọn bằng chứng bên dưới mới quyết định giữ lại.
        hits, vector_hits, graph_hits = self.retrieve_hits(
            cleaned_query,
            top_k=top_k,
            document_id=document_id,
            retrieval_mode=retrieval_mode,
            use_reranker=use_reranker,
            graph_weight=graph_weight,
            allowed_roles=allowed_roles,
            timer=timer,
        )

        with timer.step("answer_policy"):
            selected_hits = select_evidence(
                cleaned_query,
                hits,
                top_k=top_k,
                reranker=self.retriever.reranker,
                use_reranker=use_reranker,
            )
        trusted = bool(selected_hits)

        context_text, citations = (
            self._build_context_and_citations(selected_hits, cleaned_query)
            if trusted
            else ("", [])
        )

        llm = resolve_llm() if use_llm else None
        model_name = llm.model if llm else "extractive-fallback"
        verified: Optional[bool] = None

        if not trusted:
            answer = REFUSAL_TEXT
            model_name = "guardrail-refusal"
        elif llm is None:
            answer = self._generate_extractive_fallback(cleaned_query, citations, selected_hits)
        else:
            try:
                messages = [{"role": "system", "content": SYSTEM_PROMPT}]
                for msg in (history or [])[-4:]:
                    messages.append({"role": msg.role, "content": msg.content})
                messages.append({
                    "role": "user",
                    "content": f"NGỮ CẢNH TÀI LIỆU:\n{context_text}\n\nCÂU HỎI:\n{cleaned_query}",
                })
                with timer.step("llm_generate"):
                    answer = chat_completion(llm, messages)

                if "chưa tìm thấy" in answer.casefold():
                    citations = []
                elif settings.LLM_VERIFY_ANSWERS:
                    with timer.step("llm_verify"):
                        verified = self._verify_answer(llm, cleaned_query, context_text, answer)
                    if verified is False:
                        # The evidence passed the gate but the generated wording
                        # did not: show the verbatim excerpt instead.
                        logger.warning("Verifier rejected generated answer; using excerpt")
                        answer = self._generate_extractive_fallback(cleaned_query, citations, selected_hits)
                        model_name = f"{llm.model}-rejected-extractive"
            except Exception as exc:
                logger.warning("LLM call failed (%s), reverting to extractive answer", exc)
                answer = self._generate_extractive_fallback(cleaned_query, citations, selected_hits)
                model_name = f"{llm.model}-fallback"

        record_timings(timer.steps)
        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        logger.info("Ask finished in %.0f ms: %s", elapsed_ms, timer.steps)

        return AskResponse(
            success=True,
            query=cleaned_query,
            answer=answer,
            citations=citations,
            execution_time_ms=elapsed_ms,
            model_used=model_name,
            graph_candidates=len(graph_hits),
            verified=verified,
            timings_ms=timer.steps,
            retrieved_chunk_ids=[
                hit.get("chunk_id", "") for hit in hits[:RETRIEVAL_REPORT_DEPTH]
            ] if include_retrieval else [],
            retrieved_contents=[
                hit.get("content", "") for hit in hits[:RETRIEVAL_REPORT_DEPTH]
            ] if include_retrieval else [],
        )
