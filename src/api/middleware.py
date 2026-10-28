"""HTTP-level protections (Phase F), written as plain ASGI middleware so they
also cover streamed bodies and every route, including ones added later."""
import json

from src.config import security_settings as settings

UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}
DOC_PATHS = {"/docs", "/redoc", "/openapi.json", "/docs/oauth2-redirect"}

# API responses are JSON only: nothing should run, embed or be framed.
BASE_HEADERS = [
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"referrer-policy", b"no-referrer"),
    (b"content-security-policy", b"default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"),
    (b"cross-origin-resource-policy", b"same-site"),
    (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"),
]
# The interactive docs (dev only) need scripts and styles from a CDN.
DOCS_CSP = (b"content-security-policy",
            b"default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            b"style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data: https://fastapi.tiangolo.com; "
            b"frame-ancestors 'none'")


async def _json(send, status: int, code: str, detail: str):
    body = json.dumps({"detail": detail, "code": code}).encode()
    headers = [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode()), *BASE_HEADERS]
    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": body})


class SecurityMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        path = scope.get("path", "")
        method = scope.get("method", "GET")
        headers = {k.decode().lower(): v.decode("latin-1") for k, v in scope.get("headers", [])}
        is_docs = path in DOC_PATHS

        if is_docs and settings.IS_PRODUCTION:
            return await _json(send, 404, "not_found", "Not Found")

        # Writes from a browser on another site are refused, signed in or not
        # (covers login CSRF). Browsers always send Origin on cross-site POSTs.
        origin = headers.get("origin")
        if method in UNSAFE and origin and origin.rstrip("/") not in settings.CORS_ORIGINS:
            return await _json(send, 403, "origin_not_allowed", "This request came from a site that isn't allowed.")

        limit = settings.MAX_BODY_BYTES
        declared = headers.get("content-length")
        if declared and declared.isdigit() and int(declared) > limit:
            return await _json(send, 413, "body_too_large", "That request is too large.")

        received = 0
        too_large = False

        async def limited_receive():
            nonlocal received, too_large
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    too_large = True
                    # Stop reading; the app sees an empty final chunk.
                    return {"type": "http.request", "body": b"", "more_body": False}
            return message

        started = False

        async def secure_send(message):
            nonlocal started
            if message["type"] == "http.response.start":
                if too_large:
                    return
                started = True
                extra = list(BASE_HEADERS)
                if is_docs:
                    extra = [h for h in extra if h[0] != b"content-security-policy"] + [DOCS_CSP]
                if settings.IS_PRODUCTION:
                    extra.append((b"strict-transport-security", settings.HSTS_VALUE.encode()))
                existing = {k.lower() for k, _ in message.get("headers", [])}
                message["headers"] = list(message.get("headers", [])) + [h for h in extra if h[0] not in existing]
            elif message["type"] == "http.response.body" and too_large:
                return
            await send(message)

        await self.app(scope, limited_receive, secure_send)
        if too_large and not started:
            await _json(send, 413, "body_too_large", "That request is too large.")
