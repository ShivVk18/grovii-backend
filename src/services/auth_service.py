from sqlalchemy.orm import Session
from src.models.users import User

from src.repositories.user_repository import (
    get_user_by_email,
    create_user
)

from src.config.security_config import (
    hash_password,
    verify_password,
    create_access_token
)


def register_user(
    db: Session,
    username: str,
    email: str,
    password: str
):
    existing = get_user_by_email(
        db,
        email
    )

    if existing:
        raise Exception("User already exists")

    user = User(
        username=username,
        email=email,
        hashed_password=hash_password(password)
    )

    return create_user(
        db,
        user
    )


def login_user(db: Session, email: str, password: str):
    user = get_user_by_email(
        db,
        email
    )

    if not user:
        raise Exception("Invalid credentials")

    if not verify_password(password, user.hashed_password):
        raise Exception("Invalid credentials")

    token = create_access_token(str(user.id))

    return token
