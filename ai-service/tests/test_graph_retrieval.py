"""Fusion, graph traversal and graph enrichment without a live Neo4j."""
from app.adaptive_chunker import AdaptiveChunker
from app.knowledge_graph.enrich import describe_entity, enrich_entities
from app.knowledge_graph.extract import (
    extract_entities,
    heading_entity,
    link_chunks,
    own_article,
    pages_to_nodes,
)
from app.knowledge_graph.pipeline import rrf_fuse
from app.knowledge_graph.service import graph_search


def chunk(chunk_id, text, section_path):
    return {
        "chunk_id": chunk_id,
        "text": text,
        "section_path": section_path,
        "entities": extract_entities(text),
    }


class FakeStore:
    def __init__(self):
        self.candidate_args = None
        self.expand_args = None

    def entity_names(self, kb_id="KB", limit=5000):
        return ["Cổ tức"]

    def similar_entities(self, vector, min_score, k=5):
        return ["Nghỉ hằng năm"]

    def graph_candidates(self, names, kb_ids, limit, **filters):
        self.candidate_args = {"names": names, **filters}
        return [{"chunk_id": "direct", "content": "a", "matched": 2, "related": 0, "via": "entity"}]

    def expand_from_chunks(self, seed_ids, limit, max_entity_df, **filters):
        self.expand_args = {"seed_ids": seed_ids, **filters}
        return [
            {"chunk_id": "direct", "content": "a", "matched": 1, "related": 1, "via": "references"},
            {"chunk_id": "cited", "content": "b", "matched": 1, "related": 1, "via": "references"},
        ]


def test_rrf_rewards_agreement_between_sources():
    vector = [{"chunk_id": "a"}, {"chunk_id": "b"}]
    graph = [{"chunk_id": "b"}]
    fused = rrf_fuse(vector, graph, graph_weight=1.0)
    assert [hit["chunk_id"] for hit in fused] == ["b", "a"]


def test_rrf_weight_zero_keeps_vector_order():
    vector = [{"chunk_id": "a"}, {"chunk_id": "b"}]
    graph = [{"chunk_id": "b"}, {"chunk_id": "c"}]
    fused = rrf_fuse(vector, graph, graph_weight=0.0)
    assert [hit["chunk_id"] for hit in fused][:2] == ["a", "b"]


def test_graph_search_merges_entity_and_traversal_hits():
    store = FakeStore()
    hits = graph_search(
        "Cổ tức trả khi nào?",
        store=store,
        query_vector=[0.1],
        seed_chunk_ids=["seed"],
        document_id="d1",
        allowed_roles=["EMPLOYEE"],
    )
    assert [hit["chunk_id"] for hit in hits] == ["direct", "cited"]
    assert hits[1]["graph_via"] == "references"
    assert "Nghỉ hằng năm" in store.candidate_args["names"]
    assert store.candidate_args["document_id"] == "d1"
    assert store.expand_args["allowed_roles"] == ["EMPLOYEE"]


def test_graph_search_traverses_when_question_has_no_entity():
    class NoEntities(FakeStore):
        def entity_names(self, kb_id="KB", limit=5000):
            return []

        def similar_entities(self, vector, min_score, k=5):
            return []

    hits = graph_search("Câu hỏi chung chung", store=NoEntities(), seed_chunk_ids=["seed"])
    assert {hit["chunk_id"] for hit in hits} == {"direct", "cited"}


def test_references_link_clauses_of_the_same_document():
    chunks = [
        chunk("a", "Điều 5. Cổ tức được trả theo quy định tại Điều 9.", ["ĐIỀU 5. CỔ TỨC"]),
        chunk("b", "Điều 9. Thủ tục chi trả.", ["ĐIỀU 9. THỦ TỤC CHI TRẢ"]),
    ]
    link_chunks(chunks)
    assert chunks[0]["references"] == [{"target": "b", "article": "Điều 9"}]
    assert chunks[1]["references"] == []


def test_article_of_an_external_law_is_not_a_reference():
    chunks = [
        chunk("a", "Áp dụng theo Điều 9 Luật Doanh nghiệp.", ["ĐIỀU 5. ÁP DỤNG"]),
        chunk("b", "Điều 9. Thủ tục.", ["ĐIỀU 9. THỦ TỤC NỘI BỘ"]),
    ]
    link_chunks(chunks)
    assert chunks[0]["references"] == []


def test_own_article_prefers_section_path():
    assert own_article(["CHƯƠNG II", "ĐIỀU 7. X"], "Theo Điều 3") == "7"
    assert own_article([], "Điều 3. Nội dung") == "3"
    assert own_article(["Trang 4"], "Nội dung") is None


def test_heading_topic_is_normalised():
    entity = heading_entity(["ĐIỀU 12. QUYỀN CỦA CỔ ĐÔNG"])
    assert entity["name"] == "Quyền của cổ đông"
    assert entity["type"] == "tieu_de"
    assert heading_entity(["Trang 4"]) is None


