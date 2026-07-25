"""回填 medical_check.category 字段

对于 category 为 NULL 的记录，按以下优先级推断分类：
1. 通过 image_report.related_check_id 反查 ImageReport.category
2. 通过 medical_check_detail -> medical_index.category 取多数分类

使用方法:
    cd back
    conda activate oncopath
    python scripts/backfill_medical_check_category.py [--dry-run]
"""
import argparse
import asyncio
import os
import sys
from collections import Counter

# 将项目根目录加入 sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, func, text, update
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.medical import MedicalCheck, MedicalCheckDetail, MedicalIndex
from app.models.image_report import ImageReport


async def backfill(dry_run: bool = False):
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # 统计需要回填的记录数
        count_result = await db.execute(
            select(func.count()).select_from(MedicalCheck).where(MedicalCheck.category.is_(None))
        )
        total = count_result.scalar()
        print(f"需要回填的记录数: {total}")

        if total == 0:
            print("无需回填，退出。")
            await engine.dispose()
            return

        updated = 0
        no_category_found = 0

        # ===== 策略1: 通过 image_report 反查 =====
        result = await db.execute(
            select(
                MedicalCheck.medical_id,
                ImageReport.category,
            )
            .join(ImageReport, ImageReport.related_check_id == MedicalCheck.medical_id)
            .where(
                MedicalCheck.category.is_(None),
                ImageReport.category.isnot(None),
            )
        )
        image_rows = result.all()
        print(f"\n策略1 - 通过 image_report 可推断: {len(image_rows)} 条")

        if image_rows and not dry_run:
            for medical_id, category in image_rows:
                await db.execute(
                    update(MedicalCheck)
                    .where(MedicalCheck.medical_id == medical_id)
                    .values(category=category)
                )
            await db.commit()
            updated += len(image_rows)
            print(f"  已更新: {len(image_rows)} 条")

        # ===== 策略2: 通过 medical_index 的 category 多数投票 =====
        # 查询仍为 NULL 的记录
        remaining_result = await db.execute(
            select(MedicalCheck.medical_id)
            .where(MedicalCheck.category.is_(None))
        )
        remaining_ids = [row[0] for row in remaining_result.all()]
        print(f"\n策略2 - 剩余 NULL 记录: {len(remaining_ids)} 条")

        if remaining_ids:
            # 批量查询所有关联的 detail -> index category
            detail_result = await db.execute(
                select(
                    MedicalCheckDetail.medical_id,
                    MedicalIndex.category,
                )
                .join(MedicalIndex, MedicalCheckDetail.index_id == MedicalIndex.index_id)
                .where(
                    MedicalCheckDetail.medical_id.in_(remaining_ids),
                    MedicalIndex.category.isnot(None),
                )
            )
            detail_rows = detail_result.all()

            # 按 medical_id 分组，取多数分类
            category_map: dict[int, Counter] = {}
            for medical_id, cat in detail_rows:
                if medical_id not in category_map:
                    category_map[medical_id] = Counter()
                category_map[medical_id][cat] += 1

            inferred_count = 0
            for medical_id, counter in category_map.items():
                most_common = counter.most_common(1)[0][0]
                if not dry_run:
                    await db.execute(
                        update(MedicalCheck)
                        .where(MedicalCheck.medical_id == medical_id)
                        .values(category=most_common)
                    )
                inferred_count += 1

            if inferred_count > 0 and not dry_run:
                await db.commit()
                updated += inferred_count

            print(f"  通过指标库推断: {inferred_count} 条")

            # 无法推断的记录
            inferable_ids = set(category_map.keys())
            no_category_found = len(remaining_ids) - len(inferable_ids)
            if no_category_found > 0:
                print(f"  无法推断: {no_category_found} 条 (无关联标准指标或指标无分类)")

        # ===== 结果统计 =====
        print(f"\n{'[DRY RUN] ' if dry_run else ''}回填结果:")
        print(f"  总计需要回填: {total}")
        print(f"  已更新: {updated}")
        print(f"  无法推断: {no_category_found}")

        # 验证
        after_result = await db.execute(
            select(func.count()).select_from(MedicalCheck).where(MedicalCheck.category.is_(None))
        )
        remaining = after_result.scalar()
        print(f"  剩余 NULL: {remaining}")

        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="回填 medical_check.category 字段")
    parser.add_argument("--dry-run", action="store_true", help="仅统计不修改")
    args = parser.parse_args()

    asyncio.run(backfill(dry_run=args.dry_run))
