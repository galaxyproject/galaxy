"""
Manager and Serializer for TS repositories.
"""
import logging

from sqlalchemy.orm.exc import (
    MultipleResultsFound,
    NoResultFound,
)

from galaxy.exceptions import (
    InconsistentDatabase,
    InternalServerError,
    MalformedContents,
    RequestParameterInvalidException,
)
from tool_shed.metadata import repository_metadata_manager
from tool_shed.structured_app import ToolShedApp
from tool_shed.util import hg_util
from tool_shed.util.repository_content_util import upload_tar
from tool_shed.webapp.model import Repository, User

log = logging.getLogger(__name__)


# =============================================================================
class RepoManager:
    """
    Interface/service object for interacting with TS repositories.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get(self, trans, decoded_repo_id):
        """
        Get the repo from the DB.

        :param  decoded_repo_id:       decoded repo id
        :type   decoded_repo_id:       int

        :returns:   the requested repo
        :rtype:     tool_shed.webapp.model.Repository
        """
        try:
            repo = (
                trans.sa_session.query(trans.app.model.Repository)
                .filter(trans.app.model.Repository.table.c.id == decoded_repo_id)
                .one()
            )
        except MultipleResultsFound:
            raise InconsistentDatabase("Multiple repositories found with the same id.")
        except NoResultFound:
            raise RequestParameterInvalidException("No repository found with the id provided.")
        except Exception:
            raise InternalServerError("Error loading from the database.")
        return repo

    def list_by_owner(self, trans, user_id):
        """
        Return a list of of repositories owned by a given TS user from the DB.

        :returns: query that will emit repositories owned by given user
        :rtype:   sqlalchemy query
        """
        query = trans.sa_session.query(trans.app.model.Repository).filter(
            trans.app.model.Repository.table.c.user_id == user_id
        )
        return query

    def create(self, trans, name, description=""):
        """
        Create a new group.
        """

    def update(self, trans, group, name=None, description=None):
        """
        Update the given group
        """

    def delete(self, trans, group, undelete=False):
        """
        Mark given group deleted/undeleted based on the flag.
        """


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
