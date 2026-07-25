#!/bin/bash

# PostgreSQL 与文件存储备份脚本
# 用法: bash scripts/backup.sh

set -e

# 配置
BACKUP_DIR="${BACKUP_DIR:-./backups}"
DATE=$(date +%Y%m%d_%H%M%S)
DB_BACKUP_FILE="medical_database_${DATE}.dump"
STORAGE_BACKUP_FILE="medical_storage_${DATE}.tar.gz"

echo "=========================================="
echo "  医疗报告系统 - 数据库备份"
echo "=========================================="

# 创建备份目录
mkdir -p "${BACKUP_DIR}"

echo "📦 开始备份数据库..."
echo "   数据库: 使用 postgres 容器的 POSTGRES_DB 配置"
echo "   目标目录: ${BACKUP_DIR}"

# 执行 PostgreSQL custom-format 备份
docker compose exec -T postgres sh -c \
    'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' \
    > "${BACKUP_DIR}/${DB_BACKUP_FILE}"

# 检查备份是否成功
if [ -s "${BACKUP_DIR}/${DB_BACKUP_FILE}" ]; then
    DB_SIZE=$(du -h "${BACKUP_DIR}/${DB_BACKUP_FILE}" | cut -f1)
    echo "✅ 数据库备份完成: ${BACKUP_DIR}/${DB_BACKUP_FILE} (${DB_SIZE})"
else
    echo "❌ 数据库备份失败"
    exit 1
fi

echo "📦 开始备份文件存储卷..."
BACKUP_DIR_ABS=$(cd "${BACKUP_DIR}" && pwd)
docker compose run --rm --no-deps \
    -v "${BACKUP_DIR_ABS}:/backup" \
    --entrypoint sh backend \
    -c "tar -czf '/backup/${STORAGE_BACKUP_FILE}' -C /app/storage ."

if [ ! -s "${BACKUP_DIR}/${STORAGE_BACKUP_FILE}" ]; then
    echo "❌ 文件存储备份失败"
    exit 1
fi

# 清理旧备份 (保留最近30天)
echo ""
echo "🧹 清理30天前的备份..."
find "${BACKUP_DIR}" -name "medical_database_*.dump" -mtime +30 -delete
find "${BACKUP_DIR}" -name "medical_storage_*.tar.gz" -mtime +30 -delete
echo "✅ 清理完成"

# 列出当前备份
echo ""
echo "📋 当前备份列表:"
find "${BACKUP_DIR}" -maxdepth 1 -type f \
    \( -name "medical_database_*.dump" -o -name "medical_storage_*.tar.gz" \) \
    -printf "%TY-%Tm-%Td %TH:%TM %10s %f\n" | sort | tail -10

echo ""
echo "=========================================="
