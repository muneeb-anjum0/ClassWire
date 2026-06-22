"""Backend tests for ClassWire."""

import json
import os
import sys
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app import app, get_user_from_request


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def mock_user():
    return {
        'id': 'test-user-id',
        'email': 'test@example.com',
        'created_at': datetime.now().isoformat(),
    }


@pytest.fixture
def mock_store():
    mock = MagicMock()
    with patch('app.store', new=mock):
        yield mock


class TestHealthEndpoint:
    def test_health_check_success(self, client):
        response = client.get('/api/health')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert 'timestamp' in data
        assert 'firestore_connected' in data


class TestAuthentication:
    def test_get_user_from_request_valid_header(self, mock_store, mock_user):
        mock_store.get_or_create_user.return_value = mock_user

        with app.test_request_context('/', headers={'X-User-Email': 'test@example.com'}):
            user, error, status = get_user_from_request()

            assert user == mock_user
            assert error is None
            assert status is None

    def test_get_user_from_request_no_email(self):
        with app.test_request_context('/'):
            user, error, status = get_user_from_request()

            assert user is None
            assert status == 401

    def test_get_user_from_request_invalid_email(self, mock_store, mock_user):
        mock_store.get_or_create_user.return_value = mock_user

        with app.test_request_context('/', headers={'X-User-Email': 'invalid-email'}):
            user, error, status = get_user_from_request()

            assert user is not None
            assert error is None
            assert status is None


class TestSemesterConfiguration:
    def test_update_semesters_success(self, client, mock_store, mock_user):
        mock_store.get_or_create_user.return_value = mock_user
        mock_store.get_user_settings.return_value = {'allowed_semesters': []}
        mock_store.save_user_settings.return_value = True

        response = client.post(
            '/api/config/semesters',
            json={'semesters': ['BS (SE) - 5C']},
            headers={'X-User-Email': 'test@example.com'},
        )

        assert response.status_code == 200
        assert response.get_json()['success'] is True

    def test_update_semesters_invalid_data(self, client, mock_store, mock_user):
        mock_store.get_or_create_user.return_value = mock_user

        response = client.post(
            '/api/config/semesters',
            json={'invalid': 'data'},
            headers={'X-User-Email': 'test@example.com'},
        )

        assert response.status_code == 400

    def test_identity_header_is_ignored_outside_tests(self, client):
        original_testing = app.testing
        app.testing = False
        try:
            response = client.get('/api/config', headers={'X-User-Email': 'spoofed@example.com'})
        finally:
            app.testing = original_testing

        assert response.status_code == 401

    def test_update_semesters_no_auth(self, client):
        response = client.post('/api/config/semesters', json={'semesters': ['BS (SE) - 5C']})
        assert response.status_code == 401


class TestDailyEmailToggle:
    def test_enable_daily_email_requires_personal_email(self, client, mock_store, mock_user):
        mock_store.get_or_create_user.return_value = mock_user
        mock_store.get_user_settings.return_value = {'personal_email': ''}

        response = client.post(
            '/api/config/daily-email-enabled',
            json={'daily_email_enabled': True},
            headers={'X-User-Email': 'test@example.com'},
        )

        assert response.status_code == 400
        assert response.get_json()['success'] is False
        mock_store.save_user_settings.assert_not_called()

    def test_enable_daily_email_saves_true(self, client, mock_store, mock_user):
        mock_store.get_or_create_user.return_value = mock_user
        settings = {'personal_email': 'personal@example.com', 'daily_email_enabled': False}
        mock_store.get_user_settings.return_value = settings
        mock_store.save_user_settings.return_value = True

        response = client.post(
            '/api/config/daily-email-enabled',
            json={'daily_email_enabled': True},
            headers={'X-User-Email': 'test@example.com'},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['daily_email_enabled'] is True
        mock_store.save_user_settings.assert_called_once()
        assert mock_store.save_user_settings.call_args.args[1]['daily_email_enabled'] is True

    def test_disable_daily_email_saves_false(self, client, mock_store, mock_user):
        mock_store.get_or_create_user.return_value = mock_user
        settings = {'personal_email': 'personal@example.com', 'daily_email_enabled': True}
        mock_store.get_user_settings.return_value = settings
        mock_store.save_user_settings.return_value = True

        response = client.post(
            '/api/config/daily-email-enabled',
            json={'daily_email_enabled': False},
            headers={'X-User-Email': 'test@example.com'},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['daily_email_enabled'] is False
        mock_store.save_user_settings.assert_called_once()
        assert mock_store.save_user_settings.call_args.args[1]['daily_email_enabled'] is False


class TestScrapeEndpoint:
    @patch('app.run_once')
    def test_scrape_success(self, mock_run_once, client, mock_store, mock_user):
        mock_store.get_or_create_user.return_value = mock_user
        mock_store.get_user_settings.return_value = {'allowed_semesters': ['BS (SE) - 5C']}
        mock_run_once.return_value = {
            'success': True,
            'data': [{'course': 'Test Course'}],
        }

        response = client.post('/api/scrape', headers={'X-User-Email': 'test@example.com'})
        assert response.status_code == 200
        assert response.get_json()['success'] is True

    @patch('app.run_once')
    def test_scrape_failure(self, mock_run_once, client, mock_store, mock_user):
        mock_store.get_or_create_user.return_value = mock_user
        mock_store.get_user_settings.return_value = {'allowed_semesters': ['BS (SE) - 5C']}
        mock_run_once.return_value = {
            'success': False,
            'error': 'Test error',
        }

        response = client.post('/api/scrape', headers={'X-User-Email': 'test@example.com'})
        assert response.status_code == 400
        assert response.get_json()['success'] is False


class TestErrorHandling:
    def test_404_error(self, client):
        response = client.get('/api/nonexistent')
        assert response.status_code == 404
        assert b'Not Found' in response.data

    def test_405_error(self, client):
        response = client.delete('/api/health')
        assert response.status_code == 405


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
