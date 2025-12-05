"""Debug endpoints for troubleshooting ingress authentication."""

from flask import Blueprint, request, jsonify
import os

debug_bp = Blueprint('debug', __name__, url_prefix='/debug')


@debug_bp.route('/headers')
def show_headers():
    """Show all request headers (only in debug mode)."""
    if not os.environ.get('DEBUG'):
        return jsonify({'error': 'Debug mode not enabled'}), 403

    return jsonify({
        'headers': dict(request.headers),
        'cookies': list(request.cookies.keys()),
        'environ_keys': [k for k in request.environ.keys() if not k.startswith('_')]
    })
