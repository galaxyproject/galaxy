import tarfile
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import (
    Iterator,
    List,
    Optional,
    Union,
)

import requests
from typing_extensions import Protocol

from galaxy.util.resources import (
    as_file,
    resource_path,
    Traversable,
)
from galaxy_test.base import api_asserts
from galaxy_test.base.api_util import random_name
from tool_shed_client.schema import (
    BuildSearchIndexResponse,
    Category,
    CreateCategoryRequest,
    CreateRepositoryRequest,
    DetailedRepository,
    from_legacy_install_info,
    GetInstallInfoRequest,
    GetOrderedInstallableRevisionsRequest,
    InstallInfo,
    OrderedInstallableRevisions,
    RepositoriesByCategory,
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
    UpdateRepositoryRequest,
    Version,
)
from .api_util import (
    ensure_user_with_email,
    ShedApiInteractor,
)

HasRepositoryId = Union[str, Repository]

DEFAULT_PREFIX = "repofortest"
TEST_DATA_REPO_FILES = resource_path(__name__, "../test_data")
COLUMN_MAKER_PATH = TEST_DATA_REPO_FILES.joinpath("column_maker/column_maker.tar")
COLUMN_MAKER_1_1_1_PATH = TEST_DATA_REPO_FILES.joinpath("column_maker/column_maker_1.1.1.tar")
DEFAULT_COMMIT_MESSAGE = "a test commit message"


def repo_files(test_data_path: str) -> Iterator[Path]:
    repos = TEST_DATA_REPO_FILES.joinpath(f"repos/{test_data_path}")
    for child in sorted(_.name for _ in repos.iterdir()):
        with as_file(repos.joinpath(child)) as path:
            yield path


def repo_tars(test_data_path: str) -> Iterator[Path]:
    for path in repo_files(test_data_path):
        assert path.is_dir()
        prefix = f"shedtest_{test_data_path}_{path.name}_"
        with NamedTemporaryFile(prefix=prefix) as tf:
            with tarfile.open(tf.name, "w:gz") as tar:
                tar.add(str(path.absolute()), arcname=test_data_path or path.name)
            yield Path(tf.name)


class HostsTestToolShed(Protocol):
    host: str
    port: Optional[str]


