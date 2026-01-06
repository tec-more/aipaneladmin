#!/usr/bin/env python3
"""
应用启动入口
"""

import uvicorn
from base.start import init_app

# 创建FastAPI应用实例
app = init_app()

if __name__ == "__main__":
    # 启动应用
    uvicorn.run("run:app", host="0.0.0.0", port=9999, reload=True)
