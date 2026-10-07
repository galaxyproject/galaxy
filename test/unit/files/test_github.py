import base64
import json
import os
import re
from unittest.mock import (
    MagicMock,
    patch,
)

import pytest
import responses

from galaxy.exceptions import MessageException
from galaxy.files.models import FilesSourceRuntimeContext
from galaxy.files.sources.github import GithubFilesSource
from galaxy.files.sources.github_fsspec import (
    list_authorized_repositories,
    WritableGithubFileSystem,
)
from galaxy.files.templates.models import OAUTH2_CONFIGURED_SOURCES
from galaxy.util import config_templates
from galaxy.util.unittest_utils import skip_unless_environ
from ._util import (
    configured_file_sources,
    list_root,
    user_context_fixture,
)


def _github_source(conf) -> GithubFilesSource:
    file_sources = configured_file_sources(conf)
    return file_sources.get_file_source_path("gxfiles://test1").file_source


def _source_config(**overrides) -> dict:
    config = {"type": "github", "id": "test1", "org": "o", "repo": "r", "access_token": "gho_token"}
    config.update(overrides)
    return config


def _runtime_context(source: GithubFilesSource) -> FilesSourceRuntimeContext:
    return source._get_runtime_context(user_context=user_context_fixture())


def test_plugin_type():
    assert GithubFilesSource.plugin_type == "github"


def test_github_is_oauth2_configured():
    oauth2 = OAUTH2_CONFIGURED_SOURCES["github"]
    assert oauth2.authorize_url == "https://github.com/login/oauth/authorize"
    assert oauth2.token_url == "https://github.com/login/oauth/access_token"


@responses.activate
def test_open_fs_passes_repo_branch_and_token():
    _stub_repo_tree()
    source = _github_source([_source_config(org="octocat", repo="Hello-World", branch="test")])
    fs = source._open_fs(_runtime_context(source), {"use_listings_cache": True, "skip_instance_cache": True})
    # State verification: assert the config actually landed on the constructed filesystem where the
    # rest of the plugin reads it (branch -> sha -> fs.root), rather than only that kwargs were passed.
    assert fs.org == "octocat"
    assert fs.repo == "Hello-World"
    assert fs.root == "test"
    assert fs.access_token == "gho_token"


def test_to_filesystem_path():
    source = _github_source([_source_config()])
    # config is unused by this transform; None is fine at runtime.
    assert source._to_filesystem_path("/", None) == ""  # type: ignore[arg-type]
    assert source._to_filesystem_path("/dir/file.txt", None) == "dir/file.txt"  # type: ignore[arg-type]


def test_write_from_uses_configured_commit_message():
    source = _github_source([_source_config(writable=True, commit_message="Custom {path}")])
    context = _runtime_context(source)
    mock_fs = MagicMock()
    with patch.object(source, "_open_fs", return_value=mock_fs):
        source._write_from("/sub/data.txt", "/local/data.txt", context)
    mock_fs.put_file.assert_called_once()
    args, kwargs = mock_fs.put_file.call_args
    assert args[0] == "/local/data.txt"
    assert args[1] == "sub/data.txt"
    assert kwargs["message"] == "Custom sub/data.txt"


# Base kwargs for a real WritableGithubFileSystem. Passing `sha` avoids the default-branch
# lookup request; `skip_instance_cache` forces a fresh instance so its init tree request
# fires under `responses` in every test.
_REPO_KWARGS = {"org": "octocat", "repo": "Hello-World", "sha": "main", "skip_instance_cache": True}
_CONTENTS_BASE = "https://api.github.com/repos/octocat/Hello-World/contents"


def _stub_repo_tree():
    # Served during WritableGithubFileSystem.__init__ (self.ls("")) so a real instance builds.
    responses.add(
        responses.GET,
        re.compile(r"https://api\.github\.com/repos/octocat/Hello-World/git/trees/.*"),
        json={"tree": [], "truncated": False},
    )


def _make_fs(access_token="gho_token"):
    return WritableGithubFileSystem(access_token=access_token, **_REPO_KWARGS)


@responses.activate
def test_put_file_creates_new_file(tmp_path):
    _stub_repo_tree()
    # Probe for an existing blob returns 404 -> create (no sha in payload).
    responses.add(responses.GET, re.compile(rf"{re.escape(_CONTENTS_BASE)}/dir/new\.txt.*"), status=404)
    responses.add(responses.PUT, f"{_CONTENTS_BASE}/dir/new.txt", json={"content": {}}, status=201)

    local = tmp_path / "f.txt"
    local.write_bytes(b"hello world")
    _make_fs().put_file(str(local), "dir/new.txt", message="Add it")

    put = responses.calls[-1].request
    assert put.method == "PUT"
    assert put.body is not None
    body = json.loads(put.body)
    assert body["message"] == "Add it"
    assert body["branch"] == "main"
    assert body["content"] == base64.b64encode(b"hello world").decode("ascii")
    assert "sha" not in body
    # The OAuth2 token is sent as a Bearer credential on the real request.
    assert put.headers["Authorization"] == "Bearer gho_token"


