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

    def request(self, method, url, **kwargs):
        self.requests.append({"method": method, "url": url, **kwargs})
        return self.responses.pop(0) if self.responses else FakeResponse(200, {})


def make_adapter(session):
    return ThreadsAdapter(access_token="secret-token", user_id="123", session=session)


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


@pytest.mark.parametrize("status,error_type", [(401, AuthenticationError), (403, PermissionError), (429, RateLimitError), (500, ProviderError)])
def test_error_mapping(status, error_type):
    session = FakeSession()
    session.queue(status_code=status, payload={"error": {"message": "failure"}})
    adapter = make_adapter(session)
    with pytest.raises(error_type):
        adapter.search_recent("service")


def test_identity_sets_own_username():
    session = FakeSession()
    session.queue(payload={"id": "123", "username": "my_handle"})
    adapter = make_adapter(session)
    result = adapter.validate_identity()
    assert result.ok is True
    assert adapter.own_username == "my_handle"
