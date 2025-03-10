"""Tool Shed Security"""

import logging
from typing import List

from sqlalchemy import (
    false,
    select,
)

from galaxy.util import listify
from galaxy.util.bunch import Bunch
from tool_shed.webapp.model import (
    Group,
    Role,
)

IUC_NAME = "Intergalactic Utilities Commission"

log = logging.getLogger(__name__)


class Action:
    def __init__(self, action, description, model):
        self.action = action
        self.description = description
        self.model = model


class RBACAgent:
    """Handle Galaxy Tool Shed security"""

    permitted_actions = Bunch()

    def associate_components(self, **kwd):
        raise Exception(f"No valid method of associating provided components: {kwd}")

    def associate_user_role(self, user, role):
        raise Exception("No valid method of associating a user with a role")

    def convert_permitted_action_strings(self, permitted_action_strings):
        """
        When getting permitted actions from an untrusted source like a
        form, ensure that they match our actual permitted actions.
        """
        return [
            x
            for x in [self.permitted_actions.get(action_string) for action_string in permitted_action_strings]
            if x is not None
        ]

    def create_user_role(self, user, app):
        raise Exception("Unimplemented Method")

    def create_private_user_role(self, user):
        raise Exception("Unimplemented Method")

    def get_action(self, name, default=None):
        """Get a permitted action by its dict key or action name"""
        for k, v in self.permitted_actions.items():
            if k == name or v.action == name:
                return v
        return default

    def get_actions(self):
        """Get all permitted actions as a list of Action objects"""
        return list(self.permitted_actions.__dict__.values())

    def get_item_actions(self, action, item):
        raise Exception(f"No valid method of retrieving action ({action}) for item {item}.")

    def get_private_user_role(self, user):
        raise Exception("Unimplemented Method")


