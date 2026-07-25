from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict
from typing import Optional
from datetime import datetime
import re

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=128)
    phone: Optional[str] = Field(None, max_length=20)
    account_name: Optional[str] = Field(None, max_length=100)

    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        """用户名只允许字母、数字、下划线"""
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('用户名只能包含字母、数字和下划线')
        return v

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        """密码长度至少6位"""
        if len(v) < 6:
            raise ValueError('密码长度至少6位')
        return v

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v):
        """手机号格式验证"""
        if v is not None:
            if not re.match(r'^1[3-9]\d{9}$', v):
                raise ValueError('手机号格式不正确')
        return v

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    account_id: int
    username: str
    phone: Optional[str]
    account_name: Optional[str]
    account_type: str
    status: str
    wechat_nickname: Optional[str]
    wechat_avatar: Optional[str]
    # 隐私设置
    data_sharing_enabled: bool = True
    notification_enabled: bool = True
    email_notification: bool = False
    sms_notification: bool = False
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class TokenPayload(BaseModel):
    sub: int  # account_id
    exp: datetime
    type: str  # access or refresh

class WechatAuthResponse(BaseModel):
    auth_url: str

class WechatLoginRequest(BaseModel):
    code: str

class WechatBindRequest(BaseModel):
    code: str

class UserProfileUpdate(BaseModel):
    """用户资料更新"""
    account_name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)


class ForgotPasswordRequest(BaseModel):
    """忘记密码请求"""
    username: str = Field(..., min_length=1, max_length=50)


class ResetPasswordRequest(BaseModel):
    """重置密码请求"""
    username: str = Field(..., min_length=1, max_length=50)
    reset_token: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6, max_length=128)

    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v):
        """新密码长度至少6位"""
        if len(v) < 6:
            raise ValueError('密码长度至少6位')
        return v


class PasswordChangeRequest(BaseModel):
    """修改密码请求（已登录用户）"""
    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6, max_length=128)

    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v):
        """新密码长度至少6位"""
        if len(v) < 6:
            raise ValueError('密码长度至少6位')
        return v


class PrivacySettings(BaseModel):
    """隐私设置"""
    data_sharing_enabled: bool = Field(default=True)
    notification_enabled: bool = Field(default=True)
    email_notification: bool = Field(default=False)
    sms_notification: bool = Field(default=False)


class PrivacySettingsUpdate(BaseModel):
    """隐私设置更新"""
    data_sharing_enabled: Optional[bool] = None
    notification_enabled: Optional[bool] = None
    email_notification: Optional[bool] = None
    sms_notification: Optional[bool] = None


class NotificationResponse(BaseModel):
    """通知响应"""
    notification_id: int
    type: str
    title: str
    content: Optional[str]
    is_read: bool
    extra_data: Optional[dict]
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )


class NotificationListResponse(BaseModel):
    """通知列表响应"""
    items: list[NotificationResponse]
    total: int
    unread_count: int
    page: int
    limit: int


class NotificationCreate(BaseModel):
    """创建通知"""
    type: str = Field(..., pattern=r'^(system|consultation|report|reminder)$')
    title: str = Field(..., max_length=200)
    content: Optional[str] = None
    extra_data: Optional[dict] = None


# ===== Admin 用户管理 Schemas =====

class AdminUserItem(BaseModel):
    """管理端用户列表条目"""
    account_id: int
    username: str
    account_name: Optional[str] = None
    account_type: str
    status: str
    phone: Optional[str] = None
    created_at: datetime
    patient_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class AdminUserDetail(AdminUserItem):
    """管理端用户详情"""
    email: Optional[str] = None
    last_login_at: Optional[datetime] = None


class AdminUserStatusUpdate(BaseModel):
    """管理端用户启禁用"""
    status: str = Field(..., pattern=r'^(active|inactive)$')


class AdminPasswordReset(BaseModel):
    """管理端重置用户密码"""
    new_password: str = Field(..., min_length=6, max_length=128)
