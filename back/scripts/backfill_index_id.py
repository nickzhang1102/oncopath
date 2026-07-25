"""
补填 medical_check_detail.index_id

问题：从 MySQL 迁移数据时，migrate_mysql_to_pg.py 未迁移 index_id 字段，
导致所有 medical_check_detail 的 index_id 为 NULL，指标查询界面无法查到数据。

修复策略（两步）：
1. 精确匹配：index_name 完全一致
2. 模糊匹配：常见别名映射 + 包含关系

使用方式：
    cd back
    conda activate oncopath
    python scripts/backfill_index_id.py [--dry-run] [--step exact|fuzzy|all]
"""

import asyncio
import sys
import io
import os
import logging
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import asyncpg

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def _require_env(key: str) -> str:
    """获取环境变量，缺失时报错退出"""
    val = os.getenv(key)
    if not val:
        print(f"❌ 错误: 环境变量 {key} 未设置。请通过 .env 或 export 设置后再运行此脚本。")
        sys.exit(1)
    return val


PG_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', _require_env('DB_PASSWORD')),
    'database': os.getenv('DB_NAME', 'medical_report'),
}

# 常见别名映射：OCR/旧版名称 -> 标准库名称
ALIAS_MAP = {
    # 粒细胞系列
    '中性粒细胞%': '中性粒细胞百分比',
    '淋巴细胞%': '淋巴细胞百分比',
    '单核细胞%': '单核细胞百分比',
    '嗜酸性细胞%': '嗜酸性粒细胞百分比',
    '嗜碱性细胞%': '嗜碱性粒细胞百分比',
    '中性粒细胞数': '中性粒细胞计数',
    '淋巴细胞数': '淋巴细胞计数',
    '单核细胞数': '单核细胞计数',
    '嗜酸性细胞数': '嗜碱性粒细胞绝对值',
    '嗜酸性粒细胞计数': '嗜酸性粒细胞百分比',
    '嗜碱性粒细胞计数': '嗜碱性粒细胞百分比',
    # 生化系列
    'C-反应蛋白': 'C反应蛋白',
    '超敏C反应蛋白': '超敏C反应蛋白',
    '胆碱脂酶': '胆碱酯酶',
    '低密度脂蛋白胆固醇': '低密度脂蛋白',
    '高密度脂蛋白胆固醇': '高密度脂蛋白',
    '谷氨酰转肽酶乳酸脱氢酶': '谷氨酰转肽酶',
    '酶碱性磷酸酶': '碱性磷酸酶',
    '凝血酶原国际标准化': '凝血酶原国际标准化比值',
    '凝血酶原时间比值': '凝血酶原时间',
    '凝血酶原时间活度': '凝血酶原时间活动度',
    '凝血酶时间比值': '凝血酶时间',
    '活化部分凝血活酶时': '活化部分凝血活酶时间',
    '红细胞分布宽度值': '红细胞分布宽度',
    '糖类抗原153': '糖类抗原15-3',
    'β2-微球蛋白': 'β2微球蛋白',
    '脂肪酶 LIP': '脂肪酶',
    '脂肪酶LIP': '脂肪酶',
    '小而密低密度脂蛋白': '小而密低密度脂蛋白胆固醇',
    '嗜酸性细胞数嗜碱性粒细胞绝对值': '嗜碱性粒细胞绝对值',
    '血清淀粉样蛋白A视黄醇结合蛋白': '血清淀粉样蛋白A',
    '腺甘肌氨酶': '腺苷脱氨酶',
    '降钙素原': '降钙素原',
    '胱抑素C': '胱抑素C',
    '渗透压': '渗透压',
    '淀粉样蛋白A': '血清淀粉样蛋白A',
    '二氧化碳': '二氧化碳总量',
    '载脂蛋白A-I': '载脂蛋白A1',
    '载脂蛋白B': '载脂蛋白B',
    '载脂蛋白E': '载脂蛋白E',
    '脂蛋白a': '脂蛋白(a)',
    '转铁蛋白': '转铁蛋白',
    '同型半胱氨酸': '同型半胱氨酸',
    '唾液酸': '唾液酸',
    '亮氨酰氨基肽酶': '亮氨酰氨基肽酶',
    '淀粉酶': '淀粉酶',
    '视黄醇结合蛋白': '视黄醇结合蛋白',
    '腺苷脱氨酶': '腺苷脱氨酶',
}


