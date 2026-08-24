"""Remove unused system_prompt column from prompt_config.

The field was never consumed: MedicalPromptBuilder only reads
user_content_config, and AgentTeams launch sends a single message.

Revision ID: drop_prompt_config_system_prompt
Revises: agentteams_launch_manual_review_audit
"""

from alembic import op


revision = "drop_prompt_config_system_prompt"
down_revision = "agentteams_launch_manual_review_audit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 全新库由 public_schema_baseline 建表，本就无此列，必须条件删除
    op.execute('ALTER TABLE prompt_config DROP COLUMN IF EXISTS system_prompt')


def downgrade() -> None:
    op.execute(
        'ALTER TABLE prompt_config ADD COLUMN IF NOT EXISTS system_prompt '
        'TEXT NOT NULL DEFAULT \'你是一名肿瘤科专家\''
    )
