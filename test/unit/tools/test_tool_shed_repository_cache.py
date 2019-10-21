import pytest

from .conftest import create_repo


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
def test_get_installed_repository(tool_shed_repository_cache, repos, tool_conf_repos, tool_shed, name, owner, changeset_revision, installed_changeset_revision, repository_id, repo_exists):
    tool_shed_repository_cache.rebuild()
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
