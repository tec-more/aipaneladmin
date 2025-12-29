from fastapi import APIRouter, Body, Depends, Path
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/v1/users", tags=["用户管理"])

@router.get("/test", summary="获取用户信息", response_class=JSONResponse)
async def get_user_info():
	return JSONResponse(content={"user_id": 1, "username": "testuser"})