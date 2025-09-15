"""
Hugging Face Hub file source plugin using fsspec.
"""

import logging
from typing import (
    Annotated,
    Literal,
    Optional,
    Union,
)

from fsspec import AbstractFileSystem
from pydantic import Field

from galaxy.files.models import (
    AnyRemoteEntry,
    FilesSourceRuntimeContext,
    RemoteDirectory,
    RemoteFileHash,
)

try:
    from huggingface_hub import (
        HfApi,
        HfFileSystem,
    )
except ImportError:
    HfApi = None
    HfFileSystem = None

from galaxy.exceptions import MessageException
from galaxy.files.sources._fsspec import (
    CacheOptionsDictType,
    FsspecBaseFileSourceConfiguration,
    FsspecBaseFileSourceTemplateConfiguration,
    FsspecFilesSource,
)
from galaxy.util.config_templates import TemplateExpansion

log = logging.getLogger(__name__)

SortByOptions = Literal["last_modified", "trending_score", "created_at", "downloads", "likes"]

DEFAULT_SORT_BY: SortByOptions = "downloads"

MAX_REPO_LIMIT = 1000


class HuggingFaceFileSourceTemplateConfiguration(FsspecBaseFileSourceTemplateConfiguration):
    token: Annotated[
        Union[str, TemplateExpansion, None],
        Field(
            description="Hugging Face API token for accessing private model repositories. "
            "If not provided, only public repositories will be accessible.",
        ),
    ] = None
    endpoint: Annotated[
        Union[str, TemplateExpansion, None],
        Field(
            description="Custom endpoint for Hugging Face Hub. "
            "If not provided, the default Hugging Face Hub will be used (https://huggingface.co).",
        ),
    ] = None


class HuggingFaceFileSourceConfiguration(FsspecBaseFileSourceConfiguration):
    token: Optional[str] = None
    endpoint: Optional[str] = None


class HuggingFaceFilesSource(
    FsspecFilesSource[HuggingFaceFileSourceTemplateConfiguration, HuggingFaceFileSourceConfiguration]
):
    plugin_type = "huggingface"
    required_module = HfFileSystem
    required_package = "huggingface_hub"

    template_config_class = HuggingFaceFileSourceTemplateConfiguration
    resolved_config_class = HuggingFaceFileSourceConfiguration

    def _open_fs(
        self,
        context: FilesSourceRuntimeContext[HuggingFaceFileSourceConfiguration],
        cache_options: CacheOptionsDictType,
    ) -> AbstractFileSystem:
        if HfFileSystem is None:
            raise self.required_package_exception

        config = context.config
        return HfFileSystem(
            token=config.token or False,  # Use False to disable authentication
            endpoint=config.endpoint,
            **cache_options,
        )

    def _to_filesystem_path(self, path: str) -> str:
        """Transform entry path to Hugging Face filesystem path."""
        if path == "/":
            # Hugging Face does not implement access to the repositories root
            return ""
        # Remove leading slash for HF compatibility
        return path.lstrip("/")

    def _extract_timestamp(self, info: dict) -> Optional[str]:
        """Extract timestamp from Hugging Face file info to use it in the RemoteFile entry."""
        last_commit: dict = info.get("last_commit", {})
        return last_commit.get("date")

    def _get_file_hashes(self, info: dict) -> Optional[list[RemoteFileHash]]:
        """Get optional file hashes provided by Hugging Face for the RemoteFile entry."""
        # Files stored in Hugging Face repositories using Git LFS may have SHA-256 hashes.
        lfs = info.get("lfs") or {}
        sha256 = lfs.get("sha256")
        return [RemoteFileHash(hash_function="SHA-256", hash_value=sha256)] if sha256 else None

    def _list(
        self,
        context: FilesSourceRuntimeContext[HuggingFaceFileSourceConfiguration],
        path="/",
        recursive=False,
        write_intent: bool = False,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        query: Optional[str] = None,
        sort_by: Optional[str] = None,
    ) -> tuple[list[AnyRemoteEntry], int]:
        # If we're at the root, list repositories using HfApi
        if path == "/":
            return self._list_repositories(config=context.config, limit=limit, offset=offset, query=query)

        # For non-root paths, use the parent implementation
        return super()._list(
            context=context,
            path=path,
            recursive=recursive,
            limit=limit,
            offset=offset,
            query=query,
            sort_by=sort_by,
        )

    def _list_repositories(
        self,
        config: HuggingFaceFileSourceConfiguration,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        query: Optional[str] = None,
    ) -> tuple[list[AnyRemoteEntry], int]:
        if HfApi is None:
            raise self.required_package_exception

        api = HfApi(
            token=config.token or False,  # Use False to disable authentication
            endpoint=config.endpoint,
        )
        try:
            repos_iter = api.list_models(search=query, sort=DEFAULT_SORT_BY, direction=-1, limit=MAX_REPO_LIMIT)

            # Convert repositories to directory entries
            entries_list: list[AnyRemoteEntry] = []
            for repo in repos_iter:
                repo_id = repo.id if hasattr(repo, "id") else str(repo)
                entry = RemoteDirectory(
                    name=repo_id,
                    uri=self.uri_from_path(repo_id),
                    path=repo_id,
                )
                entries_list.append(entry)

            total_count = len(entries_list)

            # Apply pagination
            if offset is not None and limit is not None:
                entries_list = entries_list[offset : offset + limit]
            elif limit is not None:
                entries_list = entries_list[:limit]

            return entries_list, total_count

        except Exception as e:
            raise MessageException(f"Failed to list repositories from Hugging Face Hub: {e}") from e


__all__ = ["HuggingFaceFilesSource"]
