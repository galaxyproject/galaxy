from datetime import datetime
from typing import (
    Any,
    Optional,
    Union,
)
from urllib.parse import urlparse

import requests
from fsspec import AbstractFileSystem

from galaxy.files.models import FilesSourceRuntimeContext
from galaxy.files.sources._fsspec import (
    CacheOptionsDictType,
    FsspecBaseFileSourceConfiguration,
    FsspecBaseFileSourceTemplateConfiguration,
    FsspecFilesSource,
)
from galaxy.util import DEFAULT_SOCKET_TIMEOUT
from galaxy.util.config_templates import TemplateExpansion


class CKANFileSystem(AbstractFileSystem):
    def __init__(self, base_url: str, token: Optional[str] = None, **kwargs: Any):
        super().__init__(**kwargs)
        self.base_url = base_url.rstrip("/")  # prevents double slashes in URLs
        self.token = token

    def _get_request_headers(self) -> dict[str, str]:
        headers = {}
        # auth header, only if token is provided
        if self.token:
            headers["Authorization"] = self.token  # raw api token, CKAN doesnt need bearer prefix
        return headers

    def _raise_for_ckan_error(self, response: requests.Response) -> None:
        if response.status_code in (401, 403):
            raise PermissionError(f"Access denied (HTTP {response.status_code}).")
        if response.status_code == 404:
            raise FileNotFoundError(f"Not found (HTTP {response.status_code}): {response.url}")
        response.raise_for_status()  # any other 4xx/5xx still raises a generic HTTPError

    # call ckan action api and return response result
    def _get_response(
        self,
        action: str,
        params: Optional[dict[str, Any]] = None,
    ) -> Any:
        url = f"{self.base_url}/api/3/action/{action}"
        headers = self._get_request_headers()
        response = requests.get(url, headers=headers, timeout=DEFAULT_SOCKET_TIMEOUT, params=params)
        self._raise_for_ckan_error(response)  # raise exception for HTTP errors
        payload = response.json()
        # ckan could return HTTP 200 even for errors, so check success field in payload
        if not payload.get("success", False):  # success is False or missing
            error = payload.get("error", {})
            raise Exception(f"CKAN API call failed: {error.get('message') or error}")
        return payload["result"]

    # upload a file to an existing dataset as new resource
    def _post_resource(self, dataset_id: str, resource_name: str, file_path: str) -> None:
        url = f"{self.base_url}/api/3/action/resource_create"
        headers = self._get_request_headers()
        with open(file_path, "rb") as f:
            response = requests.post(
                url,
                headers=headers,
                data={"package_id": dataset_id, "name": resource_name},  # target dataset and display name
                files={"upload": (resource_name, f)},  # filename for download and file content
                timeout=DEFAULT_SOCKET_TIMEOUT,
            )
        self._raise_for_ckan_error(response)  # raise exception for HTTP errors
        payload = response.json()
        # ckan could return HTTP 200 even for errors, so check success field in payload
        if not payload.get("success", False):  # success is False or missing
            error = payload.get("error", {})
            raise Exception(f"CKAN API call failed: {error.get('message') or error}")

    def _list_public_datasets(self) -> list[str]:
        # cheap call that returns just the names of public datasets
        return self._get_response("package_list")

    def _list_private_datasets(self) -> list[str]:
        # for listing private datasets, package_search is needed which returns all metadata, not just names
        # since package_search paginates results, its needed to loop until all datasets are retrieved
        names = []
        start = 0
        while True:
            # if no private datasets just returns empty list
            result = self._get_response(
                "package_search",
                params={
                    "fq": "private:true",  # filter query to return only private datasets
                    "include_private": True,  # without this CKAN hides private datasets
                    "rows": 1000,  # rows is page size, 1000 is max allowed in default CKAN
                    "start": start,  # pagination offset
                },
            )
            names.extend([dataset["name"] for dataset in result["results"]])
            # result["count"] is total number of private datasets, tells if all are retrieved
            if len(names) >= result["count"]:
                break
            start += 1000
        return names

    # lists all datasets that are available to the user
    # users private datasets are listed first, then the public ones
    def _list_all_datasets(self) -> list[str]:
        return self._list_private_datasets() + self._list_public_datasets()

    # fetch dataset metadata
    def _get_dataset(self, dataset_id: str) -> dict[str, Any]:
        return self._get_response("package_show", params={"id": dataset_id})

    # extract resources from dataset payload
    def _list_resources(self, dataset_id: str) -> list[dict[str, Any]]:
        dataset = self._get_dataset(dataset_id)
        return dataset.get("resources", [])

    def _is_root(self, path: str) -> bool:
        return path in ("", "/")

    # in case resource name is missing, use id
    def _resource_name(self, resource: dict[str, Any]) -> Optional[str]:
        return resource.get("name") or resource.get("id")

    # returns last modified as a date object, or None if missing/invalid
    def _parse_modified(self, value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None

    # returns resource entry with optional metadata
    def _resource_entry(self, dataset_id: str, resource: dict[str, Any]) -> dict[str, Any]:
        size = resource.get("size") or resource.get("filesize")
        entry = {
            "name": f"/{dataset_id}/{self._resource_name(resource)}",
            "type": "file",
            "modified": self._parse_modified(resource.get("last_modified") or resource.get("metadata_modified")),
            "id": resource.get("id"),
        }
        # size isnt always known, so this prevents int(None) error
        if size is not None:
            entry["size"] = size
        return entry

    # returns dataset entry with optional metadata
    def _dataset_entry(self, name: str, dataset: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        entry: dict[str, Any] = {"name": f"/{name}", "type": "directory", "size": None}
        if dataset:
            # adds these parameter in case detail=True
            entry["modified"] = self._parse_modified(dataset.get("metadata_modified") or dataset.get("last_modified"))
            entry["id"] = dataset.get("id")
        return entry

    # splits path into dataset_id and optional resource_name
    def _split_path(self, path: str) -> tuple[str, Optional[str]]:
        parts = path.strip("/").split("/", 1)
        dataset_id = parts[0]
        resource_name = None  # path is /dataset
        if len(parts) > 1:
            resource_name = parts[1]  # path is /dataset/resource
        return dataset_id, resource_name

    # find a resource by name in a dataset
    def _find_resource(self, dataset_id: str, resource_name: str) -> dict[str, Any]:
        resources = self._list_resources(dataset_id)
        for resource in resources:
            if self._resource_name(resource) == resource_name:
                return resource
        raise FileNotFoundError(f"/{dataset_id}/{resource_name}")

    def _is_same_host(self, url: str) -> bool:
        return urlparse(url).hostname == urlparse(self.base_url).hostname

    # list datasets in root or resources in a dataset
    def ls(self, path: str = "", detail: bool = True, **kwargs: Any) -> list[dict[str, Any]] | list[str]:
        if not self._is_root(path):
            # list resources in dataset
            dataset_id, _ = self._split_path(path)  # only need dataset_id, resource_name isnt needed
            resources = self._list_resources(dataset_id)
            if detail:
                return [self._resource_entry(dataset_id, r) for r in resources]
            return [self._resource_entry(dataset_id, r)["name"] for r in resources]

        # list datasets in root
        datasets = self._list_all_datasets()
        if detail:
            return [self._dataset_entry(name) for name in datasets]
        return [self._dataset_entry(name)["name"] for name in datasets]

    # get dataset or resource metadata
    def info(self, path: str, **kwargs: Any) -> dict[str, Any]:
        if self._is_root(path):
            return {"name": "/", "type": "directory", "size": None}
        dataset_id, resource_name = self._split_path(path)
        # /dataset
        if not resource_name:
            return self._dataset_entry(dataset_id, self._get_dataset(dataset_id))
        # /dataset/resource
        resource = self._find_resource(dataset_id, resource_name)
        return self._resource_entry(dataset_id, resource)

    # stream resource content using requests, returns a file-like object
    def _open(self, path: str, mode: str = "rb", **kwargs: Any):
        if mode != "rb":
            raise NotImplementedError("Only read binary mode 'rb' is supported")
        dataset_id, resource_name = self._split_path(path)
        if resource_name is None:
            raise FileNotFoundError(path)
        resource = self._find_resource(dataset_id, resource_name)
        url = resource.get("url") or resource.get("download_url") or None
        if not url:
            raise FileNotFoundError(path)
        # only add the auth token if the resource is hosted on the same domain as the CKAN instance
        # to prevent leaking tokens to external URLs
        headers = self._get_request_headers() if self._is_same_host(url) else {}
        response = requests.get(url, stream=True, headers=headers, timeout=DEFAULT_SOCKET_TIMEOUT)
        self._raise_for_ckan_error(response)  # raise exception for HTTP errors
        response.raw.decode_content = True
        return response.raw


class CKANFileSourceTemplateConfiguration(FsspecBaseFileSourceTemplateConfiguration):
    endpoint: Union[str, TemplateExpansion]
    token: Union[str, TemplateExpansion, None] = None


class CKANFileSourceConfiguration(FsspecBaseFileSourceConfiguration):
    endpoint: str
    token: Optional[str] = None


class CKANFilesSource(FsspecFilesSource[CKANFileSourceTemplateConfiguration, CKANFileSourceConfiguration]):
    plugin_type = "ckan"
    required_module = CKANFileSystem
    required_package = "requests"

    template_config_class = CKANFileSourceTemplateConfiguration
    resolved_config_class = CKANFileSourceConfiguration

    def _open_fs(
        self, context: FilesSourceRuntimeContext[CKANFileSourceConfiguration], cache_options: CacheOptionsDictType
    ) -> CKANFileSystem:
        config = context.config
        return CKANFileSystem(base_url=config.endpoint, token=config.token, **cache_options)

    def _write_from(
        self, target_path: str, native_path: str, context: FilesSourceRuntimeContext[CKANFileSourceConfiguration]
    ) -> None:
        fs = self._open_fs(context, {})
        dataset_id, resource_name = fs._split_path(target_path)
        if not resource_name:
            raise ValueError("Select a dataset as the upload target, not the root.")
        fs._post_resource(dataset_id, resource_name, native_path)


__all__ = ("CKANFilesSource",)
