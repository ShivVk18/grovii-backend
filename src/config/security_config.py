import bcrypt
from jose import jwt
from datetime import datetime, timedelta, timezone

SECRET_KEY = "shivansh"
ALGORITHM = "HS256"

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )

def create_access_token(user_id: str):
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=7)
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )
