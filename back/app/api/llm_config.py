"""LLM 配置管理 API（主系统入口）

仅限管理员或首个注册账号查看/修改/测试全局 LLM 配置（解读/OCR 两组；
本地会诊已由 AgentTeams 承接，不再依赖本配置）。
修改保存后自动应用到运行时，无需手动重载；应用启动时也会自动加载活跃配置。
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.core.database import get_db
from app.models.admin import LLMConfig
from app.models.user import LoginAccount
from app.schemas.llm_config import (
    LLMConfigGroupUpdate, LLMConfigItem, LLMConfigStatusResponse,
    LLMConfigTestRequest, LLMConfigTestResponse,
)
from app.services.encryption_service import encryption_service

logger = logging.getLogger(__name__)

router = APIRouter()


async def get_llm_config_manager_user(
    current_user: LoginAccount = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LoginAccount:
    """LLM 配置管理鉴权：仅管理员或首个注册账号

    全局 LLM 配置决定会诊/解读/OCR 数据的出站目的地（含 API 地址与密钥），
    暴露给任意登录账号会被恶意账号改为自建服务端以窃取病历上下文，
    故收紧至 admin 账号或最早注册的账号（自托管单管理员定位）。
    """
    if current_user.account_type == "admin":
        return current_user
    first_id = (
        await db.execute(select(func.min(LoginAccount.account_id)))
    ).scalar()
    if first_id is not None and current_user.account_id == first_id:
        return current_user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="仅管理员或首个账号可管理 AI 模型配置",
    )


def _mask_secret_value(value: str) -> str:
    """敏感字段掩码：显示后4位"""
    if not value or len(value) <= 4:
        return "****"
    return f"****{value[-4:]}"


def _decrypt_or_plaintext(ciphertext: str) -> str:
    """解密配置值，解密失败视为明文旧数据"""
    try:
        return encryption_service.decrypt(ciphertext)
    except Exception:
        logger.info("LLM配置解密失败，视为明文数据（首次加密迁移）")
        return ciphertext


@router.get("/llm-configs")
async def list_llm_configs(
    current_user: LoginAccount = Depends(get_llm_config_manager_user),
    db: AsyncSession = Depends(get_db),
):
    """获取所有 LLM 配置

    表无记录 → 从 .env (Settings) 构造展示列表，is_active=False
    表有记录 → 用表记录；is_active=False 时展示 .env 值，is_active=True 时展示数据库值

    注意：本接口在读路径上顺带完成明文 secret 的自动加密迁移（commit），
    属有意的首次访问迁移策略；迁移仅在解密失败判定为明文时发生一次。
    """
    from app.services.llm_config_service import LLMConfigService, LLM_CONFIG_DEFINITIONS

    result = await db.execute(
        select(LLMConfig).order_by(LLMConfig.config_group, LLMConfig.id)
    )
    configs = result.scalars().all()
    config_map = {cfg.config_key: cfg for cfg in configs}

    items = []
    needs_migration = False
    for config_key, group, display_name, description, is_secret in LLM_CONFIG_DEFINITIONS:
        cfg = config_map.get(config_key)
        if cfg:
            # 表中有记录
            if cfg.is_active:
                if cfg.is_secret:
                    raw_value = _decrypt_or_plaintext(cfg.config_value)
                    # 明文旧数据自动迁移：解密失败说明是明文，加密后回写
                    if raw_value == cfg.config_value and cfg.config_value:
                        cfg.config_value = encryption_service.encrypt(cfg.config_value)
                        needs_migration = True
                else:
                    raw_value = cfg.config_value
            else:
                raw_value = LLMConfigService.get_effective_value(config_key)
            items.append(LLMConfigItem(
                id=cfg.id,
                config_key=cfg.config_key,
                config_value=_mask_secret_value(raw_value) if is_secret and raw_value else raw_value,
                config_group=cfg.config_group,
                display_name=cfg.display_name,
                description=cfg.description,
                is_secret=cfg.is_secret,
                is_active=cfg.is_active,
                updated_at=cfg.updated_at,
            ).model_dump())
        else:
            # 表中无记录，从 .env 读取
            raw_value = LLMConfigService.get_effective_value(config_key)
            items.append(LLMConfigItem(
                id=0,
                config_key=config_key,
                config_value=_mask_secret_value(raw_value) if is_secret and raw_value else raw_value,
                config_group=group,
                display_name=display_name,
                description=description,
                is_secret=is_secret,
                is_active=False,
                updated_at=None,
            ).model_dump())

    # 自动迁移：将明文 secret 配置加密存储
    if needs_migration:
        await db.commit()
        logger.info("已自动迁移明文 secret 配置为加密存储")

    return {"items": items}


@router.get("/llm-configs/status", response_model=LLMConfigStatusResponse)
async def get_llm_config_status(
    current_user: LoginAccount = Depends(get_llm_config_manager_user),
):
    """获取 LLM 配置状态（首启弹窗判定用，仅配置管理者可见）"""
    from app.services.llm_config_service import LLMConfigService

    return LLMConfigStatusResponse(configured=LLMConfigService.is_configured())


@router.put("/llm-configs/group/{group}")
async def update_llm_config_group(
    group: str,
    data: LLMConfigGroupUpdate,
    current_user: LoginAccount = Depends(get_llm_config_manager_user),
    db: AsyncSession = Depends(get_db),
):
    """整组更新 LLM 配置（单事务），保存后一次性应用该组到运行时

    updates 中 config_key 必须属于指定分组且不得重复；
    secret 的掩码/空值跳过（不修改），非敏感字段空值跳过，
    与前端"留空则不修改"语义一致。
    """
    from app.services.llm_config_service import LLM_CONFIG_DEFINITIONS, LLMConfigService

    metas = {d[0]: d for d in LLM_CONFIG_DEFINITIONS if d[1] == group}
    if not metas:
        raise HTTPException(status_code=404, detail="未知配置分组")

    result = await db.execute(
        select(LLMConfig).where(LLMConfig.config_group == group)
    )
    existing = {cfg.config_key: cfg for cfg in result.scalars().all()}

    seen: set[str] = set()
    for item in data.updates:
        meta = metas.get(item.config_key)
        if not meta:
            raise HTTPException(
                status_code=400,
                detail=f"配置项 {item.config_key} 不属于分组 {group}",
            )
        if item.config_key in seen:
            raise HTTPException(
                status_code=400,
                detail=f"配置项 {item.config_key} 重复提交",
            )
        seen.add(item.config_key)

        _, _, display_name, description, is_secret = meta
        value = item.config_value.strip()
        # 空值 / secret 掩码 → 不修改
        if not value or (is_secret and value.startswith("****")):
            continue

        stored_value = encryption_service.encrypt(value) if is_secret else value
        cfg = existing.get(item.config_key)
        if cfg:
            cfg.config_value = stored_value
            cfg.is_active = True
        else:
            db.add(LLMConfig(
                config_key=item.config_key,
                config_value=stored_value,
                config_group=group,
                display_name=display_name,
                description=description,
                is_secret=is_secret,
                is_active=True,
            ))

    await db.commit()

    # 单事务落库后，将该组活跃配置一次性应用到运行时
    active_result = await db.execute(
        select(LLMConfig).where(
            LLMConfig.is_active == True,  # noqa: E712
            LLMConfig.config_group == group,
        )
    )
    LLMConfigService().apply_configs(active_result.scalars().all())

    # 返回整组最新配置（secret 掩码）
    result = await db.execute(
        select(LLMConfig)
        .where(LLMConfig.config_group == group)
        .order_by(LLMConfig.id)
    )
    items = []
    for cfg in result.scalars().all():
        raw = (
            _decrypt_or_plaintext(cfg.config_value)
            if cfg.is_secret and cfg.config_value
            else cfg.config_value
        )
        items.append(LLMConfigItem(
            id=cfg.id,
            config_key=cfg.config_key,
            config_value=_mask_secret_value(raw) if cfg.is_secret and raw else raw,
            config_group=cfg.config_group,
            display_name=cfg.display_name,
            description=cfg.description,
            is_secret=cfg.is_secret,
            is_active=cfg.is_active,
            updated_at=cfg.updated_at,
        ).model_dump())
    return {"items": items}


@router.post("/llm-configs/test", response_model=LLMConfigTestResponse)
async def test_llm_config(
    data: LLMConfigTestRequest,
    current_user: LoginAccount = Depends(get_llm_config_manager_user),
):
    """测试指定配置组的 LLM 连通性

    请求中携带的 api_key/api_base/model_name 为表单即时值，优先于已保存配置，
    支持未保存直接测试；缺省字段回退到当前生效配置。
    """
    from app.services.llm_config_service import LLMConfigService

    result = await LLMConfigService.test_group(
        data.group,
        overrides={
            "api_key": data.api_key or "",
            "api_base": data.api_base or "",
            "model_name": data.model_name or "",
        },
    )
    return LLMConfigTestResponse(**result)
