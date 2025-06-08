"""
Authentication module for TxAgent - DEPRECATED

This module is deprecated in favor of the centralized auth_service.
It's kept for backward compatibility but all new code should use:

from core.auth_service import auth_service, get_auth_token, validate_token, get_user_id

This will be removed in a future version.
"""

import warnings
from .core.auth_service import (
    auth_service,
    get_auth_token,
    validate_token,
    get_user_id,
    AuthError,
    JWTPayload
)

# Issue deprecation warning
warnings.warn(
    "auth.py is deprecated. Use 'from core.auth_service import auth_service' instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export everything for backward compatibility
__all__ = [
    'auth_service',
    'get_auth_token', 
    'validate_token',
    'get_user_id',
    'AuthError',
    'JWTPayload'
]