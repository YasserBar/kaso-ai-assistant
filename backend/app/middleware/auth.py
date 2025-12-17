"""
API Key Authentication Middleware
=================================
Protects API endpoints with secret key authentication
"""

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import settings


class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    Middleware to validate API key for protected endpoints
    
    The API key should be sent in the header:
    - Header name: X-API-Key
    - Header value: <your-secret-key>
    
    Public endpoints (no auth required):
    - / (root)
    - /health
    - /docs
    - /redoc
    - /openapi.json
    """
    
    # Endpoints that don't require authentication
    PUBLIC_PATHS = {
        "/",
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
    }
    
    async def dispatch(self, request: Request, call_next):
        """
        Process incoming requests and enforce API key authentication for non-public paths.

        Flow:
        - Skip authentication for PUBLIC_PATHS (e.g., '/', '/health', docs) and for CORS preflight (OPTIONS).
        - Read the API key from the 'X-API-Key' request header.
        - Return 401 (Unauthorized) if the header is missing.
        - Return 403 (Forbidden) if the key does not match settings.api_secret_key.
        - On success, delegate to downstream handlers and return their response.

        Security:
        - Compares against settings.api_secret_key sourced from environment/.env.
        - Does not log or expose secret values.
        """
        # Skip auth for public paths (root, health, docs) to allow unauthenticated access
        if request.url.path in self.PUBLIC_PATHS:
            return await call_next(request)
        
        # Skip auth for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # Get API key from header
        api_key = request.headers.get("X-API-Key")
        
        # Validate API key
        if not api_key:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "detail": "Missing API key. Please provide X-API-Key header.",
                    "code": "MISSING_API_KEY"
                }
            )
        
        if api_key != settings.api_secret_key:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "detail": "Invalid API key.",
                    "code": "INVALID_API_KEY"
                }
            )
        
        # API key is valid, proceed with request
        response = await call_next(request)
        return response


def get_api_key_header(request: Request) -> str:
    """
    Dependency to extract and validate API key
    Use this in route dependencies if you need access to the key
    """
    api_key = request.headers.get("X-API-Key")
    if not api_key or api_key != settings.api_secret_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing API key"
        )
    return api_key
