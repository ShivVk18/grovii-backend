"""Auth request bodies. Unknown fields are refused (no mass assignment of
credits, plan, verification flags, etc.)."""
import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict, EmailStr, ValidationInfo, field_validator

PASSWORD_MIN = 10
PASSWORD_MAX_BYTES = 72  # bcrypt ignores anything past 72 bytes
PASSWORD_MIN_DISTINCT = 5
USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,30}$")

_COMMON = {
    w.strip().lower()
    for w in (Path(__file__).resolve().parent.parent / "config" / "data" / "common_passwords.txt").read_text().split()
    if w.strip()
}


def password_problem(password: str, *, email: str = "", username: str = "") -> str | None:
    """Plain-language reason a new password is too weak, or None if it's fine.

    Follows NIST SP 800-63B: length over composition rules, block common and
    context-specific passwords, no forced symbols.
    """
    if len(password) < PASSWORD_MIN:
        return f"Password must be at least {PASSWORD_MIN} characters."
    if len(password.encode("utf-8")) > PASSWORD_MAX_BYTES:
        return f"Password must be at most {PASSWORD_MAX_BYTES} bytes (about {PASSWORD_MAX_BYTES} letters)."
    if len(set(password)) < PASSWORD_MIN_DISTINCT:
        return "Password is too simple. Use a mix of different characters or a few random words."
    lowered = password.lower()
    core = re.sub(r"[^a-z]", "", lowered)
    if lowered in _COMMON or core in _COMMON:
        return "That password is too common. Pick something harder to guess."
    for part in (email.split("@")[0].lower() if email else "", username.lower()):
        if len(part) >= 4 and part in lowered:
            return "Password must not contain your email name or username."
    return None


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str
    email: EmailStr
    password: str

    @field_validator("username")
    @classmethod
    def _username(cls, v: str) -> str:
        v = v.strip()
        if not USERNAME_RE.match(v):
            raise ValueError("Username must be 3-30 letters, numbers, dots, dashes or underscores.")
        return v

    @field_validator("password")
    @classmethod
    def _password(cls, v: str, info: ValidationInfo) -> str:
        # username and email are declared first, so they're validated already.
        problem = password_problem(v, email=str(info.data.get("email") or ""), username=info.data.get("username") or "")
        if problem:
            raise ValueError(problem)
        return v


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    # No strength rules at login (older accounts), only a sane size limit.
    password: str

    @field_validator("password")
    @classmethod
    def _size(cls, v: str) -> str:
        if len(v) > 1024:
            raise ValueError("Password is too long.")
        return v


class ChangePasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _new(cls, v: str) -> str:
        # Email/username checks need the user; the route runs them too.
        problem = password_problem(v)
        if problem:
            raise ValueError(problem)
        return v


class UpdateProfileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str

    @field_validator("username")
    @classmethod
    def _username(cls, v: str) -> str:
        v = v.strip()
        if not USERNAME_RE.match(v):
            raise ValueError("Username must be 3-30 letters, numbers, dots, dashes or underscores.")
        return v


class DeleteAccountRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    password: str


class AuthResponse(BaseModel):
    """Kept for reference: login no longer returns the token in the body."""
    message: str = "Signed in"
