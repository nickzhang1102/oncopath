# 模型初始化文件
from app.core.database import Base

# 导入所有模型以便Alembic识别
from app.models.user import LoginAccount, WechatBinding
from app.models.patient import Patient
from app.models.medical import (
    MedicalIndex, MedicalCheck, MedicalCheckDetail,
    MedicalExam, PathologyReport, UserFavoriteIndex, MedicalRecord,
    UserIndexGroup
)
from app.models.conversation import (
    Conversation, ConsultationExternalSession, Message, LeaderSession, LeaderMessage,
    LeaderAgentResult, LeaderFinalReport,
)
from app.models.timeline import TimelineEvent
from app.models.image_report import ImageReport, ImageCategory
from app.models.ocr_review_log import OCRReviewLog
from app.models.medication import Medication
from app.models.follow_up import FollowUpReminder
from app.models.notification import Notification
from app.models.prompt import PromptConfig
# 知识库模型
from app.models.knowledge import (
    KnowledgeCategory, KnowledgeDocument, KnowledgeAccessLog,
    KnowledgeConfig
)
from app.models.medication_log import MedicationLog
from app.models.share_token import ShareToken
from app.models.admin import LLMConfig, AgentTeamsIntegrationConfig
from app.models.record_summary import RecordSummary

__all__ = [
    "Base",
    # 用户
    "LoginAccount",
    "WechatBinding",
    # 患者
    "Patient",
    # 医疗
    "MedicalIndex",
    "MedicalCheck",
    "MedicalCheckDetail",
    "MedicalExam",
    "PathologyReport",
    "UserFavoriteIndex",
    "MedicalRecord",
    # 会诊（对齐 claudechat）
    "Conversation",
    "ConsultationExternalSession",
    "Message",
    "LeaderSession",
    "LeaderMessage",
    "LeaderAgentResult",
    "LeaderFinalReport",
    # 时间线
    "TimelineEvent",
    # 上传报告
    "ImageReport",
    "ImageCategory",
    # 通知
    "Notification",
    # 知识库
    "KnowledgeCategory",
    "KnowledgeDocument",
    "KnowledgeAccessLog",
    "KnowledgeConfig",
    # 提示词配置
    "PromptConfig",
    # OCR审查日志
    "OCRReviewLog",
    # 用药记录
    "Medication",
    # 随访提醒
    "FollowUpReminder",
    # 服药记录
    "MedicationLog",
    # 分享
    "ShareToken",
    # Admin
    "LLMConfig",
    "AgentTeamsIntegrationConfig",
    # 记录概要
    "RecordSummary",
]