async def backfill(dry_run: bool = False, step: str = 'all'):
    pg_pool = await asyncpg.create_pool(
        host=PG_CONFIG['host'], port=PG_CONFIG['port'],
        user=PG_CONFIG['user'], password=PG_CONFIG['password'],
        database=PG_CONFIG['database'], min_size=2, max_size=5,
    )

    try:
        async with pg_pool.acquire() as pg:
            # 加载标准指标库 (index_name -> index_id)
            rows = await pg.fetch(
                "SELECT index_id, index_name FROM medical_index WHERE is_active = true"
            )
            name_to_id = {}
            for r in rows:
                name = r['index_name'].strip()
                if name not in name_to_id:
                    name_to_id[name] = r['index_id']
            logger.info(f"标准指标库: {len(name_to_id)} 条唯一名称")

            total_updated = 0

            # ---- Step 1: 精确匹配 ----
            if step in ('exact', 'all'):
                logger.info("=" * 40)
                logger.info("Step 1: 精确匹配")
                details = await pg.fetch(
                    "SELECT medical_detail_id, index_name FROM medical_check_detail WHERE index_id IS NULL"
                )
                logger.info(f"待处理: {len(details)} 条")

                update_records = []
                for d in details:
                    name = d['index_name'].strip() if d['index_name'] else ''
                    if name in name_to_id:
                        update_records.append((name_to_id[name], d['medical_detail_id']))

                logger.info(f"精确匹配: {len(update_records)}/{len(details)} 条")

                if update_records and not dry_run:
                    await pg.executemany(
                        "UPDATE medical_check_detail SET index_id = $1 WHERE medical_detail_id = $2",
                        update_records
                    )
                    total_updated += len(update_records)
                    logger.info(f"已更新 {len(update_records)} 条")
                elif dry_run:
                    logger.info("[DRY RUN] 不执行更新")

            # ---- Step 2: 模糊匹配（别名映射） ----
            if step in ('fuzzy', 'all'):
                logger.info("=" * 40)
                logger.info("Step 2: 别名模糊匹配")
                details = await pg.fetch(
                    "SELECT medical_detail_id, index_name FROM medical_check_detail WHERE index_id IS NULL"
                )
                logger.info(f"剩余待处理: {len(details)} 条")

                update_records = []
                unmatched_names = {}
                for d in details:
                    name = d['index_name'].strip() if d['index_name'] else ''
                    # 先查别名映射
                    mapped_name = ALIAS_MAP.get(name)
                    if mapped_name and mapped_name in name_to_id:
                        update_records.append((name_to_id[mapped_name], d['medical_detail_id']))
                    else:
                        # 尝试包含匹配：标准库名称包含待匹配名称，或反之
                        found = False
                        for std_name, std_id in name_to_id.items():
                            if name and std_name and (name in std_name or std_name in name):
                                if len(name) >= 2:  # 避免单字符误匹配
                                    update_records.append((std_id, d['medical_detail_id']))
                                    found = True
                                    break
                        if not found:
                            unmatched_names[name] = unmatched_names.get(name, 0) + 1

                logger.info(f"别名+模糊匹配: {len(update_records)}/{len(details)} 条")

                if update_records and not dry_run:
                    await pg.executemany(
                        "UPDATE medical_check_detail SET index_id = $1 WHERE medical_detail_id = $2",
                        update_records
                    )
                    total_updated += len(update_records)
                    logger.info(f"已更新 {len(update_records)} 条")
                elif dry_run:
                    logger.info("[DRY RUN] 不执行更新")

                if unmatched_names:
                    logger.warning(f"仍未匹配 ({len(unmatched_names)} 种):")
                    for name, count in sorted(unmatched_names.items(), key=lambda x: -x[1]):
                        logger.warning(f"  '{name}': {count} 条")

            # ---- 验证 ----
            remaining = await pg.fetchval(
                "SELECT count(*) FROM medical_check_detail WHERE index_id IS NULL"
            )
            total_count = await pg.fetchval(
                "SELECT count(*) FROM medical_check_detail"
            )
            logger.info("=" * 40)
            logger.info(f"总记录: {total_count}, 本次更新: {total_updated}, 剩余 NULL: {remaining}")

    finally:
        await pg_pool.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='补填 medical_check_detail.index_id')
    parser.add_argument('--dry-run', action='store_true', help='仅统计不更新')
    parser.add_argument('--step', choices=['exact', 'fuzzy', 'all'], default='all',
                        help='执行步骤: exact=仅精确匹配, fuzzy=仅模糊匹配, all=全部')
    args = parser.parse_args()

    asyncio.run(backfill(dry_run=args.dry_run, step=args.step))
