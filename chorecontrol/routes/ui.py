"""UI routes for ChoreControl web interface."""

from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from sqlalchemy import func, and_, or_
from datetime import datetime, date, timedelta
from functools import wraps
from auth import ha_auth_required
from models import db, User, Chore, ChoreInstance, Reward, RewardClaim, PointsHistory, ChoreAssignment

ui_bp = Blueprint('ui', __name__)


def get_current_user():
    """Get the current authenticated user from Flask g."""
    if not hasattr(g, 'ha_user') or not g.ha_user:
        return None
    user = User.query.filter_by(ha_user_id=g.ha_user).first()
    return user


def redirect_claim_only_to_today(f):
    """Decorator to redirect claim_only users to /today page.

    claim_only users should only access the Today and My Rewards pages. If they try
    to access any other route, redirect them to /today automatically.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if user and user.role == 'claim_only':
            # Already on today page, my rewards page, or logout - allow
            if request.endpoint in ('ui.today_page', 'ui.my_rewards', 'auth.logout'):
                return f(*args, **kwargs)
            # Trying to access other pages - redirect to today
            return redirect(url_for('ui.today_page'))
        # Not claim_only user - proceed normally
        return f(*args, **kwargs)
    return decorated_function


def get_pending_count():
    """Get total count of pending approvals (chores + rewards)."""
    pending_instances = ChoreInstance.query.filter_by(status='claimed').count()
    pending_claims = RewardClaim.query.filter_by(status='pending').count()
    return pending_instances + pending_claims


@ui_bp.context_processor
def inject_globals():
    """Inject global variables into all templates."""
    return {
        'current_user': get_current_user(),
        'pending_count': get_pending_count()
    }


@ui_bp.route('/')
@ha_auth_required
@redirect_claim_only_to_today
def dashboard():
    """Main dashboard view."""
    current_user = get_current_user()

    # Get stats
    pending_approvals = ChoreInstance.query.filter_by(status='claimed').count()
    pending_rewards = RewardClaim.query.filter_by(status='pending').count()

    today_start = datetime.combine(date.today(), datetime.min.time())
    today_completed = ChoreInstance.query.filter(
        ChoreInstance.status == 'approved',
        ChoreInstance.approved_at >= today_start
    ).count()

    active_chores = Chore.query.filter_by(is_active=True).count()

    stats = {
        'pending_approvals': pending_approvals,
        'pending_rewards': pending_rewards,
        'today_completed': today_completed,
        'active_chores': active_chores
    }

    # Get pending instances for approval
    pending_instances = ChoreInstance.query.filter_by(status='claimed')\
        .order_by(ChoreInstance.claimed_at.desc())\
        .limit(5)\
        .all()

    # Get kids with points
    kids = User.query.filter_by(role='kid').order_by(User.username).all()

    # Get recent activity (approved, rejected, or missed in last 7 days)
    week_ago = datetime.utcnow() - timedelta(days=7)
    recent_activity = ChoreInstance.query.filter(
        and_(
            ChoreInstance.status.in_(['approved', 'rejected', 'missed']),
            or_(
                ChoreInstance.approved_at >= week_ago,
                ChoreInstance.rejected_at >= week_ago,
                ChoreInstance.updated_at >= week_ago
            )
        )
    ).order_by(ChoreInstance.updated_at.desc()).limit(10).all()

    return render_template('dashboard.html',
                         stats=stats,
                         pending_instances=pending_instances,
                         kids=kids,
                         recent_activity=recent_activity)


@ui_bp.route('/chores')
@ha_auth_required
@redirect_claim_only_to_today
def chores_list():
    """List all chores with filters."""
    # Get filters from query params
    active_filter = request.args.get('active')
    assigned_to = request.args.get('assigned_to')
    page = request.args.get('page', 1, type=int)
    per_page = 20

    # Build query
    query = Chore.query

    if active_filter == 'true':
        query = query.filter_by(is_active=True)
    elif active_filter == 'false':
        query = query.filter_by(is_active=False)

    if assigned_to:
        query = query.join(ChoreAssignment).filter(ChoreAssignment.user_id == int(assigned_to))

    # Paginate
    pagination_obj = query.order_by(Chore.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    chores = pagination_obj.items

    # Add assigned users to each chore
    for chore in chores:
        chore.assigned_users = [assignment.user_id for assignment in chore.assignments]

    # Pagination info
    pagination = {
        'page': page,
        'total': pagination_obj.total,
        'start': (page - 1) * per_page + 1,
        'end': min(page * per_page, pagination_obj.total),
        'has_prev': pagination_obj.has_prev,
        'has_next': pagination_obj.has_next,
        'prev_page': page - 1,
        'next_page': page + 1
    } if pagination_obj.total > 0 else None

    # Get kids for filter dropdown
    kids = User.query.filter_by(role='kid').order_by(User.username).all()

    return render_template('chores/list.html',
                         chores=chores,
                         pagination=pagination,
                         kids=kids)


@ui_bp.route('/chores/<int:id>')
@ha_auth_required
@redirect_claim_only_to_today
def chore_detail(id):
    """View single chore with instances."""
    chore = Chore.query.get_or_404(id)

    # Get instance stats
    total_instances = ChoreInstance.query.filter_by(chore_id=id).count()
    completed_instances = ChoreInstance.query.filter_by(chore_id=id, status='approved').count()

    instance_stats = {
        'total': total_instances,
        'completed': completed_instances
    }

    # Get instances with pagination
    page = request.args.get('page', 1, type=int)
    per_page = 20

    pagination_obj = ChoreInstance.query.filter_by(chore_id=id)\
        .order_by(ChoreInstance.due_date.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)

    instances = pagination_obj.items

    pagination = {
        'page': page,
        'total': pagination_obj.total,
        'start': (page - 1) * per_page + 1,
        'end': min(page * per_page, pagination_obj.total),
        'has_prev': pagination_obj.has_prev,
        'has_next': pagination_obj.has_next,
        'prev_page': page - 1,
        'next_page': page + 1
    } if pagination_obj.total > 0 else None

    return render_template('chores/detail.html',
                         chore=chore,
                         instance_stats=instance_stats,
                         instances=instances,
                         pagination=pagination)


@ui_bp.route('/chores/new')
@ui_bp.route('/chores/<int:id>/edit')
@ha_auth_required
def chore_form(id=None):
    """Create or edit chore form."""
    chore = None
    if id:
        chore = Chore.query.get_or_404(id)
        # Add assigned users list
        chore.assigned_users = [assignment.user_id for assignment in chore.assignments]

    # Get kids for assignment
    kids = User.query.filter_by(role='kid').order_by(User.username).all()

    return render_template('chores/form.html', chore=chore, kids=kids)


@ui_bp.route('/calendar')
@ha_auth_required
@redirect_claim_only_to_today
def calendar():
    """Calendar view showing chore instances."""
    # Get all instances with due dates for calendar
    instances_with_dates = ChoreInstance.query.filter(
        ChoreInstance.due_date.isnot(None)
    ).all()

    # Format instances for FullCalendar
    calendar_events = []
    for instance in instances_with_dates:
        # Get assigned user name
        assigned_user = instance.assignee.username if instance.assignee else 'Unassigned'

        # Get assignment type from chore
        assignment_type = instance.chore.assignment_type if instance.chore else 'individual'

        # Map status to colors
        status_colors = {
            'assigned': '#1e88e5',   # blue
            'claimed': '#fb8c00',    # warning/orange
            'approved': '#4caf50',   # green
            'rejected': '#e53935',   # red
            'missed': '#757575'      # gray
        }

        calendar_events.append({
            'id': instance.id,
            'title': f"{instance.chore.name} - {assigned_user}",
            'start': instance.due_date.isoformat(),
            'backgroundColor': status_colors.get(instance.status, '#1e88e5'),
            'borderColor': status_colors.get(instance.status, '#1e88e5'),
            'extendedProps': {
                'choreName': instance.chore.name,
                'assignedTo': assigned_user,
                'status': instance.status,
                'points': instance.chore.points,
                'assignmentType': assignment_type
            }
        })

    # Get instances without due dates for data table
    instances_without_dates = ChoreInstance.query.filter(
        ChoreInstance.due_date.is_(None)
    ).order_by(ChoreInstance.created_at.desc()).all()

    # Add eligible kids to instances without dates for shared chores
    for instance in instances_without_dates:
        if instance.chore.assignment_type == 'shared':
            # For shared chores, all assigned kids are eligible
            instance.eligible_kids = [assignment.user for assignment in instance.chore.assignments]
        else:
            # For individual chores, the assignee is the eligible kid
            if instance.assignee:
                instance.eligible_kids = [instance.assignee]
            else:
                instance.eligible_kids = []

    return render_template('calendar.html',
                         calendar_events=calendar_events,
                         instances_without_dates=instances_without_dates)


@ui_bp.route('/rewards')
@ha_auth_required
@redirect_claim_only_to_today
def rewards_list():
    """List all rewards with filters."""
    # Get filters
    active_filter = request.args.get('active')
    page = request.args.get('page', 1, type=int)
    per_page = 20

    # Build query
    query = Reward.query

    if active_filter == 'true':
        query = query.filter_by(is_active=True)
    elif active_filter == 'false':
        query = query.filter_by(is_active=False)

    # Paginate
    pagination_obj = query.order_by(Reward.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    rewards = pagination_obj.items

    # Add claim counts
    for reward in rewards:
        reward.total_claims = RewardClaim.query.filter_by(reward_id=reward.id).count()
        reward.pending_claims = RewardClaim.query.filter_by(reward_id=reward.id, status='pending').count()

    pagination = {
        'page': page,
        'total': pagination_obj.total,
        'start': (page - 1) * per_page + 1,
        'end': min(page * per_page, pagination_obj.total),
        'has_prev': pagination_obj.has_prev,
        'has_next': pagination_obj.has_next,
        'prev_page': page - 1,
        'next_page': page + 1
    } if pagination_obj.total > 0 else None

    # Get pending claims
    pending_claims = RewardClaim.query.filter_by(status='pending')\
        .order_by(RewardClaim.claimed_at.desc())\
        .limit(5)\
        .all()

    return render_template('rewards/list.html',
                         rewards=rewards,
                         pagination=pagination,
                         pending_claims=pending_claims)


@ui_bp.route('/rewards/new')
@ui_bp.route('/rewards/<int:id>/edit')
@ha_auth_required
def reward_form(id=None):
    """Create or edit reward form."""
    reward = None
    if id:
        reward = Reward.query.get_or_404(id)

    return render_template('rewards/form.html', reward=reward)


@ui_bp.route('/approvals')
@ha_auth_required
@redirect_claim_only_to_today
def approval_queue():
    """Show all pending approvals (chores and rewards)."""
    # Get pending chore instances
    pending_instances = ChoreInstance.query.filter_by(status='claimed')\
        .order_by(ChoreInstance.claimed_at.desc())\
        .all()

    # Get pending reward claims
    pending_claims = RewardClaim.query.filter_by(status='pending')\
        .order_by(RewardClaim.claimed_at.desc())\
        .all()

    return render_template('approvals/queue.html',
                         pending_instances=pending_instances,
                         pending_claims=pending_claims)


@ui_bp.route('/available')
@ha_auth_required
@redirect_claim_only_to_today
def available_chores():
    """List all available chores that can be claimed."""
    # Get all instances with status='assigned' (claimable)
    instances = ChoreInstance.query.filter_by(status='assigned')\
        .order_by(ChoreInstance.due_date.asc().nullslast(), ChoreInstance.created_at.desc())\
        .all()

    # Separate into categories for better display
    instances_with_dates = []
    instances_without_dates = []

    for instance in instances:
        # Get eligible kids for this instance
        if instance.chore.assignment_type == 'shared':
            # For shared chores, all assigned kids can claim
            eligible_kids = [assignment.user for assignment in instance.chore.assignments]
        else:
            # For individual chores, only the assigned kid can claim
            if instance.assignee:
                eligible_kids = [instance.assignee]
            elif instance.assigned_to:
                # Fallback: load assignee if assigned_to is set but relationship not loaded
                assignee = User.query.get(instance.assigned_to)
                eligible_kids = [assignee] if assignee else []
            else:
                # No specific assignment on instance - shouldn't happen for individual chores
                # but fallback to chore assignments for robustness
                eligible_kids = [assignment.user for assignment in instance.chore.assignments]

        instance.eligible_kids = eligible_kids

        if instance.due_date:
            instances_with_dates.append(instance)
        else:
            instances_without_dates.append(instance)

    # Get all kids for the claim dropdown
    kids = User.query.filter_by(role='kid').order_by(User.username).all()

    return render_template('available.html',
                         instances_with_dates=instances_with_dates,
                         instances_without_dates=instances_without_dates,
                         kids=kids)


@ui_bp.route('/users')
@ha_auth_required
@redirect_claim_only_to_today
def users_list():
    """List all users."""
    # Get role filter
    role_filter = request.args.get('role')

    query = User.query

    if role_filter:
        query = query.filter_by(role=role_filter)

    users = query.order_by(User.username).all()

    return render_template('users/list.html', users=users)


@ui_bp.route('/users/<int:id>')
@ha_auth_required
@redirect_claim_only_to_today
def user_detail(id):
    """View single user with details."""
    user = User.query.get_or_404(id)

    stats = {}
    points_history = []
    assigned_chores = []
    pagination = None

    if user.role == 'kid':
        # Get stats
        stats['total_completed'] = ChoreInstance.query.filter_by(
            claimed_by=id,
            status='approved'
        ).count()

        stats['total_points_earned'] = db.session.query(func.sum(PointsHistory.points_delta))\
            .filter(
                PointsHistory.user_id == id,
                PointsHistory.points_delta > 0
            ).scalar() or 0

        stats['total_rewards_claimed'] = RewardClaim.query.filter_by(
            user_id=id,
            status='approved'
        ).count()

        # Get points history with pagination
        page = request.args.get('page', 1, type=int)
        per_page = 20

        pagination_obj = PointsHistory.query.filter_by(user_id=id)\
            .order_by(PointsHistory.created_at.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)

        points_history = pagination_obj.items

        pagination = {
            'page': page,
            'total': pagination_obj.total,
            'start': (page - 1) * per_page + 1,
            'end': min(page * per_page, pagination_obj.total),
            'has_prev': pagination_obj.has_prev,
            'has_next': pagination_obj.has_next,
            'prev_page': page - 1,
            'next_page': page + 1
        } if pagination_obj.total > 0 else None

        # Get assigned chores
        assigned_chores = Chore.query.join(ChoreAssignment)\
            .filter(ChoreAssignment.user_id == id)\
            .order_by(Chore.name)\
            .all()

    return render_template('users/detail.html',
                         user=user,
                         stats=stats,
                         points_history=points_history,
                         assigned_chores=assigned_chores,
                         pagination=pagination)


@ui_bp.route('/users/create', methods=['POST'])
@ha_auth_required
def create_user():
    """Create a new user."""
    current_user = get_current_user()
    if not current_user or current_user.role != 'parent':
        flash('Only parents can create users.', 'error')
        return redirect(url_for('ui.users_list'))

    username = request.form.get('username', '').strip()
    role = request.form.get('role', 'kid')
    password = request.form.get('password', '')

    if not username:
        flash('Username is required.', 'error')
        return redirect(url_for('ui.users_list'))

    if role not in ('parent', 'kid'):
        flash('Invalid role.', 'error')
        return redirect(url_for('ui.users_list'))

    # Check if username already exists
    existing = User.query.filter_by(username=username).first()
    if existing:
        flash(f'Username "{username}" already exists.', 'error')
        return redirect(url_for('ui.users_list'))

    # Generate a unique ha_user_id for local users
    ha_user_id = f'local-{username.lower().replace(" ", "-")}'

    # Ensure ha_user_id is unique
    counter = 1
    original_ha_user_id = ha_user_id
    while User.query.filter_by(ha_user_id=ha_user_id).first():
        ha_user_id = f'{original_ha_user_id}-{counter}'
        counter += 1

    # Create user
    new_user = User(
        ha_user_id=ha_user_id,
        username=username,
        role=role,
        points=0
    )

    if password:
        new_user.set_password(password)

    db.session.add(new_user)
    db.session.commit()

    flash(f'User "{username}" created successfully.', 'success')
    return redirect(url_for('ui.users_list'))


@ui_bp.route('/users/update', methods=['POST'])
@ha_auth_required
def update_user():
    """Update an existing user."""
    current_user = get_current_user()
    if not current_user or current_user.role != 'parent':
        flash('Only parents can update users.', 'error')
        return redirect(url_for('ui.users_list'))

    user_id = request.form.get('user_id', type=int)
    username = request.form.get('username', '').strip()
    role = request.form.get('role')
    password = request.form.get('password', '')

    if not user_id:
        flash('User ID is required.', 'error')
        return redirect(url_for('ui.users_list'))

    user = User.query.get(user_id)
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('ui.users_list'))

    if username:
        # Check if username is taken by another user
        existing = User.query.filter(User.username == username, User.id != user_id).first()
        if existing:
            flash(f'Username "{username}" is already taken.', 'error')
            return redirect(url_for('ui.users_list'))
        user.username = username

    if role and role in ('parent', 'kid'):
        # If changing from parent to kid, initialize points
        if user.role == 'parent' and role == 'kid':
            user.points = 0
        user.role = role

    if password:
        user.set_password(password)

    db.session.commit()

    flash(f'User "{user.username}" updated successfully.', 'success')
    return redirect(url_for('ui.users_list'))


@ui_bp.route('/settings')
@ha_auth_required
@redirect_claim_only_to_today
def settings():
    """Settings page with integration configuration."""
    from auth import get_or_create_api_token
    from models import Settings as SettingsModel

    current_user = get_current_user()
    if not current_user or current_user.role != 'parent':
        flash('Only parents can access settings.', 'error')
        return redirect(url_for('ui.dashboard'))

    # Get or create API token
    api_token = get_or_create_api_token()

    return render_template('settings.html', api_token=api_token)


@ui_bp.route('/today')
@ha_auth_required
def today_page():
    """Today's chores dashboard - shows what each kid can do to earn points today."""
    today = date.today()

    # Get all claimable instances (status='assigned') that are either:
    # 1. Due today, or
    # 2. Have no due date (anytime chores)
    instances = ChoreInstance.query.filter(
        ChoreInstance.status == 'assigned',
        or_(
            ChoreInstance.due_date == today,
            ChoreInstance.due_date.is_(None)
        )
    ).order_by(ChoreInstance.due_date.asc().nullslast()).all()

    # Get all kids
    kids = User.query.filter_by(role='kid').order_by(User.username).all()

    # Group instances by kid
    # For each kid, find instances they can claim
    kids_data = []
    for kid in kids:
        kid_instances = []
        for instance in instances:
            # Check if this kid can claim this instance
            can_claim = False
            if instance.chore.assignment_type == 'shared':
                # For shared chores, check if kid is in the assignments
                assigned_user_ids = [a.user_id for a in instance.chore.assignments]
                can_claim = kid.id in assigned_user_ids
            else:
                # For individual chores, check if assigned to this kid
                if instance.assigned_to:
                    can_claim = instance.assigned_to == kid.id
                else:
                    # Fallback to chore assignments
                    assigned_user_ids = [a.user_id for a in instance.chore.assignments]
                    can_claim = kid.id in assigned_user_ids

            if can_claim:
                kid_instances.append(instance)

        if kid_instances:
            # Calculate total potential points
            total_points = sum(inst.chore.points for inst in kid_instances)
            kids_data.append({
                'kid': kid,
                'instances': kid_instances,
                'total_points': total_points
            })

    return render_template('today.html', kids_data=kids_data, today=today)


