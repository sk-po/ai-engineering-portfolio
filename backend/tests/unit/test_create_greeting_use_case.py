import unittest

from app.application.use_cases import CreateGreeting


class CreateGreetingTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.use_case = CreateGreeting()

    def test_creates_greeting_for_name(self) -> None:
        greeting = self.use_case.execute("world")

        self.assertEqual(greeting.message, "Hello, world!")

    def test_uses_world_for_blank_name(self) -> None:
        greeting = self.use_case.execute("  ")

        self.assertEqual(greeting.message, "Hello, World!")


if __name__ == "__main__":
    unittest.main()
