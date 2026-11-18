import hashlib
import io
import json
import re
import tarfile
import threading
from collections import OrderedDict
from collections.abc import (
    Callable,
    Iterator,
)
from contextlib import (
    AbstractContextManager,
    contextmanager,
)
from functools import partial
from typing import (
    Annotated,
    Any,
    Literal,
    NamedTuple,
)

from pydantic import Field

from galaxy.exceptions import (
    MessageException,
    ObjectNotFound,
    RequestParameterInvalidException,
)
from galaxy.files.models import (
    AnyRemoteEntry,
    BaseFileSourceConfiguration,
    BaseFileSourceTemplateConfiguration,
    FilesSourceRuntimeContext,
    RemoteDirectory,
    RemoteFile,
    RemoteFileHash,
)
from galaxy.files.uris import (
    open_checking_every_redirect,
    refuse_a_private_address,
)
from galaxy.util import requests
from galaxy.util.config_templates import TemplateExpansion
from . import BaseFilesSource

EXAMPLE_URL = "https://www.radar-service.eu"
# RADAR answers at most 100 rows per page
PAGE_SIZE = 100
MAX_REDIRECTS = 5
# a cloud record without archiveCreator is federated: its files live on another RADAR instance
PUBLISHED = "state:PUBLISHED AND technicalMetadata.archiveCreator:*"
DATASET_ID = re.compile(r"[A-Za-z0-9]+")
LUCENE_SPECIAL = re.compile(r'([+\-!(){}\[\]^"~*?:\\/&|])')
# the dataset tar is untrusted input, so bound what reading its headers may fetch
BLOCK_SIZE = 64 * 1024
JUMP_BLOCK_SIZE = 4 * 1024
MAX_READ = 4 * 1024 * 1024
MAX_INDEX_BYTES = 64 * 1024 * 1024
MAX_MEMBERS = 10000
DATA_DIR = "data/dataset/"
# a collection import resolves every file in one process, so keep the file lists of a few datasets there;
# without it a dataset of small files would be downloaded again for each file
INDEX_CACHE_SIZE = 8
_index_cache: "OrderedDict[tuple[str, str], dict[str, _TarMember]]" = OrderedDict()
_index_lock = threading.Lock()


class RadarFileSourceTemplateConfiguration(BaseFileSourceTemplateConfiguration):
    base_url: str | TemplateExpansion
    writable: Literal[False] = False


class RadarFileSourceConfiguration(BaseFileSourceConfiguration):
    base_url: Annotated[
        str,
        Field(
            title="RADAR address",
            description=f"The address of a RADAR instance, e.g. {EXAMPLE_URL}.",
        ),
    ]
    writable: Literal[False] = False


class _TarMember(NamedTuple):
    offset: int
    size: int
    md5: str | None


