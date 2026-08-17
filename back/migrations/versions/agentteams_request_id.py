"""Persist stable AgentTeams launch request identifiers.

Revision ID: agentteams_request_id
Revises: public_schema_compat
"""

from alembic import op
import sqlalchemy as sa


revision = "agentteams_request_id"
down_revision = "public_schema_compat"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "consultation_external_sessions",
        sa.Column("launch_request_id", sa.String(length=100), nullable=True),
    )
    op.create_unique_constraint(
        "uq_consultation_external_provider_request",
        "consultation_external_sessions",
        ["provider", "launch_request_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_consultation_external_provider_request",
        "consultation_external_sessions",
        type_="unique",
    )
    op.drop_column("consultation_external_sessions", "launch_request_id")
