import asyncio
import numpy as np
import jwt
from fastapi import HTTPException
from typing import Optional

SILENCE_THRESHOLD = 3  # Maximum consecutive silence prompts before ending call

EXPECTED_FRAME_SIZE = 256  # Adjust based on your model's requirements


SECRET_KEY = "your_secret_key"
ALGORITHM = "HS256"



def verify_jwt_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTError:
        raise HTTPException(status_code=403, detail="Could not validate credentials")


import bcrypt

def hash_password(password: str) -> str:
    """Hashes a password using bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, stored_password: str) -> bool:
    """Verifies a password against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), stored_password.encode('utf-8'))
    except ValueError:
        print("❌ Error: Stored password is not a valid bcrypt hash.")
        return False
