import datetime
import json
import os
import ssl
import urllib.request
from typing import (
    cast,
    List,
    Optional,
)
from urllib.parse import urljoin

import requests
from typing_extensions import (
    Literal,
    TypedDict,
    Unpack,
)

from galaxy.files.sources import (
    BaseFilesSource,
    FilesSourceOptions,
    FilesSourceProperties,
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


class InvenioFilesSourceProperties(FilesSourceProperties):
    url: str


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
    resource_type: ResourceType
    publication_date: str
    access: RecordAccess
    files: RecordFiles
    metadata: RecordMetadata
    links: RecordLinks


class InvenioFilesSource(BaseFilesSource):
    """A files source for Invenio turn-key research data management repository."""

    plugin_type = "inveniordm"

    def __init__(self, **kwd: Unpack[InvenioFilesSourceProperties]):
        props = self._parse_common_config_opts(kwd)
        base_url = props.get("url", None)
        if not base_url:
            raise Exception("InvenioFilesSource requires a url")
        self._invenio_url = base_url
        self._props = props

    def _list(self, path="/", recursive=True, user_context=None, opts: Optional[FilesSourceOptions] = None):
        is_root_path = path == "/"
        if is_root_path:
            return self._list_records(user_context)
        return self._list_record_files(path, user_context)

    def _realize_to(
        self, source_path: str, native_path: str, user_context=None, opts: Optional[FilesSourceOptions] = None
    ):
        # TODO: source_path will be wrong when constructed from the UI as it assumes the target_uri is `get_root_uri() + filename`

        remote_path = urljoin(self._invenio_url, source_path)
        # TODO: user_context is always None here when called from a data fetch.
        # This prevents downloading files that require authentication even if the user provided a token.
        headers = self._get_request_headers(user_context)
        req = urllib.request.Request(remote_path, headers=headers)
        with urllib.request.urlopen(req, timeout=DEFAULT_SOCKET_TIMEOUT, context=SSL_CONTEXT) as page:
            f = open(native_path, "wb")
            return stream_to_open_named_file(
                page, f.fileno(), native_path, source_encoding=get_charset_from_http_headers(page.headers)
            )

    def _write_from(
        self, target_path: str, native_path: str, user_context=None, opts: Optional[FilesSourceOptions] = None
    ):
        filename = os.path.basename(target_path)
        record_title = f"{filename} (exported by Galaxy)"
        draft_record = self._create_draft_record(title=record_title, user_context=user_context)
        try:
            self._upload_file_to_draft_record(draft_record, filename, native_path, user_context=user_context)
            self._publish_draft_record(draft_record, user_context=user_context)
        except Exception:
            self._delete_draft_record(draft_record, user_context)
            raise

    def _list_records(self, user_context=None):
        # TODO: This is limited to 25 records by default. Add pagination support?
        request_url = urljoin(self._invenio_url, "api/records")
        response_data = self._get_response(user_context, request_url)
        return self._get_records_from_response(response_data)

    def _list_record_files(self, path, user_context=None):
        request_url = urljoin(self._invenio_url, f"{path}/files")
        response_data = self._get_response(user_context, request_url)
        return self._get_record_files_from_response(path, response_data)

    def _get_response(self, user_context, request_url: str) -> dict:
        headers = self._get_request_headers(user_context)
        response = requests.get(request_url, headers=headers, verify=VERIFY)
        self._ensure_response_has_expected_status_code(response, 200)
        return response.json()

    def _get_request_headers(self, user_context):
        preferences = user_context.preferences if user_context else None
        token = preferences.get(f"{self.id}|token", None) if preferences else None
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        return headers

    def _get_records_from_response(self, response: dict):
        records = response["hits"]["hits"]
        rval = []
        for record in records:
            uri = self._to_plugin_uri(record["links"]["self"])
            rval.append(
                {
                    "class": "Directory",
                    "name": record["metadata"]["title"],
                    "ctime": record["created"],
                    "uri": uri,
                    "path": f"/{record['id']}",
                }
            )

        return rval

    def _get_record_files_from_response(self, path: str, response: dict):
        files_enabled = response.get("enabled", False)
        if not files_enabled:
            return []
        entries = response["entries"]
        rval = []
        for entry in entries:
            if entry.get("status") == "completed":
                uri = self._to_plugin_uri(entry["links"]["content"])
                path = self._to_plugin_uri(entry["links"]["self"])
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

    def _to_plugin_uri(self, uri: str) -> str:
        return uri.replace(self._invenio_url, self.get_uri_root())

    def _serialization_props(self, user_context=None) -> InvenioFilesSourceProperties:
        effective_props = {}
        for key, val in self._props.items():
            effective_props[key] = self._evaluate_prop(val, user_context=user_context)
        effective_props["url"] = self._invenio_url
        return cast(InvenioFilesSourceProperties, effective_props)

    def _create_draft_record(self, title: str, user_context=None) -> InvenioRecord:
        today = datetime.date.today().isoformat()
        creator = self._get_creator_from_user_context(user_context)
        should_publish = self._get_public_records_user_setting_enabled_status(user_context)
        access = "public" if should_publish else "restricted"
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

        create_record_url = urljoin(self._invenio_url, "api/records")
        response = requests.post(create_record_url, json=create_record_request, headers=headers, verify=VERIFY)
        self._ensure_response_has_expected_status_code(response, 201)
        record = response.json()
        return record

    def _delete_draft_record(self, record: InvenioRecord, user_context=None):
        delete_record_url = record["links"]["self"]
        headers = self._get_request_headers(user_context)
        response = requests.delete(delete_record_url, headers=headers, verify=VERIFY)
        self._ensure_response_has_expected_status_code(response, 204)

    def _upload_file_to_draft_record(self, record: InvenioRecord, filename: str, native_path: str, user_context=None):
        upload_file_url = urljoin(self._invenio_url, f"api/records/{record['id']}/draft/files")
        headers = self._get_request_headers(user_context)

        # Add file metadata
        response = requests.post(upload_file_url, json=[{"key": filename}], headers=headers, verify=VERIFY)
        self._ensure_response_has_expected_status_code(response, 201)

        # Upload file content
        file_entry = response.json()["entries"][0]
        upload_file_content_url = file_entry["links"]["content"]
        commit_file_upload_url = file_entry["links"]["commit"]
        with open(native_path, "rb") as file:
            response = requests.put(upload_file_content_url, data=file, headers=headers, verify=VERIFY)
            self._ensure_response_has_expected_status_code(response, 200)

        # Commit file upload
        response = requests.post(commit_file_upload_url, headers=headers, verify=VERIFY)
        self._ensure_response_has_expected_status_code(response, 200)

    def _publish_draft_record(self, record: InvenioRecord, user_context=None):
        publish_record_url = urljoin(self._invenio_url, f"api/records/{record['id']}/draft/actions/publish")
        headers = self._get_request_headers(user_context)
        response = requests.post(publish_record_url, headers=headers, verify=VERIFY)
        self._ensure_response_has_expected_status_code(response, 202)

    def _get_creator_from_user_context(self, user_context):
        preferences = user_context.preferences if user_context else None
        public_name = preferences.get(f"{self.id}|public_name", None) if preferences else None
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

    def _get_public_records_user_setting_enabled_status(self, user_context) -> bool:
        preferences = user_context.preferences if user_context else None
        public_records = preferences.get(f"{self.id}|public_records", None) if preferences else None
        if public_records:
            return True
        return False

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


__all__ = ("InvenioFilesSource",)
