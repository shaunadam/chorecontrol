"""
SQLAlchemy models for ChoreControl.

This module defines the database models for the chore management system.
Uses Flask-SQLAlchemy for ORM integration with Flask.
"""

from datetime import datetime, date, timedelta
from typing import Optional, List
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CheckConstraint, UniqueConstraint, Index
from sqlalchemy.orm import relationship

db = SQLAlchemy()


class User(db.Model):
    """User model representing both parents and kids in the system."""

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ha_user_id = db.Column(db.String(255), unique=True, nullable=False, index=True)
    username = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    points = db.Column(db.Integer, default=0, nullable=False)  # Denormalized, only for kids
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    chore_assignments = relationship('ChoreAssignment', back_populates='user', cascade='all, delete-orphan')
    claimed_instances = relationship('ChoreInstance', foreign_keys='ChoreInstance.claimed_by', back_populates='claimer')
    approved_instances = relationship('ChoreInstance', foreign_keys='ChoreInstance.approved_by', back_populates='approver')
    rejected_instances = relationship('ChoreInstance', foreign_keys='ChoreInstance.rejected_by', back_populates='rejecter')
    reward_claims = relationship('RewardClaim', foreign_keys='RewardClaim.user_id', back_populates='user', cascade='all, delete-orphan')
    points_history = relationship('PointsHistory', foreign_keys='PointsHistory.user_id', back_populates='user', cascade='all, delete-orphan')
    created_chores = relationship('Chore', foreign_keys='Chore.created_by', back_populates='creator')

    # Constraints
    __table_args__ = (
        CheckConstraint("role IN ('parent', 'kid', 'system')", name='check_user_role'),
    )

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'

    def to_dict(self) -> dict:
        """Serialize User to dictionary for JSON/webhook responses."""
        return {
            'id': self.id,
            'ha_user_id': self.ha_user_id,
            'username': self.username,
            'role': self.role,
            'points': self.points,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def calculate_current_points(self) -> int:
        """
        Calculate current points from points history (audit verification).
        Should match self.points field.

        Returns:
            int: Sum of all point deltas from history
        """
        from sqlalchemy import func
        total = db.session.query(func.sum(PointsHistory.points_delta)).filter(
            PointsHistory.user_id == self.id
        ).scalar()
        return total if total is not None else 0

    def verify_points_balance(self) -> bool:
        """
        Verify that the denormalized points field matches the calculated total.

        Returns:
            bool: True if points match, False if there's a discrepancy
        """
        calculated = self.calculate_current_points()
        return self.points == calculated

    def adjust_points(self, delta: int, reason: str, created_by_id: Optional[int] = None,
                     chore_instance_id: Optional[int] = None, reward_claim_id: Optional[int] = None) -> None:
        """
        Adjust user's points and create history entry.

        Args:
            delta: Points to add (positive) or subtract (negative)
            reason: Description of why points were adjusted
            created_by_id: User ID of who made the adjustment
            chore_instance_id: Optional reference to chore instance
            reward_claim_id: Optional reference to reward claim

        """
        import logging
        logger = logging.getLogger(__name__)

        self.points += delta

        history = PointsHistory(
            user_id=self.id,
            points_delta=delta,
            reason=reason,
            created_by=created_by_id,
            chore_instance_id=chore_instance_id,
            reward_claim_id=reward_claim_id
        )
        db.session.add(history)

        # Verify balance after transaction (log discrepancies but don't fail)
        # Note: Full verification done after commit in calling code
        # This is a quick sanity check during the transaction
        calculated = self.calculate_current_points() + delta  # Add delta since history not committed yet
        if self.points != calculated:
            logger.warning(f"Points mismatch detected for user {self.id}: stored={self.points}, calculated={calculated}")


class Chore(db.Model):
    """Chore model representing a chore template (recurring or one-off)."""

    __tablename__ = 'chores'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    points = db.Column(db.Integer, default=0, nullable=False)

    # Scheduling
    recurrence_type = db.Column(db.String(20))  # 'none', 'simple', 'complex'
    recurrence_pattern = db.Column(db.JSON)  # JSON storage for flexible patterns
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)

    # Assignment
    assignment_type = db.Column(db.String(20))  # 'individual' or 'shared'

    # Workflow
    requires_approval = db.Column(db.Boolean, default=True, nullable=False)
    auto_approve_after_hours = db.Column(db.Integer)  # NULL means no auto-approve
    allow_late_claims = db.Column(db.Boolean, default=False, nullable=False)
    late_points = db.Column(db.Integer, nullable=True)

    # Metadata
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Relationships
    creator = relationship('User', foreign_keys=[created_by], back_populates='created_chores')
    assignments = relationship('ChoreAssignment', back_populates='chore', cascade='all, delete-orphan')
    instances = relationship('ChoreInstance', back_populates='chore', cascade='all, delete-orphan')

    # Constraints
    __table_args__ = (
        CheckConstraint("recurrence_type IN ('none', 'simple', 'complex') OR recurrence_type IS NULL",
                       name='check_recurrence_type'),
        CheckConstraint("assignment_type IN ('individual', 'shared') OR assignment_type IS NULL",
                       name='check_assignment_type'),
    )

    def __repr__(self):
        return f'<Chore {self.name}>'

    def to_dict(self) -> dict:
        """Serialize Chore to dictionary for JSON/webhook responses."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'points': self.points,
            'recurrence_type': self.recurrence_type,
            'recurrence_pattern': self.recurrence_pattern,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'assignment_type': self.assignment_type,
            'requires_approval': self.requires_approval,
            'auto_approve_after_hours': self.auto_approve_after_hours,
            'allow_late_claims': self.allow_late_claims,
            'late_points': self.late_points,
            'is_active': self.is_active,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def is_due(self, check_date: Optional[date] = None) -> bool:
        """
        Check if this chore is due on the given date.

        Args:
            check_date: Date to check (defaults to today)

        Returns:
            bool: True if chore is due on the given date
        """
        if check_date is None:
            check_date = date.today()

        if not self.is_active:
            return False

        if self.start_date and check_date < self.start_date:
            return False

        if self.end_date and check_date > self.end_date:
            return False

        if self.recurrence_type == 'none':
            return check_date == self.start_date if self.start_date else False

        # For recurring chores, check pattern (implement in schemas.py)
        return True  # Placeholder - actual logic in generate_next_instance

    def generate_next_instance(self, after_date: Optional[date] = None) -> Optional['ChoreInstance']:
        """
        Generate the next chore instance based on recurrence pattern.

        Args:
            after_date: Generate instance after this date (defaults to today)

        Returns:
            ChoreInstance: New instance or None if no more instances
        """
        if not self.is_active:
            return None

        if after_date is None:
            after_date = date.today()

        if self.end_date and after_date > self.end_date:
            return None

        # Determine next due date based on recurrence pattern
        from schemas import calculate_next_due_date
        next_date = calculate_next_due_date(self.recurrence_pattern, after_date)

        if next_date is None:
            return None

        if self.end_date and next_date > self.end_date:
            return None

        # Create instance
        instance = ChoreInstance(
            chore_id=self.id,
            due_date=next_date,
            status='assigned'
        )

        return instance


class ChoreAssignment(db.Model):
    """Assignment of a chore to a specific user."""

    __tablename__ = 'chore_assignments'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    chore_id = db.Column(db.Integer, db.ForeignKey('chores.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    due_date = db.Column(db.Date)  # For recurring chores, specific instance date

    # Relationships
    chore = relationship('Chore', back_populates='assignments')
    user = relationship('User', back_populates='chore_assignments')

    # Constraints
    __table_args__ = (
        UniqueConstraint('chore_id', 'user_id', 'due_date', name='unique_chore_user_date'),
        Index('idx_chore_assignments_chore_user', 'chore_id', 'user_id'),
    )

    def __repr__(self):
        return f'<ChoreAssignment chore_id={self.chore_id} user_id={self.user_id}>'


class ChoreInstance(db.Model):
    """Individual instance of a chore completion/claim."""

    __tablename__ = 'chore_instances'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    chore_id = db.Column(db.Integer, db.ForeignKey('chores.id'), nullable=False)
    due_date = db.Column(db.Date, nullable=True)
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    # Status tracking
    status = db.Column(db.String(20), default='assigned', nullable=False)

    # Who did what when
    claimed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    claimed_at = db.Column(db.DateTime)
    claimed_late = db.Column(db.Boolean, default=False, nullable=False)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    approved_at = db.Column(db.DateTime)
    rejected_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    rejected_at = db.Column(db.DateTime)
    rejection_reason = db.Column(db.Text)

    # Points awarded (may differ from chore.points for bonuses/penalties)
    points_awarded = db.Column(db.Integer)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    chore = relationship('Chore', back_populates='instances')
    assignee = relationship('User', foreign_keys=[assigned_to])
    claimer = relationship('User', foreign_keys=[claimed_by], back_populates='claimed_instances')
    approver = relationship('User', foreign_keys=[approved_by], back_populates='approved_instances')
    rejecter = relationship('User', foreign_keys=[rejected_by], back_populates='rejected_instances')
    points_history_entries = relationship('PointsHistory', back_populates='chore_instance')

    # Constraints
    __table_args__ = (
        CheckConstraint("status IN ('assigned', 'claimed', 'approved', 'rejected', 'missed')",
                       name='check_instance_status'),
        Index('idx_chore_instances_status', 'status'),
        Index('idx_chore_instances_due_date', 'due_date'),
        Index('idx_chore_instances_assigned_to', 'assigned_to'),
    )

    def __repr__(self):
        return f'<ChoreInstance chore_id={self.chore_id} due={self.due_date} status={self.status}>'

    def to_dict(self) -> dict:
        """Serialize ChoreInstance to dictionary for JSON/webhook responses."""
        result = {
            'id': self.id,
            'chore_id': self.chore_id,
            'chore_name': self.chore.name if self.chore else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'status': self.status,
            'assigned_to': self.assigned_to,
            'assigned_to_name': self.assignee.username if self.assignee else None,
            'claimed_by': self.claimed_by,
            'claimed_by_name': self.claimer.username if self.claimer else None,
            'claimed_at': self.claimed_at.isoformat() if self.claimed_at else None,
            'claimed_late': self.claimed_late,
            'approved_by': self.approved_by,
            'approved_by_name': self.approver.username if self.approver else None,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'rejected_by': self.rejected_by,
            'rejected_by_name': self.rejecter.username if self.rejecter else None,
            'rejected_at': self.rejected_at.isoformat() if self.rejected_at else None,
            'rejection_reason': self.rejection_reason,
            'points_awarded': self.points_awarded,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        return result

    def can_claim(self, user_id: int) -> bool:
        """
        Check if a user can claim this chore instance.

        Args:
            user_id: ID of user attempting to claim

        Returns:
            bool: True if user can claim this instance
        """
        # Must be in 'assigned' status
        if self.status != 'assigned':
            return False

        # Check if claimable based on due_date (Option B: Strict)
        if self.due_date is not None:
            today = date.today()

            # Cannot claim future chores
            if self.due_date > today:
                return False

            # If past due and late claims not allowed, should be 'missed'
            if self.due_date < today and not self.chore.allow_late_claims:
                return False

        # Check assignment
        # For individual chores
        if self.assigned_to is not None:
            return self.assigned_to == user_id

        # For shared chores
        assignment = ChoreAssignment.query.filter_by(
            chore_id=self.chore_id,
            user_id=user_id
        ).first()

        return assignment is not None

    def can_approve(self, user_id: int) -> bool:
        """
        Check if a user can approve this chore instance.

        Args:
            user_id: ID of user attempting to approve

        Returns:
            bool: True if user can approve this instance
        """
        if self.status != 'claimed':
            return False

        # Check if user is a parent
        user = User.query.get(user_id)
        return user is not None and user.role == 'parent'

    def award_points(self, approver_id: int, points: Optional[int] = None) -> None:
        """
        Award points to the user who claimed this chore.

        Args:
            approver_id: ID of user approving the chore
            points: Points to award (optional parent override)
        """
        if self.status != 'claimed':
            raise ValueError("Cannot award points for non-claimed chore")

        if self.claimed_by is None:
            raise ValueError("Cannot award points without a claimer")

        # Determine points to award
        if points is not None:
            # Parent override
            points_to_award = points
        elif self.claimed_late and self.chore.late_points is not None:
            # Late completion with late_points set
            points_to_award = self.chore.late_points
        else:
            # Normal or late completion without late_points override
            points_to_award = self.chore.points

        self.points_awarded = points_to_award

        # Update status
        self.status = 'approved'
        self.approved_by = approver_id
        self.approved_at = datetime.utcnow()

        # Award points to user
        claimer = User.query.get(self.claimed_by)
        if claimer:
            claimer.adjust_points(
                delta=points_to_award,
                reason=f"Completed chore: {self.chore.name}",
                created_by_id=approver_id,
                chore_instance_id=self.id
            )


class Reward(db.Model):
    """Reward that can be claimed by kids using points."""

    __tablename__ = 'rewards'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    points_cost = db.Column(db.Integer, nullable=False)

    # Limits
    cooldown_days = db.Column(db.Integer)  # NULL means no cooldown
    max_claims_total = db.Column(db.Integer)  # NULL means unlimited
    max_claims_per_kid = db.Column(db.Integer)  # NULL means unlimited
    requires_approval = db.Column(db.Boolean, default=False, nullable=False)

    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    claims = relationship('RewardClaim', back_populates='reward', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Reward {self.name} ({self.points_cost} pts)>'

    def to_dict(self) -> dict:
        """Serialize Reward to dictionary for JSON/webhook responses."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'points_cost': self.points_cost,
            'cooldown_days': self.cooldown_days,
            'max_claims_total': self.max_claims_total,
            'max_claims_per_kid': self.max_claims_per_kid,
            'requires_approval': self.requires_approval,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def can_claim(self, user_id: int) -> tuple[bool, Optional[str]]:
        """
        Check if a user can claim this reward.

        Args:
            user_id: ID of user attempting to claim

        Returns:
            tuple: (can_claim: bool, reason: str if False)
        """
        if not self.is_active:
            return False, "Reward is not active"

        user = User.query.get(user_id)
        if not user:
            return False, "User not found"

        if user.role != 'kid':
            return False, "Only kids can claim rewards"

        if user.points < self.points_cost:
            return False, f"Insufficient points (need {self.points_cost}, have {user.points})"

        # Check max claims total
        if self.max_claims_total is not None:
            total_claims = RewardClaim.query.filter_by(
                reward_id=self.id,
                status='approved'
            ).count()
            if total_claims >= self.max_claims_total:
                return False, "Reward has reached maximum claims"

        # Check max claims per kid
        if self.max_claims_per_kid is not None:
            user_claims = RewardClaim.query.filter_by(
                reward_id=self.id,
                user_id=user_id,
                status='approved'
            ).count()
            if user_claims >= self.max_claims_per_kid:
                return False, "You have reached maximum claims for this reward"

        # Check cooldown
        if self.cooldown_days is not None:
            cooldown_result, cooldown_msg = self.is_on_cooldown(user_id)
            if cooldown_result:
                return False, cooldown_msg

        return True, None

    def is_on_cooldown(self, user_id: int) -> tuple[bool, Optional[str]]:
        """
        Check if this reward is on cooldown for a specific user.

        Args:
            user_id: ID of user to check cooldown for

        Returns:
            tuple: (is_on_cooldown: bool, message: str if on cooldown)
        """
        if self.cooldown_days is None:
            return False, None

        last_claim = RewardClaim.query.filter_by(
            reward_id=self.id,
            user_id=user_id,
            status='approved'
        ).order_by(RewardClaim.claimed_at.desc()).first()

        if last_claim:
            cooldown_end = last_claim.claimed_at + timedelta(days=self.cooldown_days)
            if datetime.utcnow() < cooldown_end:
                days_left = (cooldown_end - datetime.utcnow()).days + 1
                return True, f"Reward is on cooldown for {days_left} more days"

        return False, None


