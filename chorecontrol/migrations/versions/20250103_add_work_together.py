"""Add work-together support for shared chores

Revision ID: 20250103_work_together
Revises: 0a20ee519594
Create Date: 2025-01-03

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20250103_work_together'
down_revision = '0a20ee519594'
branch_labels = None
depends_on = None


def upgrade():
    # Add allow_work_together to chores table
    with op.batch_alter_table('chores', schema=None) as batch_op:
        batch_op.add_column(sa.Column('allow_work_together', sa.Boolean(), nullable=False, server_default='0'))

    # Add claiming_closed fields to chore_instances table
    with op.batch_alter_table('chore_instances', schema=None) as batch_op:
        batch_op.add_column(sa.Column('claiming_closed_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('claiming_closed_by', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_instances_claiming_closed_by', 'users', ['claiming_closed_by'], ['id'])

    # Create chore_instance_claims table
    op.create_table(
        'chore_instance_claims',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('chore_instance_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('claimed_at', sa.DateTime(), nullable=False),
        sa.Column('claimed_late', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='claimed'),
        sa.Column('approved_by', sa.Integer(), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('rejected_by', sa.Integer(), nullable=True),
        sa.Column('rejected_at', sa.DateTime(), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('points_awarded', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['chore_instance_id'], ['chore_instances.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['rejected_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('chore_instance_id', 'user_id', name='unique_instance_claim'),
        sa.CheckConstraint("status IN ('claimed', 'approved', 'rejected')", name='check_claim_status'),
    )
    op.create_index('idx_instance_claims_instance', 'chore_instance_claims', ['chore_instance_id'])
    op.create_index('idx_instance_claims_user', 'chore_instance_claims', ['user_id'])
    op.create_index('idx_instance_claims_status', 'chore_instance_claims', ['status'])


def downgrade():
    # Drop chore_instance_claims table
    op.drop_index('idx_instance_claims_status', table_name='chore_instance_claims')
    op.drop_index('idx_instance_claims_user', table_name='chore_instance_claims')
    op.drop_index('idx_instance_claims_instance', table_name='chore_instance_claims')
    op.drop_table('chore_instance_claims')

    # Remove claiming_closed fields from chore_instances
    with op.batch_alter_table('chore_instances', schema=None) as batch_op:
        batch_op.drop_constraint('fk_instances_claiming_closed_by', type_='foreignkey')
        batch_op.drop_column('claiming_closed_by')
        batch_op.drop_column('claiming_closed_at')

    # Remove allow_work_together from chores
    with op.batch_alter_table('chores', schema=None) as batch_op:
        batch_op.drop_column('allow_work_together')
