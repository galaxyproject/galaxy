"""
Determine if installed tool shed repositories have updates available in their respective tool sheds.
"""

import logging
import threading
from typing import NamedTuple

from sqlalchemy import false

from galaxy import util
from galaxy.model.base import transaction
from galaxy.model.tool_shed_install import ToolShedRepository
from galaxy.tool_shed.util.repository_util import get_tool_shed_status_for_installed_repository
from galaxy.tool_shed.util.shed_util_common import clean_dependency_relationships
from galaxy.util.sleeper import Sleeper
from galaxy.util.tool_shed.common_util import get_tool_shed_url_from_tool_shed_registry
from galaxy.util.tool_shed.encoding_util import tool_shed_decode

log = logging.getLogger(__name__)


class UpdateToChangeset(NamedTuple):
    changeset_revision: str
    ctx_rev: str


class UpdateRepositoryManager:
    def __init__(self, app):
        self.app = app
        self.context = self.app.install_model.context
        # Ideally only one Galaxy server process should be able to check for repository updates.
        if self.app.config.enable_tool_shed_check:
            self.running = True
            self.sleeper = Sleeper()
            self.restarter = threading.Thread(target=self.__restarter)
            self.restarter.daemon = True
            self.app.application_stack.register_postfork_function(self.restarter.start)
            self.seconds_to_sleep = int(app.config.hours_between_check * 3600)

    def get_update_to_changeset_revision_and_ctx_rev(self, repository: ToolShedRepository) -> UpdateToChangeset:
        """Return the changeset revision hash to which the repository can be updated."""
        tool_shed_url = get_tool_shed_url_from_tool_shed_registry(self.app, str(repository.tool_shed))
        params = dict(
            name=str(repository.name),
            owner=str(repository.owner),
            changeset_revision=str(repository.installed_changeset_revision),
        )
        pathspec = ["repository", "get_changeset_revision_and_ctx_rev"]
        try:
            encoded_update_dict = util.url_get(
                tool_shed_url,
                auth=self.app.tool_shed_registry.url_auth(tool_shed_url),
                pathspec=pathspec,
                params=params,
            )
            update_dict = tool_shed_decode(encoded_update_dict)
            changeset_revision = update_dict.get("changeset_revision", None)
            ctx_rev = update_dict.get("ctx_rev", None)
        except Exception as e:
            log.debug(
                f"Error getting change set revision for update from the tool shed for repository '{repository.name}': {str(e)}"
            )
            changeset_revision = None
            ctx_rev = None
        # restore_repository uses changeset_revision, ctx_rev
        return UpdateToChangeset(changeset_revision, ctx_rev)

    def __restarter(self) -> None:
        log.info("Update repository manager restarter starting up...")
        while self.running:
            # Make a call to the Tool Shed for each installed repository to get the latest
            # status information in the Tool Shed for the repository.  This information includes
            # items like newer installable repository revisions, current revision updates, whether
            # the repository revision is the latest installable revision, and whether the repository
            # has been deprecated in the Tool Shed.
            for repository in self.context.query(self.app.install_model.ToolShedRepository).filter(
                self.app.install_model.ToolShedRepository.deleted == false()
            ):
                tool_shed_status_dict = get_tool_shed_status_for_installed_repository(self.app, repository)
                if tool_shed_status_dict:
                    if tool_shed_status_dict != repository.tool_shed_status:
                        repository.tool_shed_status = tool_shed_status_dict
                        with transaction(self.context):
                            self.context.commit()
                else:
                    # The received tool_shed_status_dict is an empty dictionary, so coerce to None.
                    tool_shed_status_dict = None
                    if tool_shed_status_dict != repository.tool_shed_status:
                        repository.tool_shed_status = tool_shed_status_dict
                        with transaction(self.context):
                            self.context.commit()
            self.sleeper.sleep(self.seconds_to_sleep)
        log.info("Update repository manager restarter shutting down...")

    def shutdown(self) -> None:
        if self.app.config.enable_tool_shed_check:
            self.running = False
            self.sleeper.wake()

    def update_repository_record(
        self, repository: ToolShedRepository, updated_metadata_dict, updated_changeset_revision, updated_ctx_rev
    ) -> ToolShedRepository:
        """
        Update a tool_shed_repository database record with new information retrieved from the
        Tool Shed.  This happens when updating an installed repository to a new changeset revision.
        """
        repository.metadata_ = updated_metadata_dict
        tool_shed_url = get_tool_shed_url_from_tool_shed_registry(self.app, repository.tool_shed)
        clean_dependency_relationships(self.app, updated_metadata_dict, repository, tool_shed_url)
        # Update the repository.changeset_revision column in the database.
        repository.changeset_revision = updated_changeset_revision
        repository.ctx_rev = updated_ctx_rev
        # Update the repository.tool_shed_status column in the database.
        tool_shed_status_dict = get_tool_shed_status_for_installed_repository(self.app, repository)
        if tool_shed_status_dict:
            repository.tool_shed_status = tool_shed_status_dict
        else:
            repository.tool_shed_status = None  # type:ignore[assignment]
        session = self.app.install_model.context
        session.add(repository)
        with transaction(session):
            session.commit()
        session.refresh(repository)
        return repository
