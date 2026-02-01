@echo off
REM PostgreSQL 服务启动脚本（带延迟）
REM 用于 Windows 任务计划程序

REM 等待系统稳定
timeout /t 10 /nobreak >nul

REM 停止可能存在的残留进程
taskkill /F /IM postgres.exe 2>nul

REM 清理锁定文件
del "F:\pgdata\postmaster.pid" 2>nul
del "F:\pgdata\postmaster.pid.lock" 2>nul

REM 启动服务
net start postgresql-x64-14
