import os
from fastapi import FastAPI
from base.common import database
from base.common.config import config
from base.common.setting import settings
def init_app() -> FastAPI:
	app = FastAPI(title="My FastAPI Application")
	@app.get("/")
	async def read_root():
		c = database.getapp()
		b = {"Hello": "World"}
		d = {"database": config["app"]["name"]}
		e = {"settings": settings.db_port}
		return b | c | d | e
	return app