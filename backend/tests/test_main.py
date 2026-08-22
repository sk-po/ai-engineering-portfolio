import asyncio
import unittest

from main import health, root, say_hello


class MainTestCase(unittest.TestCase):
    def test_root_returns_hello_world(self) -> None:
        response = asyncio.run(root())

        self.assertEqual(response.message, "Hello World from FastAPI!")

    def test_say_hello_uses_name(self) -> None:
        response = asyncio.run(say_hello("FDE"))

        self.assertEqual(response.message, "Hello, FDE!")

    def test_health_returns_ok(self) -> None:
        response = asyncio.run(health())

        self.assertEqual(response.status, "ok")


if __name__ == "__main__":
    unittest.main()
