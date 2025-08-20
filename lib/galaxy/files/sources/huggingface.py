"""
Hugging Face Hub file source plugin using fsspec.
"""

import logging
from typing import (
    Annotated,
    Optional,
    Union,
)

from fsspec import AbstractFileSystem
from pydantic import Field

from galaxy.files.models import (
    AnyRemoteEntry,
    FilesSourceRuntimeContext,
    RemoteDirectory,
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

    def _adapt_path(self, path: str) -> str:
        """Transform Galaxy path to Hugging Face filesystem path."""
        if path == "/":
            # Hugging Face does not implement access to the repositories root
            return ""
        # Remove leading slash for HF compatibility
        return path.lstrip("/")

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
        path = self._adapt_path(path)
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
            repos_iter = api.list_models(search=query, sort="downloads", direction=-1, limit=MAX_REPO_LIMIT)

            # Convert repositories to directory entries
            entries_list = []
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
