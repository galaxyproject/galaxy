import datetime
import json
import os
import ssl
import urllib.request
from typing import (
    List,
    Optional,
)
from urllib.parse import urljoin

import requests
from typing_extensions import (
    Literal,
    TypedDict,
)

from galaxy.files import ProvidesUserFileSourcesUserContext
from galaxy.files.sources import (
    Entry,
    EntryData,
    FilesSourceOptions,
)
from galaxy.files.sources._rdm import RDMFilesSource
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

    def _list(
        self,
        path="/",
        recursive=True,
        user_context: Optional[ProvidesUserFileSourcesUserContext] = None,
        opts: Optional[FilesSourceOptions] = None,
    ):
        write_intent = opts and opts.write_intent or False
        is_root_path = path == "/"
        if is_root_path:
            return self._list_records(write_intent, user_context)
        return self._list_record_files(path, write_intent, user_context)

    def _create_entry(
        self,
        entry_data: EntryData,
        user_context: Optional[ProvidesUserFileSourcesUserContext] = None,
        opts: Optional[FilesSourceOptions] = None,
    ) -> Entry:
        record = self._create_draft_record(entry_data["name"], user_context=user_context)
        return {
            "uri": self._to_plugin_uri(record["links"]["record"]),
            "name": record["metadata"]["title"],
            "external_link": record["links"]["self_html"],
        }

    def _realize_to(
        self,
        source_path: str,
        native_path: str,
        user_context: Optional[ProvidesUserFileSourcesUserContext] = None,
        opts: Optional[FilesSourceOptions] = None,
    ):
        # source_path = '/api/records/pxpnk-7c133/Tester.rocrate.zip'
        remote_path = urljoin(self.repository_url, source_path)
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
        self,
        target_path: str,
        native_path: str,
        user_context: Optional[ProvidesUserFileSourcesUserContext] = None,
        opts: Optional[FilesSourceOptions] = None,
    ):
        filename = os.path.basename(target_path)
        dirname = os.path.dirname(target_path)
        record_id = dirname.replace("/api/records/", "")
        use_existing_record = len(record_id) > 5

        # TODO: if we create the record here, then the target_path of the export will not have the record id and it will not be possible to import it back.
        # We need to create the record before the export and then use the record id in the target_path.

        if use_existing_record:
            draft_record = self._get_draft_record(record_id, user_context=user_context)
        else:
            record_title = f"{filename} (exported by Galaxy)"
            draft_record = self._create_draft_record(title=record_title, user_context=user_context)
        try:
            self._upload_file_to_draft_record(draft_record, filename, native_path, user_context=user_context)
            self._publish_draft_record(draft_record, user_context=user_context)
        except Exception:
            if not use_existing_record:
                self._delete_draft_record(draft_record, user_context)
            raise

    def _list_records(self, write_intent: bool, user_context: Optional[ProvidesUserFileSourcesUserContext] = None):
        if write_intent:
            return self._list_writeable_records(user_context)
        return self._list_all_records(user_context)

    def _list_all_records(self, user_context: Optional[ProvidesUserFileSourcesUserContext] = None):
        # TODO: This is limited to 25 records by default. Add pagination support?
        request_url = urljoin(self.repository_url, "api/records")
        response_data = self._get_response(user_context, request_url)
        return self._get_records_from_response(response_data)

    def _list_writeable_records(self, user_context: Optional[ProvidesUserFileSourcesUserContext] = None):
        # TODO: This is limited to 25 records by default. Add pagination support?
        # Only draft records can be written to.
        request_url = urljoin(self.repository_url, "api/user/records?is_published=false")
        response_data = self._get_response(user_context, request_url)
        return self._get_records_from_response(response_data)

    def _list_record_files(
        self, path: str, write_intent: bool, user_context: Optional[ProvidesUserFileSourcesUserContext] = None
    ):
        request_url = urljoin(self.repository_url, f"{path}{'/draft' if write_intent else '' }/files")
        response_data = self._get_response(user_context, request_url)
        return self._get_record_files_from_response(path, response_data)

    def _get_response(self, user_context: Optional[ProvidesUserFileSourcesUserContext], request_url: str) -> dict:
        headers = self._get_request_headers(user_context)
        response = requests.get(request_url, headers=headers, verify=VERIFY)
        self._ensure_response_has_expected_status_code(response, 200)
        return response.json()

    def _get_request_headers(self, user_context: Optional[ProvidesUserFileSourcesUserContext]):
        vault = user_context.user_vault if user_context else None
        token = vault.read_secret(f"preferences/{self.id}/token") if vault else None
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        return headers

    def _get_records_from_response(self, response: dict):
        records = response["hits"]["hits"]
        return self._get_records_as_directories(records)

    def _get_records_as_directories(self, records):
        rval = []
        for record in records:
            uri = self._to_plugin_uri(record["links"]["self"])
            # TODO: define model for Directory and File
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
        return uri.replace(self.repository_url, self.get_uri_root())

    def _get_draft_record(self, record_id: str, user_context: Optional[ProvidesUserFileSourcesUserContext] = None):
        request_url = urljoin(self.repository_url, f"api/records/{record_id}/draft")
        draft_record = self._get_response(user_context, request_url)
        return draft_record

    def _create_draft_record(
        self, title: str, user_context: Optional[ProvidesUserFileSourcesUserContext] = None
    ) -> InvenioRecord:
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

        create_record_url = urljoin(self.repository_url, "api/records")
        response = requests.post(create_record_url, json=create_record_request, headers=headers, verify=VERIFY)
        self._ensure_response_has_expected_status_code(response, 201)
        record = response.json()
        return record

    def _delete_draft_record(
        self, record: InvenioRecord, user_context: Optional[ProvidesUserFileSourcesUserContext] = None
    ):
        delete_record_url = record["links"]["self"]
        headers = self._get_request_headers(user_context)
        response = requests.delete(delete_record_url, headers=headers, verify=VERIFY)
        self._ensure_response_has_expected_status_code(response, 204)

    def _upload_file_to_draft_record(
        self,
        record: InvenioRecord,
        filename: str,
        native_path: str,
        user_context: Optional[ProvidesUserFileSourcesUserContext] = None,
    ):
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
        with open(native_path, "rb") as file:
            response = requests.put(upload_file_content_url, data=file, headers=headers, verify=VERIFY)
            self._ensure_response_has_expected_status_code(response, 200)

        # Commit file upload
        response = requests.post(commit_file_upload_url, headers=headers, verify=VERIFY)
        self._ensure_response_has_expected_status_code(response, 200)

    def _publish_draft_record(
        self, record: InvenioRecord, user_context: Optional[ProvidesUserFileSourcesUserContext] = None
    ):
        publish_record_url = urljoin(self.repository_url, f"api/records/{record['id']}/draft/actions/publish")
        headers = self._get_request_headers(user_context)
        response = requests.post(publish_record_url, headers=headers, verify=VERIFY)
        self._ensure_response_has_expected_status_code(response, 202)

    def _get_creator_from_user_context(self, user_context: Optional[ProvidesUserFileSourcesUserContext]):
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

    def _get_public_records_user_setting_enabled_status(
        self, user_context: Optional[ProvidesUserFileSourcesUserContext]
    ) -> bool:
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


__all__ = ("InvenioRDMFilesSource",)
