import pytest

from galaxy.model import tool_shed_install
from galaxy.model.tool_shed_install import mapping
from galaxy.tools.cache import ToolShedRepositoryCache
from galaxy.tools.toolbox.base import ToolConfRepository
from galaxy.util import bunch


@pytest.fixture
def mock_app():
    app = bunch.Bunch()
    app.install_model = mapping.init("sqlite:///:memory:", create_tables=True)
    return app


@pytest.fixture
def tool_shed_repository_cache(mock_app):
    tool_shed_repository_cache = ToolShedRepositoryCache(app=mock_app)
    return tool_shed_repository_cache


@pytest.fixture
def repos(mock_app):
    repositories = [create_repo(mock_app, changeset=i + 1, installed_changeset=i) for i in range(10)]
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
        )
        tool_shed_repository_cache.add_local_repository(repo)


def create_repo(app, changeset, installed_changeset, config_filename=None):
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
    app.install_model.context.add(repository)
    return repository


def test_empty_repo_cache(tool_shed_repository_cache):
    assert len(tool_shed_repository_cache.repositories) == 0
    assert len(tool_shed_repository_cache.local_repositories) == 0


def test_add_repository_to_repository_cache(tool_shed_repository_cache, repos):
    tool_shed_repository_cache.rebuild()
    assert len(tool_shed_repository_cache.repositories) == 10
    assert len(tool_shed_repository_cache.local_repositories) == 0


def test_add_repository_and_tool_conf_repository_to_repository_cache(tool_shed_repository_cache, repos, tool_conf_repos):
    tool_shed_repository_cache.rebuild()
    assert len(tool_shed_repository_cache.repositories) == 10
    assert len(tool_shed_repository_cache.local_repositories) == 10
    tool_shed_repository_cache.rebuild()
    assert len(tool_shed_repository_cache.repositories) == 10
    assert len(tool_shed_repository_cache.local_repositories) == 10
    create_repo(tool_shed_repository_cache.app, '21', '20')
    tool_shed_repository_cache.app.install_model.context.flush()
    tool_shed_repository_cache.rebuild()
    assert len(tool_shed_repository_cache.repositories) == 11
    assert len(tool_shed_repository_cache.local_repositories) == 10


@pytest.mark.parametrize('tool_shed,name,owner,changeset_revision,installed_changeset_revision,repository_id,repo_exists', [
    ('github.com', 'example', 'galaxyproject', None, None, None, True),
    ('github.com', 'example', 'noone', None, None, None, False),
    ('github.com', 'example', 'galaxyproject', '1', None, None, True),
    ('github.com', 'example', 'galaxyproject', None, '1', None, True),
    ('github.com', 'example', 'galaxyproject', '2', '1', None, True),
    ('github.com', 'example', 'galaxyproject', '500', '1', None, False),
    ('github.com', 'example', 'galaxyproject', '1', '500', None, False),
    ('github.com', 'example', 'galaxyproject', '2', '1', 1, True),
    ('github.com', 'example', 'galaxyproject', '2', '1', 500, False),
    ('github.com', 'example', 'galaxyproject', '19', '18', None, True),
])
def test_get_installed_repository(tool_shed_repository_cache, repos, tool_shed, tool_conf_repos, name, owner, changeset_revision, installed_changeset_revision, repository_id, repo_exists):
    tool_shed_repository_cache.rebuild()
    print(tool_shed_repository_cache.local_repositories)
    repo = tool_shed_repository_cache.get_installed_repository(
        tool_shed=tool_shed,
        name=name,
        owner=owner,
        installed_changeset_revision=installed_changeset_revision,
        changeset_revision=changeset_revision,
        repository_id=repository_id
    )
    if repo_exists:
        assert repo
    else:
        assert repo is None
