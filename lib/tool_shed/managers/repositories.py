"""
Manager and Serializer for TS repositories.
"""
import logging

from galaxy.exceptions import (
    InternalServerError,
    MalformedContents,
)
from galaxy.tool_shed.util import dependency_display
from tool_shed.metadata import repository_metadata_manager
from tool_shed.repository_types import util as rt_util
from tool_shed.structured_app import ToolShedApp
from tool_shed.util import hg_util
from tool_shed.util.repository_content_util import upload_tar
from tool_shed.webapp.model import Repository, User

log = logging.getLogger(__name__)


def upload_tar_and_set_metadata(
    app: ToolShedApp,
    host: str,
    user: User,
    repository: Repository,
    uploaded_file,
    upload_point,
    commit_message: str,
):
    repo_dir = repository.repo_path(app)
    tip = repository.tip()
    (ok, message, _, content_alert_str, _, _,) = upload_tar(
        app,
        host,
        user.username,
        repository,
        uploaded_file,
        upload_point,
        commit_message,
    )
    if ok:
        # Update the repository files for browsing.
        hg_util.update_repository(repo_dir)
        # Get the new repository tip.
        if tip == repository.tip():
            raise MalformedContents("No changes to repository.")
        else:
            rmm = repository_metadata_manager.RepositoryMetadataManager(app=app, user=user, repository=repository)
            _, error_message = rmm.set_repository_metadata_due_to_new_tip(host, content_alert_str=content_alert_str)
            if error_message:
                raise InternalServerError(error_message)
            dd = dependency_display.DependencyDisplayer(app)
            if str(repository.type) not in [
                rt_util.REPOSITORY_SUITE_DEFINITION,
                rt_util.TOOL_DEPENDENCY_DEFINITION,
            ]:
                # Provide a warning message if a tool_dependencies.xml file is provided, but tool dependencies
                # weren't loaded due to a requirement tag mismatch or some other problem.  Tool dependency
                # definitions can define orphan tool dependencies (no relationship to any tools contained in the
                # repository), so warning messages are important because orphans are always valid.  The repository
                # owner must be warned in case they did not intend to define an orphan dependency, but simply
                # provided incorrect information (tool shed, name owner, changeset_revision) for the definition.
                if repository.metadata_revisions:
                    # A repository's metadata revisions are order descending by update_time, so the zeroth revision
                    # will be the tip just after an upload.
                    metadata_dict = repository.metadata_revisions[0].metadata
                else:
                    metadata_dict = {}
                orphan_message = dd.generate_message_for_orphan_tool_dependencies(repository, metadata_dict)
                if orphan_message:
                    message += orphan_message
    else:
        raise InternalServerError(message)
    return message
