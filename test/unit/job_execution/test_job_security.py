"""Unit tests for ``galaxy.job_execution.job_security``."""

from galaxy.job_execution.job_security import (
    DEFAULT_JOB_TOKEN_KIND,
    JOB_FILES_KIND,
    job_files_kind_for_params,
    job_token_kind_for_params,
    resolve_job_key,
)


class TestJobFilesKindForParams:
    def test_no_compute_resource_returns_legacy_kind(self):
        assert job_files_kind_for_params({}) == JOB_FILES_KIND
        assert job_files_kind_for_params(None) == JOB_FILES_KIND
        assert job_files_kind_for_params({"unrelated": "value"}) == JOB_FILES_KIND

    def test_compute_resource_id_scopes_kind(self):
        # Terse by necessity: idencoding caps kinds at <15 chars (see job_security).
        # The id is base62-encoded into the kind; base62(17) == "H".
        assert job_files_kind_for_params({"compute_resource_id": 17}) == "jf:cr:H"

    def test_compute_resource_id_coerced_from_string(self):
        # TPV / DB round-trip may stringify the int; verifier and issuer must
        # converge on the same kind regardless.
        assert job_files_kind_for_params({"compute_resource_id": "17"}) == "jf:cr:H"

    def test_garbage_resource_id_falls_back_to_legacy(self):
        # A non-coercible value isn't a valid binding — treating it as
        # "not BYOC" keeps the legacy verifier path intact rather than
        # creating an unverifiable kind that locks the job out forever.
        assert job_files_kind_for_params({"compute_resource_id": "not-an-int"}) == JOB_FILES_KIND


class TestJobTokenKindForParams:
    def test_default_kind_when_no_overrides(self):
        assert job_token_kind_for_params({}) == DEFAULT_JOB_TOKEN_KIND

    def test_per_destination_override_honoured(self):
        assert job_token_kind_for_params({"job_secret_base": "custom"}) == "custom"

    def test_compute_resource_uses_tenant_scoped_kind(self):
        assert job_token_kind_for_params({"compute_resource_id": 5}) == "jt:cr:5"

    def test_compute_resource_kind_ignores_custom_base(self):
        # A compute-resource job's token kind is namespaced by the resource id,
        # not the per-destination ``job_secret_base`` override — the resource id
        # already segments the keyspace, and composing an arbitrary-length base
        # could exceed idencoding's <15-char kind limit.
        assert job_token_kind_for_params({"compute_resource_id": 5, "job_secret_base": "custom"}) == "jt:cr:5"


class TestResolveJobKey:
    def test_bearer_header_wins(self):
        assert resolve_job_key("Bearer abc123", "fallback") == "abc123"

    def test_falls_back_when_no_header(self):
        assert resolve_job_key(None, "fallback") == "fallback"
        assert resolve_job_key("", "fallback") == "fallback"

    def test_returns_none_when_neither_supplied(self):
        assert resolve_job_key(None, None) is None
        assert resolve_job_key("", None) is None

    def test_case_insensitive_scheme(self):
        # The header *name* is normalized by webob/FastAPI before reaching
        # the helper, but the scheme casing is the caller's responsibility.
        assert resolve_job_key("bearer xyz", None) == "xyz"

    def test_non_bearer_scheme_falls_through(self):
        # Don't try to interpret Basic / Digest tokens as job_keys; fall
        # through to the query-string credential so a misconfigured client
        # gets a clean "Invalid job_key" rather than an unexpected match.
        assert resolve_job_key("Basic abc", "fb") == "fb"

    def test_empty_bearer_token_falls_through(self):
        assert resolve_job_key("Bearer ", "fb") == "fb"
