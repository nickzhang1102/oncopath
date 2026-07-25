"""OCR与指标匹配集成服务

整合OCR识别、LLM解析与指标匹配的完整流程
支持检验报告、检查报告和病理报告的差异化处理
"""
import asyncio
import numpy as np
from typing import List, Dict, Optional
from pathlib import Path
import logging

from .paddle_ocr_service import paddle_ocr_service
from .image_processor import image_processor
from .llm_ocr_parser import llm_ocr_parser, get_report_type, REPORT_TYPE_LAB, REPORT_TYPE_EXAM, REPORT_TYPE_PATHOLOGY
from .ocr_config import ocr_config

logger = logging.getLogger(__name__)


def _parse_bbox_coords(bbox):
    """从bbox中解析出中心坐标、高度和x方向跨度，兼容两种格式

    PaddleOCR 3.x rec_polys 可能返回两种格式：
    - 嵌套格式: [[x1,y1],[x2,y2],[x3,y3],[x4,y4]] (4个角点)
    - 扁平格式: [x1,y1,x2,y2,x3,y3,x4,y4] (8个数值)

    Args:
        bbox: 边界框数据（列表）

    Returns:
        (center_x, center_y, height, x_left, x_right) 或 (None, None, None, None, None)
    """
    if not bbox or len(bbox) < 2:
        return None, None, None, None, None

    # 检测格式：如果第一个元素是列表/元组，则是嵌套格式
    first = bbox[0]
    if isinstance(first, (list, tuple, np.ndarray)):
        # 嵌套格式: [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
        ys = [p[1] for p in bbox if isinstance(p, (list, tuple, np.ndarray)) and len(p) >= 2]
        xs = [p[0] for p in bbox if isinstance(p, (list, tuple, np.ndarray)) and len(p) >= 2]
    elif isinstance(first, (int, float, np.integer, np.floating)):
        # 扁平格式: [x1,y1,x2,y2,x3,y3,x4,y4]
        xs = [bbox[i] for i in range(0, len(bbox), 2)]
        ys = [bbox[i] for i in range(1, len(bbox), 2)]
    else:
        return None, None, None, None, None

    if not ys or not xs:
        return None, None, None, None, None

    # numpy 类型转 float
    xs = [float(x) for x in xs]
    ys = [float(y) for y in ys]

    center_x = sum(xs) / len(xs)
    center_y = sum(ys) / len(ys)
    height = max(ys) - min(ys)
    x_left = min(xs)
    x_right = max(xs)
    return center_x, center_y, height, x_left, x_right


def _x_ranges_overlap(a: Dict, b: Dict, min_overlap_ratio: float = 0.3) -> bool:
    """判断两个文本块的 x 范围是否有显著重叠

    PaddleOCR 拆分长指标名时，拆出的碎片 bbox 常与主体 bbox 重叠。
    如 "(%)"(33-99) 与 "中性粒细胞"(37-206) 重叠区域为 37-99。

    Args:
        a: 文本块（含 x_left, x_right）
        b: 文本块（含 x_left, x_right）
        min_overlap_ratio: 最小重叠比例（相对于较窄块），超过此值视为重叠

    Returns:
        True 表示 x 方向有显著重叠
    """
    a_left, a_right = a.get('x_left'), a.get('x_right')
    b_left, b_right = b.get('x_left'), b.get('x_right')
    if any(v is None for v in [a_left, a_right, b_left, b_right]):
        return False
    # 重叠区间
    overlap_start = max(a_left, b_left)
    overlap_end = min(a_right, b_right)
    if overlap_start >= overlap_end:
        return False
    overlap_width = overlap_end - overlap_start
    # 与较窄块的宽度比较
    narrower_width = min(a_right - a_left, b_right - b_left)
    return narrower_width > 0 and (overlap_width / narrower_width) >= min_overlap_ratio


