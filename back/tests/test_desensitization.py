import pytest
from app.services.desensitization import DesensitizationService

class TestDesensitizationService:
    def test_mask_name(self):
        assert DesensitizationService.mask_name("张三") == "张*"
        assert DesensitizationService.mask_name("张三丰") == "张**"
        assert DesensitizationService.mask_name("张") == "张*"
        assert DesensitizationService.mask_name("") == ""

    def test_mask_phone(self):
        assert DesensitizationService.mask_phone("13812345678") == "138****5678"
        assert DesensitizationService.mask_phone("138123") == "138123"
        assert DesensitizationService.mask_phone("") == ""

    def test_mask_id_card(self):
        # 18位身份证：前3位 + 11个* + 后4位
        assert DesensitizationService.mask_id_card("110101199001011234") == "110***********1234"
        assert DesensitizationService.mask_id_card("123456") == "123456"

    def test_mask_email(self):
        # 邮箱：前2位 + (len-2)个* + @domain
        # zhangsan有8个字符，所以是 zh + 6个* = zh******
        assert DesensitizationService.mask_email("zhangsan@qq.com") == "zh******@qq.com"
        assert DesensitizationService.mask_email("zs@qq.com") == "zs*@qq.com"

    def test_desensitize_text(self):
        text = "联系人: 张三, 电话: 13812345678, 邮箱: zhangsan@qq.com"
        result = DesensitizationService.desensitize_text(text)
        assert "138****5678" in result
        # zhangsan有8个字符，脱敏后为zh******
        assert "zh******@qq.com" in result
