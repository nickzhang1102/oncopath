"""Add durable AgentTeams launch intents.

Revision ID: agentteams_launch_intents
Revises: agentteams_request_id
"""

from alembic import op
import sqlalchemy as sa


revision = "agentteams_launch_intents"
down_revision = "agentteams_request_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agentteams_launch_intents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("request_id", sa.String(length=100), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("payload_ciphertext", sa.Text(), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("external_conversation_id", sa.String(length=100), nullable=True),
        sa.Column("external_session_id", sa.String(length=100), nullable=True),
        sa.Column("external_share_token", sa.String(length=200), nullable=True),
        sa.Column("embed_url", sa.Text(), nullable=True),
        sa.Column("remote_status", sa.String(length=20), nullable=True),
        sa.Column("last_error_status", sa.Integer(), nullable=True),
        sa.Column("last_error_code", sa.String(length=100), nullable=True),
        sa.Column("last_error_message", sa.Text(), nullable=True),
        sa.Column("dispatch_started_at", sa.DateTime(), nullable=True),
        sa.Column("lease_owner", sa.String(length=64), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(), nullable=True),
        sa.Column("next_attempt_at", sa.DateTime(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["login_account.account_id"]),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["patient_id"], ["patient.patient_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("conversation_id"),
        sa.UniqueConstraint(
            "provider",
            "request_id",
            name="uq_agentteams_launch_intent_provider_request",
        ),
    )
    op.create_index(
        "ix_agentteams_launch_intent_patient_status",
        "agentteams_launch_intents",
        ["account_id", "patient_id", "status"],
    )
    op.create_index(
        "ix_agentteams_launch_intents_account_id",
        "agentteams_launch_intents",
        ["account_id"],
    )
    op.create_index(
        "ix_agentteams_launch_intents_conversation_id",
        "agentteams_launch_intents",
        ["conversation_id"],
        unique=True,
    )
    op.create_index(
        "ix_agentteams_launch_intents_patient_id",
        "agentteams_launch_intents",
        ["patient_id"],
    )
    op.create_index(
        "ix_agentteams_launch_intents_status",
        "agentteams_launch_intents",
        ["status"],
    )
    op.create_index(
        "ix_agentteams_launch_intents_lease_owner",
        "agentteams_launch_intents",
        ["lease_owner"],
    )
    op.create_index(
        "ix_agentteams_launch_intents_lease_expires_at",
        "agentteams_launch_intents",
        ["lease_expires_at"],
    )
    op.create_index(
        "ix_agentteams_launch_intents_next_attempt_at",
        "agentteams_launch_intents",
        ["next_attempt_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_agentteams_launch_intents_next_attempt_at", table_name="agentteams_launch_intents")
    op.drop_index("ix_agentteams_launch_intents_lease_expires_at", table_name="agentteams_launch_intents")
    op.drop_index("ix_agentteams_launch_intents_lease_owner", table_name="agentteams_launch_intents")
    op.drop_index("ix_agentteams_launch_intents_status", table_name="agentteams_launch_intents")
    op.drop_index("ix_agentteams_launch_intents_patient_id", table_name="agentteams_launch_intents")
    op.drop_index("ix_agentteams_launch_intents_conversation_id", table_name="agentteams_launch_intents")
    op.drop_index("ix_agentteams_launch_intents_account_id", table_name="agentteams_launch_intents")
    op.drop_index("ix_agentteams_launch_intent_patient_status", table_name="agentteams_launch_intents")
    op.drop_table("agentteams_launch_intents")