class ToolShedPopulator:
    """Utilities for easy fixture creation of tool shed related things."""

    _admin_api_interactor: ShedApiInteractor
    _api_interactor: ShedApiInteractor

    def __init__(self, admin_api_interactor: ShedApiInteractor, api_interactor: ShedApiInteractor):
        self._admin_api_interactor = admin_api_interactor
        self._api_interactor = api_interactor

    def setup_bismark_repo(
        self,
        repository_id: Optional[HasRepositoryId] = None,
        end: Optional[int] = None,
        category_id: Optional[str] = None,
    ) -> HasRepositoryId:
        if repository_id is None:
            category_id = category_id or self.new_category(prefix="testbismark").id
            repository_id = self.new_repository(category_id, prefix="testbismark")
        return self.setup_test_data_repo_by_id("bismark", repository_id, assert_ok=False, end=end)

    def setup_test_data_repo_by_id(
        self,
        test_data_path: str,
        repository_id: Optional[HasRepositoryId] = None,
        assert_ok=True,
        start: int = 0,
        end: Optional[int] = None,
    ) -> HasRepositoryId:
        if repository_id is None:
            prefix = test_data_path.replace("_", "")
            category_id = self.new_category(prefix=prefix).id
            repository = self.new_repository(category_id, prefix=prefix)
            repository_id = repository.id

        assert repository_id

        for index, repo_tar in enumerate(repo_tars(test_data_path)):
            if index < start:
                continue

            if end and index >= end:
                break

            commit_message = f"Updating {test_data_path} with index {index} with tar {repo_tar}"
            response = self.upload_revision_raw(repository_id, repo_tar, commit_message)
            if assert_ok:
                api_asserts.assert_status_code_is_ok(response)
                assert RepositoryUpdate(root=response.json()).is_ok
        return repository_id

    def setup_test_data_repo(
        self,
        test_data_path: str,
        repository: Optional[Repository] = None,
        assert_ok=True,
        start: int = 0,
        end: Optional[int] = None,
        category_id: Optional[str] = None,
    ) -> Repository:
        if repository is None:
            prefix = test_data_path.replace("_", "")
            if category_id is None:
                category_id = self.new_category(prefix=prefix).id
            repository = self.new_repository(category_id, prefix=prefix)
        self.setup_test_data_repo_by_id(test_data_path, repository, assert_ok=assert_ok, start=start, end=end)
        return repository

    def setup_column_maker_repo(
        self,
        prefix=DEFAULT_PREFIX,
        category_id: Optional[str] = None,
    ) -> Repository:
        if category_id is None:
            category_id = self.new_category(prefix=prefix).id
        assert category_id
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

    def get_install_info_for_repository(self, has_repository_id: HasRepositoryId) -> InstallInfo:
        repository_id = self._repository_id(has_repository_id)
        metadata = self.get_metadata(repository_id, True)
        return self.get_install_info(metadata)

    def get_install_info(self, repository_metadata: RepositoryMetadata) -> InstallInfo:
        revision_metadata = repository_metadata.latest_revision
        repo = revision_metadata.repository
        request = GetInstallInfoRequest(
            owner=repo.owner,
            name=repo.name,
            changeset_revision=revision_metadata.changeset_revision,
        )
        revisions_response = self._api_interactor.get(
            "repositories/get_repository_revision_install_info", params=request.model_dump()
        )
        api_asserts.assert_status_code_is_ok(revisions_response)
        return from_legacy_install_info(revisions_response.json())

    def update_column_maker_repo(self, repository: HasRepositoryId) -> RepositoryUpdate:
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
            f"repositories/{repository_id}/changeset_revision", params=body.model_dump(), files=files
        )
        return response

    def update_raw(self, repository: HasRepositoryId, request: UpdateRepositoryRequest) -> requests.Response:
        repository_id = self._repository_id(repository)
        body_json = request.model_dump(exclude_unset=True, by_alias=True)
        put_response = self._api_interactor.put(f"repositories/{repository_id}", json=body_json)
        return put_response

    def update(self, repository: HasRepositoryId, request: UpdateRepositoryRequest) -> Repository:
        response = self.update_raw(repository, request)
        api_asserts.assert_status_code_is_ok(response)
        return Repository(**response.json())

    def upload_revision(
        self, repository: HasRepositoryId, path: Traversable, commit_message: str = DEFAULT_COMMIT_MESSAGE
    ) -> RepositoryUpdate:
        response = self.upload_revision_raw(repository, path, commit_message=commit_message)
        if response.status_code != 200:
            response_json = None
            err_msg = None
            try:
                response_json = response.json()
            except Exception:
                pass
            if response_json and "err_msg" in response_json:
                err_msg = response_json["err_msg"]
            if err_msg and "No changes" in err_msg:
                assert_msg = f"Updating repository [{repository}] with path [{path}] and commit_message {commit_message} failed to update repository contents, no changes found. Response: [{response_json}]"
                raise AssertionError(assert_msg)
            api_asserts.assert_status_code_is_ok(response)
        return RepositoryUpdate(root=response.json())

    def new_repository(self, category_ids: Union[List[str], str], prefix: str = DEFAULT_PREFIX) -> Repository:
        name = random_name(prefix=prefix)
        synopsis = random_name(prefix=prefix)
        request = CreateRepositoryRequest(
            name=name,
            synopsis=synopsis,
            category_ids=category_ids,
        )
        return self.create_repository(request)

    def create_repository(self, request: CreateRepositoryRequest) -> Repository:
        response = self._api_interactor.post("repositories", json=request.model_dump(by_alias=True))
        api_asserts.assert_status_code_is_ok(response)
        return Repository(**response.json())

    def reindex(self) -> BuildSearchIndexResponse:
        index_response = self._admin_api_interactor.put("tools/build_search_index")
        index_response.raise_for_status()
        return BuildSearchIndexResponse(**index_response.json())

    def new_category(
        self, name: Optional[str] = None, description: Optional[str] = None, prefix=DEFAULT_PREFIX
    ) -> Category:
        category_name = name or random_name(prefix=prefix)
        category_description = description or "testcreaterepo"
        request = CreateCategoryRequest(name=category_name, description=category_description)
        response = self._admin_api_interactor.post("categories", json=request.model_dump())
        response.raise_for_status()
        return Category(**response.json())

    def get_categories(self) -> List[Category]:
        response = self._api_interactor.get("categories")
        response.raise_for_status()
        return [Category(**c) for c in response.json()]

    def get_category_with_id(self, category_id: str) -> Category:
        response = self._api_interactor.get(f"categories/{category_id}")
        response.raise_for_status()
        return Category(**response.json())

    def get_category_with_name(self, name: str) -> Category:
        categories = [c for c in self.get_categories() if c.name == name]
        if not categories:
            raise ValueError(f"No category with name {name} found.")
        return categories[0]

    def repositories_by_category(self, category_id: str) -> RepositoriesByCategory:
        response = self._api_interactor.get(f"categories/{category_id}/repositories")
        response.raise_for_status()
        return RepositoriesByCategory(**response.json())

    def assert_category_has_n_repositories(self, category_id: str, n: int):
        category_repos = self.repositories_by_category(category_id)
        assert category_repos.repository_count == n
        assert len(category_repos.repositories) == n

    def get_ordered_installable_revisions(self, owner: str, name: str) -> OrderedInstallableRevisions:
        request = GetOrderedInstallableRevisionsRequest(owner=owner, name=name)
        revisions_response = self._api_interactor.get(
            "repositories/get_ordered_installable_revisions", params=request.model_dump()
        )
        api_asserts.assert_status_code_is_ok(revisions_response)
        return OrderedInstallableRevisions(root=revisions_response.json())

    def assert_has_n_installable_revisions(self, repository: Repository, n: int):
        revisions = self.get_ordered_installable_revisions(repository.owner, repository.name)
        actual_n = len(revisions.root)
        assert actual_n == n, f"Expected {n} repository revisions, found {actual_n} for {repository}"

    def get_repository_for(self, owner: str, name: str, deleted: str = "false") -> Optional[Repository]:
        request = RepositoryIndexRequest(
            owner=owner,
            name=name,
            deleted=deleted,
        )
        index = self.repository_index(request)
        return index.root[0] if index.root else None

    def repository_index(self, request: Optional[RepositoryIndexRequest]) -> RepositoryIndexResponse:
        repository_response = self._api_interactor.get("repositories", params=(request.model_dump() if request else {}))
        api_asserts.assert_status_code_is_ok(repository_response)
        return RepositoryIndexResponse(root=repository_response.json())

    def get_usernames_allowed_to_push(self, repository: HasRepositoryId) -> List[str]:
        repository_id = self._repository_id(repository)
        show_response = self._api_interactor.get(f"repositories/{repository_id}/allow_push")
        show_response.raise_for_status()
        as_list = show_response.json()
        assert isinstance(as_list, list)
        return as_list

    def allow_user_to_push(self, repository: HasRepositoryId, username: str) -> None:
        repository_id = self._repository_id(repository)
        post_response = self._api_interactor.post(f"repositories/{repository_id}/allow_push/{username}")
        post_response.raise_for_status()

    def disallow_user_to_push(self, repository: HasRepositoryId, username: str) -> None:
        repository_id = self._repository_id(repository)
        delete_response = self._api_interactor.delete(f"repositories/{repository_id}/allow_push/{username}")
        delete_response.raise_for_status()

    def set_malicious(self, repository: HasRepositoryId, changeset_revision: str):
        repository_id = self._repository_id(repository)
        put_response = self._api_interactor.put(
            f"repositories/{repository_id}/revisions/{changeset_revision}/malicious"
        )
        put_response.raise_for_status()

    def unset_malicious(self, repository: HasRepositoryId, changeset_revision: str):
        repository_id = self._repository_id(repository)
        delete_response = self._api_interactor.delete(
            f"repositories/{repository_id}/revisions/{changeset_revision}/malicious"
        )
        delete_response.raise_for_status()

    def tip_is_malicious(self, repository: HasRepositoryId) -> bool:
        repository_metadata = self.get_metadata(repository)
        revision = repository_metadata.latest_revision
        return revision.malicious

    def set_deprecated(self, repository: HasRepositoryId):
        repository_id = self._repository_id(repository)
        put_response = self._api_interactor.put(f"repositories/{repository_id}/deprecated")
        put_response.raise_for_status()

    def unset_deprecated(self, repository: HasRepositoryId):
        repository_id = self._repository_id(repository)
        delete_response = self._api_interactor.delete(f"repositories/{repository_id}/deprecated")
        delete_response.raise_for_status()

    def get_repository(self, repository: HasRepositoryId) -> DetailedRepository:
        repository_id = self._repository_id(repository)
        repository_response = self._api_interactor.get(f"repositories/{repository_id}")
        repository_response.raise_for_status()
        return DetailedRepository(**repository_response.json())

    def is_deprecated(self, repository: HasRepositoryId) -> bool:
        return self.get_repository(repository).deprecated

    def get_metadata(self, repository: HasRepositoryId, downloadable_only=True) -> RepositoryMetadata:
        repository_id = self._repository_id(repository)
        metadata_response = self._api_interactor.get(
            f"repositories/{repository_id}/metadata?downloadable_only={downloadable_only}"
        )
        api_asserts.assert_status_code_is_ok(metadata_response)
        return RepositoryMetadata(root=metadata_response.json())

    def reset_metadata(self, repository: HasRepositoryId) -> ResetMetadataOnRepositoryResponse:
        repository_id = self._repository_id(repository)
        request = ResetMetadataOnRepositoryRequest(repository_id=repository_id)
        reset_response = self._api_interactor.post(
            "repositories/reset_metadata_on_repository", json=request.model_dump()
        )
        api_asserts.assert_status_code_is_ok(reset_response)
        return ResetMetadataOnRepositoryResponse(**reset_response.json())

    def version(self) -> Version:
        version_response = self._admin_api_interactor.get("version")
        api_asserts.assert_status_code_is_ok(version_response)
        return Version(**version_response.json())

    def tool_search_query(self, query: str) -> ToolSearchResults:
        return self.tool_search(ToolSearchRequest(q=query))

    def tool_search(self, search_request: ToolSearchRequest) -> ToolSearchResults:
        search_response = self._api_interactor.get("tools", params=search_request.model_dump())
        api_asserts.assert_status_code_is_ok(search_response)
        return ToolSearchResults(**search_response.json())

    def tool_guid(
        self, shed_host: HostsTestToolShed, repository: Repository, tool_id: str, tool_version: Optional[str] = None
    ) -> str:
        owner = repository.owner
        name = repository.name
        port = shed_host.port
        if port in [None, "80", "443"]:
            host_and_port = shed_host.host
        else:
            host_and_port = f"{shed_host.host}:{shed_host.port}"
        tool_id_base = f"{host_and_port}/repos/{owner}/{name}/{tool_id}"
        if tool_version is None:
            return tool_id_base
        else:
            return f"{tool_id_base}/{tool_version}"

    def repo_search_query(self, query: str) -> RepositorySearchResults:
        return self.repo_search(RepositorySearchRequest(q=query))

    def repo_search(self, repo_search_request: RepositorySearchRequest) -> RepositorySearchResults:
        search_response = self._api_interactor.get("repositories", params=repo_search_request.model_dump())
        api_asserts.assert_status_code_is_ok(search_response)
        return RepositorySearchResults(**search_response.json())

    def delete_api_key(self) -> None:
        response = self._api_interactor.delete("users/current/api_key")
        response.raise_for_status()

    def create_new_api_key(self) -> str:
        response = self._api_interactor.post("users/current/api_key")
        response.raise_for_status()
        return response.json()

    def guid(self, repository: Repository, tool_id: str, tool_version: str) -> str:
        url = self._api_interactor.url
        base = url.split("://")[1].split("/")[0]
        return f"{base}/repos/{repository.owner}/{repository.name}/{tool_id}/{tool_version}"

    def new_user(self, username: str, password: str):
        return ensure_user_with_email(self._admin_api_interactor, username, password)

    def _repository_id(self, has_id: HasRepositoryId) -> str:
        if isinstance(has_id, Repository):
            return has_id.id
        else:
            return str(has_id)
