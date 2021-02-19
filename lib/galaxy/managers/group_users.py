import logging

from galaxy.util import unicodify
from galaxy.web import url_for

log = logging.getLogger(__name__)


class GroupUsersManager:
    """Interface/service object shared by controllers for interacting with group users."""

    def __init__(self, app) -> None:
        self._app = app

    def index(self, trans, group_id, **kwd):
        """
        Displays a collection (list) of groups.
        """
        decoded_group_id = trans.security.decode_id(group_id)
        try:
            group = trans.sa_session.query(trans.app.model.Group).get(decoded_group_id)
        except Exception:
            group = None
        if not group:
            trans.response.status = 400
            return "Invalid group id ( %s ) specified." % str(group_id)
        rval = []
        try:
            for uga in group.users:
                user = uga.user
                encoded_id = trans.security.encode_id(user.id)
                rval.append(dict(id=encoded_id,
                                 email=user.email,
                                 url=url_for('group_user', group_id=group_id, id=encoded_id, )))
        except Exception as e:
            rval = "Error in group API at listing users"
            log.error(rval + ": %s", unicodify(e))
            trans.response.status = 500
        return rval

    def show(self, trans, id, group_id, **kwd):
        """
        Displays information about a group user.
        """
        user_id = id
        decoded_group_id = trans.security.decode_id(group_id)
        decoded_user_id = trans.security.decode_id(user_id)
        item = None
        try:
            group = trans.sa_session.query(trans.app.model.Group).get(decoded_group_id)
            user = trans.sa_session.query(trans.app.model.User).get(decoded_user_id)
            for uga in group.users:
                if uga.user == user:
                    item = dict(id=user_id,
                                email=user.email,
                                url=url_for('group_user', group_id=group_id, id=user_id))  # TODO Fix This
            if not item:
                item = f"user {user.email} not in group {group.name}"
        except Exception as e:
            item = f"Error in group_user API group {group.name} user {user.email}"
            log.error(item + ": %s", unicodify(e))
        return item

    def update(self, trans, id, group_id, **kwd):
        """
        Adds a user to a group
        """
        user_id = id
        decoded_group_id = trans.security.decode_id(group_id)
        decoded_user_id = trans.security.decode_id(user_id)
        item = None
        try:
            group = trans.sa_session.query(trans.app.model.Group).get(decoded_group_id)
            user = trans.sa_session.query(trans.app.model.User).get(decoded_user_id)
            for uga in group.users:
                if uga.user == user:
                    item = dict(id=user_id,
                                email=user.email,
                                url=url_for('group_user', group_id=group_id, id=user_id))
            if not item:
                uga = trans.app.model.UserGroupAssociation(user, group)
                # Add UserGroupAssociations
                trans.sa_session.add(uga)
                trans.sa_session.flush()
                item = dict(id=user_id,
                            email=user.email,
                            url=url_for('group_user', group_id=group_id, id=user_id))
        except Exception as e:
            item = f"Error in group_user API Adding user {user.email} to group {group.name}"
            log.error(item + ": %s", unicodify(e))
        return item

    def delete(self, trans, id, group_id, **kwd):
        """
        Removes a user from a group
        """
        user_id = id
        decoded_group_id = trans.security.decode_id(group_id)
        decoded_user_id = trans.security.decode_id(user_id)
        try:
            group = trans.sa_session.query(trans.app.model.Group).get(decoded_group_id)
            user = trans.sa_session.query(trans.app.model.User).get(decoded_user_id)
            for uga in group.users:
                if uga.user == user:
                    trans.sa_session.delete(uga)
                    trans.sa_session.flush()
                    item = dict(id=user_id,
                                email=user.email,
                                url=url_for('group_user', group_id=group_id, id=user_id))
            if not item:
                item = f"user {user.email} not in group {group.name}"
        except Exception as e:
            item = f"Error in group_user API Removing user {user.email} from group {group.name}"
            log.error(item + ": %s", unicodify(e))
        return item
