"""Add claim_only role for shared kid account access

Revision ID: 8c9d0e1f2a3b
Revises: 3c496b1f8493
Create Date: 2025-12-05 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8c9d0e1f2a3b'
down_revision = '3c496b1f8493'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add 'claim_only' role to user role constraint.

    This allows a shared kids account to have limited UI access - only able to
    view the Today page and claim chores on behalf of any kid. Perfect for a
    wall-mounted dashboard where individual kid login is not practical.
    """
    # SQLite doesn't support ALTER TABLE...DROP CONSTRAINT directly
    # We need to recreate the table with the new constraint

    with op.batch_alter_table('users', schema=None) as batch_op:
        # Drop the old constraint
        batch_op.drop_constraint('check_user_role', type_='check')

        # Add new constraint with 'claim_only' role
        batch_op.create_check_constraint(
            'check_user_role',
            "role IN ('parent', 'kid', 'system', 'unmapped', 'claim_only')"
        )


def downgrade():
    """
    Remove 'claim_only' role from constraint.

    WARNING: This will fail if any users have role='claim_only'.
    Delete or reassign those users before downgrading.
    """
    with op.batch_alter_table('users', schema=None) as batch_op:
        # Drop the constraint with claim_only
        batch_op.drop_constraint('check_user_role', type_='check')

        # Restore constraint without claim_only
        batch_op.create_check_constraint(
            'check_user_role',
            "role IN ('parent', 'kid', 'system', 'unmapped')"
        )
