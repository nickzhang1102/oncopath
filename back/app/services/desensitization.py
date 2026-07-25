import re
from typing import Optional

class DesensitizationService:
    """数据脱敏服务"""

    @staticmethod
    def mask_name(name: str) -> str:
        """姓名脱敏: 张三 -> 张**"""
        if not name:
            return ""
        if len(name) <= 1:
            return name + "*"
        return name[0] + "*" * (len(name) - 1)

    @staticmethod
    def mask_phone(phone: str) -> str:
        """手机号脱敏: 13812345678 -> 138****5678"""
        if not phone or len(phone) < 7:
            return phone
        return phone[:3] + "****" + phone[-4:]

    @staticmethod
    def mask_id_card(id_card: str) -> str:
        """身份证号脱敏: 110101199001011234 -> 110**********1234"""
        if not id_card or len(id_card) < 8:
            return id_card
        return id_card[:3] + "*" * (len(id_card) - 7) + id_card[-4:]

    @staticmethod
    def mask_email(email: str) -> str:
        """邮箱脱敏: zhangsan@qq.com -> zh****@qq.com"""
        if not email or "@" not in email:
            return email
        local, domain = email.split("@", 1)
        if len(local) <= 2:
            masked_local = local + "*"
        else:
            masked_local = local[:2] + "*" * (len(local) - 2)
        return f"{masked_local}@{domain}"

    @staticmethod
    def mask_medical_record_number(mr_number: str) -> str:
        """病历号脱敏: 2024001234 -> ****0234"""
        if not mr_number or len(mr_number) < 4:
            return mr_number
        return "****" + mr_number[-4:]

    @classmethod
    def desensitize_text(cls, text: str, sensitive_patterns: Optional[list] = None) -> str:
        """对文本内容进行脱敏"""
        if not text:
            return text

        result = text

        # 默认敏感模式
        default_patterns = [
            (r'\b1[3-9]\d{9}\b', lambda m: cls.mask_phone(m.group())),  # 手机号
            (r'\b\d{17}[\dXx]\b', lambda m: cls.mask_id_card(m.group())),  # 身份证号
            (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', lambda m: cls.mask_email(m.group())),  # 邮箱
        ]

        patterns = sensitive_patterns or default_patterns

        for pattern, replacer in patterns:
            result = re.sub(pattern, replacer, result)

        return result

# 全局实例
desensitization_service = DesensitizationService()
