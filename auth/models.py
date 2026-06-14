
from datetime import datetime

def User(email: str, hashed_password: str, full_name: str = "") -> dict:
    return {
        "email":           email,
        "hashed_password": hashed_password,
        "full_name":       full_name,
        "created_at":      datetime.utcnow(),
    }
