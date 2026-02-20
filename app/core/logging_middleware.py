import time
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger("app.access")


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        client_host = request.client.host if request.client else "unknown"
        method = request.method
        path = request.url.path
        query_params = str(request.query_params) if request.query_params else ""
        
        user_id = None
        if hasattr(request.state, "user_id"):
            user_id = request.state.user_id
        
        logger.info(
            f"{method} {path}",
            extra={
                "method": method,
                "path": path,
                "query_params": query_params,
                "client_host": client_host,
                "user_id": str(user_id) if user_id else None
            }
        )
        
        try:
            response = await call_next(request)
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"Error processing {method} {path}",
                extra={
                    "method": method,
                    "path": path,
                    "duration": duration,
                    "error": str(e),
                    "user_id": str(user_id) if user_id else None
                },
                exc_info=True
            )
            raise
        
        duration = time.time() - start_time
        status_code = response.status_code
        
        logger.info(
            f"{method} {path} - {status_code}",
            extra={
                "method": method,
                "path": path,
                "status_code": status_code,
                "duration": duration,
                "client_host": client_host,
                "user_id": str(user_id) if user_id else None
            }
        )
        
        return response
