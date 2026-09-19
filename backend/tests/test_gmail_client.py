import base64

from scraper.gmail_client import (
    get_message_html_from_message,
    get_message_subject,
    get_messages_batch,
    list_latest_messages_batch,
)


class FakeRequest:
    def __init__(self, message_id):
        self.message_id = message_id


class FakeMessages:
    def get(self, *, userId, id, format):
        assert userId == "me"
        assert format == "full"
        return FakeRequest(id)


class FakeUsers:
    def messages(self):
        return FakeMessages()


class FakeBatch:
    def __init__(self, callback):
        self.callback = callback
        self.requests = []

    def add(self, request, request_id):
        self.requests.append((request_id, request))

    def execute(self):
        for request_id, request in self.requests:
            self.callback(request_id, {"id": request.message_id}, None)


class FakeService:
    def users(self):
        return FakeUsers()

    def new_batch_http_request(self, callback):
        return FakeBatch(callback)


def test_batch_fetch_deduplicates_ids_and_maps_responses():
    messages = get_messages_batch(FakeService(), "me", ["one", "one", "two", ""])

    assert messages == {"one": {"id": "one"}, "two": {"id": "two"}}


def test_message_helpers_extract_nested_html_and_subject():
    html = "<table><tr><td>Class</td></tr></table>"
    encoded = base64.urlsafe_b64encode(html.encode()).decode()
    message = {
        "payload": {
            "mimeType": "multipart/alternative",
            "headers": [{"name": "Subject", "value": "Class Schedule – Tuesday"}],
            "parts": [{"mimeType": "text/html", "body": {"data": encoded}}],
        }
    }

    assert get_message_subject(message) == "Class Schedule – Tuesday"
    assert get_message_html_from_message(message) == html


def test_message_helper_handles_unpadded_base64_and_unknown_multipart_type():
    html = "<p>Tuesday schedule</p>"
    encoded = base64.urlsafe_b64encode(html.encode()).decode().rstrip("=")
    message = {
        "payload": {
            "mimeType": "multipart/x-custom",
            "parts": [{"mimeType": "text/html", "body": {"data": encoded}}],
        }
    }

    assert get_message_html_from_message(message) == html


class FakeListRequest:
    def __init__(self, query):
        self.query = query


class FakeListMessages:
    def list(self, *, userId, q, maxResults):
        assert userId == "me"
        assert maxResults == 1
        return FakeListRequest(q)


class FakeListUsers:
    def messages(self):
        return FakeListMessages()


class FakeListBatch(FakeBatch):
    def execute(self):
        for request_id, request in self.requests:
            self.callback(request_id, {"messages": [{"id": f"id-{request.query}"}]}, None)


class FakeListService:
    def users(self):
        return FakeListUsers()

    def new_batch_http_request(self, callback):
        return FakeListBatch(callback)


def test_weekday_message_searches_are_batched_and_return_only_latest():
    result = list_latest_messages_batch(
        FakeListService(),
        "me",
        {"Monday": "monday-query", "Tuesday": "tuesday-query"},
    )

    assert result == {
        "Monday": {"id": "id-monday-query"},
        "Tuesday": {"id": "id-tuesday-query"},
    }
