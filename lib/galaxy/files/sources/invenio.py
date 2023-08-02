import datetime
import json
import ssl
import urllib.request
from typing import (
    List,
    Optional,
)
from urllib.parse import quote

import requests
from typing_extensions import (
    Literal,
    TypedDict,
)

from galaxy.files.sources import (
    Entry,
    EntryData,
    FilesSourceOptions,
    RemoteDirectory,
    RemoteFile,
)
from galaxy.files.sources._rdm import (
    OptionalUserContext,
    RDMFilesSource,
    RDMRepositoryInteractor,
)
from galaxy.util import (
    DEFAULT_SOCKET_TIMEOUT,
    get_charset_from_http_headers,
    stream_to_open_named_file,
)

# TODO: Remove this block. Ignoring SSL errors for testing purposes.
VERIFY = False
SSL_CONTEXT = ssl.create_default_context()
SSL_CONTEXT.check_hostname = False
SSL_CONTEXT.verify_mode = ssl.CERT_NONE


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
    """A files source for Invenio turn-key research data management repository."""

    plugin_type = "inveniordm"

    def get_repository_interactor(self, repository_url: str) -> RDMRepositoryInteractor:
        return InvenioRepositoryInteractor(repository_url, self)

    def _list(
        self,
        path="/",
        recursive=True,
        user_context: OptionalUserContext = None,
        opts: Optional[FilesSourceOptions] = None,
    ):
        writeable = opts and opts.writeable or False
        is_root_path = path == "/"
        if is_root_path:
            return self.repository.get_records(writeable, user_context)
        record_id, _ = self.parse_path(path)
        return self.repository.get_files_in_record(record_id, writeable, user_context)

    def _create_entry(
        self,
        entry_data: EntryData,
        user_context: OptionalUserContext = None,
        opts: Optional[FilesSourceOptions] = None,
    ) -> Entry:
        record = self.repository.create_draft_record(entry_data["name"], user_context=user_context)
        return {
            "uri": self.repository.to_plugin_uri(record["id"]),
            "name": record["metadata"]["title"],
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
        self.repository.download_file_from_record(record_id, filename, native_path, user_context=user_context)

    def _write_from(
        self,
        target_path: str,
        native_path: str,
        user_context: OptionalUserContext = None,
        opts: Optional[FilesSourceOptions] = None,
    ):
        record_id, filename = self.parse_path(target_path)
        self.repository.upload_file_to_draft_record(record_id, filename, native_path, user_context=user_context)


class InvenioRepositoryInteractor(RDMRepositoryInteractor):
    @property
    def records_url(self) -> str:
        return f"{self.repository_url}/api/records"

    def to_plugin_uri(self, record_id: str, filename: Optional[str] = None) -> str:
        return f"{self.plugin.get_uri_root()}/{record_id}{f'/{filename}' if filename else ''}"

    def get_records(self, writeable: bool, user_context: OptionalUserContext = None) -> List[RemoteDirectory]:
        # Only draft records owned by the user can be written to.
        request_url = f"{self.repository_url}/api/user/records?is_published=false" if writeable else self.records_url
        # TODO: This is limited to 25 records by default. Add pagination support?
        response_data = self._get_response(user_context, request_url)
        return self._get_records_from_response(response_data)

    def get_files_in_record(
        self, record_id: str, writeable: bool, user_context: OptionalUserContext = None
    ) -> List[RemoteFile]:
        conditionally_draft = "/draft" if writeable else ""
        request_url = f"{self.records_url}/{record_id}{conditionally_draft}/files"
        response_data = self._get_response(user_context, request_url)
        return self._get_record_files_from_response(record_id, response_data)

    def create_draft_record(self, title: str, user_context: OptionalUserContext = None) -> RemoteDirectory:
        today = datetime.date.today().isoformat()
        creator = self._get_creator_from_user_context(user_context)
        public = bool(self.get_user_preference_by_key("public_records", user_context))
        access = "public" if public else "restricted"
        create_record_request = {
            "access": {"record": access, "files": access},
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

        headers = self._get_request_headers(user_context)
        if "Authorization" not in headers:
            raise Exception(
                "Cannot create record without authentication token. Please set your personal access token in your Galaxy preferences."
            )

        response = requests.post(self.records_url, json=create_record_request, headers=headers, verify=VERIFY)
        self._ensure_response_has_expected_status_code(response, 201)
        record = response.json()
        return record

    def upload_file_to_draft_record(
        self,
        record_id: str,
        filename: str,
        file_path: str,
        user_context: OptionalUserContext = None,
    ):
        record = self._get_draft_record(record_id, user_context=user_context)
        upload_file_url = record["links"]["files"]
        headers = self._get_request_headers(user_context)

        # Add file metadata entry
        response = requests.post(upload_file_url, json=[{"key": filename}], headers=headers, verify=VERIFY)
        self._ensure_response_has_expected_status_code(response, 201)

        # Upload file content
        entries = response.json()["entries"]
        file_entry = next(entry for entry in entries if entry["key"] == filename)
        upload_file_content_url = file_entry["links"]["content"]
        commit_file_upload_url = file_entry["links"]["commit"]
        with open(file_path, "rb") as file:
            response = requests.put(upload_file_content_url, data=file, headers=headers, verify=VERIFY)
            self._ensure_response_has_expected_status_code(response, 200)

        # Commit file upload
        response = requests.post(commit_file_upload_url, headers=headers, verify=VERIFY)
        self._ensure_response_has_expected_status_code(response, 200)

    def download_file_from_record(
        self,
        record_id: str,
        filename: str,
        file_path: str,
        user_context: OptionalUserContext = None,
    ):
        download_file_content_url = f"{self.records_url}/{record_id}/files/{quote(filename)}/content"

        headers = self._get_request_headers(user_context)
        req = urllib.request.Request(download_file_content_url, headers=headers)
        with urllib.request.urlopen(req, timeout=DEFAULT_SOCKET_TIMEOUT, context=SSL_CONTEXT) as page:
            f = open(file_path, "wb")
            return stream_to_open_named_file(
                page, f.fileno(), file_path, source_encoding=get_charset_from_http_headers(page.headers)
            )

    def _get_draft_record(self, record_id: str, user_context: OptionalUserContext = None):
        request_url = f"{self.records_url}/{record_id}/draft"
        draft_record = self._get_response(user_context, request_url)
        return draft_record

    def _get_records_from_response(self, response: dict) -> List[RemoteDirectory]:
        records = response["hits"]["hits"]
        rval: List[RemoteDirectory] = []
        for record in records:
            uri = self.to_plugin_uri(record_id=record["id"])
            path = self.plugin.to_relative_path(uri)
            rval.append(
                {
                    "class": "Directory",
                    "name": record["metadata"]["title"],
                    "uri": uri,
                    "path": path,
                }
            )
        return rval

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

    def _get_creator_from_user_context(self, user_context: OptionalUserContext):
        public_name = self.get_user_preference_by_key("public_name", user_context)
        family_name = "Galaxy User"
        given_name = "Anonymous"
        if public_name:
            tokens = public_name.split(", ")
            if len(tokens) == 2:
                family_name = tokens[0]
                given_name = tokens[1]
            else:
                given_name = public_name
        return {"person_or_org": {"family_name": family_name, "given_name": given_name, "type": "personal"}}

    def get_user_preference_by_key(self, key: str, user_context: OptionalUserContext):
        preferences = user_context.preferences if user_context else None
        value = preferences.get(f"{self.plugin.id}|{key}", None) if preferences else None
        return value

    def _get_response(self, user_context: OptionalUserContext, request_url: str) -> dict:
        headers = self._get_request_headers(user_context)
        response = requests.get(request_url, headers=headers, verify=VERIFY)
        self._ensure_response_has_expected_status_code(response, 200)
        return response.json()

    def _get_request_headers(self, user_context: OptionalUserContext):
        token = self.plugin.get_authorization_token(user_context)
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        return headers

    def _ensure_response_has_expected_status_code(self, response, expected_status_code: int):
        if response.status_code != expected_status_code:
            error_message = self._get_response_error_message(response)
            raise Exception(
                f"Request to {response.url} failed with status code {response.status_code}: {error_message}"
            )

    def _get_response_error_message(self, response):
        response_json = response.json()
        error_message = response_json.get("message") if response.status_code == 400 else response.text
        errors = response_json.get("errors", [])
        for error in errors:
            error_message += f"\n{json.dumps(error)}"
        return error_message


__all__ = ("InvenioRDMFilesSource",)
