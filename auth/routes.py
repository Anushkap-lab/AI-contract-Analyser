import os

from fastapi import APIRouter, Depends, File, HTTPException, Response, Request, UploadFile, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pymongo import MongoClient
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from .utils import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token
)
from .models import User # your DB session dependency
from motor.motor_asyncio import AsyncIOMotorClient

router = APIRouter(prefix="/auth", tags=["auth"])
bearer = HTTPBearer()

# ── Schemas ────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str = ""

class LoginRequest(BaseModel):
    email: str
    password: str
MONGO_URI                   = os.getenv("MONGO_URI")
DB_NAME                     = "AI_legal_analyser"  
sync_client      = MongoClient(MONGO_URI)
sync_db          = sync_client[DB_NAME]
users_collection = sync_db["users"]
chat_collection  = sync_db["chat_history"]

async_client = AsyncIOMotorClient(MONGO_URI)

def get_db():
    return async_client[DB_NAME]
# ── Register ───────────────────────────────────────────────
@router.post("/register", status_code=201)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(400, "Email already registered")

    if len(body.password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"message": "Account created successfully"}

# ── Login ──────────────────────────────────────────────────
@router.post("/login")
def login(body: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(401, "Invalid email or password")

    access_token  = create_access_token(user.id, user.email)
    refresh_token = create_refresh_token(user.id)

    # Refresh token in httpOnly cookie — JS can't read it (XSS safe)
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,       # HTTPS only in production
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {"id": user.id, "email": user.email, "full_name": user.full_name},
    }

# ── Refresh ────────────────────────────────────────────────
@router.post("/refresh")
def refresh(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(401, "No refresh token")

    payload = decode_token(token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(401, "Invalid refresh token")

    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(401, "User not found")

    return {"access_token": create_access_token(user.id, user.email)}

# ── Logout ─────────────────────────────────────────────────
@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("refresh_token")
    return {"message": "Logged out"}

# ── Get current user (dependency for protected routes) ─────
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db)
):
    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

# ── Me ─────────────────────────────────────────────────────
@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
    }
from auth.routes import get_current_user

@app.post("/api/analyse")
async def analyse(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)  # ← add this
):
    # current_user.id is available here — log which user uploaded what
    ...