from typing import Annotated

from fastapi import APIRouter, Depends

from app.application.use_cases import CreateGreeting
from app.presentation.api.api_dependencies import get_create_greeting
from app.presentation.api.schemas.greeting_schema import GreetingResponse

router = APIRouter(tags=["greetings"])  # include_router()へのマッピング
GreetingUseCase = Annotated[CreateGreeting, Depends(get_create_greeting)]


@router.get("/", response_model=GreetingResponse)
async def root(use_case: GreetingUseCase) -> GreetingResponse:
    greeting = use_case.execute()
    return GreetingResponse.from_domain(greeting)


@router.get("/hello/{name}", response_model=GreetingResponse)
async def say_hello(name: str, use_case: GreetingUseCase) -> GreetingResponse:
    greeting = use_case.execute(name)
    return GreetingResponse.from_domain(greeting)
