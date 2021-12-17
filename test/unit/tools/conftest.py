from tempfile import (
    mkdtemp,
    NamedTemporaryFile,
)

import pytest

from galaxy.model import tool_shed_install
from galaxy.model.tool_shed_install import mapping
from galaxy.tool_util.toolbox.base import ToolConfRepository
from galaxy.tools.cache import ToolShedRepositoryCache
from galaxy.util import bunch


@pytest.fixture
def mock_app():
    app = bunch.Bunch()
    with NamedTemporaryFile(suffix='test.sqlite') as db_file:
        install_database_connection = f"sqlite:///{db_file.name}"
        app.config = bunch.Bunch(database_connection="sqlite:///:memory:", install_database_connection=install_database_connection, database_engine_options={}, install_database_engine_options={})
        app.install_model = mapping.init(install_database_connection, create_tables=True)
        yield app


@pytest.fixture
def tool_shed_repository_cache(mock_app):
    tool_shed_repository_cache = ToolShedRepositoryCache(config=mock_app.config)
    return tool_shed_repository_cache


@pytest.fixture
def repos(mock_app):
    repositories = [create_repo(mock_app.install_model.context, changeset=i + 1, installed_changeset=i) for i in range(10)]
    mock_app.install_model.context.flush()
    return repositories


@pytest.fixture
def tool_conf_repos(tool_shed_repository_cache):
    for i in range(10, 20):
        repo = ToolConfRepository(
            'github.com',
            'example',
            'galaxyproject',
            str(i),
            str(i + 1),
            None,
            repository_path=mkdtemp(prefix='repository_path'),
            tool_path='../shed_tools',
        )
        tool_shed_repository_cache.add_local_repository(repo)
    return tool_shed_repository_cache.local_repositories


def create_repo(session, changeset, installed_changeset, config_filename=None):
    metadata = {
        'tools': [{
            'add_to_tool_panel': False,  # to have repository.includes_tools_for_display_in_tool_panel=False in InstalledRepositoryManager.activate_repository()
            'guid': "github.com/galaxyproject/example/test_tool/0.%s" % changeset,
            'tool_config': 'tool.xml'
        }],
    }
    if config_filename:
        metadata['shed_config_filename'] = config_filename
    repository = tool_shed_install.ToolShedRepository(metadata=metadata)
    repository.tool_shed = "github.com"
    repository.owner = "galaxyproject"
    repository.name = "example"
    repository.changeset_revision = str(changeset)
    repository.installed_changeset_revision = str(installed_changeset)
    repository.deleted = False
    repository.uninstalled = False
    session.add(repository)
    session.flush()
    tool_dependency = tool_shed_install.ToolDependency(
        name='Name',
        version='100',
        type='package',
        status='ok',
        tool_shed_repository_id=repository.id,
    )
    session.add(tool_dependency)
    return repository
