
from fastapi import FastAPI , APIRouter

api_router = APIRouter()

def register_routers(app: FastAPI, prefix: str = "/api"):
    app.include_router(api_router, prefix=prefix)