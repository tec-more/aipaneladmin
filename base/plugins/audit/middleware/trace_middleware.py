from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from base.common.context import (
    set_trace_id,
    clear_trace_id,
    set_user_context,
    clear_user_context,
    current_user_id,
    current_username
)
from base.plugins.audit.services.audit_service import generate_trace_id
from base.common.setting import settings


ENABLED = True
PRIORITY = 10


def is_trace_enabled() -> bool:
    return getattr(settings, 'TRACE_ENABLED', True)


class TraceMiddleware(BaseHTTPMiddleware):
    """全链路追踪中间件"""

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.exclude_paths = [
            "/health",
            "/docs",
            "/openapi.json",
            "/redoc",
            "/static",
            "/favicon.ico",
        ]

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not is_trace_enabled():
            return await call_next(request)

        path = request.url.path
        if any(path.startswith(exclude) for exclude in self.exclude_paths):
            return await call_next(request)

        trace_id = request.headers.get("X-Trace-ID", generate_trace_id())
        set_trace_id(trace_id)
        request.state.trace_id = trace_id

        try:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                from base.common.security import decode_access_token
                token_data = decode_access_token(auth_header[7:])
                if token_data:
                    uid = token_data.get("sub")
                    uname = token_data.get("username")
                    if uid:
                        set_user_context(int(uid), uname)
                        request.state.user_id = int(uid)
                        request.state.username = uname

            response = await call_next(request)
            response.headers["X-Trace-ID"] = trace_id
            return response

        finally:
            clear_trace_id()
            clear_user_context()