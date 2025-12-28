from fastapi import FastAPI
from starlette.types import ASGIApp
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from .setting import settings

class CustomCORSMiddleware(CORSMiddleware):
    """CORS跨域中间件"""
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(
            app,
            allow_origins=settings.ALLOW_ORIGINS,
            allow_methods=settings.ALLOW_METHODS,
            allow_headers=settings.ALLOW_HEADERS,
            allow_credentials=settings.ALLOW_CREDENTIALS,
            expose_headers=settings.CORS_EXPOSE_HEADERS,
        )
def register_middlewares(app: FastAPI):
	"""注册中间件"""
	app.add_middleware(CustomCORSMiddleware)