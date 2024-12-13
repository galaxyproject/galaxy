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
    RDMFilesSource,
    RDMFilesSourceProperties,
    RDMRepositoryInteractor,
    ContainerAndFileIdentifier,
)
from galaxy.util import (
    DEFAULT_SOCKET_TIMEOUT,
    get_charset_from_http_headers,
    requests,
    stream_to_open_named_file,
)

from galaxy.schema.schema import (
    ModelStoreFormat,
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

AccessStatus = Literal["public", "restricted"]

class DataverseRDMFilesSource(RDMFilesSource):
    """A files source for Dataverse turn-key research data management repository.
    
    In Dataverse a "Dataset" represents what we refer to as container in the rdm base class
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
    
    # TODO: Maybe we dont need this?
    # def score_url_match(self, url: str) ->
    #     if match := self._scheme_regex.match(url):
    #         return match.span()[1]
    #     else:
    #         return 0
        
    # TODO: Test this method (maybe we dont need it)
    def to_relative_path(self, url: str) -> str:
        legacy_uri_root = f"{DEFAULT_SCHEME}://{self.id}"
        if url.startswith(legacy_uri_root):
            return url[len(legacy_uri_root) :]
        else:
            return super().to_relative_path(url)
        
    def get_repository_interactor(self, repository_url: str) -> RDMRepositoryInteractor:
        return DataverseRepositoryInteractor(repository_url, self)

    def parse_path(self, source_path: str, container_id_only: bool = False) -> ContainerAndFileIdentifier:
        """Parses the given source path and returns the dataset_id and the file_id. 

        The source path must have the format '/<dataset_id>/<file_id>'.
        If dataset_id_only is True, the source path must have the format '/<dataset_id>' and an empty file_id will be returned.

        Example dataset_id: 
        doi:10.70122/FK2/DIG2DG

        Example file_id:
        doi:10.70122/FK2/DIG2DG/AVNCLL
        """
        def get_error_msg(details: str) -> str:
            return f"Invalid source path: '{source_path}'. Expected format: '{expected_format}'. {details}"

        expected_format = "/<dataset_id>"
        if not source_path.startswith("/"):
            raise ValueError(get_error_msg("Must start with '/'."))
        parts = source_path[1:].split("/", 4)
        dataset_id = "/".join(parts[0:3])
        if container_id_only:
            if len(parts) != 3:
                raise ValueError(get_error_msg("Please provide the dataset_id only."))
            dataset_id = "/".join(parts[0:3])
            return ContainerAndFileIdentifier(dataset_id=parts[0:3], file_identifier="")
        expected_format = "/<dataset_id>/<file_id>"
        if len(parts) < 4:
            raise ValueError(get_error_msg("Please provide both the dataset_id and file_id."))
        if len(parts) > 4:
            raise ValueError(get_error_msg("Too many parts. Please provide the dataset_id and file_id only."))
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
        """This method lists the files in the Dataverse Dataset."""
        writeable = opts and opts.writeable or False
        is_root_path = path == "/"
        if is_root_path:
            datasets, total_hits = self.repository.get_file_containers(
                writeable, user_context, limit=limit, offset=offset, query=query
            )
            return cast(List[AnyRemoteEntry], datasets), total_hits
        dataset_id = self._get_dataset_id_from_path(path)
        files = self.repository.get_files_in_container(dataset_id, writeable, user_context)
        return cast(List[AnyRemoteEntry], files), len(files)

    def _create_entry(
        self,
        entry_data: EntryData,
        user_context: OptionalUserContext = None,
        opts: Optional[FilesSourceOptions] = None,
    ) -> Entry:
        # TODO: Implement this for Dataverse
        # public_name = self.get_public_name(user_context)
        # dataset = self.repository.create_draft_file_container(entry_data.name, public_name, user_context)
        # return {
        #     "uri": self.to_plugin_uri(dataset["global_id"]),
        #     "name": dataset["name"],
        #     "external_link": 'test', 
        # }
        pass

    def _realize_to(
        self,
        source_path: str,
        native_path: str,
        user_context: OptionalUserContext = None,
        opts: Optional[FilesSourceOptions] = None,
    ):
        # TODO: user_context is always None here when called from a data fetch. (same problem as in invenio.py)
        # This prevents downloading files that require authentication even if the user provided a token.
        
        dataset_id, file_id = self.parse_path(source_path)
        try:
            self.repository.download_file_from_container(dataset_id, file_id, native_path, user_context=user_context)
        except NotFoundException as e:
            filename = file_id.split("/")[-1]
            is_archive = any(format in filename for format in ModelStoreFormat.available_formats())
            if is_archive:
                # Workaround explanation:
                # When we archive our history to dataverse, the zip sent from Galaxy to dataverse is extracted automatically.
                # Only the contents are stored, not the zip itself. 
                # So, if a zip is not found, we suppose we are trying to reimport an archived history
                # and make an API call to Dataverse to download the dataset as a zip.
                self.repository._download_dataset_as_zip(dataset_id, native_path, user_context)

    # TODO: Test this method
    def _write_from(
        self,
        target_path: str,
        native_path: str,
        user_context: OptionalUserContext = None,
        opts: Optional[FilesSourceOptions] = None,
    ):
        dataset_id, file_id = self.parse_path(target_path)
        self.repository.upload_file_to_draft_container(dataset_id, file_id, native_path, user_context=user_context)

    def _get_dataset_id_from_path(self, path: str) -> str:
        # /doi:10.70122/FK2/DIG2DG => doi:10.70122/FK2/DIG2DG
        return path.lstrip("/")
    
class DataverseRepositoryInteractor(RDMRepositoryInteractor):
    """In Dataverse a "Dataset" represents what we refer to as container in the rdm base class"""

    @property
    def api_base_url(self) -> str:
        return f"{self.repository_url}/api/v1"

    @property
    def search_url(self) -> str:
        return f"{self.api_base_url}/search"
    
    def file_access_url(self, file_id: str) -> str:
        encoded_file_id = quote(encoded_file_id, safe="")
        return f"{self.api_base_url}/access/datafile/:persistentId?persistentId={encoded_file_id}"
    
    def files_of_dataset_url(self, dataset_id: str, dataset_version: str = ':latest') -> str:
        return f"{self.api_base_url}/datasets/:persistentId/versions/{dataset_version}/files?persistentId={dataset_id}"
    
    def add_files_to_dataset_url(self, dataset_id: str) -> str:
        return f"{self.api_base_url}/datasets/:persistentId/add?persistentId={dataset_id}"

    def to_plugin_uri(self, dataset_id: str, file_identifier: Optional[str] = None) -> str:
        return f"{self.plugin.get_uri_root()}/{f'{file_identifier}' if file_identifier else f'{dataset_id}'}"
        
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
        params: Dict[str, Any] = {}
        params["type"] = "dataset"
        if writeable:
            # Only draft datasets can be written to.
            # This is not tested and assumes that drafts are never public, 
            # i.e. we automatically only get the drafts from our user
            params["fq"] = "publicationStatus:Draft"
        params["per_page"] = limit or DEFAULT_PAGE_LIMIT
        params["start"] = offset
        params["q"] = query or "*"
        params["sort"] = sort_by or "date" # can be either "name" or "date"
        response_data = self._get_response(user_context, request_url, params=params)
        total_hits = response_data["data"]["total_count"]
        return self._get_datasets_from_response(response_data["data"]), total_hits

    def get_files_in_container(
        self, dataset_id: str, writeable: bool, user_context: OptionalUserContext = None
    ) -> List[RemoteFile]:
        """This method lists the files in a dataverse dataset."""
        request_url = self.files_of_dataset_url(dataset_id=dataset_id)
        response_data = self._get_response(user_context, request_url)
        total_hits = response_data["totalCount"]
        return self._get_files_from_response(dataset_id, response_data["data"])

    def create_draft_file_container(
        self, title: str, public_name: Optional[str] = None, user_context: OptionalUserContext = None
    ) -> RemoteDirectory:
        # TODO Implement for Dataverse, see invenio
        pass

    def upload_file_to_draft_container(
        self,
        dataset_id: str,
        filename: str,
        file_path: str,
        user_context: OptionalUserContext = None,
    ):
        headers = self._get_request_headers(user_context, auth_required=True)

        with open(file_path, "rb") as file:
            files = {'file': (filename, file)}
            # --------------------------------------------------
            # Using a "jsonData" parameter, add optional description + file tags
            # --------------------------------------------------
            # params = dict(description='Blue skies!',
            #   categories=['Lily', 'Rosemary', 'Jack of Hearts'])
            # params_as_json_string = json.dumps(params)
            payload = dict()
            add_files_url = self.add_files_to_dataset_url(dataset_id)
            response = requests.post(add_files_url, data=payload, files=files, headers=headers)
            print(response.json())
            print(response.status_code)
            self._ensure_response_has_expected_status_code(response, 200)

    def download_file_from_container(
        self,
        container_id: str,
        file_identifier: str,
        file_path: str,
        user_context: OptionalUserContext = None,
    ):
        download_file_content_url = self._get_download_file_url(container_id, file_identifier, user_context)
        self._download_file(file_path, download_file_content_url, user_context)

    def _download_dataset_as_zip(
            self, 
            dataset_id: str, 
            file_path: str, 
            user_context: OptionalUserContext = None
        ):
        download_file_content_url = f"{self.api_base_url}/access/dataset/:persistentId/?persistentId={dataset_id}"
        self._download_file(file_path, download_file_content_url, user_context)

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

    def _get_download_file_url(self, container_id: str, file_id: str, user_context: OptionalUserContext = None):
        """Get the URL to download a file from a dataset(=dataverse file container).

        This method is used to download files from both published and draft datasets that are accessible by the user.
        """
        download_file_content_url = self.file_access_url(file_id=file_id)

        # file_details = self._get_response(user_context, file_details_url)
        # TODO: This is a temporary workaround from invenio for the fact that the "content" API
        # does not support downloading files from S3 or other remote storage classes.
        # We might need something like this as well for dataverse
        # if not self._can_download_from_api(file_details):
            # More info: https://inveniordm.docs.cern.ch/reference/file_storage/#remote-files-r
            # download_file_content_url = f"{file_details_url.replace('/api', '')}?download=1"

        return download_file_content_url

    def _is_api_url(self, url: str) -> bool:
        return "/api/" in url

    def _can_download_from_api(self, file_details: dict) -> bool:
        # TODO: Have a look at this problem

        # Only files stored locally seems to be fully supported by the API for now
        # More info: https://inveniordm.docs.cern.ch/reference/file_storage/
        return file_details["storage_class"] == "L"

    def _get_datasets_from_response(self, response: dict) -> List[RemoteDirectory]:
        datasets = response["items"]
        rval: List[RemoteDirectory] = []
        for dataset in datasets:
            uri = self.to_plugin_uri(dataset_id=dataset["global_id"])
            path = self.plugin.to_relative_path(uri)
            name = self._get_dataset_title(dataset)
            rval.append(
                {
                    "class": "Directory",
                    "name": name,
                    "uri": uri,
                    "path": path,
                }
            )
        return rval

    def _get_dataset_title(self, dataset: DataverseDataset) -> str:
        title = dataset.get("name")
        return title or "No title"

    def _get_files_from_response(self, dataset_id: str, response: dict) -> List[RemoteFile]:   
        
        # TODO Do we need this for Dataverse?
        # this is used in invenio, do we need it for dataverse?
        # files_enabled = response.get("enabled", False)
        # if not files_enabled:
        #    return []

        rval: List[RemoteFile] = []
        for entry in response:
            dataFile = entry.get("dataFile")
            filename = dataFile.get("filename")
            persistendId = dataFile.get("persistentId")
            uri = self.to_plugin_uri(dataset_id=dataset_id, file_identifier=persistendId)
            path = self.plugin.to_relative_path(uri)
            rval.append(
                {
                    "class": "File",
                    "name": filename,
                    "size": dataFile.get("filesize"),
                    "ctime": dataFile.get("creationDate"),
                    "uri": uri,
                    "path": path,
                }
            )
        return rval

    # TODO: Implement this for Dataverse
    # def _get_creator_from_public_name(self, public_name: Optional[str] = None) -> Creator:  
        # pass

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

    # TODO: Test this method
    def _raise_auth_required(self):
        raise AuthenticationRequired(
            f"Please provide a personal access token in your user's preferences for '{self.plugin.label}'"
        )

    # TODO: Test this method
    def _get_response_error_message(self, response):
        response_json = response.json()
        error_message = response_json.get("message") if response.status_code == 400 else response.text
        errors = response_json.get("errors", [])
        for error in errors:
            error_message += f"\n{json.dumps(error)}"
        return error_message


__all__ = ("DataverseRDMFilesSource",)