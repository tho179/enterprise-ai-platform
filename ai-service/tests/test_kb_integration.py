"""KB integration: .cypher loading, uncertainty, fuzzy resolution, conflicts."""
from app.knowledge_graph import consistency, resolve, schema
from app.knowledge_graph.cypher_loader import parse, split_statements
from app.knowledge_graph.extract import effective_date, extract_entities, heading_entity


# ------------------------------------------------------------- .cypher files
def test_cypher_blocks_are_parsed_by_name():
    text = "// header\n// :name A\nMATCH (n) RETURN n;\n\n// note\n// :name B\nRETURN 1;\n"
    assert parse(text) == {"A": "MATCH (n) RETURN n", "B": "RETURN 1"}


def test_schema_block_splits_into_statements():
    assert len(schema.CONSTRAINTS) == 6
    assert all(statement.startswith("CREATE") for statement in schema.CONSTRAINTS + schema.INDEXES)
    assert any("VECTOR INDEX" in statement for statement in schema.INDEXES)
    assert split_statements("A;\nB;\n") == ["A", "B"]


def test_retrieval_reads_only_current_non_duplicate_documents():
    for name in ("GRAPH_CANDIDATES", "EXPAND_REFERENCES", "EXPAND_SHARED_ENTITIES"):
        query = schema.QUERIES[name]
        assert "coalesce(d.is_current, true)" in query
        assert "d.duplicate_of IS NULL" in query


def test_quality_queries_are_loaded():
    assert {"Q_SIZE", "Q_COVERAGE", "Q_INTEGRITY", "Q_CONSISTENCY", "Q_FRESHNESS"} <= set(schema.QUALITY_QUERIES)


# ------------------------------------------------------- extraction certainty
def _by_name(text):
    return {entity["name"]: entity for entity in extract_entities(text)}


def test_mentions_carry_confidence_and_method():
    entities = _by_name("Hội đồng Quản trị họp theo Điều 15.")
    assert entities["Hội đồng Quản trị"]["method"] == "alias_full"
    assert entities["Điều 15"]["confidence"] == 0.95


def test_ocr_damaged_alias_matches_with_lower_confidence():
    # Real OCR output from "Phu luc sua doi dieu le lan 3 2".
    entity = _by_name("Vôn Điều Lệ của Công Tỳ là 5.431.327.770.000 đồng")["Vốn điều lệ"]
    assert entity["method"] == "alias_folded"
    assert entity["confidence"] < 0.7


def test_correct_spelling_keeps_the_higher_confidence():
    entity = _by_name("Vốn điều lệ của Công ty")["Vốn điều lệ"]
    assert entity["method"] == "alias_full"


def test_english_and_vietnamese_names_share_one_entity():
    english = _by_name("The Board of Directors approved the dividend.")
    vietnamese = _by_name("Hội đồng Quản trị thông qua cổ tức.")
    assert english["Hội đồng Quản trị"]["entity_id"] == vietnamese["Hội đồng Quản trị"]["entity_id"]
    assert english["Cổ tức"]["method"] == "alias_en"


def test_alias_needs_word_boundary():
    assert "Trái phiếu" not in _by_name("team bonding activities")  # "bond" inside a word
    assert "Trái phiếu" in _by_name("the company issued bonds")
    assert "Tổng Giám đốc" in _by_name("The CEO signed.")


def test_errors_found_by_the_precision_sample_are_fixed():
    # Each case comes from a mention labelled wrong in data/eval/kb_entity_sample.json.
    assert "Cổ phần" not in _by_name("CÔNG TY CỔ PHẦN HÀNG TIÊU DÙNG MASAN")
    assert "Cổ phần" in _by_name("Công ty Cổ phần Masan được chia thành 726.793.818 cổ phần")
    assert not any(e["type"] == "van_ban" for e in extract_entities("Điều 35: Nguyên Tắc Xử Lý Kỷ Luật Lao Động"))
    assert "Luật An toàn thông tin mạng" in _by_name("Luật An toàn thông tin Mạng 24/2018/QH14")
    assert "Nghị định 155/2020/NĐ-CP" in _by_name("Nghị định số 155/2020/NĐ- CP ngày 31")
    assert heading_entity(["Điều lệ lần thứ năm ký ngày 23 tháng 4 năm 2014"]) is None
    assert heading_entity(["CHƯƠNG XIV. TÀI KHOẢN NGÂN HÀNG VÀ HỆ THÓNG KÉ TOÁN34"]) is None


