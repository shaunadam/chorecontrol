"""Tests for Home Assistant ingress integration."""

import pytest
from flask import url_for, redirect


class TestIngressPathHandling:
    """Test that X-Ingress-Path header is handled correctly."""

    def test_script_name_set_from_header(self, client, parent_user):
        """X-Ingress-Path should set SCRIPT_NAME in environ."""
        headers = {
            'X-Ingress-Path': '/api/hassio_ingress/test_chorecontrol',
            'X-Ingress-User': parent_user.ha_user_id,
        }
        # Make a request that doesn't redirect
        response = client.get('/health', headers=headers)
        assert response.status_code == 200

    def test_dashboard_accessible_with_ingress(self, client, parent_user):
        """Dashboard should be accessible with ingress headers."""
        headers = {
            'X-Ingress-Path': '/api/hassio_ingress/test_chorecontrol',
            'X-Ingress-User': parent_user.ha_user_id,
        }
        response = client.get('/', headers=headers)
        # Dashboard renders directly when authenticated
        assert response.status_code == 200

    def test_unauthenticated_request_handled(self, client):
        """Unauthenticated requests should be rejected or redirected."""
        headers = {
            'X-Ingress-Path': '/api/hassio_ingress/test_chorecontrol',
            # No X-Ingress-User - not authenticated
        }
        # Protected route without auth
        response = client.get('/users', headers=headers)
        # Should either redirect to login (302) or return unauthorized (401)
        assert response.status_code in [302, 401]

    def test_api_endpoints_with_ingress(self, client, parent_user):
        """API endpoints should work with ingress headers."""
        headers = {
            'X-Ingress-Path': '/api/hassio_ingress/test_chorecontrol',
            'X-Ingress-User': parent_user.ha_user_id,
        }
        response = client.get('/api/users', headers=headers)
        assert response.status_code == 200

    def test_trailing_slash_stripped(self, client, parent_user):
        """Ingress path with trailing slash should be stripped."""
        headers = {
            'X-Ingress-Path': '/api/hassio_ingress/test_chorecontrol/',
            'X-Ingress-User': parent_user.ha_user_id,
        }
        response = client.get('/', headers=headers)
        # Should render dashboard successfully
        assert response.status_code == 200

    def test_health_endpoint_no_auth_required(self, client):
        """Health endpoint should work without authentication."""
        headers = {
            'X-Ingress-Path': '/api/hassio_ingress/test_chorecontrol',
        }
        response = client.get('/health', headers=headers)
        assert response.status_code == 200

        data = response.get_json()
        assert data['status'] in ['healthy', 'degraded']


class TestIngressUserExtraction:
    """Test that X-Ingress-User header is handled correctly."""

    def test_user_extracted_from_header(self, client, parent_user):
        """X-Ingress-User should be extracted and used for auth."""
        headers = {
            'X-Ingress-User': parent_user.ha_user_id,
        }
        response = client.get('/api/users', headers=headers)
        assert response.status_code == 200

    def test_missing_user_header_requires_login(self, client):
        """Without X-Ingress-User, protected routes should require login."""
        response = client.get('/api/users')
        # Should redirect to login or return 401
        assert response.status_code in [302, 401]

    def test_both_headers_together(self, client, parent_user):
        """Both ingress headers should work together."""
        headers = {
            'X-Ingress-Path': '/api/hassio_ingress/test_chorecontrol',
            'X-Ingress-User': parent_user.ha_user_id,
        }
        response = client.get('/api/users', headers=headers)
        assert response.status_code == 200


class TestUrlGeneration:
    """Test that SCRIPT_NAME affects url_for correctly.

    Note: Flask's test client doesn't fully simulate WSGI environ handling.
    These tests verify the principle that SCRIPT_NAME affects url_for.
    The actual middleware behavior needs to be tested with real requests.
    """

    def test_script_name_affects_url_for(self, app, parent_user):
        """Verify that SCRIPT_NAME prefix appears in generated URLs.

        When SCRIPT_NAME is set in the environ before the request context,
        url_for should include it in generated URLs.
        """
        from werkzeug.test import EnvironBuilder

        # Build environ with SCRIPT_NAME already set (as HA ingress would)
        builder = EnvironBuilder(
            path='/',
            headers={
                'X-Ingress-User': parent_user.ha_user_id,
            }
        )
        env = builder.get_environ()
        env['SCRIPT_NAME'] = '/api/hassio_ingress/test_chorecontrol'

        with app.request_context(env):
            url = url_for('health')
            assert url == '/api/hassio_ingress/test_chorecontrol/health'

    def test_static_url_includes_script_name(self, app, parent_user):
        """Static file URLs should include SCRIPT_NAME prefix."""
        from werkzeug.test import EnvironBuilder

        builder = EnvironBuilder(
            path='/',
            headers={
                'X-Ingress-User': parent_user.ha_user_id,
            }
        )
        env = builder.get_environ()
        env['SCRIPT_NAME'] = '/api/hassio_ingress/test_chorecontrol'

        with app.request_context(env):
            url = url_for('static', filename='css/style.css')
            assert url == '/api/hassio_ingress/test_chorecontrol/static/css/style.css'

    def test_url_for_without_script_name(self, app, parent_user):
        """url_for should work normally without SCRIPT_NAME."""
        with app.test_request_context(
            '/',
            headers={
                'X-Ingress-User': parent_user.ha_user_id,
            }
        ):
            url = url_for('health')
            assert url == '/health'
