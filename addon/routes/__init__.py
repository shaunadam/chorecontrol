"""Routes package for ChoreControl API endpoints."""

from flask import Blueprint

# Import blueprints
from .users import users_bp
from .chores import chores_bp
from .instances import instances_bp

# Export all blueprints
__all__ = ['users_bp', 'chores_bp', 'instances_bp']
