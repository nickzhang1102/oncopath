"""enforce singleton agentteams integration config

Revision ID: agentteams_config_singleton
Revises: drop_follow_up_reminder
Create Date: 2026-08-28
"""
from alembic import op
import sqlalchemy as sa


revision = "agentteams_config_singleton"
down_revision = "drop_follow_up_reminder"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 历史脏数据清理：并发首次保存可能产生多行，服务层始终读取最小 id，
    # 保留最小 id 行（运行时实际生效的配置），删除其余行。
    op.execute(
        "DELETE FROM agentteams_integration_configs a "
        "USING agentteams_integration_configs b "
        "WHERE a.id > b.id"
    )
    op.add_column(
        "agentteams_integration_configs",
        sa.Column(
            "singleton",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.create_unique_constraint(
        "uq_agentteams_integration_configs_singleton",
        "agentteams_integration_configs",
        ["singleton"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_agentteams_integration_configs_singleton",
        "agentteams_integration_configs",
        type_="unique",
    )
    op.drop_column("agentteams_integration_configs", "singleton")
