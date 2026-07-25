"""会诊服务测试

测试会诊功能的核心组件：
1. LLM服务
2. 医疗提示词构建
3. 专家配置
"""

import pytest

from app.services.llm_service import LLMService
from app.services.consultation.medical_prompt_builder import MedicalPromptBuilder
from app.config.medical_experts import MEDICAL_EXPERTS, get_expert_by_type


# ========== 测试 Claude 服务 ==========

class TestClaudeService:
    """测试Claude API服务"""

    def test_initialization_without_api_key(self):
        """测试无API密钥时的初始化"""
        service = LLMService()
        assert service.client is None
        assert service._initialized is False

    @pytest.mark.asyncio
    async def test_chat_without_client(self):
        """测试未初始化客户端时的调用"""
        service = LLMService()
        service._initialized = True

        with pytest.raises(RuntimeError, match="LLM服务未初始化"):
            await service.chat(
                system_prompt="你是一个助手",
                user_message="你好"
            )

    @pytest.mark.asyncio
    async def test_stream_chat_without_client(self):
        """测试未初始化客户端时的流式调用"""
        service = LLMService()
        service._initialized = True

        with pytest.raises(RuntimeError, match="LLM服务未初始化"):
            async for _ in service.stream_chat(
                system_prompt="你是一个助手",
                user_message="你好"
            ):
                pass


# ========== 测试医疗提示词构建器 ==========

class TestMedicalPromptBuilder:
    """测试医疗提示词构建"""

    def setup_method(self):
        self.builder = MedicalPromptBuilder()

    def test_calculate_age(self):
        """测试年龄计算"""
        from datetime import date
        birth_date = date(1990, 1, 1)
        age = self.builder._calculate_age(birth_date)
        assert "岁" in age

    def test_calculate_age_none(self):
        """测试空出生日期"""
        age = self.builder._calculate_age(None)
        assert age == "未知"

# ========== 测试专家配置 ==========

class TestMedicalExpertsConfig:
    """测试医疗专家配置"""

    def test_get_expert_by_type(self):
        """测试根据类型获取专家"""
        expert = get_expert_by_type("oncology")

        assert expert is not None
        assert expert["expert_name"] == "肿瘤科专家"
        assert "system_prompt" in expert
        assert "keywords" in expert

    def test_get_expert_by_type_not_found(self):
        """测试获取不存在的专家类型"""
        expert = get_expert_by_type("unknown")
        assert expert is None

    def test_all_experts_have_required_fields(self):
        """测试所有专家配置完整性"""
        for expert_name, config in MEDICAL_EXPERTS.items():
            assert "expert_type" in config
            assert "system_prompt" in config
            assert "keywords" in config
            assert "priority" in config
            assert isinstance(config["keywords"], list)
            assert len(config["keywords"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
