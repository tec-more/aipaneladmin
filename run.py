#!/usr/bin/env python3
"""
应用启动入口
"""

import sys
import io
import psutil

# 设置标准输出为 UTF-8 编码（解决 Windows GBK 编码问题）
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import uvicorn
from base.start import init_app

# 创建FastAPI应用实例
app = init_app()


if __name__ == "__main__":
    PORT = 9998
    # 如果主端口被占用，尝试备用端口
    try:
        uvicorn.run(app, host="0.0.0.0", port=PORT)
    except Exception as e:
        print(f"\n[ERROR] 启动失败: {e}")
