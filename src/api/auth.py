from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.config import limits
from src.config.dependencies_config import get_current_user
from src.database import get_db
from src.Schemas.auth_schema import LoginRequest, RegisterRequest
from src.services.auth_service import login_user, register_user
from src.services.rate_limit import enforce, limit_login_ip, limit_register_ip

router = APIRouter(
    prefix="/auth",
    tags=["Auth"]
)


@router.post("/register", dependencies=[Depends(limit_register_ip)])
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db)
):
    try:
        user = register_user(
            db=db,
            username=payload.username,
            email=payload.email,
            password=payload.password
        )

        return {
            "message": "User registered",
            "user_id": str(user.id)
        }

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )


@router.post("/login", dependencies=[Depends(limit_login_ip)])
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db)
):
    # Per-account limit slows password guessing spread across many IPs.
    enforce("login_email", payload.email, limits.RATE_LOGIN_PER_EMAIL)
    try:
        token = login_user(
            db=db,
            email=payload.email,
            password=payload.password
        )

        return {
            "access_token": token,
            "token_type": "bearer"
        }

    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=str(e)
        )


@router.get("/me")
def me(
    current_user=Depends(
        get_current_user
    )
):
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "username": current_user.username,
        "credits": current_user.credits,
        "plan": current_user.plan,
        "avatar_url": current_user.avatar_url
    }


@router.post("/logout")
def logout():
    return {
        "message": "Logout successful"
    }