"""OCR 结果处理模块

从 image_report.py 抽取的三种报告类型处理逻辑，
后台任务路径和 SSE 流式路径共享同一处理函数。
"""
import json
import logging
import re
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select

from app.models.image_report import ImageReport
from app.models.medical import MedicalCheck, MedicalCheckDetail

logger = logging.getLogger(__name__)

# 报告类型常量
REPORT_TYPE_LAB = "lab"
REPORT_TYPE_EXAM = "exam"

# 癌种推断映射：从病理诊断文本中提取癌种
_CANCER_TYPE_PATTERNS = [
    (r'肺癌|肺腺癌|肺鳞癌|小细胞肺癌|非小细胞肺癌', '肺癌'),
    (r'乳腺癌|浸润性导管癌|浸润性小叶癌', '乳腺癌'),
    (r'胃癌|胃腺癌|胃印戒细胞癌', '胃癌'),
    (r'结肠癌|直肠癌|结直肠癌|肠腺癌', '结直肠癌'),
    (r'肝癌|肝细胞癌|肝胆管癌', '肝癌'),
    (r'食管癌|食管鳞癌|食管腺癌', '食管癌'),
    (r'胰腺癌|胰腺导管腺癌', '胰腺癌'),
    (r'甲状腺癌|甲状腺乳头状癌|甲状腺滤泡癌', '甲状腺癌'),
    (r'肾癌|肾透明细胞癌|肾细胞癌', '肾癌'),
    (r'膀胱癌|尿路上皮癌', '膀胱癌'),
    (r'前列腺癌', '前列腺癌'),
    (r'宫颈癌|宫颈鳞癌|宫颈腺癌', '宫颈癌'),
    (r'卵巢癌|卵巢浆液性癌|卵巢黏液性癌', '卵巢癌'),
    (r'淋巴瘤|霍奇金淋巴瘤|非霍奇金淋巴瘤', '淋巴瘤'),
    (r'白血病|急性髓系白血病|慢性淋巴细胞白血病', '白血病'),
    (r'黑色素瘤', '黑色素瘤'),
    (r'肉瘤|骨肉瘤|软组织肉瘤', '肉瘤'),
]


def _infer_cancer_type(diagnosis: str, histology_type: str) -> str:
    """从病理诊断和组织学类型推断癌种

    Args:
        diagnosis: 病理诊断文本
        histology_type: 组织学类型

    Returns:
        推断的癌种，无法判断则返回空字符串
    """
    combined = f"{diagnosis or ''} {histology_type or ''}"
    for pattern, cancer_type in _CANCER_TYPE_PATTERNS:
        if re.search(pattern, combined):
            return cancer_type
    return ""


async def process_lab_result(db: AsyncSession, image_report: ImageReport, ocr_result: dict):
    """处理检验类报告结果：更新报告 + 创建检验记录及明细"""
    indicators = ocr_result.get('indicators', [])
    matched_count = ocr_result.get('matched_count', 0)
    total_count = len(indicators)

    # 更新报告匹配信息
    image_report.matched_count = matched_count
    image_report.total_count = total_count
    image_report.matching_details = {
        'indicators': [
            {
                'raw_name': ind.get('name'),
                'normalized_name': ind.get('normalized_name'),
                'value': ind.get('value'),
                'unit': ind.get('unit'),
                'reference': ind.get('reference'),
                'status': ind.get('status'),
                'matched_index_id': ind.get('matched_index_id'),
                'matched_name': ind.get('matched_name'),
                'match_confidence': ind.get('match_confidence'),
                'match_method': ind.get('match_method')
            }
            for ind in indicators
        ]
    }
    image_report.extracted_info = {
        'indicators': indicators,
        'matched_count': matched_count,
        'total_count': total_count
    }

    if indicators:
        medical_check = MedicalCheck(
            patient_id=image_report.patient_id,
            medical_date=image_report.capture_date or date.today(),
            hospital=image_report.hospital,
            category=image_report.category,
            status='abnormal' if any(ind.get('status') in ('low', 'high', 'abnormal') for ind in indicators) else 'normal'
        )
        db.add(medical_check)
        await db.flush()

        # 查询该患者同日同医院同分类下已有的 index_id 和 index_name 集合
        existing_checks = await db.execute(
            select(MedicalCheck.medical_id).where(
                MedicalCheck.patient_id == image_report.patient_id,
                MedicalCheck.medical_date == medical_check.medical_date,
                MedicalCheck.hospital == image_report.hospital,
                MedicalCheck.category == image_report.category,
                MedicalCheck.medical_id != medical_check.medical_id,
            )
        )
        existing_check_ids = [row[0] for row in existing_checks.all()]

        existing_index_ids = set()
        existing_index_names = set()
        if existing_check_ids:
            existing_details = await db.execute(
                select(MedicalCheckDetail.index_id, MedicalCheckDetail.index_name).where(
                    MedicalCheckDetail.medical_id.in_(existing_check_ids),
                )
            )
            for row in existing_details.all():
                if row[0] is not None:
                    existing_index_ids.add(row[0])
                if row[1] is not None:
                    existing_index_names.add(row[1])

        # 插入指标明细（去重）
        skipped_count = 0
        for ind in indicators:
            index_id = ind.get('matched_index_id')
            index_name = ind.get('name', '')

            # index_id 非 null 时按 index_id 去重，否则按 index_name 去重
            if index_id is not None and index_id in existing_index_ids:
                skipped_count += 1
                continue
            if index_id is None and index_name in existing_index_names:
                skipped_count += 1
                continue

            detail = MedicalCheckDetail(
                medical_id=medical_check.medical_id,
                index_id=index_id,
                index_name=index_name,
                index_value=ind.get('value', ''),
                index_unit=ind.get('unit', ''),
                reference_value=ind.get('reference', ''),
                index_status=ind.get('status', 'normal')
            )
            db.add(detail)
            # 更新去重集合，防止同一批指标内部重复
            if index_id is not None:
                existing_index_ids.add(index_id)
            existing_index_names.add(index_name)

        image_report.related_check_id = medical_check.medical_id
        logger.info(f"创建检验记录: medical_id={medical_check.medical_id}, 指标数={len(indicators)}, 跳过重复={skipped_count}")
        return medical_check.medical_id, skipped_count

    return None, 0


