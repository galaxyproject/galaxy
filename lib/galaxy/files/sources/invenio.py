import datetime
import json
import re
import urllib.request
from typing import (
    Any,
    cast,
    Dict,
    List,
    Optional,
    Tuple,
)
from urllib.parse import quote

from typing_extensions import (
    Literal,
    TypedDict,
    Unpack,
)

from galaxy.exceptions import AuthenticationRequired
from galaxy.files import OptionalUserContext
from galaxy.files.sources import (
    AnyRemoteEntry,
    DEFAULT_PAGE_LIMIT,
    DEFAULT_SCHEME,
    Entry,
    EntryData,
    FilesSourceOptions,
    RemoteDirectory,
    RemoteFile,
)
from galaxy.files.sources._rdm import (
    ContainerAndFileIdentifier,
    RDMFilesSource,
    RDMFilesSourceProperties,
    RDMRepositoryInteractor,
)
from galaxy.util import (
    DEFAULT_SOCKET_TIMEOUT,
    get_charset_from_http_headers,
    requests,
    stream_to_open_named_file,
)

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
    identifiers: List[IdentifierEntry]


class Creator(TypedDict):
    person_or_org: RecordPersonOrOrg
    affiliations: Optional[List[AffiliationEntry]]


class RecordMetadata(TypedDict):
    title: str
    resource_type: ResourceType
    publication_date: str
    creators: List[Creator]


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

    def __init__(self, **kwd: Unpack[RDMFilesSourceProperties]):
        super().__init__(**kwd)
        self._scheme_regex = re.compile(rf"^{self.get_scheme()}?://{self.id}|^{DEFAULT_SCHEME}://{self.id}")
        self.repository: InvenioRepositoryInteractor

    def get_scheme(self) -> str:
        return "invenio"

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
        path="/",
        recursive=True,
        user_context: OptionalUserContext = None,
        opts: Optional[FilesSourceOptions] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        query: Optional[str] = None,
        sort_by: Optional[str] = None,
    ) -> Tuple[List[AnyRemoteEntry], int]:
        writeable = opts and opts.writeable or False
        is_root_path = path == "/"
        if is_root_path:
            records, total_hits = self.repository.get_file_containers(
                writeable, user_context, limit=limit, offset=offset, query=query
            )
            return cast(List[AnyRemoteEntry], records), total_hits
        record_id = self.get_container_id_from_path(path)
        files = self.repository.get_files_in_container(record_id, writeable, user_context)
        return cast(List[AnyRemoteEntry], files), len(files)

    def _create_entry(
        self,
        entry_data: EntryData,
        user_context: OptionalUserContext = None,
        opts: Optional[FilesSourceOptions] = None,
    ) -> Entry:
        public_name = self.get_public_name(user_context)
        record = self.repository.create_draft_file_container(entry_data["name"], public_name, user_context=user_context)
        return {
            "uri": self.repository.to_plugin_uri(record["id"]),
            "name": record["title"],
            "external_link": record["links"]["self_html"],
        }

    def _realize_to(
        self,
        source_path: str,
        native_path: str,
        user_context: OptionalUserContext = None,
        opts: Optional[FilesSourceOptions] = None,
    ):
        # TODO: user_context is always None here when called from a data fetch.
        # This prevents downloading files that require authentication even if the user provided a token.
        record_id, filename = self.parse_path(source_path)
        self.repository.download_file_from_container(record_id, filename, native_path, user_context=user_context)

    def _write_from(
        self,
        target_path: str,
        native_path: str,
        user_context: OptionalUserContext = None,
        opts: Optional[FilesSourceOptions] = None,
    ):
        record_id, filename = self.parse_path(target_path)
        self.repository.upload_file_to_draft_container(record_id, filename, native_path, user_context=user_context)


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
        writeable: bool,
        user_context: OptionalUserContext = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        query: Optional[str] = None,
        sort_by: Optional[str] = None,
    ) -> Tuple[List[RemoteDirectory], int]:
        """Gets the records in the repository and returns the total count of records."""
        params: Dict[str, Any] = {}
        request_url = self.records_url
        if writeable:
            # Only draft records owned by the user can be written to.
            params["is_published"] = "false"
            request_url = self.user_records_url
        size, page = self._to_size_page(limit, offset)
        params["size"] = size
        params["page"] = page
        if query:
            params["q"] = query
            params["sort"] = "bestmatch"
        response_data = self._get_response(user_context, request_url, params=params)
        total_hits = response_data["hits"]["total"]
        return self._get_records_from_response(response_data), total_hits

    def _to_size_page(self, limit: Optional[int], offset: Optional[int]) -> Tuple[Optional[int], Optional[int]]:
        if limit is None and offset is None:
            return None, None
        size = limit or DEFAULT_PAGE_LIMIT
        page = (offset or 0) // size + 1
        return size, page

    def get_files_in_container(
        self, container_id: str, writeable: bool, user_context: OptionalUserContext = None, query: Optional[str] = None,
    ) -> List[RemoteFile]:
        conditionally_draft = "/draft" if writeable else ""
        request_url = f"{self.records_url}/{container_id}{conditionally_draft}/files"
        response_data = self._get_response(user_context, request_url)
        return self._get_record_files_from_response(container_id, response_data)

    def create_draft_file_container(
        self, title: str, public_name: Optional[str] = None, user_context: OptionalUserContext = None
    ) -> RemoteDirectory:
        today = datetime.date.today().isoformat()
        creator = self._get_creator_from_public_name(public_name)
        create_record_request = {
            "files": {"enabled": True},
            "metadata": {
                "title": title,
                "publication_date": today,
                "resource_type": {"id": "dataset"},
                "creators": [
                    creator,
                ],
            },
        }

        headers = self._get_request_headers(user_context, auth_required=True)
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
        user_context: OptionalUserContext = None,
    ):
        record = self._get_draft_record(record_id, user_context=user_context)
        upload_file_url = record["links"]["files"]
        headers = self._get_request_headers(user_context, auth_required=True)

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

    def download_file_from_container(
        self,
        container_id: str,
        file_identifier: str,
        file_path: str,
        user_context: OptionalUserContext = None,
    ):
        download_file_content_url = self._get_download_file_url(container_id, file_identifier, user_context)
        headers = {}
        if self._is_api_url(download_file_content_url):
            # pass the token as a header only when using the API
            headers = self._get_request_headers(user_context)
        try:
            req = urllib.request.Request(download_file_content_url, headers=headers)
            with urllib.request.urlopen(req, timeout=DEFAULT_SOCKET_TIMEOUT) as page:
                f = open(file_path, "wb")
                return stream_to_open_named_file(
                    page, f.fileno(), file_path, source_encoding=get_charset_from_http_headers(page.headers)
                )
        except urllib.error.HTTPError as e:
            # TODO: We can only download files from published records for now
            if e.code in [401, 403, 404]:
                raise Exception(
                    f"Cannot download file '{file_identifier}' from record '{container_id}'. Please make sure the record exists and it is public."
                )

    def _get_download_file_url(self, record_id: str, filename: str, user_context: OptionalUserContext = None):
        """Get the URL to download a file from a record.

        This method is used to download files from both published and draft records that are accessible by the user.
        """
        is_draft_record = self._is_draft_record(record_id, user_context)
        file_details_url = f"{self.records_url}/{record_id}/files/{quote(filename)}"
        download_file_content_url = f"{file_details_url}/content"
        if is_draft_record:
            file_details_url = self._to_draft_url(file_details_url)
            download_file_content_url = self._to_draft_url(download_file_content_url)
        file_details = self._get_response(user_context, file_details_url)
        if not self._can_download_from_api(file_details):
            # TODO: This is a temporary workaround for the fact that the "content" API
            # does not support downloading files from S3 or other remote storage classes.
            # More info: https://inveniordm.docs.cern.ch/reference/file_storage/#remote-files-r
            download_file_content_url = f"{file_details_url.replace('/api', '')}?download=1"
        return download_file_content_url

    def _is_api_url(self, url: str) -> bool:
        return "/api/" in url

    def _to_draft_url(self, url: str) -> str:
        return url.replace("/files/", "/draft/files/")

    def _can_download_from_api(self, file_details: dict) -> bool:
        # Only files stored locally seems to be fully supported by the API for now
        # More info: https://inveniordm.docs.cern.ch/reference/file_storage/
        return file_details["storage_class"] == "L"

    def _is_draft_record(self, record_id: str, user_context: OptionalUserContext = None):
        request_url = self._get_draft_record_url(record_id)
        headers = self._get_request_headers(user_context)
        response = requests.get(request_url, headers=headers)
        return response.status_code == 200

    def _get_draft_record_url(self, record_id: str):
        return f"{self.records_url}/{record_id}/draft"

    def _get_draft_record(self, record_id: str, user_context: OptionalUserContext = None):
        request_url = self._get_draft_record_url(record_id)
        draft_record = self._get_response(user_context, request_url)
        return draft_record

    def _get_records_from_response(self, response: dict) -> List[RemoteDirectory]:
        records = response["hits"]["hits"]
        rval: List[RemoteDirectory] = []
        for record in records:
            uri = self.to_plugin_uri(record_id=record["id"])
            path = self.plugin.to_relative_path(uri)
            name = self._get_record_title(record)
            rval.append(
                {
                    "class": "Directory",
                    "name": name,
                    "uri": uri,
                    "path": path,
                }
            )
        return rval

    def _get_record_title(self, record: InvenioRecord) -> str:
        title = record.get("title")
        if not title and "metadata" in record:
            title = record["metadata"].get("title")
        return title or "No title"

    def _get_record_files_from_response(self, record_id: str, response: dict) -> List[RemoteFile]:
        files_enabled = response.get("enabled", False)
        if not files_enabled:
            return []
        entries = response["entries"]
        rval: List[RemoteFile] = []
        for entry in entries:
            if entry.get("status") == "completed":
                uri = self.to_plugin_uri(record_id=record_id, filename=entry["key"])
                path = self.plugin.to_relative_path(uri)
                rval.append(
                    {
                        "class": "File",
                        "name": entry["key"],
                        "size": entry["size"],
                        "ctime": entry["created"],
                        "uri": uri,
                        "path": path,
                    }
                )
        return rval

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
        user_context: OptionalUserContext,
        request_url: str,
        params: Optional[Dict[str, Any]] = None,
        auth_required: bool = False,
    ) -> dict:
        headers = self._get_request_headers(user_context, auth_required)
        response = requests.get(request_url, params=params, headers=headers)
        self._ensure_response_has_expected_status_code(response, 200)
        return response.json()

    def _get_request_headers(self, user_context: OptionalUserContext, auth_required: bool = False):
        token = self.plugin.get_authorization_token(user_context)
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        if auth_required and token is None:
            self._raise_auth_required()
        return headers

    def _ensure_response_has_expected_status_code(self, response, expected_status_code: int):
        if response.status_code != expected_status_code:
            if response.status_code == 403:
                self._raise_auth_required()
            error_message = self._get_response_error_message(response)
            raise Exception(
                f"Request to {response.url} failed with status code {response.status_code}: {error_message}"
            )

    def _raise_auth_required(self):
        raise AuthenticationRequired(
            f"Please provide a personal access token in your user's preferences for '{self.plugin.label}'"
        )

    def _get_response_error_message(self, response):
        response_json = response.json()
        error_message = response_json.get("message") if response.status_code == 400 else response.text
        errors = response_json.get("errors", [])
        for error in errors:
            error_message += f"\n{json.dumps(error)}"
        return error_message


__all__ = ("InvenioRDMFilesSource",)
