import abc
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
)
from unittest import SkipTest

from requests import Response

from galaxy.tool_util.verify.interactor import GalaxyInteractorApi
from galaxy.util import unicodify
from galaxy_test.base.api_asserts import assert_status_code_is

DEFAULT_TOOL_SHED_URL = "https://toolshed.g2.bx.psu.edu"

OperationT = Callable[[Dict[str, Any]], Response]


class UsesShedApi:
    @property
    @abc.abstractmethod
    def galaxy_interactor(self) -> GalaxyInteractorApi:
        ...

    def delete_repo_request(self, payload: Dict[str, Any]) -> Response:
        return self.galaxy_interactor._delete("tool_shed_repositories", data=payload, admin=True)

    def install_repo_request(self, payload: Dict[str, Any]) -> Response:
        return self.galaxy_interactor._post(
            "tool_shed_repositories/new/install_repository_revision", data=payload, admin=True
        )

    def repository_operation(
        self, operation: OperationT, owner: str, name: str, changeset: str, tool_shed_url: str = DEFAULT_TOOL_SHED_URL
    ) -> Dict[str, Any]:
        payload = {"tool_shed_url": tool_shed_url, "name": name, "owner": owner, "changeset_revision": changeset}
        create_response = operation(payload)
        assert_status_code_is(create_response, 200)
        return create_response.json()

    def install_repository(
        self, owner: str, name: str, changeset: str, tool_shed_url: str = DEFAULT_TOOL_SHED_URL
    ) -> Dict[str, Any]:
        try:
            return self.repository_operation(
                operation=self.install_repo_request,
                owner=owner,
                name=name,
                changeset=changeset,
                tool_shed_url=tool_shed_url,
            )
        except AssertionError as e:
            if "Error attempting to retrieve installation information from tool shed" in unicodify(e):
                raise SkipTest(f"Toolshed '{tool_shed_url}' unavailable")
            raise

    def uninstall_repository(
        self, owner: str, name: str, changeset: str, tool_shed_url: str = DEFAULT_TOOL_SHED_URL
    ) -> Dict[str, Any]:
        return self.repository_operation(
            operation=self.delete_repo_request, owner=owner, name=name, changeset=changeset, tool_shed_url=tool_shed_url
        )

    def index_repositories(
        self, owner: Optional[str] = None, name: Optional[str] = None, changeset: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        params: Dict[str, str] = {}
        if owner is not None:
            params["owner"] = owner
        if name is not None:
            params["name"] = name
        if changeset is not None:
            params["changeset"] = changeset
        params["deleted"] = "false"
        params["uninstalled"] = "false"
        response = self.galaxy_interactor._get("tool_shed_repositories", params, admin=True)
        response.raise_for_status()
        return response.json()

    def get_installed_repository_for(
        self, owner: Optional[str] = None, name: Optional[str] = None, changeset: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        index = self.index_repositories(owner, name, changeset)
        if len(index) == 0:
            return None
        elif len(index) > 1:
            raise AssertionError(f"expected at most one repository in response {index}")
        else:
            return index[0]

    def get_installed_repository(self, id: str) -> Dict[str, Any]:
        response = self.galaxy_interactor._get(f"tool_shed_repositories/{id}", admin=True)
        response.raise_for_status()
        return response.json()
