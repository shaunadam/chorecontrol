"""
Background jobs for ChoreControl.

This package contains scheduled jobs that run in the background:
- instance_generator: Daily chore instance generation
- auto_approval: Automatic approval of claimed chores
- missed_instances: Mark overdue instances as missed
- reward_expiration: Expire pending reward claims
- points_audit: Audit user points balances
"""

from addon.jobs.instance_generator import generate_daily_instances
from addon.jobs.auto_approval import check_auto_approvals
from addon.jobs.missed_instances import mark_missed_instances
from addon.jobs.reward_expiration import expire_pending_rewards
from addon.jobs.points_audit import audit_points_balances

__all__ = [
    'generate_daily_instances',
    'check_auto_approvals',
    'mark_missed_instances',
    'expire_pending_rewards',
    'audit_points_balances'
]
