from typing import Optional
from uuid import UUID
from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from app.core.security import verify_token


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/health") or request.url.path.startswith("/docs") or request.url.path.startswith("/openapi.json"):
            return await call_next(request)
        
        authorization = request.headers.get("Authorization")
        if authorization and authorization.startswith("Bearer "):
            token = authorization.split(" ")[1]
            payload = verify_token(token)
            if payload:
                user_id_str = payload.get("sub")
                if user_id_str:
                    try:
                        user_id = UUID(user_id_str) if isinstance(user_id_str, str) else user_id_str
                        request.state.user_id = user_id
                    except (ValueError, TypeError):
                        pass
        
        response = await call_next(request)
        return response
