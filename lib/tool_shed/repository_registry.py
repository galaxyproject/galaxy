import logging

from sqlalchemy import (
    and_,
    false,
    or_,
    select,
)
from typing_extensions import Protocol

import tool_shed.repository_types.util as rt_util
from tool_shed.util import (
    hg_util,
    metadata_util,
)
from tool_shed.webapp import model
from tool_shed.webapp.model import (
    Category,
    Repository,
    RepositoryMetadata,
)
from .structured_app import ToolShedApp

log = logging.getLogger(__name__)


class RegistryInterface(Protocol):

    # only used in legacy controllers - can drop when drop old tool shed webapp
    def add_category_entry(self, category): ...

    def add_entry(self, repository):
        # used when creating a repository
        # Used in legacy add_repository_registry_entry API endpoint - already deemed not worth pulling over to 2.0
        # used in legacy undelete_repository admin controller
        # used in legacy deprecate controller
        ...

    def edit_category_entry(self, old_name, new_name):
        # used in legacy admin controller
        ...

    def is_valid(self, repository) -> bool:
        # probably not used outside this class but also not hurting anything
        ...

    def remove_category_entry(self, category): ...

    def remove_entry(self, repository): ...


# stop gap to implement the same general interface as repository_registry but do nothing,
# I don't think this stuff is needed - outside potentially old test cases?
class NullRepositoryRegistry(RegistryInterface):

    def __init__(self, app: ToolShedApp):
        self.app = app

        # all of these are only used by repository_grids - which I think the tool shed 2.0
        # does not use at all - but they are part of the "public interface" consumed by
        # the full registry.
        self.certified_level_one_viewable_repositories_and_suites_by_category: dict = {}
        self.certified_level_one_viewable_suites_by_category: dict = {}
        self.viewable_repositories_and_suites_by_category: dict = {}
        self.viewable_suites_by_category: dict = {}
        self.viewable_valid_repositories_and_suites_by_category: dict = {}
        self.viewable_valid_suites_by_category: dict = {}

    def add_category_entry(self, category):
        # only used in legacy controllers - can drop when drop old tool shed webapp
        pass

    def add_entry(self, repository):
        # used when creating a repository, and maybe more?
        pass

    def edit_category_entry(self, old_name, new_name):
        pass

    def is_valid(self, repository) -> bool:
        if repository and not repository.deleted and not repository.deprecated and repository.downloadable_revisions:
            return True
        return False

    def remove_category_entry(self, category):
        pass

    def remove_entry(self, repository):
        pass


