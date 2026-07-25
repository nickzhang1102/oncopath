"""LLM OCR解析服务

使用LLM智能解析OCR识别结果，提取医疗指标并匹配标准库
支持任意格式的医疗检验报告、检查报告和病理报告
"""
import json
import logging
import re
from typing import List, Dict, Optional
from functools import lru_cache

from app.utils.llm_parser import parse_llm_json, parse_llm_json_list

from app.services.desensitization import desensitization_service
from .openai_llm_service import get_openai_llm_service

logger = logging.getLogger(__name__)

# 报告类型常量
REPORT_TYPE_LAB = 'lab'  # 检验类：血液、尿液、体液、微生物
REPORT_TYPE_EXAM = 'exam'  # 检查类：影像学、功能、内镜
REPORT_TYPE_PATHOLOGY = 'pathology'  # 病理类：病理检查、其他


# 标准库指标缓存
_STANDARD_INDICATORS_CACHE: Dict[str, List[Dict]] = {}


class LLMOCRParser:
    """LLM辅助的OCR结果解析器
    
    使用Claude LLM智能解析各种格式的医疗报告，
    支持表格格式、单行格式、键值对格式等。
    """
    
    SYSTEM_PROMPT = """你是一个专业的医疗检验报告解析专家。你的任务是从OCR识别的文本中提取检验指标信息。

## 输入说明
你会收到一个JSON数组，包含OCR识别出的文本行。每行已经过行分组处理：同一行不同列的文本已用两个空格合并到同一行，不同行分开排列。每个数组元素对应表格的一行。

## 提取规则
1. **只提取检验指标**：忽略报告标题、医院名称、科室、日期、患者信息、医生签名等非指标内容
2. **指标名称识别**：通常包含"计数"、"率"、"蛋白"、"细胞"等关键词，或常见的英文缩写如WBC、RBC、HGB等
3. **数值提取**：提取检验结果数值（注意区分检验值和参考值）
4. **单位识别**：常见单位如g/L、mg/L、10^9/L、%、fl、pg等
5. **参考范围**：提取参考值范围，格式可能是"3.5-9.5"、"<10"、">100"等
6. **异常状态**：识别↑↓高低箭头标记，判断status为high/low/normal

## 表格格式处理
输入文本已按行合并：同一行的指标名、检验值、单位、参考值在同一行内用空格分隔。
- 每行通常对应一个检验指标，格式为：指标名  数值  单位  参考范围
- 如果某行包含多个指标，请分别提取

## 返回格式
返回严格的JSON数组格式，不要包含任何其他文本：
[
    {
        "name": "指标名称（中文或英文）",
        "value": "数值部分（纯数字）",
        "unit": "单位",
        "reference": "参考范围",
        "status": "normal/high/low"
    }
]

## 注意事项
- 如果某项信息无法确定，使用null
- 确保返回的是有效的JSON数组
- 不要添加任何解释性文字"""

    USER_PROMPT_TEMPLATE = """请从以下OCR识别的文本行中提取检验指标：

文本行列表（JSON格式）：
{rec_texts_json}

请返回JSON格式的指标列表，只包含指标数据，不要包含任何解释性文字。"""

    async def parse_ocr_results(
        self, 
        rec_texts: List[str],
        rec_scores: Optional[List[float]] = None
    ) -> List[Dict]:
        """使用LLM解析OCR结果
        
        Args:
            rec_texts: OCR识别的文本列表
            rec_scores: OCR识别的置信度列表（可选，用于过滤低置信度文本）
            
        Returns:
            解析后的指标列表，每个元素包含:
            - name: 指标名称
            - value: 数值
            - unit: 单位
            - reference: 参考范围
            - status: 状态 (normal/high/low)
            - confidence: 置信度
        """
        if not rec_texts:
            logger.warning("OCR文本列表为空")
            return []
        
        # 过滤空文本
        valid_texts = [t for t in rec_texts if t and t.strip()]
        if not valid_texts:
            logger.warning("过滤后OCR文本列表为空")
            return []

        # 脱敏处理：移除手机号、身份证号等敏感信息
        desensitized_texts = [
            desensitization_service.desensitize_text(t) for t in valid_texts
        ]

        # 调用LLM解析
        try:
            llm_service = get_openai_llm_service()

            user_prompt = self.USER_PROMPT_TEMPLATE.format(
                rec_texts_json=json.dumps(desensitized_texts, ensure_ascii=False, indent=2)
            )
            
            logger.info(f"开始LLM解析，文本行数: {len(valid_texts)}")
            
            result = await llm_service.analyze(
                system_prompt=self.SYSTEM_PROMPT,
                user_prompt=user_prompt
            )
            
            content = result.get('content', '')
            tokens_used = result.get('tokens_used', 0)
            
            # 解析JSON响应
            indicators = self._extract_json(content)
            
            # 添加置信度信息
            for indicator in indicators:
                indicator['confidence'] = 0.95  # LLM解析默认置信度
                indicator['parse_method'] = 'llm'
            
            logger.info(f"LLM解析成功，提取{len(indicators)}个指标，tokens={tokens_used}")
            
            return indicators
            
        except Exception as e:
            logger.error(f"LLM解析失败: {e}", exc_info=True)
            # 返回空列表而不是抛出异常，避免影响整体流程
            return []
    
    def _extract_json(self, content: str) -> List[Dict]:
        """从LLM响应中提取JSON数组，使用统一解析器"""
        if not content:
            logger.warning("LLM响应内容为空")
            return []

        result = parse_llm_json_list(content)
        if result is not None:
            logger.info(f"成功从LLM响应提取JSON，指标数: {len(result)}")
            return self._validate_indicators(result)

        logger.warning(
            f"无法从LLM响应中提取有效JSON，内容长度: {len(content)}, "
            f"前200字符: {content[:200]!r}, 后100字符: {content[-100:]!r}"
        )
        return []
    
    def _validate_indicators(self, indicators: List[Dict]) -> List[Dict]:
        """验证并清理指标数据
        
        Args:
            indicators: 原始指标列表
            
        Returns:
            验证后的指标列表
        """
        valid_indicators = []
        
        for ind in indicators:
            if not isinstance(ind, dict):
                continue
            
            # 必须有指标名称
            name = ind.get('name')
            if not name or not isinstance(name, str) or not name.strip():
                continue
            
            # 清理数据
            clean_ind = {
                'name': name.strip(),
                'value': self._clean_value(ind.get('value')),
                'unit': self._clean_string(ind.get('unit')),
                'reference': self._clean_string(ind.get('reference')),
                'status': self._normalize_status(ind.get('status')),
                # 保留匹配相关字段（parse_with_matching 使用）
                'matched_index_id': ind.get('matched_index_id'),
                'matched_name': self._clean_string(ind.get('matched_name')),
                'match_confidence': ind.get('match_confidence'),
            }
            
            valid_indicators.append(clean_ind)
        
        return valid_indicators
    
    def _clean_value(self, value) -> Optional[str]:
        """清理数值字段
        
        Args:
            value: 原始数值
            
        Returns:
            清理后的数值字符串
        """
        if value is None:
            return None
        
        if isinstance(value, (int, float)):
            return str(value)
        
        if isinstance(value, str):
            # 提取数字部分
            value = value.strip()
            # 匹配数字（包括小数和科学计数法）
            match = re.search(r'[\d.]+(?:[eE][+-]?\d+)?', value)
            if match:
                return match.group(0)
        
        return None
    
    def _clean_string(self, value) -> Optional[str]:
        """清理字符串字段
        
        Args:
            value: 原始值
            
        Returns:
            清理后的字符串
        """
        if value is None:
            return None
        
        if isinstance(value, str):
            value = value.strip()
            return value if value else None
        
        return str(value)
    
    def _normalize_status(self, status) -> str:
        """标准化状态字段
        
        Args:
            status: 原始状态
            
        Returns:
            标准化后的状态 (normal/high/low)
        """
        if not status or not isinstance(status, str):
            return 'normal'
        
        status = status.strip().lower()
        
        if status in ('high', '高', '偏高', '↑'):
            return 'high'
        elif status in ('low', '低', '偏低', '↓'):
            return 'low'
        else:
            return 'normal'

    # ========== 新增：带指标匹配的解析方法 ==========

    SYSTEM_PROMPT_WITH_MATCHING = """你是一个专业的医疗检验报告解析专家。你的任务是从OCR识别的文本中提取检验指标信息，并匹配到标准指标库。

## 输入说明
1. OCR文本行列表（JSON数组，已按行分组：同一行不同列的文本已用两个空格合并）
2. 标准指标库列表（包含index_id、index_name、index_code等字段）

## 提取规则
1. **只提取检验指标**：忽略报告标题、医院名称、科室、日期、患者信息、医生签名等非指标内容
2. **指标名称识别**：通常包含"计数"、"率"、"蛋白"、"细胞"等关键词，或常见的英文缩写如WBC、RBC、HGB等
3. **数值提取**：提取检验结果数值（注意区分检验值和参考值）
4. **单位识别**：常见单位如g/L、mg/L、10^9/L、%、fl、pg等
5. **参考范围**：提取参考值范围，格式可能是"3.5-9.5"、"<10"、">100"等
6. **异常状态**：识别↑↓高低箭头标记，判断status为high/low/normal

## 匹配规则
1. 将识别出的指标名称与标准指标库进行语义匹配
2. 支持中文匹配、英文缩写匹配（如"白细胞计数"匹配"WBC"）
3. 如果无法匹配到标准库，matched_index_id 设为 null
4. 匹配置信度：0.0-1.0，1.0表示完全匹配

## 表格格式处理
输入文本已按行合并：同一行的指标名、检验值、单位、参考值在同一行内用空格分隔。
- 每行通常对应一个检验指标，格式为：指标名  数值  单位  参考范围
- 如果某行包含多个指标，请分别提取

## 返回格式
返回严格的JSON数组格式：
[
    {
        "name": "原始指标名称",
        "value": "数值部分（纯数字）",
        "unit": "单位",
        "reference": "参考范围",
        "status": "normal/high/low",
        "matched_index_id": 匹配的标准指标ID或null,
        "matched_name": "匹配的标准名称",
        "match_confidence": 0.95
    }
]"""

    USER_PROMPT_WITH_MATCHING_TEMPLATE = """请从以下OCR识别的文本行中提取检验指标，并匹配到标准指标库：

## OCR文本行列表
{rec_texts_json}

## 标准指标库
{standard_indicators_json}

请返回JSON格式的指标列表。"""

    async def parse_with_matching(
        self,
        rec_texts: List[str],
        category: Optional[str] = None
    ) -> List[Dict]:
        """解析OCR结果并匹配标准库（一步到位）

        Args:
            rec_texts: OCR识别的文本列表
            category: 图片分类key（如 'blood_routine'），用于过滤标准库指标

        Returns:
            解析后的指标列表，包含匹配信息
        """
        if not rec_texts:
            logger.warning("OCR文本列表为空")
            return []

        # 过滤空文本
        valid_texts = [t for t in rec_texts if t and t.strip()]
        if not valid_texts:
            logger.warning("过滤后OCR文本列表为空")
            return []

        # 脱敏处理：移除手机号、身份证号等敏感信息
        desensitized_texts = [
            desensitization_service.desensitize_text(t) for t in valid_texts
        ]

        # 获取标准库指标
        standard_indicators = await self._get_standard_indicators(category)
        logger.info(f"标准库指标加载完成: category={category}, 数量={len(standard_indicators)}")

        if not standard_indicators:
            logger.warning("标准库指标为空，LLM将无法匹配任何指标")

        try:
            llm_service = get_openai_llm_service()

            rec_texts_json = json.dumps(desensitized_texts, ensure_ascii=False, indent=2)
            standard_indicators_json = json.dumps(standard_indicators, ensure_ascii=False, indent=2)

            user_prompt = self.USER_PROMPT_WITH_MATCHING_TEMPLATE.format(
                rec_texts_json=rec_texts_json,
                standard_indicators_json=standard_indicators_json
            )

            logger.info(f"开始LLM解析+匹配，文本行数: {len(valid_texts)}, 标准库指标数: {len(standard_indicators)}")

            # LLM 调用增加超时控制（120秒），避免无限等待
            import asyncio
            result = await asyncio.wait_for(
                llm_service.analyze(
                    system_prompt=self.SYSTEM_PROMPT_WITH_MATCHING,
                    user_prompt=user_prompt
                ),
                timeout=120.0
            )

            content = result.get('content', '')
            tokens_used = result.get('tokens_used', 0)

            # 解析JSON响应
            indicators = self._extract_json_with_matching(content)

            # 添加解析方法标记 + 类型转换
            for indicator in indicators:
                indicator['parse_method'] = 'llm'
                if indicator.get('matched_index_id'):
                    indicator['match_method'] = 'llm'
                    # [FIX] 确保 matched_index_id 是整数（LLM可能返回字符串）
                    try:
                        indicator['matched_index_id'] = int(indicator['matched_index_id'])
                    except (ValueError, TypeError) as e:
                        logger.warning(f"matched_index_id类型转换失败: {indicator.get('matched_index_id')} -> {e}, 置为None")
                        indicator['matched_index_id'] = None

            matched_count = sum(1 for ind in indicators if ind.get('matched_index_id'))
            logger.info(f"LLM解析+匹配完成，提取{len(indicators)}个指标，匹配{matched_count}个，tokens={tokens_used}")

            # 返回结果包含原始响应（用于调试）
            return {
                'indicators': indicators,
                'llm_raw_response': content
            }

        except asyncio.TimeoutError:
            logger.error(f"LLM解析+匹配超时(120s)，文本行数: {len(valid_texts)}, 标准库指标数: {len(standard_indicators)}")
            return {'indicators': [], 'llm_raw_response': ''}
        except Exception as e:
            logger.error(f"LLM解析+匹配失败: {e}", exc_info=True)
            return {'indicators': [], 'llm_raw_response': ''}

    async def _get_standard_indicators(self, category: Optional[str] = None) -> List[Dict]:
        """获取标准库指标列表

        Args:
            category: 图片分类key（如 'blood_routine'），用于过滤

        Returns:
            标准指标列表（精简字段）
        """
        global _STANDARD_INDICATORS_CACHE

        # 检查缓存
        cache_key = category or 'all'
        if cache_key in _STANDARD_INDICATORS_CACHE:
            logger.info(f"标准库命中缓存: cache_key={cache_key}, 数量={len(_STANDARD_INDICATORS_CACHE[cache_key])}")
            return _STANDARD_INDICATORS_CACHE[cache_key]

        try:
            from app.core.database import AsyncSessionLocal
            from app.models.medical import MedicalIndex
            from sqlalchemy import select, func

            async with AsyncSessionLocal() as db:

                query = select(MedicalIndex).where(MedicalIndex.is_active == True)

                # 使用 category 字符串过滤
                if category:
                    query = query.where(MedicalIndex.category == category)
                    logger.info(f"按category过滤: {category}")

                result = await db.execute(query)
                indicators = result.scalars().all()
                logger.info(f"category={category} 查询到 {len(indicators)} 条记录")

                # 如果 category 过滤结果为空，回退到全库查询
                if not indicators and category:
                    logger.warning(f"category={category} 无标准指标，回退到全库查询")
                    query = select(MedicalIndex).where(MedicalIndex.is_active == True)
                    result = await db.execute(query)
                    indicators = result.scalars().all()

                # 精简字段，只保留匹配所需的信息
                simplified = [
                    {
                        'index_id': ind.index_id,
                        'index_name': ind.index_name,
                        'index_code': ind.index_code,
                        'index_name_en': ind.index_name_en,
                        'index_unit': ind.index_unit,
                        'category': ind.category
                    }
                    for ind in indicators
                ]

                # 缓存结果
                _STANDARD_INDICATORS_CACHE[cache_key] = simplified
                logger.info(f"加载标准库指标: category={category}, 数量={len(simplified)}")

                return simplified

        except Exception as e:
            logger.error(f"获取标准库指标失败: {e}", exc_info=True)
            return []

    def _extract_json_with_matching(self, content: str) -> List[Dict]:
        """从LLM响应中提取带匹配信息的JSON数组"""
        indicators = self._extract_json(content)

        logger.info(f"_extract_json解析出 {len(indicators)} 个指标")

        # 确保每个指标都有匹配相关字段
        for i, ind in enumerate(indicators):
            if 'matched_index_id' not in ind:
                ind['matched_index_id'] = None
            if 'matched_name' not in ind:
                ind['matched_name'] = None
            if 'match_confidence' not in ind:
                ind['match_confidence'] = None

        return indicators

    @classmethod
    def clear_cache(cls):
        """清除标准库缓存"""
        global _STANDARD_INDICATORS_CACHE
        _STANDARD_INDICATORS_CACHE = {}
        logger.info("标准库缓存已清除")

    # ========== 新增：检查报告解析方法 ==========

    SYSTEM_PROMPT_EXAM = """你是一个专业的医疗检查报告解析专家。你的任务是从OCR识别的文本中提取检查报告的关键医学信息。

## 输入说明
你会收到一个JSON数组，包含OCR识别出的文本行。每行已经过行分组处理：同一行不同列的文本已用两个空格合并到同一行，不同行分开排列。

## 检查报告类型
支持以下类型的检查报告：
- 影像学检查：X光、CT、MRI、超声、PET-CT、核医学
- 功能检查：心电图、脑电图、肺功能
- 内镜检查：胃镜、肠镜、支气管镜等

## 提取规则
1. **检查类型**：识别检查的具体类型，如"胸部CT"、"腹部超声"、"胃镜"等
2. **检查所见**：提取检查中发现的异常或正常描述，这是最重要的部分
3. **诊断意见**：提取医生的诊断结论或建议
4. **关键发现**：提取重要的阳性发现，如肿块大小、位置、形态等

## 注意事项
- 保持专业术语的准确性
- 如果有具体的测量数值（如肿瘤大小），请准确提取
- 忽略医院名称、患者信息、医生签名等非医学内容

## 返回格式
返回严格的JSON对象格式：
{
    "report_title": "报告标题，如'胸部平扫+增强CT'、'盆腔MRI平扫'，取报告顶部的检查项目名称",
    "exam_type": "检查类型",
    "exam_findings": "检查所见（详细描述）",
    "diagnosis": "诊断意见",
    "key_findings": ["关键发现1", "关键发现2"],
    "abnormal": true/false
}"""

    USER_PROMPT_EXAM_TEMPLATE = """请从以下OCR识别的检查报告文本中提取关键医学信息：

文本行列表（JSON格式）：
{rec_texts_json}

请返回JSON格式的检查信息。"""

    async def parse_exam_report(
        self,
        rec_texts: List[str],
        category: Optional[str] = None
    ) -> Dict:
        """解析检查报告（影像、功能、内镜）

        Args:
            rec_texts: OCR识别的文本列表
            category: 图片分类key（如 'ct', 'mri', 'ultrasound'）

        Returns:
            解析后的检查信息，包含:
            - exam_type: 检查类型
            - exam_findings: 检查所见
            - diagnosis: 诊断意见
            - key_findings: 关键发现列表
            - abnormal: 是否异常
            - llm_raw_response: 原始LLM响应
        """
        if not rec_texts:
            logger.warning("OCR文本列表为空")
            return self._empty_exam_result()
        
        # 过滤空文本
        valid_texts = [t for t in rec_texts if t and t.strip()]
        if not valid_texts:
            logger.warning("过滤后OCR文本列表为空")
            return self._empty_exam_result()

        # 脱敏处理：移除手机号、身份证号等敏感信息
        desensitized_texts = [
            desensitization_service.desensitize_text(t) for t in valid_texts
        ]

        try:
            llm_service = get_openai_llm_service()

            user_prompt = self.USER_PROMPT_EXAM_TEMPLATE.format(
                rec_texts_json=json.dumps(desensitized_texts, ensure_ascii=False, indent=2)
            )
            
            logger.info(f"开始LLM解析检查报告，文本行数: {len(valid_texts)}")
            
            result = await llm_service.analyze(
                system_prompt=self.SYSTEM_PROMPT_EXAM,
                user_prompt=user_prompt
            )
            
            content = result.get('content', '')
            tokens_used = result.get('tokens_used', 0)
            
            # 解析JSON响应
            exam_info = self._extract_exam_json(content)
            exam_info['llm_raw_response'] = content
            
            logger.info(f"LLM解析检查报告成功，tokens={tokens_used}")
            
            return exam_info
            
        except Exception as e:
            logger.error(f"LLM解析检查报告失败: {e}", exc_info=True)
            return self._empty_exam_result()
    
    def _empty_exam_result(self) -> Dict:
        """返回空的检查结果"""
        return {
            'report_title': None,
            'exam_type': None,
            'exam_findings': None,
            'diagnosis': None,
            'key_findings': [],
            'abnormal': False,
            'llm_raw_response': None
        }
    
    def _extract_exam_json(self, content: str) -> Dict:
        """从LLM响应中提取检查报告JSON对象，使用统一解析器"""
        if not content:
            return self._empty_exam_result()

        result = parse_llm_json(content)
        if result is not None:
            return self._validate_exam_result(result)

        logger.warning("无法从LLM响应中提取有效JSON")
        return self._empty_exam_result()
    
    def _validate_exam_result(self, result: Dict) -> Dict:
        """验证并清理检查结果"""
        return {
            'report_title': self._clean_string(result.get('report_title')),
            'exam_type': self._clean_string(result.get('exam_type')),
            'exam_findings': self._clean_string(result.get('exam_findings')),
            'diagnosis': self._clean_string(result.get('diagnosis')),
            'key_findings': result.get('key_findings', []) if isinstance(result.get('key_findings'), list) else [],
            'abnormal': bool(result.get('abnormal', False)),
            'llm_raw_response': result.get('llm_raw_response')  # 保留原始响应
        }

    # ========== 新增：病理报告解析方法 ==========

    SYSTEM_PROMPT_PATHOLOGY = """你是一个专业的病理报告解析专家。你的任务是从OCR识别的文本中提取病理报告的关键医学信息。

## 输入说明
你会收到一个JSON数组，包含OCR识别出的文本行。每行已经过行分组处理：同一行不同列的文本已用两个空格合并到同一行，不同行分开排列。

## 病理报告类型
支持以下类型的病理报告：
- 活检病理：组织活检、穿刺活检
- 手术病理：肿瘤切除标本
- 细胞学检查：脱落细胞、穿刺涂片
- 免疫组化：免疫组织化学染色结果
- 分子病理：基因检测、分子分型

## 提取规则
1. **病理诊断**：提取最终的病理诊断结论，这是最重要的部分
2. **标本信息**：提取标本类型、取材部位
3. **组织学类型**：如果有肿瘤，提取组织学类型和分化程度
4. **肿瘤分期**：如果有的话，提取TNM分期信息
5. **免疫组化结果**：提取免疫组化标记物及其结果（阳性/阴性）
6. **基因检测结果**：如果报告中包含基因检测内容，提取每个检测基因的名称和完整的检测结论
7. **其他发现**：其他重要的病理发现（不包含基因检测内容，基因检测内容单独放入gene_testing）

## 注意事项
- 保持专业术语的准确性
- 准确提取诊断关键词，如"腺癌"、"鳞癌"、"良性"等
- 忽略医院名称、患者信息、医生签名等非医学内容
- 基因检测结果和免疫组化结果必须分开：免疫组化放入ihc_results，基因/分子检测放入gene_testing
- key_findings中不要包含基因检测内容，避免与gene_testing重复
- 基因检测的result字段必须逐字保留原始报告中的检测结论，不要自行概括或简化。例如报告写"变异频率0.92%"就不能只写"阳性"，报告写"p.G12D错义突变"就必须完整保留
- mutation_type和frequency如有原文则完整填写，如报告中无对应信息则设为null

## 返回格式
返回严格的JSON对象格式：
{
    "report_title": "报告标题，如'胃窦活检病理报告'、'肝脏穿刺病理报告'，取报告顶部的病理项目名称",
    "pathology_diagnosis": "病理诊断",
    "specimen_type": "标本类型",
    "histology_type": "组织学类型",
    "tumor_stage": "肿瘤分期（如TNM）",
    "ihc_results": {"标记物": "结果"},
    "gene_testing": {
        "test_items": [
            {"gene": "基因名称", "result": "原始检测结论（逐字保留，不可概括简化）", "mutation_type": "突变类型（原文有则填，无则null）", "frequency": "突变频率（原文有则填，无则null）"}
        ],
        "test_method": "检测方法（如NGS、PCR等，原文有则完整保留）",
        "interpretation": "结果解释或临床意义（原文有则完整保留，无则null）"
    },
    "key_findings": ["关键发现1", "关键发现2"],
    "malignant": true/false
}

如果没有基因检测内容，gene_testing设为null。"""

    USER_PROMPT_PATHOLOGY_TEMPLATE = """请从以下OCR识别的病理报告文本中提取关键医学信息：

文本行列表（JSON格式）：
{rec_texts_json}

请返回JSON格式的病理信息。"""

    async def parse_pathology_report(
        self,
        rec_texts: List[str],
        category: Optional[str] = None
    ) -> Dict:
        """解析病理报告

        Args:
            rec_texts: OCR识别的文本列表
            category: 图片分类key（如 'pathology', 'biopsy', 'cytology', 'other'）

        Returns:
            解析后的病理信息，包含:
            - pathology_diagnosis: 病理诊断
            - specimen_type: 标本类型
            - histology_type: 组织学类型
            - tumor_stage: 肿瘤分期
            - ihc_results: 免疫组化结果
            - key_findings: 关键发现列表
            - malignant: 是否恶性
            - llm_raw_response: 原始LLM响应
        """
        if not rec_texts:
            logger.warning("OCR文本列表为空")
            return self._empty_pathology_result()
        
        # 过滤空文本
        valid_texts = [t for t in rec_texts if t and t.strip()]
        if not valid_texts:
            logger.warning("过滤后OCR文本列表为空")
            return self._empty_pathology_result()

        # 脱敏处理：移除手机号、身份证号等敏感信息
        desensitized_texts = [
            desensitization_service.desensitize_text(t) for t in valid_texts
        ]

        try:
            llm_service = get_openai_llm_service()

            user_prompt = self.USER_PROMPT_PATHOLOGY_TEMPLATE.format(
                rec_texts_json=json.dumps(desensitized_texts, ensure_ascii=False, indent=2)
            )
            
            logger.info(f"开始LLM解析病理报告，文本行数: {len(valid_texts)}")
            
            result = await llm_service.analyze(
                system_prompt=self.SYSTEM_PROMPT_PATHOLOGY,
                user_prompt=user_prompt
            )
            
            content = result.get('content', '')
            tokens_used = result.get('tokens_used', 0)
            
            # 解析JSON响应
            pathology_info = self._extract_pathology_json(content)
            pathology_info['llm_raw_response'] = content
            
            logger.info(f"LLM解析病理报告成功，tokens={tokens_used}")
            
            return pathology_info
            
        except Exception as e:
            logger.error(f"LLM解析病理报告失败: {e}", exc_info=True)
            return self._empty_pathology_result()
    
    def _empty_pathology_result(self) -> Dict:
        """返回空的病理结果"""
        return {
            'report_title': None,
            'pathology_diagnosis': None,
            'specimen_type': None,
            'histology_type': None,
            'tumor_stage': None,
            'ihc_results': {},
            'key_findings': [],
            'gene_testing': None,
            'malignant': False,
            'llm_raw_response': None
        }
    
    def _extract_pathology_json(self, content: str) -> Dict:
        """从LLM响应中提取病理报告JSON对象，使用统一解析器"""
        if not content:
            return self._empty_pathology_result()

        result = parse_llm_json(content)
        if result is not None:
            return self._validate_pathology_result(result)

        logger.warning("无法从LLM响应中提取有效JSON")
        return self._empty_pathology_result()
    
    def _validate_pathology_result(self, result: Dict) -> Dict:
        """验证并清理病理结果"""
        gene_testing_raw = result.get('gene_testing')
        gene_testing = None
        if gene_testing_raw is not None and not isinstance(gene_testing_raw, dict):
            logger.warning(f"gene_testing 字段非预期类型: {type(gene_testing_raw).__name__}, 值: {str(gene_testing_raw)[:200]}")
        if isinstance(gene_testing_raw, dict):
            # 确保结构完整，缺失字段补默认值
            test_items = gene_testing_raw.get('test_items', [])
            if not isinstance(test_items, list):
                test_items = []
            # 规范化每个 test_item 的字段
            normalized_items = []
            for item in test_items:
                if not isinstance(item, dict):
                    continue
                normalized_items.append({
                    'gene': item.get('gene', ''),
                    'result': item.get('result', ''),
                    'mutation_type': item.get('mutation_type') or None,
                    'frequency': item.get('frequency') or None,
                })
            gene_testing = {
                'test_items': normalized_items,
                'test_method': gene_testing_raw.get('test_method') or None,
                'interpretation': gene_testing_raw.get('interpretation') or None,
            }

        return {
            'report_title': self._clean_string(result.get('report_title')),
            'pathology_diagnosis': self._clean_string(result.get('pathology_diagnosis')),
            'specimen_type': self._clean_string(result.get('specimen_type')),
            'histology_type': self._clean_string(result.get('histology_type')),
            'tumor_stage': self._clean_string(result.get('tumor_stage')),
            'ihc_results': result.get('ihc_results', {}) if isinstance(result.get('ihc_results'), dict) else {},
            'key_findings': result.get('key_findings', []) if isinstance(result.get('key_findings'), list) else [],
            'gene_testing': gene_testing,
            'malignant': bool(result.get('malignant', False)),
            'llm_raw_response': result.get('llm_raw_response')  # 保留原始响应
        }


