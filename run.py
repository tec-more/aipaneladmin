#!/usr/bin/env python3
"""
应用启动入口
"""

import sys
import io
import os

# 设置标准输出为 UTF-8 编码（解决 Windows GBK 编码问题）
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

if __name__ == "__main__":
    import uvicorn
    # 从环境变量获取端口，默认9998
    PORT = int(os.environ.get("UVICORN_PORT", "9998"))
    
    # 从环境变量获取配置，或使用默认值
    # Windows 上多 worker 有 socket 继承问题，默认使用单 worker
    import platform
    default_workers = 1 if platform.system() == "Windows" else 2
    WORKERS = int(os.environ.get("UVICORN_WORKERS", str(default_workers)))
    RELOAD = os.environ.get("UVICORN_RELOAD", "false").lower() == "true"  # 生产环境默认关闭reload
    LIMIT_CONCURRENCY = int(os.environ.get("UVICORN_LIMIT_CONCURRENCY", "200"))
    TIMEOUT_KEEP_ALIVE = int(os.environ.get("UVICORN_TIMEOUT_KEEP_ALIVE", "5"))
    
    # 注意：reload 模式下 worker 必须为1，所以如果设置了reload则强制worker=1
    if RELOAD:
        WORKERS = 1
    
    try:
        print("=" * 70, flush=True)
        print("🚀 AI Panel Admin 服务器启动中...", flush=True)
        print("=" * 70, flush=True)
        print(f"📡 服务地址: http://0.0.0.0:{PORT}", flush=True)
        print(f"📡 本地访问: http://127.0.0.1:{PORT}", flush=True)
        print(f"👷 Worker 数量: {WORKERS}", flush=True)
        print(f"🔄 热重载: {'开启' if RELOAD else '关闭'}", flush=True)
        print(f"📊 并发限制: {LIMIT_CONCURRENCY}", flush=True)
        print(f"⏱️  保持连接超时: {TIMEOUT_KEEP_ALIVE}秒", flush=True)
        print("=" * 70, flush=True)
        
        # 使用 import 字符串格式以支持 reload
        uvicorn.run(
            "base.app_wrapper:app",
            host="0.0.0.0",
            port=PORT,
            workers=WORKERS,
            reload=RELOAD,
            access_log=True,  # 启用访问日志
            log_level="info",  # 设置日志级别
            limit_concurrency=LIMIT_CONCURRENCY,  # 限制并发连接数
            timeout_keep_alive=TIMEOUT_KEEP_ALIVE,  # 保持连接超时
            backlog=128,  # Windows 上需要较小的 backlog 值
        )
    except Exception as e:
        print(f"\n[ERROR] 启动失败: {e}")
        import traceback
        traceback.print_exc()
