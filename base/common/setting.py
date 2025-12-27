from . import config

class Settings:
	def __init__(self):
		self.app_name: str = config.config.get("app", "name", fallback="AIPanelAdmin")
		self.debug: bool = config.config.getboolean("app", "debug", fallback=True)
		self.db_host: str = config.config.get("db", "host", fallback="127.0.0.1")
		self.db_name: str = config.config.get("db", "name", fallback="aipaneladmin")
		self.db_user: str = config.config.get("db", "user", fallback="admin")
		self.db_password: str = config.config.get("db", "password", fallback="123456")
		self.db_port: int = config.config.getint("db", "port", fallback=5432)

settings = Settings()