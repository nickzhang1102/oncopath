"""BYTEA → 文件系统迁移脚本

将 image_report.image_data 和 pathology_report.image 中的二进制数据
迁移到文件系统，数据库中仅保留 image_path 路径。

注意：此脚本在 BYTEA 列被 Alembic 迁移删除前使用。
如果列已被删除，此脚本无需再运行。

用法:
    # 预览模式（不实际写入）
    python -m scripts.migrate_bytea_to_filesystem --dry-run

    # 正式迁移
    python -m scripts.migrate_bytea_to_filesystem

    # 仅迁移 image_report
    python -m scripts.migrate_bytea_to_filesystem --table image_report

    # 仅迁移 pathology_report
    python -m scripts.migrate_bytea_to_filesystem --table pathology_report

    # 自定义批次大小
    python -m scripts.migrate_bytea_to_filesystem --batch-size 20
"""
import argparse
import asyncio
import logging
import sys
import os
from datetime import datetime
from pathlib import Path

# 将 back/ 加入 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# 从 .env 或环境变量获取数据库连接
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


async def migrate_image_reports(
    dry_run: bool = False,
    batch_size: int = 50,
) -> dict:
    """迁移 image_report 表的 image_data BYTEA 数据到文件系统"""
    import asyncpg

    stats = {"total": 0, "migrated": 0, "skipped": 0, "failed": 0}
    conn = await asyncpg.connect(DB_URL)

    try:
        # 检查 image_data 列是否存在
        col_exists = await conn.fetchval("""
            SELECT count(*) FROM information_schema.columns
            WHERE table_name='image_report' AND column_name='image_data'
        """)
        if not col_exists:
            logger.info("[image_report] image_data 列已不存在，跳过")
            return stats

        # 诊断：显示数据分布
        diag = await conn.fetchrow(
            "SELECT count(*) AS total, count(image_data) AS has_image_data, count(image_path) AS has_image_path FROM image_report"
        )
        logger.info(f"[image_report] 数据分布: total={diag['total']}, has_image_data={diag['has_image_data']}, has_image_path={diag['has_image_path']}")

        total = await conn.fetchval(
            "SELECT count(*) FROM image_report WHERE image_data IS NOT NULL AND image_path IS NULL"
        )
        logger.info(f"[image_report] 待迁移记录: {total}")

        if total == 0:
            return stats

        from app.services.storage_service import get_storage_service
        storage = get_storage_service()

        offset = 0
        while True:
            rows = await conn.fetch(
                "SELECT report_id, image_data, image_type FROM image_report "
                "WHERE image_data IS NOT NULL AND image_path IS NULL "
                "ORDER BY report_id LIMIT $1 OFFSET $2",
                batch_size, offset
            )
            if not rows:
                break

            for row in rows:
                stats["total"] += 1
                try:
                    rid = row["report_id"]
                    image_data = row["image_data"]
                    if not image_data:
                        stats["skipped"] += 1
                        continue

                    img_type = row["image_type"] or "jpeg"
                    ext = "jpg" if img_type == "jpeg" else img_type

                    if dry_run:
                        logger.info(f"[DRY-RUN] image_report:{rid} → images/{rid}.{ext} ({len(image_data)} bytes)")
                        stats["migrated"] += 1
                        continue

                    image_path = await storage.save_image(rid, image_data, ext)
                    await conn.execute(
                        "UPDATE image_report SET image_path=$1 WHERE report_id=$2",
                        image_path, rid
                    )

                    # 生成缩略图
                    thumb_row = await conn.fetchrow(
                        "SELECT thumbnail_path FROM image_report WHERE report_id=$1", rid
                    )
                    if thumb_row and not thumb_row["thumbnail_path"] and ext != "pdf":
                        try:
                            from app.utils.thumbnail import generate_thumbnail
                            thumb_data = generate_thumbnail(image_data)
                            thumb_path = await storage.save_thumbnail(rid, thumb_data, "jpg")
                            await conn.execute(
                                "UPDATE image_report SET thumbnail_path=$1 WHERE report_id=$2",
                                thumb_path, rid
                            )
                        except Exception as te:
                            logger.warning(f"缩略图生成失败 report_id={rid}: {te}")

                    stats["migrated"] += 1
                except Exception as e:
                    logger.error(f"迁移失败 image_report:{row['report_id']}: {e}")
                    stats["failed"] += 1

            logger.info(f"[image_report] 批次完成: offset={offset}, migrated={stats['migrated']}, failed={stats['failed']}")
            offset += batch_size
            if len(rows) < batch_size:
                break
    finally:
        await conn.close()

    logger.info(f"[image_report] 迁移完成: {stats}")
    return stats


