from . import config
import os
import typing
from pydantic_settings import BaseSettings
from typing import Any, List, Optional, Literal
from pathlib import Path

class Settings(BaseSettings):
	
	app_name: str = config.config.get("app", "name", fallback="AIPanelAdmin")
	app_description: str = config.config.get("app", "description", fallback="AIPanelAdmin API Documentation")
	app_version: str = config.config.get("app", "version", fallback="0.1.0")
	debug: bool = config.config.getboolean("app", "debug", fallback=True)
	db_host: str = config.config.get("db", "host", fallback="127.0.0.1")
	db_name: str = config.config.get("db", "name", fallback="aipaneladmin")
	db_user: str = config.config.get("db", "user", fallback="admin")
	db_password: str = config.config.get("db", "password", fallback="123456")
	db_port: int = config.config.getint("db", "port", fallback=5432)
	# 项目根目录
	base_path = Path(__file__).parent.parent.parent
	LOG_DIR = config.config.get("log", "path", fallback=str(base_path / "logs"))
	# ================================================= #
	# ******************** 跨域配置 ******************** #
	# ================================================= #
	CORS_ORIGIN_ENABLE: bool = True    # 是否启用跨域
	# ALLOW_ORIGINS: List[str] = ["*"]   # 允许的域名列表
	ALLOW_ORIGINS: List[str] = [
		'http://0.0.0.0:9999',
		'http://0.0.0.0:8000',
	]   # 允许的域名列表
	ALLOW_METHODS: List[str] = ["*"]   # 允许的HTTP方法
	ALLOW_HEADERS: List[str] = ["*"]   # 允许的请求头
	ALLOW_CREDENTIALS: bool = True     # 是否允许携带cookie
	CORS_EXPOSE_HEADERS: list[str] = ['X-Request-ID']	
	# ================================================= #	
	TORTOISE_ORM: dict = {
		"connections": {
			# SQLite configuration
			# "sqlite": {
			#     "engine": "tortoise.backends.sqlite",
			#     "credentials": {"file_path": f"{BASE_DIR}/db.sqlite3"},  # Path to SQLite database file
			# },
			# MySQL/MariaDB configuration
			# Install with: tortoise-orm[asyncmy]
			# "mysql": {
			#     "engine": "tortoise.backends.mysql",
			#     "credentials": {
			#         "host": "localhost",  # Database host address
			#         "port": 3306,  # Database port
			#         "user": "yourusername",  # Database username
			#         "password": "yourpassword",  # Database password
			#         "database": "yourdatabase",  # Database name
			#     },
			# },
			# PostgreSQL configuration
			# Install with: tortoise-orm[asyncpg]
			"postgres": {
				"engine": "tortoise.backends.asyncpg",
				"credentials": {
					"host": db_host,  # Database host address
					"port": db_port,  # Database port
					"user": db_user,  # Database username
					"password": db_password,  # Database password
					"database": db_name,  # Database name
				},
			},
			# MSSQL/Oracle configuration
			# Install with: tortoise-orm[asyncodbc]
			# "oracle": {
			#     "engine": "tortoise.backends.asyncodbc",
			#     "credentials": {
			#         "host": "localhost",  # Database host address
			#         "port": 1433,  # Database port
			#         "user": "yourusername",  # Database username
			#         "password": "yourpassword",  # Database password
			#         "database": "yourdatabase",  # Database name
			#     },
			# },
			# SQLServer configuration
			# Install with: tortoise-orm[asyncodbc]
			# "sqlserver": {
			#     "engine": "tortoise.backends.asyncodbc",
			#     "credentials": {
			#         "host": "localhost",  # Database host address
			#         "port": 1433,  # Database port
			#         "user": "yourusername",  # Database username
			#         "password": "yourpassword",  # Database password
			#         "database": "yourdatabase",  # Database name
			#     },
			# },
		},
		"apps": {
            "models": {
                "models": ["base.models.users","aerich.models"],
                "default_connection": "postgres",
            },
        },
		"use_tz": False,  # Whether to use timezone-aware datetimes
		"timezone": "Asia/Shanghai",  # Timezone setting
	}

	DATETIME_FORMAT: str = "%Y-%m-%d %H:%M:%S"
	OPERATION_LOG_RECORD: bool = True
	# ================================================= #
	# ******************* Gzip压缩配置 ******************* #
	# ================================================= #
	GZIP_ENABLE: bool = True        # 是否启用Gzip
	GZIP_MIN_SIZE: int = 1000       # 最小压缩大小(字节)
	GZIP_COMPRESS_LEVEL: int = 9    # 压缩级别(1-9)


settings = Settings()