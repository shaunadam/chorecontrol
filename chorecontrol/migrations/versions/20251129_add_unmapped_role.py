"""Add unmapped role for HA user mapping

Revision ID: 7b8c9d4e5f6a
Revises: 86674e061ea9
Create Date: 2025-11-29 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7b8c9d4e5f6a'
down_revision = '86674e061ea9'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add 'unmapped' role to user role constraint.

    This allows auto-created HA users to have a temporary 'unmapped' status
    until a parent assigns them to 'parent' or 'kid' role via the mapping UI.
    """
    # SQLite doesn't support ALTER TABLE...DROP CONSTRAINT directly
    # We need to recreate the table with the new constraint

    with op.batch_alter_table('users', schema=None) as batch_op:
        # Drop the old constraint
        batch_op.drop_constraint('check_user_role', type_='check')

        # Add new constraint with 'unmapped' role
        batch_op.create_check_constraint(
            'check_user_role',
            "role IN ('parent', 'kid', 'system', 'unmapped')"
        )


def downgrade():
    """
    Remove 'unmapped' role from constraint.

    WARNING: This will fail if any users have role='unmapped'.
    Delete or reassign those users before downgrading.
    """
    with op.batch_alter_table('users', schema=None) as batch_op:
        # Drop the constraint with unmapped
        batch_op.drop_constraint('check_user_role', type_='check')

        # Restore original constraint
        batch_op.create_check_constraint(
            'check_user_role',
            "role IN ('parent', 'kid', 'system')"
        )