class RewardClaim(db.Model):
    """Record of a reward being claimed by a user."""

    __tablename__ = 'reward_claims'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    reward_id = db.Column(db.Integer, db.ForeignKey('rewards.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    points_spent = db.Column(db.Integer, nullable=False)
    claimed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=True)

    # Approval workflow (optional for rewards)
    status = db.Column(db.String(20), default='approved', nullable=False)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    approved_at = db.Column(db.DateTime)

    # Relationships
    reward = relationship('Reward', back_populates='claims')
    user = relationship('User', foreign_keys=[user_id], back_populates='reward_claims')
    approver = relationship('User', foreign_keys=[approved_by])
    points_history_entries = relationship('PointsHistory', back_populates='reward_claim')

    # Constraints
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'approved', 'rejected')",
                       name='check_reward_claim_status'),
        Index('idx_reward_claims_user', 'user_id'),
        Index('idx_reward_claims_claimed_at', 'claimed_at'),
    )

    def __repr__(self):
        return f'<RewardClaim reward_id={self.reward_id} user_id={self.user_id}>'

    def to_dict(self) -> dict:
        """Serialize RewardClaim to dictionary for JSON/webhook responses."""
        return {
            'id': self.id,
            'reward_id': self.reward_id,
            'reward_name': self.reward.name if self.reward else None,
            'user_id': self.user_id,
            'user_name': self.user.username if self.user else None,
            'points_spent': self.points_spent,
            'claimed_at': self.claimed_at.isoformat() if self.claimed_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'status': self.status,
            'approved_by': self.approved_by,
            'approved_by_name': self.approver.username if self.approver else None,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None
        }