class RadarFilesSource(BaseFilesSource[RadarFileSourceTemplateConfiguration, RadarFileSourceConfiguration]):
    """Published RADAR datasets, read through the documented dataset tar.

    RADAR has no documented download of a single file, so the files and their sizes come from the headers of
    the dataset's uncompressed BagIt tar, read with Range requests, and their MD5s from its manifest.
    """

    plugin_type = "radar"
    supports_pagination = True
    supports_search = True

    template_config_class = RadarFileSourceTemplateConfiguration
    resolved_config_class = RadarFileSourceConfiguration

    def _list(
        self,
        context: FilesSourceRuntimeContext[RadarFileSourceConfiguration],
        path: str = "/",
        recursive: bool = False,
        write_intent: bool = False,
        limit: int | None = None,
        offset: int | None = None,
        query: str | None = None,
        sort_by: str | None = None,
    ) -> tuple[list[AnyRemoteEntry], int]:
        if recursive:
            raise RequestParameterInvalidException("Recursive listing is not supported for RADAR file sources.")
        config = context.config
        query = query.strip() if query else None
        dataset_id, folder = self._split(path)
        if not dataset_id:
            return self._datasets(config, limit, offset, query)
        members = self._members(config, dataset_id)
        prefix = f"{folder}/" if folder else ""
        directories: set[str] = set()
        entries: list[AnyRemoteEntry] = []
        for name, member in members.items():
            if not name.startswith(prefix):
                continue
            child, _, rest = name[len(prefix) :].partition("/")
            if not child:
                continue
            if rest:
                directories.add(child)
                continue
            hashes = [RemoteFileHash(hash_function="MD5", hash_value=member.md5)] if member.md5 else None
            file_path = f"/{dataset_id}/{name}"
            entries.append(
                RemoteFile(
                    name=child, size=member.size, uri=self.uri_from_path(file_path), path=file_path, hashes=hashes
                )
            )
        if not entries and not directories and folder:
            raise ObjectNotFound(f"The specified RADAR path is not a directory [{path}].")
        entries[:0] = [
            RemoteDirectory(
                name=name,
                uri=self.uri_from_path(f"/{dataset_id}/{prefix}{name}"),
                path=f"/{dataset_id}/{prefix}{name}",
            )
            for name in sorted(directories)
        ]
        if query:
            entries = [entry for entry in entries if query.lower() in entry.name.lower()]
        start = offset or 0
        return entries[start : start + limit if limit is not None else None], len(entries)

    def _realize_to(
        self,
        source_path: str,
        native_path: str,
        context: FilesSourceRuntimeContext[RadarFileSourceConfiguration],
    ) -> None:
        dataset_id, name = self._split(source_path)
        if not dataset_id or not name:
            raise ObjectNotFound(f"The specified RADAR path is not a file [{source_path}].")
        config = context.config
        # an exact match, so no name in the tar can reach outside the dataset's files
        member = self._members(config, dataset_id).get(name)
        if member is None:
            raise ObjectNotFound(f"The specified RADAR path is not a file [{source_path}].")
        md5 = hashlib.md5(usedforsecurity=False)
        written = 0
        with open(native_path, "wb") as out:
            if member.size:
                url = self._download_url(config, dataset_id)
                with self._open_range(config, url, member.offset, member.size) as response:
                    while chunk := response.raw.read(min(1024 * 1024, member.size - written)):
                        md5.update(chunk)
                        written += out.write(chunk)
        if written != member.size or (member.md5 and md5.hexdigest() != member.md5):
            raise MessageException(f"The download of {source_path} from RADAR does not match its size or MD5.")

    def _write_from(
        self,
        target_path: str,
        native_path: str,
        context: FilesSourceRuntimeContext[RadarFileSourceConfiguration],
    ) -> str | None:
        raise MessageException("RADAR file sources are read-only.")

    def _datasets(
        self, config: RadarFileSourceConfiguration, limit: int | None, offset: int | None, query: str | None
    ) -> tuple[list[AnyRemoteEntry], int]:
        search = PUBLISHED
        if query:
            # escaped and lowercased (Lucene operators are uppercase), so the words stay inside the title clause
            words = [LUCENE_SPECIAL.sub(r"\\\1", word.lower()) + "*" for word in query.split()]
            search += f" AND descriptiveMetadata.title:({' AND '.join(words)})"
        # shortcut: a page larger than RADAR's 100 rows is cut to 100; the total stays true, so clients page on
        rows = min(limit or PAGE_SIZE, PAGE_SIZE)
        params = {"query": search, "offset": str(offset or 0), "rows": str(rows)}
        try:
            data = self._get_json(config, self._api_url(config, "datasets"), params)
        except RequestParameterInvalidException as e:
            if not query:
                raise
            raise RequestParameterInvalidException(f"RADAR could not search for {query}.") from e
        entries: list[AnyRemoteEntry] = []
        for dataset in data.get("data", []):
            dataset_id = dataset.get("id")
            if not isinstance(dataset_id, str) or not DATASET_ID.fullmatch(dataset_id):
                continue
            title = (dataset.get("descriptiveMetadata") or {}).get("title")
            entries.append(
                RemoteDirectory(
                    name=title if isinstance(title, str) and title else dataset_id,
                    uri=self.uri_from_path(f"/{dataset_id}"),
                    path=f"/{dataset_id}",
                )
            )
        return entries, data.get("totalHits", len(entries))

    def _members(self, config: RadarFileSourceConfiguration, dataset_id: str) -> dict[str, _TarMember]:
        """The files of a published dataset, by their path below the tar's data/dataset folder."""
        params = {"query": f"id:{dataset_id} AND {PUBLISHED}", "rows": "1"}
        found = self._get_json(config, self._api_url(config, "datasets"), params).get("data") or []
        archive = (found[0].get("archive") or {}) if found else {}
        size = archive.get("size")
        if not isinstance(size, int):
            raise ObjectNotFound(f"There is no published RADAR dataset {dataset_id} at {config.base_url}.")
        # the archive's MD5 changes with its content, so a cached file list is never stale
        key = (self._download_url(config, dataset_id), str(archive.get("checksum") or size))
        with _index_lock:
            if key in _index_cache:
                _index_cache.move_to_end(key)
                return _index_cache[key]
        members = self._read_members(config, dataset_id, size)
        with _index_lock:
            _index_cache[key] = members
            while len(_index_cache) > INDEX_CACHE_SIZE:
                _index_cache.popitem(last=False)
        return members

    def _read_members(self, config: RadarFileSourceConfiguration, dataset_id: str, size: int) -> dict[str, _TarMember]:
        reader = _RangeReader(partial(self._open_range, config), self._download_url(config, dataset_id), size)
        files: dict[str, tarfile.TarInfo] = {}
        manifest: tarfile.TarInfo | None = None
        try:
            with tarfile.open(fileobj=reader, mode="r:") as tar:
                for count, info in enumerate(tar, 1):
                    if count > MAX_MEMBERS:
                        raise MessageException(f"RADAR dataset {dataset_id} has more than {MAX_MEMBERS} files.")
                    _, _, name = info.name.partition("/")
                    if info.isfile() and name.startswith(DATA_DIR):
                        files[name] = info
                    elif info.isfile() and name == "manifest-md5.txt":
                        manifest = info
                md5s = self._manifest(tar, manifest)
        except tarfile.TarError as e:
            raise MessageException(f"The archive of RADAR dataset {dataset_id} could not be read: {e}") from e
        return {
            name[len(DATA_DIR) :]: _TarMember(info.offset_data, info.size, md5s.get(name))
            for name, info in files.items()
        }

    def _manifest(self, tar: tarfile.TarFile, manifest: tarfile.TarInfo | None) -> dict[str, str]:
        if manifest is None or manifest.size > MAX_READ:
            return {}
        content = tar.extractfile(manifest)
        md5s = {}
        for line in content.read().decode("utf-8", "replace").splitlines() if content else []:
            md5, _, name = line.partition(" ")
            name = name.lstrip(" *")
            # BagIt percent-encodes only these in manifest paths
            name = name.replace("%0A", "\n").replace("%0D", "\r").replace("%25", "%")
            if re.fullmatch(r"[0-9a-fA-F]{32}", md5):
                md5s[name] = md5.lower()
        return md5s

    def _get_json(self, config: RadarFileSourceConfiguration, url: str, params: dict[str, str]) -> dict[str, Any]:
        with self._open(config, url, {"Accept": "application/json"}, params) as response:
            try:
                data: dict[str, Any] = json.load(response.raw)
                return data
            except ValueError as e:
                raise MessageException(f"{url} did not answer like a RADAR API.") from e

    @contextmanager
    def _open_range(
        self, config: RadarFileSourceConfiguration, url: str, start: int, length: int
    ) -> Iterator[requests.Response]:
        headers = {"Range": f"bytes={start}-{start + length - 1}", "Accept-Encoding": "identity"}
        with self._open(config, url, headers, decode=False) as response:
            content_range = response.headers.get("Content-Range", "")
            # a server that ignores Range, or answers more than asked, could send many gigabytes
            if response.status_code != 206 or not content_range.startswith(f"bytes {start}-{start + length - 1}/"):
                raise MessageException(f"RADAR at {config.base_url} did not answer a partial download of {url}.")
            yield response

    @contextmanager
    def _open(
        self,
        config: RadarFileSourceConfiguration,
        url: str,
        headers: dict[str, str],
        params: dict[str, str] | None = None,
        decode: bool = True,
    ) -> Iterator[requests.Response]:
        def check_url(hop: str) -> None:
            refuse_a_private_address(hop, self._file_sources_config.fetch_url_allowlist or [], self.label, EXAMPLE_URL)

        def headers_for(hop: str) -> dict[str, str]:
            return {"User-Agent": "Galaxy RADAR file source", **headers}

        with open_checking_every_redirect(url, "RADAR", check_url, headers_for, params, MAX_REDIRECTS) as response:
            response.raw.decode_content = decode
            yield response

    def _api_url(self, config: RadarFileSourceConfiguration, endpoint: str) -> str:
        return f"{config.base_url.strip().rstrip('/')}/radar/api/{endpoint}"

    def _download_url(self, config: RadarFileSourceConfiguration, dataset_id: str) -> str:
        return self._api_url(config, f"datasets/{dataset_id}/download")

    def _split(self, path: str) -> tuple[str | None, str]:
        # the names after the id are matched exactly, so they are not normalized
        dataset_id, _, rest = (path or "").strip("/").partition("/")
        if not dataset_id:
            return None, ""
        if not DATASET_ID.fullmatch(dataset_id):
            raise ObjectNotFound(f"The specified RADAR path has no valid RADAR id [{path}].")
        return dataset_id, rest


