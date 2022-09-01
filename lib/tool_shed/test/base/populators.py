from typing import (
    Any,
    Dict,
    Union,
)

import requests

from galaxy.util.resources import (
    resource_path,
    Traversable,
)
from galaxy_test.base import api_asserts
from galaxy_test.base.api_util import random_name
from tool_shed_client.schema import (
    Category,
    GetOrderedInstallableRevisionsRequest,
    OrderedInstallableRevisions,
    Repository,
    RepositoryMetadata,
    RepositoryUpdate,
    ResetMetadataOnRepositoryRequest,
    ResetMetadataOnRepositoryResponse,
)
from .api_util import ShedApiInteractor

HasRepositoryId = Union[str, Repository]

DEFAULT_PREFIX = "repofortest"
COLUMN_MAKER_PATH = resource_path(__package__, "../test_data/column_maker/column_maker.tar")
COLUMN_MAKER_1_1_1_PATH = resource_path(__package__, "../test_data/column_maker/column_maker.tar")
DEFAULT_COMMIT_MESSAGE = "a test commit message"


class ToolShedPopulator:
    """Utilities for easy fixture creation of tool shed related things."""

    _admin_api_interactor: ShedApiInteractor
    _api_interactor: ShedApiInteractor

    def __init__(self, admin_api_interactor: ShedApiInteractor, api_interactor: ShedApiInteractor):
        self._admin_api_interactor = admin_api_interactor
        self._api_interactor = api_interactor

    def setup_column_maker_repo(self, prefix=DEFAULT_PREFIX) -> Repository:
        category_id = self.new_category(prefix=prefix).id
        repository = self.new_repository(category_id, prefix=prefix)
        repository_id = repository.id
        assert repository_id

        response = self.upload_revision(
            repository_id,
            COLUMN_MAKER_PATH,
        )
        assert response.is_ok
        return repository

    def setup_column_maker_and_get_metadata(self, prefix=DEFAULT_PREFIX) -> RepositoryMetadata:
        repository = self.setup_column_maker_repo(prefix=prefix)
        return self.get_metadata(repository)

    def update_column_maker_repo(self, repository: HasRepositoryId) -> requests.Response:
        response = self.upload_revision(
            repository,
            COLUMN_MAKER_1_1_1_PATH,
        )
        return response

    def upload_revision_raw(
        self, repository: HasRepositoryId, path: Traversable, commit_message: str = DEFAULT_COMMIT_MESSAGE
    ) -> requests.Response:
        body = {
            "commit_message": commit_message,
        }
        files = {"file": path.open("rb")}
        repository_id = self._repository_id(repository)
        response = self._api_interactor.post(f"repositories/{repository_id}/changeset_revision", json=body, files=files)
        return response

    def upload_revision(
        self, repository: HasRepositoryId, path: Traversable, commit_message: str = DEFAULT_COMMIT_MESSAGE
    ):
        response = self.upload_revision_raw(repository, path, commit_message)
        api_asserts.assert_status_code_is_ok(response)
        return RepositoryUpdate(__root__=response.json())

    def new_repository(self, category_id, prefix=DEFAULT_PREFIX) -> Repository:
        name = random_name(prefix=prefix)
        synopsis = random_name(prefix=prefix)
        description = None
        remote_repository_url = None
        homepage_url = None
        category_ids = category_id
        type = "unrestricted"
        body = {
            "name": name,
            "synopsis": synopsis,
            "description": description,
            "remote_repository_url": remote_repository_url,
            "homepage_url": homepage_url,
            "category_ids[]": category_ids,
            "type": type,
        }
        response = self._api_interactor.post("repositories", json=body)
        api_asserts.assert_status_code_is_ok(response)
        return Repository(**response.json())

    def new_category(self, prefix=DEFAULT_PREFIX) -> Category:
        name = random_name(prefix=prefix)
        body = {"name": name, "description": "testcreaterepo"}
        response = self._admin_api_interactor.post("categories", json=body)
        response.raise_for_status()
        return Category(**response.json())

    def get_ordered_installable_revisions(self, owner: str, name: str) -> OrderedInstallableRevisions:
        request = GetOrderedInstallableRevisionsRequest(owner=owner, name=name)
        revisions_response = self._api_interactor.get(
            "repositories/get_ordered_installable_revisions", params=request.dict()
        )
        api_asserts.assert_status_code_is_ok(revisions_response)
        return OrderedInstallableRevisions(__root__=revisions_response.json())

    def get_metadata(self, repository: HasRepositoryId) -> RepositoryMetadata:
        repository_id = self._repository_id(repository)
        metadata_response = self._api_interactor.get(f"repositories/{repository_id}/metadata")
        api_asserts.assert_status_code_is_ok(metadata_response)
        return RepositoryMetadata(__root__=metadata_response.json())

    def reset_metadata(self, repository: HasRepositoryId) -> ResetMetadataOnRepositoryResponse:
        repository_id = self._repository_id(repository)
        request = ResetMetadataOnRepositoryRequest(repository_id=repository_id)
        reset_response = self._api_interactor.post("repositories/reset_metadata_on_repository", json=request.dict())
        api_asserts.assert_status_code_is_ok(reset_response)
        return ResetMetadataOnRepositoryResponse(**reset_response.json())

    def guid(self, repository: Repository, tool_id: str, tool_version: str) -> str:
        url = self._api_interactor.url
        base = url.split("://")[1].split("/")[0]
        return f"{base}/repos/{repository.owner}/{repository.name}/{tool_id}/{tool_version}"

    def _repository_id(self, has_id: HasRepositoryId) -> str:
        if isinstance(has_id, Repository):
            return has_id.id
        else:
            return str(has_id)
