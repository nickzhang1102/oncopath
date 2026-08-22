"""Remove unused system_prompt column from prompt_config.

The field was never consumed: MedicalPromptBuilder only reads
user_content_config, and AgentTeams launch sends a single message.

Revision ID: drop_prompt_config_system_prompt
Revises: agentteams_launch_manual_review_audit
"""

from alembic import op
import sqlalchemy as sa


revision = "drop_prompt_config_system_prompt"
down_revision = "agentteams_launch_manual_review_audit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("prompt_config", "system_prompt")


def downgrade() -> None:
    op.add_column(
        "prompt_config",
        sa.Column("system_prompt", sa.Text(), nullable=False, server_default="你是一名肿瘤科专家"),
    )
