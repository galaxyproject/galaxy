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


class NotFoundException(Exception):
    def __init__(self, message):
        super().__init__(message)


class DataverseDataset(TypedDict):
    name: str
    type: str
    url: str
    global_id: str
    description: str
    published_at: str
    storageIdentifier: str
    fileCount: int
    versionState: str
    createdAt: str
    updatedAt: str
    publication_date: str


class DataverseRDMFilesSource(RDMFilesSource):
    """A files source for Dataverse turn-key research data management repository.

    In Dataverse a "dataset" represents what we refer to as container in the rdm base class
    """

    plugin_type = "dataverse"
    supports_pagination = True
    supports_search = True

    def __init__(self, **kwd: Unpack[RDMFilesSourceProperties]):
        super().__init__(**kwd)
        self._scheme_regex = re.compile(rf"^{self.get_scheme()}?://{self.id}|^{DEFAULT_SCHEME}://{self.id}")
        self.repository: DataverseRepositoryInteractor

    def get_scheme(self) -> str:
        return "dataverse"

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
        return DataverseRepositoryInteractor(repository_url, self)

    def parse_path(self, source_path: str, container_id_only: bool = False) -> ContainerAndFileIdentifier:
        """Parses the given source path and returns the dataset_id and/or the file_id.

        The source path must either have the format '/<dataset_id>' or '/<file_id>' where <dataset_id> is a subset of <file_id>.
        If dataset_id_only is True, the source path must have the format '/<dataset_id>' and an empty file_id will be returned.

        Example dataset_id:
        doi:10.70122/FK2/DIG2DG

        Example file_id:
        doi:10.70122/FK2/DIG2DG/AVNCLL
        """
        if not source_path.startswith("/"):
            raise ValueError(f"Invalid source path: '{source_path}'. Must start with '/'.")

        parts = source_path[1:].split("/", 3)
        dataset_id = "/".join(parts[:3])

        if container_id_only:
            if len(parts) != 3:
                raise ValueError(f"Invalid source path: '{source_path}'. Expected format: '/<dataset_id>'.")
            return ContainerAndFileIdentifier(container_id=dataset_id, file_identifier="")

        if len(parts) != 4:
            raise ValueError(f"Invalid source path: '{source_path}'. Expected format: '/<file_id>'.")

        file_id = dataset_id + "/" + parts[3]
        return ContainerAndFileIdentifier(container_id=dataset_id, file_identifier=file_id)

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
        """This method lists the datasets or files from dataverse."""
        writeable = opts and opts.writeable or False
        is_root_path = path == "/"
        if is_root_path:
            datasets, total_hits = self.repository.get_file_containers(
                writeable, user_context, limit=limit, offset=offset, query=query
            )
            return cast(List[AnyRemoteEntry], datasets), total_hits
        dataset_id = self.get_container_id_from_path(path)
        files = self.repository.get_files_in_container(dataset_id, writeable, user_context, query)
        return cast(List[AnyRemoteEntry], files), len(files)

    def _create_entry(
        self,
        entry_data: EntryData,
        user_context: OptionalUserContext = None,
        opts: Optional[FilesSourceOptions] = None,
    ) -> Entry:
        """Creates a draft dataset in the repository."""
        public_name = self.get_public_name(user_context) or "Anonymous Galaxy User"
        title = entry_data.get("name") or "No title"
        dataset = self.repository.create_draft_file_container(title, public_name, user_context)
        datasetId = str(dataset.get("persistentId"))
        return {
            "uri": self.repository.to_plugin_uri(datasetId),
            "name": title,
            "external_link": self.repository.public_dataset_url(datasetId),
        }

    def _realize_to(
        self,
        source_path: str,
        native_path: str,
        user_context: OptionalUserContext = None,
        opts: Optional[FilesSourceOptions] = None,
    ):
        """Used when downloading files from dataverse."""
        # TODO: user_context is always None here when called from a data fetch. (same problem as in invenio.py)
        # This prevents downloading files that require authentication even if the user provided a token.

        dataset_id, file_id = self.parse_path(source_path)
        try:
            self.repository.download_file_from_container(dataset_id, file_id, native_path, user_context=user_context)
        except NotFoundException:
            filename = file_id.split("/")[-1]
            is_zip_file = self._is_zip_archive(filename)
            if is_zip_file:
                # Workaround explanation:
                # When we archive our history to dataverse, the zip sent from Galaxy to dataverse is extracted automatically.
                # Only the contents are stored, not the zip itself.
                # So, if a zip is not found, we suppose we are trying to reimport an archived history
                # and make an API call to Dataverse to download the dataset as a zip.
                self.repository._download_dataset_as_zip(dataset_id, native_path, user_context)

    def _is_zip_archive(self, file_name: str) -> bool:
        return file_name.endswith(".zip")

    def _write_from(
        self,
        target_path: str,
        native_path: str,
        user_context: OptionalUserContext = None,
        opts: Optional[FilesSourceOptions] = None,
    ):
        """Used when uploading files to dataverse."""
        dataset_id, file_id = self.parse_path(target_path)
        self.repository.upload_file_to_draft_container(dataset_id, file_id, native_path, user_context=user_context)