def group_texts_by_row(ocr_results: List[Dict], y_tolerance_ratio: float = 0.7) -> List[str]:
    """根据bbox坐标将OCR识别文本按行分组

    PaddleOCR对表格图片逐文本块识别，同一行不同列的文本会被识别为独立条目，
    且长指标名可能被拆成多个 bbox 重叠的碎片。

    多页 PDF 结果按 page_index 分组，每组独立行分组，组间插入页分隔符。

    Args:
        ocr_results: PaddleOCR返回的文本列表，每项含text/confidence/bbox/page_index
        y_tolerance_ratio: y坐标容差（相对于平均行高），小于此值的视为同一行

    Returns:
        按行合并后的文本列表，每项对应表格的一行
    """
    if not ocr_results:
        return []

    # 分离页分隔符，按 page_index 分组
    page_groups: Dict[int, List[Dict]] = {}
    separator_pages = []
    for item in ocr_results:
        if item.get('is_page_separator'):
            separator_pages.append(item.get('page_index', 0))
            continue
        text = item.get('text', '')
        if not text or not text.strip():
            continue
        page_idx = item.get('page_index', 0)
        if page_idx not in page_groups:
            page_groups[page_idx] = []
        page_groups[page_idx].append(item)

    if not page_groups:
        return []

    # 对每个 page_index 独立做行分组
    all_grouped = []
    sorted_pages = sorted(page_groups.keys())
    for page_idx in sorted_pages:
        # 插入页分隔符（第2页起）
        if page_idx > 0 and page_idx in separator_pages:
            all_grouped.append(f"===== 第{page_idx + 1}页 =====")
        all_grouped.extend(_group_single_page_by_row(page_groups[page_idx], y_tolerance_ratio))

    return all_grouped


def _group_single_page_by_row(page_items: List[Dict], y_tolerance_ratio: float = 0.7) -> List[str]:
    """对单页的OCR结果按行分组

    Args:
        page_items: 单页的OCR文本列表，每项含text/confidence/bbox
        y_tolerance_ratio: y坐标容差

    Returns:
        按行合并后的文本列表
    """
    # 解析每个文本块的中心坐标和x边界
    items_with_pos = []
    for item in page_items:
        bbox = item.get('bbox', [])
        center_x, center_y, height, x_left, x_right = _parse_bbox_coords(bbox)
        items_with_pos.append({
            'text': item.get('text', ''),
            'center_y': center_y,
            'center_x': center_x,
            'height': height,
            'x_left': x_left,
            'x_right': x_right,
        })

    # 没有任何坐标信息时，退化为原始逐行文本
    items_with_coords = [it for it in items_with_pos if it['center_y'] is not None]
    if not items_with_coords:
        return [item.get('text', '') for item in page_items if item.get('text')]

    # 计算平均行高作为容差基准
    heights = [it['height'] for it in items_with_coords if it['height'] and it['height'] > 0]
    avg_height = sum(heights) / len(heights) if heights else 20
    y_tolerance = avg_height * y_tolerance_ratio

    # 按y坐标排序
    items_with_coords.sort(key=lambda x: x['center_y'])

    # 聚合式行合并：新块与行内任意已有块的y距离 <= y_tolerance 即归入该行
    rows: List[List[Dict]] = []
    current_row = [items_with_coords[0]]

    for item in items_with_coords[1:]:
        min_y_dist = min(abs(item['center_y'] - row_item['center_y']) for row_item in current_row)
        if min_y_dist <= y_tolerance:
            current_row.append(item)
        else:
            current_row.sort(key=lambda x: x['center_x'])
            rows.append(current_row)
            current_row = [item]

    current_row.sort(key=lambda x: x['center_x'])
    rows.append(current_row)

    # 无坐标的文本各自作为独立行追加到末尾
    items_no_coords = [it for it in items_with_pos if it['center_y'] is None]
    for item in items_no_coords:
        rows.append([item])

    # 合并每行文本：重叠聚簇 → 簇内合并 → 簇间排序
    grouped_texts = []
    for row in rows:
        if len(row) <= 1:
            grouped_texts.append(row[0]['text'] if row else '')
            continue

        # 第1步：重叠聚簇 — x范围重叠的块视为同一区域的拆分碎片
        clusters: List[List[Dict]] = []
        for item in row:
            merged = False
            for cluster in clusters:
                for existing in cluster:
                    if _x_ranges_overlap(item, existing):
                        cluster.append(item)
                        merged = True
                        break
                if merged:
                    break
            if not merged:
                clusters.append([item])

        # 第2步：簇内合并 — 最宽块为主体，碎片直接追加在后
        cluster_results = []
        for cluster in clusters:
            if len(cluster) == 1:
                cluster_results.append(cluster[0])
                continue
            # 按宽度降序：最宽的块是主体文本
            cluster.sort(key=lambda x: (x.get('x_right', 0) - x.get('x_left', 0)), reverse=True)
            main_block = cluster[0]
            fragments = cluster[1:]
            merged_text = main_block['text'] + ''.join(f['text'] for f in fragments)
            all_x_lefts = [main_block.get('x_left')] + [f.get('x_left') for f in fragments]
            all_x_rights = [main_block.get('x_right')] + [f.get('x_right') for f in fragments]
            cluster_results.append({
                'text': merged_text,
                'x_left': min(x for x in all_x_lefts if x is not None) if any(x is not None for x in all_x_lefts) else None,
                'x_right': max(x for x in all_x_rights if x is not None) if any(x is not None for x in all_x_rights) else None,
            })

        # 第3步：簇之间按 x_left 排序，用两空格连接
        cluster_results.sort(key=lambda x: x.get('x_left', 0) if x.get('x_left') is not None else 0)
        grouped_texts.append('  '.join(block['text'] for block in cluster_results))

    logger.info(f"[行分组] 单页文本块: {len(page_items)}, 分组行数: {len(grouped_texts)}")
    return grouped_texts




