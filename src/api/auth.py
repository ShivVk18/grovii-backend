from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status
)

from sqlalchemy.orm import Session

from src.Schemas.auth_schema import (
    RegisterRequest,
    LoginRequest
)

from src.services.auth_service import (
    register_user,
    login_user
)

from src.database import get_db

from src.config.dependencies_config import get_current_user

router = APIRouter(
    prefix="/auth",
    tags=["Auth"]
)


@router.post("/register")
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


@router.post("/login")
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db)
):
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