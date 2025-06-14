"""
Centralized authentication service for TxAgent.

This module provides a unified authentication service that handles:
- JWT token validation and parsing
- Supabase client management with proper authentication
- User context extraction and management
- RLS-compliant database operations

Based on the consolidated migration schema in 20250608104059_warm_silence.sql
"""

import os
import jwt
import logging
import time
from typing import Dict, Optional, Tuple, Any
from fastapi import HTTPException, Header, Request
from pydantic import BaseModel
from dotenv import load_dotenv
from datetime import datetime
from supabase import create_client, Client

from .logging import request_logger
from .exceptions import StorageError

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger("auth_service")

# Supabase configuration from environment
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")

# Validate required environment variables
if not all([SUPABASE_URL, SUPABASE_ANON_KEY, JWT_SECRET]):
    raise ValueError("Missing required Supabase environment variables")

logger.info(f"🔍 AUTH_SERVICE: Initialized with URL: {SUPABASE_URL}")
logger.info(f"🔍 AUTH_SERVICE: JWT_SECRET available: {bool(JWT_SECRET)}")


class AuthError(Exception):
    """Custom exception for authentication errors."""
    
    def __init__(self, message: str, status_code: int = 401):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class JWTPayload(BaseModel):
    """Model for JWT payload based on Supabase auth structure."""
    
    sub: str  # user_id - MUST match user_id in database tables
    email: Optional[str] = None
    role: str = "authenticated"  # REQUIRED for RLS policies
    aud: str = "authenticated"  # REQUIRED for RLS policies
    exp: int  # Token expiration
    iat: Optional[int] = None  # Token issued at


