"""
初始化标准指标数据到 medical_index 表

包含:
1. 血常规指标 (20+)
2. 生化指标 (30+)
3. 肿瘤标志物 (15+)
4. 凝血功能 (10+)
5. 尿常规 (15+)

升级说明：从 StandardIndicator 迁移到 MedicalIndex，
补充 index_code、index_name_en、reference_min/max 等字段
"""
import asyncio
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.medical import MedicalIndex
from sqlalchemy import delete, func

logger = logging.getLogger(__name__)


# 血常规指标
BLOOD_ROUTINE_INDICATORS = [
    {"code": "WBC", "name": "白细胞计数", "name_en": "White Blood Cell", "unit": "10^9/L", "ref_min": 3.5, "ref_max": 9.5, "is_chart": True},
    {"code": "RBC", "name": "红细胞计数", "name_en": "Red Blood Cell", "unit": "10^12/L", "ref_min": 4.3, "ref_max": 5.8, "is_chart": True},
    {"code": "HGB", "name": "血红蛋白", "name_en": "Hemoglobin", "unit": "g/L", "ref_min": 130, "ref_max": 175, "is_chart": True},
    {"code": "HCT", "name": "红细胞压积", "name_en": "Hematocrit", "unit": "%", "ref_min": 40, "ref_max": 50, "is_chart": True},
    {"code": "MCV", "name": "平均红细胞体积", "name_en": "Mean Corpuscular Volume", "unit": "fL", "ref_min": 82, "ref_max": 100, "is_chart": True},
    {"code": "MCH", "name": "平均红细胞血红蛋白量", "name_en": "Mean Corpuscular Hemoglobin", "unit": "pg", "ref_min": 27, "ref_max": 34, "is_chart": True},
    {"code": "MCHC", "name": "平均红细胞血红蛋白浓度", "name_en": "Mean Corpuscular Hemoglobin Concentration", "unit": "g/L", "ref_min": 316, "ref_max": 354, "is_chart": True},
    {"code": "PLT", "name": "血小板计数", "name_en": "Platelet", "unit": "10^9/L", "ref_min": 125, "ref_max": 350, "is_chart": True},
    {"code": "MPV", "name": "平均血小板体积", "name_en": "Mean Platelet Volume", "unit": "fL", "ref_min": 6.8, "ref_max": 13.6, "is_chart": True},
    {"code": "PDW", "name": "血小板分布宽度", "name_en": "Platelet Distribution Width", "unit": "%", "ref_min": 9.0, "ref_max": 17.0, "is_chart": True},
    {"code": "NEUT%", "name": "中性粒细胞百分比", "name_en": "Neutrophil Percentage", "unit": "%", "ref_min": 40, "ref_max": 75, "is_chart": True},
    {"code": "LYMPH%", "name": "淋巴细胞百分比", "name_en": "Lymphocyte Percentage", "unit": "%", "ref_min": 20, "ref_max": 50, "is_chart": True},
    {"code": "MONO%", "name": "单核细胞百分比", "name_en": "Monocyte Percentage", "unit": "%", "ref_min": 3, "ref_max": 10, "is_chart": True},
    {"code": "EO%", "name": "嗜酸性粒细胞百分比", "name_en": "Eosinophil Percentage", "unit": "%", "ref_min": 0.4, "ref_max": 8, "is_chart": True},
    {"code": "BASO%", "name": "嗜碱性粒细胞百分比", "name_en": "Basophil Percentage", "unit": "%", "ref_min": 0, "ref_max": 1, "is_chart": True},
    {"code": "NEUT#", "name": "中性粒细胞计数", "name_en": "Neutrophil Count", "unit": "10^9/L", "ref_min": 1.8, "ref_max": 6.3, "is_chart": True},
    {"code": "LYMPH#", "name": "淋巴细胞计数", "name_en": "Lymphocyte Count", "unit": "10^9/L", "ref_min": 1.1, "ref_max": 3.2, "is_chart": True},
    {"code": "MONO#", "name": "单核细胞计数", "name_en": "Monocyte Count", "unit": "10^9/L", "ref_min": 0.1, "ref_max": 0.6, "is_chart": True},
    {"code": "EO#", "name": "嗜酸性粒细胞计数", "name_en": "Eosinophil Count", "unit": "10^9/L", "ref_min": 0.02, "ref_max": 0.52, "is_chart": True},
    {"code": "BASO#", "name": "嗜碱性粒细胞计数", "name_en": "Basophil Count", "unit": "10^9/L", "ref_min": 0, "ref_max": 0.06, "is_chart": True},
]

