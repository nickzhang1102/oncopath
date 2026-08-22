@echo off
REM ==========================================
REM 后端本地开发启动脚本
REM ==========================================

echo ========================================
echo 本地开发环境启动
echo ========================================

REM 切换到后端目录
cd /d "%~dp0"
echo 当前目录: %CD%

echo.
echo 启动后端服务...
echo ----------------------------------------
echo 访问地址: http://localhost:8000
echo API文档: http://localhost:8000/docs
echo 健康检查: http://localhost:8000/health
echo.
echo 按 Ctrl+C 停止服务
echo ----------------------------------------
uvicorn app.main:app --reload --port 8000

pause
