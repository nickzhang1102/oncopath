"""LLM OCR解析器测试"""
import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.ocr.llm_ocr_parser import LLMOCRParser, llm_ocr_parser


class TestLLMOCRParser:
    """LLM OCR解析器测试"""

    @pytest.fixture
    def parser(self):
        """创建解析器实例"""
        return LLMOCRParser()

    @pytest.fixture
    def sample_ocr_texts(self):
        """示例OCR识别结果（表格格式）"""
        return [
            '*春香***岁',
            '申请科室：胰腺外科',
            '报告日期：2025-4-150:00:00',
            '项目明细',
            '项目名称',
            '结果/单位',
            '白细胞计数',
            '参考值：3.5-9.5*10^9/L',
            '9.5*10^9/L',
            '淋巴细胞%',
            '21.5%',
            '参考值：20.0-50.0%',
            '单核细胞%',
            '5.6%',
            '参考值：3.0-10%',
            '中性粒细胞%',
            '71.2%',
            '参考值：40-75%',
            '淋巴细胞数',
            '2.1*10^9/L',
            '参考值：1.1-3.2*10^9/L',
            '中性粒细胞数',
            '6.8*10^9/L',
            '↑',
            '参考值：1.8-6.3*10^9/L',
            '红细胞计数',
            '4.19*10^12/L',
            '参考值：3.8-5.1*10^12/L',
            '血红蛋白',
            '116g/l',
            '参考值：115-150g/l',
            '血小板计数',
            '205*10^9/L',
            '参考值：125-350*10^9/L',
        ]

    @pytest.fixture
    def sample_llm_response(self):
        """示例LLM响应"""
        return json.dumps([
            {"name": "白细胞计数", "value": "9.5", "unit": "*10^9/L", "reference": "3.5-9.5", "status": "normal"},
            {"name": "淋巴细胞%", "value": "21.5", "unit": "%", "reference": "20.0-50.0", "status": "normal"},
            {"name": "单核细胞%", "value": "5.6", "unit": "%", "reference": "3.0-10", "status": "normal"},
            {"name": "中性粒细胞%", "value": "71.2", "unit": "%", "reference": "40-75", "status": "normal"},
            {"name": "淋巴细胞数", "value": "2.1", "unit": "*10^9/L", "reference": "1.1-3.2", "status": "normal"},
            {"name": "中性粒细胞数", "value": "6.8", "unit": "*10^9/L", "reference": "1.8-6.3", "status": "high"},
            {"name": "红细胞计数", "value": "4.19", "unit": "*10^12/L", "reference": "3.8-5.1", "status": "normal"},
            {"name": "血红蛋白", "value": "116", "unit": "g/l", "reference": "115-150", "status": "normal"},
            {"name": "血小板计数", "value": "205", "unit": "*10^9/L", "reference": "125-350", "status": "normal"}
        ])

    def test_extract_json_direct(self, parser):
        """测试直接JSON提取"""
        json_str = '[{"name": "测试", "value": "1.0"}]'
        result = parser._extract_json(json_str)
        assert len(result) == 1
        assert result[0]['name'] == '测试'

    def test_extract_json_code_block(self, parser):
        """测试代码块中的JSON提取"""
        content = '''```json
[{"name": "白细胞计数", "value": "9.5"}]
```'''
        result = parser._extract_json(content)
        assert len(result) == 1
        assert result[0]['name'] == '白细胞计数'

    def test_extract_json_with_text(self, parser):
        """测试混合文本中的JSON提取"""
        content = '''这是解析结果：
[{"name": "血红蛋白", "value": "116"}]
以上是结果。'''
        result = parser._extract_json(content)
        assert len(result) == 1
        assert result[0]['name'] == '血红蛋白'

    def test_validate_indicators(self, parser):
        """测试指标验证"""
        raw_indicators = [
            {"name": "白细胞计数", "value": "9.5", "unit": "*10^9/L", "reference": "3.5-9.5", "status": "normal"},
            {"name": "", "value": "1.0"},  # 无名称，应被过滤
            {"name": "血红蛋白", "value": 116, "unit": "g/L"},  # 数值类型
            {"name": "异常指标", "value": "10.5", "status": "high"},
        ]
        
        result = parser._validate_indicators(raw_indicators)
        
        assert len(result) == 3  # 过滤掉无名称的
        assert result[0]['name'] == '白细胞计数'
        assert result[1]['value'] == '116'  # 数值转换为字符串
        assert result[2]['status'] == 'high'

    def test_clean_value(self, parser):
        """测试数值清理"""
        assert parser._clean_value("9.5*10^9/L") == "9.5"
        assert parser._clean_value("116") == "116"
        assert parser._clean_value(116) == "116"
        assert parser._clean_value(3.14) == "3.14"
        assert parser._clean_value(None) is None
        assert parser._clean_value("") is None

    def test_normalize_status(self, parser):
        """测试状态标准化"""
        assert parser._normalize_status('high') == 'high'
        assert parser._normalize_status('高') == 'high'
        assert parser._normalize_status('偏高') == 'high'
        assert parser._normalize_status('↑') == 'high'
        
        assert parser._normalize_status('low') == 'low'
        assert parser._normalize_status('低') == 'low'
        assert parser._normalize_status('↓') == 'low'
        
        assert parser._normalize_status('normal') == 'normal'
        assert parser._normalize_status('正常') == 'normal'
        assert parser._normalize_status(None) == 'normal'
        assert parser._normalize_status('') == 'normal'

    @pytest.mark.asyncio
    async def test_parse_ocr_results_empty(self, parser):
        """测试空输入"""
        result = await parser.parse_ocr_results([])
        assert result == []
        
        result = await parser.parse_ocr_results(['', '  ', None])
        assert result == []

    @pytest.mark.asyncio
    async def test_parse_ocr_results_with_llm(self, parser, sample_ocr_texts, sample_llm_response):
        """测试LLM解析（Mock）"""
        with patch('app.services.ocr.llm_ocr_parser.get_openai_llm_service') as mock_get_service:
            # Mock OpenAI兼容LLM服务
            mock_service = MagicMock()
            mock_service.analyze = AsyncMock(return_value={
                'content': sample_llm_response,
                'tokens_used': 500
            })
            mock_get_service.return_value = mock_service
            
            result = await parser.parse_ocr_results(sample_ocr_texts)
            
            assert len(result) == 9
            assert result[0]['name'] == '白细胞计数'
            assert result[0]['value'] == '9.5'
            assert result[0]['confidence'] == 0.95
            assert result[0]['parse_method'] == 'llm'
            assert result[5]['name'] == '中性粒细胞数'
            assert result[5]['status'] == 'high'

    @pytest.mark.asyncio
    async def test_parse_ocr_results_llm_failure(self, parser, sample_ocr_texts):
        """测试LLM解析失败时的处理"""
        with patch('app.services.ocr.llm_ocr_parser.get_openai_llm_service') as mock_get_service:
            # Mock OpenAI兼容LLM服务抛出异常
            mock_service = MagicMock()
            mock_service.analyze = AsyncMock(side_effect=Exception("API Error"))
            mock_get_service.return_value = mock_service
            
            result = await parser.parse_ocr_results(sample_ocr_texts)
            
            # 应返回空列表而不是抛出异常
            assert result == []


