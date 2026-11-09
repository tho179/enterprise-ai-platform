import pytest

from app.answer_policy import _answer_shape
from app.config import settings
from app.rag_service import RAGService


@pytest.fixture(autouse=True)
def domain_rules_on(monkeypatch):
    """These cases pin the optional corpus-tuned rules."""
    monkeypatch.setattr(settings, "ANSWER_DOMAIN_RULES", True)


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


def test_count_question_rejects_shareholder_rights_clause():
    content = (
        "Cô đông là tổ chức sở hữu ít nhất 10% tổng số cổ phần phổ thông "
        "có thể ủy quyền tối đa 03 Người đại diện theo ủy quyền."
    )

    assert _answer_shape("Công ty có bao nhiêu cổ đông?", content) is None


def test_count_question_accepts_board_size_clause():
    content = (
        "Hội đồng Quản trị có từ 03 đến 11 thành viên. Số lượng cụ thể "
        "thành viên Hội đồng Quản trị cho từng nhiệm kỳ sẽ được Đại hội đồng "
        "Cổ đông quyết định."
    )

    assert _answer_shape(
        "Công ty có bao nhiêu thành viên Hội đồng Quản trị?", content
    ) == "count"


def test_term_question_accepts_term_clause_not_meeting_window():
    term_clause = (
        "Nhiệm kỳ của thành viên Hội đồng Quản trị không quá năm (05) năm; "
        "thành viên Hội đồng Quản trị có thể được bầu lại."
    )
    meeting_clause = (
        "Cuộc họp đầu tiên của nhiệm kỳ Hội đồng Quản trị để bầu Chủ tịch "
        "phải được tiến hành trong thời hạn bảy ngày làm việc."
    )

    assert _answer_shape("Nhiệm kỳ của Hội đồng Quản trị là bao lâu?", term_clause) == "time"
    assert _answer_shape("Nhiệm kỳ của Hội đồng Quản trị là bao lâu?", meeting_clause) is None


def test_postponement_question_accepts_correct_duration_only():
    wrong = (
        "Đại hội đồng Cổ đông phải họp thường niên trong thời hạn 4 tháng "
        "kể từ ngày kết thúc năm tài chính, nhưng không quá 06 tháng."
    )
    right = (
        "Thời gian hoãn tối đa không quá ba ngày làm việc kể từ ngày dự định "
        "khai mạc cuộc họp Đại hội đồng Cổ đông."
    )

    question = "Thời gian hoãn họp Đại hội đồng cổ đông tối đa là bao lâu?"
    assert _answer_shape(question, wrong) is None
    assert _answer_shape(question, right) == "time"


def test_third_meeting_question_rejects_second_meeting_clause():
    second = "Cuộc họp Đại hội đồng Cổ đông lần thứ hai được tiến hành khi có 33% cổ phần tham dự."
    third = (
        "Thông báo mời họp lần thứ ba phải được gửi trong thời hạn 20 ngày. "
        "Trong trường hợp này cuộc họp được tiến hành không phụ thuộc vào số "
        "lượng Cổ đông tham dự."
    )

    question = "Cuộc họp Đại hội đồng cổ đông lần thứ ba có cần đủ số lượng cổ đông không?"
    assert _answer_shape(question, second) is None
    assert _answer_shape(question, third) == "meeting"


def test_audit_question_rejects_committee_membership_clause():
    committee = (
        "Thành viên Ủy ban Kiểm toán phải có kiến thức về kế toán, kiểm toán "
        "và không làm việc trong bộ phận kế toán."
    )
    mandatory = "Báo cáo tài chính năm phải được kiểm toán theo quy định của Pháp luật."

    question = "Công ty có bắt buộc phải kiểm toán không?"
    assert _answer_shape(question, committee) is None
    assert _answer_shape(question, mandatory) == "yesno"


def test_loan_question_accepts_board_approval_clause():
    content = (
        "Hội đồng Quản trị quyết định các hợp đồng mua, bán, vay, cho vay và "
        "hợp đồng khác có giá trị nhỏ hơn 35% tổng giá trị tài sản của Công ty."
    )

    assert _answer_shape("Công ty có thể cho vay không?", content) == "yesno"


def test_who_signs_contract_accepts_director_clause():
    content = (
        "Tổng Giám đốc quyết định các vấn đề kinh doanh hằng ngày, bao gồm "
        "việc thay mặt Công ty ký kết các hợp đồng mà Công ty là một bên."
    )

    assert _answer_shape("Ai có quyền ký hợp đồng thay Công ty?", content) == "who"


def test_dividend_question_accepts_payment_condition():
    content = (
        "Công ty chỉ được trả cổ tức cho Cổ đông khi Công ty đã hoàn thành "
        "nghĩa vụ thuế và các nghĩa vụ tài chính khác theo quy định."
    )

    assert _answer_shape("Cổ tức được trả khi nào?", content) == "time"


def test_out_of_scope_question_is_not_answered():
    content = "Điều lệ quy định cơ cấu tổ chức và quyền của cổ đông."

    assert _answer_shape("Cách làm bánh pizza hải sản phô mai?", content) is None
