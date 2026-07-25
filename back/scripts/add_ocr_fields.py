"""添加 OCR 相关字段到 image_report 表"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.database import AsyncSessionLocal


async def add_ocr_fields():
    """添加 OCR 相关字段"""
    async with AsyncSessionLocal() as session:
        # 检查并添加 ocr_text 字段
        result = await session.execute(text("""
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'image_report' AND column_name = 'ocr_text'
        """))
        if not result.scalar():
            await session.execute(text("ALTER TABLE image_report ADD COLUMN ocr_text TEXT"))
            print("添加 ocr_text 字段")

        # 检查并添加 ocr_status 字段
        result = await session.execute(text("""
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'image_report' AND column_name = 'ocr_status'
        """))
        if not result.scalar():
            await session.execute(text("ALTER TABLE image_report ADD COLUMN ocr_status VARCHAR(20) DEFAULT 'pending'"))
            print("添加 ocr_status 字段")

        # 检查并添加 ocr_error 字段
        result = await session.execute(text("""
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'image_report' AND column_name = 'ocr_error'
        """))
        if not result.scalar():
            await session.execute(text("ALTER TABLE image_report ADD COLUMN ocr_error TEXT"))
            print("添加 ocr_error 字段")

        # 检查并添加 matched_count 字段
        result = await session.execute(text("""
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'image_report' AND column_name = 'matched_count'
        """))
        if not result.scalar():
            await session.execute(text("ALTER TABLE image_report ADD COLUMN matched_count INTEGER DEFAULT 0"))
            print("添加 matched_count 字段")

        # 检查并添加 total_count 字段
        result = await session.execute(text("""
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'image_report' AND column_name = 'total_count'
        """))
        if not result.scalar():
            await session.execute(text("ALTER TABLE image_report ADD COLUMN total_count INTEGER DEFAULT 0"))
            print("添加 total_count 字段")

        # 检查并添加 matching_details 字段
        result = await session.execute(text("""
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'image_report' AND column_name = 'matching_details'
        """))
        if not result.scalar():
            await session.execute(text("ALTER TABLE image_report ADD COLUMN matching_details JSONB"))
            print("添加 matching_details 字段")

        # 检查并添加 created_at 字段
        result = await session.execute(text("""
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'image_report' AND column_name = 'created_at'
        """))
        if not result.scalar():
            await session.execute(text("ALTER TABLE image_report ADD COLUMN created_at TIMESTAMP"))
            print("添加 created_at 字段")

        # 检查并添加 updated_at 字段
        result = await session.execute(text("""
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'image_report' AND column_name = 'updated_at'
        """))
        if not result.scalar():
            await session.execute(text("ALTER TABLE image_report ADD COLUMN updated_at TIMESTAMP"))
            print("添加 updated_at 字段")

        # 检查并添加 upload_date 字段
        result = await session.execute(text("""
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'image_report' AND column_name = 'upload_date'
        """))
        if not result.scalar():
            await session.execute(text("ALTER TABLE image_report ADD COLUMN upload_date TIMESTAMP"))
            print("添加 upload_date 字段")

        # 创建索引
        try:
            await session.execute(text("CREATE INDEX IF NOT EXISTS idx_image_report_ocr_status ON image_report(ocr_status)"))
            print("创建索引 idx_image_report_ocr_status")
        except Exception as e:
            print(f"创建索引时出错: {e}")

        await session.commit()
        print("OCR 字段添加完成！")


if __name__ == "__main__":
    asyncio.run(add_ocr_fields())