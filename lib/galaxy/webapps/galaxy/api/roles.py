"""
API operations on Role objects.
"""
import logging

from sqlalchemy import false

from galaxy import web
from galaxy.web.base.controller import BaseAPIController, url_for

log = logging.getLogger(__name__)


class RoleAPIController(BaseAPIController):

    @web.expose_api
    def index(self, trans, **kwd):
        """
        GET /api/roles
        Displays a collection (list) of roles.
        """
        rval = []
        for role in trans.sa_session.query(trans.app.model.Role).filter(trans.app.model.Role.table.c.deleted == false()):
            if trans.user_is_admin or trans.app.security_agent.ok_to_display(trans.user, role):
                item = role.to_dict(value_mapper={'id': trans.security.encode_id})
                encoded_id = trans.security.encode_id(role.id)
                item['url'] = url_for('role', id=encoded_id)
                rval.append(item)
        return rval

    @web.expose_api
    def show(self, trans, id, **kwd):
        """
        GET /api/roles/{encoded_role_id}
        Displays information about a role.
        """
        role_id = id
        try:
            decoded_role_id = trans.security.decode_id(role_id)
        except Exception:
            trans.response.status = 400
            return "Malformed role id ( %s ) specified, unable to decode." % str(role_id)
        try:
            role = trans.sa_session.query(trans.app.model.Role).get(decoded_role_id)
        except Exception:
            role = None
        if not role or not (trans.user_is_admin or trans.app.security_agent.ok_to_display(trans.user, role)):
            trans.response.status = 400
            return "Invalid role id ( %s ) specified." % str(role_id)
        item = role.to_dict(view='element', value_mapper={'id': trans.security.encode_id})
        item['url'] = url_for('role', id=role_id)
        return item

    @web.expose_api
    def create(self, trans, payload, **kwd):
        """
        POST /api/roles
        Creates a new role.
        """
        if not trans.user_is_admin:
            trans.response.status = 403
            return "You are not authorized to create a new role."
        name = payload.get('name', None)
        description = payload.get('description', None)
        if not name or not description:
            trans.response.status = 400
            return "Enter a valid name and a description"
        if trans.sa_session.query(trans.app.model.Role).filter(trans.app.model.Role.table.c.name == name).first():
            trans.response.status = 400
            return "A role with that name already exists"

        role_type = trans.app.model.Role.types.ADMIN  # TODO: allow non-admins to create roles

        role = trans.app.model.Role(name=name, description=description, type=role_type)
        trans.sa_session.add(role)
        user_ids = payload.get('user_ids', [])
        users = [trans.sa_session.query(trans.model.User).get(trans.security.decode_id(i)) for i in user_ids]
        group_ids = payload.get('group_ids', [])
        groups = [trans.sa_session.query(trans.model.Group).get(trans.security.decode_id(i)) for i in group_ids]

        # Create the UserRoleAssociations
        for user in users:
            trans.app.security_agent.associate_user_role(user, role)

        # Create the GroupRoleAssociations
        for group in groups:
            trans.app.security_agent.associate_group_role(group, role)

        trans.sa_session.flush()
        encoded_id = trans.security.encode_id(role.id)
        item = role.to_dict(view='element', value_mapper={'id': trans.security.encode_id})
        item['url'] = url_for('role', id=encoded_id)
        return [item]
