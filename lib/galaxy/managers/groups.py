from typing import (
    Any,
    Dict,
)

from sqlalchemy import false

from galaxy import model
from galaxy.managers.context import ProvidesAppContext
from galaxy.schema.fields import EncodedDatabaseIdField
from galaxy.web import url_for


class GroupsManager:
    """Interface/service object shared by controllers for interacting with groups."""

    def index(self, trans: ProvidesAppContext):
        """
        Displays a collection (list) of groups.
        """
        rval = []
        for group in trans.sa_session.query(model.Group).filter(model.Group.table.c.deleted == false()):
            if trans.user_is_admin:
                item = group.to_dict(value_mapper={'id': trans.security.encode_id})
                encoded_id = trans.security.encode_id(group.id)
                item['url'] = url_for('group', id=encoded_id)
                rval.append(item)
        return rval

    def create(self, trans: ProvidesAppContext, payload: Dict[str, Any]):
        """
        Creates a new group.
        """
        if not trans.user_is_admin:
            trans.response.status = 403
            return "You are not authorized to create a new group."
        name = payload.get('name', None)
        if not name:
            trans.response.status = 400
            return "Enter a valid name"
        if trans.sa_session.query(model.Group).filter(model.Group.table.c.name == name).first():
            trans.response.status = 400
            return "A group with that name already exists"

        group = model.Group(name=name)
        trans.sa_session.add(group)
        user_ids = payload.get('user_ids', [])
        users = [trans.sa_session.query(model.User).get(trans.security.decode_id(i)) for i in user_ids]
        role_ids = payload.get('role_ids', [])
        roles = [trans.sa_session.query(model.Role).get(trans.security.decode_id(i)) for i in role_ids]
        trans.app.security_agent.set_entity_group_associations(groups=[group], roles=roles, users=users)
        """
        # Create the UserGroupAssociations
        for user in users:
            trans.app.security_agent.associate_user_group( user, group )
        # Create the GroupRoleAssociations
        for role in roles:
            trans.app.security_agent.associate_group_role( group, role )
        """
        trans.sa_session.flush()
        encoded_id = trans.security.encode_id(group.id)
        item = group.to_dict(view='element', value_mapper={'id': trans.security.encode_id})
        item['url'] = url_for('group', id=encoded_id)
        return [item]

    def show(self, trans: ProvidesAppContext, id: EncodedDatabaseIdField):
        """
        Displays information about a group.
        """
        group_id = id
        try:
            decoded_group_id = trans.security.decode_id(group_id)
        except TypeError:
            trans.response.status = 400
            return "Malformed group id ( %s ) specified, unable to decode." % str(group_id)
        try:
            group = trans.sa_session.query(model.Group).get(decoded_group_id)
        except Exception:
            group = None
        if not group:
            trans.response.status = 400
            return "Invalid group id ( %s ) specified." % str(group_id)
        item = group.to_dict(view='element', value_mapper={'id': trans.security.encode_id})
        item['url'] = url_for('group', id=group_id)
        item['users_url'] = url_for('group_users', group_id=group_id)
        item['roles_url'] = url_for('group_roles', group_id=group_id)
        return item

    def update(self, trans: ProvidesAppContext, id: EncodedDatabaseIdField, payload: Dict[str, Any]):
        """
        Modifies a group.
        """
        group_id = id
        try:
            decoded_group_id = trans.security.decode_id(group_id)
        except TypeError:
            trans.response.status = 400
            return "Malformed group id ( %s ) specified, unable to decode." % str(group_id)
        try:
            group = trans.sa_session.query(model.Group).get(decoded_group_id)
        except Exception:
            group = None
        if not group:
            trans.response.status = 400
            return "Invalid group id ( %s ) specified." % str(group_id)
        name = payload.get('name', None)
        if name:
            group.name = name
            trans.sa_session.add(group)
        user_ids = payload.get('user_ids', [])
        users = [trans.sa_session.query(model.User).get(trans.security.decode_id(i)) for i in user_ids]
        role_ids = payload.get('role_ids', [])
        roles = [trans.sa_session.query(model.Role).get(trans.security.decode_id(i)) for i in role_ids]
        trans.app.security_agent.set_entity_group_associations(groups=[group], roles=roles, users=users, delete_existing_assocs=False)
        trans.sa_session.flush()
