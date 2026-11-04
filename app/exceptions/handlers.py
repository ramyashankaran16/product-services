
import logging
from datetime import datetime, timezone
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.exceptions.errors import AppError

logger = logging.getLogger(__name__)

# Internal parameter names that should be shown to clients under their public name.
_FIELD_ALIASES = {"product_id": "id"}
_LOCATION_PREFIXES = {"body", "query", "path", "header"}


def build_error_body(
    status_code: int, message: str, path: str, details: list[dict[str, str]] | None = None
) -> dict[str, Any]:
    return {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": status_code,
        "error": HTTPStatus(status_code).phrase,
        "message": message,
        "path": path,
        "details": details or [],
    }


def _error_response(
    request: Request,
    status_code: int,
    message: str,
    details: list[dict[str, str]] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    body = build_error_body(status_code, message, request.url.path, details)
    return JSONResponse(status_code=status_code, content=body, headers=headers)


def _field_name(loc: tuple[Any, ...]) -> str:
    parts = [str(p) for p in loc if p not in _LOCATION_PREFIXES]
    name = ".".join(parts) or "body"
    return _FIELD_ALIASES.get(name, name)


def _issue(error: dict[str, Any]) -> str:
    error_type = error.get("type", "")
    if error_type == "missing":
        return "is required"
    if error_type == "extra_forbidden":
        return "is not allowed (unknown or server-managed field)"
    if error.get("input", ...) is None and error_type.endswith("_type"):
        return "must not be null"
    if error_type == "uuid_parsing":
        return "must be a valid UUID"
    return str(error.get("msg", "is invalid")).removeprefix("Value error, ")


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    logger.warning("%s %s rejected: %s", request.method, request.url.path, exc.message)
    return _error_response(request, exc.status_code, exc.message, exc.details)


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    if any(e.get("type") == "json_invalid" for e in errors):
        details = [{"field": "body", "issue": "request body is not valid JSON"}]
        return _error_response(request, 400, "Malformed JSON request body", details)

    details = [{"field": _field_name(e.get("loc", ())), "issue": _issue(e)} for e in errors]
    logger.info("Validation failed for %s %s: %s", request.method, request.url.path, details)
    return _error_response(request, 400, "Validation failed", details)


async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handles framework-level errors such as unknown routes (404) and wrong methods (405)."""
    if exc.status_code == 404:
        message = "Resource not found"
    elif exc.status_code == 405:
        message = f"Method {request.method} is not allowed on this path"
    else:
        message = str(exc.detail)
    return _error_response(request, exc.status_code, message, headers=exc.headers)


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    # Full details go to the log only; the client gets a generic message.
    logger.exception("Unhandled error while processing %s %s", request.method, request.url.path)
    return _error_response(request, 500, "An unexpected error occurred. Please try again later.")


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)
