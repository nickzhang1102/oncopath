from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.utils.time_utils import get_utc_now


class LoginAccount(Base):
    """登录账号表"""
    __tablename__ = "login_account"

    account_id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, comment="用户名")
    password = Column(String(255), nullable=False, comment="密码哈希")
    phone = Column(String(20), nullable=True, comment="手机号")
    account_name = Column(String(100), nullable=True, comment="账号显示名称")
    account_type = Column(String(20), default="user", comment="账号类型: admin/user")
    status = Column(String(20), default="active", comment="状态: active/inactive")
    wechat_nickname = Column(String(100), nullable=True, comment="微信昵称")
    wechat_avatar = Column(String(255), nullable=True, comment="微信头像URL")
    # 隐私设置
    data_sharing_enabled = Column(Boolean, default=True, comment="是否允许数据分享")
    notification_enabled = Column(Boolean, default=True, comment="是否接收系统通知")
    email_notification = Column(Boolean, default=False, comment="是否接收邮件通知")
    sms_notification = Column(Boolean, default=False, comment="是否接收短信通知")
    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    # 关系
    patients = relationship("Patient", back_populates="account", cascade="all, delete-orphan")
    wechat_binding = relationship("WechatBinding", back_populates="account", uselist=False, cascade="all, delete-orphan")
    conversations_v2 = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    prompt_configs = relationship("PromptConfig", back_populates="account", cascade="all, delete-orphan")
    medications = relationship("Medication", back_populates="account", cascade="all, delete-orphan")
    follow_up_reminders = relationship("FollowUpReminder", back_populates="account", cascade="all, delete-orphan")
    image_reports = relationship("ImageReport", back_populates="account", cascade="all, delete-orphan")
    medication_logs = relationship("MedicationLog", back_populates="account", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="account", cascade="all, delete-orphan")


class WechatBinding(Base):
    """微信绑定表"""
    __tablename__ = "wechat_binding"

    binding_id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("login_account.account_id"), nullable=False)
    openid = Column(String(100), unique=True, nullable=False, comment="微信OpenID")
    unionid = Column(String(100), nullable=True, comment="微信UnionID")
    nickname = Column(String(100), nullable=True)
    avatar_url = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    # 关系
    account = relationship("LoginAccount", back_populates="wechat_binding")
