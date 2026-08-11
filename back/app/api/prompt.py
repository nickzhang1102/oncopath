"""提示词配置 API路由

提供提示词配置的保存和读取功能，以及记录概要摘要 CRUD API。
"""

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field, model_validator
from typing import List, Optional
import copy
import json
import logging

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.user import LoginAccount
from app.models.patient import Patient
from app.models.prompt import PromptConfig
from app.services.consultation.medical_prompt_builder import MedicalPromptBuilder
from app.services.consultation.summary_service import SummaryService
from app.schemas.consultation import PromptPreviewRequest

logger = logging.getLogger(__name__)

router = APIRouter()


class UserContentConfigItem(BaseModel):
    """用户内容配置项"""
    id: int
    name: str
    description: str = ""
    type: str  # custom, info, history, record, timeline, pathology, lab, exam, treatment, medication_record, status
    enabled: bool
    customText: Optional[str] = None
    indicatorCount: Optional[int] = None
    recentCount: Optional[int] = None
    category: Optional[str] = None  # lab category identifier
    contentLimit: Optional[int] = None  # content truncation chars (record/exam/status)
    findingsLimit: Optional[int] = None  # findings truncation chars (exam)


class PromptConfigRequest(BaseModel):
    """提示词配置请求"""
    patient_id: int
    system_prompt: str
    time_range_days: int = 60
    user_content_config: List[UserContentConfigItem]


class PromptConfigResponse(BaseModel):
    """提示词配置响应"""
    status: str
    message: str = ""
    data: Optional[dict] = None


# 默认提示词配置
DEFAULT_PROMPT_CONFIG = {
    "system_prompt": "你是一名经验丰富的肿瘤科专家",
    "time_range_days": 60,
    "user_content_config": [
        {"id": 1, "name": "自定义内容", "description": "添加自定义的医疗信息", "type": "custom", "enabled": False, "customText": ""},
        {"id": 2, "name": "病人概况", "description": "患者姓名、性别、年龄、病史、过敏史", "type": "info", "enabled": True},
        {"id": 3, "name": "病史记录", "description": "患者既往病史", "type": "history", "enabled": True},
        {"id": 4, "name": "治疗时间线", "description": "治疗历程事件", "type": "timeline", "enabled": False, "recentCount": 20},
        {"id": 5, "name": "病理报告", "description": "全部病理报告", "type": "pathology", "enabled": True},
        {"id": 6, "name": "血常规", "description": "血液常规检查指标", "type": "lab", "enabled": True, "indicatorCount": 7, "recentCount": 3, "category": "blood_routine"},
        {"id": 7, "name": "肿瘤指标", "description": "肿瘤相关检查指标", "type": "lab", "enabled": True, "indicatorCount": 10, "recentCount": 4, "category": "tumor_marker"},
        {"id": 8, "name": "生化指标", "description": "生化检查相关指标", "type": "lab", "enabled": True, "indicatorCount": 27, "recentCount": 1, "category": "biochemistry"},
        {"id": 9, "name": "凝血指标", "description": "凝血功能检查指标", "type": "lab", "enabled": True, "indicatorCount": 7, "recentCount": 1, "category": "coagulation"},
        {"id": 10, "name": "体重记录", "description": "患者体重变化记录", "type": "lab", "enabled": True, "indicatorCount": 2, "recentCount": 3, "category": "body_weight"},
        {"id": 11, "name": "尿常规", "description": "尿液常规检查指标", "type": "lab", "enabled": False, "indicatorCount": 10, "recentCount": 1, "category": "urine_routine"},
        {"id": 12, "name": "CT/检查报告", "description": "CT检查报告", "type": "exam", "enabled": True, "recentCount": 2, "findingsLimit": 500},
        {"id": 13, "name": "治疗记录", "description": "化疗、放疗、手术等治疗事件", "type": "treatment", "enabled": True, "recentCount": 10},
        {"id": 14, "name": "用药记录", "description": "全部用药含停药详情", "type": "medication_record", "enabled": True, "recentCount": 20},
        {"id": 15, "name": "状态记录", "description": "每日状态评分记录", "type": "status", "enabled": True, "recentCount": 30, "contentLimit": 500},
        {"id": 16, "name": "当前用药方案", "description": "正在使用和最近停药的药物", "type": "medication", "enabled": True},
        {"id": 17, "name": "用户补充说明", "description": "用户附加的会诊说明", "type": "custom", "enabled": True, "customText": ""},
        {"id": 18, "name": "诊断要求", "description": "对AI诊断的具体要求", "type": "custom", "enabled": True, "customText": "请根据以上信息，提供：1. 当前病情分析 2. 诊断意见 3. 后续治疗建议 4. 注意事项"},
    ]
}


