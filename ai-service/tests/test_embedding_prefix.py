import unittest

from app.embedding_service import EmbeddingService


class _Encoded:
    def __init__(self, texts, flat=False):
        self._texts = texts
        self._flat = flat

    def tolist(self):
        if self._flat:
            return [float(len(text)) for text in self._texts]
        return [[float(len(text))] for text in self._texts]


class _FakeModel:
    def __init__(self):
        self.seen = []

    def encode(self, texts, **kwargs):
        if isinstance(texts, str):
            self.seen.append(texts)
            return _Encoded([texts], flat=True)
        self.seen.append(list(texts))
        return _Encoded(texts)


def _service(query_prefix="query: ", passage_prefix="passage: "):
    service = object.__new__(EmbeddingService)
    service.model_name = "fake"
    service.vector_dim = 1
    service.model = _FakeModel()
    service.query_prefix = query_prefix
    service.passage_prefix = passage_prefix
    return service


class TestEmbeddingPrefix(unittest.TestCase):
    def test_query_uses_query_prefix_and_keeps_accents(self):
        service = _service()

        service.embed_query("Hội đồng Quản trị")

        self.assertEqual(service.model.seen, ["query: Hội đồng Quản trị"])

    def test_documents_use_passage_prefix(self):
        service = _service()

        service.embed_documents(["Điều 14. Quyền của cổ đông."])

        self.assertEqual(
            service.model.seen,
            [["passage: Điều 14. Quyền của cổ đông."]],
        )

    def test_empty_prefix_keeps_accents(self):
        service = _service(query_prefix="", passage_prefix="")

        service.embed_query("Hội đồng")

        self.assertEqual(service.model.seen, ["Hội đồng"])


if __name__ == "__main__":
    unittest.main()
