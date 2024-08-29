import logging
import socket
import sqlite3
from datetime import (
    datetime,
    timedelta,
)
from typing import (
    List,
    Optional,
)

from sqlalchemy import (
    and_,
    delete,
    false,
    func,
    insert,
    not_,
    or_,
    select,
    text,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

import galaxy.model
from galaxy.exceptions import RequestParameterInvalidException
from galaxy.model import (
    Dataset,
    DatasetCollection,
    DatasetPermissions,
    DefaultHistoryPermissions,
    DefaultUserPermissions,
    Group,
    GroupRoleAssociation,
    HistoryDatasetAssociationDisplayAtAuthorization,
    Library,
    LibraryDataset,
    LibraryDatasetCollectionAssociation,
    LibraryDatasetDatasetAssociation,
    LibraryDatasetDatasetAssociationPermissions,
    LibraryDatasetPermissions,
    LibraryFolder,
    LibraryFolderPermissions,
    LibraryPermissions,
    Role,
    User,
    UserGroupAssociation,
    UserRoleAssociation,
)
from galaxy.model.base import transaction
from galaxy.model.db.role import (
    get_npns_roles,
    get_private_user_role,
)
from galaxy.security import (
    Action,
    get_permitted_actions,
    RBACAgent,
)
from galaxy.util import listify
from galaxy.util.bunch import Bunch

log = logging.getLogger(__name__)


class GalaxyRBACAgent(RBACAgent):
    def __init__(self, sa_session, permitted_actions=None):
        self.sa_session = sa_session
        if permitted_actions:
            self.permitted_actions = permitted_actions
        # List of "library_item" objects and their associated permissions and info template objects
        self.library_item_assocs = (
            (Library, LibraryPermissions),
            (LibraryFolder, LibraryFolderPermissions),
            (LibraryDataset, LibraryDatasetPermissions),
            (LibraryDatasetDatasetAssociation, LibraryDatasetDatasetAssociationPermissions),
        )

    def sort_by_attr(self, seq, attr):
        """
        Sort the sequence of objects by object's attribute
        Arguments:
        seq  - the list or any sequence (including immutable one) of objects to sort.
        attr - the name of attribute to sort by
        """
        # Use the "Schwartzian transform"
        # Create the auxiliary list of tuples where every i-th tuple has form
        # (seq[i].attr, i, seq[i]) and sort it. The second item of tuple is needed not
        # only to provide stable sorting, but mainly to eliminate comparison of objects
        # (which can be expensive or prohibited) in case of equal attribute values.
        intermed = [(getattr(v, attr), i, v) for i, v in enumerate(seq)]
        intermed.sort()
        return [_[-1] for _ in intermed]

    def get_all_roles(self, trans, cntrller):
        admin_controller = cntrller in ["library_admin"]
        roles = set()
        if not trans.user:
            return get_npns_roles(trans.sa_session)
        if admin_controller:
            # The library is public and the user is an admin, so all roles are legitimate
            stmt = select(Role).where(Role.deleted == false()).order_by(Role.name)
            for role in trans.sa_session.scalars(stmt):
                roles.add(role)
        else:
            # Add the current user's private role
            roles.add(self.get_private_user_role(trans.user))
            # Add the current user's sharing roles
            for role in self.get_sharing_roles(trans.user):
                roles.add(role)
            # Add all remaining non-private, non-sharing roles
            for role in get_npns_roles(trans.sa_session):
                roles.add(role)
        return self.sort_by_attr(list(roles), "name")

    def get_roles_for_action(self, item, action):
        """
        Return a list containing the roles associated with given action on given item
        where item is one of Library, LibraryFolder, LibraryDatasetDatasetAssociation,
        LibraryDataset, Dataset.
        """
        roles = []
        for item_permission in item.actions:
            permission_action = self.get_action(item_permission.action)
            if permission_action == action:
                roles.append(item_permission.role)
        return roles

    def get_valid_roles(self, trans, item, query=None, page=None, page_limit=None, is_library_access=False):
        """
        This method retrieves the list of possible roles that user can select
        in the item permissions form. Admins can select any role so the
        results are paginated in order to save the bandwidth and to speed
        things up.
        Standard users can select their own private role, any of their
        sharing roles and any public role (not private and not sharing).
        """
        roles = []
        if query not in [None, ""]:
            query = query.strip().replace("_", "/_").replace("%", "/%").replace("/", "//")
            search_query = f"{query}%"
        else:
            search_query = None
        # Limit the query only to get the page needed
        if page is not None and page_limit is not None:
            limit = page * page_limit
        else:
            limit = None
        total_count = None
        if isinstance(item, Library) and self.library_is_public(item):
            is_public_item = True
        elif isinstance(item, Dataset) and self.dataset_is_public(item):
            is_public_item = True
        elif isinstance(item, LibraryFolder):
            is_public_item = True
        else:
            is_public_item = False
        # Admins can always choose from all non-deleted roles
        if trans.user_is_admin or trans.app.config.expose_user_email:
            if trans.user_is_admin:
                stmt = select(Role).where(Role.deleted == false())
            else:
                # User is not an admin but the configuration exposes all private roles to all users.
                stmt = select(Role).where(and_(Role.deleted == false(), Role.type == Role.types.PRIVATE))
            if search_query:
                stmt = stmt.where(Role.name.like(search_query, escape="/"))

            count_stmt = select(func.count()).select_from(stmt)
            total_count = trans.sa_session.scalar(count_stmt)

            if limit is not None:
                # Takes the least number of results from beginning that includes the requested page
                stmt = stmt.order_by(Role.name).limit(limit)
                page_start = (page * page_limit) - page_limit
                page_end = page_start + page_limit
                if total_count < page_start + 1:
                    # Return empty list if there are less results than the requested position
                    roles = []
                else:
                    roles = trans.sa_session.scalars(stmt).all()
                    roles = roles[page_start:page_end]
            else:
                stmt = stmt.order_by(Role.name)
                roles = trans.sa_session.scalars(stmt).all()
        # Non-admin and public item
        elif is_public_item:
            # Add the current user's private role
            roles.append(self.get_private_user_role(trans.user))
            # Add the current user's sharing roles
            for role in self.get_sharing_roles(trans.user):
                roles.append(role)
            # Add all remaining non-private, non-sharing roles
            for role in get_npns_roles(trans.sa_session):
                roles.append(role)
        # User will see all the roles derived from the access roles on the item
        else:
            # If item has roles associated with the access permission, we need to start with them.
            access_roles = item.get_access_roles(self)
            for role in access_roles:
                if self.ok_to_display(trans.user, role):
                    roles.append(role)
                    # Each role potentially has users.  We need to find all roles that each of those users have.
                    for ura in role.users:
                        user = ura.user
                        for ura2 in user.roles:
                            if self.ok_to_display(trans.user, ura2.role):
                                roles.append(ura2.role)
                    # Each role also potentially has groups which, in turn, have members ( users ).  We need to
                    # find all roles that each group's members have.
                    for gra in role.groups:
                        group = gra.group
                        for uga in group.users:
                            user = uga.user
                            for ura in user.roles:
                                if self.ok_to_display(trans.user, ura.role):
                                    roles.append(ura.role)

        # Omit duplicated roles by converting to set
        return_roles = set(roles)
        if total_count is None:
            total_count = len(return_roles)
        return self.sort_by_attr(list(return_roles), "name"), total_count

    def get_legitimate_roles(self, trans, item, cntrller):
        """
        Return a sorted list of legitimate roles that can be associated with a permission on
        item where item is a Library or a Dataset.  The cntrller param is the controller from
        which the request is sent.  We cannot use trans.user_is_admin because the controller is
        what is important since admin users do not necessarily have permission to do things
        on items outside of the admin view.

        If cntrller is from the admin side ( e.g., library_admin ):

            - if item is public, all roles, including private roles, are legitimate.
            - if item is restricted, legitimate roles are derived from the users and groups associated
              with each role that is associated with the access permission ( i.e., DATASET_MANAGE_PERMISSIONS or
              LIBRARY_MANAGE ) on item.  Legitimate roles will include private roles.

        If cntrller is not from the admin side ( e.g., root, library ):

            - if item is public, all non-private roles, except for the current user's private role,
              are legitimate.
            - if item is restricted, legitimate roles are derived from the users and groups associated
              with each role that is associated with the access permission on item.  Private roles, except
              for the current user's private role, will be excluded.
        """
        admin_controller = cntrller in ["library_admin"]
        roles = set()
        if (isinstance(item, Library) and self.library_is_public(item)) or (
            isinstance(item, Dataset) and self.dataset_is_public(item)
        ):
            return self.get_all_roles(trans, cntrller)
        # If item has roles associated with the access permission, we need to start with them.
        access_roles = item.get_access_roles(self)
        for role in access_roles:
            if admin_controller or self.ok_to_display(trans.user, role):
                roles.add(role)
                # Each role potentially has users.  We need to find all roles that each of those users have.
                for ura in role.users:
                    user = ura.user
                    for ura2 in user.roles:
                        if admin_controller or self.ok_to_display(trans.user, ura2.role):
                            roles.add(ura2.role)
                # Each role also potentially has groups which, in turn, have members ( users ).  We need to
                # find all roles that each group's members have.
                for gra in role.groups:
                    group = gra.group
                    for uga in group.users:
                        user = uga.user
                        for ura in user.roles:
                            if admin_controller or self.ok_to_display(trans.user, ura.role):
                                roles.add(ura.role)
        return self.sort_by_attr(list(roles), "name")

    def ok_to_display(self, user, role):
        """
        Method for checking if:
        - a role is private and is the current user's private role
        - a role is a sharing role and belongs to the current user
        """
        role_type = role.type
        if user:
            if role_type == Role.types.PRIVATE:
                return role == self.get_private_user_role(user)
            if role_type == Role.types.SHARING:
                return role in self.get_sharing_roles(user)
            # If role_type is neither private nor sharing, it's ok to display
            return True
        return role_type != Role.types.PRIVATE and role_type != Role.types.SHARING

    def allow_action(self, roles, action, item):
        """
        Method for checking a permission for the current user ( based on roles ) to perform a
        specific action on an item, which must be one of:
        Dataset, Library, LibraryFolder, LibraryDataset, LibraryDatasetDatasetAssociation
        """
        # SM: Note that calling get_item_actions will emit a query.
        item_actions = self.get_item_actions(action, item)

        if not item_actions:
            return action.model == "restrict"
        ret_val = False
        # For DATASET_ACCESS only, user must have ALL associated roles
        if action == self.permitted_actions.DATASET_ACCESS:
            for item_action in item_actions:
                if item_action.role not in roles:
                    break
            else:
                ret_val = True
        # For remaining actions, user must have any associated role
        else:
            for item_action in item_actions:
                if item_action.role in roles:
                    ret_val = True
                    break
        return ret_val

    def get_actions_for_items(self, trans, action, permission_items):
        # TODO: Rename this; it's a replacement for get_item_actions, but it
        # doesn't represent what it's really doing, which is confusing.
        # TODO: Make this work for other classes besides lib_datasets.
        # That should be as easy as checking the type and writing a query for each;
        # we're avoiding using the SQLAlchemy backrefs because they can cause lots
        # of queries to be generated.
        #
        # Originally, get_item_actions did:
        # return [ permission for permission in item.actions if permission.action == action.action ]
        # The "item" can be just about anything with permissions, and referencing
        # item.actions causes the item's permissions to be retrieved.
        # This method will retrieve all permissions for all "items" and only
        # return the permissions associated with that given action.
        # We initialize the permissions list to be empty; we will return an
        # empty list by default.
        #
        # If the dataset id has no corresponding action in its permissions,
        # then the returned permissions will not carry an entry for the dataset.
        ret_permissions = {}
        if len(permission_items) > 0:
            # SM: NB: LibraryDatasets became Datasets for some odd reason.
            if isinstance(permission_items[0], LibraryDataset):
                ids = [item.library_dataset_id for item in permission_items]
                stmt = select(LibraryDatasetPermissions).where(
                    and_(
                        LibraryDatasetPermissions.library_dataset_id.in_(ids),
                        LibraryDatasetPermissions.action == action.action,
                    )
                )
                permissions = trans.sa_session.scalars(stmt)
                # Massage the return data. We will return a list of permissions
                # for each library dataset. So we initialize the return list to
                # have an empty list for each dataset. Then each permission is
                # appended to the right lib dataset.
                # TODO: Consider eliminating the initialization and just return
                # empty values for each library dataset id.
                for item in permission_items:
                    ret_permissions[item.library_dataset_id] = []
                for permission in permissions:
                    ret_permissions[permission.library_dataset_id].append(permission)
            elif isinstance(permission_items[0], Dataset):
                ids = [item.id for item in permission_items]

                stmt = select(DatasetPermissions).where(
                    and_(DatasetPermissions.dataset_id.in_(ids), DatasetPermissions.action == action.action)
                )
                permissions = trans.sa_session.scalars(stmt)
                # Massage the return data. We will return a list of permissions
                # for each library dataset. So we initialize the return list to
                # have an empty list for each dataset. Then each permission is
                # appended to the right lib dataset.
                # TODO: Consider eliminating the initialization and just return
                # empty values for each library dataset id.
                for item in permission_items:
                    ret_permissions[item.id] = []
                for permission in permissions:
                    ret_permissions[permission.dataset_id].append(permission)

        # Test that we get the same response from get_item_actions each item:
        test_code = False
        if test_code:
            try:
                log.debug("get_actions_for_items: Test start")
                for item in permission_items:
                    base_result = self.get_item_actions(action, item)
                    new_result = ret_permissions[item.library_dataset_id]
                    # For now, just test against LibraryDatasetIds; other classes
                    # are not tested yet.
                    if len(base_result) == len(new_result):
                        common_result = set(base_result).intersection(new_result)
                        if len(common_result) == len(base_result):
                            log.debug("Match on permissions for id %d" % item.library_dataset_id)
                        # TODO: Fix this failure message:
                        else:
                            log.debug(
                                "Error: dataset %d; originally: %s; now: %s"
                                % (item.library_dataset_id, base_result, new_result)
                            )
                    else:
                        log.debug(
                            "Error: dataset %d: had %d entries, now %d entries"
                            % (item.library_dataset_id, len(base_result), len(new_result))
                        )
                log.debug("get_actions_for_items: Test end")
            except Exception as e:
                log.debug(f"Exception in test code: {e}")

        return ret_permissions

    def allow_action_on_libitems(self, trans, user_roles, action, items):
        """
        This should be the equivalent of allow_action defined on multiple items.
        It is meant to specifically replace allow_action for multiple
        LibraryDatasets, but it could be reproduced or modified for
        allow_action's permitted classes - Dataset, Library, LibraryFolder, and
        LDDAs.
        """
        all_items_actions = self.get_actions_for_items(trans, action, items)
        ret_allow_action = {}

        # Change item to lib_dataset or vice-versa.
        for item in items:
            if item.id in all_items_actions:
                item_actions = all_items_actions[item.id]

                if self.permitted_actions.DATASET_ACCESS == action:
                    ret_allow_action[item.id] = True
                    for item_action in item_actions:
                        if item_action.role not in user_roles:
                            ret_allow_action[item.id] = False
                            break

                # Else look for just one dataset role to be in the list of
                # acceptable user roles:
                else:
                    ret_allow_action[item.id] = False
                    for item_action in item_actions:
                        if item_action.role in user_roles:
                            ret_allow_action[item.id] = True
                            break

            else:
                if "restrict" == action.model:
                    ret_allow_action[item.id] = True
                else:
                    ret_allow_action[item.id] = False

        # Test it: the result for each dataset should match the result for
        # allow_action:
        test_code = False
        if test_code:
            log.debug("allow_action_for_items: test start")
            for item in items:
                orig_value = self.allow_action(user_roles, action, item)
                if orig_value == ret_allow_action[item.id]:
                    log.debug("Item %d: success" % item.id)
                else:
                    log.debug("Item %d: fail: original: %s; new: %s" % (item.id, orig_value, ret_allow_action[item.id]))
            log.debug("allow_action_for_items: test end")
        return ret_allow_action

    # DELETEME: SM: DO NOT TOUCH! This actually works.
    def dataset_access_mapping(self, trans, user_roles, datasets):
        """
        For the given list of datasets, return a mapping of the datasets' ids
        to whether they can be accessed by the user or not. The datasets input
        is expected to be a simple list of Dataset objects.
        """
        datasets_public_map = self.datasets_are_public(trans, datasets)
        datasets_allow_action_map = self.allow_action_on_libitems(
            trans, user_roles, self.permitted_actions.DATASET_ACCESS, datasets
        )
        can_access = {}
        for dataset in datasets:
            can_access[dataset.id] = datasets_public_map[dataset.id] or datasets_allow_action_map[dataset.id]
        return can_access

    def dataset_permission_map_for_access(self, trans, user_roles, libitems):
        """
        For a given list of library items (e.g., Datasets), return a map of the
        datasets' ids to whether they can have permission to use that action
        (e.g., "access" or "modify") on the dataset. The libitems input is
        expected to be a simple list of library items, such as Datasets or
        LibraryDatasets.
        NB: This is currently only usable for Datasets; it was intended to
        be used for any library item.
        """
        # Map the library items to whether they are publicly accessible or not.
        # Then determine what actions are allowed on the item (in case it's not
        # public). Finally, the item is accessible if it's publicly available
        # or the right permissions are enabled.
        # TODO: This only works for Datasets; other code is using X_is_public,
        # so this will have to be rewritten to support other items.
        libitems_public_map = self.datasets_are_public(trans, libitems)
        libitems_allow_action_map = self.allow_action_on_libitems(
            trans, user_roles, self.permitted_actions.DATASET_ACCESS, libitems
        )
        can_access = {}
        for libitem in libitems:
            can_access[libitem.id] = libitems_public_map[libitem.id] or libitems_allow_action_map[libitem.id]
        return can_access

    def item_permission_map_for_modify(self, trans, user_roles, libitems):
        return self.allow_action_on_libitems(trans, user_roles, self.permitted_actions.LIBRARY_MODIFY, libitems)

    def item_permission_map_for_manage(self, trans, user_roles, libitems):
        return self.allow_action_on_libitems(trans, user_roles, self.permitted_actions.LIBRARY_MANAGE, libitems)

    def item_permission_map_for_add(self, trans, user_roles, libitems):
        return self.allow_action_on_libitems(trans, user_roles, self.permitted_actions.LIBRARY_ADD, libitems)

    def can_access_dataset(self, user_roles, dataset: Dataset):
        # SM: dataset_is_public will access dataset.actions, which is a
        # backref that causes a query to be made to DatasetPermissions
        retval = self.dataset_is_public(dataset) or self.allow_action(
            user_roles, self.permitted_actions.DATASET_ACCESS, dataset
        )
        return retval

    def can_access_datasets(self, user_roles, action_tuples):
        user_role_ids = [galaxy.model.cached_id(r) for r in user_roles]

        # For DATASET_ACCESS, user must have ALL associated roles
        for action, user_role_id in action_tuples:
            if action == self.permitted_actions.DATASET_ACCESS.action:
                if user_role_id not in user_role_ids:
                    return False

        return True

    def can_access_collection(self, user_roles: List[Role], collection: DatasetCollection):
        action_tuples = collection.dataset_action_tuples
        if not self.can_access_datasets(user_roles, action_tuples):
            return False
        return True

    def can_manage_dataset(self, roles, dataset):
        return self.allow_action(roles, self.permitted_actions.DATASET_MANAGE_PERMISSIONS, dataset)

    def can_access_library(self, roles, library):
        return self.library_is_public(library) or self.allow_action(
            roles, self.permitted_actions.LIBRARY_ACCESS, library
        )

    def get_accessible_libraries(self, trans, user):
        """Return all data libraries that the received user can access"""
        accessible_libraries = []
        current_user_role_ids = [role.id for role in user.all_roles()]
        library_access_action = self.permitted_actions.LIBRARY_ACCESS.action

        stmt = select(LibraryPermissions).where(LibraryPermissions.action == library_access_action).distinct()
        restricted_library_ids = [lp.library_id for lp in trans.sa_session.scalars(stmt)]

        stmt = select(LibraryPermissions).where(
            and_(
                LibraryPermissions.action == library_access_action,
                LibraryPermissions.role_id.in_(current_user_role_ids),
            )
        )
        accessible_restricted_library_ids = [lp.library_id for lp in trans.sa_session.scalars(stmt)]

        # Filter to get libraries accessible by the current user.  Get both
        # public libraries and restricted libraries accessible by the current user.
        stmt = (
            select(Library)
            .where(
                and_(
                    Library.deleted == false(),
                    or_(
                        not_(Library.id.in_(restricted_library_ids)),
                        Library.id.in_(accessible_restricted_library_ids),
                    ),
                )
            )
            .order_by(Library.name)
        )
        for library in trans.sa_session.scalars(stmt):
            accessible_libraries.append(library)
        return accessible_libraries

    def has_accessible_folders(self, trans, folder, user, roles, search_downward=True):
        if (
            self.has_accessible_library_datasets(trans, folder, user, roles, search_downward=search_downward)
            or self.can_add_library_item(roles, folder)
            or self.can_modify_library_item(roles, folder)
            or self.can_manage_library_item(roles, folder)
        ):
            return True
        if search_downward:
            for active_folder in folder.active_folders:
                return self.has_accessible_folders(trans, active_folder, user, roles, search_downward=search_downward)
        return False

    def has_accessible_library_datasets(self, trans, folder, user, roles, search_downward=True):
        stmt = select(LibraryDataset).where(
            and_(LibraryDataset.deleted == false(), LibraryDataset.folder_id == folder.id)
        )
        for library_dataset in trans.sa_session.scalars(stmt):
            if self.can_access_library_item(roles, library_dataset, user):
                return True
        if search_downward:
            return self.__active_folders_have_accessible_library_datasets(trans, folder, user, roles)
        return False

    def __active_folders_have_accessible_library_datasets(self, trans, folder, user, roles):
        for active_folder in folder.active_folders:
            if self.has_accessible_library_datasets(trans, active_folder, user, roles):
                return True
        return False

    def can_access_library_item(self, roles, item, user):
        if isinstance(item, Library):
            return self.can_access_library(roles, item)
        elif isinstance(item, LibraryFolder):
            return (
                self.can_access_library(roles, item.parent_library) and self.check_folder_contents(user, roles, item)[0]
            )
        elif isinstance(item, LibraryDataset):
            return self.can_access_library(roles, item.folder.parent_library) and self.can_access_dataset(
                roles, item.library_dataset_dataset_association.dataset
            )
        elif isinstance(item, LibraryDatasetDatasetAssociation):
            return self.can_access_library(
                roles, item.library_dataset.folder.parent_library
            ) and self.can_access_dataset(roles, item.dataset)
        elif isinstance(item, LibraryDatasetCollectionAssociation):
            return self.can_access_library(roles, item.folder.parent_library)
        else:
            log.warning(f"Unknown library item type: {type(item)}")
            return False

    def can_add_library_item(self, roles, item):
        return self.allow_action(roles, self.permitted_actions.LIBRARY_ADD, item)

    def can_modify_library_item(self, roles, item):
        return self.allow_action(roles, self.permitted_actions.LIBRARY_MODIFY, item)

    def can_manage_library_item(self, roles, item):
        return self.allow_action(roles, self.permitted_actions.LIBRARY_MANAGE, item)

    def can_change_object_store_id(self, user, dataset):
        # prevent update if dataset shared with anyone but the current user
        # private object stores would prevent this but if something has been
        # kept private in a sharable object store still allow the swap
        if dataset.library_associations:
            return False
        else:
            query = text(
                """
SELECT COUNT(*)
FROM history
INNER JOIN
    history_dataset_association on history_dataset_association.history_id = history.id
WHERE history.user_id != :user_id and history_dataset_association.dataset_id = :dataset_id
"""
            ).bindparams(dataset_id=dataset.id, user_id=user.id if user else None)
            return self.sa_session.scalars(query).first() == 0

    def get_item_actions(self, action, item):
        # item must be one of: Dataset, Library, LibraryFolder, LibraryDataset, LibraryDatasetDatasetAssociation
        # SM: Accessing item.actions emits a query to Library_Dataset_Permissions
        # if the item is a LibraryDataset:
        # TODO: Pass in the item's actions - the item isn't needed
        return [permission for permission in item.actions if permission.action == action.action]

    def guess_derived_permissions_for_datasets(self, datasets=None):
        """Returns a dict of { action : [ role, role, ... ] } for the output dataset based upon provided datasets"""
        datasets = datasets or []
        perms = {}
        for dataset in datasets:
            if not isinstance(dataset, Dataset):
                dataset = dataset.dataset
            these_perms = {}
            # initialize blank perms
            for action in self.get_actions():
                these_perms[action] = []
            # collect this dataset's perms
            these_perms = self.get_permissions(dataset)
            # join or intersect this dataset's permissions with others
            for action, roles in these_perms.items():
                if action not in perms.keys():
                    perms[action] = roles
                else:
                    if action.model == "grant":
                        # intersect existing roles with new roles
                        perms[action] = [_ for _ in roles if _ in perms[action]]
                    elif action.model == "restrict":
                        # join existing roles with new roles
                        perms[action].extend([_ for _ in roles if _ not in perms[action]])
        return perms

    def guess_derived_permissions(self, all_input_permissions):
        """Returns a dict of { action : [ role_id, role_id, ... ] } for the output dataset based upon input dataset permissions.

        all_input_permissions should be of the form {action_name: set(role_ids)}
        """
        perms = {}
        for action_name, role_ids in all_input_permissions.items():
            if not role_ids:
                continue
            action = self.get_action(action_name)
            if action not in perms.keys():
                perms[action] = list(role_ids)
            else:
                if action.model == "grant":
                    # intersect existing roles with new roles
                    perms[action] = [_ for _ in role_ids if _ in perms[action]]
                elif action.model == "restrict":
                    # join existing roles with new roles
                    perms[action].extend([_ for _ in role_ids if _ not in perms[action]])
        return perms

    def associate_user_group(self, user, group):
        assoc = UserGroupAssociation(user, group)
        self.sa_session.add(assoc)
        with transaction(self.sa_session):
            self.sa_session.commit()
        return assoc

    def associate_user_role(self, user, role):
        assoc = UserRoleAssociation(user, role)
        self.sa_session.add(assoc)
        with transaction(self.sa_session):
            self.sa_session.commit()
        return assoc

    def associate_group_role(self, group, role):
        assoc = GroupRoleAssociation(group, role)
        self.sa_session.add(assoc)
        with transaction(self.sa_session):
            self.sa_session.commit()
        return assoc

    def associate_action_dataset_role(self, action, dataset, role):
        assoc = DatasetPermissions(action, dataset, role)
        self.sa_session.add(assoc)
        with transaction(self.sa_session):
            self.sa_session.commit()
        return assoc

    def create_user_role(self, user, app):
        # Create private user role if necessary
        self.get_private_user_role(user, auto_create=True)
        # Create default user permissions if necessary
        if not user.default_permissions:
            if hasattr(app.config, "new_user_dataset_access_role_default_private"):
                permissions = app.config.new_user_dataset_access_role_default_private
                self.user_set_default_permissions(user, default_access_private=permissions)
            else:
                self.user_set_default_permissions(user, history=True, dataset=True)

    def create_private_user_role(self, user):
        user.attempt_create_private_role()
        return self.get_private_user_role(user)

    def get_private_user_role(self, user, auto_create=False):
        if auto_create and user.id is None:
            # New user, directly create private role
            return self.create_private_user_role(user)
        role = get_private_user_role(user, self.sa_session)
        if not role and auto_create:
            role = self.create_private_user_role(user)
        return role

    def get_role(self, name, type=None):
        type = type or Role.types.SYSTEM
        # will raise exception if not found
        stmt = select(Role).where(and_(Role.name == name, Role.type == type))
        return self.sa_session.execute(stmt).scalar_one()

    def create_role(self, name, description, in_users, in_groups, create_group_for_role=False, type=None):
        type = type or Role.types.SYSTEM
        role = Role(name=name, description=description, type=type)
        self.sa_session.add(role)
        # Create the UserRoleAssociations
        for user in [self.sa_session.get(User, x) for x in in_users]:
            self.associate_user_role(user, role)
        # Create the GroupRoleAssociations
        for group in [self.sa_session.get(Group, x) for x in in_groups]:
            self.associate_group_role(group, role)
        if create_group_for_role:
            # Create the group
            group = Group(name=name)
            self.sa_session.add(group)
            # Associate the group with the role
            self.associate_group_role(group, role)
            num_in_groups = len(in_groups) + 1
        else:
            num_in_groups = len(in_groups)
        with transaction(self.sa_session):
            self.sa_session.commit()
        return role, num_in_groups

    def get_sharing_roles(self, user):
        stmt = select(Role).where(
            and_((Role.name).like(f"Sharing role for: %{user.email}%"), Role.type == Role.types.SHARING)
        )
        return self.sa_session.scalars(stmt)

    def user_set_default_permissions(
        self,
        user,
        permissions=None,
        history=False,
        dataset=False,
        bypass_manage_permission=False,
        default_access_private=False,
    ):
        # bypass_manage_permission is used to change permissions of datasets in a userless history when logging in
        flush_needed = False
        permissions = permissions or {}
        if user is None:
            return None
        if not permissions:
            # default permissions
            permissions = {
                self.permitted_actions.DATASET_MANAGE_PERMISSIONS: [self.get_private_user_role(user, auto_create=True)]
            }
            # new_user_dataset_access_role_default_private is set as True in config file
            if default_access_private:
                permissions[self.permitted_actions.DATASET_ACCESS] = next(iter(permissions.values()))
        # Delete all of the current default permissions for the user
        for dup in user.default_permissions:
            self.sa_session.delete(dup)
            flush_needed = True
        # Add the new default permissions for the user
        for action, roles in permissions.items():
            if isinstance(action, Action):
                action = action.action
            for dup in [DefaultUserPermissions(user, action, role) for role in roles]:
                self.sa_session.add(dup)
                flush_needed = True
        if flush_needed:
            with transaction(self.sa_session):
                self.sa_session.commit()
        if history:
            for history in user.active_histories:
                self.history_set_default_permissions(
                    history, permissions=permissions, dataset=dataset, bypass_manage_permission=bypass_manage_permission
                )

    def user_get_default_permissions(self, user):
        permissions = {}
        for dup in user.default_permissions:
            action = self.get_action(dup.action)
            if action in permissions:
                permissions[action].append(dup.role)
            else:
                permissions[action] = [dup.role]
        return permissions

    def history_set_default_permissions(self, history, permissions=None, dataset=False, bypass_manage_permission=False):
        # bypass_manage_permission is used to change permissions of datasets in a user-less history when logging in
        flush_needed = False
        permissions = permissions or {}
        user = history.user
        if not user:
            # default permissions on a user-less history are None
            return None
        if not permissions:
            permissions = self.user_get_default_permissions(user)
        # Delete all of the current default permission for the history
        for dhp in history.default_permissions:
            self.sa_session.delete(dhp)
            flush_needed = True
        # Add the new default permissions for the history
        for action, roles in permissions.items():
            if isinstance(action, Action):
                action = action.action
            for dhp in [DefaultHistoryPermissions(history, action, role) for role in roles]:
                self.sa_session.add(dhp)
                flush_needed = True
        if flush_needed:
            with transaction(self.sa_session):
                self.sa_session.commit()
        if dataset:
            # Only deal with datasets that are not purged
            for hda in history.activatable_datasets:
                dataset = hda.dataset
                if dataset.library_associations:
                    # Don't change permissions on a dataset associated with a library
                    continue
                if [assoc for assoc in dataset.history_associations if assoc.history not in user.histories]:
                    # Don't change permissions on a dataset associated with a history not owned by the user
                    continue
                if bypass_manage_permission or self.can_manage_dataset(user.all_roles(), dataset):
                    self.set_all_dataset_permissions(dataset, permissions)

    def history_get_default_permissions(self, history):
        permissions = {}
        for dhp in history.default_permissions:
            action = self.get_action(dhp.action)
            if action in permissions:
                permissions[action].append(dhp.role)
            else:
                permissions[action] = [dhp.role]
        return permissions

    def set_all_dataset_permissions(self, dataset, permissions=None, new=False, flush=True):
        """
        Set new full permissions on a dataset, eliminating all current permissions.
        Permission looks like: { Action : [ Role, Role ] }
        """
        # Make sure that DATASET_MANAGE_PERMISSIONS is associated with at least 1 role
        has_dataset_manage_permissions = False
        permissions = permissions or {}
        for _ in _walk_action_roles(permissions, self.permitted_actions.DATASET_MANAGE_PERMISSIONS):
            has_dataset_manage_permissions = True
            break
        if not has_dataset_manage_permissions:
            return "At least 1 role must be associated with manage permissions on this dataset."

        # If this is new, the objectstore likely hasn't been set yet - defer check until
        # the job handler assigns it.
        if not new and not dataset.shareable:
            # ensure dataset not shared.
            dataset_access_roles = []
            for _, roles in _walk_action_roles(permissions, self.permitted_actions.DATASET_ACCESS):
                dataset_access_roles.extend(roles)

            if len(dataset_access_roles) != 1 or dataset_access_roles[0].type != Role.types.PRIVATE:
                return galaxy.model.CANNOT_SHARE_PRIVATE_DATASET_MESSAGE

        flush_needed = False
        # Delete all of the current permissions on the dataset
        if not new:
            for dp in dataset.actions:
                self.sa_session.delete(dp)
                flush_needed = True
        # Add the new permissions on the dataset
        for action, roles in permissions.items():
            if isinstance(action, Action):
                action = action.action
            for role in roles:
                if hasattr(role, "id"):
                    role_id = role.id
                else:
                    role_id = role
                dp = DatasetPermissions(action, dataset, role_id=role_id)
                self.sa_session.add(dp)
                flush_needed = True
        if flush_needed and flush:
            with transaction(self.sa_session):
                self.sa_session.commit()
        return ""

    def set_dataset_permission(self, dataset, permission=None):
        """
        Set a specific permission on a dataset, leaving all other current permissions on the dataset alone.
        Permission looks like: { Action.action : [ Role, Role ] }
        """
        permission = permission or {}

        # if modifying access - ensure it is shareable.
        for _ in _walk_action_roles(permission, self.permitted_actions.DATASET_ACCESS):
            dataset.ensure_shareable()
            break

        flush_needed = False
        for action, roles in permission.items():
            if isinstance(action, Action):
                action = action.action
            # Delete the current specific permission on the dataset if one exists
            for dp in dataset.actions:
                if dp.action == action:
                    self.sa_session.delete(dp)
                    flush_needed = True
            # Add the new specific permission on the dataset
            for dp in [DatasetPermissions(action, dataset, role) for role in roles]:
                self.sa_session.add(dp)
                flush_needed = True
        if flush_needed:
            with transaction(self.sa_session):
                self.sa_session.commit()

    def get_permissions(self, item):
        """
        Return a dictionary containing the actions and associated roles on item
        where item is one of Library, LibraryFolder, LibraryDatasetDatasetAssociation,
        LibraryDataset, Dataset.  The dictionary looks like: { Action : [ Role, Role ] }.
        """
        permissions = {}
        for item_permission in item.actions:
            action = self.get_action(item_permission.action)
            if action in permissions:
                permissions[action].append(item_permission.role)
            else:
                permissions[action] = [item_permission.role]
        return permissions

    def copy_dataset_permissions(self, src, dst, flush=True):
        if not isinstance(src, Dataset):
            src = src.dataset
        if not isinstance(dst, Dataset):
            dst = dst.dataset
        self.set_all_dataset_permissions(dst, self.get_permissions(src), flush=flush)

    def privately_share_dataset(self, dataset, users=None):
        dataset.ensure_shareable()
        intersect = None
        users = users or []
        for user in users:
            roles = [ura.role for ura in user.roles if ura.role.type == Role.types.SHARING]
            if intersect is None:
                intersect = roles
            else:
                new_intersect = []
                for role in roles:
                    if role in intersect:
                        new_intersect.append(role)
                intersect = new_intersect
        sharing_role = None
        if intersect:
            for role in intersect:
                if not [_ for _ in [ura.user for ura in role.users] if _ not in users]:
                    # only use a role if it contains ONLY the users we're sharing with
                    sharing_role = role
                    break
        if sharing_role is None:
            sharing_role = Role(name=f"Sharing role for: {', '.join(u.email for u in users)}", type=Role.types.SHARING)
            self.sa_session.add(sharing_role)
            with transaction(self.sa_session):
                self.sa_session.commit()
            for user in users:
                self.associate_user_role(user, sharing_role)
        self.set_dataset_permission(dataset, {self.permitted_actions.DATASET_ACCESS: [sharing_role]})

    def set_all_library_permissions(self, trans, library_item, permissions=None):
        # Set new permissions on library_item, eliminating all current permissions
        flush_needed = False
        permissions = permissions or {}
        for role_assoc in library_item.actions:
            self.sa_session.delete(role_assoc)
            flush_needed = True
        # Add the new permissions on library_item
        for item_class, permission_class in self.library_item_assocs:
            if isinstance(library_item, item_class):
                for action, roles in list(permissions.items()):
                    if isinstance(action, Action):
                        action = action.action
                    for role_assoc in [permission_class(action, library_item, role) for role in roles]:
                        self.sa_session.add(role_assoc)
                        flush_needed = True
                    if isinstance(library_item, LibraryDatasetDatasetAssociation):
                        # Permission setting related to DATASET_MANAGE_PERMISSIONS was broken for a period of time,
                        # so it is possible that some Datasets have no roles associated with the DATASET_MANAGE_PERMISSIONS
                        # permission.  In this case, we'll reset this permission to the library_item user's private role.
                        if not library_item.dataset.has_manage_permissions_roles(self):
                            # Well this looks like a bug, this should be looked at.
                            # Default permissions above is single hash that keeps getting reeditted here
                            # because permission is being defined instead of permissions. -John
                            permissions[self.permitted_actions.DATASET_MANAGE_PERMISSIONS] = [
                                trans.app.security_agent.get_private_user_role(library_item.user)
                            ]
                            self.set_dataset_permission(library_item.dataset, permissions)
                        if action == self.permitted_actions.LIBRARY_MANAGE.action and roles:
                            # Handle the special case when we are setting the LIBRARY_MANAGE_PERMISSION on a
                            # library_dataset_dataset_association since the roles need to be applied to the
                            # DATASET_MANAGE_PERMISSIONS permission on the associated dataset.
                            permissions = {}
                            permissions[self.permitted_actions.DATASET_MANAGE_PERMISSIONS] = roles
                            self.set_dataset_permission(library_item.dataset, permissions)
        if flush_needed:
            with transaction(self.sa_session):
                self.sa_session.commit()

    def set_library_item_permission(self, library_item, permission=None):
        """
        Set a specific permission on a library item, leaving all other current permissions on the item alone.
        Permission looks like: { Action.action : [ Role, Role ] }
        """
        permission = permission or {}
        flush_needed = False
        for action, roles in permission.items():
            if isinstance(action, Action):
                action = action.action
            # Delete the current specific permission on the library item if one exists
            for item_permission in library_item.actions:
                if item_permission.action == action:
                    self.sa_session.delete(item_permission)
                    flush_needed = True
            # Add the new specific permission on the library item
            if isinstance(library_item, LibraryDataset):
                for item_permission in [LibraryDatasetPermissions(action, library_item, role) for role in roles]:
                    self.sa_session.add(item_permission)
                    flush_needed = True
            elif isinstance(library_item, LibraryPermissions):
                for item_permission in [LibraryPermissions(action, library_item, role) for role in roles]:
                    self.sa_session.add(item_permission)
                    flush_needed = True
        if flush_needed:
            with transaction(self.sa_session):
                self.sa_session.commit()

    def library_is_public(self, library, contents=False):
        if contents:
            # Check all contained folders and datasets to find any that are not public
            if not self.folder_is_public(library.root_folder):
                return False
        # A library is considered public if there are no "access" actions associated with it.
        return self.permitted_actions.LIBRARY_ACCESS.action not in [a.action for a in library.actions]

    def library_is_unrestricted(self, library):
        # A library is considered unrestricted if there are no "access" actions associated with it.
        return self.permitted_actions.LIBRARY_ACCESS.action not in [a.action for a in library.actions]

    def make_library_public(self, library, contents=False):
        flush_needed = False
        if contents:
            # Make all contained folders (include deleted folders, but not purged folders), public
            self.make_folder_public(library.root_folder)
        # A library is considered public if there are no LIBRARY_ACCESS actions associated with it.
        for lp in library.actions:
            if lp.action == self.permitted_actions.LIBRARY_ACCESS.action:
                self.sa_session.delete(lp)
                flush_needed = True
        if flush_needed:
            with transaction(self.sa_session):
                self.sa_session.commit()

    def folder_is_public(self, folder):
        for sub_folder in folder.folders:
            if not self.folder_is_public(sub_folder):
                return False
        for library_dataset in folder.datasets:
            ldda = library_dataset.library_dataset_dataset_association
            if ldda and ldda.dataset and not self.dataset_is_public(ldda.dataset):
                return False
        return True

    def folder_is_unrestricted(self, folder):
        # TODO implement folder restrictions
        # for now all folders are _visible_ but the restricted datasets within are not visible
        return True

    def make_folder_public(self, folder):
        # Make all of the contents (include deleted contents, but not purged contents) of folder public
        for sub_folder in folder.folders:
            if not sub_folder.purged:
                self.make_folder_public(sub_folder)
        for library_dataset in folder.datasets:
            dataset = library_dataset.library_dataset_dataset_association.dataset
            if not dataset.purged and not self.dataset_is_public(dataset):
                self.make_dataset_public(dataset)

    def dataset_is_public(self, dataset: Dataset):
        """
        A dataset is considered public if there are no "access" actions
        associated with it.  Any other actions ( 'manage permissions',
        'edit metadata' ) are irrelevant. Accessing dataset.actions
        will cause a query to be emitted.
        """
        return self.permitted_actions.DATASET_ACCESS.action not in [a.action for a in dataset.actions]

    def dataset_is_unrestricted(self, trans, dataset):
        """
        Different implementation of the method above with signature:
        def dataset_is_public( self, dataset )
        """
        return len(dataset.library_dataset_dataset_association.get_access_roles(self)) == 0

    def dataset_is_private_to_user(self, trans, dataset):
        """
        If the Dataset object has exactly one access role and that is
        the current user's private role then we consider the dataset private.
        """
        private_role = self.get_private_user_role(trans.user)
        access_roles = dataset.get_access_roles(self)

        if len(access_roles) != 1 or private_role is None:
            return False
        else:
            if access_roles[0].id == private_role.id:
                return True
            else:
                return False

    def dataset_is_private_to_a_user(self, dataset):
        """
        If the Dataset object has exactly one access role and that is
        the current user's private role then we consider the dataset private.
        """
        access_roles = dataset.get_access_roles(self)

        if len(access_roles) != 1:
            return False
        else:
            access_role = access_roles[0]
            return access_role.type == Role.types.PRIVATE

    def datasets_are_public(self, trans, datasets):
        """
        Given a transaction object and a list of Datasets, return
        a mapping from Dataset ids to whether the Dataset is public
        or not. All Dataset ids should be returned in the mapping's keys.
        """
        # We go the other way around from dataset_is_public: we start with
        # all datasets being marked as public. If there is an access action
        # associated with the dataset, then we mark it as nonpublic:
        datasets_public = {}
        dataset_ids = [dataset.id for dataset in datasets]
        for dataset_id in dataset_ids:
            datasets_public[dataset_id] = True

        # Now get all datasets which have DATASET_ACCESS actions:
        stmt = select(DatasetPermissions).where(
            and_(
                DatasetPermissions.dataset_id.in_(dataset_ids),
                DatasetPermissions.action == self.permitted_actions.DATASET_ACCESS.action,
            )
        )
        access_data_perms = trans.sa_session.scalars(stmt)
        # Every dataset returned has "access" privileges associated with it,
        # so it's not public.
        for permission in access_data_perms:
            datasets_public[permission.dataset_id] = False
        return datasets_public

    def make_dataset_public(self, dataset):
        # A dataset is considered public if there are no "access" actions associated with it.  Any
        # other actions ( 'manage permissions', 'edit metadata' ) are irrelevant.
        dataset.ensure_shareable()

        flush_needed = False
        for dp in dataset.actions:
            if dp.action == self.permitted_actions.DATASET_ACCESS.action:
                self.sa_session.delete(dp)
                flush_needed = True
        if flush_needed:
            with transaction(self.sa_session):
                self.sa_session.commit()

    def derive_roles_from_access(self, trans, item_id, cntrller, library=False, **kwd):
        # Check the access permission on a dataset.  If library is true, item_id refers to a library.  If library
        # is False, item_id refers to a dataset ( item_id must currently be decoded before being sent ).  The
        # cntrller param is the calling controller, which needs to be passed to get_legitimate_roles().
        msg = ""
        permissions = {}
        # accessible will be True only if at least 1 user has every role in DATASET_ACCESS_in
        accessible = False
        # legitimate will be True only if all roles in DATASET_ACCESS_in are in the set of roles returned from
        # get_legitimate_roles()
        # legitimate = False # TODO: not used
        # private_role_found will be true only if more than 1 role is being associated with the DATASET_ACCESS
        # permission on item, and at least 1 of the roles is private.
        private_role_found = False
        error = False
        for k, v in get_permitted_actions(filter="DATASET").items():
            # Change for removing the prefix '_in' from the roles select box
            in_roles = [self.sa_session.get(Role, x) for x in listify(kwd[k])]
            if not in_roles:
                in_roles = [self.sa_session.get(Role, x) for x in listify(kwd.get(f"{k}_in", []))]
            if v == self.permitted_actions.DATASET_ACCESS and in_roles:
                if library:
                    item = self.sa_session.get(Library, item_id)
                else:
                    item = self.sa_session.get(Dataset, item_id)
                if (library and not self.library_is_public(item)) or (not library and not self.dataset_is_public(item)):
                    # Ensure that roles being associated with DATASET_ACCESS are a subset of the legitimate roles
                    # derived from the roles associated with the access permission on item if it's not public.  This
                    # will keep illegitimate roles from being associated with the DATASET_ACCESS permission on the
                    # dataset (i.e., in the case where item is .a library, if Role1 is associated with LIBRARY_ACCESS,
                    # then only those users that have Role1 should be associated with DATASET_ACCESS.
                    legitimate_roles = self.get_legitimate_roles(trans, item, cntrller)
                    illegitimate_roles = []
                    for role in in_roles:
                        if role not in legitimate_roles:
                            illegitimate_roles.append(role)
                    if illegitimate_roles:
                        # This condition should never occur since illegitimate roles are filtered out of the set of
                        # roles displayed on the forms, but just in case there is a bug somewhere that incorrectly
                        # filters, we'll display this message.
                        error = True
                        msg += "The following roles are not associated with users that have the 'access' permission on this "
                        msg += "item, so they were incorrectly displayed: "
                        for role in illegitimate_roles:
                            msg += f"{role.name}, "
                        msg = msg.rstrip(", ")
                        new_in_roles = []
                        for role in in_roles:
                            if role in legitimate_roles:
                                new_in_roles.append(role)
                        in_roles = new_in_roles
                if len(in_roles) > 1:
                    # At least 1 user must have every role associated with the access
                    # permission on this dataset, or the dataset is not accessible.
                    # Since we have more than 1 role, none of them can be private.
                    for role in in_roles:
                        if role.type == Role.types.PRIVATE:
                            private_role_found = True
                            break
                if len(in_roles) == 1:
                    accessible = True
                else:
                    # At least 1 user must have every role associated with the access
                    # permission on this dataset, or the dataset is not accessible.
                    in_roles_set = set()
                    for role in in_roles:
                        in_roles_set.add(role)
                    users_set = set()
                    for role in in_roles:
                        for ura in role.users:
                            users_set.add(ura.user)
                        for gra in role.groups:
                            group = gra.group
                            for uga in group.users:
                                users_set.add(uga.user)
                    # Make sure that at least 1 user has every role being associated with the dataset.
                    for user in users_set:
                        user_roles_set = set()
                        for ura in user.roles:
                            user_roles_set.add(ura.role)
                        if in_roles_set.issubset(user_roles_set):
                            accessible = True
                            break
                if private_role_found or not accessible:
                    error = True
                    # Don't set the permissions for DATASET_ACCESS if inaccessible or multiple roles with
                    # at least 1 private, but set all other permissions.
                    permissions[self.get_action(v.action)] = []
                    msg = "At least 1 user must have every role associated with accessing datasets.  "
                    if private_role_found:
                        msg += "Since you are associating more than 1 role, no private roles are allowed."
                    if not accessible:
                        msg += "The roles you attempted to associate for access would make the datasets in-accessible by everyone."
                else:
                    permissions[self.get_action(v.action)] = in_roles
            else:
                permissions[self.get_action(v.action)] = in_roles
        return permissions, in_roles, error, msg

    def copy_library_permissions(self, trans, source_library_item, target_library_item, user=None):
        # Copy all relevant permissions from source.
        permissions = {}
        for role_assoc in source_library_item.actions:
            if role_assoc.action != self.permitted_actions.LIBRARY_ACCESS.action:
                # LIBRARY_ACCESS is a special permission that is set only at the library level.
                if role_assoc.action in permissions:
                    permissions[role_assoc.action].append(role_assoc.role)
                else:
                    permissions[role_assoc.action] = [role_assoc.role]
        self.set_all_library_permissions(trans, target_library_item, permissions)
        if user:
            for item_class, permission_class in self.library_item_assocs:
                if isinstance(target_library_item, item_class):
                    found_permission_class = permission_class
                    break
            else:
                raise Exception(
                    f"Invalid class ({target_library_item.__class__}) specified for target_library_item ({target_library_item.__class__.__name__})"
                )
            # Make sure user's private role is included
            private_role = self.get_private_user_role(user)
            for action in self.permitted_actions.values():
                if not found_permission_class.filter_by(role_id=private_role.id, action=action.action).first():
                    lp = found_permission_class(action.action, target_library_item, private_role)
                    self.sa_session.add(lp)
                    with transaction(self.sa_session):
                        self.sa_session.commit()

    def get_permitted_libraries(self, trans, user, actions):
        """
        This method is historical (it is not currently used), but may be useful again at some
        point.  It returns a dictionary whose keys are library objects and whose values are a
        comma-separated string of folder ids.  This method works with the show_library_item()
        method below, and it returns libraries for which the received user has permission to
        perform the received actions.  Here is an example call to this method to return all
        libraries for which the received user has LIBRARY_ADD permission::

            libraries = trans.app.security_agent.get_permitted_libraries( trans, user,
                [ trans.app.security_agent.permitted_actions.LIBRARY_ADD ] )
        """
        stmt = select(Library).where(Library.deleted == false()).order_by(Library.name)
        all_libraries = trans.sa_session.scalars(stmt)
        roles = user.all_roles()
        actions_to_check = actions
        # The libraries dictionary looks like: { library : '1,2' }, library : '3' }
        # Its keys are the libraries that should be displayed for the current user and whose values are a
        # string of comma-separated folder ids, of the associated folders the should NOT be displayed.
        # The folders that should not be displayed may not be a complete list, but it is ultimately passed
        # to the calling method to keep from re-checking the same folders when the library / folder
        # select lists are rendered.
        libraries = {}
        for library in all_libraries:
            can_show, hidden_folder_ids = self.show_library_item(self, roles, library, actions_to_check)
            if can_show:
                libraries[library] = hidden_folder_ids
        return libraries

    def show_library_item(self, user, roles, library_item, actions_to_check, hidden_folder_ids=""):
        """
        This method must be sent an instance of Library() or LibraryFolder().  Recursive execution produces a
        comma-separated string of folder ids whose folders do NOT meet the criteria for showing. Along with
        the string, True is returned if the current user has permission to perform any 1 of actions_to_check
        on library_item. Otherwise, cycle through all sub-folders in library_item until one is found that meets
        this criteria, if it exists.  This method does not necessarily scan the entire library as it returns
        when it finds the first library_item that allows user to perform any one action in actions_to_check.
        """
        for action in actions_to_check:
            if self.allow_action(roles, action, library_item):
                return True, hidden_folder_ids
        if isinstance(library_item, Library):
            return self.show_library_item(user, roles, library_item.root_folder, actions_to_check, hidden_folder_ids="")
        if isinstance(library_item, LibraryFolder):
            for folder in library_item.active_folders:
                can_show, hidden_folder_ids = self.show_library_item(
                    user, roles, folder, actions_to_check, hidden_folder_ids=hidden_folder_ids
                )
                if can_show:
                    return True, hidden_folder_ids
                if hidden_folder_ids:
                    hidden_folder_ids = "%s,%d" % (hidden_folder_ids, folder.id)
                else:
                    hidden_folder_ids = "%d" % folder.id
        return False, hidden_folder_ids

    def get_showable_folders(
        self, user, roles, library_item, actions_to_check, hidden_folder_ids=None, showable_folders=None
    ):
        """
        This method must be sent an instance of Library(), all the folders of which are scanned to determine if
        user is allowed to perform any action in actions_to_check. The param hidden_folder_ids, if passed, should
        contain a list of folder IDs which was generated when the library was previously scanned
        using the same actions_to_check. A list of showable folders is generated. This method scans the entire library.
        """
        hidden_folder_ids = hidden_folder_ids or []
        showable_folders = showable_folders or []
        if isinstance(library_item, Library):
            return self.get_showable_folders(
                user, roles, library_item.root_folder, actions_to_check, showable_folders=[]
            )
        if isinstance(library_item, LibraryFolder):
            if library_item.id not in hidden_folder_ids:
                for action in actions_to_check:
                    if self.allow_action(roles, action, library_item):
                        showable_folders.append(library_item)
                        break
            for folder in library_item.active_folders:
                self.get_showable_folders(user, roles, folder, actions_to_check, showable_folders=showable_folders)
        return showable_folders

    def set_user_group_and_role_associations(
        self,
        user: User,
        *,
        group_ids: Optional[List[int]] = None,
        role_ids: Optional[List[int]] = None,
    ) -> None:
        """
        Set user groups and user roles, replacing current associations.

        Associations are set only if a list of new associations is provided.
        If the provided list is empty, existing associations will be removed.
        If the provided value is None, existing associations will not be updated.
        """
        self._ensure_model_instance_has_id(user)
        if group_ids is not None:
            self._set_user_groups(user, group_ids or [])
        if role_ids is not None:
            self._set_user_roles(user, role_ids or [])
        # Commit only if both user groups and user roles have been set.
        self.sa_session.commit()

    def set_group_user_and_role_associations(
        self,
        group: Group,
        *,
        user_ids: Optional[List[int]] = None,
        role_ids: Optional[List[int]] = None,
    ) -> None:
        """
        Set group users and group roles, replacing current associations.

        Associations are set only if a list of new associations is provided.
        If the provided list is empty, existing associations will be removed.
        If the provided value is None, existing associations will not be updated.
        """
        self._ensure_model_instance_has_id(group)
        if user_ids is not None:
            self._set_group_users(group, user_ids)
        if role_ids is not None:
            self._set_group_roles(group, role_ids)
        # Commit only if both group users and group roles have been set.
        self.sa_session.commit()

    def set_role_user_and_group_associations(
        self,
        role: Role,
        *,
        user_ids: Optional[List[int]] = None,
        group_ids: Optional[List[int]] = None,
    ) -> None:
        """
        Set role users and role groups, replacing current associations.

        Associations are set only if a list of new associations is provided.
        If the provided list is empty, existing associations will be removed.
        If the provided value is None, existing associations will not be updated.
        """
        self._ensure_model_instance_has_id(role)
        if user_ids is not None:
            self._set_role_users(role, user_ids or [])
        if group_ids is not None:
            self._set_role_groups(role, group_ids or [])
        # Commit only if both role users and role groups have been set.
        self.sa_session.commit()

    def _set_user_groups(self, user, group_ids):
        delete_stmt = delete(UserGroupAssociation).where(UserGroupAssociation.user_id == user.id)
        insert_values = [{"user_id": user.id, "group_id": group_id} for group_id in group_ids]
        self._set_associations(user, UserGroupAssociation, delete_stmt, insert_values)

    def _set_user_roles(self, user, role_ids):
        # Do not include user's private role association in delete statement.
        delete_stmt = delete(UserRoleAssociation).where(UserRoleAssociation.user_id == user.id)
        private_role = get_private_user_role(user, self.sa_session)
        if not private_role:
            log.warning("User %s does not have a private role assigned", user)
        else:
            delete_stmt = delete_stmt.where(UserRoleAssociation.role_id != private_role.id)
        role_ids = self._filter_private_roles(role_ids)
        insert_values = [{"user_id": user.id, "role_id": role_id} for role_id in role_ids]
        self._set_associations(user, UserRoleAssociation, delete_stmt, insert_values)

    def _filter_private_roles(self, role_ids):
        """Filter out IDs of private roles: those should not be assignable via UI"""
        filtered = []
        for role_id in role_ids:
            stmt = select(Role.id).where(Role.id == role_id).where(Role.type == Role.types.PRIVATE)
            is_private = bool(self.sa_session.scalars(stmt).all())
            if not is_private:
                filtered.append(role_id)
        return filtered

    def _set_group_users(self, group, user_ids):
        delete_stmt = delete(UserGroupAssociation).where(UserGroupAssociation.group_id == group.id)
        insert_values = [{"group_id": group.id, "user_id": user_id} for user_id in user_ids]
        self._set_associations(group, UserGroupAssociation, delete_stmt, insert_values)

    def _set_group_roles(self, group, role_ids):
        delete_stmt = delete(GroupRoleAssociation).where(GroupRoleAssociation.group_id == group.id)
        insert_values = [{"group_id": group.id, "role_id": role_id} for role_id in role_ids]
        self._set_associations(group, GroupRoleAssociation, delete_stmt, insert_values)

    def _set_role_users(self, role, user_ids):
        # Do not set users if the role is private
        # Even though we do not expect to be handling a private role here, the following code is
        # a safeguard against deleting a user-role-association record for a private role.
        if role.type == Role.types.PRIVATE:
            return

        # First, check previously associated users to:
        # - delete DefaultUserPermissions for users that are being removed from this role;
        # - delete DefaultHistoryPermissions for histories associated with users that are being removed from this role.
        for ura in role.users:
            if ura.user_id not in user_ids:  # If a user will be removed from this role, then:
                user = self.sa_session.get(User, ura.user_id)
                # Delete DefaultUserPermissions for this user
                for dup in user.default_permissions:
                    if role == dup.role:
                        self.sa_session.delete(dup)
                # Delete DefaultHistoryPermissions for histories associated with this user
                for history in user.histories:
                    for dhp in history.default_permissions:
                        if role == dhp.role:
                            self.sa_session.delete(dhp)

        delete_stmt = delete(UserRoleAssociation).where(UserRoleAssociation.role_id == role.id)
        insert_values = [{"role_id": role.id, "user_id": user_id} for user_id in user_ids]
        self._set_associations(role, UserRoleAssociation, delete_stmt, insert_values)

    def _set_role_groups(self, role, group_ids):
        delete_stmt = delete(GroupRoleAssociation).where(GroupRoleAssociation.role_id == role.id)
        insert_values = [{"role_id": role.id, "group_id": group_id} for group_id in group_ids]
        self._set_associations(role, GroupRoleAssociation, delete_stmt, insert_values)

    def _ensure_model_instance_has_id(self, model_instance):
        # If model_instance is new, it may have not been assigned a database id yet, which is required
        # for creating association records. Flush if that's the case.
        if model_instance.id is None:
            self.sa_session.flush([model_instance])

    def _set_associations(self, parent_model, assoc_model, delete_stmt, insert_values):
        """
        Delete current associations for assoc_model, then insert new associations if values are provided.
        """
        # Ensure sqlite respects foreign key constraints.
        if self.sa_session.bind.dialect.name == "sqlite":
            self.sa_session.execute(text("PRAGMA foreign_keys = ON;"))
        self.sa_session.execute(delete_stmt)
        if not insert_values:
            return
        try:
            self.sa_session.execute(insert(assoc_model), insert_values)
        except IntegrityError as ie:
            self.sa_session.rollback()
            if is_unique_constraint_violation(ie):
                msg = f"Attempting to create a duplicate {assoc_model} record ({insert_values})"
                log.exception(msg)
                raise RequestParameterInvalidException()
            elif is_foreign_key_violation(ie):
                msg = f"Attempting to create an invalid {assoc_model} record ({insert_values})"
                log.exception(msg)
                raise RequestParameterInvalidException()
            else:
                raise

    def get_component_associations(self, **kwd):
        assert len(kwd) == 2, "You must specify exactly 2 Galaxy security components to check for associations."
        if "dataset" in kwd:
            if "action" in kwd:
                stmt = (
                    select(DatasetPermissions)
                    .filter_by(action=kwd["action"].action, dataset_id=kwd["dataset"].id)
                    .limit(1)
                )
                return self.sa_session.scalars(stmt).first()
        elif "user" in kwd:
            if "group" in kwd:
                stmt = select(UserGroupAssociation).filter_by(group_id=kwd["group"].id, user_id=kwd["user"].id).limit(1)
                return self.sa_session.scalars(stmt).first()
            elif "role" in kwd:
                stmt = select(UserRoleAssociation).filter_by(role_id=kwd["role"].id, user_id=kwd["user"].id).limit(1)
                return self.sa_session.scalars(stmt).first()
        elif "group" in kwd:
            if "role" in kwd:
                stmt = select(GroupRoleAssociation).filter_by(role_id=kwd["role"].id, group_id=kwd["group"].id).limit(1)
                return self.sa_session.scalars(stmt).first()
        raise Exception(f"No valid method of associating provided components: {kwd}")

    def check_folder_contents(self, user, roles, folder, hidden_folder_ids=""):
        """
        This method must always be sent an instance of LibraryFolder().  Recursive execution produces a
        comma-separated string of folder ids whose folders do NOT meet the criteria for showing.  Along
        with the string, True is returned if the current user has permission to access folder. Otherwise,
        cycle through all sub-folders in folder until one is found that meets this criteria, if it exists.
        This method does not necessarily scan the entire library as it returns when it finds the first
        folder that is accessible to user.
        """
        # If a folder is writeable, it's accessable and we need not go further
        if self.can_add_library_item(roles, folder):
            return True, ""
        action = self.permitted_actions.DATASET_ACCESS

        stmt = (
            select(LibraryDatasetDatasetAssociation)
            .join(LibraryDatasetDatasetAssociation.library_dataset)
            .where(LibraryDataset.folder == folder)
            .join(Dataset)
            .options(joinedload(LibraryDatasetDatasetAssociation.dataset).joinedload(Dataset.actions))
        )
        lddas = self.sa_session.scalars(stmt).unique()
        for ldda in lddas:
            ldda_access_permissions = self.get_item_actions(action, ldda.dataset)
            if not ldda_access_permissions:
                # Dataset is public
                return True, hidden_folder_ids
            for ldda_access_permission in ldda_access_permissions:
                if ldda_access_permission.role in roles:
                    # The current user has access permission on the dataset
                    return True, hidden_folder_ids
        for sub_folder in folder.active_folders:
            can_access, hidden_folder_ids = self.check_folder_contents(
                user, roles, sub_folder, hidden_folder_ids=hidden_folder_ids
            )
            if can_access:
                return True, hidden_folder_ids
            if hidden_folder_ids:
                hidden_folder_ids = "%s,%d" % (hidden_folder_ids, sub_folder.id)
            else:
                hidden_folder_ids = "%d" % sub_folder.id
        return False, hidden_folder_ids


class HostAgent(RBACAgent):
    """
    A simple security agent which allows access to datasets based on host.
    This exists so that externals sites such as UCSC can gain access to
    datasets which have permissions which would normally prevent such access.
    """

    # TODO: Make sites user configurable
    sites = Bunch(
        ucsc_main=(
            "hgw1.cse.ucsc.edu",
            "hgw2.cse.ucsc.edu",
            "hgw3.cse.ucsc.edu",
            "hgw4.cse.ucsc.edu",
            "hgw5.cse.ucsc.edu",
            "hgw6.cse.ucsc.edu",
            "hgw7.cse.ucsc.edu",
            "hgw8.cse.ucsc.edu",
        ),
        ucsc_test=("hgwdev.cse.ucsc.edu",),
        ucsc_archaea=("lowepub.cse.ucsc.edu",),
    )

    def __init__(self, sa_session, permitted_actions=None):
        self.sa_session = sa_session
        if permitted_actions:
            self.permitted_actions = permitted_actions

    def allow_action(self, addr, action, **kwd):
        if "dataset" in kwd and action == self.permitted_actions.DATASET_ACCESS:
            hda = kwd["dataset"]
            if action == self.permitted_actions.DATASET_ACCESS and action.action not in [
                dp.action for dp in hda.dataset.actions
            ]:
                log.debug("Allowing access to public dataset with hda: %i." % hda.id)
                return True  # dataset has no roles associated with the access permission, thus is already public
            stmt = (
                select(HistoryDatasetAssociationDisplayAtAuthorization)
                .filter_by(history_dataset_association_id=hda.id)
                .limit(1)
            )
            hdadaa = self.sa_session.scalars(stmt).first()
            if not hdadaa:
                log.debug(
                    "Denying access to private dataset with hda: %i.  No hdadaa record for this dataset." % hda.id
                )
                return False  # no auth
            # We could just look up the reverse of addr, but then we'd also
            # have to verify it with the forward address and special case any
            # IPs (instead of hosts) in the server list.
            #
            # This would be improved by caching, but that's what the OS's name
            # service cache daemon is for (you ARE running nscd, right?).
            for server in HostAgent.sites.get(hdadaa.site, []):
                # We're going to search in order, but if the remote site is load
                # balancing their connections (as UCSC does), this is okay.
                try:
                    if socket.gethostbyname(server) == addr:
                        break  # remote host is in the server list
                except (OSError, socket.gaierror):
                    pass  # can't resolve, try next
            else:
                log.debug(
                    "Denying access to private dataset with hda: %i.  Remote addr is not a valid server for site: %s."
                    % (hda.id, hdadaa.site)
                )
                return False  # remote addr is not in the server list
            if (datetime.utcnow() - hdadaa.update_time) > timedelta(seconds=60):
                log.debug(
                    "Denying access to private dataset with hda: %i.  Authorization was granted, but has expired."
                    % hda.id
                )
                return False  # not authz'd in the last 60 seconds
            log.debug("Allowing access to private dataset with hda: %i.  Remote server is: %s." % (hda.id, server))
            return True
        else:
            raise Exception("The dataset access permission is the only valid permission in the host security agent.")

    def set_dataset_permissions(self, hda, user, site):
        stmt = (
            select(HistoryDatasetAssociationDisplayAtAuthorization)
            .filter_by(history_dataset_association_id=hda.id)
            .limit(1)
        )
        hdadaa = self.sa_session.scalars(stmt).first()
        if hdadaa:
            hdadaa.update_time = datetime.utcnow()
        else:
            hdadaa = HistoryDatasetAssociationDisplayAtAuthorization(hda=hda, user=user, site=site)
        self.sa_session.add(hdadaa)
        with transaction(self.sa_session):
            self.sa_session.commit()


def _walk_action_roles(permissions, query_action):
    for action, roles in permissions.items():
        if isinstance(action, Action):
            if action == query_action and roles:
                yield action, roles
        elif action == query_action.action and roles:
            yield action, roles


def is_unique_constraint_violation(error):
    # A more elegant way to handle sqlite iw this:
    #   if hasattr(error.orig, "sqlite_errorname"):
    #       return error.orig.sqlite_errorname == "SQLITE_CONSTRAINT_UNIQUE"
    # However, that's only possible with Python 3.11+
    # https://docs.python.org/3/library/sqlite3.html#sqlite3.Error.sqlite_errorcode
    if isinstance(error.orig, sqlite3.IntegrityError):
        return error.orig.args[0].startswith("UNIQUE constraint failed")
    else:
        # If this is a PostgreSQL unique constraint, then error.orig is an instance of psycopg2.errors.UniqueViolation
        # and should have an attribute `pgcode` = 23505.
        return int(getattr(error.orig, "pgcode", -1)) == 23505


def is_foreign_key_violation(error):
    # A more elegant way to handle sqlite iw this:
    #   if hasattr(error.orig, "sqlite_errorname"):
    #       return error.orig.sqlite_errorname == "SQLITE_CONSTRAINT_UNIQUE"
    # However, that's only possible with Python 3.11+
    # https://docs.python.org/3/library/sqlite3.html#sqlite3.Error.sqlite_errorcode
    if isinstance(error.orig, sqlite3.IntegrityError):
        return error.orig.args[0] == "FOREIGN KEY constraint failed"
    else:
        # If this is a PostgreSQL foreign key error, then error.orig is an instance of psycopg2.errors.ForeignKeyViolation
        # and should have an attribute `pgcode` = 23503.
        return int(getattr(error.orig, "pgcode", -1)) == 23503
