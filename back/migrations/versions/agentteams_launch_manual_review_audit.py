"""Add manual review audit trail for AgentTeams launch intents.

Revision ID: agentteams_launch_manual_review_audit
Revises: agentteams_launch_intent_payload_retention
"""

from alembic import op
import sqlalchemy as sa


revision = "agentteams_launch_manual_review_audit"
down_revision = "agentteams_launch_intent_payload_retention"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agentteams_launch_intent_audits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("intent_id", sa.Integer(), nullable=True),
        sa.Column("request_id", sa.String(length=100), nullable=False),
        sa.Column("actor_account_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("before_status", sa.String(length=20), nullable=False),
        sa.Column("after_status", sa.String(length=20), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["intent_id"],
            ["agentteams_launch_intents.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["actor_account_id"],
            ["login_account.account_id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_agentteams_launch_intent_audits_intent_id",
        "agentteams_launch_intent_audits",
        ["intent_id"],
    )
    op.create_index(
        "ix_agentteams_launch_intent_audits_request_id",
        "agentteams_launch_intent_audits",
        ["request_id"],
    )
    op.create_index(
        "ix_agentteams_launch_intent_audits_actor_account_id",
        "agentteams_launch_intent_audits",
        ["actor_account_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_agentteams_launch_intent_audits_actor_account_id",
        table_name="agentteams_launch_intent_audits",
    )
    op.drop_index(
        "ix_agentteams_launch_intent_audits_request_id",
        table_name="agentteams_launch_intent_audits",
    )
    op.drop_index(
        "ix_agentteams_launch_intent_audits_intent_id",
        table_name="agentteams_launch_intent_audits",
    )
    op.drop_table("agentteams_launch_intent_audits")
