#!/usr/bin/env python
"""
Management script for ChoreControl.

This script provides command-line utilities for database migrations
and other administrative tasks.
"""

import os
import sys

# Add addon directory to path
sys.path.insert(0, os.path.dirname(__file__))

from flask_migrate import Migrate
from addon.app import create_app
from addon.models import db

# Create Flask app
app = create_app()

# Initialize Migrate
migrate = Migrate(app, db)

# Make app context available for Flask CLI
if __name__ == '__main__':
    # This allows running: python manage.py
    app.run(debug=True)