class AuthService:
    """
    Centralized authentication service for TxAgent.
    
    This service handles all authentication operations including:
    - JWT token validation
    - Supabase client creation with proper auth context
    - User context management for RLS compliance
    """
    
    def __init__(self):
        """Initialize the authentication service."""
        # Create base Supabase clients
        self.anon_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        self.service_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY) if SUPABASE_SERVICE_ROLE_KEY else None
        
        logger.info("✅ AUTH_SERVICE: Authentication service initialized")
    
    def decode_jwt(self, token: str) -> Dict[str, Any]:
        """
        Decode and validate a JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            Decoded JWT payload
            
        Raises:
            AuthError: If token is invalid or expired
        """
        logger.info(f"🔍 DECODE_JWT: Starting JWT validation")
        logger.info(f"🔍 DECODE_JWT: Token length: {len(token)}")
        
        if not JWT_SECRET:
            logger.error("❌ DECODE_JWT: JWT_SECRET not configured")
            raise AuthError("JWT secret not configured")
        
        try:
            # First, decode without verification for inspection
            unverified_payload = jwt.decode(token, options={"verify_signature": False})
            logger.info(f"🔍 DECODE_JWT: Token payload preview: {list(unverified_payload.keys())}")
            
            # Check timing
            current_time = time.time()
            if 'exp' in unverified_payload:
                exp_time = unverified_payload['exp']
                time_until_exp = exp_time - current_time
                logger.info(f"⏰ DECODE_JWT: Time until expiration: {time_until_exp} seconds")
                
                if time_until_exp < 0:
                    logger.error(f"❌ DECODE_JWT: Token expired {abs(time_until_exp)} seconds ago")
            
            # Verify token with full validation
            logger.info("🔍 DECODE_JWT: Performing verified decode")
            payload = jwt.decode(
                token,
                JWT_SECRET,
                algorithms=["HS256"],
                audience=["authenticated"],  # Required for Supabase RLS
                options={"verify_signature": True}
            )
            
            logger.info("✅ DECODE_JWT: Token validation successful")
            logger.info(f"✅ DECODE_JWT: User ID: {payload.get('sub')}")
            return payload
            
        except jwt.ExpiredSignatureError as e:
            logger.error(f"❌ DECODE_JWT: Token expired: {str(e)}")
            raise AuthError("Token has expired")
        except jwt.InvalidAudienceError as e:
            logger.error(f"❌ DECODE_JWT: Invalid audience: {str(e)}")
            raise AuthError("Invalid token audience")
        except jwt.InvalidSignatureError as e:
            logger.error(f"❌ DECODE_JWT: Invalid signature: {str(e)}")
            raise AuthError("Invalid token signature")
        except jwt.DecodeError as e:
            logger.error(f"❌ DECODE_JWT: Decode error: {str(e)}")
            raise AuthError("Invalid token format")
        except Exception as e:
            logger.error(f"❌ DECODE_JWT: Unexpected error: {str(e)}")
            raise AuthError(f"Token validation failed: {str(e)}")
    
    def extract_token_from_header(self, authorization: Optional[str] = None) -> str:
        """
        Extract JWT token from Authorization header.
        
        Args:
            authorization: Authorization header value
            
        Returns:
            JWT token string
            
        Raises:
            HTTPException: If token is missing or invalid format
        """
        logger.info(f"🔍 EXTRACT_TOKEN: Processing authorization header")
        
        if not authorization:
            logger.error("❌ EXTRACT_TOKEN: Authorization header missing")
            raise HTTPException(status_code=401, detail="Authorization header missing")
            
        parts = authorization.split()
        logger.info(f"🔍 EXTRACT_TOKEN: Header parts count: {len(parts)}")
        
        if len(parts) != 2 or parts[0].lower() != "bearer":
            logger.error(f"❌ EXTRACT_TOKEN: Invalid header format: {parts}")
            raise HTTPException(status_code=401, detail="Invalid authorization header format")
            
        token = parts[1]
        logger.info(f"✅ EXTRACT_TOKEN: Successfully extracted token")
        return token
    
    def validate_token_and_get_user(self, token: str) -> Tuple[str, Dict[str, Any]]:
        """
        Validate JWT token and extract user information.
        
        Args:
            token: JWT token string
            
        Returns:
            Tuple of (user_id, payload)
            
        Raises:
            HTTPException: If token is invalid or user ID missing
        """
        logger.info(f"🔍 VALIDATE_TOKEN: Starting token validation")
        
        try:
            payload = self.decode_jwt(token)
            
            # Extract user ID from subject claim
            user_id = payload.get("sub")
            if not user_id:
                logger.error(f"❌ VALIDATE_TOKEN: User ID not found in token")
                raise HTTPException(status_code=401, detail="User ID not found in token")
            
            # Validate required claims for RLS
            if payload.get("aud") != "authenticated":
                logger.error(f"❌ VALIDATE_TOKEN: Invalid audience: {payload.get('aud')}")
                raise HTTPException(status_code=401, detail="Invalid token audience")
            
            if payload.get("role") != "authenticated":
                logger.error(f"❌ VALIDATE_TOKEN: Invalid role: {payload.get('role')}")
                raise HTTPException(status_code=401, detail="Invalid token role")
            
            logger.info(f"✅ VALIDATE_TOKEN: Token validation successful for user: {user_id}")
            return user_id, payload
            
        except AuthError as e:
            logger.error(f"❌ VALIDATE_TOKEN: AuthError: {e.message}")
            raise HTTPException(status_code=e.status_code, detail=e.message)
        except Exception as e:
            logger.error(f"❌ VALIDATE_TOKEN: Unexpected error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Authentication error: {str(e)}")
    

    def get_authenticated_client(self, jwt_token: Optional[str] = None) -> Client:
        """
        Get a Supabase client with JWT token injected.
        """
        logger.info(f"🔍 GET_CLIENT: Creating Supabase client with JWT: {bool(jwt_token)}")

        try:
            client: Client = create_client(SUPABASE_URL, jwt_token or SUPABASE_ANON_KEY)
            
            # Headers are set internally by supabase-py, but this is safe if needed
            client.postgrest.session.headers.update({
                "Authorization": f"Bearer {jwt_token if jwt_token else SUPABASE_ANON_KEY}",
                "apikey": SUPABASE_ANON_KEY
            })

            logger.info(f"✅ GET_CLIENT: {'Authenticated' if jwt_token else 'Anonymous'} client created")
            return client

        except Exception as e:
            logger.error(f"❌ GET_CLIENT: Error creating client: {str(e)}")
            raise StorageError(f"Failed to create Supabase client: {str(e)}")
        
        
    async def get_user_from_request(self, request: Request) -> str:
        """
        Extract and validate user ID from FastAPI request.
        
        Args:
            request: FastAPI request object
            
        Returns:
            User ID string
        """
        logger.info(f"🔍 GET_USER_FROM_REQUEST: Processing request")
        
        authorization = request.headers.get("Authorization")
        token = self.extract_token_from_header(authorization)
        user_id, _ = self.validate_token_and_get_user(token)
        
        logger.info(f"✅ GET_USER_FROM_REQUEST: Successfully extracted user: {user_id}")
        return user_id
    
    def log_auth_event(self, event_type: str, user_context: Dict[str, Any] = None, 
                      success: bool = True, details: Dict[str, Any] = None):
        """
        Log authentication events with proper context.
        
        Args:
            event_type: Type of auth event
            user_context: User context from JWT payload
            success: Whether the event was successful
            details: Additional event details
        """
        request_logger.log_auth_event(
            event_type=event_type,
            user_context=user_context,
            success=success,
            details=details
        )


# Global authentication service instance
auth_service = AuthService()


# Convenience functions for backward compatibility
def get_auth_token(authorization: Optional[str] = Header(None)) -> str:
    """Extract JWT token from Authorization header."""
    return auth_service.extract_token_from_header(authorization)


def validate_token(token: str) -> Tuple[str, Dict[str, Any]]:
    """Validate JWT token and extract user ID."""
    return auth_service.validate_token_and_get_user(token)


async def get_user_id(request: Request) -> str:
    """Extract and validate user ID from request."""
    return await auth_service.get_user_from_request(request)