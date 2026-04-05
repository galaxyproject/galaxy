from __future__ import annotations

from typing import (
    Annotated,
    Optional,
    Union,
)
from urllib.parse import quote

import requests
from pydantic import (
    AliasChoices,
    Field,
)

from galaxy.exceptions import (
    AuthenticationRequired,
    MessageException,
    RequestParameterInvalidException,
)
from galaxy.files.models import (
    AnyRemoteEntry,
    BaseFileSourceConfiguration,
    BaseFileSourceTemplateConfiguration,
    Entry,
    EntryData,
    FilesSourceRuntimeContext,
    RemoteDirectory,
    RemoteFile,
)
from galaxy.util.config_templates import TemplateExpansion
from . import BaseFilesSource

AccessTokenField = Field(
    ...,
    title="Access Token",
    description="The OAuth2 access token for Microsoft Graph.",
    validation_alias=AliasChoices("oauth2_access_token", "accessToken", "access_token"),
)


class OneDriveFileSourceTemplateConfiguration(BaseFileSourceTemplateConfiguration):
    access_token: Annotated[Union[str, TemplateExpansion], AccessTokenField]
    drive_api_base: Union[str, TemplateExpansion] = "https://graph.microsoft.com/v1.0/me/drive"


class OneDriveFilesSourceConfiguration(BaseFileSourceConfiguration):
    access_token: Annotated[str, AccessTokenField]
    drive_api_base: str = "https://graph.microsoft.com/v1.0/me/drive"


class OneDriveFilesSource(
    BaseFilesSource[OneDriveFileSourceTemplateConfiguration, OneDriveFilesSourceConfiguration]
):
    plugin_type = "onedrive"

    template_config_class = OneDriveFileSourceTemplateConfiguration
    resolved_config_class = OneDriveFilesSourceConfiguration

    def _headers(self, config: OneDriveFilesSourceConfiguration) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {config.access_token}",
        }

    def _json_headers(self, config: OneDriveFilesSourceConfiguration) -> dict[str, str]:
        headers = self._headers(config)
        headers["Content-Type"] = "application/json"
        return headers

    def _encoded_path(self, path: str) -> str:
        normalized = path.strip("/")
        if not normalized:
            return ""
        return "/".join(quote(component, safe="") for component in normalized.split("/"))

    def _item_url(self, config: OneDriveFilesSourceConfiguration, path: str) -> str:
        api_base = config.drive_api_base.rstrip("/")
        encoded_path = self._encoded_path(path)
        if encoded_path:
            return f"{api_base}/special/approot:/{encoded_path}"
        return f"{api_base}/special/approot"

    def _children_url(self, config: OneDriveFilesSourceConfiguration, path: str) -> str:
        item_url = self._item_url(config, path)
        if path.strip("/"):
            return f"{item_url}:/children"
        return f"{item_url}/children"

    def _content_url(self, config: OneDriveFilesSourceConfiguration, path: str) -> str:
        return f"{self._item_url(config, path)}:/content" if path.strip("/") else f"{self._item_url(config, path)}/content"

    def _request(
        self,
        method: str,
        url: str,
        context: FilesSourceRuntimeContext[OneDriveFilesSourceConfiguration],
        **kwargs,
    ) -> requests.Response:
        try:
            response = requests.request(method, url, headers=self._headers(context.config), timeout=30, **kwargs)
        except requests.RequestException as exc:
            raise MessageException(f"Error connecting to OneDrive. Reason: {exc}") from exc

        if response.status_code in {401, 403}:
            raise AuthenticationRequired(
                "Permission denied while accessing OneDrive. Check the Microsoft app registration, granted scopes, and the stored user authorization."
            )
        if response.status_code == 404:
            raise RequestParameterInvalidException(f"Path not found in OneDrive: {url}")
        if not response.ok:
            try:
                payload = response.json()
                message = payload.get("error", {}).get("message", response.text)
            except Exception:
                message = response.text
            raise MessageException(f"Error communicating with OneDrive. Reason: {message}")
        return response

    def _entry_from_item(
        self,
        item: dict,
        parent_path: str,
    ) -> AnyRemoteEntry:
        relative_parent = parent_path.rstrip("/")
        relative_path = f"{relative_parent}/{item['name']}".replace("//", "/")
        if not relative_path.startswith("/"):
            relative_path = f"/{relative_path}"
        uri = self.uri_from_path(relative_path)
        if "folder" in item:
            return RemoteDirectory(
                name=item["name"],
                uri=uri,
                path=relative_path,
            )
        return RemoteFile(
            name=item["name"],
            uri=uri,
            path=relative_path,
            size=item.get("size", 0),
            ctime=item.get("lastModifiedDateTime"),
        )

    def _list(
        self,
        context: FilesSourceRuntimeContext[OneDriveFilesSourceConfiguration],
        path: str = "/",
        recursive: bool = False,
        write_intent: bool = False,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        query: Optional[str] = None,
        sort_by: Optional[str] = None,
    ) -> tuple[list[AnyRemoteEntry], int]:
        response = self._request("GET", self._children_url(context.config, path), context)
        items = response.json().get("value", [])
        entries = [self._entry_from_item(item, path) for item in items]
        return entries, len(entries)

    def _realize_to(
        self, source_path: str, native_path: str, context: FilesSourceRuntimeContext[OneDriveFilesSourceConfiguration]
    ):
        response = self._request("GET", self._content_url(context.config, source_path), context, stream=True)
        with open(native_path, "wb") as out:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    out.write(chunk)

    def _write_from(
        self, target_path: str, native_path: str, context: FilesSourceRuntimeContext[OneDriveFilesSourceConfiguration]
    ) -> str:
        upload_url = self._content_url(context.config, target_path)
        with open(native_path, "rb") as handle:
            response = requests.put(
                upload_url,
                headers={"Authorization": f"Bearer {context.config.access_token}", "Content-Type": "application/octet-stream"},
                data=handle,
                timeout=300,
            )
        if response.status_code in {401, 403}:
            raise AuthenticationRequired(
                "Permission denied while writing to OneDrive. Check the Microsoft app scopes and stored user authorization."
            )
        if not response.ok:
            try:
                payload = response.json()
                message = payload.get("error", {}).get("message", response.text)
            except Exception:
                message = response.text
            raise MessageException(f"Error uploading to OneDrive. Reason: {message}")
        return self.uri_from_path(target_path)

    def _create_entry(
        self, entry_data: EntryData, context: FilesSourceRuntimeContext[OneDriveFilesSourceConfiguration]
    ) -> Entry:
        parent_path = getattr(entry_data, "path", None)
        if parent_path is None:
            target = getattr(entry_data, "target", "/")
            parent_path = self.to_relative_path(target)
        payload = {
            "name": entry_data.name,
            "folder": {},
            "@microsoft.graph.conflictBehavior": "fail",
        }
        response = requests.post(
            self._children_url(context.config, parent_path),
            json=payload,
            headers=self._json_headers(context.config),
            timeout=30,
        )
        if response.status_code in {401, 403}:
            raise AuthenticationRequired(
                "Permission denied while creating a OneDrive folder. Check the Microsoft app scopes and stored user authorization."
            )
        if not response.ok:
            try:
                body = response.json()
                message = body.get("error", {}).get("message", response.text)
            except Exception:
                message = response.text
            raise MessageException(f"Error creating OneDrive folder. Reason: {message}")
        item = response.json()
        path = self._entry_from_item(item, parent_path).path
        return Entry(name=item["name"], uri=self.uri_from_path(path), external_link=item.get("webUrl"))


__all__ = ("OneDriveFilesSource",)
