"""
Manager and Serializer for TS groups.
"""

import logging

from sqlalchemy import (
    false,
    select,
    true,
)
from sqlalchemy.exc import (
    MultipleResultsFound,
    NoResultFound,
)

from galaxy.exceptions import (
    Conflict,
    InconsistentDatabase,
    InternalServerError,
    ItemAccessibilityException,
    ObjectNotFound,
    RequestParameterInvalidException,
)
from tool_shed.webapp.model import Group

log = logging.getLogger(__name__)


class GroupManager:
    """
    Interface/service object for interacting with TS groups.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get(self, trans, decoded_group_id=None, name=None):
        """
        Get the group from the DB based on its ID or name.

        :param  decoded_group_id:       decoded group id
        :type   decoded_group_id:       int

        :returns:   the requested group
        :rtype:     tool_shed.model.Group
        """
        if decoded_group_id is None and name is None:
            raise RequestParameterInvalidException("You must supply either ID or a name of the group.")

        try:
            if decoded_group_id:
                group = trans.sa_session.get(Group, decoded_group_id)
            else:
                group = get_group_by_name(trans.sa_session, name, Group)
        except MultipleResultsFound:
            raise InconsistentDatabase("Multiple groups found with the same identifier.")
        except NoResultFound:
            raise ObjectNotFound("No group found with the identifier provided.")
        except Exception:
            raise InternalServerError("Error loading from the database.")
        return group

    def create(self, trans, name, description=""):
        """
        Create a new group.
        """
        if not trans.user_is_admin:
            raise ItemAccessibilityException("Only administrators can create groups.")
        else:
            if self.get(trans, name=name):
                raise Conflict(f"Group with the given name already exists. Name: {str(name)}")
            # TODO add description field to the model
            group = Group(name=name)
            trans.sa_session.add(group)
            trans.sa_session.commit()
            return group

    def update(self, trans, group, name=None, description=None):
        """
        Update the given group
        """
        changed = False
        if not trans.user_is_admin:
            raise ItemAccessibilityException("Only administrators can update groups.")
        if group.deleted:
            raise RequestParameterInvalidException("You cannot modify a deleted group. Undelete it first.")
        if name is not None:
            group.name = name
            changed = True
        if description is not None:
            group.description = description
            changed = True
        if changed:
            trans.sa_session.add(group)
            trans.sa_session.commit()
        return group

    def delete(self, trans, group, undelete=False):
        """
        Mark given group deleted/undeleted based on the flag.
        """
        if not trans.user_is_admin:
            raise ItemAccessibilityException("Only administrators can delete and undelete groups.")
        if undelete:
            group.deleted = False
        else:
            group.deleted = True
        trans.sa_session.add(group)
        trans.sa_session.commit()
        return group

    def list(self, trans, deleted=False):
        """
        Return a list of groups from the DB.

        :returns: query that will emit all groups
        :rtype:   sqlalchemy query
        """
        stmt = select(Group)
        if trans.user_is_admin:
            if deleted is None:
                #  Flag is not specified, do not filter on it.
                pass
            elif deleted:
                stmt = stmt.where(Group.deleted == true())
            else:
                stmt = stmt.where(Group.deleted == false())
        else:
            stmt = stmt.where(Group.deleted == false())
        return trans.sa_session.scalars(stmt)


def get_group_by_name(session, name, group_model):
    stmt = select(group_model).where(group_model.name == name)
    return session.execute(stmt).scalar_one()
