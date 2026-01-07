"""Add extra field to chores

Revision ID: 20250106_extra
Revises: 20250103_work_together
Create Date: 2025-01-06

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20250106_extra'
down_revision = '20250103_work_together'
branch_labels = None
depends_on = None


def upgrade():
    # Add extra field to chores table
    with op.batch_alter_table('chores', schema=None) as batch_op:
        batch_op.add_column(sa.Column('extra', sa.Boolean(), nullable=False, server_default='0'))


def downgrade():
    # Remove extra field from chores
    with op.batch_alter_table('chores', schema=None) as batch_op:
        batch_op.drop_column('extra')
