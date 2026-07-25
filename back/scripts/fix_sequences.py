"""修复 PostgreSQL 自增序列

MySQL 迁移数据到 PostgreSQL 后，自增序列 (sequence) 不会自动同步到已有数据的最大 ID，
导致新插入时 UniqueViolationError。本脚本遍历所有有序列表，将序列设为 MAX(pk)。

使用方式:
    # 本地
    cd back
    conda activate oncopath
    python scripts/fix_sequences.py

    # Docker
    docker compose exec backend python scripts/fix_sequences.py
"""

import asyncio
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 加载 .env 环境变量，避免 Settings 校验失败
from dotenv import load_dotenv
env_path = Path(__file__).resolve().parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)

from app.core.database import engine
from sqlalchemy import text


async def fix_sequences():
    """查询所有序列并修复为对应表的 MAX(pk)"""
    async with engine.begin() as conn:
        # 查询所有自增序列及其关联的表/列
        result = await conn.execute(text("""
            SELECT
                s.relname AS sequence_name,
                t.relname AS table_name,
                a.attname AS column_name
            FROM pg_class s
            JOIN pg_depend d ON d.objid = s.oid
            JOIN pg_class t ON d.refobjid = t.oid
            JOIN pg_attribute a ON (a.attrelid = t.oid AND a.attnum = d.refobjsubid)
            WHERE s.relkind = 'S'
              AND d.deptype = 'a'
            ORDER BY t.relname, a.attname
        """))
        sequences = result.fetchall()

        if not sequences:
            print("未发现自增序列")
            return

        fixed = 0
        skipped = 0
        for seq_name, table_name, col_name in sequences:
            # 获取表中该列的最大值
            max_result = await conn.execute(
                text(f"SELECT COALESCE(MAX({col_name}), 0) FROM {table_name}")
            )
            max_id = max_result.scalar()

            if max_id == 0:
                skipped += 1
                continue

            # 将序列设为最大值，下次插入从 max_id + 1 开始
            await conn.execute(
                text(f"SELECT setval('{seq_name}', {max_id})")
            )
            print(f"  {table_name}.{col_name} -> {seq_name} = {max_id}")
            fixed += 1

        print(f"\n完成: 修复 {fixed} 个序列, 跳过 {skipped} 个空表")


if __name__ == "__main__":
    print("修复 PostgreSQL 自增序列...\n")
    asyncio.run(fix_sequences())
