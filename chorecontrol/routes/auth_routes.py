"""Authentication routes for ChoreControl web interface."""

from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from models import db, User
from auth import login_user, logout_user, get_current_user

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login."""
    # If already authenticated, redirect to dashboard
    if hasattr(g, 'ha_user') and g.ha_user:
        return redirect(url_for('ui.dashboard'))

    error = None

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            error = 'Username and password are required'
        else:
            # Find user by username
            user = User.query.filter_by(username=username).first()

            if user is None:
                error = 'Invalid username or password'
            elif not user.has_password():
                error = 'This user cannot log in with a password'
            elif not user.check_password(password):
                error = 'Invalid username or password'
            else:
                # Successful login
                login_user(user)
                flash(f'Welcome back, {user.username}!', 'success')

                # Redirect to requested page or dashboard
                next_page = request.args.get('next')
                if next_page:
                    return redirect(next_page)
                return redirect(url_for('ui.dashboard'))

    return render_template('auth/login.html', error=error)


@auth_bp.route('/logout')
def logout():
    """Handle user logout."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
