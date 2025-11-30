"""User mapping routes for assigning roles to HA users."""

from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from auth import parent_required, get_current_user
from models import db, User
from utils.ha_api import clear_ha_user_cache

user_mapping_bp = Blueprint('user_mapping', __name__, url_prefix='/users')


@user_mapping_bp.route('/mapping')
@parent_required
def mapping_page():
    """
    Display user mapping interface for assigning roles to HA users.

    Shows:
    - Unmapped users prominently at top (need attention)
    - All users below for review/changes
    """
    # Get unmapped users (need attention)
    unmapped_users = User.query.filter_by(role='unmapped').order_by(User.created_at.desc()).all()

    # Get all users grouped by role
    parents = User.query.filter_by(role='parent').order_by(User.username).all()
    kids = User.query.filter_by(role='kid').order_by(User.username).all()
    system_users = User.query.filter_by(role='system').order_by(User.username).all()

    return render_template('users/mapping.html',
                         unmapped_users=unmapped_users,
                         parents=parents,
                         kids=kids,
                         system_users=system_users)


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
