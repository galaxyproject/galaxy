import logging

from galaxy.util import unicodify
from galaxy.web import url_for

log = logging.getLogger(__name__)


class GroupRolesManager:
    """Interface/service object shared by controllers for interacting with group roles."""

    def __init__(self, app) -> None:
        self._app = app

    def index(self, trans, group_id):
        """
        Returns a collection (list) of roles.
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
            for gra in group.roles:
                role = gra.role
                encoded_id = trans.security.encode_id(role.id)
                rval.append(dict(id=encoded_id,
                                 name=role.name,
                                 url=url_for('group_role', group_id=group_id, id=encoded_id, )))
        except Exception as e:
            rval = "Error in group API at listing roles"
            log.error(rval + ": %s", unicodify(e))
            trans.response.status = 500
        return rval

    def show(self, trans, id, group_id):
        """
        Returns information about a group role.
        """
        role_id = id
        decoded_group_id = trans.security.decode_id(group_id)
        decoded_role_id = trans.security.decode_id(role_id)
        item = None
        try:
            group = trans.sa_session.query(trans.app.model.Group).get(decoded_group_id)
            role = trans.sa_session.query(trans.app.model.Role).get(decoded_role_id)
            for gra in group.roles:
                if gra.role == role:
                    item = dict(id=role_id,
                                name=role.name,
                                url=url_for('group_role', group_id=group_id, id=role_id))  # TODO Fix This
            if not item:
                item = f"role {role.name} not in group {group.name}"
        except Exception as e:
            item = f"Error in group_role API group {group.name} role {role.name}"
            log.error(item + ": %s", unicodify(e))
        return item

    def update(self, trans, id, group_id):
        """
        Adds a role to a group
        """
        role_id = id
        decoded_group_id = trans.security.decode_id(group_id)
        decoded_role_id = trans.security.decode_id(role_id)
        item = None
        try:
            group = trans.sa_session.query(trans.app.model.Group).get(decoded_group_id)
            role = trans.sa_session.query(trans.app.model.Role).get(decoded_role_id)
            for gra in group.roles:
                if gra.role == role:
                    item = dict(id=role_id,
                                name=role.name,
                                url=url_for('group_role', group_id=group_id, id=role_id))
            if not item:
                gra = trans.app.model.GroupRoleAssociation(group, role)
                # Add GroupRoleAssociation
                trans.sa_session.add(gra)
                trans.sa_session.flush()
                item = dict(id=role_id,
                            name=role.name,
                            url=url_for('group_role', group_id=group_id, id=role_id))
        except Exception as e:
            item = f"Error in group_role API Adding role {role.name} to group {group.name}"
            log.error(item + ": %s", unicodify(e))
        return item

    def delete(self, trans, id, group_id):
        """
        Removes a role from a group
        """
        role_id = id
        decoded_group_id = trans.security.decode_id(group_id)
        decoded_role_id = trans.security.decode_id(role_id)
        try:
            group = trans.sa_session.query(trans.app.model.Group).get(decoded_group_id)
            role = trans.sa_session.query(trans.app.model.Role).get(decoded_role_id)
            for gra in group.roles:
                if gra.role == role:
                    trans.sa_session.delete(gra)
                    trans.sa_session.flush()
                    item = dict(id=role_id,
                                name=role.name,
                                url=url_for('group_role', group_id=group_id, id=role_id))
            if not item:
                item = f"role {role.name} not in group {group.name}"
        except Exception as e:
            item = f"Error in group_role API Removing role {role.name} from group {group.name}"
            log.error(item + ": %s", unicodify(e))
        return item