# 生化指标
BIOCHEMISTRY_INDICATORS = [
    # 肝功能
    {"code": "ALT", "name": "丙氨酸氨基转移酶", "name_en": "Alanine Aminotransferase", "unit": "U/L", "ref_min": 9, "ref_max": 50, "is_chart": True},
    {"code": "AST", "name": "天门冬氨酸氨基转移酶", "name_en": "Aspartate Aminotransferase", "unit": "U/L", "ref_min": 15, "ref_max": 40, "is_chart": True},
    {"code": "ALP", "name": "碱性磷酸酶", "name_en": "Alkaline Phosphatase", "unit": "U/L", "ref_min": 45, "ref_max": 125, "is_chart": True},
    {"code": "GGT", "name": "γ-谷氨酰转肽酶", "name_en": "Gamma-Glutamyl Transferase", "unit": "U/L", "ref_min": 10, "ref_max": 60, "is_chart": True},
    {"code": "TBIL", "name": "总胆红素", "name_en": "Total Bilirubin", "unit": "μmol/L", "ref_min": 5.1, "ref_max": 22.2, "is_chart": True},
    {"code": "DBIL", "name": "直接胆红素", "name_en": "Direct Bilirubin", "unit": "μmol/L", "ref_min": 0, "ref_max": 6.8, "is_chart": True},
    {"code": "IBIL", "name": "间接胆红素", "name_en": "Indirect Bilirubin", "unit": "μmol/L", "ref_min": 1.7, "ref_max": 13.2, "is_chart": True},
    {"code": "TP", "name": "总蛋白", "name_en": "Total Protein", "unit": "g/L", "ref_min": 65, "ref_max": 85, "is_chart": True},
    {"code": "ALB", "name": "白蛋白", "name_en": "Albumin", "unit": "g/L", "ref_min": 40, "ref_max": 55, "is_chart": True},
    {"code": "GLB", "name": "球蛋白", "name_en": "Globulin", "unit": "g/L", "ref_min": 20, "ref_max": 40, "is_chart": True},
    {"code": "A/G", "name": "白球比", "name_en": "Albumin/Globulin Ratio", "unit": "", "ref_min": 1.2, "ref_max": 2.0, "is_chart": True},

    # 肾功能
    {"code": "CREA", "name": "肌酐", "name_en": "Creatinine", "unit": "μmol/L", "ref_min": 57, "ref_max": 111, "is_chart": True},
    {"code": "UREA", "name": "尿素", "name_en": "Urea", "unit": "mmol/L", "ref_min": 3.1, "ref_max": 8.0, "is_chart": True},
    {"code": "UA", "name": "尿酸", "name_en": "Uric Acid", "unit": "μmol/L", "ref_min": 208, "ref_max": 428, "is_chart": True},
    {"code": "CYS-C", "name": "胱抑素C", "name_en": "Cystatin C", "unit": "mg/L", "ref_min": 0.59, "ref_max": 1.03, "is_chart": True},
    {"code": "BUN", "name": "尿素氮", "name_en": "Blood Urea Nitrogen", "unit": "mmol/L", "ref_min": 2.9, "ref_max": 8.2, "is_chart": True},

    # 血糖血脂
    {"code": "GLU", "name": "葡萄糖", "name_en": "Glucose", "unit": "mmol/L", "ref_min": 3.9, "ref_max": 6.1, "is_chart": True},
    {"code": "TC", "name": "总胆固醇", "name_en": "Total Cholesterol", "unit": "mmol/L", "ref_min": 3.1, "ref_max": 5.7, "is_chart": True},
    {"code": "TG", "name": "甘油三酯", "name_en": "Triglyceride", "unit": "mmol/L", "ref_min": 0.56, "ref_max": 1.7, "is_chart": True},
    {"code": "HDL-C", "name": "高密度脂蛋白胆固醇", "name_en": "HDL Cholesterol", "unit": "mmol/L", "ref_min": 1.0, "ref_max": 1.9, "is_chart": True},
    {"code": "LDL-C", "name": "低密度脂蛋白胆固醇", "name_en": "LDL Cholesterol", "unit": "mmol/L", "ref_min": 0, "ref_max": 3.4, "is_chart": True},

    # 电解质
    {"code": "K", "name": "钾", "name_en": "Potassium", "unit": "mmol/L", "ref_min": 3.5, "ref_max": 5.3, "is_chart": True},
    {"code": "Na", "name": "钠", "name_en": "Sodium", "unit": "mmol/L", "ref_min": 137, "ref_max": 147, "is_chart": True},
    {"code": "Cl", "name": "氯", "name_en": "Chloride", "unit": "mmol/L", "ref_min": 99, "ref_max": 110, "is_chart": True},
    {"code": "Ca", "name": "钙", "name_en": "Calcium", "unit": "mmol/L", "ref_min": 2.11, "ref_max": 2.52, "is_chart": True},
    {"code": "P", "name": "磷", "name_en": "Phosphorus", "unit": "mmol/L", "ref_min": 0.85, "ref_max": 1.51, "is_chart": True},
    {"code": "Mg", "name": "镁", "name_en": "Magnesium", "unit": "mmol/L", "ref_min": 0.75, "ref_max": 1.02, "is_chart": True},
]

