import logging

import galaxy.exceptions
from galaxy import (
    model,
    security,
)
from galaxy.managers import users

log = logging.getLogger(__name__)


class RBACPermissionFailedException(galaxy.exceptions.InsufficientPermissionsException):
    pass


class RBACPermission:
    """
    Base class for wrangling/controlling the permissions ORM models (Permissions, Roles)
    that control which users can perform certain actions on their associated models
    (Libraries, Datasets).
    """

    permissions_class: type
    permission_failed_error_class = RBACPermissionFailedException

    def __init__(self, app):
        self.app = app
        self.user_manager = users.UserManager(app)

    def session(self):
        return self.app.model.context

    # TODO: implement group
    # TODO: how does admin play into this?
    def is_permitted(self, item, user, trans=None):
        raise NotImplementedError("abstract parent class")

    def error_unless_permitted(self, item, user, trans=None):
        if not self.is_permitted(item, user, trans=trans):
            error_info = dict(model_class=item.__class__, id=getattr(item, "id", None))
            raise self.permission_failed_error_class(**error_info)

    def grant(self, item, user, flush: bool = True):
        raise NotImplementedError("abstract parent class")

    def revoke(self, item, user, flush: bool = True):
        raise NotImplementedError("abstract parent class")

    def _role_is_permitted(self, item, role):
        raise NotImplementedError("abstract parent class")

    def _error_unless_role_permitted(self, item, role):
        if not self._role_is_permitted(item, role):
            error_info = dict(model_class=item.__class__, id=getattr(item, "id", None))
            raise self.permission_failed_error_class(**error_info)

    def _grant_role(self, item, role, flush=True):
        raise NotImplementedError("abstract parent class")

    def _revoke_role(self, item, role, flush=True):
        raise NotImplementedError("abstract parent class")


class DatasetRBACPermission(RBACPermission):
    """
    Base class for the manage and access RBAC permissions used by dataset security.

    The DatasetPermissions used by the RBAC agent are associations between a Dataset
    and a single Role.

    DatasetPermissions are typed (but not polymorphic themselves) by a string 'action'.
    There are two types:

    - manage permissions : can a role manage the permissions on a dataset
    - access : can a role read/look at/copy a dataset
    """

    permissions_class = model.DatasetPermissions
    action_name = None

    # ---- double secrect probation
    def __assert_action(self):
        if not self.action_name:
            raise NotImplementedError("abstract parent class needs action_name")

    # ---- interface
    def by_dataset(self, dataset):
        self.__assert_action()
        all_permissions = self._all_types_by_dataset(dataset)
        return list(filter(lambda p: p.action == self.action_name, all_permissions))

    def by_roles(self, dataset, roles):
        permissions = self.by_dataset(dataset)
        return list(filter(lambda p: p.role in roles, permissions))

    def by_role(self, dataset, role):
        permissions = self.by_dataset(dataset)
        found = list(filter(lambda p: p.role == role, permissions))
        if not found:
            return None
        if len(found) > 1:
            raise galaxy.exceptions.InconsistentDatabase(dataset=dataset.id, role=role.id)
        return found[0]

    def set(self, dataset, roles, flush=True):
        # NOTE: this removes all previous permissions of this type
        self.clear(dataset, flush=False)
        permissions = []
        for role in roles:
            permissions.append(self._create(dataset, role, flush=False))
        if flush:
            session = self.session()
            session.commit()
        return permissions

    def clear(self, dataset, flush=True):
        permissions = self.by_dataset(dataset)
        return self._delete(permissions, flush=flush)

    # ---- private
    def _create(self, dataset, role, flush=True):
        permission = self.permissions_class(self.action_name, dataset, role)
        self.session().add(permission)
        if flush:
            session = self.session()
            session.commit()
        return permission

    def _roles(self, dataset):
        return [permission.role for permission in self.by_dataset(dataset)]

    def _all_types_by_dataset(self, dataset):
        return dataset.actions

    # as a general rule, DatasetPermissions are considered disposable
    #   and there is no reason to update the models

    # TODO: list?
    def _delete(self, permissions, flush=True):
        for permission in permissions:
            if permission in self.session().new:
                self.session().expunge(permission)
            else:
                self.session().delete(permission)
        if flush:
            session = self.session()
            session.commit()

    def _revoke_role(self, dataset, role, flush=True):
        role_permissions = self.by_roles(dataset, [role])
        return self._delete(role_permissions, flush=flush)


