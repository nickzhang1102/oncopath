"""Allow terminal launch intent payloads to be purged.

Revision ID: agentteams_launch_intent_payload_retention
Revises: agentteams_launch_intents
"""

from alembic import op
import sqlalchemy as sa


revision = "agentteams_launch_intent_payload_retention"
down_revision = "agentteams_launch_intents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "agentteams_launch_intents",
        "payload_ciphertext",
        existing_type=sa.Text(),
        nullable=True,
    )
    op.add_column(
        "agentteams_launch_intents",
        sa.Column("payload_purged_at", sa.DateTime(), nullable=True),
    )
    # Purge already-terminal rows as part of the schema rollout.  Unresolved
    # rows retain their immutable snapshot for read-only reconciliation.
    op.execute(
        sa.text(
            "UPDATE agentteams_launch_intents "
            "SET payload_ciphertext = NULL, payload_purged_at = CURRENT_TIMESTAMP "
            "WHERE status IN ('accepted', 'rejected') "
            "AND payload_ciphertext IS NOT NULL"
        )
    )


def downgrade() -> None:
    # Refuse to make the column required again if terminal rows were already
    # purged; inventing PHI to satisfy a downgrade would be unsafe.
    op.drop_column("agentteams_launch_intents", "payload_purged_at")
    op.alter_column(
        "agentteams_launch_intents",
        "payload_ciphertext",
        existing_type=sa.Text(),
        nullable=False,
    )
