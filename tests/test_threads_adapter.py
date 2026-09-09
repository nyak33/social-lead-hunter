import requests
import pytest

from social_lead_hunter.platforms.base import AuthenticationError, PermissionError, RateLimitError, ProviderError
from social_lead_hunter.platforms.threads import ThreadsAdapter


class FakeResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.text = text

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self):
        self.responses = []
        self.requests = []

    def queue(self, status_code=200, payload=None, text=""):
        self.responses.append(FakeResponse(status_code, payload, text))

    def queue_exception(self, exc):
        self.responses.append(exc)

    def request(self, method, url, **kwargs):
        self.requests.append({"method": method, "url": url, **kwargs})
        if not self.responses:
            return FakeResponse(200, {})
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def make_adapter(session, **kwargs):
    return ThreadsAdapter(access_token="secret-token", user_id="123", session=session, retry_backoff_seconds=0, **kwargs)


def test_search_uses_recent_keyword_search():
    session = FakeSession()
    session.queue(payload={"data": []})
    adapter = make_adapter(session)
    adapter.search_recent("custom service", limit=5)
    request = session.requests[-1]
    assert request["method"] == "GET"
    assert request["url"].endswith("/keyword_search")
    assert request["params"]["q"] == "custom service"
    assert request["params"]["search_type"] == "RECENT"
    assert request["params"]["limit"] == 5


def test_reply_uses_reply_to_id_and_auto_publish():
    session = FakeSession()
    session.queue(payload={"id": "reply-id"})
    adapter = make_adapter(session)
    reply_id = adapter.publish_reply("source-post-id", "Helpful reply")
    request = session.requests[-1]
    assert reply_id == "reply-id"
    assert request["method"] == "POST"
    assert request["url"].endswith("/me/threads")
    assert request["params"]["media_type"] == "TEXT"
    assert request["params"]["reply_to_id"] == "source-post-id"
    assert request["params"]["auto_publish_text"] == "true"


def test_debug_token_checks_required_scopes():
    session = FakeSession()
    session.queue(payload={"data": {"is_valid": True, "scopes": ["threads_basic", "threads_keyword_search", "threads_content_publish"]}})
    adapter = make_adapter(session)
    result = adapter.validate_reply_capability()
    assert result.ok is True
    assert session.requests[-1]["url"].endswith("/debug_token")


@pytest.mark.parametrize("status,error_type", [(401, AuthenticationError), (403, PermissionError), (429, RateLimitError), (400, ProviderError)])
def test_non_retryable_error_mapping(status, error_type):
    session = FakeSession()
    session.queue(status_code=status, payload={"error": {"message": "failure"}})
    adapter = make_adapter(session, max_retries=2)
    with pytest.raises(error_type):
        adapter.search_recent("service")
    assert len(session.requests) == 1


def test_retries_temporary_server_error_then_succeeds():
    session = FakeSession()
    session.queue(status_code=500, payload={"error": {"message": "temporary"}})
    session.queue(payload={"data": []})
    adapter = make_adapter(session, max_retries=2)
    assert adapter.search_recent("service") == []
    assert len(session.requests) == 2


def test_retries_connection_error_then_succeeds():
    session = FakeSession()
    session.queue_exception(requests.ConnectionError("temporary network failure"))
    session.queue(payload={"data": []})
    adapter = make_adapter(session, max_retries=2)
    assert adapter.search_recent("service") == []
    assert len(session.requests) == 2


def test_temporary_error_stops_after_bounded_retries():
    session = FakeSession()
    session.queue(status_code=500)
    session.queue(status_code=502)
    session.queue(status_code=503)
    adapter = make_adapter(session, max_retries=2)
    with pytest.raises(ProviderError):
        adapter.search_recent("service")
    assert len(session.requests) == 3


def test_identity_sets_own_username():
    session = FakeSession()
    session.queue(payload={"id": "123", "username": "my_handle"})
    adapter = make_adapter(session)
    result = adapter.validate_identity()
    assert result.ok is True
    assert adapter.own_username == "my_handle"