def test_heading_equal_to_canonical_entity_is_not_duplicated():
    assert heading_entity(["ĐIỀU 3. HỘI ĐỒNG QUẢN TRỊ"]) is None


def test_applies_to_points_at_the_section_subject():
    chunks = [chunk("a", "Nội dung về nhiệm vụ.", ["ĐIỀU 3. NHIỆM VỤ CỦA HỘI ĐỒNG QUẢN TRỊ"])]
    link_chunks(chunks)
    names = {entity["entity_id"]: entity["name"] for entity in extract_entities("Hội đồng Quản trị")}
    assert set(names) <= set(chunks[0]["applies_to"])


def test_aliases_resolve_to_one_entity():
    long_form = extract_entities("Hội đồng Quản trị họp mỗi quý")
    short_form = extract_entities("HĐQT họp mỗi quý")
    assert [e["entity_id"] for e in long_form] == [e["entity_id"] for e in short_form]


def test_legal_documents_are_extracted():
    names = {e["name"] for e in extract_entities(
        "Căn cứ Luật Doanh nghiệp và Nghị định 155/2020/NĐ-CP của Chính phủ."
    )}
    assert "Luật Doanh nghiệp" in names
    assert "Nghị định 155/2020/NĐ-CP" in names


def test_description_comes_from_source_text():
    text = "Phần đầu không liên quan. Cổ tức được trả bằng tiền mặt. Phần cuối."
    assert describe_entity("Cổ tức", [text]) == "Cổ tức được trả bằng tiền mặt."


def test_enrichment_is_idempotent():
    class Store:
        def __init__(self):
            self.pending = [{"entity_id": "e1", "name": "Cổ tức", "samples": ["Cổ tức trả sau."]}]
            self.saved = []

        def entities_missing_embedding(self, limit):
            pending, self.pending = self.pending, []
            return pending

        def set_entity_enrichment(self, rows):
            self.saved.extend(rows)

    class Embedder:
        def embed_documents(self, texts):
            return [[0.5] for _ in texts]

    store = Store()
    assert enrich_entities(store, Embedder()) == 1
    assert enrich_entities(store, Embedder()) == 0
    assert store.saved[0]["embedding"] == [0.5]


def _paths(lines):
    nodes = pages_to_nodes([{"page": 1, "text": chr(10).join(lines)}])
    return {node["text"]: node["section_path"] for node in nodes}


def test_ordinary_text_is_not_a_heading():
    paths = _paths([
        "CHƯƠNG II. CỔ PHẦN",
        "phần vốn góp hoặc cổ phần;",
        "điều lệ.",
        "Điều 51 của Điều lệ này quy định việc giải thể.",
    ])
    assert all(path == ["CHƯƠNG II. CỔ PHẦN"] for path in paths.values())


def test_articles_are_siblings_not_nested():
    paths = _paths(["Điều 1: Đối tượng", "Nội dung một.", "", "Điều 2: Thời hạn", "Nội dung hai."])
    assert paths["Nội dung hai."] == ["Điều 2: Thời hạn"]


def test_article_stays_under_its_chapter():
    paths = _paths(["CHƯƠNG I. CHUNG", "Điều 1. A", "Một.", "", "CHƯƠNG II. RIÊNG", "Điều 2. B", "Hai."])
    assert paths["Hai."] == ["CHƯƠNG II. RIÊNG", "Điều 2. B"]


def test_ocr_lowercase_l_article_is_a_heading():
    paths = _paths(["Điều l. Phạm vi", "Nội dung."])
    assert paths["Nội dung."] == ["Điều l. Phạm vi"]


def test_numbered_titles_structure_policy_documents():
    paths = _paths(["V. QUY TRÌNH THỰC HIỆN", "5.1 XỬ LÝ VỤ VIỆC", "Nội dung.", "", "VI. HIỆU LỰC THI HÀNH", "Cuối."])
    assert paths["Nội dung."] == ["V. QUY TRÌNH THỰC HIỆN", "5.1 XỬ LÝ VỤ VIỆC"]
    assert paths["Cuối."] == ["VI. HIỆU LỰC THI HÀNH"]


def test_numbered_clause_inside_an_article_is_body_text():
    paths = _paths(["Điều 3. Quyền", "1. CỔ ĐÔNG LỚN CÓ QUYỀN", "Nội dung."])
    assert paths["Nội dung."] == ["Điều 3. Quyền"]


def test_heading_stays_with_its_long_body():
    long_body = "Câu nội dung của điều khoản này khá dài. " * 60
    chunks = AdaptiveChunker(chunk_size=800)._fallback_split("Điều 26. Thành phần" + chr(10) * 2 + long_body)
    assert chunks[0].startswith("Điều 26. Thành phần")
    assert len(chunks[0]) > 100
