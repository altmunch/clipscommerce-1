"""
Rate limiting configuration and utilities
"""

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, HTTPException, status
from functools import wraps
import logging

logger = logging.getLogger(__name__)

# Create rate limiter instance
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["1000/day", "200/hour"]
)

# Custom rate limit exceeded handler
def custom_rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Custom handler for rate limit exceeded"""
    logger.warning(f"Rate limit exceeded for {get_remote_address(request)}: {exc.detail}")
    
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail={
            "error": "Rate limit exceeded",
            "message": f"Too many requests. Limit: {exc.detail}",
            "retry_after": exc.retry_after
        }
    )

# Rate limiting decorators for different endpoints
def auth_rate_limit(request: Request):
    """Rate limiting for authentication endpoints"""
    return f"{get_remote_address(request)}"

def api_rate_limit(request: Request):
    """Rate limiting for general API endpoints"""
    return f"{get_remote_address(request)}"

def user_rate_limit(request: Request):
    """Rate limiting per authenticated user"""
    # Try to get user ID from request if available
    if hasattr(request.state, 'user_id'):
        return f"user:{request.state.user_id}"
    return f"{get_remote_address(request)}"

# Rate limit configurations
RATE_LIMITS = {
    "auth_login": "5/minute",        # 5 login attempts per minute
    "auth_register": "3/minute",     # 3 registrations per minute
    "password_reset": "3/hour",      # 3 password resets per hour
    "api_general": "60/minute",      # 60 API calls per minute
    "scraping": "10/hour",           # 10 scraping jobs per hour
    "video_generation": "5/hour",    # 5 video generations per hour
}