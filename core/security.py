import jwt
import logging
from datetime import datetime, timedelta, timezone
from fastapi import Request, HTTPException, Security
from fastapi.security import APIKeyCookie
from slowapi import Limiter
from slowapi.util import get_remote_address
from core.config import SECRET_KEY

logger = logging.getLogger("venueiq")

# Rate Limiter
limiter = Limiter(key_func=get_remote_address)

# Security Headers Middleware
async def add_security_headers(request: Request, call_next):
    """Add comprehensive security headers to every HTTP response."""
    try:
        response = await call_next(request)
    except Exception as exc:
        logger.error("Unhandled middleware error: %s", exc, exc_info=True)
        raise
    response.headers["X-Content-Type-Options"]  = "nosniff"
    response.headers["X-Frame-Options"]         = "DENY"
    response.headers["X-XSS-Protection"]        = "1; mode=block"
    response.headers["Referrer-Policy"]         = "strict-origin-when-cross-origin"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://maps.googleapis.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https://*.googleapis.com https://*.gstatic.com; "
        "frame-src https://www.google.com; "
        "connect-src 'self'"
    )
    return response

# JWT Setup
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120

cookie_scheme = APIKeyCookie(name="access_token", auto_error=False)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Security(cookie_scheme)):
    """Dependency to check the JWT token from the cookie."""
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
