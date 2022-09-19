from unittest import SkipTest

from galaxy.tool_util.verify.interactor import GalaxyInteractorApi
from galaxy.util import unicodify
from galaxy_test.base.api_asserts import assert_status_code_is


class UsesShedApi:
    @property
    def galaxy_interactor(self) -> GalaxyInteractorApi:
        ...

    def delete_repo_request(self, payload):
        return self.galaxy_interactor._delete("tool_shed_repositories", data=payload, admin=True)

    def install_repo_request(self, payload):
        return self.galaxy_interactor._post(
            "tool_shed_repositories/new/install_repository_revision", data=payload, admin=True
        )

    def repository_operation(self, operation, owner, name, changeset, tool_shed_url="https://toolshed.g2.bx.psu.edu"):
        payload = {"tool_shed_url": tool_shed_url, "name": name, "owner": owner, "changeset_revision": changeset}
        create_response = operation(payload)
        assert_status_code_is(create_response, 200)
        return create_response.json()

    def install_repository(self, owner, name, changeset, tool_shed_url="https://toolshed.g2.bx.psu.edu"):
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

    def uninstall_repository(self, owner, name, changeset, tool_shed_url="https://toolshed.g2.bx.psu.edu"):
        return self.repository_operation(
            operation=self.delete_repo_request, owner=owner, name=name, changeset=changeset, tool_shed_url=tool_shed_url
        )
