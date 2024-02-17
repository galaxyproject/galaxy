import logging
from collections import defaultdict
from typing import (
    Dict,
    List,
    Tuple,
)

from sqlalchemy.orm import defer

from galaxy.model.scoped_session import install_model_scoped_session
from galaxy.model.tool_shed_install import ToolShedRepository
from galaxy.tool_util.toolbox.base import ToolConfRepository

log = logging.getLogger(__name__)


class ToolShedRepositoryCache:
    """
    Cache installed ToolShedRepository objects.
    """

    local_repositories: List[ToolConfRepository]
    repositories: List[ToolShedRepository]
    repos_by_tuple: Dict[Tuple[str, str, str], List[ToolConfRepository]]

    def __init__(self, session: install_model_scoped_session):
        self.session = session()
        # Contains ToolConfRepository objects created from shed_tool_conf.xml entries
        self.local_repositories = []
        # Repositories loaded from database
        self.repositories = []
        self.repos_by_tuple = defaultdict(list)
        self._build()
        self.session.close()

    def add_local_repository(self, repository):
        self.local_repositories.append(repository)
        self.repos_by_tuple[(repository.tool_shed, repository.owner, repository.name)].append(repository)

    def _build(self):
        self.repositories = self.session.query(ToolShedRepository).options(defer(ToolShedRepository.metadata_)).all()
        repos_by_tuple = defaultdict(list)
        for repository in self.repositories + self.local_repositories:
            repos_by_tuple[(repository.tool_shed, repository.owner, repository.name)].append(repository)
        self.repos_by_tuple = repos_by_tuple

    def get_installed_repository(
        self,
        tool_shed=None,
        name=None,
        owner=None,
        installed_changeset_revision=None,
        changeset_revision=None,
        repository_id=None,
    ):
        if repository_id:
            repos = [repo for repo in self.repositories if repo.id == repository_id]
            if repos:
                return repos[0]
            else:
                return None
        repos = self.repos_by_tuple[(tool_shed, owner, name)]
        for repo in repos:
            if installed_changeset_revision and repo.installed_changeset_revision != installed_changeset_revision:
                continue
            if changeset_revision and repo.changeset_revision != changeset_revision:
                continue
            return repo
        return None