# 肿瘤标志物
TUMOR_MARKER_INDICATORS = [
    {"code": "AFP", "name": "甲胎蛋白", "name_en": "Alpha-Fetoprotein", "unit": "ng/mL", "ref_min": 0, "ref_max": 7, "is_chart": True},
    {"code": "CEA", "name": "癌胚抗原", "name_en": "Carcinoembryonic Antigen", "unit": "ng/mL", "ref_min": 0, "ref_max": 5, "is_chart": True},
    {"code": "CA125", "name": "糖类抗原125", "name_en": "Cancer Antigen 125", "unit": "U/mL", "ref_min": 0, "ref_max": 35, "is_chart": True},
    {"code": "CA199", "name": "糖类抗原19-9", "name_en": "Cancer Antigen 19-9", "unit": "U/mL", "ref_min": 0, "ref_max": 37, "is_chart": True},
    {"code": "CA153", "name": "糖类抗原15-3", "name_en": "Cancer Antigen 15-3", "unit": "U/mL", "ref_min": 0, "ref_max": 25, "is_chart": True},
    {"code": "CA724", "name": "糖类抗原72-4", "name_en": "Cancer Antigen 72-4", "unit": "U/mL", "ref_min": 0, "ref_max": 6.9, "is_chart": True},
    {"code": "CA242", "name": "糖类抗原242", "name_en": "Cancer Antigen 242", "unit": "U/mL", "ref_min": 0, "ref_max": 20, "is_chart": True},
    {"code": "CA50", "name": "糖类抗原50", "name_en": "Cancer Antigen 50", "unit": "U/mL", "ref_min": 0, "ref_max": 24, "is_chart": True},
    {"code": "NSE", "name": "神经元特异性烯醇化酶", "name_en": "Neuron-Specific Enolase", "unit": "ng/mL", "ref_min": 0, "ref_max": 16.3, "is_chart": True},
    {"code": "CYFRA211", "name": "细胞角蛋白19片段", "name_en": "Cytokeratin 19 Fragment", "unit": "ng/mL", "ref_min": 0, "ref_max": 3.3, "is_chart": True},
    {"code": "SCC", "name": "鳞状细胞癌抗原", "name_en": "Squamous Cell Carcinoma Antigen", "unit": "ng/mL", "ref_min": 0, "ref_max": 1.5, "is_chart": True},
    {"code": "PSA", "name": "前列腺特异性抗原", "name_en": "Prostate-Specific Antigen", "unit": "ng/mL", "ref_min": 0, "ref_max": 4, "is_chart": True},
    {"code": "FPSA", "name": "游离前列腺特异性抗原", "name_en": "Free Prostate-Specific Antigen", "unit": "ng/mL", "ref_min": 0, "ref_max": 1.0, "is_chart": True},
    {"code": "FPSA/PSA", "name": "游离PSA/总PSA比值", "name_en": "Free/Total PSA Ratio", "unit": "", "ref_min": 0.16, "ref_max": 1.0, "is_chart": True},
]

