"""分享 Token 模型 - 用于报告分享功能"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON

from app.core.database import Base
from app.utils.time_utils import get_utc_now


class ShareToken(Base):
    """分享令牌表"""
    __tablename__ = "share_token"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(64), unique=True, nullable=False, index=True, comment="分享令牌")
    account_id = Column(Integer, ForeignKey("login_account.account_id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patient.patient_id"), nullable=False)

    # 分享内容类型: check_report(检验报告), exam_report(检查报告), pathology_report(病理报告)
    content_type = Column(String(30), nullable=False, comment="分享内容类型")
    content_id = Column(Integer, nullable=False, comment="内容ID")

    # 限制
    max_access_count = Column(Integer, default=10, comment="最大访问次数")
    current_access_count = Column(Integer, default=0, comment="当前访问次数")
    expire_hours = Column(Integer, default=72, comment="有效期(小时)")
    expire_at = Column(DateTime, nullable=True, comment="过期时间（冗余字段，避免每次计算）")

    created_at = Column(DateTime, default=get_utc_now)