from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Greeting:
    message: str

    @classmethod
    def for_name(cls, name: str | None = None) -> "Greeting":
        normalized_name = (name or "").strip() or "World"
        return cls(message=f"Hello, {normalized_name}!")
