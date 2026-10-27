from fastapi import (
    Depends,
    HTTPException
)
from fastapi.security import HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.users import User
from src.config.security_config import decode_access_token

security = HTTPBearer()

def get_current_user(
    credentials=Depends(security),
    db: Session = Depends(get_db)
):
    token = credentials.credentials

    try:
        payload = decode_access_token(token)

        user_id_str = payload.get("sub")

        if user_id_str is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            )

    except (JWTError, ValueError):
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )

    user = (
        db.query(User)
        .filter(User.id == user_id_str)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found"
        )

    return user