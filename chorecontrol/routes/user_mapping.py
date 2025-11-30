"""User mapping routes for assigning roles to HA users."""

from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from auth import parent_required, get_current_user
from models import db, User
from utils.ha_api import clear_ha_user_cache, get_all_ha_users
import logging

logger = logging.getLogger(__name__)

user_mapping_bp = Blueprint('user_mapping', __name__, url_prefix='/users')


@user_mapping_bp.route('/mapping')
@parent_required
def mapping_page():
    """
    Display user mapping interface for assigning roles to HA users.

    Shows:
    - All HA users from Home Assistant
    - Unmapped users prominently at top (need attention)
    - All users below for review/changes

    If HA API is unavailable, falls back to showing only ChoreControl database users.
    """
    # Fetch all HA users from the Supervisor API
    ha_users_list = get_all_ha_users()
    ha_api_available = ha_users_list is not None

    if ha_api_available:
        logger.info(f"Fetched {len(ha_users_list)} users from HA API")
    else:
        logger.warning("HA API unavailable, showing only existing ChoreControl users")
        ha_users_list = []

    # Get existing ChoreControl users by ha_user_id
    all_cc_users = User.query.all()
    cc_users_by_ha_id = {user.ha_user_id: user for user in all_cc_users}

    # Build combined list of HA users with their ChoreControl status
    ha_users_with_status = []
    for ha_user in ha_users_list:
        ha_user_id = ha_user.get('id')
        if not ha_user_id:
            continue

        # Skip system users
        if ha_user.get('system_generated', False):
            continue

        # Get corresponding ChoreControl user if exists
        cc_user = cc_users_by_ha_id.get(ha_user_id)

        ha_users_with_status.append({
            'ha_user_id': ha_user_id,
            'ha_username': ha_user.get('username', ha_user_id),
            'ha_name': ha_user.get('name', ha_user.get('username', ha_user_id)),
            'is_owner': ha_user.get('is_owner', False),
            'is_active': ha_user.get('is_active', True),
            'cc_user': cc_user,  # None if not yet created
            'cc_role': cc_user.role if cc_user else None,
            'cc_id': cc_user.id if cc_user else None
        })

    # Get unmapped users (need attention) - only from ChoreControl DB
    unmapped_users = User.query.filter_by(role='unmapped').order_by(User.created_at.desc()).all()

    # Get all users grouped by role - only from ChoreControl DB
    parents = User.query.filter_by(role='parent').order_by(User.username).all()
    kids = User.query.filter_by(role='kid').order_by(User.username).all()
    system_users = User.query.filter_by(role='system').order_by(User.username).all()

    return render_template('users/mapping.html',
                         unmapped_users=unmapped_users,
                         parents=parents,
                         kids=kids,
                         system_users=system_users,
                         ha_users=ha_users_with_status,
                         ha_api_available=ha_api_available)


@user_mapping_bp.route('/mapping/update', methods=['POST'])
@parent_required
def update_mappings():
    """
    Bulk update user role mappings.

    Accepts form data with user IDs and their new roles.
    Format: role_{user_id} = 'parent' | 'kid' | 'unmapped'
    """
    current_user = get_current_user()

    # Track changes for flash message
    updated_count = 0
    errors = []

    # Process all role updates from form
    for key, new_role in request.form.items():
        if not key.startswith('role_'):
            continue

        try:
            user_id = int(key.replace('role_', ''))
        except ValueError:
            continue

        # Validate role
        if new_role not in ('parent', 'kid', 'unmapped', 'system'):
            errors.append(f'Invalid role for user {user_id}')
            continue

        # Get user
        user = User.query.get(user_id)
        if not user:
            errors.append(f'User {user_id} not found')
            continue

        # Prevent changing local admin accounts
        if user.ha_user_id.startswith('local-'):
            errors.append(f'Cannot change role for local account: {user.username}')
            continue

        # Skip if role unchanged
        if user.role == new_role:
            continue

        # Update role
        old_role = user.role
        user.role = new_role

        # If changing to kid, initialize points
        if new_role == 'kid' and old_role != 'kid':
            user.points = 0

        updated_count += 1

    # Commit all changes
    try:
        db.session.commit()

        # Clear HA user cache to refresh display names
        clear_ha_user_cache()

        if updated_count > 0:
            flash(f'Successfully updated {updated_count} user(s).', 'success')
        else:
            flash('No changes were made.', 'info')

        if errors:
            for error in errors:
                flash(error, 'error')

    except Exception as e:
        db.session.rollback()
        flash(f'Failed to update user mappings: {str(e)}', 'error')

    return redirect(url_for('user_mapping.mapping_page'))


@user_mapping_bp.route('/mapping/refresh-cache', methods=['POST'])
@parent_required
def refresh_user_cache():
    """
    Manually refresh the HA user cache.

    Useful when HA users are added/removed and display names need updating.
    """
    try:
        clear_ha_user_cache()
        flash('User cache refreshed successfully.', 'success')
    except Exception as e:
        flash(f'Failed to refresh cache: {str(e)}', 'error')

    return redirect(url_for('user_mapping.mapping_page'))
