from app.domain.models import Greeting


class CreateGreeting:
    def execute(self, name: str | None = None) -> Greeting:
        return Greeting.for_name(name)