@responses.activate
def test_put_file_updates_existing_file(tmp_path):
    _stub_repo_tree()
    # Probe returns the current blob sha -> update (sha required in payload).
    responses.add(
        responses.GET,
        re.compile(rf"{re.escape(_CONTENTS_BASE)}/existing\.txt.*"),
        json={"sha": "existing-blob-sha"},
        status=200,
    )
    responses.add(responses.PUT, f"{_CONTENTS_BASE}/existing.txt", json={"content": {}}, status=200)

    local = tmp_path / "f.txt"
    local.write_bytes(b"updated")
    _make_fs().put_file(str(local), "existing.txt")

    request_body = responses.calls[-1].request.body
    assert request_body is not None
    body = json.loads(request_body)
    assert body["sha"] == "existing-blob-sha"
    assert body["message"] == "Add existing.txt (uploaded from Galaxy)"


@responses.activate
def test_put_file_raises_on_error_response(tmp_path):
    _stub_repo_tree()
    responses.add(responses.GET, re.compile(rf"{re.escape(_CONTENTS_BASE)}/bad\.txt.*"), status=404)
    responses.add(responses.PUT, f"{_CONTENTS_BASE}/bad.txt", json={"message": "Validation Failed"}, status=422)

    local = tmp_path / "f.txt"
    local.write_bytes(b"data")
    with pytest.raises(MessageException, match="422"):
        _make_fs().put_file(str(local), "bad.txt")


@responses.activate
def test_put_file_requires_token(tmp_path):
    _stub_repo_tree()
    local = tmp_path / "f.txt"
    local.write_bytes(b"data")
    with pytest.raises(MessageException, match="access token"):
        _make_fs(access_token=None).put_file(str(local), "remote.txt")


@responses.activate
def test_get_token_from_code_always_sends_json_accept_header():
    # Token requests carry Accept: application/json unconditionally so form-encoding providers
    # like GitHub return JSON; the OAuth2Configuration does not need to opt in.
    responses.add(responses.POST, "https://github.com/login/oauth/access_token", json={"access_token": "x"})
    config = config_templates.OAuth2Configuration(
        authorize_url="https://github.com/login/oauth/authorize",
        token_url="https://github.com/login/oauth/access_token",
        authorize_params={},
    )
    client_pair = config_templates.OAuth2ClientPair(client_id="cid", client_secret="csecret")
    config_templates.get_token_from_code_raw("the-code", client_pair, config, redirect_uri=None)
    assert responses.calls[-1].request.headers["Accept"] == "application/json"


@responses.activate
def test_list_authorized_repositories_combines_installations():
    responses.add(
        responses.GET,
        "https://api.github.com/user/installations",
        json={"installations": [{"id": 1}, {"id": 2}]},
    )
    responses.add(
        responses.GET,
        "https://api.github.com/user/installations/1/repositories",
        json={"repositories": [{"full_name": "galaxyproject/tools"}, {"full_name": "galaxyproject/galaxy"}]},
    )
    responses.add(
        responses.GET,
        "https://api.github.com/user/installations/2/repositories",
        json={"repositories": [{"full_name": "me/data"}]},
    )

    repositories = list_authorized_repositories("gho_token")

    # Repositories from every installation are combined and sorted by full name.
    assert repositories == [
        {"owner": "galaxyproject", "repo": "galaxy", "full_name": "galaxyproject/galaxy"},
        {"owner": "galaxyproject", "repo": "tools", "full_name": "galaxyproject/tools"},
        {"owner": "me", "repo": "data", "full_name": "me/data"},
    ]
    # The access token is sent as a Bearer credential.
    assert responses.calls[0].request.headers["Authorization"] == "Bearer gho_token"


@responses.activate
def test_list_authorized_repositories_translates_http_error():
    # A failed GitHub API call must surface as a clean MessageException carrying GitHub's own
    # message, not a leaked 500 from requests' raise_for_status.
    responses.add(
        responses.GET,
        "https://api.github.com/user/installations",
        json={"message": "Resource not accessible by integration"},
        status=403,
    )

    with pytest.raises(MessageException, match="Resource not accessible by integration") as exc_info:
        list_authorized_repositories("gho_token")
    assert "403" in str(exc_info.value)
    assert exc_info.value.status_code == 400


# Transient/network failures that should skip rather than fail the live smoke test.
_TRANSIENT_MARKERS = ("rate limit", "403", "connection", "timed out", "timeout", "temporarily")


@skip_unless_environ("GALAXY_TEST_GITHUB_TOKEN")
def test_repo_listing_against_github():
    """Live smoke test: list a public repo using a real token from the environment."""
    conf = [
        {
            "type": "github",
            "id": "test1",
            "org": "octocat",
            "repo": "Hello-World",
            "access_token": os.environ["GALAXY_TEST_GITHUB_TOKEN"],
        }
    ]
    user_context = user_context_fixture()
    file_sources = configured_file_sources(conf)
    try:
        res = list_root(file_sources, "gxfiles://test1", recursive=False, user_context=user_context)
    except MessageException as e:
        # Only tolerate transient/rate-limit conditions; surface genuine regressions.
        if any(marker in str(e).lower() for marker in _TRANSIENT_MARKERS):
            pytest.skip(f"GitHub API unavailable or rate-limited: {e}")
        raise
    assert len(res) > 0, "Expected to find files/directories in the public GitHub repository"
