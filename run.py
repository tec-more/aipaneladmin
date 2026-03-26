#!/usr/bin/env python3
"""
应用启动入口
"""

import sys
import io

# 设置标准输出为 UTF-8 编码（解决 Windows GBK 编码问题）
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

if __name__ == "__main__":
    import uvicorn
    PORT = 9998
    try:
        # 使用 import 字符串格式以支持 reload
        uvicorn.run(
            "base.app_wrapper:app",
            host="0.0.0.0",
            port=PORT,
            reload=True,
            access_log=True,  # 启用访问日志
            log_level="info"   # 设置日志级别
        )
    except Exception as e:
        print(f"\n[ERROR] 启动失败: {e}")
