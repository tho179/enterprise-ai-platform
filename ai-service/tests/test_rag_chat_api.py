import unittest
from fastapi.testclient import TestClient

from app.main import app

class TestRAGChatApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_ask_valid_question_with_citations(self):
        payload = {
            "query": "Chủ tịch Hội đồng Quản trị có quyền và nghĩa vụ gì?",
            "top_k": 2,
            "min_score": 0.3
        }
        response = self.client.post("/api/v1/chat/ask", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertTrue(data.get("success"))
        self.assertIn("answer", data)
        self.assertTrue(len(data["answer"]) > 0)
        self.assertIn("citations", data)
        self.assertGreater(len(data["citations"]), 0)
        self.assertIn("execution_time_ms", data)
        self.assertIn("model_used", data)

        # Validate citation details
        citation = data["citations"][0]
        self.assertEqual(citation["index"], 1)
        self.assertIn("chunk_id", citation)
        self.assertIn("pages", citation)
        self.assertIn("section_path", citation)
        self.assertIn("snippet", citation)

    def test_ask_empty_question_returns_400(self):
        payload = {
            "query": "   ",
            "top_k": 3
        }
        response = self.client.post("/api/v1/chat/ask", json=payload)
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data.get("success"))
        self.assertIn("error", data)
        self.assertIn(data["error"]["code"], ["HTTP_400", "VALIDATION_ERROR"])

    def test_ask_with_conversation_history(self):
        payload = {
            "query": "Thời hạn hoạt động của Công ty là bao lâu?",
            "top_k": 2,
            "history": [
                {"role": "user", "content": "Xin chào"},
                {"role": "assistant", "content": "Chào bạn, tôi có thể giúp gì cho bạn?"}
            ]
        }
        response = self.client.post("/api/v1/chat/ask", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("success"))
        self.assertIn("answer", data)
        self.assertGreater(len(data["citations"]), 0)

    def test_ask_unmatched_query_anti_hallucination(self):
        payload = {
            "query": "Cách làm bánh pizza hải sản phô mai?",
            "top_k": 2,
            "min_score": 0.95  # Unreachable threshold for document database
        }
        response = self.client.post("/api/v1/chat/ask", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("success"))
        self.assertEqual(len(data["citations"]), 0)
        is_not_found = "chưa tìm thấy" in data["answer"].lower() or "không tìm thấy" in data["answer"].lower()
        self.assertTrue(is_not_found)

if __name__ == "__main__":
    unittest.main()