# 报告类型分类映射
REPORT_TYPE_MAPPING = {
    # 检验类：血液检验
    'blood_routine': REPORT_TYPE_LAB,
    'blood_biochemistry': REPORT_TYPE_LAB,
    'coagulation': REPORT_TYPE_LAB,
    'tumor_markers': REPORT_TYPE_LAB,
    'immune': REPORT_TYPE_LAB,
    'infection': REPORT_TYPE_LAB,
    'hormone': REPORT_TYPE_LAB,
    'genetics': REPORT_TYPE_LAB,
    
    # 检验类：尿液检验
    'urine_routine': REPORT_TYPE_LAB,
    'urine_biochemistry': REPORT_TYPE_LAB,
    
    # 检验类：体液检验
    'stool': REPORT_TYPE_LAB,
    'sputum': REPORT_TYPE_LAB,
    
    # 检查类：影像学检查
    'xray': REPORT_TYPE_EXAM,
    'ct': REPORT_TYPE_EXAM,
    'mri': REPORT_TYPE_EXAM,
    'ultrasound': REPORT_TYPE_EXAM,
    'pet_ct': REPORT_TYPE_EXAM,
    'nuclear': REPORT_TYPE_EXAM,
    
    # 检查类：功能检查
    'ecg': REPORT_TYPE_EXAM,
    'eeg': REPORT_TYPE_EXAM,
    'pulmonary': REPORT_TYPE_EXAM,
    
    # 检查类：内镜检查
    'endoscopy': REPORT_TYPE_EXAM,
    'gastroscopy': REPORT_TYPE_EXAM,
    'colonoscopy': REPORT_TYPE_EXAM,
    
    # 病理类（包含其他）
    'pathology': REPORT_TYPE_PATHOLOGY,
    'biopsy': REPORT_TYPE_PATHOLOGY,
    'cytology': REPORT_TYPE_PATHOLOGY,
    'other': REPORT_TYPE_PATHOLOGY,
}


