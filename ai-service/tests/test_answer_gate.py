from app.rag_service import RAGService


def test_extractive_fallback_refuses_when_not_trusted():
    service = object.__new__(RAGService)
    answer = service._generate_extractive_fallback(
        "được nghỉ tối đa bao nhiêu ngày",
        [],
        [{"content": "Nội dung không liên quan", "metadata": {}}],
    )
    assert "chưa tìm thấy" in answer.lower()