class _RangeReader(io.RawIOBase):
    """A seekable view of a remote file for ``tarfile``, fetching blocks with Range requests."""

    def __init__(
        self,
        open_range: Callable[[str, int, int], AbstractContextManager[requests.Response]],
        url: str,
        size: int,
    ):
        self._open_range = open_range
        self._url = url
        self._size = size
        self._pos = 0
        self._block = b""
        self._block_start = 0
        self._fetched = 0

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self._pos

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        base = {io.SEEK_SET: 0, io.SEEK_CUR: self._pos, io.SEEK_END: self._size}[whence]
        self._pos = base + offset
        return self._pos

    def read(self, size: int | None = -1) -> bytes:
        if size is None or size < 0:
            size = self._size - self._pos
        size = min(size, self._size - self._pos)
        if size <= 0:
            return b""
        if size > MAX_READ:
            raise MessageException(f"A header in the RADAR archive {self._url} is too large to read.")
        end = self._pos + size
        block_end = self._block_start + len(self._block)
        if not (self._block_start <= self._pos and end <= block_end):
            # a jump over a file's content usually lands on a big file's next header, so fetch little
            block = BLOCK_SIZE if self._pos == block_end else JUMP_BLOCK_SIZE
            length = min(max(size, block), self._size - self._pos)
            self._fetched += length
            if self._fetched > MAX_INDEX_BYTES:
                raise MessageException(f"The RADAR archive {self._url} has too many files to list.")
            with self._open_range(self._url, self._pos, length) as response:
                self._block = response.raw.read(length)
                # later blocks go straight to where the download link redirected, a hop already checked
                self._url = response.url
                # the archive's own length, since the one in the search index may be out of date
                total = response.headers["Content-Range"].rpartition("/")[2]
                if total.isdigit():
                    self._size = int(total)
            self._block_start = self._pos
        data = self._block[self._pos - self._block_start : end - self._block_start]
        self._pos += len(data)
        return data


__all__ = ("RadarFilesSource",)