# 凝血功能
COAGULATION_INDICATORS = [
    {"code": "PT", "name": "凝血酶原时间", "name_en": "Prothrombin Time", "unit": "秒", "ref_min": 11.0, "ref_max": 14.5, "is_chart": True},
    {"code": "APTT", "name": "活化部分凝血活酶时间", "name_en": "Activated Partial Thromboplastin Time", "unit": "秒", "ref_min": 25, "ref_max": 37, "is_chart": True},
    {"code": "TT", "name": "凝血酶时间", "name_en": "Thrombin Time", "unit": "秒", "ref_min": 14, "ref_max": 21, "is_chart": True},
    {"code": "FIB", "name": "纤维蛋白原", "name_en": "Fibrinogen", "unit": "g/L", "ref_min": 2.0, "ref_max": 4.0, "is_chart": True},
    {"code": "D-Dimer", "name": "D-二聚体", "name_en": "D-Dimer", "unit": "mg/L", "ref_min": 0, "ref_max": 0.5, "is_chart": True},
    {"code": "FDP", "name": "纤维蛋白降解产物", "name_en": "Fibrin Degradation Products", "unit": "mg/L", "ref_min": 0, "ref_max": 5, "is_chart": True},
    {"code": "INR", "name": "国际标准化比值", "name_en": "International Normalized Ratio", "unit": "", "ref_min": 0.8, "ref_max": 1.2, "is_chart": True},
    {"code": "AT-III", "name": "抗凝血酶III", "name_en": "Antithrombin III", "unit": "%", "ref_min": 75, "ref_max": 125, "is_chart": True},
]

# 尿常规
URINE_ROUTINE_INDICATORS = [
    {"code": "U-SG", "name": "尿比重", "name_en": "Urine Specific Gravity", "unit": "", "ref_min": 1.003, "ref_max": 1.030, "is_chart": True},
    {"code": "U-pH", "name": "尿酸碱度", "name_en": "Urine pH", "unit": "", "ref_min": 4.6, "ref_max": 8.0, "is_chart": True},
    {"code": "U-LEU", "name": "尿白细胞", "name_en": "Urine Leukocyte", "unit": "", "ref_min": None, "ref_max": None, "is_chart": False},
    {"code": "U-NIT", "name": "尿亚硝酸盐", "name_en": "Urine Nitrite", "unit": "", "ref_min": None, "ref_max": None, "is_chart": False},
    {"code": "U-PRO", "name": "尿蛋白", "name_en": "Urine Protein", "unit": "", "ref_min": None, "ref_max": None, "is_chart": False},
    {"code": "U-GLU", "name": "尿糖", "name_en": "Urine Glucose", "unit": "", "ref_min": None, "ref_max": None, "is_chart": False},
    {"code": "U-KET", "name": "尿酮体", "name_en": "Urine Ketone", "unit": "", "ref_min": None, "ref_max": None, "is_chart": False},
    {"code": "U-UBG", "name": "尿胆原", "name_en": "Urobilinogen", "unit": "", "ref_min": None, "ref_max": None, "is_chart": False},
    {"code": "U-BIL", "name": "尿胆红素", "name_en": "Urine Bilirubin", "unit": "", "ref_min": None, "ref_max": None, "is_chart": False},
    {"code": "U-BLD", "name": "尿潜血", "name_en": "Urine Blood", "unit": "", "ref_min": None, "ref_max": None, "is_chart": False},
]


async def deduplicate_indicators(db: AsyncSession) -> int:
    """去除 OCR 创建的重复指标记录，保留 is_system=True 或 index_id 最小的记录"""
    # 查找有重复名称的指标组
    stmt = (
        select(MedicalIndex.index_name, func.count(MedicalIndex.index_id))
        .group_by(MedicalIndex.index_name)
        .having(func.count(MedicalIndex.index_id) > 1)
    )
    result = await db.execute(stmt)
    duplicate_groups = result.all()

    total_removed = 0
    for name, count in duplicate_groups:
        # 查找该名称的所有记录，按 is_system desc, index_id asc 排序
        stmt = (
            select(MedicalIndex)
            .where(MedicalIndex.index_name == name)
            .order_by(MedicalIndex.is_system.desc(), MedicalIndex.index_id.asc())
        )
        result = await db.execute(stmt)
        records = result.scalars().all()

        # 保留第一条（优先 is_system=True, index_id 最小）
        keep_id = records[0].index_id
        remove_ids = [r.index_id for r in records[1:]]

        if remove_ids:
            # 将关联的 medical_check_detail.index_id 指向保留的记录
            from app.models.medical import MedicalCheckDetail
            stmt = (
                MedicalCheckDetail.__table__.update()
                .where(MedicalCheckDetail.index_id.in_(remove_ids))
                .values(index_id=keep_id)
            )
            await db.execute(stmt)

            # 删除重复记录
            stmt = delete(MedicalIndex).where(MedicalIndex.index_id.in_(remove_ids))
            await db.execute(stmt)
            total_removed += len(remove_ids)
            logger.info(f"去重: '{name}' 保留 index_id={keep_id}, 删除 {len(remove_ids)} 条重复")

    if total_removed:
        await db.commit()
    logger.info(f"去重完成: 删除 {total_removed} 条重复记录")
    return total_removed