@ui_bp.route('/my-rewards')
@ha_auth_required
def my_rewards():
    """Rewards page - claim rewards and view pending claims for all kids."""
    from sqlalchemy import func
    from collections import defaultdict

    current_user = get_current_user()

    # Get all kids
    kids = User.query.filter_by(role='kid').order_by(User.username).all()
    kid_ids = [kid.id for kid in kids]

    # Get all active rewards
    active_rewards = Reward.query.filter_by(is_active=True).order_by(Reward.points_cost).all()
    reward_ids = [r.id for r in active_rewards]

    # Pre-fetch all data in bulk queries (instead of N+1 queries)

    # 1. Get approved claim counts per (user_id, reward_id)
    approved_counts_query = db.session.query(
        RewardClaim.user_id,
        RewardClaim.reward_id,
        func.count(RewardClaim.id).label('count')
    ).filter(
        RewardClaim.user_id.in_(kid_ids),
        RewardClaim.reward_id.in_(reward_ids),
        RewardClaim.status == 'approved'
    ).group_by(RewardClaim.user_id, RewardClaim.reward_id).all()

    # Build lookup: {(user_id, reward_id): count}
    approved_counts = {(r.user_id, r.reward_id): r.count for r in approved_counts_query}

    # 2. Get total approved claim counts per reward_id
    total_counts_query = db.session.query(
        RewardClaim.reward_id,
        func.count(RewardClaim.id).label('count')
    ).filter(
        RewardClaim.reward_id.in_(reward_ids),
        RewardClaim.status == 'approved'
    ).group_by(RewardClaim.reward_id).all()

    # Build lookup: {reward_id: count}
    total_counts = {r.reward_id: r.count for r in total_counts_query}

    # 3. Get most recent claim per (user_id, reward_id) for cooldown checking
    # Subquery to get max claimed_at per (user_id, reward_id)
    recent_claims_subq = db.session.query(
        RewardClaim.user_id,
        RewardClaim.reward_id,
        func.max(RewardClaim.claimed_at).label('max_claimed_at')
    ).filter(
        RewardClaim.user_id.in_(kid_ids),
        RewardClaim.reward_id.in_(reward_ids),
        RewardClaim.status.in_(['approved', 'pending'])
    ).group_by(RewardClaim.user_id, RewardClaim.reward_id).subquery()

    recent_claims = db.session.query(
        recent_claims_subq.c.user_id,
        recent_claims_subq.c.reward_id,
        recent_claims_subq.c.max_claimed_at
    ).all()

    # Build lookup: {(user_id, reward_id): claimed_at}
    last_claim_dates = {(r.user_id, r.reward_id): r.max_claimed_at for r in recent_claims}

    # 4. Get all pending claims for all kids (with reward relationship)
    all_pending_claims = RewardClaim.query.filter(
        RewardClaim.user_id.in_(kid_ids),
        RewardClaim.status == 'pending'
    ).order_by(RewardClaim.claimed_at.desc()).all()

    # Group by user_id
    pending_by_kid = defaultdict(list)
    for claim in all_pending_claims:
        pending_by_kid[claim.user_id].append(claim)

    # Now build kids_data using the pre-fetched lookups (no additional queries)
    kids_data = []
    now = datetime.utcnow()

    for kid in kids:
        kid_rewards = []

        for reward in active_rewards:
            reward_data = {
                'id': reward.id,
                'name': reward.name,
                'description': reward.description,
                'points_cost': reward.points_cost,
                'cooldown_days': reward.cooldown_days,
                'max_claims_per_kid': reward.max_claims_per_kid,
                'max_claims_total': reward.max_claims_total,
                'requires_approval': reward.requires_approval,
            }

            # Check if kid has enough points
            reward_data['can_afford'] = kid.points >= reward.points_cost

            # Check cooldown using pre-fetched data
            if reward.cooldown_days:
                last_claim_date = last_claim_dates.get((kid.id, reward.id))
                if last_claim_date:
                    days_since_claim = (now - last_claim_date).days
                    reward_data['on_cooldown'] = days_since_claim < reward.cooldown_days
                    reward_data['cooldown_remaining'] = reward.cooldown_days - days_since_claim if reward_data['on_cooldown'] else 0
                else:
                    reward_data['on_cooldown'] = False
                    reward_data['cooldown_remaining'] = 0
            else:
                reward_data['on_cooldown'] = False
                reward_data['cooldown_remaining'] = 0

            # Check max claims per kid using pre-fetched data
            if reward.max_claims_per_kid:
                kid_claim_count = approved_counts.get((kid.id, reward.id), 0)
                reward_data['at_max_claims'] = kid_claim_count >= reward.max_claims_per_kid
                reward_data['claims_remaining'] = max(0, reward.max_claims_per_kid - kid_claim_count)
            else:
                reward_data['at_max_claims'] = False
                reward_data['claims_remaining'] = None

            # Check max total claims using pre-fetched data
            if reward.max_claims_total:
                total_claim_count = total_counts.get(reward.id, 0)
                reward_data['at_max_total'] = total_claim_count >= reward.max_claims_total
            else:
                reward_data['at_max_total'] = False

            # Can claim if: has points, not on cooldown, not at max, reward not exhausted
            reward_data['can_claim'] = (
                reward_data['can_afford'] and
                not reward_data['on_cooldown'] and
                not reward_data['at_max_claims'] and
                not reward_data['at_max_total']
            )

            kid_rewards.append(reward_data)

        # Get kid's pending claims from pre-fetched data
        pending_claims = pending_by_kid.get(kid.id, [])

        # Add time remaining for each pending claim
        for claim in pending_claims:
            if claim.expires_at:
                time_remaining = claim.expires_at - now
                claim.days_until_expiry = max(0, time_remaining.days)
                claim.is_expiring_soon = claim.days_until_expiry <= 2
            else:
                claim.days_until_expiry = None
                claim.is_expiring_soon = False

        kids_data.append({
            'kid': kid,
            'rewards': kid_rewards,
            'pending_claims': pending_claims
        })

    # Get claim history (approved/rejected in last 30 days) with pagination
    history_page = request.args.get('history_page', 1, type=int)
    per_page = 10
    cutoff_date = datetime.utcnow() - timedelta(days=30)

    history_query = RewardClaim.query.filter(
        RewardClaim.status.in_(['approved', 'rejected']),
        RewardClaim.claimed_at >= cutoff_date
    ).order_by(RewardClaim.claimed_at.desc())

    history_pagination = history_query.paginate(
        page=history_page, per_page=per_page, error_out=False
    )

    claim_history = history_pagination.items
    history_pagination_data = {
        'page': history_page,
        'total': history_pagination.total,
        'pages': history_pagination.pages,
        'has_prev': history_pagination.has_prev,
        'has_next': history_pagination.has_next,
        'prev_page': history_page - 1,
        'next_page': history_page + 1,
        'start': (history_page - 1) * per_page + 1 if history_pagination.total > 0 else 0,
        'end': min(history_page * per_page, history_pagination.total)
    } if history_pagination.total > 0 else None

    return render_template('rewards/my_rewards.html',
                         kids_data=kids_data,
                         current_user=current_user,
                         claim_history=claim_history,
                         history_pagination=history_pagination_data)
