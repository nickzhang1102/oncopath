"""AgentTeams conversation mapping and legacy consultation persistence.

Legacy Leader records remain readable for historical sharing and deletable for
data-retention workflows. New consultation execution is delegated to AgentTeams.
"""
import logging
import secrets
from typing import Optional, List, Tuple
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, and_, desc, delete as sa_delete
from sqlalchemy.orm import selectinload

from app.models.conversation import (
    Conversation, ConsultationExternalSession, Message, LeaderSession, LeaderMessage,
    LeaderAgentResult, LeaderFinalReport,
)
from app.models.agentteams_launch_intent import AgentTeamsLaunchIntent
from app.utils.time_utils import get_utc_now

logger = logging.getLogger(__name__)


class ConversationService:
    """会诊对话服务 — 数据持久化层"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ===== Conversation CRUD =====

    async def create_conversation(
        self, user_id: int, patient_id: int, title: Optional[str] = None
    ) -> Conversation:
        """创建会诊对话"""
        share_token = await self._generate_unique_share_token()
        conversation = Conversation(
            user_id=user_id,
            patient_id=patient_id,
            title=title or "虚拟会诊",
            share_token=share_token,
            status="new",
            category="medical",
        )
        self.db.add(conversation)
        await self.db.flush()
        return conversation

    async def get_conversations(
        self,
        user_id: int,
        patient_id: Optional[int] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[Conversation], int]:
        """获取用户或指定患者的 AgentTeams 会诊历史。"""
        filters = [
            Conversation.user_id == user_id,
            ConsultationExternalSession.provider == "agentteams",
        ]
        if patient_id is not None:
            filters.append(Conversation.patient_id == patient_id)
        base_filter = and_(*filters)
        # 总数
        count_result = await self.db.execute(
            select(func.count(Conversation.id))
            .join(
                ConsultationExternalSession,
                ConsultationExternalSession.conversation_id == Conversation.id,
            )
            .where(base_filter)
        )
        total = count_result.scalar() or 0

        # 列表
        result = await self.db.execute(
            select(Conversation, ConsultationExternalSession)
            .join(
                ConsultationExternalSession,
                ConsultationExternalSession.conversation_id == Conversation.id,
            )
            .where(base_filter)
            .order_by(desc(Conversation.updated_at))
            .limit(limit)
            .offset(offset)
        )
        conversations = []
        for conversation, external_session in result.all():
            conversation.provider = external_session.provider
            conversation.external_session_status = external_session.status
            conversations.append(conversation)
        return conversations, total

    async def get_conversation_by_id(self, conversation_id: int) -> Optional[Conversation]:
        """按 ID 获取对话"""
        result = await self.db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        return result.scalar_one_or_none()

    async def get_conversation_by_token(self, share_token: str) -> Optional[Conversation]:
        """按 share_token 获取对话"""
        result = await self.db.execute(
            select(Conversation).where(Conversation.share_token == share_token)
        )
        return result.scalar_one_or_none()

    async def delete_conversation(self, conversation_id: int, user_id: int) -> bool:
        """删除对话（仅限本人）— 手动级联删除关联数据

        数据库外键为 NO ACTION，需按依赖顺序手动删除：
        1. 外部会话映射 (依赖 conversation_id)
        2. LeaderMessage (依赖 leader_session_id)
        3. LeaderAgentResult (依赖 leader_session_id)
        4. LeaderFinalReport (依赖 leader_session_id)
        5. LeaderSession (依赖 conversation_id)
        6. Message (依赖 conversation_id)
        7. Conversation (主表)
        """
        result = await self.db.execute(
            select(Conversation).where(
                and_(
                    Conversation.id == conversation_id,
                    Conversation.user_id == user_id,
                )
            )
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            return False

        unresolved_result = await self.db.execute(
            select(AgentTeamsLaunchIntent.status).where(
                AgentTeamsLaunchIntent.conversation_id == conversation_id,
                AgentTeamsLaunchIntent.status.in_(AgentTeamsLaunchIntent.UNRESOLVED_STATUSES),
            )
        )
        unresolved_status = unresolved_result.scalar_one_or_none()
        if unresolved_status is not None:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "agentteams_launch_pending",
                    "message": "会诊启动结果尚未确认，暂不能删除本地记录",
                },
            )

        # 1. 删除外部会话映射
        await self.db.execute(
            sa_delete(ConsultationExternalSession).where(
                ConsultationExternalSession.conversation_id == conversation_id
            )
        )

        # 查询关联的 LeaderSession IDs
        ls_result = await self.db.execute(
            select(LeaderSession.id).where(
                LeaderSession.conversation_id == conversation_id
            )
        )
        session_ids = [row[0] for row in ls_result.all()]

        if session_ids:
            # 2. 删除 LeaderMessage
            await self.db.execute(
                sa_delete(LeaderMessage).where(
                    LeaderMessage.leader_session_id.in_(session_ids)
                )
            )
            # 3. 删除 LeaderAgentResult
            await self.db.execute(
                sa_delete(LeaderAgentResult).where(
                    LeaderAgentResult.leader_session_id.in_(session_ids)
                )
            )
            # 4. 删除 LeaderFinalReport
            await self.db.execute(
                sa_delete(LeaderFinalReport).where(
                    LeaderFinalReport.leader_session_id.in_(session_ids)
                )
            )
            # 5. 删除 LeaderSession
            await self.db.execute(
                sa_delete(LeaderSession).where(
                    LeaderSession.id.in_(session_ids)
                )
            )

        # 6. 删除 Message
        await self.db.execute(
            sa_delete(Message).where(Message.conversation_id == conversation_id)
        )

        # 7. 删除 Conversation 主表
        await self.db.delete(conversation)
        await self.db.flush()
        return True

    async def update_conversation_status(
        self, conversation_id: int, status: str
    ) -> None:
        """更新对话状态"""
        await self.db.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(status=status, updated_at=get_utc_now())
        )
        await self.db.flush()

    async def update_conversation_title(
        self, conversation_id: int, title: str
    ) -> None:
        """更新对话标题"""
        await self.db.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(title=title, updated_at=get_utc_now())
        )
        await self.db.flush()

    # ===== LeaderSession =====

    async def create_leader_session(
        self,
        conversation_id: int,
        patient_id: int,
        user_message: str,
    ) -> LeaderSession:
        """创建 Leader 会话"""
        session = LeaderSession(
            conversation_id=conversation_id,
            patient_id=patient_id,
            user_message=user_message,
            state="idle",
        )
        self.db.add(session)
        await self.db.flush()
        return session

    async def get_leader_session(self, session_id: int) -> Optional[LeaderSession]:
        """获取 Leader 会话"""
        result = await self.db.execute(
            select(LeaderSession).where(LeaderSession.id == session_id)
        )
        return result.scalar_one_or_none()

    async def get_active_session_by_conversation(
        self, conversation_id: int
    ) -> Optional[LeaderSession]:
        """获取对话中最近的一个会话"""
        result = await self.db.execute(
            select(LeaderSession)
            .where(LeaderSession.conversation_id == conversation_id)
            .order_by(desc(LeaderSession.id))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def update_session_state(self, session_id: int, state: str, **kwargs) -> None:
        """更新会话状态"""
        values = {"state": state}
        if state in ("completed", "stopped", "failed"):
            values["completed_at"] = get_utc_now()
        values.update(kwargs)
        await self.db.execute(
            update(LeaderSession).where(LeaderSession.id == session_id).values(**values)
        )
        await self.db.flush()

    async def request_stop(self, session_id: int) -> None:
        """请求停止会诊"""
        await self.db.execute(
            update(LeaderSession)
            .where(LeaderSession.id == session_id)
            .values(stop_requested=True)
        )
        await self.db.flush()

    # ===== LeaderMessage =====

    async def add_leader_message(
        self,
        leader_session_id: int,
        message_type: str,
        content: dict,
        sequence_number: int,
    ) -> LeaderMessage:
        """添加 Leader 消息"""
        message = LeaderMessage(
            leader_session_id=leader_session_id,
            message_type=message_type,
            content=content,
            sequence_number=sequence_number,
        )
        self.db.add(message)
        await self.db.flush()
        return message

    async def get_leader_messages(
        self, leader_session_id: int
    ) -> List[LeaderMessage]:
        """获取会话的所有 Leader 消息"""
        result = await self.db.execute(
            select(LeaderMessage)
            .where(LeaderMessage.leader_session_id == leader_session_id)
            .order_by(LeaderMessage.sequence_number)
        )
        return list(result.scalars().all())

    # ===== LeaderAgentResult =====

    async def add_agent_result(
        self,
        leader_session_id: int,
        agent_id: str,
        agent_name: str,
        status: str,
        sequence_number: int,
        content: Optional[str] = None,
        error: Optional[str] = None,
    ) -> LeaderAgentResult:
        """添加专家分析结果"""
        result = LeaderAgentResult(
            leader_session_id=leader_session_id,
            agent_id=agent_id,
            agent_name=agent_name,
            status=status,
            content=content,
            error=error,
            sequence_number=sequence_number,
        )
        self.db.add(result)
        await self.db.flush()
        return result

    async def get_agent_results(
        self, leader_session_id: int
    ) -> List[LeaderAgentResult]:
        """获取会话的所有专家结果"""
        result = await self.db.execute(
            select(LeaderAgentResult)
            .where(LeaderAgentResult.leader_session_id == leader_session_id)
            .order_by(LeaderAgentResult.sequence_number)
        )
        return list(result.scalars().all())

    # ===== LeaderFinalReport =====

    async def add_final_report(
        self,
        leader_session_id: int,
        report: str,
    ) -> LeaderFinalReport:
        """添加综合报告"""
        report_obj = LeaderFinalReport(
            leader_session_id=leader_session_id,
            report=report,
        )
        self.db.add(report_obj)
        await self.db.flush()
        return report_obj

    async def get_final_report(
        self, leader_session_id: int
    ) -> Optional[LeaderFinalReport]:
        """获取会话的综合报告"""
        result = await self.db.execute(
            select(LeaderFinalReport).where(
                LeaderFinalReport.leader_session_id == leader_session_id
            )
        )
        return result.scalar_one_or_none()

    # ===== Message =====

    async def add_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        leader_session_id: Optional[int] = None,
        message_type: str = "normal",
        sequence_number: int = 0,
    ) -> Message:
        """添加对话消息"""
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            leader_session_id=leader_session_id,
            message_type=message_type,
            sequence_number=sequence_number,
        )
        self.db.add(message)
        await self.db.flush()
        return message

    async def get_messages(
        self, conversation_id: int
    ) -> List[Message]:
        """获取对话的所有消息"""
        result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.sequence_number)
        )
        return list(result.scalars().all())

    # ===== Session 数据恢复（前端重新加载用） =====

    async def get_session_data(self, conversation_id: int) -> Optional[dict]:
        """获取对话完整数据（前端恢复用）

        使用 selectinload 预加载关联数据，减少查询次数。

        Returns:
            包含 conversation, session, messages, agent_results, final_report 的字典
        """
        # 查询 Conversation 并预加载 messages 和 leader_sessions 及其子关联
        result = await self.db.execute(
            select(Conversation)
            .options(
                selectinload(Conversation.messages),
                selectinload(Conversation.leader_sessions)
                .selectinload(LeaderSession.leader_messages),
                selectinload(Conversation.leader_sessions)
                .selectinload(LeaderSession.agent_results),
                selectinload(Conversation.leader_sessions)
                .selectinload(LeaderSession.final_report),
            )
            .where(Conversation.id == conversation_id)
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            return None

        # 获取最近的 LeaderSession
        session = None
        if conversation.leader_sessions:
            session = max(conversation.leader_sessions, key=lambda s: s.id)

        if not session:
            return {
                "conversation": conversation,
                "session": None,
                "messages": [],
                "agent_results": [],
                "final_report": None,
                "conversation_messages": list(conversation.messages),
            }

        # 迁移移除了 leader 子表的 conversation_id 列，手动赋值便于 Schema 序列化
        conv_id = conversation.id
        for msg in session.leader_messages:
            msg.conversation_id = conv_id
        for ar in session.agent_results:
            ar.conversation_id = conv_id
        if session.final_report:
            session.final_report.conversation_id = conv_id

        return {
            "conversation": conversation,
            "session": session,
            "messages": list(session.leader_messages),
            "agent_results": list(session.agent_results),
            "final_report": session.final_report,
            "conversation_messages": list(conversation.messages),
        }

    async def get_session_data_by_token(self, share_token: str) -> Optional[dict]:
        """通过 share_token 获取会话数据（分享链接），校验过期时间"""
        conversation = await self.get_conversation_by_token(share_token)
        if not conversation:
            return None

        # 校验过期时间
        if conversation.share_expire_at and get_utc_now() > conversation.share_expire_at:
            return None

        return await self.get_session_data(conversation.id)

    async def generate_and_save_share_token(
        self,
        conversation_id: int,
        password: Optional[str] = None,
        expire_hours: Optional[int] = None,
    ) -> Tuple[str, bool, Optional[datetime]]:
        """生成并保存分享令牌

        Args:
            conversation_id: 对话 ID
            password: 可选的分享密码（明文，存入时 bcrypt 哈希）
            expire_hours: 可选的有效期小时数

        Returns:
            (token, has_password, expire_at) 元组
        """
        token = await self._generate_unique_share_token()

        values = {"share_token": token, "updated_at": get_utc_now()}

        # 密码处理
        has_password = False
        if password:
            from app.core.security import get_password_hash
            values["share_password"] = get_password_hash(password)
            has_password = True
        else:
            values["share_password"] = None

        # 过期时间处理
        expire_at = None
        if expire_hours:
            expire_at = get_utc_now() + timedelta(hours=expire_hours)
            values["share_expire_at"] = expire_at
        else:
            values["share_expire_at"] = None

        await self.db.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(**values)
        )
        await self.db.flush()
        return token, has_password, expire_at

    # ===== 重连辅助方法 =====

    async def get_latest_leader_session(self, conversation_id: int) -> Optional[LeaderSession]:
        """获取对话最新的 LeaderSession"""
        result = await self.db.execute(
            select(LeaderSession)
            .where(LeaderSession.conversation_id == conversation_id)
            .order_by(LeaderSession.started_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_session_messages(self, leader_session_id: int) -> List[LeaderMessage]:
        """获取指定 LeaderSession 的历史消息（按序号排序）"""
        result = await self.db.execute(
            select(LeaderMessage)
            .where(LeaderMessage.leader_session_id == leader_session_id)
            .order_by(LeaderMessage.sequence_number)
        )
        return list(result.scalars().all())

    # ===== 工具方法 =====

    @staticmethod
    def _generate_share_token() -> str:
        """生成 256bit 分享令牌（token_urlsafe(32)，43 字符）"""
        return secrets.token_urlsafe(32)

    async def _generate_unique_share_token(self) -> str:
        """生成唯一分享令牌；256bit 熵下碰撞概率可忽略，查重仅作防御"""
        for _ in range(3):
            token = self._generate_share_token()
            result = await self.db.execute(
                select(Conversation).where(Conversation.share_token == token)
            )
            if not result.scalar_one_or_none():
                return token
        # 理论不可达：连续碰撞时直接返回新 token
        return self._generate_share_token()

    # ===== 启动清理 =====