class OCRIntegrationService:
    """OCR集成服务 - 根据报告类型选择不同的处理流程"""

    async def process_medical_report_image(
        self,
        image_path: str,
        category: Optional[str] = None,
        is_pdf: bool = False,
        db=None
    ) -> Dict:
        """处理医疗报告图片/PDF的完整流程

        根据分类自动选择处理流程：
        - 检验类（血液、尿液、体液）：表格识别 → LLM解析 → 匹配标准库 → 返回指标列表
          （表格识别失败时降级为基础文本识别）
        - 检查类（影像、功能、内镜）：OCR → LLM提取医学信息 → 返回检查信息
        - 病理类（病理、其他）：OCR → LLM提取病理信息 → 返回病理信息

        Args:
            image_path: 图片或PDF文件路径
            category: 图片分类key（如 'blood_routine', 'ct', 'pathology'）
            is_pdf: 是否为PDF文件

        Returns:
            处理结果，根据报告类型包含不同内容:
            - report_type: 报告类型 (lab/exam/pathology)
            - raw_text: 原始OCR文本
            - 检验类额外返回: indicators, matched_count, total_count
            - 检查类额外返回: exam_info
            - 病理类额外返回: pathology_info
        """
        # 1. 验证文件
        if is_pdf:
            is_valid, error_msg = image_processor.validate_pdf(image_path)
            if not is_valid:
                raise ValueError(f"PDF验证失败: {error_msg}")
        else:
            is_valid, error_msg = image_processor.validate_image(image_path)
            if not is_valid:
                raise ValueError(f"图片验证失败: {error_msg}")

        # 2. 根据分类确定报告类型
        report_type = await get_report_type(category, db=db) if category else REPORT_TYPE_LAB
        logger.info(f"处理报告: category={category}, report_type={report_type}, is_pdf={is_pdf}")

        # 3. 基础OCR（所有类型都需要）
        ocr_results = await paddle_ocr_service.extract_text_from_image(image_path)
        ocr_row_texts = group_texts_by_row(ocr_results)
        metadata = await paddle_ocr_service._extract_metadata(ocr_results)

        rec_texts = None
        raw_text = None
        use_table_rec = False

        # 4. 检验类额外走表格识别，合并两者结果
        if report_type == REPORT_TYPE_LAB and ocr_config.use_table_recognition:
            logger.info("[OCR集成] 尝试表格识别...")
            table_result = await paddle_ocr_service.extract_table_from_image(image_path)
            if table_result.get('success'):
                table_texts = table_result['rec_texts']
                use_table_rec = True
                # 拼接：表格识别结果 + 基础OCR补充，LLM综合处理冗余
                rec_texts = list(table_texts) + ['===== 基础OCR补充 ====='] + list(ocr_row_texts)
                raw_text = "\n".join(rec_texts)
                logger.info(f"[表格识别] 拼接后行数={len(rec_texts)} (表格={len(table_texts)}, OCR={len(ocr_row_texts)})")
            else:
                logger.warning(
                    f"[表格识别] 失败: {table_result.get('error')}，使用基础文本识别"
                )

        # 5. 降级路径：仅基础文本识别
        if rec_texts is None:
            rec_texts = ocr_row_texts
            raw_text = "\n".join(rec_texts)

        if report_type == REPORT_TYPE_LAB:
            return await self._process_lab_report(
                rec_texts, raw_text, metadata, category, use_table_rec=use_table_rec
            )
        elif report_type == REPORT_TYPE_EXAM:
            return await self._process_exam_report(rec_texts, raw_text, metadata, category)
        else:
            return await self._process_pathology_report(rec_texts, raw_text, metadata, category)

    async def _process_lab_report(
        self,
        rec_texts: List[str],
        raw_text: str,
        metadata: Dict,
        category: Optional[str],
        use_table_rec: bool = False
    ) -> Dict:
        """处理检验报告

        Args:
            rec_texts: OCR识别的文本列表
            raw_text: 原始OCR文本
            metadata: 元数据
            category: 分类key
            use_table_rec: 是否使用了表格识别

        Returns:
            检验报告处理结果
        """
        # LLM解析+匹配（一步到位）
        parse_result = await llm_ocr_parser.parse_with_matching(rec_texts, category)

        # 处理返回结果（可能是字典或列表）
        if isinstance(parse_result, dict):
            indicators = parse_result.get('indicators', [])
            llm_raw_response = parse_result.get('llm_raw_response', '')
        else:
            # 兼容旧版本返回列表的情况
            indicators = parse_result
            llm_raw_response = ''

        # 统计匹配数量
        matched_count = sum(1 for ind in indicators if ind.get('matched_index_id'))

        return {
            'report_type': REPORT_TYPE_LAB,
            'indicators': indicators,
            'matched_count': matched_count,
            'total_count': len(indicators),
            'metadata': metadata,
            'raw_text': raw_text,
            'parse_method': 'table_recognition' if use_table_rec else 'llm',
            'llm_raw_response': llm_raw_response
        }

    async def _process_exam_report(
        self,
        rec_texts: List[str],
        raw_text: str,
        metadata: Dict,
        category: Optional[str]
    ) -> Dict:
        """处理检查报告

        Args:
            rec_texts: OCR识别的文本列表
            raw_text: 原始OCR文本
            metadata: 元数据
            category: 分类key

        Returns:
            检查报告处理结果
        """
        # LLM提取检查信息
        exam_info = await llm_ocr_parser.parse_exam_report(rec_texts, category)

        return {
            'report_type': REPORT_TYPE_EXAM,
            'exam_info': exam_info,
            'metadata': metadata,
            'raw_text': raw_text,
            'parse_method': 'llm',
            'llm_raw_response': exam_info.get('llm_raw_response', '')
        }

    async def _process_pathology_report(
        self,
        rec_texts: List[str],
        raw_text: str,
        metadata: Dict,
        category: Optional[str]
    ) -> Dict:
        """处理病理报告

        Args:
            rec_texts: OCR识别的文本列表
            raw_text: 原始OCR文本
            metadata: 元数据
            category: 分类key

        Returns:
            病理报告处理结果
        """
        # LLM提取病理信息
        pathology_info = await llm_ocr_parser.parse_pathology_report(rec_texts, category)

        return {
            'report_type': REPORT_TYPE_PATHOLOGY,
            'pathology_info': pathology_info,
            'metadata': metadata,
            'raw_text': raw_text,
            'parse_method': 'llm',
            'llm_raw_response': pathology_info.get('llm_raw_response', '')
        }

    async def batch_process_images(
        self,
        image_paths: List[str],
        category: Optional[str] = None
    ) -> List[Dict]:
        """批量处理图片

        Args:
            image_paths: 图片路径列表
            category: 报告分类key

        Returns:
            处理结果列表
        """
        tasks = [
            self.process_medical_report_image(path, category)
            for path in image_paths
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理异常
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    'image_path': image_paths[i],
                    'error': str(result),
                    'success': False
                })
            else:
                result['image_path'] = image_paths[i]
                result['success'] = True
                processed_results.append(result)

        return processed_results

    async def process_check_report(
        self,
        file_path: str,
        category: Optional[str],
        hospital: str,
        medical_date,
        patient_id: int
    ) -> Dict:
        """处理检验报告（适配上传API）

        Args:
            file_path: 图片文件路径
            category: 报告分类key
            hospital: 医院名称
            medical_date: 医疗日期
            patient_id: 患者ID

        Returns:
            处理结果
        """
        from sqlalchemy.ext.asyncio import AsyncSession
        from app.core.database import AsyncSessionLocal
        from app.models.medical import MedicalCheck, MedicalCheckDetail

        # 使用OCR处理图片
        result = await self.process_medical_report_image(file_path, category)

        indicators = result.get('indicators', [])

        if not indicators:
            raise ValueError("未能从图片中识别出有效的检验指标")

        # 保存到数据库
        async with AsyncSessionLocal() as db:
            # 创建检验记录
            has_abnormal = any(
                ind.get('status') in ('low', 'high', 'abnormal')
                for ind in indicators
            )

            medical_check = MedicalCheck(
                patient_id=patient_id,
                medical_date=medical_date.date() if hasattr(medical_date, 'date') else medical_date,
                hospital=hospital,
                category=category,
                status='abnormal' if has_abnormal else 'normal'
            )
            db.add(medical_check)
            await db.flush()

            # 添加检验明细
            items_added = 0
            for ind in indicators:
                detail = MedicalCheckDetail(
                    medical_id=medical_check.medical_id,
                    index_id=ind.get('matched_index_id'),
                    index_name=ind.get('name', ''),
                    index_value=ind.get('value', ''),
                    index_unit=ind.get('unit', ''),
                    reference_value=ind.get('reference', ''),
                    index_status=ind.get('status', 'normal')
                )
                db.add(detail)
                items_added += 1

            await db.commit()

        return {
            'status': 'success',
            'medical_id': medical_check.medical_id,
            'items_count': items_added,
            'has_abnormal': has_abnormal,
            'matched_count': result.get('matched_count', 0)
        }

    async def process_exam_report(
        self,
        file_path: str,
        category: Optional[str],
        hospital: str,
        medical_date,
        patient_id: int
    ) -> Dict:
        """处理检查报告（适配上传API）

        Args:
            file_path: 图片文件路径
            category: 报告分类key
            hospital: 医院名称
            medical_date: 医疗日期
            patient_id: 患者ID

        Returns:
            处理结果
        """
        from sqlalchemy.ext.asyncio import AsyncSession
        from app.core.database import AsyncSessionLocal
        from app.models.medical import MedicalExam

        # 使用OCR处理图片
        result = await self.process_medical_report_image(file_path, category)

        raw_text = result.get('raw_text', '')

        if not raw_text.strip():
            raise ValueError("未能从图片中识别出有效的检查信息")

        # 保存到数据库
        async with AsyncSessionLocal() as db:
            # 创建检查记录
            medical_exam = MedicalExam(
                patient_id=patient_id,
                medical_date=medical_date.date() if hasattr(medical_date, 'date') else medical_date,
                exam_type=category,
                hospital=hospital,
                exam_info=raw_text[:500],  # 取前500字符作为检查信息
                exam_diag=''  # 诊断信息需要后续人工填写或AI分析
            )
            db.add(medical_exam)
            await db.commit()

        return {
            'status': 'success',
            'exam_id': medical_exam.exam_id,
            'exam_info': raw_text[:500]
        }


# 全局实例
ocr_integration_service = OCRIntegrationService()