class PointsHistory(db.Model):
    """Audit log of all point changes."""

    __tablename__ = 'points_history'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    points_delta = db.Column(db.Integer, nullable=False)  # Can be negative
    reason = db.Column(db.Text, nullable=False)

    # Reference to what caused this change
    chore_instance_id = db.Column(db.Integer, db.ForeignKey('chore_instances.id'))
    reward_claim_id = db.Column(db.Integer, db.ForeignKey('reward_claims.id'))

    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))  # Who made the change
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship('User', foreign_keys=[user_id], back_populates='points_history')
    creator = relationship('User', foreign_keys=[created_by])
    chore_instance = relationship('ChoreInstance', back_populates='points_history_entries')
    reward_claim = relationship('RewardClaim', back_populates='points_history_entries')

    # Indexes
    __table_args__ = (
        Index('idx_points_history_user', 'user_id'),
        Index('idx_points_history_created_at', 'created_at'),
    )

    def __repr__(self):
        return f'<PointsHistory user_id={self.user_id} delta={self.points_delta}>'

    def to_dict(self) -> dict:
        """Serialize PointsHistory to dictionary for JSON/webhook responses."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'points_delta': self.points_delta,
            'reason': self.reason,
            'chore_instance_id': self.chore_instance_id,
            'reward_claim_id': self.reward_claim_id,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
