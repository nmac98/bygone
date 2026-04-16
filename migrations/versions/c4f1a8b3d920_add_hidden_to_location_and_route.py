"""add hidden to location and route

Revision ID: c4f1a8b3d920
Revises: 27a9da997fc5
Create Date: 2026-04-16 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c4f1a8b3d920'
down_revision = '27a9da997fc5'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('location', schema=None) as batch_op:
        batch_op.add_column(sa.Column('hidden', sa.Boolean(), nullable=False, server_default='false'))

    with op.batch_alter_table('route', schema=None) as batch_op:
        batch_op.add_column(sa.Column('hidden', sa.Boolean(), nullable=False, server_default='false'))


def downgrade():
    with op.batch_alter_table('location', schema=None) as batch_op:
        batch_op.drop_column('hidden')

    with op.batch_alter_table('route', schema=None) as batch_op:
        batch_op.drop_column('hidden')