class TestLLMOCRParserIntegration:
    """LLM OCR解析器集成测试（需要实际API）"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_real_parse(self):
        """真实API调用测试（标记为integration，默认跳过）"""
        # 这个测试需要真实的API配置
        # 运行时使用: pytest -m integration
        parser = LLMOCRParser()
        
        sample_texts = [
            '白细胞计数',
            '9.5*10^9/L',
            '参考值：3.5-9.5*10^9/L',
            '血红蛋白',
            '116g/l',
            '参考值：115-150g/l'
        ]
        
        result = await parser.parse_ocr_results(sample_texts)
        
        # 验证返回结构
        assert isinstance(result, list)
        if len(result) > 0:
            assert 'name' in result[0]
            assert 'value' in result[0]


class TestExamReportParser:
    """检查报告解析测试"""

    @pytest.fixture
    def parser(self):
        """创建解析器实例"""
        return LLMOCRParser()

    @pytest.fixture
    def sample_ct_ocr_texts(self):
        """示例CT报告OCR识别结果"""
        return [
            '检查类型：胸部CT平扫',
            '检查所见：',
            '双肺纹理清晰，右肺上叶可见结节影，直径约8mm',
            '纵隔居中，气管通畅',
            '诊断意见：',
            '右肺上叶结节，建议随访复查',
        ]

    @pytest.fixture
    def sample_exam_llm_response(self):
        """示例检查报告LLM响应"""
        return '''```json
{
    "exam_type": "胸部CT平扫",
    "exam_findings": "双肺纹理清晰，右肺上叶可见结节影，直径约8mm。纵隔居中，气管通畅。",
    "diagnosis": "右肺上叶结节，建议随访复查",
    "key_findings": ["右肺上叶结节，直径约8mm"],
    "abnormal": true
}
```'''

    def test_empty_exam_result(self, parser):
        """测试空检查结果"""
        result = parser._empty_exam_result()
        assert result['exam_type'] is None
        assert result['exam_findings'] is None
        assert result['diagnosis'] is None
        assert result['key_findings'] == []
        assert result['abnormal'] is False

    def test_extract_exam_json(self, parser, sample_exam_llm_response):
        """测试检查报告JSON提取"""
        result = parser._extract_exam_json(sample_exam_llm_response)
        assert result['exam_type'] == '胸部CT平扫'
        assert '结节' in result['exam_findings']
        assert result['abnormal'] is True

    def test_validate_exam_result(self, parser):
        """测试检查结果验证"""
        raw_result = {
            'exam_type': '胸部CT',
            'exam_findings': '检查所见内容',
            'diagnosis': '诊断意见',
            'key_findings': ['发现1', '发现2'],
            'abnormal': True
        }
        result = parser._validate_exam_result(raw_result)
        assert result['exam_type'] == '胸部CT'
        assert len(result['key_findings']) == 2

    @pytest.mark.asyncio
    async def test_parse_exam_report_empty(self, parser):
        """测试空输入的检查报告解析"""
        result = await parser.parse_exam_report([])
        assert result == parser._empty_exam_result()

    @pytest.mark.asyncio
    async def test_parse_exam_report_with_llm(self, parser, sample_ct_ocr_texts, sample_exam_llm_response):
        """测试检查报告LLM解析（Mock）"""
        with patch('app.services.ocr.llm_ocr_parser.get_openai_llm_service') as mock_get_service:
            mock_service = MagicMock()
            mock_service.analyze = AsyncMock(return_value={
                'content': sample_exam_llm_response,
                'tokens_used': 300
            })
            mock_get_service.return_value = mock_service
            
            result = await parser.parse_exam_report(sample_ct_ocr_texts)
            
            assert result['exam_type'] == '胸部CT平扫'
            assert result['abnormal'] is True
            assert '结节' in result['exam_findings']


class TestPathologyReportParser:
    """病理报告解析测试"""

    @pytest.fixture
    def parser(self):
        """创建解析器实例"""
        return LLMOCRParser()

    @pytest.fixture
    def sample_pathology_ocr_texts(self):
        """示例病理报告OCR识别结果"""
        return [
            '病理诊断：',
            '（右肺上叶）腺癌，中分化',
            '肿瘤大小：2.5cm x 2.0cm x 1.5cm',
            '免疫组化：',
            'TTF-1(+)，NapsinA(+)，Ki-67约30%',
            'pTNM分期：T1cN0M0',
        ]

    @pytest.fixture
    def sample_pathology_llm_response(self):
        """示例病理报告LLM响应"""
        return '''```json
{
    "pathology_diagnosis": "（右肺上叶）腺癌，中分化",
    "specimen_type": "肺组织活检",
    "histology_type": "腺癌，中分化",
    "tumor_stage": "T1cN0M0",
    "ihc_results": {"TTF-1": "阳性", "NapsinA": "阳性", "Ki-67": "约30%"},
    "key_findings": ["腺癌，中分化", "肿瘤大小2.5cm"],
    "malignant": true
}
```'''

    def test_empty_pathology_result(self, parser):
        """测试空病理结果"""
        result = parser._empty_pathology_result()
        assert result['pathology_diagnosis'] is None
        assert result['specimen_type'] is None
        assert result['ihc_results'] == {}
        assert result['malignant'] is False

    def test_extract_pathology_json(self, parser, sample_pathology_llm_response):
        """测试病理报告JSON提取"""
        result = parser._extract_pathology_json(sample_pathology_llm_response)
        assert '腺癌' in result['pathology_diagnosis']
        assert result['malignant'] is True
        assert 'TTF-1' in result['ihc_results']

    def test_validate_pathology_result(self, parser):
        """测试病理结果验证"""
        raw_result = {
            'pathology_diagnosis': '腺癌',
            'specimen_type': '肺组织',
            'histology_type': '腺癌，中分化',
            'tumor_stage': 'T1cN0M0',
            'ihc_results': {'TTF-1': '阳性'},
            'key_findings': ['发现1'],
            'malignant': True
        }
        result = parser._validate_pathology_result(raw_result)
        assert result['pathology_diagnosis'] == '腺癌'
        assert result['malignant'] is True

    @pytest.mark.asyncio
    async def test_parse_pathology_report_empty(self, parser):
        """测试空输入的病理报告解析"""
        result = await parser.parse_pathology_report([])
        assert result == parser._empty_pathology_result()

    @pytest.mark.asyncio
    async def test_parse_pathology_report_with_llm(self, parser, sample_pathology_ocr_texts, sample_pathology_llm_response):
        """测试病理报告LLM解析（Mock）"""
        with patch('app.services.ocr.llm_ocr_parser.get_openai_llm_service') as mock_get_service:
            mock_service = MagicMock()
            mock_service.analyze = AsyncMock(return_value={
                'content': sample_pathology_llm_response,
                'tokens_used': 400
            })
            mock_get_service.return_value = mock_service
            
            result = await parser.parse_pathology_report(sample_pathology_ocr_texts)
            
            assert '腺癌' in result['pathology_diagnosis']
            assert result['malignant'] is True


class TestReportTypeMapping:
    """报告类型映射测试"""

    @pytest.mark.asyncio
    async def test_lab_type_mapping(self):
        """测试检验类映射"""
        from app.services.ocr.llm_ocr_parser import get_report_type, REPORT_TYPE_LAB

        assert await get_report_type('blood_routine') == REPORT_TYPE_LAB
        assert await get_report_type('blood_biochemistry') == REPORT_TYPE_LAB
        assert await get_report_type('tumor_markers') == REPORT_TYPE_LAB
        assert await get_report_type('urine_routine') == REPORT_TYPE_LAB
        assert await get_report_type('stool') == REPORT_TYPE_LAB

    @pytest.mark.asyncio
    async def test_exam_type_mapping(self):
        """测试检查类映射"""
        from app.services.ocr.llm_ocr_parser import get_report_type, REPORT_TYPE_EXAM

        assert await get_report_type('ct') == REPORT_TYPE_EXAM
        assert await get_report_type('mri') == REPORT_TYPE_EXAM
        assert await get_report_type('ultrasound') == REPORT_TYPE_EXAM
        assert await get_report_type('ecg') == REPORT_TYPE_EXAM
        assert await get_report_type('gastroscopy') == REPORT_TYPE_EXAM

    @pytest.mark.asyncio
    async def test_pathology_type_mapping(self):
        """测试病理类映射"""
        from app.services.ocr.llm_ocr_parser import get_report_type, REPORT_TYPE_PATHOLOGY

        assert await get_report_type('pathology') == REPORT_TYPE_PATHOLOGY
        assert await get_report_type('biopsy') == REPORT_TYPE_PATHOLOGY
        assert await get_report_type('cytology') == REPORT_TYPE_PATHOLOGY
        assert await get_report_type('other') == REPORT_TYPE_PATHOLOGY

    @pytest.mark.asyncio
    async def test_unknown_type_defaults_to_pathology(self):
        """测试未知类型默认为病理类"""
        from app.services.ocr.llm_ocr_parser import get_report_type, REPORT_TYPE_PATHOLOGY

        assert await get_report_type('unknown_category') == REPORT_TYPE_PATHOLOGY
        assert await get_report_type('') == REPORT_TYPE_PATHOLOGY
