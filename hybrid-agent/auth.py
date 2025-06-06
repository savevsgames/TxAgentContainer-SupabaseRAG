import os
import jwt
import logging
import time
from typing import Dict, Optional, Tuple
from fastapi import HTTPException, Header, Request
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("auth")

# Supabase JWT configuration
JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")

class AuthError(Exception):
    """Custom exception for authentication errors."""
    
    def __init__(self, message: str, status_code: int = 401):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class JWTPayload(BaseModel):
    """Model for JWT payload."""
    
    sub: str  # user_id
    email: Optional[str] = None
    role: str = "authenticated"
    exp: int


def decode_jwt(token: str) -> Dict:
    """
    Decode and validate a JWT token.
    
    Args:
        token: JWT token
        
    Returns:
        Decoded JWT payload
        
    Raises:
        AuthError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_signature": True}
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthError("Token has expired")
    except jwt.InvalidTokenError:
        raise AuthError("Invalid token")
    except Exception as e:
        logger.error(f"JWT decode error: {str(e)}")
        raise AuthError(f"Failed to decode token: {str(e)}")


def get_auth_token(authorization: Optional[str] = Header(None)) -> str:
    """
    Extract JWT token from Authorization header.
    
    Args:
        authorization: Authorization header
        
    Returns:
        JWT token
        
    Raises:
        HTTPException: If token is missing or invalid
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
        
    parts = authorization.split()
    
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid authorization header format")
        
    return parts[1]


def validate_token(token: str) -> Tuple[str, Dict]:
    """
    Validate JWT token and extract user ID.
    
    Args:
        token: JWT token
        
    Returns:
        Tuple of (user_id, payload)
        
    Raises:
        HTTPException: If token is invalid or user ID is missing
    """
    try:
        payload = decode_jwt(token)
        
        # Check if token has expired
        if "exp" in payload and payload["exp"] < time.time():
            raise HTTPException(status_code=401, detail="Token has expired")
            
        # Get user ID from subject claim
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in token")
            
        return user_id, payload
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Token validation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Authentication error: {str(e)}")


async def get_user_id(request: Request) -> str:
    """
    Extract and validate user ID from request.
    
    Args:
        request: FastAPI request object
        
    Returns:
        User ID
    """
    authorization = request.headers.get("Authorization")
    token = get_auth_token(authorization)
    user_id, _ = validate_token(token)
    return user_id