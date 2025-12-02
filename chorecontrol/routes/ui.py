"""UI routes for ChoreControl web interface."""

from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from sqlalchemy import func, and_, or_
from datetime import datetime, date, timedelta
from auth import ha_auth_required
from models import db, User, Chore, ChoreInstance, Reward, RewardClaim, PointsHistory, ChoreAssignment

ui_bp = Blueprint('ui', __name__)


def get_current_user():
    """Get the current authenticated user from Flask g."""
    if not hasattr(g, 'ha_user') or not g.ha_user:
        return None
    user = User.query.filter_by(ha_user_id=g.ha_user).first()
    return user


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