class CommunityRBACAgent(RBACAgent):
    def __init__(self, model, permitted_actions=None):
        self.model = model
        if permitted_actions:
            self.permitted_actions = permitted_actions

    @property
    def sa_session(self):
        """Returns a SQLAlchemy scoped session"""
        return self.model.context

    def allow_action(self, roles, action, item):
        """
        Method for checking a permission for the current user ( based on roles ) to perform a
        specific action on an item
        """
        item_actions = self.get_item_actions(action, item)
        if not item_actions:
            return action.model == "restrict"
        ret_val = False
        for item_action in item_actions:
            if item_action.role in roles:
                ret_val = True
                break
        return ret_val

    def associate_components(self, **kwd):
        if "user" in kwd:
            if "group" in kwd:
                return self.associate_user_group(kwd["user"], kwd["group"])
            elif "role" in kwd:
                return self.associate_user_role(kwd["user"], kwd["role"])
        elif "role" in kwd:
            if "group" in kwd:
                return self.associate_group_role(kwd["group"], kwd["role"])
        elif "repository" in kwd:
            return self.associate_repository_category(kwd["repository"], kwd["category"])
        raise Exception(f"No valid method of associating provided components: {kwd}")

    def associate_group_role(self, group, role):
        assoc = self.model.GroupRoleAssociation(group, role)
        self.sa_session.add(assoc)
        session = self.sa_session()
        session.commit()
        return assoc

    def associate_user_group(self, user, group):
        assoc = self.model.UserGroupAssociation(user, group)
        self.sa_session.add(assoc)
        session = self.sa_session()
        session.commit()
        return assoc

    def associate_user_role(self, user, role):
        assoc = self.model.UserRoleAssociation(user, role)
        self.sa_session.add(assoc)
        session = self.sa_session()
        session.commit()
        return assoc

    def associate_repository_category(self, repository, category):
        assoc = self.model.RepositoryCategoryAssociation(repository, category)
        self.sa_session.add(assoc)
        session = self.sa_session()
        session.commit()
        return assoc

    def create_private_user_role(self, user):
        # Create private role
        role = self.model.Role(
            name=user.email, description=f"Private Role for {user.email}", type=self.model.Role.types.PRIVATE
        )
        self.sa_session.add(role)
        session = self.sa_session()
        session.commit()
        # Add user to role
        self.associate_components(role=role, user=user)
        return role

    def create_user_role(self, user, app):
        self.get_private_user_role(user, auto_create=True)

    def get_item_actions(self, action, item):
        # item must be one of: Dataset, Library, LibraryFolder, LibraryDataset, LibraryDatasetDatasetAssociation
        return [permission for permission in item.actions if permission.action == action.action]

    def get_private_user_role(self, user, auto_create=False):
        role = _get_private_user_role(self.sa_session, user.email)
        if not role:
            if auto_create:
                return self.create_private_user_role(user)
            else:
                return None
        return role

    def set_entity_group_associations(self, groups=None, users=None, roles=None, delete_existing_assocs=True):
        if groups is None:
            groups = []
        if users is None:
            users = []
        if roles is None:
            roles = []
        for group in groups:
            if delete_existing_assocs:
                for a in group.roles + group.users:
                    self.sa_session.delete(a)
                    session = self.sa_session()
                    session.commit()
            for role in roles:
                self.associate_components(group=group, role=role)
            for user in users:
                self.associate_components(group=group, user=user)

    def set_entity_role_associations(
        self, roles=None, users=None, groups=None, repositories=None, delete_existing_assocs=True
    ):
        if roles is None:
            roles = []
        if users is None:
            users = []
        if groups is None:
            groups = []
        if repositories is None:
            repositories = []
        for role in roles:
            if delete_existing_assocs:
                for a in role.users + role.groups:
                    self.sa_session.delete(a)
                    session = self.sa_session()
                    session.commit()
            for user in users:
                self.associate_components(user=user, role=role)
            for group in groups:
                self.associate_components(group=group, role=role)

    def set_entity_user_associations(self, users=None, roles=None, groups=None, delete_existing_assocs=True):
        if users is None:
            users = []
        if roles is None:
            roles = []
        if groups is None:
            groups = []
        for user in users:
            if delete_existing_assocs:
                for a in user.non_private_roles + user.groups:
                    self.sa_session.delete(a)
                    session = self.sa_session()
                    session.commit()
            self.sa_session.refresh(user)
            for role in roles:
                # Make sure we are not creating an additional association with a PRIVATE role
                if role not in user.roles:
                    self.associate_components(user=user, role=role)
            for group in groups:
                self.associate_components(user=user, group=group)

    def usernames_that_can_push(self, repository) -> List[str]:
        return listify(repository.allow_push())

    def can_push(self, app, user, repository):
        if user:
            return user.username in self.usernames_that_can_push(repository)
        return False

    def user_can_administer_repository(self, user, repository):
        """Return True if the received user can administer the received repository."""
        if user:
            if repository:
                repository_admin_role = repository.admin_role
                for rra in repository.roles:
                    role = rra.role
                    if role.id == repository_admin_role.id:
                        # We have the repository's admin role, so see if the user is associated with it.
                        for ura in role.users:
                            role_member = ura.user
                            if role_member.id == user.id:
                                return True
                        # The user is not directly associated with the role, so see if they are a member
                        # of a group that is associated with the role.
                        for gra in role.groups:
                            group = gra.group
                            for uga in group.users:
                                member = uga.user
                                if member.id == user.id:
                                    return True
        return False

    def user_can_import_repository_archive(self, user, archive_owner):
        # This method should be called only if the current user is not an admin.
        if user.username == archive_owner:
            return True
        # A member of the IUC is authorized to create new repositories that are owned by another user.
        if (iuc_group := get_iuc_group(self.sa_session)) is not None:
            for uga in iuc_group.users:
                if uga.user.id == user.id:
                    return True
        return False


def get_permitted_actions(filter=None):
    """Utility method to return a subset of RBACAgent's permitted actions"""
    if filter is None:
        return RBACAgent.permitted_actions
    tmp_bunch = Bunch()
    [tmp_bunch.__dict__.__setitem__(k, v) for k, v in RBACAgent.permitted_actions.items() if k.startswith(filter)]
    return tmp_bunch


def get_iuc_group(session):
    stmt = select(Group).where(Group.name == IUC_NAME).where(Group.deleted == false()).limit(1)
    return session.scalars(stmt).first()


def _get_private_user_role(session, user_email):
    stmt = select(Role).where(Role.name == user_email).where(Role.type == Role.types.PRIVATE).limit(1)
    return session.scalars(stmt).first()
