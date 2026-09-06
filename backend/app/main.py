from fastapi import FastAPI

from app.presentation.api.routers import asvs, greeting, health


def create_app() -> FastAPI:
    application = FastAPI(
        title="ASVS Requirement Search API",
        description="Search OWASP ASVS 5.0.0 in Japanese and English.",
        version="0.2.0",
    )
    application.include_router(asvs.router)
    application.include_router(greeting.router)
    application.include_router(health.router)
    return application


app = create_app()
