import unittest
from fastapi.testclient import TestClient

from app.main import app

class TestRetrievalApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_root_and_health_endpoints(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get("success"))

        health_resp = self.client.get("/health")
        self.assertEqual(health_resp.status_code, 200)
        self.assertEqual(health_resp.json().get("status"), "healthy")

    def test_search_stats_endpoint(self):
        response = self.client.get("/api/v1/search/stats")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("success"))
        self.assertIn("total_points", data)
        self.assertIn("vector_dimension", data)
        self.assertEqual(data["vector_dimension"], 384)

    def test_search_valid_query(self):
        payload = {
            "query": "Chủ tịch Hội đồng Quản trị có quyền gì?",
            "top_k": 3,
            "min_score": 0.2
        }
        response = self.client.post("/api/v1/search", json=payload)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body.get("success"))
        self.assertGreater(body.get("total", 0), 0)
        self.assertLessEqual(len(body["data"]), 3)

        first_item = body["data"][0]
        self.assertIn("chunk_id", first_item)
        self.assertIn("score", first_item)
        self.assertIn("content", first_item)
        self.assertIn("metadata", first_item)
        self.assertGreaterEqual(first_item["score"], 0.2)
        self.assertIn("section_path", first_item["metadata"])

    def test_search_empty_query_returns_400(self):
        payload = {
            "query": "   ",
            "top_k": 3
        }
        response = self.client.post("/api/v1/search", json=payload)
        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertFalse(body.get("success"))
        self.assertIn("error", body)
        self.assertIn(body["error"]["code"], ["HTTP_400", "VALIDATION_ERROR"])

    def test_search_invalid_payload_validation(self):
        payload = {
            # missing query
            "top_k": -5
        }
        response = self.client.post("/api/v1/search", json=payload)
        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertFalse(body.get("success"))
        self.assertEqual(body["error"]["code"], "VALIDATION_ERROR")

if __name__ == "__main__":
    unittest.main()
