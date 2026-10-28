"""Sign-up, sign-in and server-side sessions (Phase F)."""
import hashlib
import logging
from datetime import datetime, timedelta

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.api.errors import AppError
from src.config import security_settings as settings
from src.config.security_config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    csrf_token_for,
    hash_password,
    verify_password_or_dummy,
)
from src.models.sessions import UserSession
from src.models.users import User
from src.repositories.user_repository import get_user_by_email
from src.services.redis_service import redis_client

logger = logging.getLogger("grovii.auth")

GENERIC_LOGIN_ERROR = "Wrong email or password."
DUPLICATE_ACCOUNT = "An account with this email or username already exists. Try signing in."


def register_user(db: Session, username: str, email: str, password: str) -> User:
    if db.query(User.id).filter(or_(User.email == email, User.username == username)).first():
        raise AppError(409, "account_exists", DUPLICATE_ACCOUNT)
    user = User(username=username, email=email, hashed_password=hash_password(password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # Two sign-ups racing for the same email/username.
        db.rollback()
        raise AppError(409, "account_exists", DUPLICATE_ACCOUNT) from None
    db.refresh(user)
    return user


# ---------------------------------------------------------- login lockout ---

def _failures_key(email: str) -> str:
    return "grovii:loginfail:" + hashlib.sha256(email.strip().lower().encode()).hexdigest()[:32]


def _check_not_locked(email: str) -> None:
    try:
        key = _failures_key(email)
        count = int(redis_client.get(key) or 0)
        if count >= settings.LOGIN_MAX_FAILURES:
            ttl = int(redis_client.ttl(key))
            retry = ttl if ttl > 0 else settings.LOGIN_LOCK_SECONDS
            raise AppError(
                429, "login_locked",
                f"Too many wrong attempts. Try again in {max(1, retry // 60)} minute(s), or reset your password.",
                headers={"Retry-After": str(retry)}, retry_after=retry,
            )
    except AppError:
        raise
    except Exception as e:  # noqa: BLE001 - Redis down: the per-IP limit still applies
        logger.error("Login lockout check unavailable: %s", type(e).__name__)


def _record_failure(email: str) -> None:
    try:
        key = _failures_key(email)
        pipe = redis_client.pipeline()
        pipe.incr(key)
        pipe.expire(key, settings.LOGIN_LOCK_SECONDS)
        pipe.execute()
    except Exception as e:  # noqa: BLE001
        logger.error("Could not record failed login: %s", type(e).__name__)


def _clear_failures(email: str) -> None:
    try:
        redis_client.delete(_failures_key(email))
    except Exception:  # noqa: BLE001
        pass


# ---------------------------------------------------------------- sessions ---

def authenticate(db: Session, email: str, password: str) -> User:
    """The user for these credentials, or a generic 401 (same message and the
    same password-hashing work whether or not the email exists)."""
    _check_not_locked(email)
    user = get_user_by_email(db, email)
    ok = verify_password_or_dummy(password, user.hashed_password if user else None)
    if not user or not ok:
        _record_failure(email)
        raise AppError(401, "invalid_credentials", GENERIC_LOGIN_ERROR)
    _clear_failures(email)
    return user


def start_session(db: Session, user: User) -> tuple[str, str, int]:
    """Create a session row; return (token, csrf_token, max_age_seconds)."""
    max_age = ACCESS_TOKEN_EXPIRE_MINUTES * 60
    session = UserSession(user_id=user.id, expires_at=datetime.utcnow() + timedelta(seconds=max_age))
    db.add(session)
    db.commit()
    return create_access_token(str(user.id), session.id), csrf_token_for(session.id), max_age


def revoke_session(db: Session, session_id: str) -> None:
    db.query(UserSession).filter(UserSession.id == session_id, UserSession.revoked_at.is_(None)).update(
        {UserSession.revoked_at: datetime.utcnow()}, synchronize_session=False)
    db.commit()


def revoke_all_sessions(db: Session, user_id: str) -> int:
    n = db.query(UserSession).filter(UserSession.user_id == user_id, UserSession.revoked_at.is_(None)).update(
        {UserSession.revoked_at: datetime.utcnow()}, synchronize_session=False)
    db.commit()
    return n


# Kept for scripts that imported it; returns a session-bound token.
def login_user(db: Session, email: str, password: str) -> str:
    user = authenticate(db, email, password)
    token, _, _ = start_session(db, user)
    return token
