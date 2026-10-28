from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from src.config.security_config import decode_access_token
from src.database import get_db
from src.models.users import User

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

    # Give the connection back to the pool now. FastAPI runs this dependency
    # and the route handler as two separate thread-pool steps; holding the
    # connection in between let all threads wait for connections while all
    # connections waited for threads (HTTP 500 after DB_POOL_TIMEOUT under
    # load). The user is detached with its columns loaded; handlers use its
    # plain attributes (id, email, ...), and queries they run re-open a
    # connection inside their own thread step.
    if user is not None:
        db.expunge(user)
    db.rollback()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found"
        )

    return user