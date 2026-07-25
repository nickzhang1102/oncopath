"""导入图片分类数据"""
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.database import AsyncSessionLocal


async def import_categories():
    """导入图片分类数据"""
    categories = [
        # 检验类
        ('blood_routine', '血常规', '🩸', '#ff4d4f', '血常规检查', 101),
        ('blood_biochemistry', '生化', '🧬', '#ff7875', '血液生化检查', 102),
        ('coagulation', '凝血', '🩹', '#ffa940', '凝血功能检查', 103),
        ('tumor_markers', '肿瘤标志物', '🎯', '#ff4d4f', '肿瘤标志物检测', 104),
        ('immune', '免疫', '🛡️', '#9254de', '免疫功能检查', 105),
        ('infection', '感染', '🦠', '#52c41a', '感染指标检查', 106),
        ('hormone', '激素', '💊', '#eb2f96', '激素水平检查', 107),
        ('genetics', '基因', '🧬', '#1890ff', '基因检测', 108),
        
        # 尿液检验
        ('urine_routine', '尿常规', '🚰', '#13c2c2', '尿液常规检查', 201),
        ('urine_biochemistry', '尿生化', '🧪', '#52c41a', '尿液生化检查', 202),
        
        # 检查类 - 影像学检查
        ('xray', 'X光', '📷', '#1890ff', 'X射线检查', 301),
        ('ct', 'CT', '🔍', '#52c41a', '计算机断层扫描', 302),
        ('mri', 'MRI', '🔬', '#fa8c16', '磁共振成像', 303),
        ('ultrasound', '超声', '🌊', '#13c2c2', '超声检查', 304),
        ('pet_ct', 'PET-CT', '☢️', '#722ed1', '正电子发射断层扫描', 305),
        ('nuclear', '核医学', '⚛️', '#9254de', '核医学检查', 306),
        
        # 检查类 - 功能检查
        ('ecg', '心电图', '❤️', '#ff4d4f', '心电图检查', 401),
        ('eeg', '脑电图', '🧠', '#ff7875', '脑电图检查', 402),
        ('pulmonary', '肺功能', '🫁', '#faad14', '肺功能检查', 403),
        ('ultrasound_func', '超声功能', '💓', '#13c2c2', '心脏超声等功能检查', 404),
        
        # 检查类 - 内镜检查
        ('endoscopy', '内镜', '🎯', '#722ed1', '内镜检查', 501),
        ('gastroscopy', '胃镜', '🍽️', '#d93661', '胃部内镜检查', 502),
        ('colonoscopy', '肠镜', '🚽', '#d93661', '肠道内镜检查', 503),
        ('bronchoscopy', '支气管镜', '🌬️', '#d93661', '支气管内镜检查', 504),
        
        # 检查类 - 病理检查
        ('pathology', '病理', '🧪', '#eb2f96', '病理检查', 601),
        ('biopsy', '活检', '✂️', '#ff85c0', '组织活检', 602),
        ('cytology', '细胞学', '🔬', '#ffadd2', '细胞学检查', 603),
        
        # 其他体液检验
        ('stool', '粪便', '💩', '#8c8c8c', '粪便检查', 701),
        ('sputum', '痰液', '😷', '#8c8c8c', '痰液检查', 702),
        ('cerebrospinal', '脑脊液', '💧', '#1890ff', '脑脊液检查', 703),
        
        # 微生物检验
        ('microbiology', '微生物', '🔬', '#52c41a', '微生物培养', 801),
        ('bacteria', '细菌', '🦠', '#52c41a', '细菌培养', 802),
        ('fungus', '真菌', '🍄', '#faad14', '真菌培养', 803),
        ('virus', '病毒', '🔬', '#ff4d4f', '病毒检测', 804),
        
        # 其他
        ('pathology_report', '病理报告', '📄', '#8c8c8c', '病理报告文档', 901),
        ('other', '其他', '📁', '#8c8c8c', '其他类型的检查', 999),
    ]
    
    async with AsyncSessionLocal() as session:
        # 清空现有数据
        await session.execute(text("TRUNCATE TABLE image_category RESTART IDENTITY"))
        
        # 插入数据
        for cat in categories:
            await session.execute(text("""
                INSERT INTO image_category (category_key, category_name, icon, color, description, sort_order, is_active)
                VALUES (:key, :name, :icon, :color, :desc, :sort, true)
            """), {
                'key': cat[0],
                'name': cat[1],
                'icon': cat[2],
                'color': cat[3],
                'desc': cat[4],
                'sort': cat[5]
            })
        
        await session.commit()
        print(f"成功导入 {len(categories)} 条分类数据")


if __name__ == "__main__":
    asyncio.run(import_categories())