@router.get("/config/{patient_id}", response_model=PromptConfigResponse)
async def get_prompt_config(
    patient_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """获取提示词配置
    
    Args:
        patient_id: 患者ID
        
    Returns:
        提示词配置
    """
    try:
        # 验证患者权限
        patient_result = await db.execute(
            select(Patient).where(
                Patient.patient_id == patient_id,
                Patient.account_id == current_user.account_id
            )
        )
        patient = patient_result.scalar_one_or_none()
        
        if not patient:
            raise HTTPException(status_code=404, detail="患者不存在或无权访问")
        
        # 查询已保存的配置
        config_result = await db.execute(
            select(PromptConfig)
            .where(PromptConfig.patient_id == patient_id)
            .order_by(
                PromptConfig.updated_at.desc().nullslast(),
                PromptConfig.config_id.desc(),
            )
            .limit(1)
        )
        config = config_result.scalar_one_or_none()
        
        if config:
            # 返回已保存的配置
            return PromptConfigResponse(
                status="success",
                data=config.to_dict()
            )
        else:
            # 返回默认配置
            return PromptConfigResponse(
                status="success",
                data=copy.deepcopy(DEFAULT_PROMPT_CONFIG)
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取提示词配置失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取配置失败")


@router.post("/config", response_model=PromptConfigResponse)
async def save_prompt_config(
    config: PromptConfigRequest,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """保存提示词配置
    
    Args:
        config: 提示词配置
        
    Returns:
        保存结果
    """
    try:
        # 验证患者权限
        patient_result = await db.execute(
            select(Patient).where(
                Patient.patient_id == config.patient_id,
                Patient.account_id == current_user.account_id
            )
        )
        patient = patient_result.scalar_one_or_none()
        
        if not patient:
            raise HTTPException(status_code=404, detail="患者不存在或无权访问")
        
        # 查找现有配置
        existing_result = await db.execute(
            select(PromptConfig)
            .where(PromptConfig.patient_id == config.patient_id)
            .order_by(
                PromptConfig.updated_at.desc().nullslast(),
                PromptConfig.config_id.desc(),
            )
            .limit(1)
        )
        existing_config = existing_result.scalar_one_or_none()
        
        # 转换user_content_config为JSON字符串
        user_content_json = json.dumps(
            [item.model_dump() for item in config.user_content_config],
            ensure_ascii=False
        )
        
        if existing_config:
            # 更新现有配置
            # 配置的业务归属是患者；同步修复历史遗留的旧账号外键，
            # 使预览与 AgentTeams 启动读取保持一致。
            existing_config.account_id = current_user.account_id
            existing_config.system_prompt = config.system_prompt
            existing_config.time_range_days = config.time_range_days
            existing_config.user_content_config = user_content_json
        else:
            # 创建新配置
            new_config = PromptConfig(
                account_id=current_user.account_id,
                patient_id=config.patient_id,
                system_prompt=config.system_prompt,
                time_range_days=config.time_range_days,
                user_content_config=user_content_json
            )
            db.add(new_config)
        
        await db.commit()
        
        # 重新查询以获取最新数据
        if existing_config:
            await db.refresh(existing_config)
            saved_config = existing_config
        else:
            await db.refresh(new_config)
            saved_config = new_config
        
        return PromptConfigResponse(
            status="success",
            message="提示词配置已保存",
            data=saved_config.to_dict()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"保存提示词配置失败: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail="保存配置失败")


@router.get("/default", response_model=PromptConfigResponse)
async def get_default_prompt_config(
    current_user=Depends(get_current_user)
):
    """获取默认提示词配置

    Returns:
        默认提示词配置
    """
    return PromptConfigResponse(
        status="success",
        data=copy.deepcopy(DEFAULT_PROMPT_CONFIG)
    )


@router.post("/preview")
async def preview_prompt(
    request: PromptPreviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user)
):
    """根据配置预览生成的提示词"""
    try:
        # 验证患者权限
        patient_result = await db.execute(
            select(Patient).where(
                Patient.patient_id == request.patient_id,
                Patient.account_id == current_user.account_id
            )
        )
        patient = patient_result.scalar_one_or_none()

        if not patient:
            raise HTTPException(status_code=404, detail="患者不存在或无权访问")

        # 构建配置 dict
        config = {
            "system_prompt": request.system_prompt,
            "time_range_days": request.time_range_days,
            "user_content_config": [item.model_dump() for item in request.user_content_config],
        }

        builder = MedicalPromptBuilder()
        prompt = await builder.build_consultation_prompt(
            patient_id=request.patient_id,
            db=db,
            prompt_config=config,
        )

        return {"status": "success", "data": {"prompt": prompt}}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"预览提示词失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="预览失败")


# ========== 记录概要摘要 API ==========

class SummaryGenerateRequest(BaseModel):
    """概要生成请求"""
    patient_id: int
    summary_type: str = Field(..., pattern=r"^(treatment|medication_record|status)$")
    period_start: date
    period_end: date
    source: str = Field("rule_template", pattern=r"^(rule_template|llm_generated)$")

    @model_validator(mode="after")
    def _validate_type_source_compat(self):
        if self.source == "rule_template" and self.summary_type == "status":
            raise ValueError("规则模板不支持 status 类型，请选择 LLM 摘要")
        if self.source == "llm_generated" and self.summary_type != "status":
            raise ValueError("LLM 摘要当前仅支持 status 类型")
        return self


class SummaryUpdateRequest(BaseModel):
    """概要更新请求"""
    summary_text: Optional[str] = None
    status: Optional[str] = Field(None, pattern=r"^(draft|confirmed)$")


class SummaryResponse(BaseModel):
    """概要响应"""
    summary_id: int
    patient_id: int
    summary_type: str
    period_start: str
    period_end: str
    summary_text: str
    source: str
    status: str
    source_record_count: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@router.get("/summaries/{patient_id}", response_model=List[SummaryResponse])
async def list_summaries(
    patient_id: int,
    summary_type: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user),
):
    """获取患者概要列表"""
    await _verify_patient_access(db, patient_id, current_user.account_id)
    svc = SummaryService(db)
    summaries = await svc.list_summaries(patient_id, summary_type=summary_type, status=status)
    return [SummaryResponse(**s.to_dict()) for s in summaries]


@router.post("/summaries/generate", response_model=SummaryResponse)
async def generate_summary(
    req: SummaryGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user),
):
    """生成概要（规则模板 / LLM）"""
    await _verify_patient_access(db, req.patient_id, current_user.account_id)
    svc = SummaryService(db)

    if req.source == "rule_template":
        result = await svc.generate_rule_summary(
            patient_id=req.patient_id,
            summary_type=req.summary_type,
            period_start=req.period_start,
            period_end=req.period_end,
        )
    else:
        from app.services.llm_service import LLMService
        llm = LLMService()
        result = await svc.generate_llm_summary(
            patient_id=req.patient_id,
            period_start=req.period_start,
            period_end=req.period_end,
            llm_service=llm,
        )

    if not result:
        raise HTTPException(status_code=422, detail="该时段内无记录，无法生成概要")

    await db.commit()
    await db.refresh(result)
    return SummaryResponse(**result.to_dict())


@router.put("/summaries/{summary_id}", response_model=SummaryResponse)
async def update_summary(
    summary_id: int,
    req: SummaryUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user),
):
    """编辑/确认概要"""
    svc = SummaryService(db)
    existing = await svc.get_summary(summary_id)
    if not existing:
        raise HTTPException(status_code=404, detail="概要不存在")
    await _verify_patient_access(db, existing.patient_id, current_user.account_id)
    result = await svc.update_summary(
        summary_id=summary_id,
        summary_text=req.summary_text,
        status=req.status,
    )
    await db.commit()
    await db.refresh(result)
    return SummaryResponse(**result.to_dict())


@router.delete("/summaries/{summary_id}")
async def delete_summary(
    summary_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: LoginAccount = Depends(get_current_user),
):
    """删除概要"""
    svc = SummaryService(db)
    existing = await svc.get_summary(summary_id)
    if not existing:
        raise HTTPException(status_code=404, detail="概要不存在")
    await _verify_patient_access(db, existing.patient_id, current_user.account_id)
    ok = await svc.delete_summary(summary_id)
    await db.commit()
    return {"message": "删除成功"}


async def _verify_patient_access(db: AsyncSession, patient_id: int, account_id: int):
    """验证患者归属"""
    result = await db.execute(
        select(Patient).where(
            Patient.patient_id == patient_id,
            Patient.account_id == account_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="患者不存在或无权访问")