class DataverseRepositoryInteractor(RDMRepositoryInteractor):
    """In Dataverse a "Dataset" represents what we refer to as container in the rdm base class"""

    @property
    def api_base_url(self) -> str:
        return f"{self.repository_url}/api/v1"

    @property
    def search_url(self) -> str:
        return f"{self.api_base_url}/search"

    def file_access_url(self, file_id: str) -> str:
        encoded_file_id = quote(file_id, safe="")
        return f"{self.api_base_url}/access/datafile/:persistentId?persistentId={encoded_file_id}"

    def download_dataset_as_zip_url(self, dataset_id: str) -> str:
        return f"{self.api_base_url}/access/dataset/:persistentId/?persistentId={dataset_id}"

    def files_of_dataset_url(self, dataset_id: str, dataset_version: str = ":latest") -> str:
        return f"{self.api_base_url}/datasets/:persistentId/versions/{dataset_version}/files?persistentId={dataset_id}"

    def add_files_to_dataset_url(self, dataset_id: str) -> str:
        return f"{self.api_base_url}/datasets/:persistentId/add?persistentId={dataset_id}"

    def create_collection_url(self, parent_alias: str) -> str:
        return f"{self.api_base_url}/dataverses/{parent_alias}"

    def create_dataset_url(self, parent_alias: str) -> str:
        return f"{self.api_base_url}/dataverses/{parent_alias}/datasets"

    def public_dataset_url(self, dataset_id: str) -> str:
        return f"{self.repository_url}/dataset.xhtml?persistentId={dataset_id}"

    def to_plugin_uri(self, dataset_id: str, file_identifier: Optional[str] = None) -> str:
        return f"{self.plugin.get_uri_root()}/{f'{file_identifier}' if file_identifier else f'{dataset_id}'}"

    def _is_api_url(self, url: str) -> bool:
        return "/api/" in url

    def get_file_containers(
        self,
        writeable: bool,
        user_context: OptionalUserContext = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        query: Optional[str] = None,
        sort_by: Optional[str] = None,
    ) -> Tuple[List[RemoteDirectory], int]:
        """Lists the Dataverse datasets in the repository."""
        request_url = self.search_url
        params = {
            "type": "dataset",
            "per_page": limit or DEFAULT_PAGE_LIMIT,
            "start": offset,
            "q": f"title:{query}" if query else "*",
            "sort": sort_by or "date",
        }
        if writeable:
            params["fq"] = "publicationStatus:Draft"
        response_data = self._get_response(user_context, request_url, params)
        total_hits = response_data["data"]["total_count"]
        return self._get_datasets_from_response(response_data["data"]), total_hits

    def get_files_in_container(
        self,
        container_id: str,
        writeable: bool,
        user_context: OptionalUserContext = None,
        query: Optional[str] = None,
    ) -> List[RemoteFile]:
        """This method lists the files in a dataverse dataset."""
        request_url = self.files_of_dataset_url(dataset_id=container_id)
        response_data = self._get_response(user_context, request_url)
        files = self._get_files_from_response(container_id, response_data["data"])
        files = self._filter_files_by_name(files, query)
        return files

    def _filter_files_by_name(self, files: List[RemoteFile], query: Optional[str] = None) -> List[RemoteFile]:
        if not query:
            return files
        return [file for file in files if query in file["name"]]

    def create_draft_file_container(
        self, title: str, public_name: str, user_context: OptionalUserContext = None
    ) -> RemoteDirectory:
        """Creates a draft dataset in the repository. Dataverse datasets are contained in collections. Collections can be contained in collections.
        We create a collection inside the root collection and then a dataset inside that collection.
        """
        # Prepare and create the collection
        collection_payload = self._prepare_collection_data(title, public_name, user_context)
        collection = self._create_collection(":root", collection_payload, user_context)
        if not collection or "data" not in collection or "alias" not in collection["data"]:
            raise Exception("Could not create collection in Dataverse or response has an unexpected format.")
        collection_alias = collection["data"]["alias"]

        # Prepare and create the dataset
        dataset_payload = self._prepare_dataset_data(title, public_name, user_context)
        dataset = self._create_dataset(collection_alias, dataset_payload, user_context)
        if not dataset or "data" not in dataset:
            raise Exception("Could not create dataset in Dataverse or response has an unexpected format.")

        dataset["data"]["name"] = title
        return dataset["data"]

    def _create_collection(
        self, parent_alias: str, collection_payload: str, user_context: OptionalUserContext = None
    ) -> dict:
        headers = self._get_request_headers(user_context, auth_required=True)
        response = requests.post(self.create_collection_url(parent_alias), data=collection_payload, headers=headers)
        self._ensure_response_has_expected_status_code(response, 201)
        return response.json()

    def _create_dataset(
        self, parent_alias: str, dataset_payload: str, user_context: OptionalUserContext = None
    ) -> dict:
        headers = self._get_request_headers(user_context, auth_required=True)
        response = requests.post(self.create_dataset_url(parent_alias), data=dataset_payload, headers=headers)
        self._ensure_response_has_expected_status_code(response, 201)
        return response.json()

    def upload_file_to_draft_container(
        self,
        dataset_id: str,
        filename: str,
        file_path: str,
        user_context: OptionalUserContext = None,
    ):
        """Uploads a file to a draft dataset in the repository."""
        headers = self._get_request_headers(user_context, auth_required=True)

        with open(file_path, "rb") as file:
            # TODO: For some reason tar.gz files are not uploaded successfully to Dataverse.
            files = {"file": (filename, file)}
            add_files_url = self.add_files_to_dataset_url(dataset_id)
            response = requests.post(add_files_url, files=files, headers=headers)
            self._ensure_response_has_expected_status_code(response, 200)

    def download_file_from_container(
        self,
        container_id: str,
        file_identifier: str,
        file_path: str,
        user_context: OptionalUserContext = None,
    ):
        download_file_content_url = self.file_access_url(file_identifier)
        self._download_file(file_path, download_file_content_url, user_context)

    def _download_dataset_as_zip(self, dataset_id: str, file_path: str, user_context: OptionalUserContext = None):
        download_dataset_url = self.download_dataset_as_zip_url(dataset_id)
        self._download_file(file_path, download_dataset_url, user_context)

    def _download_file(
        self,
        file_path: str,
        download_file_content_url: str,
        user_context: OptionalUserContext = None,
    ):
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
            # TODO: We can only download files from published datasets for now
            if e.code in [401, 403, 404]:
                raise NotFoundException(
                    f"Cannot download file from URL '{file_path}'. Please make sure the dataset and/or file exists and it is public."
                )

    def _get_datasets_from_response(self, response: dict) -> List[RemoteDirectory]:
        rval: List[RemoteDirectory] = []
        for dataset in response["items"]:
            uri = self.to_plugin_uri(dataset_id=dataset["global_id"])
            rval.append(
                {
                    "class": "Directory",
                    "name": dataset.get("name") or "No title",
                    "uri": uri,
                    "path": self.plugin.to_relative_path(uri),
                }
            )
        return rval

    def _get_files_from_response(self, dataset_id: str, response: dict) -> List[RemoteFile]:
        rval: List[RemoteFile] = []
        for entry in response:
            dataFile = entry.get("dataFile")
            uri = self.to_plugin_uri(dataset_id, dataFile.get("persistentId"))
            rval.append(
                {
                    "class": "File",
                    "name": dataFile.get("filename"),
                    "size": dataFile.get("filesize"),
                    "ctime": dataFile.get("creationDate"),
                    "uri": uri,
                    "path": self.plugin.to_relative_path(uri),
                }
            )
        return rval

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
        headers = {"X-Dataverse-Key": f"{token}"} if token else {}
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

    def _get_user_email(self, user_context: OptionalUserContext = None) -> str:
        return user_context.email if user_context and user_context.email else "enteryourmail@placeholder.com"

    def _create_valid_alias(self, public_name: str, title: str) -> str:
        return re.sub(
            r"[^a-zA-Z0-9-_]", "", public_name.lower().replace(" ", "-") + "_" + title.lower().replace(" ", "-")
        )

    def _prepare_collection_data(
        self,
        title: str,
        public_name: str,
        user_context: OptionalUserContext = None,
    ) -> str:
        return json.dumps(
            {
                "name": title,
                "alias": self._create_valid_alias(public_name, title),
                "dataverseContacts": [
                    {"contactEmail": self._get_user_email(user_context)},
                ],
            }
        )

    def _prepare_dataset_data(
        self,
        title: str,
        public_name: str,
        user_context: OptionalUserContext = None,
    ) -> str:
        """Prepares the dataset data with all required metadata fields."""
        user_email = self._get_user_email(user_context)
        author_name = public_name
        dataset_data = {
            "datasetVersion": {
                "license": {"name": "CC0 1.0", "uri": "http://creativecommons.org/publicdomain/zero/1.0"},
                "metadataBlocks": {
                    "citation": {
                        "fields": [
                            {"value": title, "typeClass": "primitive", "multiple": False, "typeName": "title"},
                            {
                                "value": [
                                    {
                                        "authorName": {
                                            "value": author_name,
                                            "typeClass": "primitive",
                                            "multiple": False,
                                            "typeName": "authorName",
                                        }
                                    }
                                ],
                                "typeClass": "compound",
                                "multiple": True,
                                "typeName": "author",
                            },
                            {
                                "value": [
                                    {
                                        "datasetContactEmail": {
                                            "typeClass": "primitive",
                                            "multiple": False,
                                            "typeName": "datasetContactEmail",
                                            "value": user_email,
                                        },
                                        "datasetContactName": {
                                            "typeClass": "primitive",
                                            "multiple": False,
                                            "typeName": "datasetContactName",
                                            "value": author_name,
                                        },
                                    }
                                ],
                                "typeClass": "compound",
                                "multiple": True,
                                "typeName": "datasetContact",
                            },
                            {
                                "value": [
                                    {
                                        "dsDescriptionValue": {
                                            "value": "Exported history from Galaxy",
                                            "multiple": False,
                                            "typeClass": "primitive",
                                            "typeName": "dsDescriptionValue",
                                        }
                                    }
                                ],
                                "typeClass": "compound",
                                "multiple": True,
                                "typeName": "dsDescription",
                            },
                            {
                                "value": ["Medicine, Health and Life Sciences"],
                                "typeClass": "controlledVocabulary",
                                "multiple": True,
                                "typeName": "subject",
                            },
                        ],
                        "displayName": "Citation Metadata",
                    }
                },
            }
        }
        return json.dumps(dataset_data)


__all__ = ("DataverseRDMFilesSource",)
