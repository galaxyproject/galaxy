import datetime
import json
import logging
import math
import os
import re
from concurrent.futures import (
    as_completed,
    ThreadPoolExecutor,
)
from typing import (
    Any,
    cast,
    Literal,
    Optional,
)
from urllib.parse import quote

from typing_extensions import (
    TypedDict,
)

log = logging.getLogger(__name__)

from galaxy.exceptions import (
    AuthenticationRequired,
    MessageException,
)
from galaxy.files.models import (
    AnyRemoteEntry,
    Entry,
    EntryData,
    FilesSourceRuntimeContext,
    RemoteDirectory,
    RemoteFile,
    RemoteFileHash,
)
from galaxy.files.sources import DEFAULT_PAGE_LIMIT
from galaxy.files.sources._defaults import DEFAULT_SCHEME
from galaxy.files.sources._rdm import (
    ContainerAndFileIdentifier,
    RDMFileSourceConfiguration,
    RDMFileSourceTemplateConfiguration,
    RDMFilesSource,
    RDMRepositoryInteractor,
)
from galaxy.util import (
    DEFAULT_SOCKET_TIMEOUT,
    requests,
)
from galaxy.util.hash_util import as_hash_function_name

AccessStatus = Literal["public", "restricted"]


class ResourceType(TypedDict):
    id: str


class RecordAccess(TypedDict):
    record: AccessStatus
    files: AccessStatus


class RecordFiles(TypedDict):
    enabled: bool


class IdentifierEntry(TypedDict):
    scheme: str
    identifier: str


class AffiliationEntry(TypedDict):
    id: str
    name: str


class RecordPersonOrOrg(TypedDict):
    family_name: str
    given_name: str
    type: Literal["personal", "organizational"]
    name: str
    identifiers: list[IdentifierEntry]


class Creator(TypedDict):
    person_or_org: RecordPersonOrOrg
    affiliations: Optional[list[AffiliationEntry]]


class RecordMetadata(TypedDict):
    title: str
    resource_type: ResourceType
    publication_date: str
    creators: list[Creator]


class RecordLinks(TypedDict):
    self: str
    self_html: str
    self_iiif_manifest: str
    self_iiif_sequence: str
    files: str
    record: str
    record_html: str
    publish: str
    review: str
    versions: str
    access_links: str
    reserve_doi: str


# AWS S3 multipart default limits (used by Invenio RDM)
MIN_UPLOAD_PART_SIZE = 5 * 1024 * 1024  # 5 MiB
MAX_UPLOAD_PART_SIZE = 5 * 1024**3  # 5 GiB
MAX_UPLOAD_PARTS = 10_000


def calculate_multipart_params(file_size: int, preferred_part_size: int | None = None) -> tuple[int, int]:
    """Calculate parts count and part size for multipart upload.

    Args:
        file_size: Total file size in bytes
        preferred_part_size: Preferred part size in bytes (optional)

    Returns:
        Tuple of (parts_count, part_size)

    Raises:
        ValueError: If the file is larger than MAX_UPLOAD_PARTS * MAX_UPLOAD_PART_SIZE
            (~48.8 TiB), which exceeds the maximum uploadable size.

    Note:
        Maximum uploadable file size is MAX_UPLOAD_PARTS * MAX_UPLOAD_PART_SIZE (~48.8 TiB).
        Files larger than this cannot be uploaded via multipart and raise ValueError.
    """
    if file_size == 0:
        return 1, MIN_UPLOAD_PART_SIZE

    # Start with preferred or minimum part size, clamped to [min, max]
    part_size = preferred_part_size or MIN_UPLOAD_PART_SIZE
    part_size = max(part_size, MIN_UPLOAD_PART_SIZE)
    part_size = min(part_size, MAX_UPLOAD_PART_SIZE)

    # Grow part_size to the minimum that keeps the part count within MAX_UPLOAD_PARTS.
    part_size = max(part_size, math.ceil(file_size / MAX_UPLOAD_PARTS))
    part_size = min(part_size, MAX_UPLOAD_PART_SIZE)

    max_upload_size = MAX_UPLOAD_PARTS * MAX_UPLOAD_PART_SIZE
    if file_size > max_upload_size:
        raise ValueError(
            f"File size {file_size} bytes exceeds the maximum multipart upload size "
            f"of {max_upload_size} bytes ({MAX_UPLOAD_PARTS} parts x {MAX_UPLOAD_PART_SIZE} bytes)."
        )

    parts = math.ceil(file_size / part_size)
    return parts, part_size


