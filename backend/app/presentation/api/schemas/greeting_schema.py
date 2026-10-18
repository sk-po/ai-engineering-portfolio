from pydantic import BaseModel

from app.domain.models import Greeting


class GreetingResponse(BaseModel):
    message: str

    @classmethod
    def from_domain(cls, greeting: Greeting) -> "GreetingResponse":
        return cls(message=greeting.message)
