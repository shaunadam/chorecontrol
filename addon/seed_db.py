#!/usr/bin/env python3
"""
Simple seed script for ChoreControl database.
Creates system user and sample data with new business logic fields.
"""

from datetime import date, datetime, timedelta
import logging

from app import create_app
from models import db, User, Chore, ChoreAssignment, ChoreInstance, Reward, RewardClaim

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Main seed function."""
    print("\n🌱 ChoreControl Database Seeding")
    print("=" * 60)

    app = create_app()

    with app.app_context():
        # Create system user first
        system_user = User.query.filter_by(ha_user_id='system').first()
        if not system_user:
            system_user = User(
                ha_user_id='system',
                username='System',
                role='system',
                points=0
            )
            db.session.add(system_user)
            db.session.commit()
            logger.info("✓ Created system user")
        else:
            logger.info("✓ System user already exists")

        # Create users
        users_data = [
            {'ha_user_id': 'parent1', 'username': 'Mom', 'role': 'parent'},
            {'ha_user_id': 'parent2', 'username': 'Dad', 'role': 'parent'},
            {'ha_user_id': 'kid1', 'username': 'Alice', 'role': 'kid'},
            {'ha_user_id': 'kid2', 'username': 'Bob', 'role': 'kid'},
        ]

        users = []
        for user_data in users_data:
            existing = User.query.filter_by(ha_user_id=user_data['ha_user_id']).first()
            if not existing:
                user = User(**user_data)
                db.session.add(user)
                users.append(user)
                logger.info(f"✓ Created user: {user_data['username']} ({user_data['role']})")
            else:
                users.append(existing)
                logger.info(f"✓ User already exists: {user_data['username']}")

        db.session.commit()

        # Now seed chores, rewards, and instances
        parent = [u for u in users if u.role == 'parent'][0]
        kids = [u for u in users if u.role == 'kid']

        chores = seed_chores_internal(parent, kids)
        rewards = seed_rewards_internal()
        seed_sample_instances_internal(chores, kids)

    print("=" * 60)
    print("✨ Seeding complete!")
    print("=" * 60)


def seed_chores_internal(parent, kids):
    """Internal function to seed chores within an app context."""
    chores_data = [
        {
            'name': 'Make Bed',
            'points': 5,
            'recurrence_type': 'simple',
            'recurrence_pattern': {'type': 'daily'},
            'assignment_type': 'individual',
            'requires_approval': True,
            'allow_late_claims': True,
            'late_points': 3,
            'assigned_users': [kids[0].id, kids[1].id]
        },
        {
            'name': 'Take out trash',
            'points': 10,
            'recurrence_type': 'simple',
            'recurrence_pattern': {'type': 'weekly', 'days_of_week': [1, 4]},
            'assignment_type': 'shared',
            'requires_approval': True,
            'auto_approve_after_hours': 24,
            'allow_late_claims': False,
            'assigned_users': [kids[0].id, kids[1].id]
        },
        {
            'name': 'Clean room',
            'points': 15,
            'recurrence_type': 'simple',
            'recurrence_pattern': {'type': 'weekly', 'days_of_week': [6]},
            'assignment_type': 'individual',
            'requires_approval': True,
            'allow_late_claims': True,
            'late_points': 10,
            'assigned_users': [kids[0].id, kids[1].id]
        },
        {
            'name': 'Water plants',
            'points': 5,
            'recurrence_type': 'simple',
            'recurrence_pattern': {'type': 'monthly', 'days_of_month': [1, 15]},
            'assignment_type': 'shared',
            'requires_approval': True,
            'allow_late_claims': False,
            'assigned_users': [kids[0].id, kids[1].id]
        },
        {
            'name': 'Organize toys',
            'points': 8,
            'recurrence_type': 'none',
            'recurrence_pattern': None,
            'assignment_type': 'individual',
            'requires_approval': False,
            'allow_late_claims': True,
            'assigned_users': [kids[0].id]
        }
    ]

    chores = []
    for chore_data in chores_data:
        existing = Chore.query.filter_by(name=chore_data['name']).first()
        if existing:
            logger.info(f"✓ Chore already exists: {chore_data['name']}")
            chores.append(existing)
            continue

        assigned_users = chore_data.pop('assigned_users')

        chore = Chore(
            name=chore_data['name'],
            points=chore_data['points'],
            recurrence_type=chore_data['recurrence_type'],
            recurrence_pattern=chore_data.get('recurrence_pattern'),
            assignment_type=chore_data['assignment_type'],
            requires_approval=chore_data['requires_approval'],
            auto_approve_after_hours=chore_data.get('auto_approve_after_hours'),
            allow_late_claims=chore_data.get('allow_late_claims', False),
            late_points=chore_data.get('late_points'),
            created_by=parent.id,
            is_active=True
        )
        db.session.add(chore)
        db.session.flush()

        for user_id in assigned_users:
            assignment = ChoreAssignment(
                chore_id=chore.id,
                user_id=user_id
            )
            db.session.add(assignment)

        chores.append(chore)
        logger.info(f"✓ Created chore: {chore_data['name']}")

    db.session.commit()
    return chores


def seed_rewards_internal():
    """Internal function to seed rewards within an app context."""
    rewards_data = [
        {
            'name': '30 minutes screen time',
            'points_cost': 20,
            'requires_approval': False,
            'is_active': True
        },
        {
            'name': 'Pick dinner menu',
            'points_cost': 50,
            'requires_approval': True,
            'is_active': True
        },
        {
            'name': 'Stay up 30 min late',
            'points_cost': 30,
            'requires_approval': True,
            'cooldown_days': 7,
            'is_active': True
        },
        {
            'name': 'Choose movie night film',
            'points_cost': 40,
            'requires_approval': False,
            'max_claims_per_kid': 2,
            'is_active': True
        }
    ]

    rewards = []
    for reward_data in rewards_data:
        existing = Reward.query.filter_by(name=reward_data['name']).first()
        if existing:
            logger.info(f"✓ Reward already exists: {reward_data['name']}")
            rewards.append(existing)
            continue

        reward = Reward(**reward_data)
        db.session.add(reward)
        rewards.append(reward)
        logger.info(f"✓ Created reward: {reward_data['name']}")

    db.session.commit()
    return rewards


def seed_sample_instances_internal(chores, kids):
    """Internal function to create sample instances within an app context."""
    existing_count = ChoreInstance.query.count()
    if existing_count > 0:
        logger.info(f"✓ Sample instances already exist ({existing_count} instances)")
        return

    instances_data = [
        {
            'chore_id': chores[0].id,
            'due_date': date.today(),
            'status': 'claimed',
            'assigned_to': kids[0].id,
            'claimed_by': kids[0].id,
            'claimed_at': datetime.utcnow(),
            'claimed_late': False
        },
        {
            'chore_id': chores[0].id,
            'due_date': date.today() - timedelta(days=1),
            'status': 'claimed',
            'assigned_to': kids[1].id,
            'claimed_by': kids[1].id,
            'claimed_at': datetime.utcnow(),
            'claimed_late': True
        },
        {
            'chore_id': chores[1].id,
            'due_date': date.today() - timedelta(days=2),
            'status': 'missed',
            'assigned_to': None
        },
        {
            'chore_id': chores[0].id,
            'due_date': date.today() + timedelta(days=1),
            'status': 'assigned',
            'assigned_to': kids[0].id
        }
    ]

    for instance_data in instances_data:
        instance = ChoreInstance(**instance_data)
        db.session.add(instance)

    db.session.commit()
    logger.info(f"✓ Created {len(instances_data)} sample instances")


if __name__ == '__main__':
    main()
