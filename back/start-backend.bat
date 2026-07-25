@echo off
REM ==========================================
REM 首页UI迁移测试 - 快速启动脚本
REM ==========================================

echo ========================================
echo 首页UI迁移 - 测试环境启动
echo ========================================

REM 切换到后端目录
cd /d "%~dp0"
echo 当前目录: %CD%

echo.
echo [步骤1] 创建测试数据...
echo ----------------------------------------
python scripts\create_test_data.py
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 测试数据创建失败
    pause
    exit /b 1
)

echo.
echo [步骤2] 启动后端服务...
echo ----------------------------------------
echo 访问地址: http://localhost:8000
echo API文档: http://localhost:8000/docs
echo 健康检查: http://localhost:8000/health
echo.
echo 按 Ctrl+C 停止服务
echo ----------------------------------------
uvicorn app.main:app --reload --port 8000

pause
