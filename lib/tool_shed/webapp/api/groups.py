import logging
from typing import (
    Callable,
    Dict,
)

from sqlalchemy import select

from galaxy import (
    util,
    web,
)
from galaxy.exceptions import (
    AdminRequiredException,
    ObjectNotFound,
    RequestParameterMissingException,
)
from galaxy.util import (
    pretty_print_time_interval,
    UNKNOWN,
)
from galaxy.web import (
    expose_api,
    expose_api_anonymous_and_sessionless,
    require_admin,
)
from tool_shed.managers import groups
from tool_shed.structured_app import ToolShedApp
from tool_shed.webapp.model import (
    Category,
    Repository,
    RepositoryCategoryAssociation,
    RepositoryMetadata,
    User,
)
from . import BaseShedAPIController

log = logging.getLogger(__name__)


class GroupsController(BaseShedAPIController):
    """RESTful controller for interactions with groups in the Tool Shed."""

    def __init__(self, app: ToolShedApp):
        super().__init__(app)
        self.group_manager = groups.GroupManager()

    def __get_value_mapper(self, trans) -> Dict[str, Callable]:
        value_mapper = {"id": trans.security.encode_id}
        return value_mapper

    @expose_api_anonymous_and_sessionless
    def index(self, trans, deleted=False, **kwd):
        """
        GET /api/groups
        Return a list of dictionaries that contain information about each Group.

        :param deleted: flag used to include deleted groups

        Example: GET localhost:9009/api/groups
        """
        group_dicts = []
        deleted = util.asbool(deleted)
        if deleted and not trans.user_is_admin:
            raise AdminRequiredException("Only administrators can query deleted groups.")
        for group in self.group_manager.list(trans, deleted):
            group_dicts.append(self._populate(trans, group))
        return group_dicts

    @expose_api
    @require_admin
    def create(self, trans, payload, **kwd):
        """
        POST /api/groups
        Return a dictionary of information about the created group.
        The following parameters are included in the payload:

        :param name (required): the name of the group
        :param description (optional): the description of the group

        Example: POST /api/groups/?key=XXXYYYXXXYYY
        Content-Disposition: form-data; name="name" Group_Name
        Content-Disposition: form-data; name="description" Group_Description
        """
        group_dict = dict(message="", status="ok")
        if name := payload.get("name", ""):
            description = payload.get("description", "")
            if not description:
                description = ""
            else:
                # TODO add description field to the model
                group_dict = self.group_manager.create(trans, name=name).to_dict(
                    view="element", value_mapper=self.__get_value_mapper(trans)
                )
        else:
            raise RequestParameterMissingException('Missing required parameter "name".')
        return group_dict

    @expose_api_anonymous_and_sessionless
    def show(self, trans, encoded_id, **kwd):
        """
        GET /api/groups/{encoded_group_id}
        Return a dictionary of information about a group.

        :param id: the encoded id of the Group object

        Example: GET localhost:9009/api/groups/f9cad7b01a472135
        """
        decoded_id = trans.security.decode_id(encoded_id)
        group = self.group_manager.get(trans, decoded_id)
        if group is None:
            raise ObjectNotFound("Unable to locate group record with the given id.")
        return self._populate(trans, group)

    def _populate(self, trans, group):
        """
        Turn the given group information from DB into a dict
        and add other characteristics like members and repositories.
        """
        group_dict = group.to_dict(view="collection", value_mapper=self.__get_value_mapper(trans))
        group_members = []
        group_repos = []
        total_downloads = 0
        for uga in group.users:
            user = trans.sa_session.get(User, uga.user_id)
            user_repos_count = 0
            for repo in get_user_repositories(trans.sa_session, uga.user_id):
                categories = []
                for rca in repo.categories:
                    cat_dict = dict(name=rca.category.name, id=trans.app.security.encode_id(rca.category.id))
                    categories.append(cat_dict)
                time_repo_created_full = repo.create_time.strftime("%Y-%m-%d %I:%M %p")
                time_repo_updated_full = repo.update_time.strftime("%Y-%m-%d %I:%M %p")
                time_repo_created = pretty_print_time_interval(repo.create_time, True)
                time_repo_updated = pretty_print_time_interval(repo.update_time, True)
                # TODO add user ratings
                total_downloads += repo.times_downloaded
                group_repos.append(
                    {
                        "name": repo.name,
                        "times_downloaded": repo.times_downloaded,
                        "owner": repo.user.username,
                        "time_created_full": time_repo_created_full,
                        "time_created": time_repo_created,
                        "time_updated_full": time_repo_updated_full,
                        "time_updated": time_repo_updated,
                        "description": repo.description,
                        "categories": categories,
                    }
                )
                user_repos_count += 1
            encoded_user_id = trans.app.security.encode_id(user.id)
            user_repos_url = web.url_for(
                controller="repository", action="browse_repositories_by_user", user_id=encoded_user_id
            )
            time_created = pretty_print_time_interval(user.create_time, True)
            member_dict = {
                "id": encoded_user_id,
                "username": user.username,
                "user_repos_url": user_repos_url,
                "user_repos_count": user_repos_count,
                "user_tools_count": UNKNOWN,
                "time_created": time_created,
            }
            group_members.append(member_dict)
        group_dict["members"] = group_members
        group_dict["total_members"] = len(group_members)
        group_dict["repositories"] = group_repos
        group_dict["total_repos"] = len(group_repos)
        group_dict["total_downloads"] = total_downloads
        return group_dict


def get_user_repositories(session, user_id):
    stmt = (
        select(Repository)
        .where(Repository.user_id == user_id)
        .join(RepositoryMetadata)
        .join(User)
        .outerjoin(RepositoryCategoryAssociation)
        .outerjoin(Category)
    )
    return session.scalars(stmt)
