"""删除 BYTEA 列的独立脚本

在运行 migrate_bytea_to_filesystem.py 完成数据迁移并验证后，
手动执行此脚本删除数据库中的 BYTEA 列。

⚠️ 此操作不可逆！执行前请确认：
  1. 已运行 migrate_bytea_to_filesystem.py 完成数据迁移
  2. 已验证文件系统中的文件完整且可读
  3. 已备份数据库

用法:
    # 预览模式（检查列是否存在，不实际删除）
    python -m scripts.drop_bytea_columns --dry-run

    # 正式删除
    python -m scripts.drop_bytea_columns

    # 仅删除 image_report.image_data
    python -m scripts.drop_bytea_columns --table image_report

    # 仅删除 pathology_report.image
    python -m scripts.drop_bytea_columns --table pathology_report
"""
import argparse
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

import os


def _require_env(key: str) -> str:
    """获取环境变量，缺失时报错退出"""
    val = os.getenv(key)
    if not val:
        print(f"❌ 错误: 环境变量 {key} 未设置。请通过 .env 或 export 设置后再运行此脚本。")
        sys.exit(1)
    return val


DB_URL = os.environ.get(
    "DATABASE_URL",
    f"postgresql://postgres:{_require_env('DB_PASSWORD')}@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME', 'medical_report')}"
)


async def drop_image_data_column(dry_run: bool = False) -> bool:
    """删除 image_report.image_data 列"""
    import asyncpg

    conn = await asyncpg.connect(DB_URL)
    try:
        col_exists = await conn.fetchval("""
            SELECT count(*) FROM information_schema.columns
            WHERE table_name='image_report' AND column_name='image_data'
        """)
        if not col_exists:
            logger.info("[image_report] image_data 列已不存在，无需操作")
            return True

        # 安全检查：确保没有未迁移的数据
        remaining = await conn.fetchval(
            "SELECT count(*) FROM image_report WHERE image_data IS NOT NULL AND image_path IS NULL"
        )
        if remaining > 0:
            logger.error(f"[image_report] 仍有 {remaining} 条未迁移数据！请先运行迁移脚本")
            return False

        if dry_run:
            logger.info("[DRY-RUN] 将删除 image_report.image_data 列")
            return True

        await conn.execute("ALTER TABLE image_report DROP COLUMN image_data")
        logger.info("[image_report] 已删除 image_data 列")
        return True
    finally:
        await conn.close()


async def drop_pathology_image_column(dry_run: bool = False) -> bool:
    """删除 pathology_report.image 列"""
    import asyncpg

    conn = await asyncpg.connect(DB_URL)
    try:
        col_exists = await conn.fetchval("""
            SELECT count(*) FROM information_schema.columns
            WHERE table_name='pathology_report' AND column_name='image'
        """)
        if not col_exists:
            logger.info("[pathology_report] image 列已不存在，无需操作")
            return True

        # 安全检查：确保没有未迁移的数据
        remaining = await conn.fetchval(
            "SELECT count(*) FROM pathology_report WHERE image IS NOT NULL AND image_path IS NULL"
        )
        if remaining > 0:
            logger.error(f"[pathology_report] 仍有 {remaining} 条未迁移数据！请先运行迁移脚本")
            return False

        if dry_run:
            logger.info("[DRY-RUN] 将删除 pathology_report.image 列")
            return True

        await conn.execute("ALTER TABLE pathology_report DROP COLUMN image")
        logger.info("[pathology_report] 已删除 image 列")
        return True
    finally:
        await conn.close()


async def main(dry_run: bool, table: str):
    logger.info("=" * 60)
    logger.info("删除 BYTEA 列（独立脚本）")
    logger.info(f"模式: {'预览(DRY-RUN)' if dry_run else '⚠️ 正式删除'}")
    logger.info(f"目标表: {table or '全部'}")
    logger.info("=" * 60)

    results = {}
    if table in (None, "image_report"):
        try:
            results["image_report"] = await drop_image_data_column(dry_run)
        except Exception as e:
            logger.error(f"[image_report] 操作异常: {e}", exc_info=True)
            results["image_report"] = False

    if table in (None, "pathology_report"):
        try:
            results["pathology_report"] = await drop_pathology_image_column(dry_run)
        except Exception as e:
            logger.error(f"[pathology_report] 操作异常: {e}", exc_info=True)
            results["pathology_report"] = False

    logger.info("=" * 60)
    logger.info("操作结果:")
    for tbl, ok in results.items():
        status = "✓ 成功" if ok else "✗ 失败"
        logger.info(f"  {tbl}: {status}")
    logger.info("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="删除 BYTEA 列（需先完成数据迁移）")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不实际删除")
    parser.add_argument("--table", choices=["image_report", "pathology_report"], default=None, help="仅删除指定表的列")
    args = parser.parse_args()
    asyncio.run(main(dry_run=args.dry_run, table=args.table))