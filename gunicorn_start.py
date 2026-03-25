#!/usr/bin/env python3
"""
生产环境Gunicorn配置文件
使用方法: gunicorn gunicorn_start:app -c gunicorn_config.py
"""
import multiprocessing
import os
from base.start import init_app

# 创建FastAPI应用实例
app = init_app()

# Gunicorn配置
bind = "0.0.0.0:9998"
workers = multiprocessing.cpu_count() * 2 + 1  # 根据CPU核心数自动计算
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000

# 进程管理
max_requests = 1000  # 每个worker处理1000个请求后重启，防止内存泄漏
max_requests_jitter = 100  # 随机抖动，避免所有worker同时重启

# 超时配置
timeout = 120
keepalive = 5

# 日志配置
accesslog = "/var/log/aipaneladmin/access.log"
errorlog = "/var/log/aipaneladmin/error.log"
loglevel = "info"

# 安全配置
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190

# 预加载应用（减少内存占用，但热重载会失效）
preload_app = True

# 进程名称
proc_name = "aipaneladmin"

# 守护进程（生产环境True，开发环境False）
daemon = False

# PID文件
pidfile = "/var/run/aipaneladmin.pid"

# 启用时清除环境（避免传递不必要的环境变量）
clear_untrusted_env_headers = True
