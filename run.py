#!/usr/bin/env python3
"""
应用启动入口
"""

import sys
import io

# 设置标准输出为 UTF-8 编码（解决 Windows GBK 编码问题）
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import uvicorn
from base.start import init_app

# 创建FastAPI应用实例
app = init_app()

if __name__ == "__main__":
    # 启动应用
    uvicorn.run("run:app", host="0.0.0.0", port=9999, reload=True)
