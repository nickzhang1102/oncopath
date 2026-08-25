"""share_token 列宽扩容至 64，支持 256bit 分享令牌

Revision ID: share_token_256bit
Revises: drop_prompt_config_system_prompt
Create Date: 2026-08-25
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "share_token_256bit"
down_revision = "drop_prompt_config_system_prompt"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 旧 8 字符令牌在 varchar(64) 下继续有效，无需数据迁移
    op.alter_column(
        "conversations",
        "share_token",
        existing_type=sa.String(20),
        type_=sa.String(64),
        existing_nullable=True,
    )


def downgrade() -> None:
    # 注意：若已存在超过 20 字符的令牌，降级会失败；需先清理长令牌
    op.alter_column(
        "conversations",
        "share_token",
        existing_type=sa.String(64),
        type_=sa.String(20),
        existing_nullable=True,
    )