def test_numbers_are_normalised():
    assert "Điều 7" in _by_name("theo Điều 07 của Điều lệ")
    assert "5/3/2020" in _by_name("ký ngày 05/03/2020")


def test_heading_entity_is_low_confidence():
    entity = heading_entity(["Điều 3. Quyền và nghĩa vụ của cổ đông"])
    assert entity["method"] == "heading" and entity["confidence"] == 0.6


def test_effective_date_from_title_then_text():
    assert effective_date("Dieu le cong ty 2025", "") == ("2025-01-01", "title")
    assert effective_date("Phu luc", "Hà Nội, ngày 26 tháng 4 năm 2023") == ("2023-04-26", "text")
    assert effective_date("Phu luc", "không có ngày") == (None, None)


def test_amendment_date_is_the_latest_cited_date():
    # Opening of "Phu luc sua doi dieu le lan 3 1": it cites earlier versions first.
    head = ("Điều lệ ký ngày 23 tháng 4 năm 2012, lần thứ hai ký ngày 18 tháng 02 năm 2013. "
            "Nghị quyết số 09/2013 ngày 22/4/2013. Hôm nay, ngày 22 tháng 4 năm 2013")
    assert effective_date("Phu luc sua doi dieu le lan 3 1", head) == ("2013-04-22", "text")


# ------------------------------------------------------ fuzzy entity matching
def test_membership_function_is_piecewise_linear():
    assert resolve.membership(0.70) == 0.0
    assert resolve.membership(0.86) == 0.5
    assert resolve.membership(0.95) == 1.0


def test_different_numbers_never_match():
    assert resolve.similarity("Nghị định 155/2020/NĐ-CP", "Nghị định 156/2020/NĐ-CP") == 0.0


def test_case_and_punctuation_variants_are_same_as():
    score = resolve.similarity("Quyền và nghĩa vụ của cổ đông", "Quyền, nghĩa vụ của Cổ đông")
    assert resolve.decide(score) == "SAME_AS"


def test_close_but_different_titles_go_to_review():
    score = resolve.similarity("Nhiệm vụ của Tổng Giám đốc", "Nhiệm vụ của Giám đốc")
    assert resolve.decide(score) == "POSSIBLY_SAME_AS"


def test_negation_blocks_automatic_merge():
    # Real pair from the corpus: similarity 0.96 but opposite meaning.
    entities = [
        {"entity_id": "a", "name": "Quy trình xử lý vụ việc chưa xác định người vi phạm", "type": "tieu_de"},
        {"entity_id": "b", "name": "Quy trình xử lý vụ việc đã xác định người vi phạm", "type": "tieu_de"},
    ]
    [pair] = resolve.resolve_pairs(entities)
    assert pair["relation"] == "POSSIBLY_SAME_AS" and pair["guard"] == "phu_dinh"


def test_manual_decisions_are_never_overridden():
    entities = [
        {"entity_id": "a", "name": "Quyền của cổ đông", "type": "tieu_de"},
        {"entity_id": "b", "name": "Quyền của Cổ đông.", "type": "tieu_de"},
    ]
    assert resolve.resolve_pairs(entities)
    assert resolve.resolve_pairs(entities, manual={("a", "b"): "NOT_SAME_AS"}) == []


def test_numbered_types_are_not_fuzzy_matched():
    entities = [
        {"entity_id": "a", "name": "Điều 7", "type": "dieu_khoan"},
        {"entity_id": "b", "name": "Điều 17", "type": "dieu_khoan"},
    ]
    assert resolve.resolve_pairs(entities) == []


# ------------------------------------------------------- duplicates, versions
BODY = " ".join(f"điều khoản số {i} quy định nội dung quản trị công ty" for i in range(60))


def test_upload_copy_is_kept_over_offline_pdf():
    docs = [
        {"doc_id": "pdf", "title": "Dieu le 2021", "source_type": "pdf", "source_trust": 1.0, "text": BODY},
        {"doc_id": "up", "title": "Điều lệ - 2021", "source_type": "upload", "source_trust": 1.0, "text": BODY + " thêm"},
        {"doc_id": "other", "title": "Nội quy", "source_type": "pdf", "text": "nội quy lao động " * 40},
    ]
    pairs = consistency.find_duplicates(docs)
    assert [(p["duplicate"], p["keep"], p["relation"]) for p in pairs] == [("pdf", "up", "DUPLICATE_OF")]


