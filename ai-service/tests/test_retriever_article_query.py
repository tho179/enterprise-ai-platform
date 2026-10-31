from app.retriever import _article_numbers


def test_article_numbers_extracted_from_folded_query():
    assert _article_numbers("Điều 43 quy định gì?") == {"43"}
    assert _article_numbers("điều 9 và Điều 12") == {"9", "12"}
    assert _article_numbers("cổ tức được chia thế nào?") == set()
