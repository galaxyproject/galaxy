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

import requests

from galaxy.exceptions import MessageException

try:
    from fsspec.implementations.github import GithubFileSystem
except ImportError:
    GithubFileSystem = None  # type: ignore[assignment, misc, unused-ignore]

log = logging.getLogger(__name__)

# Contents API endpoint used to create or update a single file (PUT).
_PUT_URL = "https://api.github.com/repos/{org}/{repo}/contents/{path}"


if GithubFileSystem is not None:

    class WritableGithubFileSystem(GithubFileSystem):
        """``GithubFileSystem`` with OAuth2 Bearer auth and write support via the Contents API."""

        def __init__(self, *args, access_token: str | None = None, **kwargs):
            # Store the token before super().__init__, which calls self.ls("") using self.kw.
            self.access_token = access_token
            super().__init__(*args, **kwargs)

        @property
        def kw(self):
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


__all__ = ("WritableGithubFileSystem",)