async def process_exam_result(db: AsyncSession, image_report: ImageReport, ocr_result: dict):
    """处理检查类报告结果：更新报告 + 创建检查记录"""
    from app.models.medical import MedicalExam

    exam_info = ocr_result.get('exam_info', {})

    image_report.matched_count = 0
    image_report.total_count = 0
    image_report.extracted_info = exam_info

    medical_exam = MedicalExam(
        patient_id=image_report.patient_id,
        medical_date=image_report.capture_date or date.today(),
        hospital=image_report.hospital,
        title=exam_info.get('report_title') or image_report.title,
        exam_type=image_report.category,
        exam_info=exam_info.get('exam_findings', ''),
        exam_diag=exam_info.get('diagnosis', ''),
        comment='\n'.join(exam_info.get('key_findings', [])) if exam_info.get('key_findings') else None
    )
    db.add(medical_exam)
    await db.flush()

    image_report.related_exam_id = medical_exam.exam_id
    logger.info(f"创建检查记录: exam_id={medical_exam.exam_id}")
    return medical_exam.exam_id


async def process_pathology_result(db: AsyncSession, image_report: ImageReport, ocr_result: dict):
    """处理病理类报告结果：更新报告 + 创建病理记录

    LLM 解析的 pathology_info 字段映射到 PathologyReport 结构化字段：
    - diagnosis ← pathology_diagnosis
    - cancer_type ← 从诊断文本推断
    - stage ← tumor_stage
    - histology_type ← histology_type
    - immunohistochemistry ← ihc_results JSON 序列化
    - gene_testing ← gene_testing JSON 序列化
    """
    from app.models.medical import PathologyReport

    pathology_info = ocr_result.get('pathology_info', {})

    image_report.matched_count = 0
    image_report.total_count = 0
    image_report.extracted_info = pathology_info

    report_title = pathology_info.get('report_title') or image_report.title

    # 从 LLM 解析结果推断癌种
    diagnosis = pathology_info.get('pathology_diagnosis', '')
    histology_type = pathology_info.get('histology_type', '')
    cancer_type = _infer_cancer_type(diagnosis, histology_type)

    # 免疫组化结果序列化
    ihc_results = pathology_info.get('ihc_results', {})
    immunohistochemistry = json.dumps(ihc_results, ensure_ascii=False) if ihc_results else None

    # 基因检测结果序列化
    gene_testing_data = pathology_info.get('gene_testing')
    gene_testing = json.dumps(gene_testing_data, ensure_ascii=False) if gene_testing_data else None

    pathology_report = PathologyReport(
        patient_id=image_report.patient_id,
        report_title=report_title,
        report_date=image_report.capture_date or date.today(),
        hospital=image_report.hospital,
        comment='\n'.join(pathology_info.get('key_findings', [])) if pathology_info.get('key_findings') else None,
        # 结构化字段
        diagnosis=diagnosis or None,
        cancer_type=cancer_type or None,
        stage=pathology_info.get('tumor_stage') or None,
        histology_type=histology_type or None,
        immunohistochemistry=immunohistochemistry,
        gene_testing=gene_testing,
    )

    # 先 flush 主报告获取 report_id
    db.add(pathology_report)
    await db.flush()
    _report_flushed = True

    # 创建免疫组化结构化子记录
    if ihc_results and isinstance(ihc_results, dict):
        from app.models.medical import PathologyIHC
        for marker_name, result_value in ihc_results.items():
            result_str = str(result_value) if result_value is not None else None
            intensity = None
            percentage = None
            if result_str and '%' in result_str:
                pct_match = re.search(r'([\d>]+\s*%)', result_str)
                if pct_match:
                    percentage = pct_match.group(1)
            ihc_marker = PathologyIHC(
                report_id=pathology_report.report_id,
                marker_name=marker_name,
                result=result_str,
                intensity=intensity,
                percentage=percentage,
            )
            db.add(ihc_marker)
    # 传递病理图片：从文件系统读取
    image_data = None
    storage = None
    if image_report.image_path:
        try:
            from app.services.storage_service import get_storage_service
            storage = get_storage_service()
            ext = "jpg" if image_report.image_type == "jpeg" else (image_report.image_type or "jpg")
            image_data = await storage.read_image(image_report.report_id, ext)
        except Exception as e:
            logger.warning(f"读取图片报告文件失败 report_id={image_report.report_id}: {str(e)}")

    if image_data:
        try:
            img_type = image_report.image_type or "jpeg"
            ext = "jpg" if img_type == "jpeg" else img_type
            image_path = await storage.save_pathology_image(pathology_report.report_id, image_data, ext)
            pathology_report.image_path = image_path
            pathology_report.image_type = image_report.image_type
        except Exception as e:
            logger.warning(f"保存病理图片到文件系统失败 report_id={pathology_report.report_id}: {str(e)}")

    image_report.related_pathology_id = pathology_report.report_id
    logger.info(f"创建病理记录: pathology_id={pathology_report.report_id}, cancer_type={cancer_type}")
    return pathology_report.report_id
