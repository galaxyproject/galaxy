"""
Manager and Serializer for TS repositories.
"""
import logging

from galaxy.exceptions import (
    InternalServerError,
    MalformedContents,
)
from tool_shed.metadata import repository_metadata_manager
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
    else:
        raise InternalServerError(message)
    return message
