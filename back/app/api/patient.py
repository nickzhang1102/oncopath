from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, text
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import date
import logging

from app.core.database import get_db
from app.api.auth import get_current_user
from app.api.deps import verify_patient_access
from app.models.user import LoginAccount
from app.models.patient import Patient
from app.models.medical import MedicalCheck, MedicalExam, MedicalRecord, PathologyReport
from app.schemas.patient import (
    PatientCreate, PatientUpdate, PatientResponse, PatientListResponse,
    PatientEditResponse
)
from app.services.desensitization import desensitization_service
from app.services.encryption_service import encryption_service
from app.utils.time_utils import utc_isoformat
from app.core.rate_limit import limiter
from app.utils.time_utils import calculate_age

# 向后兼容：保留从 api.patient 导入 calculate_age 的能力
# （已迁移至 app.utils.time_utils，新代码应从 utils 导入）

router = APIRouter()


def _desensitize_patient(patient: Patient) -> dict:
    """对患者敏感字段脱敏后返回字典（调用前需已解密）"""
    data = patient.to_dict()
    data['patient_name'] = desensitization_service.mask_name(data.get('patient_name', ''))
    data['patient_phone'] = desensitization_service.mask_phone(data.get('patient_phone') or '')
    data['id_card'] = desensitization_service.mask_id_card(data.get('id_card') or '')
    data['emergency_contact'] = desensitization_service.mask_name(data.get('emergency_contact') or '')
    data['emergency_phone'] = desensitization_service.mask_phone(data.get('emergency_phone') or '')
    return data


def build_patient_response(patient: Patient) -> PatientResponse:
    """构建患者响应的公共函数 — 敏感字段脱敏"""
    return PatientResponse(**_desensitize_patient(patient))