class Registry(RegistryInterface):
    def __init__(self, app):
        log.debug("Loading the repository registry...")
        self.app = app
        # The following lists contain tuples like ( repository.name, repository.user.username, changeset_revision )
        # where the changeset_revision entry is always the latest installable changeset_revision..
        self.certified_level_one_repository_and_suite_tuples = []
        self.certified_level_one_suite_tuples = []
        # These category dictionaries contain entries where the key is the category and the value is the integer count
        # of viewable repositories within that category.

        # only used internally to class and by repository_grids
        self.certified_level_one_viewable_repositories_and_suites_by_category = {}
        # only used internally to class and by repository_grids
        self.certified_level_one_viewable_suites_by_category = {}

        # not even used in legacy shed code...
        # self.certified_level_two_repository_and_suite_tuples = []
        # self.certified_level_two_suite_tuples = []
        # self.certified_level_two_viewable_repositories_and_suites_by_category = {}
        # self.certified_level_two_viewable_suites_by_category = {}

        # only used internally to class
        self.repository_and_suite_tuples = []
        # only used internally to class
        self.suite_tuples = []

        # only used internally to class and by repository_grids
        self.viewable_repositories_and_suites_by_category = {}
        # only used internally to class and by repository_grids
        self.viewable_suites_by_category = {}
        # only used internally to class and by repository_grids
        self.viewable_valid_repositories_and_suites_by_category = {}
        # only used internally to class and by repository_grids
        self.viewable_valid_suites_by_category = {}
        self.load()

    def load(self):
        with self.sa_session.begin():
            self.load_viewable_repositories_and_suites_by_category()
            self.load_repository_and_suite_tuples()

    def add_category_entry(self, category):
        category_name = str(category.name)
        if category_name not in self.viewable_repositories_and_suites_by_category:
            self.viewable_repositories_and_suites_by_category[category_name] = 0
        if category_name not in self.viewable_suites_by_category:
            self.viewable_suites_by_category[category_name] = 0
        if category_name not in self.viewable_valid_repositories_and_suites_by_category:
            self.viewable_valid_repositories_and_suites_by_category[category_name] = 0
        if category_name not in self.viewable_valid_suites_by_category:
            self.viewable_valid_suites_by_category[category_name] = 0
        if category_name not in self.certified_level_one_viewable_repositories_and_suites_by_category:
            self.certified_level_one_viewable_repositories_and_suites_by_category[category_name] = 0
        if category_name not in self.certified_level_one_viewable_suites_by_category:
            self.certified_level_one_viewable_suites_by_category[category_name] = 0

    def add_entry(self, repository):
        try:
            if repository:
                is_valid = self.is_valid(repository)
                certified_level_one_tuple = self.get_certified_level_one_tuple(repository)
                latest_installable_changeset_revision, is_level_one_certified = certified_level_one_tuple
                for rca in repository.categories:
                    category = rca.category
                    category_name = str(category.name)
                    if category_name in self.viewable_repositories_and_suites_by_category:
                        self.viewable_repositories_and_suites_by_category[category_name] += 1
                    else:
                        self.viewable_repositories_and_suites_by_category[category_name] = 1
                    if is_valid:
                        if category_name in self.viewable_valid_repositories_and_suites_by_category:
                            self.viewable_valid_repositories_and_suites_by_category[category_name] += 1
                        else:
                            self.viewable_valid_repositories_and_suites_by_category[category_name] = 1
                    if repository.type == rt_util.REPOSITORY_SUITE_DEFINITION:
                        if category_name in self.viewable_suites_by_category:
                            self.viewable_suites_by_category[category_name] += 1
                        else:
                            self.viewable_suites_by_category[category_name] = 1
                        if is_valid:
                            if category_name in self.viewable_valid_suites_by_category:
                                self.viewable_valid_suites_by_category[category_name] += 1
                            else:
                                self.viewable_valid_suites_by_category[category_name] = 1
                    if is_level_one_certified:
                        if category_name in self.certified_level_one_viewable_repositories_and_suites_by_category:
                            self.certified_level_one_viewable_repositories_and_suites_by_category[category_name] += 1
                        else:
                            self.certified_level_one_viewable_repositories_and_suites_by_category[category_name] = 1
                        if repository.type == rt_util.REPOSITORY_SUITE_DEFINITION:
                            if category_name in self.certified_level_one_viewable_suites_by_category:
                                self.certified_level_one_viewable_suites_by_category[category_name] += 1
                            else:
                                self.certified_level_one_viewable_suites_by_category[category_name] = 1
                self.load_repository_and_suite_tuple(repository)
                if is_level_one_certified:
                    self.load_certified_level_one_repository_and_suite_tuple(repository)
        except Exception:
            # The viewable repository numbers and the categorized (filtered) lists of repository tuples
            # may be slightly skewed, but that is no reason to result in a potential server error.  All
            # will be corrected at next server start.
            log.exception("Handled error adding entry to repository registry")

    def edit_category_entry(self, old_name, new_name):
        if old_name in self.viewable_repositories_and_suites_by_category:
            val = self.viewable_repositories_and_suites_by_category[old_name]
            del self.viewable_repositories_and_suites_by_category[old_name]
            self.viewable_repositories_and_suites_by_category[new_name] = val
        else:
            self.viewable_repositories_and_suites_by_category[new_name] = 0
        if old_name in self.viewable_valid_repositories_and_suites_by_category:
            val = self.viewable_valid_repositories_and_suites_by_category[old_name]
            del self.viewable_valid_repositories_and_suites_by_category[old_name]
            self.viewable_valid_repositories_and_suites_by_category[new_name] = val
        else:
            self.viewable_valid_repositories_and_suites_by_category[new_name] = 0
        if old_name in self.viewable_suites_by_category:
            val = self.viewable_suites_by_category[old_name]
            del self.viewable_suites_by_category[old_name]
            self.viewable_suites_by_category[new_name] = val
        else:
            self.viewable_suites_by_category[new_name] = 0
        if old_name in self.viewable_valid_suites_by_category:
            val = self.viewable_valid_suites_by_category[old_name]
            del self.viewable_valid_suites_by_category[old_name]
            self.viewable_valid_suites_by_category[new_name] = val
        else:
            self.viewable_valid_suites_by_category[new_name] = 0
        if old_name in self.certified_level_one_viewable_repositories_and_suites_by_category:
            val = self.certified_level_one_viewable_repositories_and_suites_by_category[old_name]
            del self.certified_level_one_viewable_repositories_and_suites_by_category[old_name]
            self.certified_level_one_viewable_repositories_and_suites_by_category[new_name] = val
        else:
            self.certified_level_one_viewable_repositories_and_suites_by_category[new_name] = 0
        if old_name in self.certified_level_one_viewable_suites_by_category:
            val = self.certified_level_one_viewable_suites_by_category[old_name]
            del self.certified_level_one_viewable_suites_by_category[old_name]
            self.certified_level_one_viewable_suites_by_category[new_name] = val
        else:
            self.certified_level_one_viewable_suites_by_category[new_name] = 0

    def get_certified_level_one_clause_list(self):
        # only used internally to class
        clause_list = []
        for repository in get_repositories(self.sa_session):
            certified_level_one_tuple = self.get_certified_level_one_tuple(repository)
            latest_installable_changeset_revision, is_level_one_certified = certified_level_one_tuple
            if is_level_one_certified:
                clause_list.append(
                    and_(
                        RepositoryMetadata.repository_id == repository.id,
                        RepositoryMetadata.changeset_revision == latest_installable_changeset_revision,
                    )
                )
        return clause_list

    def get_certified_level_one_tuple(self, repository):
        """
        Return True if the latest installable changeset_revision of the received repository is level one certified.
        """
        # only used internally to class
        if repository is None:
            return (None, False)
        if repository.deleted or repository.deprecated:
            return (None, False)
        # Get the latest installable changeset revision since that is all that is currently configured for testing.
        latest_installable_changeset_revision = metadata_util.get_latest_downloadable_changeset_revision(
            self.app, repository
        )
        if latest_installable_changeset_revision not in [None, hg_util.INITIAL_CHANGELOG_HASH]:
            encoded_repository_id = self.app.security.encode_id(repository.id)
            repository_metadata = metadata_util.get_repository_metadata_by_changeset_revision(
                self.app, encoded_repository_id, latest_installable_changeset_revision
            )
            if repository_metadata:
                # No repository_metadata.
                return (latest_installable_changeset_revision, True)
        else:
            # No installable changeset_revision.
            return (None, False)

    def is_level_one_certified(self, repository_metadata):
        # only used internally to class
        if repository_metadata:
            repository = repository_metadata.repository
            if repository:
                if repository.deprecated or repository.deleted:
                    return False
                tuple = (
                    str(repository.name),
                    str(repository.user.username),
                    str(repository_metadata.changeset_revision),
                )
                if repository.type in [rt_util.REPOSITORY_SUITE_DEFINITION]:
                    return tuple in self.certified_level_one_suite_tuples
                else:
                    return tuple in self.certified_level_one_repository_and_suite_tuples
        return False

    def is_valid(self, repository) -> bool:
        if repository and not repository.deleted and not repository.deprecated and repository.downloadable_revisions:
            return True
        return False

    def load_certified_level_one_repository_and_suite_tuple(self, repository):
        # only used internally to class
        # The received repository has been determined to be level one certified.
        name = str(repository.name)
        owner = str(repository.user.username)
        tip_changeset_hash = repository.tip()
        if tip_changeset_hash != hg_util.INITIAL_CHANGELOG_HASH:
            certified_level_one_tuple = (name, owner, tip_changeset_hash)
            if repository.type == rt_util.REPOSITORY_SUITE_DEFINITION:
                if certified_level_one_tuple not in self.certified_level_one_suite_tuples:
                    self.certified_level_one_suite_tuples.append(certified_level_one_tuple)
            else:
                if certified_level_one_tuple not in self.certified_level_one_repository_and_suite_tuples:
                    self.certified_level_one_repository_and_suite_tuples.append(certified_level_one_tuple)

    def load_repository_and_suite_tuple(self, repository):
        # only used internally to class
        name = str(repository.name)
        owner = str(repository.user.username)
        for repository_metadata in repository.metadata_revisions:
            changeset_revision = str(repository_metadata.changeset_revision)
            tuple = (name, owner, changeset_revision)
            if tuple not in self.repository_and_suite_tuples:
                self.repository_and_suite_tuples.append(tuple)
            if repository.type == rt_util.REPOSITORY_SUITE_DEFINITION:
                if tuple not in self.suite_tuples:
                    self.suite_tuples.append(tuple)

    def load_repository_and_suite_tuples(self):
        # only used internally to class
        # Load self.certified_level_one_repository_and_suite_tuples and self.certified_level_one_suite_tuples.
        clauses = self.get_certified_level_one_clause_list()
        for repository in get_certified_repositories_with_user(self.sa_session, clauses, model.User):
            self.load_certified_level_one_repository_and_suite_tuple(repository)
        # Load self.repository_and_suite_tuples and self.suite_tuples
        for repository in get_repositories_with_user(self.sa_session, model.User):
            self.load_repository_and_suite_tuple(repository)

    def load_viewable_repositories_and_suites_by_category(self):
        # only used internally to class
        # Clear all dictionaries just in case they were previously loaded.
        self.certified_level_one_viewable_repositories_and_suites_by_category = {}
        self.certified_level_one_viewable_suites_by_category = {}
        # self.certified_level_two_viewable_repositories_and_suites_by_category = {}
        # self.certified_level_two_viewable_suites_by_category = {}
        self.viewable_repositories_and_suites_by_category = {}
        self.viewable_suites_by_category = {}
        self.viewable_valid_repositories_and_suites_by_category = {}
        self.viewable_valid_suites_by_category = {}
        for category in self.sa_session.scalars(select(Category)):
            category_name = str(category.name)
            if category not in self.certified_level_one_viewable_repositories_and_suites_by_category:
                self.certified_level_one_viewable_repositories_and_suites_by_category[category_name] = 0
            if category not in self.certified_level_one_viewable_suites_by_category:
                self.certified_level_one_viewable_suites_by_category[category_name] = 0
            if category not in self.viewable_repositories_and_suites_by_category:
                self.viewable_repositories_and_suites_by_category[category_name] = 0
            if category not in self.viewable_suites_by_category:
                self.viewable_suites_by_category[category_name] = 0
            if category not in self.viewable_valid_repositories_and_suites_by_category:
                self.viewable_valid_repositories_and_suites_by_category[category_name] = 0
            if category not in self.viewable_valid_suites_by_category:
                self.viewable_valid_suites_by_category[category_name] = 0
            for rca in category.repositories:
                repository = rca.repository
                if not repository.deleted and not repository.deprecated:
                    is_valid = self.is_valid(repository)
                    encoded_repository_id = self.app.security.encode_id(repository.id)
                    tip_changeset_hash = repository.tip()
                    repository_metadata = metadata_util.get_repository_metadata_by_changeset_revision(
                        self.app, encoded_repository_id, tip_changeset_hash
                    )
                    self.viewable_repositories_and_suites_by_category[category_name] += 1
                    if is_valid:
                        self.viewable_valid_repositories_and_suites_by_category[category_name] += 1
                    if repository.type in [rt_util.REPOSITORY_SUITE_DEFINITION]:
                        self.viewable_suites_by_category[category_name] += 1
                        if is_valid:
                            self.viewable_valid_suites_by_category[category_name] += 1
                    if self.is_level_one_certified(repository_metadata):
                        self.certified_level_one_viewable_repositories_and_suites_by_category[category_name] += 1
                        if repository.type in [rt_util.REPOSITORY_SUITE_DEFINITION]:
                            self.certified_level_one_viewable_suites_by_category[category_name] += 1

    def remove_category_entry(self, category):
        catgeory_name = str(category.name)
        if catgeory_name in self.viewable_repositories_and_suites_by_category:
            del self.viewable_repositories_and_suites_by_category[catgeory_name]
        if catgeory_name in self.viewable_valid_repositories_and_suites_by_category:
            del self.viewable_valid_repositories_and_suites_by_category[catgeory_name]
        if catgeory_name in self.viewable_suites_by_category:
            del self.viewable_suites_by_category[catgeory_name]
        if catgeory_name in self.viewable_valid_suites_by_category:
            del self.viewable_valid_suites_by_category[catgeory_name]
        if catgeory_name in self.certified_level_one_viewable_repositories_and_suites_by_category:
            del self.certified_level_one_viewable_repositories_and_suites_by_category[catgeory_name]
        if catgeory_name in self.certified_level_one_viewable_suites_by_category:
            del self.certified_level_one_viewable_suites_by_category[catgeory_name]

    def remove_entry(self, repository):
        try:
            if repository:
                is_valid = self.is_valid(repository)
                certified_level_one_tuple = self.get_certified_level_one_tuple(repository)
                latest_installable_changeset_revision, is_level_one_certified = certified_level_one_tuple
                for rca in repository.categories:
                    category = rca.category
                    category_name = str(category.name)
                    if category_name in self.viewable_repositories_and_suites_by_category:
                        if self.viewable_repositories_and_suites_by_category[category_name] > 0:
                            self.viewable_repositories_and_suites_by_category[category_name] -= 1
                    else:
                        self.viewable_repositories_and_suites_by_category[category_name] = 0
                    if is_valid:
                        if category_name in self.viewable_valid_repositories_and_suites_by_category:
                            if self.viewable_valid_repositories_and_suites_by_category[category_name] > 0:
                                self.viewable_valid_repositories_and_suites_by_category[category_name] -= 1
                        else:
                            self.viewable_valid_repositories_and_suites_by_category[category_name] = 0
                    if repository.type == rt_util.REPOSITORY_SUITE_DEFINITION:
                        if category_name in self.viewable_suites_by_category:
                            if self.viewable_suites_by_category[category_name] > 0:
                                self.viewable_suites_by_category[category_name] -= 1
                        else:
                            self.viewable_suites_by_category[category_name] = 0
                        if is_valid:
                            if category_name in self.viewable_valid_suites_by_category:
                                if self.viewable_valid_suites_by_category[category_name] > 0:
                                    self.viewable_valid_suites_by_category[category_name] -= 1
                            else:
                                self.viewable_valid_suites_by_category[category_name] = 0
                    if is_level_one_certified:
                        if category_name in self.certified_level_one_viewable_repositories_and_suites_by_category:
                            if self.certified_level_one_viewable_repositories_and_suites_by_category[category_name] > 0:
                                self.certified_level_one_viewable_repositories_and_suites_by_category[
                                    category_name
                                ] -= 1
                        else:
                            self.certified_level_one_viewable_repositories_and_suites_by_category[category_name] = 0
                        if repository.type == rt_util.REPOSITORY_SUITE_DEFINITION:
                            if category_name in self.certified_level_one_viewable_suites_by_category:
                                if self.certified_level_one_viewable_suites_by_category[category_name] > 0:
                                    self.certified_level_one_viewable_suites_by_category[category_name] -= 1
                            else:
                                self.certified_level_one_viewable_suites_by_category[category_name] = 0
                self.unload_repository_and_suite_tuple(repository)
                if is_level_one_certified:
                    self.unload_certified_level_one_repository_and_suite_tuple(repository)
        except Exception:
            # The viewable repository numbers and the categorized (filtered) lists of repository tuples
            # may be slightly skewed, but that is no reason to result in a potential server error.  All
            # will be corrected at next server start.
            log.exception("Handled error removing entry from repository registry")

    @property
    def sa_session(self):
        # only used internally to class
        return self.app.model.session

    def unload_certified_level_one_repository_and_suite_tuple(self, repository):
        # The received repository has been determined to be level one certified.
        name = str(repository.name)
        owner = str(repository.user.username)
        tip_changeset_hash = repository.tip()
        if tip_changeset_hash != hg_util.INITIAL_CHANGELOG_HASH:
            certified_level_one_tuple = (name, owner, tip_changeset_hash)
            if repository.type == rt_util.REPOSITORY_SUITE_DEFINITION:
                if certified_level_one_tuple in self.certified_level_one_suite_tuples:
                    self.certified_level_one_suite_tuples.remove(certified_level_one_tuple)
            else:
                if certified_level_one_tuple in self.certified_level_one_repository_and_suite_tuples:
                    self.certified_level_one_repository_and_suite_tuples.remove(certified_level_one_tuple)

    def unload_repository_and_suite_tuple(self, repository):
        name = str(repository.name)
        owner = str(repository.user.username)
        for repository_metadata in repository.metadata_revisions:
            changeset_revision = str(repository_metadata.changeset_revision)
            tuple = (name, owner, changeset_revision)
            if tuple in self.repository_and_suite_tuples:
                self.repository_and_suite_tuples.remove(tuple)
            if repository.type == rt_util.REPOSITORY_SUITE_DEFINITION:
                if tuple in self.suite_tuples:
                    self.suite_tuples.remove(tuple)


def get_repositories(session):
    stmt = select(Repository).where(Repository.deleted == false()).where(Repository.deprecated == false())
    return session.scalars(stmt)


def get_repositories_with_user(session, user_model):
    stmt = (
        select(Repository).where(Repository.deleted == false()).where(Repository.deprecated == false()).join(user_model)
    )
    return session.scalars(stmt)


def get_certified_repositories_with_user(session, where_clauses, user_model):
    stmt = select(Repository).join(RepositoryMetadata).where(or_(*where_clauses)).join(user_model)
    return session.scalars(stmt)
