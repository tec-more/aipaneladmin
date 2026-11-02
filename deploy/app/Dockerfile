# aipaneladmin 应用镜像（docker-compose 部署形态）
# 构建上下文为项目根目录：docker build -f deploy/app/Dockerfile -t aipanel-app .
#
# 注意：requirements.txt 若含 torch 等重型依赖，构建较慢且镜像较大；
# 生产可按需裁剪为 requirements-prod.txt（本文件不代裁，避免改变依赖契约）
FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 先装依赖（利用镜像层缓存）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 再拷源码
COPY . .

# 数据目录（容器内日志/存储，生产以卷挂载覆盖）
RUN mkdir -p /app/logs /app/storage

EXPOSE 9998

# 上线硬约束默认值（H-1 单 worker；生产模式 + 严格自检）
# 可被 docker-compose environment 覆盖，但不建议覆盖 UVICORN_WORKERS
ENV UVICORN_WORKERS=1 \
    UVICORN_PORT=9998 \
    DEPLOY_ENV=docker \
    STRICT_STARTUP=true

CMD ["python", "run.py"]