def iterable_has_all(iterable, has_these):
    for item in has_these:
        if item not in iterable:
            return False
    return True


class DatasetManagePermissionFailedException(RBACPermissionFailedException):
    pass


class ManageDatasetRBACPermission(DatasetRBACPermission):
    """
    A class that controls the dataset permissions that control
    who can manage that dataset's permissions.

    When checking permissions for a user, if any of the user's roles
    have permission on the dataset
    """

    # TODO: We may also be able to infer/record the dataset 'owner' as well.
    action_name = security.RBACAgent.permitted_actions.get("DATASET_MANAGE_PERMISSIONS").action
    permission_failed_error_class = DatasetManagePermissionFailedException

    # ---- interface
    def is_permitted(self, dataset, user, trans=None):
        if trans and trans.user_is_admin:
            return True

        # anonymous users cannot manage permissions on datasets
        if self.user_manager.is_anonymous(user):
            return False
        # admin is always permitted
        # TODO: could probably move this into RBACPermission and call that first
        if self.user_manager.is_admin(user):
            return True
        for role in user.all_roles():
            if self._role_is_permitted(dataset, role):
                return True
        return False

    def grant(self, item, user, flush: bool = True):
        private_role = self._user_private_role(user)
        return self._grant_role(item, private_role, flush=flush)

    def revoke(self, item, user, flush: bool = True):
        private_role = self._user_private_role(user)
        return self._revoke_role(item, private_role, flush=flush)

    # ---- private
    def _role_is_permitted(self, dataset, role):
        return role in self._roles(dataset)

    def _user_private_role(self, user):
        # error with 401 if no user
        self.user_manager.error_if_anonymous(user)
        return self.user_manager.private_role(user)

    def _grant_role(self, dataset, role, flush=True):
        if existing := self.by_role(dataset, role):
            return existing
        return self._create(dataset, role, flush=flush)

    def _revoke_role(self, dataset, role, flush=True):
        permission = self.by_roles(dataset, [role])
        return self._delete([permission], flush=flush)


class DatasetAccessPermissionFailedException(RBACPermissionFailedException):
    pass


class AccessDatasetRBACPermission(DatasetRBACPermission):
    """
    A class to manage access permissions on a dataset.

    An user must have all the Roles of all the access permissions associated
    with a dataset in order to access it.
    """

    action_name = security.RBACAgent.permitted_actions.get("DATASET_ACCESS").action
    permission_failed_error_class = DatasetAccessPermissionFailedException

    # ---- interface
    def is_permitted(self, dataset, user, trans=None):
        if trans and trans.user_is_admin:
            return True

        current_roles = self._roles(dataset)
        # NOTE: that because of short circuiting this allows
        #   anonymous access to public datasets
        return (
            self._is_public_based_on_roles(current_roles)
            or self.user_manager.is_admin(user)  # admin is always permitted
            or self._user_has_all_roles(user, current_roles)
        )

    def grant(self, item, user, flush: bool = True):
        pass
        # not so easy
        # need to check for a sharing role
        # then add the new user to it

    def revoke(self, item, user, flush: bool = True):
        pass
        # not so easy

    # TODO: these are a lil off message
    def is_public(self, dataset):
        current_roles = self._roles(dataset)
        return self._is_public_based_on_roles(current_roles)

    def set_private(self, dataset, user, flush=True):
        private_role = self.user_manager.private_role(user)
        return self.set(dataset, [private_role], flush=flush)

    # ---- private
    def _is_public_based_on_roles(self, roles):
        return len(roles) == 0

    def _user_has_all_roles(self, user, roles):
        user_roles = []
        if not self.user_manager.is_anonymous(user):
            user_roles = user.all_roles()
        return iterable_has_all(user_roles, roles)

    def _role_is_permitted(self, dataset, role):
        current_roles = self._roles(dataset)
        return (
            self._is_public_based_on_roles(current_roles)
            # if there's only one role and this is it, let em in
            or ((len(current_roles) == 1) and (role == current_roles[0]))
        )
