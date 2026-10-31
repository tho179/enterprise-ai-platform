from app.rag_service import RAGService


def test_extractive_fallback_refuses_when_not_trusted():
    service = object.__new__(RAGService)
    answer = service._generate_extractive_fallback(
        "được nghỉ tối đa bao nhiêu ngày",
        [],
        [{"content": "Nội dung không liên quan", "metadata": {}}],
    )
    assert "chưa tìm thấy" in answer.lower()


def test_focused_excerpt_starts_at_relevant_sentence():
    service = object.__new__(RAGService)
    content = (
        "Điều 1. Quy định chung về quản trị công ty. "
        "Công ty có thể mua lại cổ phần của mình. "
        "Việc mua lại không quá 10% tổng số cổ phần của từng loại đã bán. "
        "Các nội dung khác không liên quan."
    )

    excerpt = service._focused_excerpt(
        "Công ty có thể mua lại cổ phần không?", content
    )

    assert excerpt.startswith("Công ty có thể mua lại cổ phần")
    assert "10%" in excerpt


def test_focused_excerpt_keeps_article_heading():
    service = object.__new__(RAGService)
    content = (
        "Các quy định chung về quyền và nghĩa vụ. "
        "Điều 43. Trả cổ tức. Cổ tức được trả bằng tiền mặt. "
        "Các nội dung khác."
    )

    excerpt = service._focused_excerpt("Điều 43 quy định gì?", content)

    assert excerpt.startswith("Điều 43")
    assert "cổ tức" in excerpt.lower()


def test_focused_excerpt_joins_ocr_line_breaks():
    service = object.__new__(RAGService)
    content = (
        "Việc Công ty mua lại không quá 10% tổng số cổ phần\n"
        "của từng loại đã bán trong mỗi mười hai tháng."
    )

    excerpt = service._focused_excerpt(
        "Công ty có thể mua lại cổ phần không?", content
    )

    assert "mười hai tháng" in excerpt


def test_focused_excerpt_stops_before_chapter_heading():
    service = object.__new__(RAGService)
    content = (
        "Trừ khi chấm dứt hoạt động theo Điều 51 của Điều lệ này, "
        "thời hạn hoạt động của Công ty là vô thời hạn kể từ Ngày Thành lập. "
        "CHƯƠNG III MỤC TIÊU, PHẠM VI KINH DOANH. "
        "Điều 3. Mục tiêu hoạt động."
    )

    excerpt = service._focused_excerpt(
        "Thời hạn hoạt động của Công ty là bao lâu?", content
    )

    assert excerpt.startswith("Trừ khi")
    assert "CHƯƠNG" not in excerpt
