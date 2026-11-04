"""Per-user monitoring schedules; password monitoring never stores secret material.

Revision ID: af43b7d1c202
Revises: 236780708991
"""
from alembic import op
import sqlalchemy as sa

revision = 'af43b7d1c202'
down_revision = '236780708991'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('monitoring_preferences',
        sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('email_enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('email_interval', sa.String(length=8), nullable=False, server_default='24h'),
        sa.Column('password_enabled', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('password_interval', sa.String(length=8), nullable=False, server_default='7d'),
    )


def downgrade():
    op.drop_table('monitoring_preferences')
