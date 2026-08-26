"""移除随访提醒功能：删除 follow_up_reminder 表

该功能的推送链路（Celery worker/beat）从未纳入部署编排，提醒创建后
无法自动触达用户，状态机实际停留在 pending。功能已整体下线。

版本 ID：drop_follow_up_reminder
父版本：share_token_256bit
创建日期：2026-08-26
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "drop_follow_up_reminder"
down_revision = "share_token_256bit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index('idx_follow_up_patient_status', table_name='follow_up_reminder')
    op.drop_index(op.f('ix_follow_up_reminder_id'), table_name='follow_up_reminder')
    op.drop_table('follow_up_reminder')


def downgrade() -> None:
    op.create_table('follow_up_reminder',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('patient_id', sa.Integer(), nullable=False),
    sa.Column('account_id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False, comment='提醒标题'),
    sa.Column('description', sa.Text(), nullable=True, comment='描述'),
    sa.Column('reminder_date', sa.Date(), nullable=False, comment='提醒日期'),
    sa.Column('status', sa.String(length=20), nullable=True, comment='状态: pending/sent/confirmed/expired'),
    sa.Column('source_type', sa.String(length=30), nullable=True, comment='来源: manual/interpretation/consultation'),
    sa.Column('source_id', sa.Integer(), nullable=True, comment='关联来源ID'),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['account_id'], ['login_account.account_id'], ),
    sa.ForeignKeyConstraint(['patient_id'], ['patient.patient_id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_follow_up_patient_status', 'follow_up_reminder', ['patient_id', 'status'], unique=False)
    op.create_index(op.f('ix_follow_up_reminder_id'), 'follow_up_reminder', ['id'], unique=False)
