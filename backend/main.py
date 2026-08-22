from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel


class MessageResponse(BaseModel):
    message: str


class HealthResponse(BaseModel):
    status: Literal["ok"]


app = FastAPI(
    title="FDE Portfolio API",
    description="Hello World API for the FDE portfolio.",
    version="0.1.0",
)


@app.get("/", response_model=MessageResponse)
async def root() -> MessageResponse:
    return MessageResponse(message="Hello World from FastAPI!")


@app.get("/hello/{name}", response_model=MessageResponse)
async def say_hello(name: str) -> MessageResponse:
    return MessageResponse(message=f"Hello, {name}!")


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")
