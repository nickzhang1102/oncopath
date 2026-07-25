#!/bin/bash

# 医疗报告系统部署脚本
# 用法: bash scripts/deploy.sh [environment]
# environment: development | production (默认: production)

set -e

ENVIRONMENT=${1:-production}

echo "=========================================="
echo "  医疗报告系统 v2.0 部署脚本"
echo "  环境: ${ENVIRONMENT}"
echo "=========================================="

# 检查环境变量文件
if [ ! -f .env ]; then
    echo "⚠️  .env 文件不存在，从模板创建..."
    cp .env.example .env
    echo "📝 请编辑 .env 文件配置环境变量后重新运行"
    exit 1
fi

# 只读取数值端口；其余配置由 Docker Compose 自行加载，避免执行 .env 内容。
FRONTEND_PORT=$(sed -n 's/^FRONTEND_PORT=//p' .env | tail -1)
FRONTEND_PORT=${FRONTEND_PORT:-3000}
case "${FRONTEND_PORT}" in
    *[!0-9]*) echo "❌ FRONTEND_PORT 必须是数字"; exit 1 ;;
esac

# 1. 拉取最新代码
echo ""
echo "[1/6] 拉取最新代码..."
git pull origin main

# 2. 检查依赖
echo ""
echo "[2/6] 检查依赖..."
command -v docker >/dev/null 2>&1 || { echo "❌ Docker 未安装"; exit 1; }
docker compose version >/dev/null 2>&1 || { echo "❌ Docker Compose v2 未安装"; exit 1; }
echo "✅ 依赖检查通过"

# 3. 构建镜像
echo ""
echo "[3/6] 构建 Docker 镜像..."
docker compose build --no-cache

# 4. 停止旧服务
echo ""
echo "[4/6] 停止旧服务..."
docker compose down

# 5. 启动新服务
echo ""
echo "[5/6] 启动新服务..."
docker compose up -d

# 6. 检查服务状态
echo ""
echo "[6/6] 检查服务状态..."
sleep 10

# 检查后端健康状态
BACKEND_HEALTH=$(curl -sf "http://localhost:${FRONTEND_PORT}/api/v1/health" 2>/dev/null || echo "failed")
if [ "$BACKEND_HEALTH" != "failed" ]; then
    echo "✅ 后端服务运行正常"
else
    echo "⚠️  后端服务可能未完全启动，请检查日志"
fi

# 检查前端
FRONTEND_STATUS=$(curl -sf -o /dev/null -w "%{http_code}" "http://localhost:${FRONTEND_PORT}" 2>/dev/null || echo "000")
if [ "$FRONTEND_STATUS" = "200" ]; then
    echo "✅ 前端服务运行正常"
else
    echo "⚠️  前端服务可能未完全启动，请检查日志"
fi

echo ""
echo "=========================================="
echo "  部署完成!"
echo "=========================================="
echo ""
echo "📍 访问地址:"
echo "   前端: http://localhost:${FRONTEND_PORT}"
echo "   API:  http://localhost:${FRONTEND_PORT}/api"
echo ""
echo "📋 常用命令:"
echo "   查看日志:   docker compose logs -f"
echo "   查看状态:   docker compose ps"
echo "   停止服务:   docker compose down"
echo "   重启服务:   docker compose restart"
echo ""
