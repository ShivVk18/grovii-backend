"""Consistent error responses.

Every error body has a human-readable string in `detail`, because the frontend
shows `detail` directly. Machine-readable extras sit next to it:

    {"detail": "You're out of credits.", "code": "insufficient_credits", ...}
    {"detail": "Idea must be at least 10 characters.", "code": "validation_error",
     "errors": {"idea": "Idea must be at least 10 characters."}}
"""
import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(self, status_code: int, code: str, message: str,
                 headers: dict[str, str] | None = None, **extra: Any):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.headers = headers
        self.extra = extra
        super().__init__(message)


def _field_message(error: dict) -> str:
    msg = str(error.get("msg", "Invalid value."))
    # Pydantic prefixes messages from custom validators with "Value error, ".
    if msg.startswith("Value error, "):
        msg = msg[len("Value error, "):]
    if error.get("type") == "missing":
        msg = "This field is required."
    elif error.get("type") == "extra_forbidden":
        msg = "This field can't be set."
    elif error.get("type") == "json_invalid":
        msg = "The request body is not valid JSON."
    return msg


def _field_name(error: dict) -> str:
    loc = [str(part) for part in error.get("loc", ()) if part not in ("body", "query", "path")]
    return ".".join(loc) or "body"


async def _app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message, "code": exc.code, **exc.extra},
        headers=exc.headers,
    )


async def _validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    errors: dict[str, str] = {}
    for err in exc.errors():
        errors.setdefault(_field_name(err), _field_message(err))
    return JSONResponse(
        status_code=422,
        content={"detail": " ".join(dict.fromkeys(errors.values())), "code": "validation_error", "errors": errors},
    )


logger = logging.getLogger("grovii.errors")


async def _unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
    # Full details go to the server log (type and place only, see
    # log_safety); the client gets a generic message, never a traceback.
    logger.error("Unhandled %s on %s %s", type(exc).__name__, request.method, request.url.path,
                 exc_info=(type(exc), exc, exc.__traceback__))
    return JSONResponse(
        status_code=500,
        content={"detail": "Something went wrong on our side. Please try again.", "code": "internal_error"},
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(Exception, _unhandled_handler)
    app.add_exception_handler(AppError, _app_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, _validation_handler)  # type: ignore[arg-type]
