import json

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from src.api.errors import AppError
from src.config import security_settings as settings
from src.config.dependencies_config import get_current_user
from src.config.security_config import verify_password
from src.database import get_db
from src.models.users import User
from src.Schemas.auth_schema import (
    ChangePasswordRequest,
    DeleteAccountRequest,
    LoginRequest,
    RegisterRequest,
    UpdateProfileRequest,
)
from src.services import account_service, auth_service
from src.services.rate_limit import limit_login_ip, limit_register_ip

router = APIRouter(prefix="/auth", tags=["Auth"])


def _set_session_cookies(response: Response, token: str, csrf: str, max_age: int) -> None:
    secure = settings.cookie_secure()
    # The session itself: never readable by page scripts.
    response.set_cookie(settings.cookie_name(settings.SESSION_COOKIE), token, max_age=max_age, path="/",
                        secure=secure, httponly=True, samesite="lax")
    # The CSRF token: the frontend reads it and echoes it in X-CSRF-Token.
    response.set_cookie(settings.cookie_name(settings.CSRF_COOKIE), csrf, max_age=max_age, path="/",
                        secure=secure, httponly=False, samesite="lax")


def _clear_session_cookies(response: Response) -> None:
    for base in (settings.SESSION_COOKIE, settings.CSRF_COOKIE):
        response.delete_cookie(settings.cookie_name(base), path="/", secure=settings.cookie_secure(), samesite="lax")


@router.post("/register", dependencies=[Depends(limit_register_ip)])
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    user = auth_service.register_user(db=db, username=payload.username, email=payload.email, password=payload.password)
    return {"message": "User registered", "user_id": str(user.id)}


@router.post("/login", dependencies=[Depends(limit_login_ip)])
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = auth_service.authenticate(db, payload.email, payload.password)
    token, csrf, max_age = auth_service.start_session(db, user)
    _set_session_cookies(response, token, csrf, max_age)
    # No token in the body: page scripts must not be able to read it.
    return {"message": "Signed in"}


def _me(user) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "username": user.username,
        "credits": user.credits,
        "plan": user.plan,
        "avatar_url": user.avatar_url,
    }


@router.get("/me")
def me(current_user=Depends(get_current_user)):
    return _me(current_user)


@router.patch("/me")
def update_me(payload: UpdateProfileRequest, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return _me(auth_service.update_username(db, current_user.id, payload.username))


@router.post("/change-password")
def change_password(payload: ChangePasswordRequest, request: Request, db: Session = Depends(get_db),
                    current_user=Depends(get_current_user)):
    auth_service.change_password(db, current_user.id, request.state.session_id,
                                 payload.current_password, payload.new_password)
    return {"message": "Password changed. Other devices were signed out."}


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db),
           current_user=Depends(get_current_user)):
    auth_service.revoke_session(db, request.state.session_id)
    _clear_session_cookies(response)
    return {"message": "Logout successful"}


@router.post("/logout-all")
def logout_all(response: Response, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    n = auth_service.revoke_all_sessions(db, current_user.id)
    _clear_session_cookies(response)
    return {"message": f"Signed out of {n} session(s)."}


@router.get("/me/export")
def export_my_data(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    data = account_service.export_user_data(db, current_user.id)
    return Response(
        content=json.dumps(data, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="grovii-my-data.json"', "Cache-Control": "no-store"},
    )


@router.delete("/me")
def delete_my_account(payload: DeleteAccountRequest, response: Response, db: Session = Depends(get_db),
                      current_user=Depends(get_current_user)):
    # Re-check the password: a stolen open session alone can't delete the account.
    hashed = db.query(User.hashed_password).filter(User.id == current_user.id).scalar()
    if not hashed or not verify_password(payload.password, hashed):
        raise AppError(403, "wrong_password", "That password is wrong. Your account was not deleted.")
    account_service.delete_user_data(db, current_user.id)
    _clear_session_cookies(response)
    return {"message": "Your account and all your data were deleted."}
