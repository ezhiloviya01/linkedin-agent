import os
import sys

# Make the project root importable and avoid needing a real API key
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("GEMINI_API_KEY", "test-key")

import check_post


class FakeResponse:
    def __init__(self, text):
        self.text = text


class FakeModels:
    def __init__(self, text=None, error=None):
        self.text = text
        self.error = error

    def generate_content(self, model, contents):
        if self.error:
            raise self.error
        return FakeResponse(self.text)


class FakeClient:
    def __init__(self, text=None, error=None):
        self.models = FakeModels(text, error)


CONFIG = {"business": "Test company"}


def test_empty_post_fails(monkeypatch):
    result = check_post.check_post("   ", CONFIG)
    assert result.startswith("FAIL")


def test_pass_decision(monkeypatch):
    monkeypatch.setattr(check_post, "client", FakeClient("PASS\nLooks good."))
    result = check_post.check_post("Hello world", CONFIG)
    assert result == "PASS\nLooks good."


def test_fail_decision(monkeypatch):
    monkeypatch.setattr(check_post, "client", FakeClient("FAIL\nUnsupported claim."))
    result = check_post.check_post("We are number 1", CONFIG)
    assert result.startswith("FAIL")


def test_unclear_response_fails_closed(monkeypatch):
    monkeypatch.setattr(check_post, "client", FakeClient("Maybe it is fine"))
    result = check_post.check_post("Hello world", CONFIG)
    assert result.startswith("FAIL")


def test_gemini_error_is_not_approved(monkeypatch):
    monkeypatch.setattr(check_post, "client", FakeClient(error=RuntimeError("boom")))
    result = check_post.check_post("Hello world", CONFIG)
    assert result.startswith("CHECK_ERROR")
    assert not result.startswith("PASS")