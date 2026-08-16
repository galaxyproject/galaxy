from typing import (
    Any,
    cast,
)
from urllib.parse import urlparse

from galaxy.exceptions import (
    AuthenticationRequired,
    MessageException,
    ObjectNotFound,
)
from galaxy.files.models import (
    AnyRemoteEntry,
    Entry,
    EntryData,
    FilesSourceRuntimeContext,
    RemoteDirectory,
    RemoteFile,
)
from galaxy.files.sources._defaults import DEFAULT_SCHEME
from galaxy.files.sources._rdm import (
    ContainerAndFileIdentifier,
    RDMFileSourceConfiguration,
    RDMFileSourceTemplateConfiguration,
    RDMFilesSource,
    RDMRepositoryInteractor,
)
from galaxy.files.uris import validate_non_local
from galaxy.util import (
    DEFAULT_SOCKET_TIMEOUT,
    requests,
    stream_to_open_named_file,
)

# CKAN caps package_search at ckan.search.rows_max, which defaults to 1000
MAX_ROWS_PER_REQUEST = 1000

# CKAN indexes the visibility as "capacity", ascending puts "private" before "public". Score comes
# first to keep the relevance order when searching, while browsing gives every dataset the same score
DEFAULT_SORT = "score desc, capacity asc, title_string asc"


class CKANRDMFilesSource(RDMFilesSource):
    """A files source for CKAN open data portals.

    In CKAN a "dataset" (also called package) represents what we refer to as container in the rdm base class.
    """

    plugin_type = "ckan"
    supports_pagination = True
    supports_search = True

    def __init__(self, template_config: RDMFileSourceTemplateConfiguration):
        super().__init__(template_config)
        self.repository: CKANRepositoryInteractor

    @property
    def allowlist(self) -> list:
        """The urls Galaxy is allowed to fetch, used to validate the resource urls from CKAN."""
        return self._file_sources_config.fetch_url_allowlist or []

    def get_scheme(self) -> str:
        return self.scheme if self.scheme and self.scheme != DEFAULT_SCHEME else self.plugin_type

    def get_repository_interactor(self, repository_url: str) -> RDMRepositoryInteractor:
        return CKANRepositoryInteractor(repository_url, self)

    def parse_path(self, source_path: str, container_id_only: bool = False) -> ContainerAndFileIdentifier:
        """Parses the given source path into the dataset id and the resource name.

        The path is either '/<dataset_id>' or '/<dataset_id>/<resource_name>'. Dataset ids are slugs
        without slashes, so splitting on the first one is enough and resource names may contain slashes.
        """
        if not source_path.startswith("/"):
            raise ValueError(f"Invalid source path: '{source_path}'. Must start with '/'.")
        path_without_slash = source_path[1:]

        if container_id_only:
            if not path_without_slash:
                raise ValueError(f"Invalid source path: '{source_path}'. Expected format: '/<dataset_id>'.")
            dataset_id = path_without_slash.split("/", 1)[0]
            return ContainerAndFileIdentifier(container_id=dataset_id, file_identifier="")

        parts = path_without_slash.split("/", 1)
        if len(parts) < 2 or not parts[1]:
            raise ValueError(f"Invalid source path: '{source_path}'. Expected format: '/<dataset_id>/<resource_name>'.")
        return ContainerAndFileIdentifier(container_id=parts[0], file_identifier=parts[1])

    def get_container_id_from_path(self, source_path: str) -> str:
        return self.parse_path(source_path, container_id_only=True).container_id

    def _list(
        self,
        context: FilesSourceRuntimeContext[RDMFileSourceConfiguration],
        path="/",
        recursive=False,
        write_intent: bool = False,
        limit: int | None = None,
        offset: int | None = None,
        query: str | None = None,
        sort_by: str | None = None,
    ) -> tuple[list[AnyRemoteEntry], int]:
        """This method lists the datasets or the resources of a dataset from CKAN."""
        is_root_path = path == "/"
        if is_root_path:
            datasets, total_hits = self.repository.get_file_containers(
                context, write_intent, limit=limit, offset=offset, query=query, sort_by=sort_by
            )
            return cast(list[AnyRemoteEntry], datasets), total_hits
        dataset_id = self.get_container_id_from_path(path)
        files = self.repository.get_files_in_container(context, dataset_id, write_intent, query)
        return cast(list[AnyRemoteEntry], files), len(files)

    def _realize_to(
        self, source_path: str, native_path: str, context: FilesSourceRuntimeContext[RDMFileSourceConfiguration]
    ):
        """Used when downloading resources from CKAN."""
        dataset_id, resource_name = self.parse_path(source_path)
        self.repository.download_file_from_container(dataset_id, resource_name, native_path, context)

    def _write_from(
        self, target_path: str, native_path: str, context: FilesSourceRuntimeContext[RDMFileSourceConfiguration]
    ):
        """Used when uploading files to CKAN as a new resource of an existing dataset."""
        dataset_id, resource_name = self.parse_path(target_path)
        self.repository.upload_file_to_draft_container(dataset_id, resource_name, native_path, context)

    def _create_entry(
        self, entry_data: EntryData, context: FilesSourceRuntimeContext[RDMFileSourceConfiguration]
    ) -> Entry:
        """Rejects the creation of datasets, the export dialogs cannot ask for an organization."""
        # the base class would raise NotImplementedError, which the api reports as a server error
        raise MessageException(
            "Creating new CKAN datasets from Galaxy is not supported, a new dataset has to be "
            "assigned to an organization. Create the dataset in CKAN and export into it instead."
        )


