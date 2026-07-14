"""GitHub repository file source plugin using fsspec.

Each instance exposes a single repository (at a branch or commit) for browsing and download,
and optionally for upload: writes commit the uploaded file to the branch through the GitHub
Contents API with an automatic commit message. Users who need several repositories create
several instances of the template, one per repository.

Authentication uses an OAuth2 access token obtained through Galaxy's OAuth2 flow (see the
``github`` entry in ``OAUTH2_CONFIGURED_SOURCES``). The token is passed to GitHub as a
``Bearer`` credential by :class:`WritableGithubFileSystem`.
"""

import logging
from typing import (
    Annotated,
)

from fsspec import AbstractFileSystem
from pydantic import (
    AliasChoices,
    Field,
)

from galaxy.files.models import FilesSourceRuntimeContext
from galaxy.files.sources._fsspec import (
    CacheOptionsDictType,
    FsspecBaseFileSourceConfiguration,
    FsspecBaseFileSourceTemplateConfiguration,
    FsspecFilesSource,
)
from galaxy.files.sources.github_fsspec import WritableGithubFileSystem
from galaxy.util.config_templates import TemplateExpansion

log = logging.getLogger(__name__)

DEFAULT_COMMIT_MESSAGE = "Add {path} (uploaded from Galaxy)"

AccessTokenField = Field(
    ...,
    title="Access Token",
    description="OAuth2 access token used to authenticate with GitHub.",
    validation_alias=AliasChoices("oauth2_access_token", "access_token"),
)


class GithubFileSourceTemplateConfiguration(FsspecBaseFileSourceTemplateConfiguration):
    org: Annotated[
        str | TemplateExpansion,
        Field(description="The GitHub repository owner (a user or organization name)."),
    ]
    repo: Annotated[
        str | TemplateExpansion,
        Field(description="The GitHub repository name."),
    ]
    branch: Annotated[
        str | TemplateExpansion | None,
        Field(
            description="Branch name or commit SHA to browse. "
            "If not provided, the repository's default branch is used.",
        ),
    ] = None
    commit_message: Annotated[
        str | TemplateExpansion | None,
        Field(
            description="Commit message used when uploading files. May contain a '{path}' "
            "placeholder that is replaced with the uploaded file path.",
        ),
    ] = None
    access_token: Annotated[str | TemplateExpansion, AccessTokenField]


class GithubFileSourceConfiguration(FsspecBaseFileSourceConfiguration):
    org: str
    repo: str
    branch: str | None = None
    commit_message: str | None = None
    access_token: Annotated[str, AccessTokenField]


class GithubFilesSource(FsspecFilesSource[GithubFileSourceTemplateConfiguration, GithubFileSourceConfiguration]):
    plugin_type = "github"
    required_module = WritableGithubFileSystem
    required_package = "fsspec"

    template_config_class = GithubFileSourceTemplateConfiguration
    resolved_config_class = GithubFileSourceConfiguration

    def _open_fs(
        self,
        context: FilesSourceRuntimeContext[GithubFileSourceConfiguration],
        cache_options: CacheOptionsDictType,
    ) -> AbstractFileSystem:
        if WritableGithubFileSystem is None:
            raise self.required_package_exception

        config = context.config
        return WritableGithubFileSystem(
            org=config.org,
            repo=config.repo,
            sha=config.branch or None,
            access_token=config.access_token,
            **cache_options,
        )

    def _to_filesystem_path(self, path: str, config: GithubFileSourceConfiguration) -> str:
        """Transform an entry path to a GitHub filesystem path (relative to the repo root)."""
        if path == "/":
            return ""
        return path.lstrip("/")

    def _write_from(
        self,
        target_path: str,
        native_path: str,
        context: FilesSourceRuntimeContext[GithubFileSourceConfiguration],
    ) -> None:
        """Upload a local file to the repository with an automatic commit message."""
        config = context.config
        fs = self._open_fs(context, self._get_cache_options(config))
        rpath = self._to_filesystem_path(target_path, config)
        message_template = config.commit_message or DEFAULT_COMMIT_MESSAGE
        fs.put_file(native_path, rpath, message=message_template.format(path=rpath))


__all__ = ("GithubFilesSource",)
