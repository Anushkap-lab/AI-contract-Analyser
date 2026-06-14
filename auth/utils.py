from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
import os

SECRET_KEY    = os.getenv("KEY")   # set in .env — keep this secret!
ALGORITHM     = "HS256"
ACCESS_EXPIRE = 15          # minutes
REFRESH_EXPIRE = 60 * 24 * 7  # 7 days in minutes

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_ctx.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_ctx.verify(plain, hashed)

def create_token(data: dict, expires_minutes: int) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(minutes=expires_minutes)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def create_access_token(user_id: int, email: str) -> str:
    return create_token(
        {"sub": str(user_id), "email": email, "type": "access"},
        ACCESS_EXPIRE
    )

def create_refresh_token(user_id: int) -> str:
    return create_token(
        {"sub": str(user_id), "type": "refresh"},
        REFRESH_EXPIRE
    )

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None