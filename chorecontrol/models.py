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
from werkzeug.security import generate_password_hash, check_password_hash

from utils.timezone import local_today

db = SQLAlchemy()


class User(db.Model):
    """User model representing both parents and kids in the system."""

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ha_user_id = db.Column(db.String(255), unique=True, nullable=False, index=True)
    username = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    points = db.Column(db.Integer, default=0, nullable=False)  # Denormalized, only for kids
    password_hash = db.Column(db.String(255), nullable=True)  # NULL for HA-only users
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
        CheckConstraint("role IN ('parent', 'kid', 'system', 'unmapped', 'claim_only')", name='check_user_role'),
    )

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'

    def set_password(self, password: str) -> None:
        """Set password hash from plaintext password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Check if provided password matches the stored hash."""
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def has_password(self) -> bool:
        """Check if user has a password set (for local login)."""
        return self.password_hash is not None

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
        db.session.flush()  # Flush so history is visible to the query

        # Verify balance after transaction (log discrepancies but don't fail)
        # Note: Full verification done after commit in calling code
        # This is a quick sanity check during the transaction
        calculated = self.calculate_current_points()
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
    allow_work_together = db.Column(db.Boolean, default=False, nullable=False)  # For shared: allow multiple kids to claim

    # Workflow
    requires_approval = db.Column(db.Boolean, default=True, nullable=False)
    auto_approve_after_hours = db.Column(db.Integer)  # NULL means no auto-approve
    allow_late_claims = db.Column(db.Boolean, default=False, nullable=False)  # Deprecated: use grace_period_days
    late_points = db.Column(db.Integer, nullable=True)

    # Claiming windows
    early_claim_days = db.Column(db.Integer, default=0, nullable=False)  # Days before due date chore can be claimed
    grace_period_days = db.Column(db.Integer, default=0, nullable=False)  # Days after due date chore can still be claimed
    expires_after_days = db.Column(db.Integer, nullable=True)  # For anytime chores: days until expiration

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
            'allow_work_together': self.allow_work_together,
            'requires_approval': self.requires_approval,
            'auto_approve_after_hours': self.auto_approve_after_hours,
            'allow_late_claims': self.allow_late_claims,
            'late_points': self.late_points,
            'early_claim_days': self.early_claim_days,
            'grace_period_days': self.grace_period_days,
            'expires_after_days': self.expires_after_days,
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
            check_date = local_today()

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
            after_date = local_today()

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

    # Work-together support
    claiming_closed_at = db.Column(db.DateTime, nullable=True)  # When claiming was closed (NULL = still open)
    claiming_closed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    chore = relationship('Chore', back_populates='instances')
    assignee = relationship('User', foreign_keys=[assigned_to])
    claimer = relationship('User', foreign_keys=[claimed_by], back_populates='claimed_instances')
    approver = relationship('User', foreign_keys=[approved_by], back_populates='approved_instances')
    rejecter = relationship('User', foreign_keys=[rejected_by], back_populates='rejected_instances')
    claiming_closer = relationship('User', foreign_keys=[claiming_closed_by])
    points_history_entries = relationship('PointsHistory', back_populates='chore_instance')
    claims = relationship('ChoreInstanceClaim', back_populates='instance', cascade='all, delete-orphan')

    # Constraints
    __table_args__ = (
        CheckConstraint("status IN ('assigned', 'claimed', 'claiming_closed', 'approved', 'rejected', 'missed')",
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
            'instance_id': self.id,  # Alias for clarity in automations
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
            'claiming_closed_at': self.claiming_closed_at.isoformat() if self.claiming_closed_at else None,
            'claiming_closed_by': self.claiming_closed_by,
            'is_work_together': self.is_work_together(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        # Include claims for work-together instances
        if self.is_work_together():
            result['claims'] = [c.to_dict() for c in self.claims]
        return result

    def is_work_together(self) -> bool:
        """Check if this is a work-together instance."""
        return (self.chore.assignment_type == 'shared' and
                self.chore.allow_work_together)

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

        # Check if claimable based on due_date with early/late windows
        if self.due_date is not None:
            today = local_today()

            # Calculate claiming window
            earliest_claim = self.due_date - timedelta(days=self.chore.early_claim_days)
            latest_claim = self.due_date + timedelta(days=self.chore.grace_period_days)

            # Cannot claim before early claim window
            if today < earliest_claim:
                return False

            # Cannot claim after grace period expires
            if today > latest_claim:
                return False

        # Work-together chores: check if claiming is still open and user hasn't claimed
        if self.is_work_together():
            if self.claiming_closed_at is not None:
                return False
            # Check if user already claimed
            existing_claim = ChoreInstanceClaim.query.filter_by(
                chore_instance_id=self.id,
                user_id=user_id
            ).first()
            if existing_claim:
                return False
            # Check if user is eligible (assigned to the chore)
            return self._is_user_assigned(user_id)

        # Check assignment
        # For individual chores (assigned_to is set)
        if self.assigned_to is not None:
            return self.assigned_to == user_id

        # For shared chores (non-work-together)
        if self.chore.assignment_type == 'shared':
            return self._is_user_assigned(user_id)

        # For individual chores without assigned_to, check ChoreAssignment
        assignment = ChoreAssignment.query.filter_by(
            chore_id=self.chore_id,
            user_id=user_id
        ).first()
        return assignment is not None

    def _is_user_assigned(self, user_id: int) -> bool:
        """Check if user is assigned to this chore (for shared chores)."""
        if self.chore.assignments:
            # If assignments exist, only those kids can claim
            assignment = ChoreAssignment.query.filter_by(
                chore_id=self.chore_id,
                user_id=user_id
            ).first()
            return assignment is not None
        else:
            # No specific assignments = ALL kids can claim
            user = db.session.get(User, user_id)
            return user is not None and user.role == 'kid'

    def can_close_claiming(self, user_id: int) -> bool:
        """Check if user can close claiming for this work-together instance."""
        if not self.is_work_together():
            return False
        if self.claiming_closed_at is not None:
            return False  # Already closed
        if len(self.claims) == 0:
            return False  # No claims to close
        user = db.session.get(User, user_id)
        return user is not None and user.role == 'parent'

    def close_claiming(self, closed_by_id: int) -> None:
        """Close claiming for this work-together instance."""
        self.claiming_closed_at = datetime.utcnow()
        self.claiming_closed_by = closed_by_id
        self.status = 'claiming_closed'

    def check_auto_close_claiming(self) -> bool:
        """Auto-close claiming if all assigned kids have claimed. Returns True if closed."""
        if not self.is_work_together() or self.claiming_closed_at is not None:
            return False

        # Get all assigned user IDs
        if self.chore.assignments:
            assigned_user_ids = {a.user_id for a in self.chore.assignments}
        else:
            # No assignments = all kids. Get all kid IDs
            assigned_user_ids = {u.id for u in User.query.filter_by(role='kid').all()}

        # Get all claimed user IDs
        claimed_user_ids = {c.user_id for c in self.claims}

        # If all assigned users have claimed, auto-close
        if assigned_user_ids and assigned_user_ids == claimed_user_ids:
            self.claiming_closed_at = datetime.utcnow()
            self.claiming_closed_by = None  # System auto-closed
            self.status = 'claiming_closed'
            return True
        return False

    def check_all_claims_resolved(self) -> bool:
        """Check if all claims are resolved and update instance status.

        Sets status to 'approved' if at least one claim was approved,
        or 'rejected' if all claims were rejected.
        """
        if not self.is_work_together():
            return False

        unresolved = [c for c in self.claims if c.status == 'claimed']
        if len(unresolved) == 0 and len(self.claims) > 0:
            # All claims resolved - check if any were approved
            approved_claims = [c for c in self.claims if c.status == 'approved']
            if len(approved_claims) > 0:
                self.status = 'approved'
            else:
                # All claims were rejected
                self.status = 'rejected'
            return True
        return False

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
        user = db.session.get(User, user_id)
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
        claimer = db.session.get(User, self.claimed_by)
        if claimer:
            claimer.adjust_points(
                delta=points_to_award,
                reason=f"Completed chore: {self.chore.name}",
                created_by_id=approver_id,
                chore_instance_id=self.id
            )


class ChoreInstanceClaim(db.Model):
    """Individual claim for work-together chores."""

    __tablename__ = 'chore_instance_claims'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    chore_instance_id = db.Column(db.Integer, db.ForeignKey('chore_instances.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Claim tracking
    claimed_at = db.Column(db.DateTime, nullable=False)
    claimed_late = db.Column(db.Boolean, default=False, nullable=False)

    # Approval tracking (individual per claim)
    status = db.Column(db.String(20), default='claimed', nullable=False)  # 'claimed', 'approved', 'rejected'
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    approved_at = db.Column(db.DateTime)
    rejected_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    rejected_at = db.Column(db.DateTime)
    rejection_reason = db.Column(db.Text)

    # Points awarded to this specific claimer
    points_awarded = db.Column(db.Integer)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    instance = relationship('ChoreInstance', back_populates='claims')
    user = relationship('User', foreign_keys=[user_id])
    approver = relationship('User', foreign_keys=[approved_by])
    rejecter = relationship('User', foreign_keys=[rejected_by])

    # Constraints
    __table_args__ = (
        UniqueConstraint('chore_instance_id', 'user_id', name='unique_instance_claim'),
        CheckConstraint("status IN ('claimed', 'approved', 'rejected')", name='check_claim_status'),
        Index('idx_instance_claims_instance', 'chore_instance_id'),
        Index('idx_instance_claims_user', 'user_id'),
        Index('idx_instance_claims_status', 'status'),
    )

    def __repr__(self):
        return f'<ChoreInstanceClaim instance_id={self.chore_instance_id} user_id={self.user_id} status={self.status}>'

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON responses."""
        return {
            'id': self.id,
            'chore_instance_id': self.chore_instance_id,
            'user_id': self.user_id,
            'user_name': self.user.username if self.user else None,
            'claimed_at': self.claimed_at.isoformat() if self.claimed_at else None,
            'claimed_late': self.claimed_late,
            'status': self.status,
            'approved_by': self.approved_by,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'rejected_by': self.rejected_by,
            'rejected_at': self.rejected_at.isoformat() if self.rejected_at else None,
            'rejection_reason': self.rejection_reason,
            'points_awarded': self.points_awarded,
        }

    def can_approve(self, user_id: int) -> bool:
        """Check if user can approve this claim."""
        if self.status != 'claimed':
            return False
        # Instance must have claiming closed
        if self.instance.claiming_closed_at is None:
            return False
        user = db.session.get(User, user_id)
        return user is not None and user.role == 'parent'

    def award_points(self, approver_id: int, points: Optional[int] = None) -> None:
        """Award points to the claimer."""
        if self.status != 'claimed':
            raise ValueError("Cannot award points for non-claimed entry")

        # Determine points to award
        chore = self.instance.chore
        if points is not None:
            points_to_award = points
        elif self.claimed_late and chore.late_points is not None:
            points_to_award = chore.late_points
        else:
            points_to_award = chore.points

        self.points_awarded = points_to_award
        self.status = 'approved'
        self.approved_by = approver_id
        self.approved_at = datetime.utcnow()

        # Award points to user
        user = db.session.get(User, self.user_id)
        if user:
            user.adjust_points(
                delta=points_to_award,
                reason=f"Completed chore (teamwork): {chore.name}",
                created_by_id=approver_id,
                chore_instance_id=self.chore_instance_id
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

        user = db.session.get(User, user_id)
        if not user:
            return False, "User not found"

        if user.role not in ('kid', 'claim_only'):
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
            'claim_id': self.id,  # Alias for clarity in automations
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


class Settings(db.Model):
    """System settings and configuration."""

    __tablename__ = 'settings'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    key = db.Column(db.String(255), unique=True, nullable=False, index=True)
    value = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<Settings {self.key}>'

    @staticmethod
    def get(key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a setting value by key."""
        setting = Settings.query.filter_by(key=key).first()
        return setting.value if setting else default

    @staticmethod
    def set(key: str, value: str) -> 'Settings':
        """Set a setting value (creates or updates)."""
        setting = Settings.query.filter_by(key=key).first()
        if setting:
            setting.value = value
            setting.updated_at = datetime.utcnow()
        else:
            setting = Settings(key=key, value=value)
            db.session.add(setting)
        db.session.commit()
        return setting
