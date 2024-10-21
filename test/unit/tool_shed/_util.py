import os
import random
import string
import tarfile
from pathlib import Path
from tempfile import (
    mkdtemp,
    NamedTemporaryFile,
)
from typing import (
    Any,
    Dict,
    Optional,
)

import tool_shed.repository_registry
from galaxy.security.idencoding import IdEncodingHelper
from galaxy.util import safe_makedirs
from tool_shed.context import ProvidesRepositoriesContext
from tool_shed.managers.model_cache import ModelCache
from tool_shed.managers.repositories import upload_tar_and_set_metadata
from tool_shed.managers.users import create_user
from tool_shed.repository_types import util as rt_util
from tool_shed.repository_types.registry import Registry as RepositoryTypesRegistry
from tool_shed.structured_app import ToolShedApp
from tool_shed.test.base.populators import (
    repo_tars,
    TEST_DATA_REPO_FILES,
)
from tool_shed.util.hgweb_config import hgweb_config_manager
from tool_shed.util.repository_util import create_repository
from tool_shed.webapp.model import (
    Category,
    mapping,
    Repository,
    RepositoryCategoryAssociation,
    User,
)
from tool_shed_client.schema import CreateCategoryRequest

TEST_DATA_FILES = TEST_DATA_REPO_FILES
TEST_HOST = "localhost"
TEST_COMMIT_MESSAGE = "Test Commit Message"


class TestToolShedConfig:
    user_activation_on = False
    file_path: str
    id_secret: str = "thisistheshedunittestsecret"
    smtp_server: Optional[str] = None
    hgweb_repo_prefix = "repos/"
    config_hg_for_dev = False

    def __init__(self, temp_directory):
        files_path = os.path.join(temp_directory, "files")
        safe_makedirs(files_path)
        self.file_path = files_path

    def get(self, key, default):
        assert key == "admin_users"
        return "admin@galaxyproject.org"


class TestToolShedApp(ToolShedApp):
    repository_types_registry = RepositoryTypesRegistry()
    config: TestToolShedConfig
    hgweb_config_manager = hgweb_config_manager
    repository_registry: tool_shed.repository_registry.Registry
    security: IdEncodingHelper
    name: str = "ToolShed"

    def __init__(self, temp_directory=None):
        self.model = mapping.init(
            "sqlite:///:memory:",
            create_tables=True,
        )
        temp_directory = temp_directory or mkdtemp()
        hgweb_config_dir = os.path.join(temp_directory, "hgweb")
        safe_makedirs(hgweb_config_dir)
        self.hgweb_config_manager.hgweb_config_dir = hgweb_config_dir
        self.hgweb_config_manager.hgweb_repo_prefix = "repos/"
        self.config = TestToolShedConfig(temp_directory)
        self.security = IdEncodingHelper(id_secret=self.config.id_secret)
        self.repository_registry = tool_shed.repository_registry.Registry(self)
        self.model_cache = ModelCache(os.path.join(temp_directory, "model_cache"))

    @property
    def security_agent(self):
        return self.model.security_agent


def user_fixture(app: ToolShedApp, username: str, password: str = "testpassword", email: Optional[str] = None) -> User:
    email = email or f"{username}@galaxyproject.org"
    return create_user(
        app,
        email,
        username,
        password,
    )


class ProvidesRepositoriesImpl(ProvidesRepositoriesContext):
    def __init__(self, app: TestToolShedApp, user: User):
        self._app = app
        self._user = user

    @property
    def app(self) -> ToolShedApp:
        return self._app

    @property
    def user(self) -> User:
        return self._user

    @property
    def repositories_hostname(self) -> str:
        return "shed_unit_test://localhost"


def provides_repositories_fixture(
    app: TestToolShedApp,
    user: User,
):
    return ProvidesRepositoriesImpl(app, user)


def repository_fixture(app: ToolShedApp, user: User, name: str, category: Optional[Category] = None) -> Repository:
    type = rt_util.UNRESTRICTED
    description = f"test repo named {name}"
    long_description = f"test repo named {name} a longer description"
    category_ids = []
    if category:
        category_ids.append(app.security.encode_id(category.id))
    repository, message = create_repository(
        app,
        name,
        type,
        description,
        long_description,
        user,
        category_ids=category_ids,
        remote_repository_url=None,
        homepage_url=None,
    )
    assert "created" in message
    return repository


def _mock_url_for(x, qualified: bool = False):
    return "shed_unit_test://localhost/"


from unittest import mock

patch_url_for = mock.patch("galaxy.util.tool_shed.common_util.url_for", _mock_url_for)


def upload(
    provides_repositories: ProvidesRepositoriesContext,
    repository: Repository,
    path: Path,
    arcname: Optional[str] = None,
):
    if path.is_dir():
        tf = NamedTemporaryFile(delete=False)
        with tarfile.open(tf.name, "w:gz") as tar:
            print(path.name)
            print(str(path))
            tar.add(str(path), arcname=arcname or path.name)
        tar_path = tf.name
    else:
        tar_path = str(path)
    return upload_tar_and_set_metadata(
        provides_repositories,
        TEST_HOST,
        repository,
        tar_path,
        commit_message=TEST_COMMIT_MESSAGE,
    )


def upload_directories_to_repository(
    provides_repositories: ProvidesRepositoriesContext, repository: Repository, test_data_path: str
):
    paths = repo_tars(test_data_path)
    for path in paths:
        upload(provides_repositories, repository, Path(path), arcname=test_data_path)


def random_name(len: int = 10) -> str:
    return "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(len))


def create_category(provides_repositories: ProvidesRepositoriesContext, create: Dict[str, Any]) -> Category:
    from tool_shed.managers.categories import CategoryManager

    request = CreateCategoryRequest(**create)
    return CategoryManager(provides_repositories.app).create(provides_repositories, request)


def attach_category(provides_repositories: ProvidesRepositoriesContext, repository: Repository, category: Category):
    assoc = RepositoryCategoryAssociation(
        repository=repository,
        category=category,
    )
    provides_repositories.sa_session.add(assoc)
    provides_repositories.sa_session.flush()
