"""Unit tests for ``galaxy.job_execution.job_security``."""

from galaxy.job_execution.job_security import resolve_job_key


class TestResolveJobKey:
    def test_bearer_header_wins(self):
        assert resolve_job_key({"Authorization": "Bearer abc123"}, "fallback") == "abc123"

    def test_falls_back_to_query_param_when_no_header(self):
        assert resolve_job_key({}, "fallback") == "fallback"

    def test_returns_none_when_neither_supplied(self):
        assert resolve_job_key({}, None) is None
        assert resolve_job_key({"Authorization": ""}, None) is None

    def test_case_insensitive_header_name(self):
        # ASGI / WSGI normalize differently; the helper must tolerate both.
        assert resolve_job_key({"authorization": "Bearer xyz"}, None) == "xyz"

    def test_case_insensitive_scheme(self):
        assert resolve_job_key({"Authorization": "bearer xyz"}, None) == "xyz"

    def test_non_bearer_scheme_falls_through(self):
        # Don't try to interpret Basic / Digest tokens as job_keys; fall
        # through to the query-string credential so a misconfigured client
        # gets a clean "Invalid job_key" rather than an unexpected match.
        assert resolve_job_key({"Authorization": "Basic abc"}, "fb") == "fb"

    def test_empty_bearer_token_falls_through(self):
        assert resolve_job_key({"Authorization": "Bearer "}, "fb") == "fb"