class _LimitedFileReader:
    """File-like wrapper that limits reads to a specified number of bytes.

    Enables streaming a slice of a file for upload without loading the
    entire slice into memory. The __len__ method lets requests determine
    the correct Content-Length for the upload.
    """

    def __init__(self, file_obj, length: int):
        self._file = file_obj
        self._length = length

    def read(self, size: int = -1) -> bytes:
        if size is None or size < 0:
            size = self._length
        else:
            size = min(size, self._length)
        data = self._file.read(size)
        self._length -= len(data)
        return data

    def __len__(self) -> int:
        return self._length


class InvenioRequestError(Exception):
    """Raised when an Invenio API request returns an unexpected status code."""

    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.status_code = status_code


class InvenioRecord(TypedDict):
    id: str
    title: str
    created: str
    updated: str
    resource_type: ResourceType
    publication_date: str
    access: RecordAccess
    files: RecordFiles
    metadata: RecordMetadata
    links: RecordLinks


class InvenioRDMFilesSource(RDMFilesSource):
    """A files source for Invenio turn-key research data management repository.

    In Invenio a "Record" represents what we refer to as container in the rdm base class
    """

    plugin_type = "inveniordm"
    supports_pagination = True
    supports_search = True
    rdm_scheme = "invenio"

    def __init__(self, template_config: RDMFileSourceTemplateConfiguration):
        super().__init__(template_config)
        self._scheme_regex = re.compile(rf"^{self.get_scheme()}?://{self.id}|^{DEFAULT_SCHEME}://{self.id}")
        self.repository: InvenioRepositoryInteractor

    def get_scheme(self) -> str:
        return self.scheme if self.scheme and self.scheme != DEFAULT_SCHEME else self.rdm_scheme

    def score_url_match(self, url: str) -> int:
        if match := self._scheme_regex.match(url):
            return match.span()[1]
        else:
            return 0

    def to_relative_path(self, url: str) -> str:
        legacy_uri_root = f"{DEFAULT_SCHEME}://{self.id}"
        if url.startswith(legacy_uri_root):
            return url[len(legacy_uri_root) :]
        else:
            return super().to_relative_path(url)

    def get_repository_interactor(self, repository_url: str) -> RDMRepositoryInteractor:
        return InvenioRepositoryInteractor(repository_url, self)

    def parse_path(self, source_path: str, container_id_only: bool = False) -> ContainerAndFileIdentifier:
        """Parses the given source path and returns the record_id and filename.

        The source path must have the format '/<record_id>/<file_name>'.
        If container_id_only is True, the source path must have the format '/<record_id>' and and an empty filename will be returned.
        """

        def get_error_msg(details: str) -> str:
            return f"Invalid source path: '{source_path}'. Expected format: '{expected_format}'. {details}"

        expected_format = "/<record_id>"
        if not source_path.startswith("/"):
            raise ValueError(get_error_msg("Must start with '/'."))
        parts = source_path[1:].split("/", 2)
        if container_id_only:
            if len(parts) != 1:
                raise ValueError(get_error_msg("Please provide the record_id only."))
            return ContainerAndFileIdentifier(container_id=parts[0], file_identifier="")
        expected_format = "/<record_id>/<file_name>"
        if len(parts) < 2:
            raise ValueError(get_error_msg("Please provide both the record_id and file_name."))
        if len(parts) > 2:
            # TODO: This causes downloads to crash if the filename contains a slash
            raise ValueError(get_error_msg("Too many parts. Please provide the record_id and file_name only."))
        record_id, file_name = parts
        return ContainerAndFileIdentifier(container_id=record_id, file_identifier=file_name)

    def get_container_id_from_path(self, source_path: str) -> str:
        return self.parse_path(source_path, container_id_only=True).container_id

    def _list(
        self,
        context: FilesSourceRuntimeContext[RDMFileSourceConfiguration],
        path="/",
        recursive=False,
        write_intent: bool = False,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        query: Optional[str] = None,
        sort_by: Optional[str] = None,
    ) -> tuple[list[AnyRemoteEntry], int]:
        is_root_path = path == "/"
        if is_root_path:
            records, total_hits = self.repository.get_file_containers(
                context, write_intent, limit=limit, offset=offset, query=query
            )
            return cast(list[AnyRemoteEntry], records), total_hits
        record_id = self.get_container_id_from_path(path)
        files = self.repository.get_files_in_container(context, record_id, write_intent, query)
        return cast(list[AnyRemoteEntry], files), len(files)

    def _create_entry(
        self, entry_data: EntryData, context: FilesSourceRuntimeContext[RDMFileSourceConfiguration]
    ) -> Entry:
        public_name = self.get_public_name(context)
        record = self.repository.create_draft_file_container(entry_data.name, public_name, context)
        record_id = record.get("id")
        record_id = str(record_id) if record_id else None
        if not record_id:
            raise Exception("Failed to create record.")
        uri = self.repository.to_plugin_uri(record_id=record_id)
        name = record.get("title") or "Untitled"
        if not isinstance(name, str):
            raise Exception("Failed to get record title.")
        links = record.get("links")
        if not links or not isinstance(links, dict):
            raise Exception("Failed to get record links.")
        external_link = links.get("self_html")
        if not external_link or not isinstance(external_link, str):
            raise Exception("Failed to get record link.")
        return Entry(
            name=name,
            uri=uri,
            external_link=external_link,
        )

    def _realize_to(
        self, source_path: str, native_path: str, context: FilesSourceRuntimeContext[RDMFileSourceConfiguration]
    ):
        record_id, filename = self.parse_path(source_path)
        self.repository.download_file_from_container(record_id, filename, native_path, context)

    def _write_from(
        self, target_path: str, native_path: str, context: FilesSourceRuntimeContext[RDMFileSourceConfiguration]
    ):
        record_id, filename = self.parse_path(target_path)
        self.repository.upload_file_to_draft_container(record_id, filename, native_path, context)