async def get_report_type(category: str, db=None) -> str:
    """根据分类key获取报告类型

    优先从数据库 image_category.report_type 查询，
    无 db 或查不到时回退到 REPORT_TYPE_MAPPING 硬编码字典。

    Args:
        category: 分类key
        db: 可选的 AsyncSession，传入时走数据库查询

    Returns:
        报告类型：lab/exam/pathology
    """
    if db is not None:
        try:
            from sqlalchemy import select
            from app.models.image_report import ImageCategory
            result = await db.execute(
                select(ImageCategory.report_type).where(ImageCategory.category_key == category)
            )
            report_type = result.scalar_one_or_none()
            if report_type:
                return report_type
        except Exception as e:
            logger.warning(f"get_report_type DB查询失败，回退字典: {e}")

    return REPORT_TYPE_MAPPING.get(category, REPORT_TYPE_PATHOLOGY)


# 全局单例实例
_llm_ocr_parser_instance: Optional[LLMOCRParser] = None


def get_llm_ocr_parser() -> LLMOCRParser:
    """获取LLM OCR解析器单例
    
    Returns:
        LLMOCRParser 实例
    """
    global _llm_ocr_parser_instance

    if _llm_ocr_parser_instance is None:
        _llm_ocr_parser_instance = LLMOCRParser()

    return _llm_ocr_parser_instance


# 便捷访问
llm_ocr_parser = LLMOCRParser()