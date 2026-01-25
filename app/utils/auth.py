from jose import jwt 
from fastapi import Header ,HTTPException 
import os 

CLERK_JWT_PUBLIC_KEY = os.getenv("CLERK_JWT_PUBLIC_KEY")

def verify_clerk_token(authorization:str = Header(...)):
    if not (authorization.startswith('Bearer ')):
        raise HTTPException(status_code=401,detail="Missing Token")
    token = authorization.split(' ')[1]
    try:
        decoded = jwt.decode(token,CLERK_JWT_PUBLIC_KEY,algorithms=["RS256"])
        return decoded
    except Exception:
        raise HTTPException(status_code=401,detail="Invalid or expired token")