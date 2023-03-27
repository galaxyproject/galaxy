from typing import (
    List,
    Optional,
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
    CreateCategoryRequest,
    CreateRepositoryRequest,
    from_legacy_install_info,
    GetInstallInfoRequest,
    GetOrderedInstallableRevisionsRequest,
    InstallInfo,
    OrderedInstallableRevisions,
    Repository,
    RepositoryIndexRequest,
    RepositoryIndexResponse,
    RepositoryMetadata,
    RepositorySearchRequest,
    RepositorySearchResults,
    RepositoryUpdate,
    RepositoryUpdateRequest,
    ResetMetadataOnRepositoryRequest,
    ResetMetadataOnRepositoryResponse,
    ToolSearchRequest,
    ToolSearchResults,
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

    def get_install_info(self, repository_metadata: RepositoryMetadata) -> InstallInfo:
        revision_metadata = repository_metadata.latest_revision
        repo = revision_metadata.repository
        request = GetInstallInfoRequest(
            owner=repo.owner,
            name=repo.name,
            changeset_revision=revision_metadata.changeset_revision,
        )
        revisions_response = self._api_interactor.get(
            "repositories/get_repository_revision_install_info", params=request.dict()
        )
        api_asserts.assert_status_code_is_ok(revisions_response)
        return from_legacy_install_info(revisions_response.json())

    def update_column_maker_repo(self, repository: HasRepositoryId) -> requests.Response:
        response = self.upload_revision(
            repository,
            COLUMN_MAKER_1_1_1_PATH,
        )
        return response

    def upload_revision_raw(
        self, repository: HasRepositoryId, path: Traversable, commit_message: str = DEFAULT_COMMIT_MESSAGE
    ) -> requests.Response:
        body = RepositoryUpdateRequest(
            commit_message=commit_message,
        )
        files = {"file": path.open("rb")}
        repository_id = self._repository_id(repository)
        response = self._api_interactor.post(
            f"repositories/{repository_id}/changeset_revision", params=body.dict(), files=files
        )
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
        request = CreateRepositoryRequest(
            name=name,
            synopsis=synopsis,
            category_ids=category_id,
        )
        return self.create_repository(request)

    def create_repository(self, request: CreateRepositoryRequest) -> Repository:
        response = self._api_interactor.post("repositories", json=request.dict(by_alias=True))
        api_asserts.assert_status_code_is_ok(response)
        return Repository(**response.json())

    def reindex(self):
        index_response = self._admin_api_interactor.put("tools/build_search_index")
        index_response.raise_for_status()

    def new_category(
        self, name: Optional[str] = None, description: Optional[str] = None, prefix=DEFAULT_PREFIX
    ) -> Category:
        category_name = name or random_name(prefix=prefix)
        category_description = description or "testcreaterepo"
        request = CreateCategoryRequest(name=category_name, description=category_description)
        response = self._admin_api_interactor.post("categories", json=request.dict())
        response.raise_for_status()
        return Category(**response.json())

    def get_categories(self) -> List[Category]:
        response = self._api_interactor.get("categories")
        response.raise_for_status()
        return [Category(**c) for c in response.json()]

    def get_category_with_name(self, name: str) -> Optional[Category]:
        response = self._api_interactor.get("categories")
        response.raise_for_status()
        categories = [c for c in self.get_categories() if c.name == name]
        return categories[0] if categories else None

    def has_category_with_name(self, name: str) -> bool:
        return self.get_category_with_name(name) is not None

    def get_ordered_installable_revisions(self, owner: str, name: str) -> OrderedInstallableRevisions:
        request = GetOrderedInstallableRevisionsRequest(owner=owner, name=name)
        revisions_response = self._api_interactor.get(
            "repositories/get_ordered_installable_revisions", params=request.dict()
        )
        api_asserts.assert_status_code_is_ok(revisions_response)
        return OrderedInstallableRevisions(__root__=revisions_response.json())

    def get_repository_for(self, owner: str, name: str, deleted: str = "false") -> Optional[Repository]:
        request = RepositoryIndexRequest(
            owner=owner,
            name=name,
            deleted=deleted,
        )
        index = self.repository_index(request)
        return index.__root__[0] if index.__root__ else None

    def repository_index(self, request: Optional[RepositoryIndexRequest]) -> RepositoryIndexResponse:
        repository_response = self._api_interactor.get("repositories", params=(request.dict() if request else {}))
        api_asserts.assert_status_code_is_ok(repository_response)
        return RepositoryIndexResponse(__root__=repository_response.json())

    def get_metadata(self, repository: HasRepositoryId, downloadable_only=True) -> RepositoryMetadata:
        repository_id = self._repository_id(repository)
        metadata_response = self._api_interactor.get(
            f"repositories/{repository_id}/metadata?downloadable_only={downloadable_only}"
        )
        api_asserts.assert_status_code_is_ok(metadata_response)
        return RepositoryMetadata(__root__=metadata_response.json())

    def reset_metadata(self, repository: HasRepositoryId) -> ResetMetadataOnRepositoryResponse:
        repository_id = self._repository_id(repository)
        request = ResetMetadataOnRepositoryRequest(repository_id=repository_id)
        reset_response = self._api_interactor.post("repositories/reset_metadata_on_repository", json=request.dict())
        api_asserts.assert_status_code_is_ok(reset_response)
        return ResetMetadataOnRepositoryResponse(**reset_response.json())

    def tool_search_query(self, query: str) -> ToolSearchResults:
        return self.tool_search(ToolSearchRequest(q=query))

    def tool_search(self, search_request: ToolSearchRequest) -> ToolSearchResults:
        search_response = self._api_interactor.get("tools", params=search_request.dict())
        api_asserts.assert_status_code_is_ok(search_response)
        return ToolSearchResults(**search_response.json())

    def repo_search_query(self, query: str) -> RepositorySearchResults:
        return self.repo_search(RepositorySearchRequest(q=query))

    def repo_search(self, repo_search_request: RepositorySearchRequest) -> RepositorySearchResults:
        search_response = self._api_interactor.get("repositories", params=repo_search_request.dict())
        api_asserts.assert_status_code_is_ok(search_response)
        return RepositorySearchResults(**search_response.json())

    def guid(self, repository: Repository, tool_id: str, tool_version: str) -> str:
        url = self._api_interactor.url
        base = url.split("://")[1].split("/")[0]
        return f"{base}/repos/{repository.owner}/{repository.name}/{tool_id}/{tool_version}"

    def _repository_id(self, has_id: HasRepositoryId) -> str:
        if isinstance(has_id, Repository):
            return has_id.id
        else:
            return str(has_id)
