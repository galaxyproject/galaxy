"""Writable fsspec filesystem for GitHub repositories.

The ``GithubFileSystem`` shipped with fsspec is read-only (its ``_open`` rejects any write
mode). This module subclasses it to add ``put_file``, which uploads a file by committing it
to the configured branch through the GitHub Contents API with an automatic commit message.

The Galaxy GitHub file source plugin (``github.py``) wraps this filesystem. It authenticates
with an OAuth2 access token sent as a ``Bearer`` credential (overriding fsspec's HTTP Basic
auth), which is used for every request including uploads. Writing requires a token with write
access to the repository.
"""

import base64
import logging

from galaxy.exceptions import MessageException
from galaxy.util import requests

try:
    from fsspec.implementations.github import GithubFileSystem
except ImportError:
    GithubFileSystem = None  # type: ignore[assignment, misc, unused-ignore]

log = logging.getLogger(__name__)

# Contents API endpoint used to create or update a single file (PUT).
_PUT_URL = "https://api.github.com/repos/{org}/{repo}/contents/{path}"

# Endpoints used to enumerate the repositories the user granted the GitHub App.
_INSTALLATIONS_URL = "https://api.github.com/user/installations"
_INSTALLATION_REPOS_URL = "https://api.github.com/user/installations/{installation_id}/repositories"
_PER_PAGE = 100
_API_TIMEOUT = 30


def _github_api_headers(access_token: str) -> dict[str, str]:
    """Bearer-auth headers for GitHub REST API calls (mirrors ``WritableGithubFileSystem.kw``)."""
    return {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _raise_for_github_error(response: requests.Response) -> None:
    """Translate a failed GitHub API response into a user-facing ``MessageException``.

    ``requests``' own ``raise_for_status`` raises an ``HTTPError`` that would surface as an
    opaque HTTP 500. Instead we log GitHub's own diagnostics (the response body and the
    ``x-accepted-github-permissions`` / rate-limit headers, which pinpoint *why* a 403 happened)
    and raise a clean ``MessageException`` carrying GitHub's message back to the user.
    """
    if response.ok:
        return
    # Headers GitHub uses to explain a 403: the permission the endpoint requires and whether the
    # request was rate limited.
    diagnostic_headers = {
        header: response.headers[header]
        for header in ("x-accepted-github-permissions", "x-ratelimit-remaining", "x-github-request-id")
        if header in response.headers
    }
    log.warning(
        "GitHub API request to %s failed with %s: %s (headers: %s)",
        response.url,
        response.status_code,
        response.text,
        diagnostic_headers,
    )
    raise MessageException(f"GitHub API request failed with {response.status_code}: {response.text}")


def _paginate(url: str, headers: dict[str, str], items_key: str) -> list[dict]:
    """Yield all items across paginated GitHub responses keyed by ``items_key``."""
    items: list[dict] = []
    page = 1
    while True:
        response = requests.get(
            url, headers=headers, params={"per_page": _PER_PAGE, "page": page}, timeout=_API_TIMEOUT
        )
        _raise_for_github_error(response)
        page_items = response.json().get(items_key, [])
        items.extend(page_items)
        if len(page_items) < _PER_PAGE:
            break
        page += 1
    return items


def list_authorized_repositories(access_token: str) -> list[dict]:
    """Return the repositories the user authorized the GitHub App to access.

    Combines the repositories granted across every App installation the user can
    access. Each entry is ``{"owner": ..., "repo": ..., "full_name": "owner/repo"}``.
    """
    headers = _github_api_headers(access_token)
    installations = _paginate(_INSTALLATIONS_URL, headers, "installations")
    repositories: dict[str, dict] = {}
    for installation in installations:
        installation_id = installation["id"]
        url = _INSTALLATION_REPOS_URL.format(installation_id=installation_id)
        for repository in _paginate(url, headers, "repositories"):
            full_name = repository["full_name"]
            if full_name in repositories:
                continue
            owner, _, repo = full_name.partition("/")
            repositories[full_name] = {"owner": owner, "repo": repo, "full_name": full_name}
    return sorted(repositories.values(), key=lambda entry: entry["full_name"].lower())


if GithubFileSystem is not None:

    class WritableGithubFileSystem(GithubFileSystem):
        """``GithubFileSystem`` with OAuth2 Bearer auth and write support via the Contents API."""

        def __init__(self, *args, access_token: str | None = None, **kwargs):
            # Store the token before super().__init__, which calls self.ls("") using self.kw.
            self.access_token = access_token
            super().__init__(*args, **kwargs)

        @property
        def kw(self) -> dict:
            """Authenticate every request with the OAuth2 token as a Bearer credential.

            fsspec's ``GithubFileSystem`` uses HTTP Basic auth keyed on ``username``; an OAuth2
            access token has no username, so we send it via the ``Authorization`` header instead.
            """
            if self.access_token:
                return {"headers": {"Authorization": f"Bearer {self.access_token}"}}
            return super().kw

        def put_file(self, lpath: str, rpath: str, message: str | None = None, **kwargs) -> None:
            """Upload a local file to the repository, committing it to the current branch."""
            if not self.access_token:
                raise MessageException(
                    "Writing to a GitHub repository requires an authenticated file source "
                    "with an access token that has write access to the repository."
                )
            rpath = self._strip_protocol(rpath)
            with open(lpath, "rb") as f:
                content = base64.b64encode(f.read()).decode("ascii")

            payload = {
                "message": message or f"Add {rpath} (uploaded from Galaxy)",
                "content": content,
                "branch": self.root,
            }
            # The Contents API requires the current blob sha to update an existing file;
            # it must be omitted when creating a new one.
            existing_sha = self._existing_sha(rpath)
            if existing_sha is not None:
                payload["sha"] = existing_sha

            url = _PUT_URL.format(org=self.org, repo=self.repo, path=rpath)
            response = requests.put(url, json=payload, timeout=self.timeout, **self.kw)
            if response.status_code not in (200, 201):
                raise MessageException(
                    f"Failed to upload file to GitHub ({self.org}/{self.repo}:{rpath}). "
                    f"GitHub responded with {response.status_code}: {response.text}"
                )
            self.invalidate_cache(self._parent(rpath))

        def _existing_sha(self, rpath: str) -> str | None:
            """Return the blob sha of an existing file at ``rpath``, or None if absent."""
            url = self.content_url.format(org=self.org, repo=self.repo, path=rpath, sha=self.root)
            response = requests.get(url, timeout=self.timeout, **self.kw)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            data = response.json()
            # A directory path returns a list; only a file response carries a sha.
            if isinstance(data, dict):
                return data.get("sha")
            return None

else:
    WritableGithubFileSystem = None  # type: ignore[assignment, misc, unused-ignore]


__all__ = ("WritableGithubFileSystem", "list_authorized_repositories")
