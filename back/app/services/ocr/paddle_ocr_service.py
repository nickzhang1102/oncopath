"""PaddleOCR服务封装

提供医疗报告图片的文本提取和指标解析功能
支持基础文本识别和表格结构识别

注意:
- PaddleOCR 3.4.0 要求 PaddlePaddle >= 3.0.0
- Windows用户需使用 PaddlePaddle 3.2.0 以避免oneDNN兼容性问题
- 安装: pip install paddlepaddle==3.2.0 -i https://www.paddlepaddle.org.cn/packages/stable/cpu/
"""
import os

# 在导入 paddleocr 之前设置环境变量，确保 paddlex 使用正确的缓存目录
os.environ.setdefault("PADDLE_PDX_MODEL_DIR", "/app/.paddlex")
os.environ.setdefault("PADDLE_OCR_MODEL_DIR", "/app/.paddleocr")
# 禁用 oneDNN 以避免 PaddlePaddle 3.x 在 CPU 环境下的兼容性问题
os.environ.setdefault("FLAGS_use_onednn", "0")
os.environ.setdefault("FLAGS_mkl_num_threads", "1")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("FLAGS_inter_op_parallelism_threads", "1")
os.environ.setdefault("FLAGS_intra_op_parallelism_threads", "1")

from typing import List, Dict, Optional
import numpy as np
from pathlib import Path
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging

from .ocr_config import ocr_config

logger = logging.getLogger(__name__)

# 模块级共享线程池，避免每次 OCR 调用创建/销毁线程池
_ocr_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="paddle_ocr")


def _require_cv2():
    try:
        import cv2
        return cv2
    except ImportError as exc:
        raise RuntimeError(
            "OpenCV 依赖未安装，无法执行图片 OCR 预处理。请安装 opencv-python-headless 后重试。"
        ) from exc


