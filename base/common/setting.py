from . import config
import os
import typing
from pydantic_settings import BaseSettings
from typing import Any, List, Optional, Literal
from pathlib import Path


def get_enabled_plugins() -> List[str]:
	"""
	从各插件的 manifest.json 读取已安装且激活的插件列表
	用于在 ORM 配置阶段确定要加载哪些插件模型
	"""
	import json
	plugins_dir = Path(__file__).parent.parent / "plugins"
	exclude_dirs = {"__pycache__", ".git"}

	enabled_plugins = []
	if plugins_dir.exists() and plugins_dir.is_dir():
		for plugin in plugins_dir.iterdir():
			if plugin.is_dir() and not plugin.name.startswith("_") and plugin.name not in exclude_dirs:
				manifest_file = plugin / "manifest.json"
				if manifest_file.exists():
					try:
						with open(manifest_file, "r", encoding="utf-8") as f:
							manifest = json.load(f)
							if manifest.get("is_installed") and manifest.get("is_enabled"):
								enabled_plugins.append(plugin.name)
					except Exception:
						pass

	return enabled_plugins


def get_plugin_models_from_manifest(plugin_name: str) -> List[str]:
	"""
	从插件的 manifest.json 读取模型列表
	"""
	import json
	plugins_dir = Path(__file__).parent.parent / "plugins"
	manifest_file = plugins_dir / plugin_name / "manifest.json"

	models = []
	if manifest_file.exists():
		try:
			with open(manifest_file, "r", encoding="utf-8") as f:
				manifest = json.load(f)
				# 从 manifest 中读取 models 字段
				model_files = manifest.get("models", [])
				for model_file in model_files:
					# model_file 格式: "greeting" 或 "models/greeting"
					if "/" in model_file:
						model_path = model_file.replace("/", ".")
					else:
						model_path = f"models.{model_file}"
					models.append(f"base.plugins.{plugin_name}.{model_path}")
		except Exception:
			pass

	return models


def get_model_list() -> List[str]:
	"""
	获取所有需要加载的模型列表
	- 核心模块的模型总是加载
	- 插件模型只有在已安装且激活时才加载（从 manifest.json 读取模型声明）
	"""
	plugin_models = []
	core_models = []

	# 加载核心模块的模型
	core_dir = Path(__file__).parent.parent / "core"
	if core_dir.exists() and core_dir.is_dir():
		for core_module in core_dir.iterdir():
			models_path = core_module / "models"
			if models_path.exists() and models_path.is_dir():
				for model_file in models_path.glob("*.py"):
					if model_file.name != "__init__.py":
						relative_model = f"base.core.{core_module.name}.models.{model_file.stem}"
						core_models.append(relative_model)

	# 只加载已安装且激活的插件模型
	enabled_plugins = get_enabled_plugins()
	for plugin_name in enabled_plugins:
		models = get_plugin_models_from_manifest(plugin_name)
		plugin_models.extend(models)

	model_list = core_models + plugin_models + ['aerich.models']
	return model_list

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
	# Redis配置
	REDIS_ENABLED: bool = config.config.getboolean("redis", "enabled", fallback=False)
	REDIS_HOST: str = config.config.get("redis", "host", fallback="127.0.0.1")
	REDIS_PORT: int = config.config.getint("redis", "port", fallback=6379)
	REDIS_PASSWORD: str = config.config.get("redis", "password", fallback="")
	REDIS_DB: int = config.config.getint("redis", "db", fallback=0)
	# 项目根目录
	base_path: Path = Path(__file__).parent.parent.parent
	LOG_DIR: str = config.config.get("log", "path", fallback=str(base_path / "logs"))
	# ================================================= #
	# ******************** 跨域配置 ******************** #
	# ================================================= #
	CORS_ORIGIN_ENABLE: bool = True    # 是否启用跨域
	# ALLOW_ORIGINS: List[str] = ["*"]   # 允许的域名列表
	ALLOW_ORIGINS: List[str] = [
		'http://0.0.0.0:9999',
		'http://0.0.0.0:8000',
		'http://localhost:3000',
		'http://127.0.0.1:3000',
		'http://localhost:9999',
		'http://127.0.0.1:9999',
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
					"ssl": False,  # Disable SSL
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
                "models": get_model_list(),
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

	# ================================================= #
	# ******************* 邮件服务配置 ******************* #
	# ================================================= #
	EMAIL_ENABLED: bool = config.config.getboolean("email", "enabled", fallback=True)
	SMTP_HOST: str = config.config.get("email", "smtp_host", fallback="smtp.qq.com")
	SMTP_PORT: int = config.config.getint("email", "smtp_port", fallback=587)
	SMTP_USE_TLS: bool = config.config.getboolean("email", "smtp_use_tls", fallback=True)
	SENDER_EMAIL: str = config.config.get("email", "sender_email", fallback="")
	SENDER_PASSWORD: str = config.config.get("email", "sender_password", fallback="")
	SENDER_NAME: str = config.config.get("email", "sender_name", fallback="AIPanelAdmin")


settings = Settings()