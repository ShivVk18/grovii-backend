"""Who is calling.

Two ways to authenticate, both naming a server-side session:

* Browser: the httpOnly session cookie (set at login). Writes (POST, PATCH,
  PUT, DELETE) must also send the CSRF header, and their Origin, if present,
  must be an allowed origin.
* API clients and tests: `Authorization: Bearer <token>`. No CSRF header is
  needed: another website can't make a browser attach this header.
"""
from datetime import datetime

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWTError as JWTError
from sqlalchemy.orm import Session

from src.api.errors import AppError
from src.config import security_settings as settings
from src.config.security_config import csrf_matches, decode_access_token
from src.database import get_db
from src.models.sessions import UserSession
from src.models.users import User

security = HTTPBearer(auto_error=False)

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _unauthorized(message: str = "Please sign in again.") -> AppError:
    return AppError(401, "not_authenticated", message, headers={"WWW-Authenticate": "Bearer"})


def origin_allowed(request: Request) -> bool:
    origin = request.headers.get("origin")
    if not origin:
        return True  # same-origin requests and non-browser clients may omit it
    return origin.rstrip("/") in settings.CORS_ORIGINS


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
):
    from_cookie = False
    token = credentials.credentials if credentials else None
    if not token:
        token = request.cookies.get(settings.cookie_name(settings.SESSION_COOKIE))
        from_cookie = token is not None
    if not token:
        raise _unauthorized("Please sign in.")

    try:
        payload = decode_access_token(token)
    except (JWTError, ValueError):
        raise _unauthorized()
    user_id, session_id = payload.get("sub"), payload.get("sid")
    if not user_id or not session_id:
        raise _unauthorized()  # tokens from before Phase F carry no session

    if from_cookie and request.method in UNSAFE_METHODS:
        if not origin_allowed(request):
            raise AppError(403, "origin_not_allowed", "This request came from a site that isn't allowed.")
        if not csrf_matches(session_id, request.headers.get(settings.CSRF_HEADER)):
            raise AppError(403, "csrf_failed", "Your session check failed. Refresh the page and try again.")

    row = (
        db.query(User, UserSession)
        .join(UserSession, UserSession.user_id == User.id)
        .filter(UserSession.id == session_id, User.id == user_id)
        .first()
    )
    user = row[0] if row else None
    session = row[1] if row else None

    # Give the connection back to the pool now. FastAPI runs this dependency
    # and the route handler as two separate thread-pool steps; holding the
    # connection in between let all threads wait for connections while all
    # connections waited for threads (HTTP 500 after DB_POOL_TIMEOUT under
    # load). The user is detached with its columns loaded; handlers use its
    # plain attributes (id, email, ...), and queries they run re-open a
    # connection inside their own thread step.
    if user is not None:
        db.expunge(user)
    if session is not None:
        db.expunge(session)
    db.rollback()

    if user is None or session is None:
        raise _unauthorized()
    if session.revoked_at is not None or session.expires_at <= datetime.utcnow():
        raise _unauthorized("Your session expired. Please sign in again.")

    request.state.session_id = session_id
    return user
