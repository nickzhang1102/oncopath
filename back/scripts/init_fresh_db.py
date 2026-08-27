"""数据库种子数据初始化脚本

表结构必须先由 ``alembic upgrade head`` 创建。本脚本只写入幂等种子数据，
可在全新数据库初始化后或已有数据库升级后重复执行。

初始化内容:
1. 默认管理员账号 (admin/ADMIN_INITIAL_PASSWORD 环境变量)
2. 指标分类 (image_category 表，复用于指标分类)
3. 医疗标准指标库 (血常规/生化/肿瘤标志物/凝血/尿常规)
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import select, func
from app.core.config import settings
from app.core.security import get_password_hash
from app.models import *  # noqa: ensure all models registered
from app.models.medical import MedicalIndex
from app.models.image_report import ImageCategory


DEFAULT_ADMIN_USERNAME = "admin"


def _get_admin_password() -> str:
    """从环境变量获取管理员初始密码，未设置则拒绝初始化。"""
    pw = os.environ.get("ADMIN_INITIAL_PASSWORD")
    if not pw or len(pw) < 12:
        raise RuntimeError("必须设置长度至少 12 位的 ADMIN_INITIAL_PASSWORD 后才能初始化管理员账号")
    return pw


# ============================================================
# 标准指标数据定义 (来源: init_indicators.py)
# ============================================================

BLOOD_ROUTINE_INDICATORS = [
    {"code": "WBC", "name": "白细胞计数", "name_en": "White Blood Cell", "unit": "10^9/L", "ref_min": 3.5, "ref_max": 9.5},
    {"code": "RBC", "name": "红细胞计数", "name_en": "Red Blood Cell", "unit": "10^12/L", "ref_min": 4.3, "ref_max": 5.8},
    {"code": "HGB", "name": "血红蛋白", "name_en": "Hemoglobin", "unit": "g/L", "ref_min": 130, "ref_max": 175},
    {"code": "HCT", "name": "红细胞压积", "name_en": "Hematocrit", "unit": "%", "ref_min": 40, "ref_max": 50},
    {"code": "MCV", "name": "平均红细胞体积", "name_en": "Mean Corpuscular Volume", "unit": "fL", "ref_min": 82, "ref_max": 100},
    {"code": "MCH", "name": "平均红细胞血红蛋白量", "name_en": "Mean Corpuscular Hemoglobin", "unit": "pg", "ref_min": 27, "ref_max": 34},
    {"code": "MCHC", "name": "平均红细胞血红蛋白浓度", "name_en": "Mean Corpuscular Hemoglobin Concentration", "unit": "g/L", "ref_min": 316, "ref_max": 354},
    {"code": "PLT", "name": "血小板计数", "name_en": "Platelet", "unit": "10^9/L", "ref_min": 125, "ref_max": 350},
    {"code": "MPV", "name": "平均血小板体积", "name_en": "Mean Platelet Volume", "unit": "fL", "ref_min": 6.8, "ref_max": 13.6},
    {"code": "PDW", "name": "血小板分布宽度", "name_en": "Platelet Distribution Width", "unit": "%", "ref_min": 9.0, "ref_max": 17.0},
    {"code": "NEUT%", "name": "中性粒细胞百分比", "name_en": "Neutrophil Percentage", "unit": "%", "ref_min": 40, "ref_max": 75},
    {"code": "LYMPH%", "name": "淋巴细胞百分比", "name_en": "Lymphocyte Percentage", "unit": "%", "ref_min": 20, "ref_max": 50},
    {"code": "MONO%", "name": "单核细胞百分比", "name_en": "Monocyte Percentage", "unit": "%", "ref_min": 3, "ref_max": 10},
    {"code": "EO%", "name": "嗜酸性粒细胞百分比", "name_en": "Eosinophil Percentage", "unit": "%", "ref_min": 0.4, "ref_max": 8},
    {"code": "BASO%", "name": "嗜碱性粒细胞百分比", "name_en": "Basophil Percentage", "unit": "%", "ref_min": 0, "ref_max": 1},
    {"code": "NEUT#", "name": "中性粒细胞计数", "name_en": "Neutrophil Count", "unit": "10^9/L", "ref_min": 1.8, "ref_max": 6.3},
    {"code": "LYMPH#", "name": "淋巴细胞计数", "name_en": "Lymphocyte Count", "unit": "10^9/L", "ref_min": 1.1, "ref_max": 3.2},
    {"code": "MONO#", "name": "单核细胞计数", "name_en": "Monocyte Count", "unit": "10^9/L", "ref_min": 0.1, "ref_max": 0.6},
    {"code": "EO#", "name": "嗜酸性粒细胞计数", "name_en": "Eosinophil Count", "unit": "10^9/L", "ref_min": 0.02, "ref_max": 0.52},
    {"code": "BASO#", "name": "嗜碱性粒细胞计数", "name_en": "Basophil Count", "unit": "10^9/L", "ref_min": 0, "ref_max": 0.06},
]

BIOCHEMISTRY_INDICATORS = [
    # 肝功能
    {"code": "ALT", "name": "丙氨酸氨基转移酶", "name_en": "Alanine Aminotransferase", "unit": "U/L", "ref_min": 9, "ref_max": 50},
    {"code": "AST", "name": "天门冬氨酸氨基转移酶", "name_en": "Aspartate Aminotransferase", "unit": "U/L", "ref_min": 15, "ref_max": 40},
    {"code": "ALP", "name": "碱性磷酸酶", "name_en": "Alkaline Phosphatase", "unit": "U/L", "ref_min": 45, "ref_max": 125},
    {"code": "GGT", "name": "γ-谷氨酰转肽酶", "name_en": "Gamma-Glutamyl Transferase", "unit": "U/L", "ref_min": 10, "ref_max": 60},
    {"code": "TBIL", "name": "总胆红素", "name_en": "Total Bilirubin", "unit": "μmol/L", "ref_min": 5.1, "ref_max": 22.2},
    {"code": "DBIL", "name": "直接胆红素", "name_en": "Direct Bilirubin", "unit": "μmol/L", "ref_min": 0, "ref_max": 6.8},
    {"code": "IBIL", "name": "间接胆红素", "name_en": "Indirect Bilirubin", "unit": "μmol/L", "ref_min": 1.7, "ref_max": 13.2},
    {"code": "TP", "name": "总蛋白", "name_en": "Total Protein", "unit": "g/L", "ref_min": 65, "ref_max": 85},
    {"code": "ALB", "name": "白蛋白", "name_en": "Albumin", "unit": "g/L", "ref_min": 40, "ref_max": 55},
    {"code": "GLB", "name": "球蛋白", "name_en": "Globulin", "unit": "g/L", "ref_min": 20, "ref_max": 40},
    {"code": "A/G", "name": "白球比", "name_en": "Albumin/Globulin Ratio", "unit": "", "ref_min": 1.2, "ref_max": 2.0},
    # 肾功能
    {"code": "CREA", "name": "肌酐", "name_en": "Creatinine", "unit": "μmol/L", "ref_min": 57, "ref_max": 111},
    {"code": "UREA", "name": "尿素", "name_en": "Urea", "unit": "mmol/L", "ref_min": 3.1, "ref_max": 8.0},
    {"code": "UA", "name": "尿酸", "name_en": "Uric Acid", "unit": "μmol/L", "ref_min": 208, "ref_max": 428},
    {"code": "CYS-C", "name": "胱抑素C", "name_en": "Cystatin C", "unit": "mg/L", "ref_min": 0.59, "ref_max": 1.03},
    {"code": "BUN", "name": "尿素氮", "name_en": "Blood Urea Nitrogen", "unit": "mmol/L", "ref_min": 2.9, "ref_max": 8.2},
    # 血糖血脂
    {"code": "GLU", "name": "葡萄糖", "name_en": "Glucose", "unit": "mmol/L", "ref_min": 3.9, "ref_max": 6.1},
    {"code": "TC", "name": "总胆固醇", "name_en": "Total Cholesterol", "unit": "mmol/L", "ref_min": 3.1, "ref_max": 5.7},
    {"code": "TG", "name": "甘油三酯", "name_en": "Triglyceride", "unit": "mmol/L", "ref_min": 0.56, "ref_max": 1.7},
    {"code": "HDL-C", "name": "高密度脂蛋白胆固醇", "name_en": "HDL Cholesterol", "unit": "mmol/L", "ref_min": 1.0, "ref_max": 1.9},
    {"code": "LDL-C", "name": "低密度脂蛋白胆固醇", "name_en": "LDL Cholesterol", "unit": "mmol/L", "ref_min": 0, "ref_max": 3.4},
    # 电解质
    {"code": "K", "name": "钾", "name_en": "Potassium", "unit": "mmol/L", "ref_min": 3.5, "ref_max": 5.3},
    {"code": "Na", "name": "钠", "name_en": "Sodium", "unit": "mmol/L", "ref_min": 137, "ref_max": 147},
    {"code": "Cl", "name": "氯", "name_en": "Chloride", "unit": "mmol/L", "ref_min": 99, "ref_max": 110},
    {"code": "Ca", "name": "钙", "name_en": "Calcium", "unit": "mmol/L", "ref_min": 2.11, "ref_max": 2.52},
    {"code": "P", "name": "磷", "name_en": "Phosphorus", "unit": "mmol/L", "ref_min": 0.85, "ref_max": 1.51},
    {"code": "Mg", "name": "镁", "name_en": "Magnesium", "unit": "mmol/L", "ref_min": 0.75, "ref_max": 1.02},
]

TUMOR_MARKER_INDICATORS = [
    {"code": "AFP", "name": "甲胎蛋白", "name_en": "Alpha-Fetoprotein", "unit": "ng/mL", "ref_min": 0, "ref_max": 7},
    {"code": "CEA", "name": "癌胚抗原", "name_en": "Carcinoembryonic Antigen", "unit": "ng/mL", "ref_min": 0, "ref_max": 5},
    {"code": "CA125", "name": "糖类抗原125", "name_en": "Cancer Antigen 125", "unit": "U/mL", "ref_min": 0, "ref_max": 35},
    {"code": "CA199", "name": "糖类抗原19-9", "name_en": "Cancer Antigen 19-9", "unit": "U/mL", "ref_min": 0, "ref_max": 37},
    {"code": "CA153", "name": "糖类抗原15-3", "name_en": "Cancer Antigen 15-3", "unit": "U/mL", "ref_min": 0, "ref_max": 25},
    {"code": "CA724", "name": "糖类抗原72-4", "name_en": "Cancer Antigen 72-4", "unit": "U/mL", "ref_min": 0, "ref_max": 6.9},
    {"code": "CA242", "name": "糖类抗原242", "name_en": "Cancer Antigen 242", "unit": "U/mL", "ref_min": 0, "ref_max": 20},
    {"code": "CA50", "name": "糖类抗原50", "name_en": "Cancer Antigen 50", "unit": "U/mL", "ref_min": 0, "ref_max": 24},
    {"code": "NSE", "name": "神经元特异性烯醇化酶", "name_en": "Neuron-Specific Enolase", "unit": "ng/mL", "ref_min": 0, "ref_max": 16.3},
    {"code": "CYFRA211", "name": "细胞角蛋白19片段", "name_en": "Cytokeratin 19 Fragment", "unit": "ng/mL", "ref_min": 0, "ref_max": 3.3},
    {"code": "SCC", "name": "鳞状细胞癌抗原", "name_en": "Squamous Cell Carcinoma Antigen", "unit": "ng/mL", "ref_min": 0, "ref_max": 1.5},
    {"code": "PSA", "name": "前列腺特异性抗原", "name_en": "Prostate-Specific Antigen", "unit": "ng/mL", "ref_min": 0, "ref_max": 4},
    {"code": "FPSA", "name": "游离前列腺特异性抗原", "name_en": "Free Prostate-Specific Antigen", "unit": "ng/mL", "ref_min": 0, "ref_max": 1.0},
    {"code": "FPSA/PSA", "name": "游离PSA/总PSA比值", "name_en": "Free/Total PSA Ratio", "unit": "", "ref_min": 0.16, "ref_max": 1.0},
]

COAGULATION_INDICATORS = [
    {"code": "PT", "name": "凝血酶原时间", "name_en": "Prothrombin Time", "unit": "秒", "ref_min": 11.0, "ref_max": 14.5},
    {"code": "APTT", "name": "活化部分凝血活酶时间", "name_en": "Activated Partial Thromboplastin Time", "unit": "秒", "ref_min": 25, "ref_max": 37},
    {"code": "TT", "name": "凝血酶时间", "name_en": "Thrombin Time", "unit": "秒", "ref_min": 14, "ref_max": 21},
    {"code": "FIB", "name": "纤维蛋白原", "name_en": "Fibrinogen", "unit": "g/L", "ref_min": 2.0, "ref_max": 4.0},
    {"code": "D-Dimer", "name": "D-二聚体", "name_en": "D-Dimer", "unit": "mg/L", "ref_min": 0, "ref_max": 0.5},
    {"code": "FDP", "name": "纤维蛋白降解产物", "name_en": "Fibrin Degradation Products", "unit": "mg/L", "ref_min": 0, "ref_max": 5},
    {"code": "INR", "name": "国际标准化比值", "name_en": "International Normalized Ratio", "unit": "", "ref_min": 0.8, "ref_max": 1.2},
    {"code": "AT-III", "name": "抗凝血酶III", "name_en": "Antithrombin III", "unit": "%", "ref_min": 75, "ref_max": 125},
]

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

ALL_INDICATOR_GROUPS = [
    ("blood_routine", BLOOD_ROUTINE_INDICATORS),
    ("biochemistry", BIOCHEMISTRY_INDICATORS),
    ("tumor_marker", TUMOR_MARKER_INDICATORS),
    ("coagulation", COAGULATION_INDICATORS),
    ("urine_routine", URINE_ROUTINE_INDICATORS),
]

# ============================================================
# 指标分类数据 (image_category 表，复用于指标分类)
# ============================================================

DEFAULT_INDEX_CATEGORIES = [
    # 血液检验 (1xx)
    {"category_key": "blood_routine", "category_name": "血常规", "icon": "🩸", "color": "#ff4d4f", "description": "血常规检查", "sort_order": 101, "group_key": "blood", "report_type": "lab"},
    {"category_key": "blood_biochemistry", "category_name": "生化", "icon": "🧬", "color": "#ff7875", "description": "血液生化检查", "sort_order": 102, "group_key": "blood", "report_type": "lab"},
    {"category_key": "coagulation", "category_name": "凝血", "icon": "🩹", "color": "#ffa940", "description": "凝血功能检查", "sort_order": 103, "group_key": "blood", "report_type": "lab"},
    {"category_key": "tumor_markers", "category_name": "肿瘤标志物", "icon": "🎯", "color": "#ff4d4f", "description": "肿瘤标志物检测", "sort_order": 104, "group_key": "blood", "report_type": "lab"},
    {"category_key": "immune", "category_name": "免疫", "icon": "🛡️", "color": "#9254de", "description": "免疫功能检查", "sort_order": 105, "group_key": "blood", "report_type": "lab"},
    {"category_key": "infection", "category_name": "感染", "icon": "🦠", "color": "#52c41a", "description": "感染指标检查", "sort_order": 106, "group_key": "blood", "report_type": "lab"},
    {"category_key": "hormone", "category_name": "激素", "icon": "💊", "color": "#eb2f96", "description": "激素水平检查", "sort_order": 107, "group_key": "blood", "report_type": "lab"},
    {"category_key": "genetics", "category_name": "基因", "icon": "🧬", "color": "#1890ff", "description": "基因检测", "sort_order": 108, "group_key": "blood", "report_type": "lab"},
    # 尿液检验 (2xx)
    {"category_key": "urine_routine", "category_name": "尿常规", "icon": "🚰", "color": "#13c2c2", "description": "尿液常规检查", "sort_order": 201, "group_key": "urine", "report_type": "lab"},
    {"category_key": "urine_biochemistry", "category_name": "尿生化", "icon": "🧪", "color": "#52c41a", "description": "尿液生化检查", "sort_order": 202, "group_key": "urine", "report_type": "lab"},
    # 影像检查 (3xx)
    {"category_key": "xray", "category_name": "X光", "icon": "📷", "color": "#1890ff", "description": "X射线检查", "sort_order": 301, "group_key": "examination", "report_type": "exam"},
    {"category_key": "ct", "category_name": "CT", "icon": "🔍", "color": "#52c41a", "description": "计算机断层扫描", "sort_order": 302, "group_key": "examination", "report_type": "exam"},
    {"category_key": "mri", "category_name": "MRI", "icon": "🔬", "color": "#fa8c16", "description": "磁共振成像", "sort_order": 303, "group_key": "examination", "report_type": "exam"},
    {"category_key": "ultrasound", "category_name": "超声", "icon": "🌊", "color": "#13c2c2", "description": "超声检查", "sort_order": 304, "group_key": "examination", "report_type": "exam"},
    {"category_key": "pet_ct", "category_name": "PET-CT", "icon": "☢️", "color": "#722ed1", "description": "正电子发射断层扫描", "sort_order": 305, "group_key": "examination", "report_type": "exam"},
    {"category_key": "nuclear", "category_name": "核医学", "icon": "⚛️", "color": "#9254de", "description": "核医学检查", "sort_order": 306, "group_key": "examination", "report_type": "exam"},
    # 功能检查 (4xx)
    {"category_key": "ecg", "category_name": "心电图", "icon": "❤️", "color": "#ff4d4f", "description": "心电图检查", "sort_order": 401, "group_key": "functional", "report_type": "exam"},
    {"category_key": "eeg", "category_name": "脑电图", "icon": "🧠", "color": "#ff7875", "description": "脑电图检查", "sort_order": 402, "group_key": "functional", "report_type": "exam"},
    {"category_key": "pulmonary", "category_name": "肺功能", "icon": "🫁", "color": "#faad14", "description": "肺功能检查", "sort_order": 403, "group_key": "functional", "report_type": "exam"},
    {"category_key": "ultrasound_func", "category_name": "超声功能", "icon": "💓", "color": "#13c2c2", "description": "心脏超声等功能检查", "sort_order": 404, "group_key": "functional", "report_type": "exam"},
    # 内镜检查 (5xx)
    {"category_key": "endoscopy", "category_name": "内镜", "icon": "🎯", "color": "#722ed1", "description": "内镜检查", "sort_order": 501, "group_key": "endoscopic", "report_type": "exam"},
    {"category_key": "gastroscopy", "category_name": "胃镜", "icon": "🍽️", "color": "#d93661", "description": "胃部内镜检查", "sort_order": 502, "group_key": "endoscopic", "report_type": "exam"},
    {"category_key": "colonoscopy", "category_name": "肠镜", "icon": "🚽", "color": "#d93661", "description": "肠道内镜检查", "sort_order": 503, "group_key": "endoscopic", "report_type": "exam"},
    {"category_key": "bronchoscopy", "category_name": "支气管镜", "icon": "🌬️", "color": "#d93661", "description": "支气管内镜检查", "sort_order": 504, "group_key": "endoscopic", "report_type": "exam"},
    # 病理检查 (6xx)
    {"category_key": "pathology", "category_name": "病理", "icon": "🧪", "color": "#eb2f96", "description": "病理检查", "sort_order": 601, "group_key": "pathology", "report_type": "pathology"},
    {"category_key": "biopsy", "category_name": "活检", "icon": "✂️", "color": "#ff85c0", "description": "组织活检", "sort_order": 602, "group_key": "pathology", "report_type": "pathology"},
    {"category_key": "cytology", "category_name": "细胞学", "icon": "🔬", "color": "#ffadd2", "description": "细胞学检查", "sort_order": 603, "group_key": "pathology", "report_type": "pathology"},
    # 体液检查 (7xx)
    {"category_key": "stool", "category_name": "粪便", "icon": "💩", "color": "#8c8c8c", "description": "粪便检查", "sort_order": 701, "group_key": "body_fluid", "report_type": "lab"},
    {"category_key": "sputum", "category_name": "痰液", "icon": "😷", "color": "#8c8c8c", "description": "痰液检查", "sort_order": 702, "group_key": "body_fluid", "report_type": "lab"},
    {"category_key": "cerebrospinal", "category_name": "脑脊液", "icon": "💧", "color": "#1890ff", "description": "脑脊液检查", "sort_order": 703, "group_key": "body_fluid", "report_type": "lab"},
    # 微生物检查 (8xx)
    {"category_key": "microbiology", "category_name": "微生物", "icon": "🔬", "color": "#52c41a", "description": "微生物培养", "sort_order": 801, "group_key": "microbiology", "report_type": "lab"},
    {"category_key": "bacteria", "category_name": "细菌", "icon": "🦠", "color": "#52c41a", "description": "细菌培养", "sort_order": 802, "group_key": "microbiology", "report_type": "lab"},
    {"category_key": "fungus", "category_name": "真菌", "icon": "🍄", "color": "#faad14", "description": "真菌培养", "sort_order": 803, "group_key": "microbiology", "report_type": "lab"},
    {"category_key": "virus", "category_name": "病毒", "icon": "🔬", "color": "#ff4d4f", "description": "病毒检测", "sort_order": 804, "group_key": "microbiology", "report_type": "lab"},
    # 其他 (9xx)
    {"category_key": "pathology_report", "category_name": "病理报告", "icon": "📄", "color": "#8c8c8c", "description": "病理报告文档", "sort_order": 901, "group_key": "other", "report_type": "pathology"},
    {"category_key": "other", "category_name": "其他", "icon": "📁", "color": "#8c8c8c", "description": "其他类型的检查", "sort_order": 999, "group_key": "other", "report_type": "pathology"},
]


async def create_default_admin():
    """创建默认管理员账号（如不存在）"""
    engine = create_async_engine(settings.DATABASE_URL)

    async with AsyncSession(engine) as session:
        result = await session.execute(
            select(LoginAccount).where(LoginAccount.username == DEFAULT_ADMIN_USERNAME)
        )
        existing = result.scalar_one_or_none()

        if existing:
            print(f"管理员账号 '{DEFAULT_ADMIN_USERNAME}' 已存在，跳过创建")
            await engine.dispose()
            return

        admin = LoginAccount(
            username=DEFAULT_ADMIN_USERNAME,
            password=get_password_hash(_get_admin_password()),
            account_name="管理员",
            account_type="admin",
            status="active",
        )
        session.add(admin)
        await session.commit()
        await session.refresh(admin)

        print(f"管理员账号已创建: {DEFAULT_ADMIN_USERNAME}")

    await engine.dispose()


async def init_medical_indices():
    """初始化医疗标准指标库（如为空）"""
    engine = create_async_engine(settings.DATABASE_URL)

    async with AsyncSession(engine) as session:
        # 检查是否已有数据
        count_result = await session.execute(select(func.count(MedicalIndex.index_id)))
        count = count_result.scalar()

        if count > 0:
            print(f"标准指标库已有 {count} 条记录，跳过初始化")
            await engine.dispose()
            return

        total = 0
        for category, indicators in ALL_INDICATOR_GROUPS:
            for idx in indicators:
                indicator = MedicalIndex(
                    index_code=idx.get("code"),
                    index_name=idx["name"],
                    index_name_en=idx.get("name_en"),
                    category=category,
                    index_unit=idx.get("unit") or None,
                    reference_min=idx.get("ref_min"),
                    reference_max=idx.get("ref_max"),
                    is_chart=idx.get("is_chart", True),
                    is_edit=True,
                    is_active=True,
                    is_system=True,
                    description=idx.get("name_en"),
                )
                session.add(indicator)
                total += 1
            await session.commit()

        print(f"标准指标库初始化完成: 共 {total} 条记录")

    await engine.dispose()


async def init_image_categories():
    """初始化指标分类数据到 image_category 表（如为空）"""
    engine = create_async_engine(settings.DATABASE_URL)

    async with AsyncSession(engine) as session:
        count_result = await session.execute(select(func.count(ImageCategory.category_id)))
        count = count_result.scalar()

        if count > 0:
            print(f"image_category 表已有 {count} 条记录，跳过初始化")
            await engine.dispose()
            return

        for cat in DEFAULT_INDEX_CATEGORIES:
            category = ImageCategory(
                category_key=cat["category_key"],
                category_name=cat["category_name"],
                icon=cat.get("icon"),
                color=cat.get("color"),
                description=cat.get("description"),
                sort_order=cat.get("sort_order", 0),
                is_active=True,
            )
            session.add(category)
        await session.commit()

        print(f"指标分类初始化完成: 共 {len(DEFAULT_INDEX_CATEGORIES)} 条记录")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(create_default_admin())
    asyncio.run(init_image_categories())
    asyncio.run(init_medical_indices())
    print("初始化完成！")