class CKANRepositoryInteractor(RDMRepositoryInteractor):
    """In CKAN a "dataset" (also called package) represents what we refer to as container in the rdm base class."""

    def __init__(self, repository_url: str, plugin: CKANRDMFilesSource):
        super().__init__(repository_url, plugin)
        # precomputed once, used to decide if the api token may be sent to a resource url
        self._repository_origin = self._to_origin(self.repository_url)
        self._allowlist = plugin.allowlist
        self._user_id: str | None = None

    @property
    def api_base_url(self) -> str:
        return f"{self.repository_url}/api/3/action"

    def to_plugin_uri(self, container_id: str, filename: str | None = None) -> str:
        if filename:
            return f"{self.plugin.get_uri_root()}/{container_id}/{filename}"
        return f"{self.plugin.get_uri_root()}/{container_id}"

    def get_file_containers(
        self,
        context: FilesSourceRuntimeContext[RDMFileSourceConfiguration],
        write_intent: bool,
        limit: int | None = None,
        offset: int | None = None,
        query: str | None = None,
        sort_by: str | None = None,
    ) -> tuple[list[RemoteDirectory], int]:
        """Lists the datasets of the CKAN instance.

        The pagination happens in CKAN, so only the requested page is fetched. Without a limit the
        maximum number of rows CKAN allows per request is used.
        """
        params: dict[str, Any] = {
            "q": query or "*:*",
            "rows": limit if limit is not None else MAX_ROWS_PER_REQUEST,
            "start": offset or 0,
            "include_private": True,
            "sort": sort_by or DEFAULT_SORT,
        }
        if write_intent:
            # a dataset is writable through the user's role in its organization, not through the private flag
            filter_query = self._get_writable_filter_query(context)
            if not filter_query:
                return [], 0
            params["fq"] = filter_query
        result = self._get_response(context, "package_search", params)
        return self._get_datasets_from_response(result), result["count"]

    def get_files_in_container(
        self,
        context: FilesSourceRuntimeContext[RDMFileSourceConfiguration],
        container_id: str,
        writeable: bool,
        query: str | None = None,
    ) -> list[RemoteFile]:
        """This method lists the resources of a CKAN dataset."""
        dataset = self._get_dataset(context, container_id)
        files = self._get_files_from_response(container_id, dataset.get("resources", []))
        if query:
            files = [file for file in files if query in file.name]
        return files

    def upload_file_to_draft_container(
        self,
        container_id: str,
        filename: str,
        file_path: str,
        context: FilesSourceRuntimeContext[RDMFileSourceConfiguration],
    ) -> None:
        """Uploads a file as a new resource of an existing CKAN dataset."""
        headers = self._get_request_headers(context, auth_required=True)
        with open(file_path, "rb") as file:
            response = requests.post(
                f"{self.api_base_url}/resource_create",
                data={"package_id": container_id, "name": filename},  # target dataset and display name
                files={"upload": (filename, file)},  # filename for the download and the file content
                headers=headers,
                timeout=DEFAULT_SOCKET_TIMEOUT,
            )
        self._ensure_response_has_expected_status_code(response, 200)

    def download_file_from_container(
        self,
        container_id: str,
        file_identifier: str,
        file_path: str,
        context: FilesSourceRuntimeContext[RDMFileSourceConfiguration],
    ) -> None:
        """Downloads a resource of a CKAN dataset to the given file path."""
        resource = self._get_resource(context, container_id, file_identifier)
        download_url = resource.get("url")
        if not download_url:
            raise ObjectNotFound(f"The resource '{file_identifier}' does not have a download url.")
        if not download_url.startswith(("http://", "https://")):
            # requests refuses other schemes anyway, but with a generic error message
            raise MessageException(
                f"The resource '{file_identifier}' is linked with an unsupported url scheme, "
                "only http and https can be downloaded"
            )
        # the url is taken from the CKAN metadata, so it has to be validated before Galaxy requests it
        validate_non_local(download_url, self._allowlist)
        # CKAN resources can also be hosted on other servers, the token must not leak to them
        is_hosted_by_ckan = self._is_same_origin(download_url)
        headers = self._get_request_headers(context) if is_hosted_by_ckan else {}
        with requests.get(
            download_url,
            headers=headers,
            stream=True,
            timeout=DEFAULT_SOCKET_TIMEOUT,
        ) as response:
            self._ensure_download_response_is_ok(response, is_hosted_by_ckan)
            validate_non_local(response.url, self._allowlist)  # the request could have been redirected
            response.raw.decode_content = True  # without this gzipped responses stay compressed
            target_file = open(file_path, "wb")  # the file descriptor is closed by stream_to_open_named_file
            stream_to_open_named_file(response.raw, target_file.fileno(), file_path)

    def _get_writable_filter_query(self, context: FilesSourceRuntimeContext[RDMFileSourceConfiguration]) -> str | None:
        """Builds the search filter for the datasets the user may add a resource to.

        The whole expression has to be wrapped in parentheses, CKAN appends its own required
        filters (site id, state, permission labels) to it and the grouping would be lost otherwise.
        """
        clauses = []
        organization_ids = self._get_writable_organization_ids(context)
        if organization_ids:
            quoted_ids = " OR ".join(f'"{organization_id}"' for organization_id in organization_ids)
            clauses.append(f"owner_org:({quoted_ids})")
        user_id = self._get_current_user_id(context)
        if user_id:
            # datasets without an organization are not covered by the filter above. CKAN itself would
            # let any logged in user edit them, but only offering the own ones matches expectations
            clauses.append(f'(creator_user_id:"{user_id}" AND -owner_org:[* TO *])')
        if not clauses:
            return None
        return "({})".format(" OR ".join(clauses))

    def _get_writable_organization_ids(
        self, context: FilesSourceRuntimeContext[RDMFileSourceConfiguration]
    ) -> list[str]:
        """Returns the organizations in which the user is allowed to add resources to a dataset.

        An export adds a resource to an existing dataset, so update_dataset is the matching
        permission. In CKAN it is held by the editor and the admin role.
        """
        organizations = self._get_response(
            context, "organization_list_for_user", {"permission": "update_dataset"}, auth_required=True
        )
        return [organization["id"] for organization in organizations]

    def _get_current_user_id(self, context: FilesSourceRuntimeContext[RDMFileSourceConfiguration]) -> str | None:
        """Returns the id of the CKAN user the api token belongs to.

        Called without an id, user_show returns the authenticated user, which is the only way to
        find out the own user id.
        """
        if self._user_id is None:
            self._user_id = self._get_response(context, "user_show", auth_required=True).get("id")
        return self._user_id

    def _get_dataset(
        self, context: FilesSourceRuntimeContext[RDMFileSourceConfiguration], dataset_id: str
    ) -> dict[str, Any]:
        return self._get_response(context, "package_show", {"id": dataset_id})

    def _get_resource(
        self, context: FilesSourceRuntimeContext[RDMFileSourceConfiguration], dataset_id: str, resource_name: str
    ) -> dict[str, Any]:
        """Looks up a resource by its name, CKAN download urls are not predictable from the name."""
        dataset = self._get_dataset(context, dataset_id)
        for resource in dataset.get("resources", []):
            if self._get_resource_name(resource) == resource_name:
                return resource
        raise ObjectNotFound(f"The dataset '{dataset_id}' does not contain a resource '{resource_name}'.")

    def _get_resource_name(self, resource: dict[str, Any]) -> str:
        # resources are not required to have a name in CKAN, then the id is used instead
        return resource.get("name") or resource["id"]

    def _get_datasets_from_response(self, response: dict) -> list[RemoteDirectory]:
        rval: list[RemoteDirectory] = []
        for dataset in response["results"]:
            # the name is the slug of the dataset and is used to address it in the api
            uri = self.to_plugin_uri(dataset["name"])
            rval.append(
                RemoteDirectory(
                    name=dataset.get("title") or dataset["name"],
                    uri=uri,
                    path=self.plugin.to_relative_path(uri),
                )
            )
        return rval

    def _get_files_from_response(self, dataset_id: str, resources: list[dict[str, Any]]) -> list[RemoteFile]:
        rval: list[RemoteFile] = []
        for resource in resources:
            resource_name = self._get_resource_name(resource)
            uri = self.to_plugin_uri(dataset_id, resource_name)
            rval.append(
                RemoteFile(
                    name=resource_name,
                    size=int(resource.get("size") or 0),  # the size is not always known in CKAN
                    ctime=resource.get("last_modified") or resource.get("created"),
                    uri=uri,
                    path=self.plugin.to_relative_path(uri),
                )
            )
        return rval

    def _get_response(
        self,
        context: FilesSourceRuntimeContext[RDMFileSourceConfiguration],
        action: str,
        params: dict[str, Any] | None = None,
        auth_required: bool = False,
    ) -> Any:
        """Calls an action of the CKAN Action API and returns the result of the payload."""
        headers = self._get_request_headers(context, auth_required)
        response = requests.get(
            f"{self.api_base_url}/{action}",
            params=params,
            headers=headers,
            timeout=DEFAULT_SOCKET_TIMEOUT,
        )
        self._ensure_response_has_expected_status_code(response, 200)
        payload = response.json()
        # a host that is not CKAN can answer with 200 as well, the success flag identifies a real payload
        if not payload.get("success", False):
            error = payload.get("error", {})
            raise MessageException(f"CKAN API call failed: {error.get('message') or error}")
        return payload["result"]

    def _get_request_headers(
        self, context: FilesSourceRuntimeContext[RDMFileSourceConfiguration], auth_required: bool = False
    ) -> dict[str, str]:
        token = self.plugin.get_authorization_token(context)
        # CKAN expects the raw api token in the Authorization header, without a "Bearer" prefix
        headers = {"Authorization": token} if token else {}
        if auth_required and not token:
            self._raise_auth_required()
        return headers

    def _ensure_response_has_expected_status_code(self, response, expected_status_code: int) -> None:
        if response.status_code == expected_status_code:
            return
        if response.status_code in (401, 403):
            # CKAN ignores an invalid token and answers anonymously, so it never reports a bad token
            self._raise_auth_required(
                f"CKAN denied the request (HTTP {response.status_code}). The access token for "
                f"'{self.plugin.label}' may be invalid or may not have the required permission."
            )
        if response.status_code == 404:
            raise ObjectNotFound(f"Not found (HTTP {response.status_code}): {response.url}")
        raise MessageException(f"Request to {response.url} failed with status code {response.status_code}")

    def _ensure_download_response_is_ok(self, response, is_hosted_by_ckan: bool) -> None:
        """Checks the response of a resource download.

        A resource can link to a server outside of CKAN. Asking the user for a CKAN token would not
        help there, so such a denial is not reported as a missing authentication.
        """
        if not is_hosted_by_ckan and response.status_code in (401, 403):
            raise MessageException(
                f"Access to the resource at '{response.url}' was denied (HTTP {response.status_code}). "
                "It is hosted outside of the CKAN instance, so the CKAN access token does not apply to it."
            )
        self._ensure_response_has_expected_status_code(response, 200)

    def _raise_auth_required(self, message: str | None = None) -> None:
        raise AuthenticationRequired(
            message or f"Please provide a personal access token in your user's preferences for '{self.plugin.label}'"
        )

    def _is_same_origin(self, url: str) -> bool:
        """Checks if a url points to the CKAN instance itself and not to an external server."""
        return self._to_origin(url) == self._repository_origin

    @staticmethod
    def _to_origin(url: str) -> tuple[str | None, str | None, int | None]:
        parsed_url = urlparse(url)
        return parsed_url.scheme, parsed_url.hostname, parsed_url.port


__all__ = ("CKANRDMFilesSource",)
