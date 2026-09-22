"""Backend tests for ClassWire."""

import json
import gzip
import os
import sys
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app import app, get_user_from_request
from core.app_support import compress_large_json_response


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
        assert data['config_loaded'] is True
        assert 'firestore_connected' not in data

    def test_large_json_responses_are_gzipped_when_supported(self):
        with app.test_request_context('/', headers={'Accept-Encoding': 'gzip, deflate'}):
            response = app.json.response({'payload': 'x' * 5000})
            original_size = len(response.get_data())
            compressed = compress_large_json_response(response)

        assert compressed.headers['Content-Encoding'] == 'gzip'
        assert len(compressed.get_data()) < original_size
        assert json.loads(gzip.decompress(compressed.get_data()))['payload'] == 'x' * 5000

    def test_request_includes_trace_and_server_timing_headers(self, client):
        response = client.get('/api/health')
        assert response.headers['X-Request-ID']
        assert response.headers['Server-Timing'].startswith('app;dur=')


class TestBootstrapEndpoint:
    def test_bootstrap_combines_user_config_and_cached_timetable(self, client, mock_store, mock_user):
        mock_store.get_or_create_user.return_value = mock_user
        mock_store.get_bootstrap_data.return_value = {
            'settings': {'allowed_semesters': ['BS(SE)-7A']},
            'timetable': {'items': [], 'for_day': 'Entire Week'},
            'last_update': '2026-09-22T10:00:00Z',
        }
        response = client.get('/api/bootstrap', headers={'X-User-Email': mock_user['email']})
        assert response.status_code == 200
        data = response.get_json()
        assert data['user']['email'] == mock_user['email']
        assert data['config']['semester_filter'] == ['BS(SE)-7A']
        assert data['timetable']['for_day'] == 'Entire Week'

    def test_metrics_require_automation_secret(self, client):
        response = client.get('/api/metrics')
        assert response.status_code == 401


class TestAccountDeletion:
    @patch('requests.post')
    def test_deletion_revokes_google_token_and_removes_all_user_data(self, revoke, client, mock_store, mock_user):
        mock_store.get_or_create_user.return_value = mock_user
        mock_store.get_user_tokens.return_value = {'refresh_token': 'refresh-token'}
        mock_store.delete_user_data.return_value = True
        response = client.delete('/api/account', headers={'X-User-Email': mock_user['email']})
        assert response.status_code == 200
        revoke.assert_called_once()
        mock_store.delete_user_data.assert_called_once_with(mock_user['id'])


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


class TestSearchEndpoint:
    @patch('app.run_once')
    def test_search_persists_compact_source_and_does_not_duplicate_items(self, mock_run_once, client, mock_store, mock_user):
        item = {
            'schedule_day': 'Monday',
            'semester_display': 'BS(SE)-7A',
            'course': 'SEC 3603 Software Project Management (3,0)',
            'course_code': 'SEC 3603',
            'course_title': 'Software Project Management',
            'faculty': 'Ada Lovelace',
            'room': '204',
            'time': '02:00 PM - 03:30 PM',
            'campus': 'Main Campus',
        }
        source = {
            'for_day': 'Entire Week',
            'for_date': '2026-09-19',
            'query': 'gmail query',
            'message_id': 'message-1',
            'message_ids': ['message-1'],
            'items': [item],
            'semesters': [],
            'summary': {},
        }
        mock_store.get_or_create_user.return_value = mock_user
        mock_store.get_user_settings.return_value = {}
        mock_store.get_search_source_cache.return_value = None
        mock_store.save_search_source_cache.return_value = True
        mock_store.save_timetable_cache.return_value = True
        mock_run_once.return_value = {'success': True, 'data': source}

        response = client.post(
            '/api/search',
            json={'query': 'When does Ada Lovelace have classes?', 'force_refresh': True},
            headers={'X-User-Email': 'test@example.com'},
        )

        assert response.status_code == 200
        data = response.get_json()['data']
        assert data['items'] == [item]
        assert 'items' not in data['search']
        mock_store.save_search_source_cache.assert_called_once_with(mock_user['id'], source)
        mock_store.save_timetable_cache.assert_called_once()

    @patch('app.run_once')
    def test_search_falls_back_to_stale_source_when_gmail_refresh_fails(self, mock_run_once, client, mock_store):
        user = {'id': 'stale-cache-user', 'email': 'stale@example.com'}
        item = {
            'schedule_day': 'Monday',
            'semester_display': 'BS(SE)-7A',
            'course': 'SEC 3603 Software Project Management (3,0)',
            'course_code': 'SEC 3603',
            'course_title': 'Software Project Management',
            'faculty': 'Ada Lovelace',
            'time': '02:00 PM - 03:30 PM',
        }
        source = {'items': [item], 'for_day': 'Entire Week', 'summary': {}}
        mock_store.get_or_create_user.return_value = user
        mock_store.get_user_settings.return_value = {}
        mock_store.get_search_source_cache.side_effect = [None, source]
        mock_store.save_timetable_cache.return_value = True
        mock_run_once.return_value = {'success': False, 'error': 'Stored OAuth credentials could not be decrypted'}

        response = client.post(
            '/api/search',
            json={'query': 'BSSE7A classes on Monday'},
            headers={'X-User-Email': user['email']},
        )

        assert response.status_code == 200
        payload = response.get_json()
        assert payload['cached'] is True
        assert payload['data']['items'] == [item]
        assert payload['data']['search']['source_stale'] is True
        assert 'last saved timetable' in payload['message']

    def test_search_rejects_unbounded_query_input(self, client, mock_store, mock_user):
        mock_store.get_or_create_user.return_value = mock_user

        response = client.post(
            '/api/search',
            json={'query': 'x' * 501},
            headers={'X-User-Email': 'test@example.com'},
        )

        assert response.status_code == 400
        assert '500 characters' in response.get_json()['error']


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
