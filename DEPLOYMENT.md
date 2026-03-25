# 生产环境部署指南

## 启动方式对比

### 1. 开发环境（使用 run.py）

```bash
# 启动开发服务器
python run.py

# 或使用uvicorn（推荐，支持热重载）
uvicorn base.start:app --host 0.0.0.0 --port 9999 --reload
```

**特点：**
- ✅ 代码修改自动重启（--reload）
- ✅ 详细调试信息
- ✅ 单进程运行
- ❌ 不适合生产环境

### 2. 生产环境

#### Linux/Mac 生产环境（推荐）

```bash
# 使用启动脚本
chmod +x start.sh
./start.sh

# 或直接使用gunicorn
gunicorn gunicorn_start:app -c gunicorn_config.py
```

**特点：**
- ✅ 多进程worker（利用多核CPU）
- ✅ 自动重启崩溃进程
- ✅ 日志管理
- ✅ 进程监控
- ✅ 生产环境稳定性

#### Windows 生产环境

```bash
# 使用启动脚本
start.bat

# 或直接使用uvicorn
uvicorn base.start:app --host 0.0.0.0 --port 9999 --workers 4 --log-level info
```

**注意：** Windows不支持Gunicorn，使用Uvicorn多worker模式

## 配置文件说明

### gunicorn_start.py
生产环境应用入口，包含FastAPI应用实例和基础配置

### gunicorn_config.py
Gunicorn配置文件，定义：
- Worker进程数量
- 超时设置
- 日志配置
- 进程管理

### run.py
开发环境启动脚本，保持原有功能用于开发调试

## 环境切换建议

### 开发环境
```bash
# 使用 run.py
python run.py

# 配置：config.conf 中 debug = true
```

### 生产环境
```bash
# 使用 gunicorn
gunicorn gunicorn_start:app -c gunicorn_config.py

# 配置：config.conf 中 debug = false
```

## Systemd 服务配置

创建 `/etc/systemd/system/aipaneladmin.service`：

```ini
[Unit]
Description=AIPanelAdmin FastAPI Application
After=network.target postgresql.service

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/path/to/aipaneladmin
Environment="PATH=/path/to/aipaneladmin/.venv/bin"
ExecStart=/path/to/aipaneladmin/.venv/bin/gunicorn gunicorn_start:app -c gunicorn_config.py
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 启动服务

```bash
# 重载配置
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start aipaneladmin

# 开机自启
sudo systemctl enable aipaneladmin

# 查看状态
sudo systemctl status aipaneladmin

# 查看日志
sudo journalctl -u aipaneladmin -f
```

## Docker 部署

创建 `Dockerfile`：

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 暴露端口
EXPOSE 9999

# 启动命令
CMD ["uvicorn", "base.start:app", "--host", "0.0.0.0", "--port", "9999", "--workers", "4"]
```

创建 `docker-compose.yml`：

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "9999:9999"
    environment:
      - DEBUG=false
    depends_on:
      - db
    restart: always

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=aipaneladmin
      - POSTGRES_USER=admin
      - POSTGRES_PASSWORD=your_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: always

volumes:
  postgres_data:
```

## 性能优化建议

1. **Worker数量**：CPU核心数 × 2 + 1
2. **数据库连接池**：已在 Tortoise ORM 中配置
3. **静态文件**：使用Nginx提供
4. **缓存**：启用Redis（config.conf中配置）
5. **HTTPS**：配置Nginx反向代理 + SSL证书

## 安全检查清单

- [ ] 关闭debug模式（debug = false）
- [ ] 修改数据库密码
- [ ] 修改JWT密钥
- [ ] 配置防火墙
- [ ] 启用HTTPS
- [ ] 配置CORS白名单
- [ ] 定期备份数据库
- [ ] 日志轮转配置

## 监控和维护

```bash
# 查看进程
ps aux | grep gunicorn

# 查看日志
tail -f /var/log/aipaneladmin/access.log
tail -f /var/log/aipaneladmin/error.log

# 重启服务
sudo systemctl restart aipaneladmin

# 平滑重启（不中断服务）
sudo systemctl reload aipaneladmin
```

## 故障排查

### 服务无法启动
```bash
# 检查配置文件
python -c "from gunicorn_start import app; print('Config OK')"

# 检查端口占用
lsof -i :9999
```

### 性能问题
```bash
# 查看worker状态
ps aux | grep gunicorn | wc -l

# 检查数据库连接
# PostgreSQL
SELECT * FROM pg_stat_activity WHERE datname = 'aipaneladmin';
```

### 日志查看
```bash
# 应用日志
tail -f /var/log/aipaneladmin/access.log

# Systemd日志
sudo journalctl -u aipaneladmin -f
```
