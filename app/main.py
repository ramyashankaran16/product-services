
from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.v1.products import router as products_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.middleware import request_logging_middleware
from app.exceptions.handlers import register_exception_handlers


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="Product Service",
        version="1.0.0",
        description="Manages products for the online store (Microservices Task 1).",
    )
    app.middleware("http")(request_logging_middleware)
    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(products_router)
    return app


app = create_app()