async def migrate_pathology_reports(
    dry_run: bool = False,
    batch_size: int = 50,
) -> dict:
    """迁移 pathology_report 表的 image BYTEA 数据到文件系统"""
    import asyncpg

    stats = {"total": 0, "migrated": 0, "skipped": 0, "failed": 0}
    conn = await asyncpg.connect(DB_URL)

    try:
        col_exists = await conn.fetchval("""
            SELECT count(*) FROM information_schema.columns
            WHERE table_name='pathology_report' AND column_name='image'
        """)
        if not col_exists:
            logger.info("[pathology_report] image 列已不存在，跳过")
            return stats

        # 诊断：显示数据分布
        diag = await conn.fetchrow(
            "SELECT count(*) AS total, count(image) AS has_image, count(image_path) AS has_image_path FROM pathology_report"
        )
        logger.info(f"[pathology_report] 数据分布: total={diag['total']}, has_image={diag['has_image']}, has_image_path={diag['has_image_path']}")

        total = await conn.fetchval(
            "SELECT count(*) FROM pathology_report WHERE image IS NOT NULL AND image_path IS NULL"
        )
        logger.info(f"[pathology_report] 待迁移记录: {total}")

        if total == 0:
            return stats

        from app.services.storage_service import get_storage_service
        storage = get_storage_service()

        offset = 0
        while True:
            rows = await conn.fetch(
                "SELECT report_id, image, image_type FROM pathology_report "
                "WHERE image IS NOT NULL AND image_path IS NULL "
                "ORDER BY report_id LIMIT $1 OFFSET $2",
                batch_size, offset
            )
            if not rows:
                break

            for row in rows:
                stats["total"] += 1
                try:
                    rid = row["report_id"]
                    image_data = row["image"]
                    if not image_data:
                        stats["skipped"] += 1
                        continue

                    img_type = row["image_type"]
                    if not img_type:
                        img_type = "pdf" if image_data[:4] == b'%PDF' else "jpeg"
                    ext = "jpg" if img_type == "jpeg" else img_type

                    if dry_run:
                        logger.info(f"[DRY-RUN] pathology_report:{rid} → pathology/{rid}.{ext} ({len(image_data)} bytes)")
                        stats["migrated"] += 1
                        continue

                    image_path = await storage.save_pathology_image(rid, image_data, ext)
                    await conn.execute(
                        "UPDATE pathology_report SET image_path=$1, image_type=$2 WHERE report_id=$3",
                        image_path, img_type, rid
                    )
                    stats["migrated"] += 1
                except Exception as e:
                    logger.error(f"迁移失败 pathology_report:{row['report_id']}: {e}")
                    stats["failed"] += 1

            logger.info(f"[pathology_report] 批次完成: offset={offset}, migrated={stats['migrated']}, failed={stats['failed']}")
            offset += batch_size
            if len(rows) < batch_size:
                break
    finally:
        await conn.close()

    logger.info(f"[pathology_report] 迁移完成: {stats}")
    return stats


async def main(dry_run: bool, table: str, batch_size: int):
    logger.info("=" * 60)
    logger.info("BYTEA → 文件系统迁移")
    logger.info(f"模式: {'预览(DRY-RUN)' if dry_run else '正式迁移'}")
    logger.info(f"目标表: {table or '全部'}")
    logger.info(f"批次大小: {batch_size}")
    logger.info(f"开始时间: {datetime.now().isoformat()}")
    logger.info("=" * 60)

    results = {}
    if table in (None, "image_report"):
        try:
            results["image_report"] = await migrate_image_reports(dry_run, batch_size)
        except Exception as e:
            logger.error(f"[image_report] 迁移异常: {e}", exc_info=True)
            results["image_report"] = {"total": 0, "migrated": 0, "skipped": 0, "failed": 0, "error": str(e)}
    if table in (None, "pathology_report"):
        try:
            results["pathology_report"] = await migrate_pathology_reports(dry_run, batch_size)
        except Exception as e:
            logger.error(f"[pathology_report] 迁移异常: {e}", exc_info=True)
            results["pathology_report"] = {"total": 0, "migrated": 0, "skipped": 0, "failed": 0, "error": str(e)}

    logger.info("=" * 60)
    logger.info("迁移汇总:")
    for tbl, st in results.items():
        logger.info(f"  {tbl}: total={st['total']}, migrated={st['migrated']}, skipped={st['skipped']}, failed={st['failed']}")
    logger.info(f"结束时间: {datetime.now().isoformat()}")
    logger.info("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BYTEA → 文件系统迁移")
    parser.add_argument("--dry-run", action="store_true", help="预览模式")
    parser.add_argument("--table", choices=["image_report", "pathology_report"], default=None, help="仅迁移指定表")
    parser.add_argument("--batch-size", type=int, default=50, help="每批处理记录数")
    args = parser.parse_args()
    asyncio.run(main(dry_run=args.dry_run, table=args.table, batch_size=args.batch_size))