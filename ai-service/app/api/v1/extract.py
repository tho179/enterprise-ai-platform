import logging
import os
import tempfile
from pathlib import Path

import pymupdf
from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.adaptive_chunker import AdaptiveChunker
from app.document_parser import extract_text_from_pdf
from app.knowledge_graph.extract import pages_to_nodes
from app.schemas import ExtractedChunk, ExtractedPage, ExtractResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/extract", tags=["Extract"])

MAX_PDF_BYTES = 25 * 1024 * 1024
READ_BLOCK = 1024 * 1024


def build_extract_chunks(pages: list[dict]) -> list[ExtractedChunk]:
    chunks = AdaptiveChunker().chunk_nodes(pages_to_nodes(pages))
    return [
        ExtractedChunk(
            index=index,
            pageStart=int(chunk.metadata.get("page_start", 1)),
            pageEnd=int(chunk.metadata.get("page_end", 1)),
            headingLevel=len(chunk.metadata.get("section_path") or []),
            sectionPath=list(chunk.metadata.get("section_path") or []),
            content=chunk.content,
        )
        for index, chunk in enumerate(chunks)
    ]


@router.post("", response_model=ExtractResponse)
def extract_pdf(file: UploadFile = File(...)) -> ExtractResponse:
    """Extract PDF pages, using OCR for pages without a usable text layer."""
    filename = file.filename or "document.pdf"
    if Path(filename).suffix.lower() != ".pdf":
        raise HTTPException(status_code=400, detail="Chỉ hỗ trợ tệp PDF.")

    fd, temp_path = tempfile.mkstemp(suffix=".pdf")
    try:
        size = 0
        with os.fdopen(fd, "wb") as output:
            while True:
                block = file.file.read(READ_BLOCK)
                if not block:
                    break
                size += len(block)
                if size > MAX_PDF_BYTES:
                    raise HTTPException(status_code=413, detail="Tệp PDF vượt quá 25 MB.")
                output.write(block)

        try:
            with pymupdf.open(temp_path) as document:
                page_count = document.page_count
        except Exception as exc:
            logger.exception("Cannot open uploaded PDF")
            raise HTTPException(status_code=422, detail=f"Không đọc được PDF: {exc}") from exc

        if page_count < 1:
            raise HTTPException(status_code=422, detail="Tệp PDF không có trang nào.")

        try:
            pages = extract_text_from_pdf(temp_path)
        except Exception as exc:
            logger.exception("PDF text/OCR extraction failed")
            raise HTTPException(status_code=422, detail=f"Không trích xuất được PDF: {exc}") from exc

        if not pages:
            raise HTTPException(
                status_code=422,
                detail="Không trích xuất được văn bản từ PDF, kể cả OCR.",
            )

        native_pages = sum(1 for page in pages if page["source"] == "native")
        ocr_pages = len(pages) - native_pages
        logger.info(
            "Extracted %s/%s pages from PDF (%s native, %s OCR)",
            len(pages),
            page_count,
            native_pages,
            ocr_pages,
        )
        return ExtractResponse(
            pageCount=page_count,
            nativePages=native_pages,
            ocrPages=ocr_pages,
            pages=[
                ExtractedPage(page=page["page"], text=page["text"], source=page["source"], words=page.get("words", []))
                for page in pages
            ],
            chunks=build_extract_chunks(pages),
        )
    finally:
        try:
            os.unlink(temp_path)
        except OSError:
            pass