def test_partial_overlap_is_similar_not_duplicate():
    # A new charter version shares most clauses with the old one.
    old = BODY
    kept = " ".join(f"điều khoản số {i} quy định nội dung quản trị công ty" for i in range(50))
    new = kept + " " + " ".join(f"khoản bổ sung thứ {i} về tăng vốn" for i in range(10))  # ~84% shared
    docs = [
        {"doc_id": "v2021", "title": "Dieu le 2021", "source_type": "pdf", "text": old},
        {"doc_id": "v2025", "title": "Dieu le 2025", "source_type": "pdf", "text": new},
    ]
    [pair] = consistency.find_duplicates(docs)
    assert pair["relation"] == "SIMILAR_TO"


def test_series_orders_versions_by_effective_date():
    docs = [
        {"doc_id": "d25", "title": "Dieu le cong ty 2025", "source_type": "pdf", "effective_date": "2025-01-01"},
        {"doc_id": "d21", "title": "Dieu le cong ty 2021", "source_type": "pdf", "effective_date": "2021-01-01"},
        {"doc_id": "d26", "title": "Dieu le cong ty 2026", "source_type": "pdf", "effective_date": "2026-01-01"},
        {"doc_id": "up", "title": "Điều lệ công ty - 2021", "source_type": "upload", "effective_date": "2021-01-01"},
    ]
    links = consistency.find_series(docs)
    assert [(link["new"], link["old"]) for link in links] == [("d25", "d21"), ("d26", "d25")]


# -------------------------------------------------------------- conflicts
def _chunk(cid, text, date, **extra):
    return {"chunk_id": cid, "doc_id": cid, "text": text, "source_trust": 1.0,
            "is_current": True, "effective_date": date, **extra}


def test_claim_extracted_through_ocr_noise():
    claims = consistency.extract_claims(_chunk(
        "c1",
        "Vôn Điều Lệ của Công Tỳ là 5.431.327.770.000 đồng (Năm nghìn bốn trăm tỷ đồng).",
        "2019-01-01",
    ))
    capital = [c for c in claims if c["attribute"] == "Vốn điều lệ"]
    assert capital[0]["value"] == 5_431_327_770_000
    assert "khop_khong_dau" in capital[0]["flags"]


def test_share_count_mismatch_is_flagged():
    # Real OCR case: 135.553.179 shares x 10.000 đ != 7.355.531.790.000 đ.
    claims = consistency.extract_claims(_chunk(
        "c1",
        "Vốn Điều Lệ của Công Ty là 7.355.531.790.000 đồng. "
        "Vốn Điều Lệ của Công Ty được chia thành 135.553.179 cổ phần với mệnh giá là 10.000 đồng.",
        "2020-01-01",
    ))
    capital = [c for c in claims if c["attribute"] == "Vốn điều lệ"][0]
    assert "lech_so_co_phan_x_menh_gia" in capital["flags"]


def test_newer_document_wins_and_older_value_is_superseded():
    old = consistency.extract_claims(_chunk("c21", "Vốn Điều Lệ của Công Ty là 7.267.938.180.000 đồng.", "2021-01-01"))
    new = consistency.extract_claims(_chunk("c25", "Vốn Điều Lệ của Công Ty là 10.623.648.220.000 đồng.", "2025-01-01"))
    claims, conflicts = consistency.resolve_conflicts(old + new)
    status = {c["chunk_id"]: c["status"] for c in claims if c["attribute"] == "Vốn điều lệ"}
    assert status == {"c21": "superseded", "c25": "accepted"}
    assert conflicts[0]["reason"] == "R2_hieu_luc_moi_hon"


def test_tie_without_rule_is_left_for_review():
    a = consistency.extract_claims(_chunk("a", "Vốn điều lệ là 1.000.000.000.000 đồng.", None))
    b = consistency.extract_claims(_chunk("b", "Vốn điều lệ là 2.000.000.000.000 đồng.", None))
    claims, conflicts = consistency.resolve_conflicts(a + b)
    assert {c["status"] for c in claims} == {"unresolved"}
    assert conflicts[0]["reason"] == "khong_phan_dinh_duoc"


def test_agreeing_sources_are_all_accepted():
    a = consistency.extract_claims(_chunk("a", "mệnh giá là 10.000 đồng/cổ phần", "2020-01-01"))
    b = consistency.extract_claims(_chunk("b", "mệnh giá 10.000 đồng/cổ phần", "2025-01-01"))
    claims, conflicts = consistency.resolve_conflicts(a + b)
    assert {c["status"] for c in claims} == {"accepted"} and conflicts == []