class PaddleOCRService:
    """PaddleOCR服务封装"""

    def __init__(self):
        """初始化PaddleOCR服务"""
        self.ocr = None
        self._initialized = False
        self._table_pipeline = None
        self._table_initialized = False
        self._table_init_failed = False

    def _lazy_init(self):
        """延迟初始化OCR模型（避免启动时加载）"""
        if not self._initialized:
            try:
                import paddle
                from paddleocr import PaddleOCR
            except ImportError as exc:
                raise RuntimeError(
                    "PaddleOCR 依赖未安装，无法执行 OCR。请按 requirements.txt 安装 "
                    "paddlepaddle/paddleocr/paddlex 后重试。"
                ) from exc

            # 显式设置使用 CPU 设备
            paddle.set_device('cpu')
            # 禁用 oneDNN
            paddle.set_flags({"FLAGS_use_onednn": False})

            # PaddleOCR 3.x API
            # 注意: 使用 predict() 方法，初始化参数已更新
            self.ocr = PaddleOCR(
                lang=ocr_config.paddle_lang,
                device=ocr_config.paddle_device,
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=ocr_config.paddle_use_angle_cls
            )
            self._initialized = True

    async def extract_text_from_image(self, image_path: str) -> List[Dict]:
        """从图片/PDF中提取文本

        PaddleOCR 3.x 的 predict() 原生支持 PDF 文件路径。
        多页 PDF 会返回多个 Result（每页一个），本方法按页合并文本。

        Args:
            image_path: 图片或PDF文件路径

        Returns:
            提取的文本列表
        """
        self._lazy_init()
        cv2 = _require_cv2()

        # 1. 尝试直接识别
        loop = asyncio.get_event_loop()
        try:
            # 优先读取为 numpy 数组，避免 paddlex 内部读取路径编码问题
            is_pdf = image_path.lower().endswith('.pdf')
            if not is_pdf:
                img = cv2.imread(image_path)
                if img is None:
                    logger.warning(f"[PaddleOCR] cv2.imread 失败: {image_path}")
                    predict_input = image_path
                else:
                    predict_input = img
            else:
                predict_input = image_path

            result = await loop.run_in_executor(
                _ocr_executor,
                lambda: self.ocr.predict(predict_input)
            )
        except Exception as e:
            logger.warning(f"[PaddleOCR] 第一次识别异常: {e}")
            result = None

        extracted_data = self._parse_ocr_result(result, ocr_config.min_text_confidence)

        # 2. 如果识别结果为空且是图片，尝试预处理后重试
        if not extracted_data and not is_pdf:
            logger.info(f"[PaddleOCR] 初始识别结果为空，尝试预处理重试: {image_path}")
            try:
                img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
                if img is not None:
                    height, width = img.shape[:2]
                    resized = cv2.resize(
                        img,
                        (int(width * ocr_config.retry_resize_scale), int(height * ocr_config.retry_resize_scale)),
                        interpolation=cv2.INTER_CUBIC
                    )

                    if len(resized.shape) == 2:
                        gray = resized
                    elif resized.shape[2] == 4:
                        gray = cv2.cvtColor(resized, cv2.COLOR_BGRA2GRAY)
                    else:
                        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)

                    clahe = cv2.createCLAHE(
                        clipLimit=ocr_config.retry_clahe_clip_limit,
                        tileGridSize=(ocr_config.retry_clahe_tile_size, ocr_config.retry_clahe_tile_size)
                    )
                    enhanced_gray = clahe.apply(gray)
                    threshold_gray = cv2.adaptiveThreshold(
                        enhanced_gray,
                        255,
                        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                        cv2.THRESH_BINARY,
                        ocr_config.retry_threshold_block_size,
                        ocr_config.retry_threshold_c
                    )

                    retry_inputs = [
                        ("clahe", cv2.cvtColor(enhanced_gray, cv2.COLOR_GRAY2BGR)),
                        ("threshold", cv2.cvtColor(threshold_gray, cv2.COLOR_GRAY2BGR)),
                    ]

                    for retry_name, retry_input in retry_inputs:
                        result_retry = await loop.run_in_executor(
                            _ocr_executor,
                            lambda current_input=retry_input: self.ocr.predict(current_input)
                        )

                        extracted_data = self._parse_ocr_result(
                            result_retry,
                            ocr_config.min_text_confidence
                        )
                        if extracted_data:
                            logger.info(
                                f"[PaddleOCR] 预处理重试成功(strategy={retry_name})，识别到 {len(extracted_data)} 条目"
                            )
                            break

                    if not extracted_data:
                        retry_path = f"{image_path}.ocr_retry.jpg"
                        try:
                            cv2.imwrite(retry_path, retry_inputs[-1][1])
                            result_retry = await loop.run_in_executor(
                                _ocr_executor,
                                lambda: self.ocr.predict(retry_path)
                            )
                            extracted_data = self._parse_ocr_result(
                                result_retry,
                                ocr_config.min_text_confidence
                            )
                            if extracted_data:
                                logger.info(
                                    f"[PaddleOCR] 预处理重试成功(strategy=threshold_file)，识别到 {len(extracted_data)} 条目"
                                )
                        finally:
                            try:
                                if os.path.exists(retry_path):
                                    os.remove(retry_path)
                            except OSError:
                                pass

                    if not extracted_data:
                        cropped = self._crop_content_region(img)
                        if cropped is not None:
                            logger.info(
                                f"[PaddleOCR] 内容区域裁剪后重试: original={img.shape[:2]}, cropped={cropped.shape[:2]}"
                            )
                            extracted_data = await self._run_segmented_ocr(loop, cropped)
            except Exception as e:
                logger.warning(f"[PaddleOCR] 预处理重试失败: {e}")

        if not extracted_data:
            logger.warning(f"[PaddleOCR] 最终识别结果仍为空: {image_path}")

        return extracted_data

    async def _run_segmented_ocr(self, loop: asyncio.AbstractEventLoop, image: np.ndarray) -> List[Dict]:
        """对裁剪后的长图做整图和分段识别。"""
        extracted_data = await self._predict_image_array(loop, image)
        if extracted_data:
            logger.info(f"[PaddleOCR] 裁剪整图识别成功，条目数={len(extracted_data)}")
            return extracted_data

        height, width = image.shape[:2]
        if height <= ocr_config.segment_min_height:
            return []

        step = ocr_config.segment_step
        overlap = ocr_config.segment_overlap
        collected: List[Dict] = []
        slice_index = 0

        for start_y in range(0, height, step):
            end_y = min(start_y + step + overlap, height)
            segment = image[start_y:end_y, 0:width]
            if segment.size == 0:
                continue

            segment_items = await self._predict_image_array(loop, segment)
            if segment_items:
                for item in segment_items:
                    item["bbox"] = self._offset_bbox_y(item.get("bbox", []), start_y)
                    item["page_index"] = 0
                collected.extend(segment_items)
                logger.info(
                    f"[PaddleOCR] 分段识别成功: slice={slice_index}, y={start_y}-{end_y}, 条目数={len(segment_items)}"
                )
            else:
                logger.info(f"[PaddleOCR] 分段识别为空: slice={slice_index}, y={start_y}-{end_y}")

            slice_index += 1
            if end_y >= height:
                break

        return collected

    async def _predict_image_array(self, loop: asyncio.AbstractEventLoop, image: np.ndarray) -> List[Dict]:
        """对 ndarray 图像执行 OCR 并解析结果。"""
        result = await loop.run_in_executor(
            _ocr_executor,
            lambda current_image=image: self.ocr.predict(current_image)
        )
        return self._parse_ocr_result(result, ocr_config.min_text_confidence)

    def _crop_content_region(self, image: np.ndarray) -> Optional[np.ndarray]:
        """裁掉长截图中大面积白边、状态栏和底部空白。"""
        cv2 = _require_cv2()

        if image is None or image.size == 0:
            return None

        if len(image.shape) == 2:
            gray = image
        elif image.shape[2] == 4:
            gray = cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
        else:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        _, binary = cv2.threshold(gray, 245, 255, cv2.THRESH_BINARY_INV)
        coords = cv2.findNonZero(binary)
        if coords is None:
            return None

        x, y, w, h = cv2.boundingRect(coords)
        if w <= 0 or h <= 0:
            return None

        padding = ocr_config.crop_padding
        x1 = max(x - padding, 0)
        y1 = max(y - padding, 0)
        x2 = min(x + w + padding, image.shape[1])
        y2 = min(y + h + padding, image.shape[0])

        cropped = image[y1:y2, x1:x2]
        if cropped.size == 0:
            return None

        # 只有裁掉足够多空白时才启用，避免无意义裁剪
        original_area = image.shape[0] * image.shape[1]
        cropped_area = cropped.shape[0] * cropped.shape[1]
        if cropped_area >= original_area * ocr_config.crop_min_area_ratio:
            return None

        return cropped

    def _offset_bbox_y(self, bbox, offset_y: int):
        """将切片识别得到的 bbox 回写到原图坐标。"""
        if not bbox:
            return bbox

        first = bbox[0]
        if isinstance(first, (list, tuple, np.ndarray)):
            shifted = []
            for point in bbox:
                if len(point) >= 2:
                    shifted.append([float(point[0]), float(point[1]) + offset_y])
            return shifted

        if isinstance(first, (int, float, np.integer, np.floating)):
            shifted = list(bbox)
            for i in range(1, len(shifted), 2):
                shifted[i] = float(shifted[i]) + offset_y
            return shifted

        return bbox

    def _parse_ocr_result(self, result, min_confidence: float) -> List[Dict]:
        """解析 PaddleOCR predict() 返回结果"""
        if not result:
            return []
            
        data = []
        page_index = 0
        try:
            for res in result:
                res_json = None
                try:
                    res_json = res.json if hasattr(res, 'json') else None
                except Exception as e:
                    logger.warning(f"[PaddleOCR] result[{page_index}] res.json access failed: {e}")

                if res_json and isinstance(res_json, dict) and 'res' in res_json:
                    res_data = res_json['res']
                elif isinstance(res, dict):
                    res_data = res
                else:
                    res_data = {}

                rec_texts = res_data.get('rec_texts', [])
                rec_scores = res_data.get('rec_scores', [])
                dt_polys = res_data.get('dt_polys', [])
                rec_polys = res_data.get('rec_polys', [])
                
                dt_polys_count = len(dt_polys)
                if not rec_texts:
                    logger.warning(f"[PaddleOCR] result[{page_index}] rec_texts is empty, dt_polys={dt_polys_count}")
                else:
                    logger.info(f"[PaddleOCR] result[{page_index}] rec_texts={len(rec_texts)}, dt_polys={dt_polys_count}")

                # 优先使用 dt_polys（检测坐标），其次 rec_polys
                polys = dt_polys if len(dt_polys) >= len(rec_texts) else rec_polys

                page_items = []
                for i, text in enumerate(rec_texts):
                    if not text:
                        continue
                    
                    try:
                        confidence = float(rec_scores[i]) if i < len(rec_scores) else 0.95
                    except (TypeError, IndexError):
                        confidence = 0.95

                    try:
                        poly = polys[i] if i < len(polys) else []
                        bbox = poly.tolist() if hasattr(poly, 'tolist') and poly is not None else list(poly) if poly else []
                    except (TypeError, IndexError):
                        bbox = []

                    if confidence >= min_confidence:
                        page_items.append({
                            "text": str(text),
                            "confidence": confidence,
                            "bbox": bbox,
                            "page_index": page_index
                        })

                if page_index > 0 and page_items:
                    data.append({
                        "text": f"===== 第{page_index + 1}页 =====",
                        "confidence": 1.0,
                        "bbox": [],
                        "page_index": page_index,
                        "is_page_separator": True
                    })

                data.extend(page_items)
                page_index += 1
        except Exception as e:
            logger.error(f"[PaddleOCR] Error in _parse_ocr_result: {e}", exc_info=True)

        return data

    async def parse_medical_report(self, image_path: str) -> Dict:
        """解析医疗报告，提取指标列表"""
        extracted_data = await self.extract_text_from_image(image_path)
        raw_text = "\n".join([item["text"] for item in extracted_data])
        metadata = await self._extract_metadata(extracted_data)
        return {
            "indicators": [],  # 指标匹配已由 llm_ocr_parser 独立完成，此处仅保留接口兼容
            "raw_text": raw_text,
            "metadata": metadata
        }

    async def _extract_metadata(self, extracted_data: List[Dict]) -> Dict:
        """提取报告元数据"""
        metadata = {
            "hospital": None,
            "department": None,
            "report_date": None,
            "patient_name": None
        }

        # 提取医院名称
        for item in extracted_data:
            text = item["text"]
            if "医院" in text:
                metadata["hospital"] = text
                break

        # 提取科室
        for item in extracted_data:
            text = item["text"]
            if "科" in text and len(text) < 10:
                metadata["department"] = text
                break

        # 提取日期
        import re
        date_pattern = r'\d{4}[-年/]\d{1,2}[-月/]\d{1,2}[日]?'
        for item in extracted_data:
            match = re.search(date_pattern, item["text"])
            if match:
                metadata["report_date"] = match.group(0)
                break

        return metadata

    def _lazy_init_table(self):
        """延迟初始化表格识别管线"""
        if not self._table_initialized:
            self._try_init_table()

    def _try_init_table(self):
        """尝试初始化表格识别管线"""
        try:
            from paddleocr import TableRecognitionPipelineV2
            self._table_pipeline = TableRecognitionPipelineV2(device="cpu")
            self._table_initialized = True
            self._table_init_failed = False
            logger.info("[TablePipeline] TableRecognitionPipelineV2 (CPU) 初始化完成")
        except ImportError as e:
            logger.error(f"[TablePipeline] PaddleOCR 依赖未安装: {e}")
            self._table_pipeline = None
            self._table_initialized = True
            self._table_init_failed = True
        except Exception as e:
            logger.error(f"[TablePipeline] 初始化失败: {e}", exc_info=True)
            self._table_pipeline = None
            self._table_initialized = True
            self._table_init_failed = True

    async def extract_table_from_image(self, image_path: str) -> Dict:
        """使用表格识别管线提取表格结构"""
        self._lazy_init_table()

        if self._table_pipeline is None:
            if self._table_init_failed:
                self._table_initialized = False
                self._lazy_init_table()
            if self._table_pipeline is None:
                return {"success": False, "error": "表格识别管线不可用"}

        loop = asyncio.get_event_loop()
        try:
            cv2 = _require_cv2()
            # 同样优先使用 numpy 数组
            is_pdf = image_path.lower().endswith('.pdf')
            if not is_pdf:
                img = cv2.imread(image_path)
                predict_input = img if img is not None else image_path
            else:
                predict_input = image_path

            result = await loop.run_in_executor(
                _ocr_executor,
                lambda: self._table_pipeline.predict(predict_input)
            )
        except Exception as e:
            logger.error(f"[TablePipeline] predict 异常: {e}")
            return {"success": False, "error": str(e)}

        if not result:
            return {"success": False, "error": "表格识别返回空结果"}

        try:
            page_index = 0
            first_table_result = None
            supplemental_texts = []

            for res in result:
                res_json = res.json if hasattr(res, 'json') else {}
                if not isinstance(res_json, dict):
                    page_index += 1
                    continue

                res_data = res_json.get('res', {})
                table_res_list = res_data.get('table_res_list', [])

                if page_index == 0:
                    if not table_res_list:
                        page_index += 1
                        continue

                    table_info = table_res_list[0]
                    pred_html = table_info.get('pred_html', '')
                    cell_box_list = table_info.get('cell_box_list', [])

                    if pred_html:
                        rec_texts, raw_text = self._html_to_text(pred_html)
                        first_table_result = {
                            "pred_html": pred_html,
                            "raw_text": raw_text,
                            "rec_texts": rec_texts,
                            "cell_box_list": cell_box_list,
                        }
                else:
                    rec_texts_page = res_data.get('rec_texts', [])
                    if rec_texts_page:
                        supplemental_texts.append(f"===== 第{page_index + 1}页 =====")
                        supplemental_texts.extend(rec_texts_page)
                page_index += 1

            if not first_table_result:
                return {"success": False, "error": "未识别到表格结构"}

            if supplemental_texts:
                first_table_result["rec_texts"] = list(first_table_result["rec_texts"]) + supplemental_texts
                first_table_result["raw_text"] = first_table_result["raw_text"] + "\n" + "\n".join(supplemental_texts)

            logger.info(
                f"[TablePipeline] 识别完成: pred_html长度={len(first_table_result['pred_html'])}, "
                f"行数={len(first_table_result['rec_texts'])}, "
                f"单元格数={len(first_table_result['cell_box_list'])}, "
                f"总页数={page_index}"
            )

            first_table_result["success"] = True
            first_table_result["error"] = None
            return first_table_result

        except Exception as e:
            logger.error(f"[TablePipeline] 解析异常: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def get_page_count(self, file_path: str) -> int:
        """获取PDF页数"""
        if not file_path.lower().endswith('.pdf'):
            return 1
        try:
            import pypdfium2 as pdfium
            doc = pdfium.PdfDocument(file_path)
            try:
                return len(doc)
            finally:
                doc.close()
        except ImportError:
            logger.warning("[PaddleOCR] pypdfium2 未安装，回退返回页数1")
        except Exception as e:
            logger.warning(f"[PaddleOCR] 获取PDF页数失败: {e}")
        return 1

    async def extract_first_page_as_image(self, file_path: str) -> Optional[bytes]:
        """提取PDF第一页为图片（用于缩略图）"""
        if not file_path.lower().endswith('.pdf'):
            return None

        try:
            from io import BytesIO
            import pypdfium2 as pdfium

            doc = pdfium.PdfDocument(file_path)
            try:
                if len(doc) == 0:
                    return None
                page = doc[0]
                try:
                    bitmap = page.render(scale=150 / 72)
                    image = bitmap.to_pil().convert("RGB")
                    image_buffer = BytesIO()
                    image.save(image_buffer, format="JPEG", quality=90)
                    return image_buffer.getvalue()
                finally:
                    page.close()
            finally:
                doc.close()
        except ImportError:
            logger.warning("[PaddleOCR] pypdfium2 未安装，无法提取PDF第一页图片")
        except Exception as e:
            logger.warning(f"[PaddleOCR] 提取PDF第一页图片失败: {e}")

        return None

    @staticmethod
    def _html_to_text(pred_html: str) -> tuple:
        """从表格HTML中提取纯文本"""
        from html.parser import HTMLParser
        import re

        class TableTextExtractor(HTMLParser):
            def __init__(self):
                super().__init__()
                self.rows = []
                self.current_row = []
                self.current_cell = []
                self.in_cell = False

            def handle_starttag(self, tag, attrs):
                if tag in ('td', 'th'):
                    self.in_cell = True
                    self.current_cell = []
                elif tag == 'tr':
                    self.current_row = []

            def handle_endtag(self, tag):
                if tag in ('td', 'th'):
                    cell_text = ''.join(self.current_cell).strip()
                    self.current_row.append(cell_text)
                    self.in_cell = False
                elif tag == 'tr':
                    if self.current_row:
                        self.rows.append(self.current_row)

            def handle_data(self, data):
                if self.in_cell:
                    self.current_cell.append(data)

        extractor = TableTextExtractor()
        extractor.feed(pred_html)

        # OCR常见箭头符号误识别修正
        ARROW_FIXES = {
            '√': '↓',   # 下箭头常被误识为根号
            '个': '↑',   # 上箭头常被误识为"个"
            'J': '↓',    # 下箭头有时被误识为J
            'T': '↑',    # 上箭头有时被误识为T
        }

        def fix_arrows(text: str) -> str:
            """修正数值旁边的箭头符号"""
            for wrong, correct in ARROW_FIXES.items():
                text = re.sub(
                    r'(\d\.?\d*)\s*' + re.escape(wrong) + r'(?=\s|$|\t)',
                    rf'\1{correct}',
                    text
                )
            return text

        rec_texts = []
        for row in extractor.rows:
            non_empty = [cell for cell in row if cell]
            if non_empty:
                line = '\t'.join(non_empty)
                line = fix_arrows(line)
                rec_texts.append(line)

        raw_text = '\n'.join(rec_texts)
        return rec_texts, raw_text


# 全局服务实例
paddle_ocr_service = PaddleOCRService()