async def init_indicators(db: AsyncSession):
    """初始化标准指标到 medical_index 表"""

    all_indicators = [
        ("blood_routine", BLOOD_ROUTINE_INDICATORS),
        ("biochemistry", BIOCHEMISTRY_INDICATORS),
        ("tumor_marker", TUMOR_MARKER_INDICATORS),
        ("coagulation", COAGULATION_INDICATORS),
        ("urine_routine", URINE_ROUTINE_INDICATORS),
    ]

    total_created = 0
    total_updated = 0

    for category, indicators in all_indicators:
        logger.info(f"初始化 {category} 指标...")

        for idx_data in indicators:
            # 通过 index_code 查找已有记录
            code = idx_data.get("code")
            name = idx_data["name"]

            existing = None
            if code:
                stmt = select(MedicalIndex).where(MedicalIndex.index_code == code)
                result = await db.execute(stmt)
                existing = result.scalars().first()

            if not existing:
                # 尝试通过名称查找（可能有多条 OCR 创建的重复记录，取第一条）
                stmt = (
                    select(MedicalIndex)
                    .where(MedicalIndex.index_name == name)
                    .order_by(MedicalIndex.is_system.desc(), MedicalIndex.index_id.asc())
                )
                result = await db.execute(stmt)
                existing = result.scalars().first()

            if existing:
                # 更新已有记录，补充缺失字段
                updated = False
                if code and not existing.index_code:
                    existing.index_code = code
                    updated = True
                if idx_data.get("name_en") and not existing.index_name_en:
                    existing.index_name_en = idx_data["name_en"]
                    updated = True
                if not existing.category:
                    existing.category = category
                    updated = True
                if idx_data.get("ref_min") is not None and existing.reference_min is None:
                    existing.reference_min = idx_data["ref_min"]
                    updated = True
                if idx_data.get("ref_max") is not None and existing.reference_max is None:
                    existing.reference_max = idx_data["ref_max"]
                    updated = True
                if idx_data.get("unit") and not existing.index_unit:
                    existing.index_unit = idx_data["unit"]
                    updated = True

                if updated:
                    total_updated += 1
                    logger.debug(f"更新指标: {name}")
                continue

            # 创建新指标
            indicator = MedicalIndex(
                index_code=code,
                index_name=name,
                index_name_en=idx_data.get("name_en"),
                category=category,
                index_unit=idx_data.get("unit"),
                reference_min=idx_data.get("ref_min"),
                reference_max=idx_data.get("ref_max"),
                is_chart=idx_data.get("is_chart", True),
                is_edit=True,
                is_active=True,
                is_system=True,
                description=idx_data.get("name_en"),
            )
            db.add(indicator)
            total_created += 1

        await db.commit()
        logger.info(f"{category} 指标初始化完成")

    logger.info(f"总计: 新建 {total_created} 个指标, 更新 {total_updated} 个指标")
    return total_created, total_updated


async def main():
    """主函数"""
    async with AsyncSessionLocal() as db:
        try:
            # 先去重 OCR 创建的重复记录
            logger.info("步骤1: 去除重复指标记录...")
            removed = await deduplicate_indicators(db)
            logger.info(f"去重完成: 删除 {removed} 条")

            # 再初始化/更新标准指标
            logger.info("步骤2: 初始化标准指标数据...")
            created, updated = await init_indicators(db)
            logger.info(f"初始化完成: 新建 {created} 个, 更新 {updated} 个")
        except Exception as e:
            logger.error(f"初始化失败: {e}")
            await db.rollback()
            raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())