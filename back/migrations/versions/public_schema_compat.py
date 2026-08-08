"""统一原私有迁移链创建的数据库结构。

版本 ID：public_schema_compat
父版本：drop_billing_appointment
创建日期：2026-08-08

全新数据库已经通过 ``public_schema_baseline`` 获得目标结构。停留在
``drop_billing_appointment`` 的现有部署仍使用私有迁移链中等效的约束和索引
布局，并且缺少当前列注释。下面的检查确保两条路径都能安全升级。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "public_schema_compat"
down_revision: Union[str, Sequence[str], None] = "drop_billing_appointment"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CONFIG_TABLE = "agentteams_integration_configs"
SESSION_TABLE = "consultation_external_sessions"
CONVERSATION_CONSTRAINT = "uq_consultation_external_conversation"
CONVERSATION_INDEX = "ix_consultation_external_sessions_conversation_id"
ID_INDEX = "ix_consultation_external_sessions_id"

CONFIG_COMMENTS = {
    "base_url": (sa.String(length=500), "AgentTeams 部署地址或同站反代路径"),
    "integration_secret": (sa.Text(), "加密存储的 AgentTeams 集成密钥"),
    "enabled": (sa.Boolean(), "是否启用 AgentTeams 集成"),
    "upsell_title": (sa.String(length=100), "未配置提示标题"),
    "upsell_message": (sa.Text(), "未配置提示说明"),
    "demo_asset_url": (sa.String(length=500), "演示资源 URL"),
    "cta_label": (sa.String(length=100), "行动按钮文案"),
    "cta_url": (sa.String(length=500), "行动按钮 URL"),
}


def _inspector() -> sa.Inspector:
    return sa.inspect(op.get_bind())


def _index_map() -> dict[str, dict]:
    return {
        index["name"]: index
        for index in _inspector().get_indexes(SESSION_TABLE)
    }


def upgrade() -> None:
    for column_name, (column_type, comment) in CONFIG_COMMENTS.items():
        op.alter_column(
            CONFIG_TABLE,
            column_name,
            existing_type=column_type,
            comment=comment,
        )

    constraint_names = {
        constraint["name"]
        for constraint in _inspector().get_unique_constraints(SESSION_TABLE)
    }
    if CONVERSATION_CONSTRAINT in constraint_names:
        op.drop_constraint(
            CONVERSATION_CONSTRAINT,
            SESSION_TABLE,
            type_="unique",
        )

    indexes = _index_map()
    conversation_index = indexes.get(CONVERSATION_INDEX)
    if conversation_index is not None and not conversation_index.get("unique"):
        op.drop_index(CONVERSATION_INDEX, table_name=SESSION_TABLE)
        indexes = _index_map()

    if CONVERSATION_INDEX not in indexes:
        op.create_index(
            CONVERSATION_INDEX,
            SESSION_TABLE,
            ["conversation_id"],
            unique=True,
        )

    if ID_INDEX not in _index_map():
        op.create_index(ID_INDEX, SESSION_TABLE, ["id"], unique=False)


def downgrade() -> None:
    for column_name, (column_type, _) in CONFIG_COMMENTS.items():
        op.alter_column(
            CONFIG_TABLE,
            column_name,
            existing_type=column_type,
            comment=None,
        )

    indexes = _index_map()
    if ID_INDEX in indexes:
        op.drop_index(ID_INDEX, table_name=SESSION_TABLE)
    if CONVERSATION_INDEX in indexes:
        op.drop_index(CONVERSATION_INDEX, table_name=SESSION_TABLE)

    constraint_names = {
        constraint["name"]
        for constraint in _inspector().get_unique_constraints(SESSION_TABLE)
    }
    if CONVERSATION_CONSTRAINT not in constraint_names:
        op.create_unique_constraint(
            CONVERSATION_CONSTRAINT,
            SESSION_TABLE,
            ["conversation_id"],
        )
    op.create_index(
        CONVERSATION_INDEX,
        SESSION_TABLE,
        ["conversation_id"],
        unique=False,
    )
