import unittest

from fastapi.testclient import TestClient

from app.main import app


class ApiTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def test_root_returns_hello_world(self) -> None:
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "Hello, World!"})

    def test_say_hello_uses_name(self) -> None:
        response = self.client.get("/hello/FDE")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "Hello, FDE!"})

    def test_health_returns_ok(self) -> None:
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_searches_asvs_requirements_in_japanese(self) -> None:
        response = self.client.post(
            "/api/v1/requirements/search",
            json={"query": "パスワードの安全な保存", "level": 2, "limit": 3},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["query"], "パスワードの安全な保存")
        self.assertLessEqual(len(body["results"]), 3)
        self.assertGreater(len(body["results"]), 0)
        self.assertEqual(body["results"][0]["requirement_id"], "V11.4.2")
        self.assertTrue(body["results"][0]["description_ja"])
        self.assertIn("邦訳ドラフト", body["translation_notice"])

    def test_finds_an_exact_requirement_id(self) -> None:
        response = self.client.post(
            "/api/v1/requirements/search",
            json={"query": "V6.1.1", "level": None, "limit": 1},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"][0]["requirement_id"], "V6.1.1")

    def test_rejects_a_blank_search_query(self) -> None:
        response = self.client.post(
            "/api/v1/requirements/search",
            json={"query": "  "},
        )

        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