class InvenioRepositoryInteractor(RDMRepositoryInteractor):
    """In Invenio a "Record" represents what we refer to as container in the rdm base class"""

    @property
    def records_url(self) -> str:
        return f"{self.repository_url}/api/records"

    @property
    def user_records_url(self) -> str:
        return f"{self.repository_url}/api/user/records"

    def to_plugin_uri(self, record_id: str, filename: Optional[str] = None) -> str:
        return f"{self.plugin.get_uri_root()}/{record_id}{f'/{filename}' if filename else ''}"

    def get_file_containers(
        self,
        context: FilesSourceRuntimeContext[RDMFileSourceConfiguration],
        write_intent: bool,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        query: Optional[str] = None,
        sort_by: Optional[str] = None,
    ) -> tuple[list[RemoteDirectory], int]:
        """Gets the records in the repository and returns the total count of records."""
        params: dict[str, Any] = {}
        request_url = self.records_url
        if self.plugin.get_authorization_token(context) or write_intent:
            # Authenticated users should browse only their own records.
            request_url = self.user_records_url
        if write_intent:
            # Only draft records owned by the user can be written to.
            params["is_published"] = "false"
        size, page = self._to_size_page(limit, offset)
        params["size"] = size
        params["page"] = page
        if query:
            params["q"] = query
            params["sort"] = "bestmatch"
        response_data = self._get_response(context, request_url, params=params)
        total_hits = response_data["hits"]["total"]
        return self._get_records_from_response(response_data), total_hits

    def _to_size_page(self, limit: Optional[int], offset: Optional[int]) -> tuple[Optional[int], Optional[int]]:
        if limit is None and offset is None:
            return None, None
        size = limit or DEFAULT_PAGE_LIMIT
        page = (offset or 0) // size + 1
        return size, page

    def get_files_in_container(
        self,
        context: FilesSourceRuntimeContext[RDMFileSourceConfiguration],
        container_id: str,
        writeable: bool,
        query: Optional[str] = None,
    ) -> list[RemoteFile]:
        conditionally_draft = "/draft" if writeable or self._is_draft_record(container_id, context) else ""
        request_url = f"{self.records_url}/{container_id}{conditionally_draft}/files"
        response_data = self._get_response(context, request_url)
        return self._get_record_files_from_response(container_id, response_data)

    def create_draft_file_container(
        self, title: str, public_name: str, context: FilesSourceRuntimeContext[RDMFileSourceConfiguration]
    ) -> dict[str, Any]:
        today = datetime.date.today().isoformat()
        creator = self._get_creator_from_public_name(public_name)
        resource_type_id = context.config.default_resource_type or "dataset"
        create_record_request = {
            "files": {"enabled": True},
            "metadata": {
                "title": title,
                "publication_date": today,
                "resource_type": {"id": resource_type_id},
                "creators": [
                    creator,
                ],
            },
        }

        headers = self._get_request_headers(context, auth_required=True)
        response = requests.post(self.records_url, json=create_record_request, headers=headers)
        self._ensure_response_has_expected_status_code(response, 201)
        record = response.json()
        record["title"] = self._get_record_title(record)
        return record

    def upload_file_to_draft_container(
        self,
        record_id: str,
        filename: str,
        file_path: str,
        context: FilesSourceRuntimeContext[RDMFileSourceConfiguration],
    ):
        file_size = os.path.getsize(file_path)

        threshold_mb = context.config.multipart_threshold
        # Convert threshold from MB to bytes (config value is always in MB)
        threshold_bytes = threshold_mb * 1024 * 1024 if threshold_mb else None
        use_multipart = file_size >= threshold_bytes if threshold_bytes else False
        if use_multipart:
            self._upload_file_multipart(record_id, filename, file_path, file_size, context)
        else:
            try:
                self._upload_file_single(record_id, filename, file_path, context)
            except InvenioRequestError as e:
                if e.status_code == 413:
                    raise Exception(
                        f"Failed to upload file '{filename}' ({file_size} bytes): HTTP 413 Payload Too Large. "
                        f"The server rejected the upload because the file is too large for a single request. "
                        f"Please configure 'multipart_threshold' in the file source configuration to enable multipart upload for files of this size."
                    ) from e
                raise

    def _upload_file_single(
        self,
        record_id: str,
        filename: str,
        file_path: str,
        context: FilesSourceRuntimeContext[RDMFileSourceConfiguration],
    ):
        """Upload a file using single PUT request."""

        record = self._get_draft_record(record_id, context)
        upload_file_url = record["links"]["files"]
        headers = self._get_request_headers(context, auth_required=True)

        # Add file metadata entry
        response = requests.post(upload_file_url, json=[{"key": filename}], headers=headers)
        self._ensure_response_has_expected_status_code(response, 201)

        # Upload file content
        entries = response.json()["entries"]
        file_entry = next(entry for entry in entries if entry["key"] == filename)
        upload_file_content_url = file_entry["links"]["content"]
        commit_file_upload_url = file_entry["links"]["commit"]
        with open(file_path, "rb") as file:
            response = requests.put(upload_file_content_url, data=file, headers=headers)
            self._ensure_response_has_expected_status_code(response, 200)

        # Commit file upload
        response = requests.post(commit_file_upload_url, headers=headers)
        self._ensure_response_has_expected_status_code(response, 200)

    def _upload_file_multipart(
        self,
        record_id: str,
        filename: str,
        file_path: str,
        file_size: int,
        context: FilesSourceRuntimeContext[RDMFileSourceConfiguration],
    ):
        """Upload a file using multipart upload.

        Flow:
        1. Calculate parts/part_size
        2. POST with transfer metadata
        3. Server returns links.parts[] with URL for each part
        4. Upload parts (parallel for > 2 parts)
        5. POST to commit URL
        """
        preferred_part_size_mb = context.config.multipart_chunk_size
        # Convert chunk size from MB to bytes (config value is always in MB)
        preferred_part_size = preferred_part_size_mb * 1024 * 1024 if preferred_part_size_mb else None
        num_parts, part_size = calculate_multipart_params(file_size, preferred_part_size)

        log.info(f"Multipart upload: {num_parts} parts of {part_size} bytes each for '{filename}'")

        record = self._get_draft_record(record_id, context)
        upload_file_url = record["links"]["files"]
        headers = self._get_request_headers(context, auth_required=True)

        file_metadata = {
            "key": filename,
            "size": file_size,
            "transfer": {
                "type": "M",
                "parts": num_parts,
                "part_size": part_size,
            },
        }
        response = requests.post(upload_file_url, json=[file_metadata], headers=headers)
        self._ensure_response_has_expected_status_code(response, 201)

        # Get part upload URLs from response
        entries = response.json()["entries"]
        file_entry = next(entry for entry in entries if entry["key"] == filename)
        commit_url = file_entry["links"]["commit"]
        part_links = file_entry.get("links", {}).get("parts", [])

        if len(part_links) != num_parts:
            raise Exception(
                f"Server returned {len(part_links)} part URLs but expected {num_parts} for file '{filename}'"
            )

        # Sort part links by part number to ensure correct ordering
        part_links = sorted(part_links, key=lambda p: p.get("part", 0))
        self._upload_parts(file_path, file_size, part_size, part_links, headers)
        response = requests.post(commit_url, json={}, headers=headers)
        self._ensure_response_has_expected_status_code(response, 200)
        log.info(f"Multipart upload completed for '{filename}'")

    def _upload_parts(
        self,
        file_path: str,
        file_size: int,
        part_size: int,
        part_links: list[dict],
        headers: dict,
    ):
        """Upload all parts in parallel using a thread pool."""
        num_parts = len(part_links)
        max_workers = min(4, num_parts)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            for part_index, part_info in enumerate(part_links):
                future = executor.submit(
                    self._upload_single_part,
                    file_path,
                    file_size,
                    part_size,
                    part_index,
                    part_info,
                    headers,
                )
                futures[future] = part_index

            for future in as_completed(futures):
                part_index = futures[future]
                try:
                    future.result()
                except Exception as e:
                    log.error(f"Failed to upload part {part_index}: {e}")
                    raise

    def _upload_single_part(
        self,
        file_path: str,
        file_size: int,
        part_size: int,
        part_index: int,
        part_info: dict,
        headers: dict,
    ):
        """Upload a single part of a multipart upload."""
        part_url = part_info.get("url")
        if not part_url:
            raise Exception(f"No URL provided for part {part_index}")

        start_byte = part_index * part_size
        end_byte = min(start_byte + part_size, file_size)
        part_content_length = end_byte - start_byte

        log.debug(f"Uploading part {part_index}: bytes {start_byte}-{end_byte - 1} ({part_content_length} bytes)")

        # Presigned S3 URLs are authenticated via query parameters; adding
        # Authorization or other headers would invalidate the signature.
        # Invenio API proxy URLs require the Authorization header.
        # Check for both X-Amz-Signature (current) and Signature (legacy v2) query params.
        is_presigned = "X-Amz-Signature" in part_url or "Signature=" in part_url
        part_headers = None if is_presigned else headers

        # Stream the file slice without loading the entire part into memory
        with open(file_path, "rb") as f:
            f.seek(start_byte)
            reader = _LimitedFileReader(f, part_content_length)
            response = requests.put(part_url, data=reader, headers=part_headers)
            self._ensure_response_has_expected_status_code(response, 200)

    def download_file_from_container(
        self,
        container_id: str,
        file_identifier: str,
        file_path: str,
        context: FilesSourceRuntimeContext[RDMFileSourceConfiguration],
    ):
        download_file_content_url = self._get_download_file_url(container_id, file_identifier, context)
        headers = {}
        if self._is_api_url(download_file_content_url):
            # pass the token as a header only when using the API
            headers = self._get_request_headers(context)
        try:
            with requests.get(
                download_file_content_url, headers=headers, stream=True, timeout=DEFAULT_SOCKET_TIMEOUT
            ) as response:
                response.raise_for_status()
                with open(file_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=2**20):
                        if chunk:
                            f.write(chunk)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code in [401, 403, 404]:
                raise Exception(
                    f"Cannot download file '{file_identifier}' from record '{container_id}'. Please make sure the record exists and you have access to it."
                )
            raise

    def _get_download_file_url(
        self, record_id: str, filename: str, context: FilesSourceRuntimeContext[RDMFileSourceConfiguration]
    ):
        """Get the URL to download a file from a record.

        This method is used to download files from both published and draft records that are accessible by the user.
        """
        file_details_url = self._get_file_details_url(record_id, filename)
        if self._is_published_record(record_id, context):
            # For restricted content, we need to use the regular API endpoint with credentials
            if self._is_record_content_restricted(record_id, context):
                return f"{file_details_url}/content"
            return self._file_url_to_download_url(file_details_url)
        if self._is_draft_record(record_id, context):
            draft_download_url = f"{self._to_draft_url(file_details_url)}/content"
            return draft_download_url
        raise MessageException(
            f"Cannot download file '{filename}' from record '{record_id}'. The record is not accessible or does not exist."
        )

    def _is_api_url(self, url: str) -> bool:
        return "/api/" in url

    def _to_draft_url(self, url: str) -> str:
        return url.replace("/files/", "/draft/files/")

    def _is_draft_record(self, record_id: str, context: FilesSourceRuntimeContext[RDMFileSourceConfiguration]):
        request_url = self._get_draft_record_url(record_id)
        headers = self._get_request_headers(context)
        response = requests.head(request_url, headers=headers)
        return response.status_code == 200

    def _is_published_record(self, record_id: str, context: FilesSourceRuntimeContext[RDMFileSourceConfiguration]):
        request_url = self._get_record_url(record_id)
        headers = self._get_request_headers(context)
        response = requests.head(request_url, headers=headers)
        return response.status_code == 200

    def _is_record_content_restricted(
        self, record_id: str, context: FilesSourceRuntimeContext[RDMFileSourceConfiguration]
    ):
        request_url = self._get_record_url(record_id)
        response_data = self._get_response(context, request_url)
        metadata = response_data.get("metadata", {})
        access_right = metadata.get("access_right", "public")
        return access_right == "restricted"

    def _get_record_url(self, record_id: str):
        return f"{self.records_url}/{record_id}"

    def _get_draft_record_url(self, record_id: str):
        return f"{self._get_record_url(record_id)}/draft"

    def _get_file_details_url(self, record_id: str, filename: str):
        return f"{self._get_record_url(record_id)}/files/{quote(filename)}"

    def _file_url_to_download_url(self, file_url: str) -> str:
        # Downloading through the API is only supported for local files and depends on how
        # the InvenioRDM instance file storage is configured.
        # So this is the most reliable way to download files for now.
        return f"{file_url.replace('/api', '')}?download=1"

    def _get_draft_record(self, record_id: str, context: FilesSourceRuntimeContext[RDMFileSourceConfiguration]):
        request_url = self._get_draft_record_url(record_id)
        draft_record = self._get_response(context, request_url)
        return draft_record

    def _get_records_from_response(self, response: dict) -> list[RemoteDirectory]:
        records = response["hits"]["hits"]
        rval: list[RemoteDirectory] = []
        for record in records:
            uri = self.to_plugin_uri(record_id=record["id"])
            path = self.plugin.to_relative_path(uri)
            name = self._get_record_title(record)
            rval.append(
                RemoteDirectory(
                    name=name,
                    uri=uri,
                    path=path,
                )
            )
        return rval

    def _get_record_title(self, record: InvenioRecord) -> str:
        title = record.get("title")
        if not title and "metadata" in record:
            title = record["metadata"].get("title")
        return title or "No title"

    def _get_record_files_from_response(self, record_id: str, response: dict) -> list[RemoteFile]:
        files_enabled = response.get("enabled", False)
        if not files_enabled:
            return []
        entries = response["entries"]
        rval: list[RemoteFile] = []
        for entry in entries:
            if entry.get("status") == "completed":
                uri = self.to_plugin_uri(record_id=record_id, filename=entry["key"])
                path = self.plugin.to_relative_path(uri)
                rval.append(
                    RemoteFile(
                        name=entry["key"],
                        size=entry["size"],
                        ctime=entry["created"],
                        uri=uri,
                        path=path,
                        hashes=self._get_file_hashes(entry),
                    )
                )
        return rval

    def _get_file_hashes(self, info: dict) -> Optional[list[RemoteFileHash]]:
        """Get optional file hashes provided by InvenioRDM for the RemoteFile entry."""
        # InvenioRDM may provide an optional "checksum" field with the file hash.
        checksum = info.get("checksum")
        if checksum and isinstance(checksum, str):
            # InvenioRDM's checksum field is a string in the format "<hash_function>:<hash_value>", e.g. "md5:1B2M2Y8AsgTpgAmY7PhCfg=="
            parts = checksum.split(":", 1)
            if len(parts) == 2:
                hash_function, hash_value = parts
                hash_function_name = as_hash_function_name(hash_function)
                if hash_function_name:
                    return [RemoteFileHash(hash_function=hash_function_name, hash_value=hash_value)]
        return None

    def _get_creator_from_public_name(self, public_name: Optional[str] = None) -> Creator:
        given_name = "Anonymous"
        family_name = "Galaxy User"
        if public_name:
            tokens = public_name.split(", ")
            if len(tokens) == 2:
                family_name = tokens[0]
                given_name = tokens[1]
            else:
                given_name = public_name
        return {
            "person_or_org": {
                "name": f"{given_name} {family_name}",
                "family_name": family_name,
                "given_name": given_name,
                "type": "personal",
                "identifiers": [],
            },
            "affiliations": [],
        }

    def _get_response(
        self,
        context: FilesSourceRuntimeContext[RDMFileSourceConfiguration],
        request_url: str,
        params: Optional[dict[str, Any]] = None,
        auth_required: bool = False,
    ) -> dict:
        headers = self._get_request_headers(context, auth_required)
        response = requests.get(request_url, params=params, headers=headers)
        self._ensure_response_has_expected_status_code(response, 200)
        return response.json()

    def _get_request_headers(
        self, context: FilesSourceRuntimeContext[RDMFileSourceConfiguration], auth_required: bool = False
    ):
        token = self.plugin.get_authorization_token(context)
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        if auth_required and token is None:
            self._raise_auth_required()
        return headers

    def _ensure_response_has_expected_status_code(self, response, expected_status_code: int):
        if response.status_code != expected_status_code:
            if response.status_code == 403:
                self._raise_auth_required()
            error_message = self._get_response_error_message(response)
            raise InvenioRequestError(
                f"Request to {response.url} failed with status code {response.status_code}: {error_message}",
                status_code=response.status_code,
            )

    def _raise_auth_required(self):
        raise AuthenticationRequired(
            f"Access denied. Please make sure you have provided a personal access token in your user's preferences for '{self.plugin.label}'"
        )

    def _get_response_error_message(self, response):
        try:
            response_json = response.json()
        except Exception:
            # Response is not JSON, return raw text or status info
            return response.text or f"HTTP {response.status_code} error"

        error_message = response_json.get("message") if response.status_code == 400 else response.text
        errors = response_json.get("errors", [])
        for error in errors:
            error_message += f"\n{json.dumps(error)}"
        return error_message


__all__ = ("InvenioRDMFilesSource",)
