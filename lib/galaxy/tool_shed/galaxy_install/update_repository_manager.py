"""
Determine if installed tool shed repositories have updates available in their respective tool sheds.
"""
import logging
import threading

from sqlalchemy import false

from galaxy import util
from galaxy.tool_shed.util.repository_util import get_tool_shed_status_for_installed_repository
from galaxy.tool_shed.util.shed_util_common import clean_dependency_relationships
from galaxy.util.tool_shed.common_util import get_tool_shed_url_from_tool_shed_registry
from galaxy.util.tool_shed.encoding_util import tool_shed_decode

log = logging.getLogger(__name__)


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

    def get_update_to_changeset_revision_and_ctx_rev(self, repository):
        """Return the changeset revision hash to which the repository can be updated."""
        changeset_revision_dict = {}
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
            if encoded_update_dict:
                update_dict = tool_shed_decode(encoded_update_dict)
                includes_data_managers = update_dict.get("includes_data_managers", False)
                includes_datatypes = update_dict.get("includes_datatypes", False)
                includes_tools = update_dict.get("includes_tools", False)
                includes_tools_for_display_in_tool_panel = update_dict.get(
                    "includes_tools_for_display_in_tool_panel", False
                )
                includes_tool_dependencies = update_dict.get("includes_tool_dependencies", False)
                includes_workflows = update_dict.get("includes_workflows", False)
                has_repository_dependencies = update_dict.get("has_repository_dependencies", False)
                has_repository_dependencies_only_if_compiling_contained_td = update_dict.get(
                    "has_repository_dependencies_only_if_compiling_contained_td", False
                )
                changeset_revision = update_dict.get("changeset_revision", None)
                ctx_rev = update_dict.get("ctx_rev", None)
            changeset_revision_dict["includes_data_managers"] = includes_data_managers
            changeset_revision_dict["includes_datatypes"] = includes_datatypes
            changeset_revision_dict["includes_tools"] = includes_tools
            changeset_revision_dict[
                "includes_tools_for_display_in_tool_panel"
            ] = includes_tools_for_display_in_tool_panel
            changeset_revision_dict["includes_tool_dependencies"] = includes_tool_dependencies
            changeset_revision_dict["includes_workflows"] = includes_workflows
            changeset_revision_dict["has_repository_dependencies"] = has_repository_dependencies
            changeset_revision_dict[
                "has_repository_dependencies_only_if_compiling_contained_td"
            ] = has_repository_dependencies_only_if_compiling_contained_td
            changeset_revision_dict["changeset_revision"] = changeset_revision
            changeset_revision_dict["ctx_rev"] = ctx_rev
        except Exception as e:
            log.debug(
                f"Error getting change set revision for update from the tool shed for repository '{repository.name}': {str(e)}"
            )
            changeset_revision_dict["includes_data_managers"] = False
            changeset_revision_dict["includes_datatypes"] = False
            changeset_revision_dict["includes_tools"] = False
            changeset_revision_dict["includes_tools_for_display_in_tool_panel"] = False
            changeset_revision_dict["includes_tool_dependencies"] = False
            changeset_revision_dict["includes_workflows"] = False
            changeset_revision_dict["has_repository_dependencies"] = False
            changeset_revision_dict["has_repository_dependencies_only_if_compiling_contained_td"] = False
            changeset_revision_dict["changeset_revision"] = None
            changeset_revision_dict["ctx_rev"] = None
        return changeset_revision_dict

    def __restarter(self):
        log.info("Update repository manager restarter starting up...")
        while self.running:
            # Make a call to the Tool Shed for each installed repository to get the latest
            # status information in the Tool Shed for the repository.  This information includes
            # items like newer installable repository revisions, current revision updates, whether
            # the repository revision is the latest installable revision, and whether the repository
            # has been deprecated in the Tool Shed.
            for repository in self.context.query(self.app.install_model.ToolShedRepository).filter(
                self.app.install_model.ToolShedRepository.table.c.deleted == false()
            ):
                tool_shed_status_dict = get_tool_shed_status_for_installed_repository(self.app, repository)
                if tool_shed_status_dict:
                    if tool_shed_status_dict != repository.tool_shed_status:
                        repository.tool_shed_status = tool_shed_status_dict
                        self.context.flush()
                else:
                    # The received tool_shed_status_dict is an empty dictionary, so coerce to None.
                    tool_shed_status_dict = None
                    if tool_shed_status_dict != repository.tool_shed_status:
                        repository.tool_shed_status = tool_shed_status_dict
                        self.context.flush()
            self.sleeper.sleep(self.seconds_to_sleep)
        log.info("Update repository manager restarter shutting down...")

    def shutdown(self):
        if self.app.config.enable_tool_shed_check:
            self.running = False
            self.sleeper.wake()

    def update_repository_record(self, repository, updated_metadata_dict, updated_changeset_revision, updated_ctx_rev):
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
            repository.tool_shed_status = None
        self.app.install_model.context.add(repository)
        self.app.install_model.context.flush()
        self.app.install_model.context.refresh(repository)
        return repository


class Sleeper:
    """
    Provides a 'sleep' method that sleeps for a number of seconds *unless* the notify method
    is called (from a different thread).
    """

    def __init__(self):
        self.condition = threading.Condition()

    def sleep(self, seconds):
        self.condition.acquire()
        self.condition.wait(seconds)
        self.condition.release()

    def wake(self):
        self.condition.acquire()
        self.condition.notify()
        self.condition.release()
