import os
import jwt
import logging
import time
from typing import Dict, Optional, Tuple
from fastapi import HTTPException, Header, Request
from pydantic import BaseModel
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("auth")

# Supabase JWT configuration
JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")

# SECURITY WARNING: The following logging exposes sensitive information
# TODO: Remove these debug logs before production deployment
logger.warning("🚨 SECURITY WARNING: Debug logging enabled - JWT secrets will be logged!")
logger.info(f"🔐 JWT_SECRET loaded: {JWT_SECRET[:10]}...{JWT_SECRET[-10:] if JWT_SECRET and len(JWT_SECRET) > 20 else 'NONE'}")
logger.info(f"🔐 JWT_SECRET length: {len(JWT_SECRET) if JWT_SECRET else 0}")
logger.info(f"🔐 JWT_SECRET type: {type(JWT_SECRET)}")
logger.info(f"🔐 JWT_SECRET repr: {repr(JWT_SECRET[:50]) if JWT_SECRET else 'None'}")

# Log current system time for clock skew detection
current_time = time.time()
current_datetime = datetime.utcfromtimestamp(current_time)
logger.info(f"⏰ Container system time: {current_time} ({current_datetime} UTC)")


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
    # SECURITY WARNING: Logging token details for debugging
    logger.info(f"🔍 Attempting to decode JWT token")
    logger.info(f"🔍 Token length: {len(token)}")
    logger.info(f"🔍 Token preview: {token[:50]}...{token[-20:] if len(token) > 70 else token}")
    
    # Check if JWT_SECRET is available
    if not JWT_SECRET:
        logger.error("❌ JWT_SECRET is not set or empty!")
        raise AuthError("JWT secret not configured")
    
    try:
        # First, decode without verification to inspect the token
        logger.info("🔍 Decoding token header and payload without verification...")
        unverified_header = jwt.get_unverified_header(token)
        unverified_payload = jwt.decode(token, options={"verify_signature": False})
        
        # SECURITY WARNING: Logging unverified token contents
        logger.info(f"🔍 Unverified header: {unverified_header}")
        logger.info(f"🔍 Unverified payload: {unverified_payload}")
        
        # Check timing claims
        current_time = time.time()
        if 'exp' in unverified_payload:
            exp_time = unverified_payload['exp']
            exp_datetime = datetime.utcfromtimestamp(exp_time)
            time_until_exp = exp_time - current_time
            logger.info(f"⏰ Token exp: {exp_time} ({exp_datetime} UTC)")
            logger.info(f"⏰ Current time: {current_time}")
            logger.info(f"⏰ Time until expiration: {time_until_exp} seconds")
            
            if time_until_exp < 0:
                logger.error(f"❌ Token is expired by {abs(time_until_exp)} seconds")
            elif time_until_exp < 300:  # Less than 5 minutes
                logger.warning(f"⚠️ Token expires soon: {time_until_exp} seconds")
        
        if 'iat' in unverified_payload:
            iat_time = unverified_payload['iat']
            iat_datetime = datetime.utcfromtimestamp(iat_time)
            time_since_issued = current_time - iat_time
            logger.info(f"⏰ Token iat: {iat_time} ({iat_datetime} UTC)")
            logger.info(f"⏰ Time since issued: {time_since_issued} seconds")
        
        # Now attempt verified decode
        logger.info("🔍 Attempting verified decode...")
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_signature": True}
        )
        
        logger.info("✅ JWT token successfully decoded and verified")
        logger.info(f"✅ Verified payload: {payload}")
        return payload
        
    except jwt.ExpiredSignatureError as e:
        logger.error(f"❌ JWT ExpiredSignatureError: {str(e)}")
        logger.error(f"❌ Exception details: {repr(e)}")
        raise AuthError("Token has expired")
    except jwt.InvalidSignatureError as e:
        logger.error(f"❌ JWT InvalidSignatureError: {str(e)}")
        logger.error(f"❌ Exception details: {repr(e)}")
        logger.error("❌ This usually means the JWT_SECRET is incorrect")
        raise AuthError("Invalid token signature")
    except jwt.DecodeError as e:
        logger.error(f"❌ JWT DecodeError: {str(e)}")
        logger.error(f"❌ Exception details: {repr(e)}")
        logger.error("❌ This usually means the token format is invalid")
        raise AuthError("Invalid token format")
    except jwt.InvalidTokenError as e:
        logger.error(f"❌ JWT InvalidTokenError: {str(e)}")
        logger.error(f"❌ Exception type: {type(e).__name__}")
        logger.error(f"❌ Exception details: {repr(e)}")
        logger.error(f"❌ Exception args: {e.args}")
        raise AuthError("Invalid token")
    except Exception as e:
        logger.error(f"❌ Unexpected JWT decode error: {str(e)}")
        logger.error(f"❌ Exception type: {type(e).__name__}")
        logger.error(f"❌ Exception details: {repr(e)}")
        logger.error(f"❌ Exception args: {getattr(e, 'args', 'No args')}")
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
    logger.info(f"🔍 Extracting auth token from header")
    logger.info(f"🔍 Authorization header: {authorization[:50] if authorization else 'None'}...")
    
    if not authorization:
        logger.error("❌ Authorization header missing")
        raise HTTPException(status_code=401, detail="Authorization header missing")
        
    parts = authorization.split()
    logger.info(f"🔍 Authorization parts count: {len(parts)}")
    logger.info(f"🔍 Authorization parts: {parts}")
    
    if len(parts) != 2 or parts[0].lower() != "bearer":
        logger.error(f"❌ Invalid authorization header format: {parts}")
        raise HTTPException(status_code=401, detail="Invalid authorization header format")
        
    token = parts[1]
    logger.info(f"✅ Successfully extracted token from header")
    return token


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
    logger.info(f"🔍 Validating token...")
    
    try:
        payload = decode_jwt(token)
        
        # Check if token has expired (additional check)
        current_time = time.time()
        if "exp" in payload and payload["exp"] < current_time:
            exp_datetime = datetime.utcfromtimestamp(payload["exp"])
            logger.error(f"❌ Token has expired: {exp_datetime} UTC")
            raise HTTPException(status_code=401, detail="Token has expired")
            
        # Get user ID from subject claim
        user_id = payload.get("sub")
        if not user_id:
            logger.error(f"❌ User ID not found in token payload: {payload}")
            raise HTTPException(status_code=401, detail="User ID not found in token")
            
        logger.info(f"✅ Token validation successful for user: {user_id}")
        return user_id, payload
        
    except AuthError as e:
        logger.error(f"❌ AuthError during token validation: {e.message}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"❌ Unexpected error during token validation: {str(e)}")
        logger.error(f"❌ Exception type: {type(e).__name__}")
        logger.error(f"❌ Exception details: {repr(e)}")
        raise HTTPException(status_code=500, detail=f"Authentication error: {str(e)}")


async def get_user_id(request: Request) -> str:
    """
    Extract and validate user ID from request.
    
    Args:
        request: FastAPI request object
        
    Returns:
        User ID
    """
    logger.info(f"🔍 Getting user ID from request")
    authorization = request.headers.get("Authorization")
    token = get_auth_token(authorization)
    user_id, _ = validate_token(token)
    logger.info(f"✅ Successfully got user ID: {user_id}")
    return user_id