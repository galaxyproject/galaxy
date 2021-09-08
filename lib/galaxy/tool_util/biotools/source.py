import functools
import json
import os
from typing import Callable, Dict, List, Optional

import requests

from galaxy.util import DEFAULT_SOCKET_TIMEOUT
from .interface import BiotoolsEntry


class BiotoolsMetadataSource:

    def get_biotools_metadata(self, biotools_reference: str) -> Optional[BiotoolsEntry]:
        """Return a BiotoolsEntry if available."""


class GitContentBiotoolsMetadataSource(BiotoolsMetadataSource):
    """Parse entries from a repository clone of https://github.com/bio-tools/content."""

    def __init__(self, content_directory):
        self._content_directory = content_directory

    def get_biotools_metadata(self, biotools_reference: str) -> Optional[BiotoolsEntry]:
        """Return a BiotoolsEntry if available."""
        path = os.path.join(self._content_directory, "data", biotools_reference, f"{biotools_reference}.biotools.json")
        if not os.path.exists(path):
            return None
        with open(path, "r") as f:
            content_json = json.load(f)
            return BiotoolsEntry.from_json(content_json)


class InMemoryCache:
    backend: Dict[str, Optional[str]] = {}

    def get(self, key: str, createfunc: Callable[[], Optional[str]]):
        backend = self.backend
        if key not in backend:
            backend[key] = createfunc()

        return backend.get(key)


class ApiBiotoolsMetadataSource(BiotoolsMetadataSource):
    """Parse entries from bio.tools API."""

    def __init__(self, cache=None):
        self._cache = cache or InMemoryCache()

    def _raw_get_metadata(self, biotools_reference) -> Optional[str]:
        api_url = f"https://bio.tools/api/tool/{biotools_reference}?format=json"
        req = requests.get(api_url, timeout=DEFAULT_SOCKET_TIMEOUT)
        req.encoding = req.apparent_encoding
        if req.status_code == 404:
            return None
        else:
            return req.text

    def get_biotools_metadata(self, biotools_reference: str) -> Optional[BiotoolsEntry]:
        createfunc = functools.partial(self._raw_get_metadata, biotools_reference)
        content = self._cache.get(key=biotools_reference, createfunc=createfunc)
        if content is not None:
            return BiotoolsEntry.from_json(json.loads(content))
        else:
            return None


class CascadingBiotoolsMetadataSource(BiotoolsMetadataSource):

    def __init__(self, use_api=False, cache=None, content_directory: Optional[str] = None):
        sources: List[BiotoolsMetadataSource] = []
        if content_directory:
            git_content_source = GitContentBiotoolsMetadataSource(content_directory)
            sources.append(git_content_source)
        if use_api:
            api_metadata_source = ApiBiotoolsMetadataSource(cache=cache)
            sources.append(api_metadata_source)
        self._sources = sources

    def get_biotools_metadata(self, biotools_reference: str) -> Optional[BiotoolsEntry]:
        for source in self._sources:
            entry = source.get_biotools_metadata(biotools_reference)
            if entry is not None:
                return entry
        return None


class BiotoolsMetadataSourceConfig:
    use_api: bool = False
    content_directory: Optional[str] = None
    cache = None


def get_biotools_metadata_source(metadata_source_config: BiotoolsMetadataSourceConfig) -> BiotoolsMetadataSource:
    return CascadingBiotoolsMetadataSource(
        use_api=metadata_source_config.use_api,
        content_directory=metadata_source_config.content_directory,
        cache=metadata_source_config.cache,
    )
