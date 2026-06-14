import os
import asyncio
from fastapi import APIRouter, Depends, File, HTTPException, Response, Request, UploadFile, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pymongo import MongoClient
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr
from .utils import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token
)
from bson import ObjectId
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


# ── MongoDB Configuration ─────────────────────────────────
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = "AI_legal_analyser"
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
users_collection = db["users"]
chat_collection = db["chat_history"]





# ── Register ───────────────────────────────────────────────
@router.post("/register", status_code=201)
def register(body: RegisterRequest):

    existing_user = users_collection.find_one(
        {"email": body.email}
    )

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    if len(body.password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters"
        )

    user = {
        "email": body.email,
        "hashed_password": hash_password(body.password),
        "full_name": body.full_name,
    }

    result = users_collection.insert_one(user)

    return {
        "message": "Account created successfully",
        "user_id": str(result.inserted_id)
    }

# ── Login ──────────────────────────────────────────────────
@router.post("/login")
def login(body: LoginRequest, response: Response):

    user = users_collection.find_one(
        {"email": body.email}
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    if not verify_password(
        body.password,
        user["hashed_password"]
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    access_token = create_access_token(
        str(user["_id"]),
        user["email"]
    )

    refresh_token = create_refresh_token(
        str(user["_id"])
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(user["_id"]),
            "email": user["email"],
            "full_name": user["full_name"]
        }
    }


# ── Refresh ────────────────────────────────────────────────
@router.post("/refresh")
def refresh(request: Request):
    token = request.cookies.get("refresh_token")

    if not token:
        raise HTTPException(401, "No refresh token")

    payload = decode_token(token)

    if not payload or payload.get("type") != "refresh":
        raise HTTPException(401, "Invalid refresh token")

    user = users_collection.find_one(
        {"_id": ObjectId(payload["sub"])}
    )

    if not user:
        raise HTTPException(401, "User not found")

    return {
        "access_token": create_access_token(
            str(user["_id"]),
            user["email"]
        )
    }


# ── Logout ─────────────────────────────────────────────────
@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("refresh_token")
    return {"message": "Logged out"}


# ── Get current user (dependency for protected routes) ─────
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer)
):
    payload = decode_token(credentials.credentials)

    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=401,
            detail="Invalid token type"
        )

    user = users_collection.find_one(
        {"_id": ObjectId(payload["sub"])}
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found"
        )

    return user

# ── Me ─────────────────────────────────────────────────────
@router.get("/me")
def me(current_user=Depends(get_current_user)):
    return {
        "id": str(current_user["_id"]),
        "email": current_user["email"],
        "full_name": current_user["full_name"],
    } 








































