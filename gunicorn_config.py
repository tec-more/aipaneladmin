#!/usr/bin/env python3
"""
Gunicorn配置文件
使用方法: gunicorn gunicorn_start:app -c gunicorn_config.py
"""
import multiprocessing
import os

# 绑定地址
bind = "0.0.0.0:9998"

# Worker进程数（公式：CPU核心数 * 2 + 1）
workers = multiprocessing.cpu_count() * 2 + 1

# Worker类型（使用Uvicorn支持异步）
worker_class = "uvicorn.workers.UvicornWorker"

# 每个worker的并发连接数
worker_connections = 1000

# 最大请求数（防止内存泄漏）
max_requests = 1000
max_requests_jitter = 100

# 超时配置
timeout = 120
keepalive = 5

# 日志配置
accesslog = "-"  # 输出到stdout，配合systemd使用
errorlog = "-"
loglevel = "info"

# 进程名称
proc_name = "aipaneladmin"

# 安全限制
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190

# 预加载应用
preload_app = True

# 守护进程（systemd管理时设为False）
daemon = False

# PID文件
pidfile = "/var/run/aipaneladmin.pid"

# 工作目录（如果需要）
# chdir = "/path/to/aipaneladmin"
