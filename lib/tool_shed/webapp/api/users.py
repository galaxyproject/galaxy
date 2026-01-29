import logging

import tool_shed.util.shed_util_common as suc
from galaxy import (
    util,
    web,
)
from tool_shed.managers.users import (
    api_create_user,
    index,
)
from tool_shed_client.schema import CreateUserRequest
from . import BaseShedAPIController

log = logging.getLogger(__name__)


class UsersController(BaseShedAPIController):
    """RESTful controller for interactions with users in the Tool Shed."""

    @web.expose_api
    @web.require_admin
    def create(self, trans, payload, **kwd):
        """
                POST /api/users
                Returns a dictionary of information about the created user.

        :       param key: the current Galaxy admin user's API key

                The following parameters are included in the payload.
                :param email (required): the email address of the user
                :param password (required): the password of the user
                :param username (required): the public username of the user
        """
        # Get the information about the user to be created from the payload.
        email = payload.get("email", "")
        password = payload.get("password", "")
        username = payload.get("username", "")
        # Create the user.
        request = CreateUserRequest(
            email=email,
            username=username,
            password=password,
        )
        user = api_create_user(trans, request)
        user_dict = user.dict()
        user_dict["message"] = f"User '{str(user.username)}' has been created."
        user_dict["url"] = web.url_for(controller="users", action="show", id=trans.security.encode_id(user.id))
        return user_dict

    def __get_value_mapper(self, trans):
        value_mapper = {"id": trans.security.encode_id}
        return value_mapper

    @web.expose_api_anonymous_and_sessionless
    def index(self, trans, deleted=False, **kwd):
        """
        GET /api/users
        Returns a list of dictionaries that contain information about each user.
        """
        # Example URL: http://localhost:9009/api/users
        user_dicts = []
        deleted = util.asbool(deleted)
        for user in index(trans.app, deleted):
            user_dict = user.dict()
            user_dict["url"] = web.url_for(controller="users", action="show", id=trans.security.encode_id(user.id))
            user_dicts.append(user_dict)
        return user_dicts

    @web.expose_api_anonymous_and_sessionless
    def show(self, trans, id, **kwd):
        """
        GET /api/users/{encoded_user_id}
        GET /api/users/current
        Returns a dictionary of information about a user.

        :param id: the encoded id of the User object.
        """
        user = None
        # user is requesting data about themselves
        user = trans.user if id == "current" else suc.get_user(trans.app, id)
        if user is None:
            user_dict = dict(message=f"Unable to locate user record for id {str(id)}.", status="error")
            return user_dict
        user_dict = user.to_dict(view="element", value_mapper=self.__get_value_mapper(trans))
        user_dict["url"] = web.url_for(controller="users", action="show", id=trans.security.encode_id(user.id))
        return user_dict