@router.get("", response_model=List[PatientListResponse])
async def get_patient_list(
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """获取当前账号下所有患者列表"""
    # 使用子查询避免多 LEFT JOIN 笛卡尔积导致 count 膨胀
    check_sub = (
        select(MedicalCheck.patient_id, func.count(MedicalCheck.medical_id).label('check_count'))
        .group_by(MedicalCheck.patient_id)
        .subquery()
    )
    exam_sub = (
        select(MedicalExam.patient_id, func.count(MedicalExam.exam_id).label('exam_count'))
        .group_by(MedicalExam.patient_id)
        .subquery()
    )
    record_sub = (
        select(MedicalRecord.patient_id, func.count(MedicalRecord.record_id).label('record_count'))
        .group_by(MedicalRecord.patient_id)
        .subquery()
    )

    stmt = select(
        Patient,
        func.coalesce(check_sub.c.check_count, 0).label('check_count'),
        func.coalesce(exam_sub.c.exam_count, 0).label('exam_count'),
        func.coalesce(record_sub.c.record_count, 0).label('record_count')
    ).outerjoin(
        check_sub, Patient.patient_id == check_sub.c.patient_id
    ).outerjoin(
        exam_sub, Patient.patient_id == exam_sub.c.patient_id
    ).outerjoin(
        record_sub, Patient.patient_id == record_sub.c.patient_id
    ).where(
        Patient.account_id == current_user.account_id
    )

    result = await db.execute(stmt)
    rows = result.all()

    response_list = []
    for row in rows:
        patient = row[0]
        # 解密后脱敏
        patient.decrypt_sensitive_fields()
        check_count = row.check_count or 0
        exam_count = row.exam_count or 0
        record_count = row.record_count or 0

        masked_name = desensitization_service.mask_name(patient.patient_name)
        age = calculate_age(patient.birth_date)

        response_list.append(PatientListResponse(
            patient_id=patient.patient_id,
            patient_name=masked_name,
            gender=patient.gender,
            birth_date=patient.birth_date,
            age=age,
            is_primary=patient.is_primary,
            check_count=check_count,
            exam_count=exam_count,
            record_count=record_count
        ))

    return response_list


@router.post("", response_model=PatientResponse)
async def create_patient(
    patient_data: PatientCreate,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """添加新患者"""
    # 检查身份证号是否已存在（使用哈希索引查询）
    if patient_data.id_card:
        id_card_hash = encryption_service.hash_for_index(patient_data.id_card)
        result = await db.execute(
            select(Patient).where(Patient.id_card_hash == id_card_hash)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail="该身份证号已存在"
            )

    # 检查是否是第一个患者 — 自动设为主患者
    existing_count = await db.execute(
        select(func.count(Patient.patient_id)).where(
            Patient.account_id == current_user.account_id
        )
    )
    is_first = (existing_count.scalar() or 0) == 0

    # 创建患者并加密敏感字段
    new_patient = Patient(
        account_id=current_user.account_id,
        is_primary=is_first,
        **patient_data.model_dump()
    )
    new_patient.encrypt_sensitive_fields()
    db.add(new_patient)
    await db.commit()
    await db.refresh(new_patient)

    # 解密后构建脱敏响应
    new_patient.decrypt_sensitive_fields()
    return build_patient_response(new_patient)


@router.get("/primary", response_model=PatientResponse)
async def get_primary_patient(
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """获取主患者"""
    result = await db.execute(
        select(Patient).where(
            Patient.account_id == current_user.account_id,
            Patient.is_primary == True
        )
    )
    patient = result.scalar_one_or_none()

    if not patient:
        raise HTTPException(status_code=404, detail="主患者不存在")

    patient.decrypt_sensitive_fields()
    return build_patient_response(patient)


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """获取指定患者信息（敏感字段脱敏）"""
    patient = await verify_patient_access(db, patient_id, current_user.account_id)
    return build_patient_response(patient)


@router.get("/{patient_id}/edit", response_model=PatientEditResponse)
@limiter.limit("10/minute")
async def get_patient_for_edit(
    patient_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """获取患者编辑信息 — 敏感字段返回明文供编辑表单使用"""
    patient = await verify_patient_access(db, patient_id, current_user.account_id)

    # 审计日志：记录明文 PHI 访问
    logger = logging.getLogger(__name__)
    logger.info(
        f"PHI_ACCESS: account_id={current_user.account_id}, "
        f"patient_id={patient_id}, action=view_plaintext_phi"
    )

    return PatientEditResponse(**patient.to_dict())


@router.put("/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: int,
    patient_data: PatientUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """更新患者信息"""
    patient = await verify_patient_access(db, patient_id, current_user.account_id)

    # 更新字段
    update_data = patient_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(patient, field, value)

    # 重新加密敏感字段
    patient.encrypt_sensitive_fields()

    await db.commit()
    await db.refresh(patient)

    # 解密后构建脱敏响应
    patient.decrypt_sensitive_fields()
    return build_patient_response(patient)


@router.delete("/{patient_id}")
async def delete_patient(
    patient_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """删除患者（含安全检查 + 手动级联删除）"""
    patient = await verify_patient_access(db, patient_id, current_user.account_id)

    if patient.is_primary:
        raise HTTPException(status_code=400, detail="主患者不能删除")

    # 统计关联数据
    from app.models.conversation import ConsultationExternalSession, LeaderSession, Conversation
    from app.models.follow_up import FollowUpReminder
    from app.models.image_report import ImageReport
    from app.models.medication import Medication
    from app.models.medication_log import MedicationLog
    from app.models.timeline import TimelineEvent

    # 统计各模块数据量
    counts = {}
    count_queries = {
        "conversations": select(func.count(Conversation.id)).where(Conversation.patient_id == patient_id),
        "medications": select(func.count(Medication.id)).where(Medication.patient_id == patient_id),
        "medication_logs": select(func.count(MedicationLog.id)).where(MedicationLog.patient_id == patient_id),
        "follow_ups": select(func.count(FollowUpReminder.id)).where(FollowUpReminder.patient_id == patient_id),
        "checks": select(func.count(MedicalCheck.medical_id)).where(MedicalCheck.patient_id == patient_id),
        "exams": select(func.count(MedicalExam.exam_id)).where(MedicalExam.patient_id == patient_id),
        "pathology": select(func.count(PathologyReport.report_id)).where(PathologyReport.patient_id == patient_id),
        "image_reports": select(func.count(ImageReport.report_id)).where(ImageReport.patient_id == patient_id),
    }
    for key, query in count_queries.items():
        result = await db.execute(query)
        counts[key] = result.scalar() or 0

    # 手动级联删除：先删除 ORM cascade 未覆盖的子表
    # 1. MedicationLog（依赖 Medication）
    await db.execute(
        MedicationLog.__table__.delete().where(MedicationLog.patient_id == patient_id)
    )
    # 2. FollowUpReminder
    await db.execute(
        FollowUpReminder.__table__.delete().where(FollowUpReminder.patient_id == patient_id)
    )
    # 3. ImageReport
    await db.execute(
        ImageReport.__table__.delete().where(ImageReport.patient_id == patient_id)
    )
    # 4. Conversation（手动级联：LeaderSession/LeaderMessage/LeaderAgentResult/LeaderFinalReport）
    conv_result = await db.execute(
        select(Conversation.id).where(Conversation.patient_id == patient_id)
    )
    conv_ids = [row[0] for row in conv_result.all()]
    if conv_ids:
        from app.models.conversation import LeaderMessage, LeaderAgentResult, LeaderFinalReport, Message
        await db.execute(
            ConsultationExternalSession.__table__.delete().where(
                ConsultationExternalSession.conversation_id.in_(conv_ids)
            )
        )
        session_result = await db.execute(
            select(LeaderSession.id).where(LeaderSession.conversation_id.in_(conv_ids))
        )
        leader_session_ids = [row[0] for row in session_result.all()]
        if leader_session_ids:
            await db.execute(LeaderAgentResult.__table__.delete().where(
                LeaderAgentResult.leader_session_id.in_(leader_session_ids)
            ))
            await db.execute(LeaderFinalReport.__table__.delete().where(
                LeaderFinalReport.leader_session_id.in_(leader_session_ids)
            ))
            await db.execute(LeaderMessage.__table__.delete().where(
                LeaderMessage.leader_session_id.in_(leader_session_ids)
            ))
            await db.execute(LeaderSession.__table__.delete().where(LeaderSession.id.in_(leader_session_ids)))
        await db.execute(Message.__table__.delete().where(Message.conversation_id.in_(conv_ids)))
        await db.execute(Conversation.__table__.delete().where(Conversation.id.in_(conv_ids)))

    # ORM cascade 删除 patient（覆盖: MedicalCheck, MedicalExam, PathologyReport, MedicalRecord, TimelineEvent, Medication, PromptConfig）
    await db.delete(patient)
    await db.commit()

    return {
        "message": "删除成功",
        "deleted_counts": counts,
    }


@router.post("/{patient_id}/switch")
async def switch_patient(
    patient_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """切换当前患者"""
    await verify_patient_access(db, patient_id, current_user.account_id)
    return {"message": "切换成功", "patient_id": patient_id}


@router.put("/{patient_id}/primary")
async def set_primary_patient(
    patient_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """设置主患者"""
    patients_result = await db.execute(
        select(Patient).where(Patient.account_id == current_user.account_id)
    )
    patients = patients_result.scalars().all()
    for p in patients:
        p.is_primary = False

    patient = await verify_patient_access(db, patient_id, current_user.account_id)
    patient.is_primary = True
    await db.commit()

    return {"message": "设置成功"}


@router.get("/{patient_id}/timeline")
async def get_patient_timeline(
    patient_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """获取患者时间线"""
    from app.models.timeline import TimelineEvent
    from sqlalchemy import desc

    # 验证患者权限
    patient = await verify_patient_access(db, patient_id, current_user.account_id)

    result = await db.execute(
        select(TimelineEvent)
        .where(TimelineEvent.patient_id == patient_id)
        .order_by(desc(TimelineEvent.event_date))
        .limit(100)
    )
    events = result.scalars().all()

    return [{
        "event_id": e.event_id,
        "event_type": e.event_type,
        "event_date": e.event_date.isoformat() if e.event_date else None,
        "title": e.title,
        "description": e.description,
        "category": e.category if hasattr(e, 'category') else None,
        "metadata": e.metadata if hasattr(e, 'metadata') else None
    } for e in events]


@router.get("/{patient_id}/stats")
async def get_patient_stats(
    patient_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """获取患者统计信息"""
    from app.models.medical import MedicalCheck, MedicalExam, MedicalRecord
    from sqlalchemy import func

    # 验证患者权限
    patient = await verify_patient_access(db, patient_id, current_user.account_id)

    # 统计各类记录数量
    check_count = await db.execute(
        select(func.count(MedicalCheck.medical_id)).where(MedicalCheck.patient_id == patient_id)
    )
    exam_count = await db.execute(
        select(func.count(MedicalExam.exam_id)).where(MedicalExam.patient_id == patient_id)
    )
    record_count = await db.execute(
        select(func.count(MedicalRecord.record_id)).where(MedicalRecord.patient_id == patient_id)
    )

    return {
        "patient_id": patient_id,
        "check_count": check_count.scalar() or 0,
        "exam_count": exam_count.scalar() or 0,
        "record_count": record_count.scalar() or 0
    }


@router.get("/{patient_id}/consultations")
async def get_patient_consultations(
    patient_id: int,
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """获取患者会诊列表"""
    from app.models.conversation import Conversation

    # 验证患者权限
    patient = await verify_patient_access(db, patient_id, current_user.account_id)

    result = await db.execute(
        select(Conversation)
        .where(Conversation.patient_id == patient_id)
        .order_by(desc(Conversation.created_at))
        .limit(limit)
        .offset(offset)
    )
    conversations = result.scalars().all()

    return [{
        "consultation_id": c.id,
        "question": c.title,
        "status": c.status,
        "created_at": utc_isoformat(c.created_at),
        "ai_response": None
    } for c in conversations]


# 异常指标端点已移至 medical.py（/medical/patients/{patient_id}/indicators/abnormal）
