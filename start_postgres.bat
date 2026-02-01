@echo off
REM PostgreSQL 启动清理脚本
REM 以管理员身份运行

echo 正在停止所有 PostgreSQL 进程...
taskkill /F /IM postgres.exe 2>nul

timeout /t 2 /nobreak >nul

echo 正在清理锁定文件...
del "F:\pgdata\postmaster.pid" 2>nul
del "F:\pgdata\postmaster.pid.lock" 2>nul

echo 正在启动 PostgreSQL 服务...
net start postgresql-x64-14

echo.
echo PostgreSQL 服务状态:
sc query postgresql-x64-14

pause
