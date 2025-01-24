"""
Manager and Serializer for libraries.
"""

import logging
from typing import (
    Dict,
    Optional,
    Set,
    Tuple,
)

from sqlalchemy.exc import (
    MultipleResultsFound,
    NoResultFound,
)
from sqlalchemy.orm import Query

from galaxy import exceptions
from galaxy.managers.folders import FolderManager
from galaxy.model import (
    Library,
    Role,
)
from galaxy.model.base import transaction
from galaxy.model.db.library import (
    get_libraries_by_name,
    get_libraries_for_admins,
    get_libraries_for_nonadmins,
    get_library_ids,
    get_library_permissions_by_role,
)
from galaxy.util import (
    pretty_print_time_interval,
    unicodify,
)

log = logging.getLogger(__name__)


# =============================================================================
class LibraryManager:
    """
    Interface/service object for interacting with libraries.
    """

    def get(self, trans, decoded_library_id: int, check_accessible: bool = True) -> Library:
        """
        Get the library from the DB.

        :param  decoded_library_id:       decoded library id
        :type   decoded_library_id:       int
        :param  check_accessible:         flag whether to check that user can access item
        :type   check_accessible:         bool

        :returns:   the requested library
        :rtype:     galaxy.model.Library
        """
        try:
            library = trans.sa_session.get(Library, decoded_library_id)
        except MultipleResultsFound:
            raise exceptions.InconsistentDatabase("Multiple libraries found with the same id.")
        except NoResultFound:
            raise exceptions.RequestParameterInvalidException("No library found with the id provided.")
        except Exception as e:
            raise exceptions.InternalServerError(f"Error loading from the database.{unicodify(e)}")
        library = self.secure(trans, library, check_accessible)
        return library

    def create(self, trans, name: str, description: Optional[str] = "", synopsis: Optional[str] = "") -> Library:
        """
        Create a new library.
        """
        if not trans.user_is_admin:
            raise exceptions.ItemAccessibilityException("Only administrators can create libraries.")
        else:
            library = trans.app.model.Library(name=name, description=description, synopsis=synopsis)
            root_folder = trans.app.model.LibraryFolder(name=name, description="")
            library.root_folder = root_folder
            trans.sa_session.add_all((library, root_folder))
            with transaction(trans.sa_session):
                trans.sa_session.commit()
            return library

    def update(
        self,
        trans,
        library: Library,
        name: Optional[str] = None,
        description: Optional[str] = None,
        synopsis: Optional[str] = None,
    ) -> Library:
        """
        Update the given library
        """
        changed = False
        if not trans.user_is_admin:
            current_user_roles = trans.get_current_user_roles()
            library_modify_roles = self.get_modify_roles(trans, library)
            user_can_modify = any(role in library_modify_roles for role in current_user_roles)
            if not user_can_modify:
                raise exceptions.ItemAccessibilityException("You don't have permission update libraries.")
        if library.deleted:
            raise exceptions.RequestParameterInvalidException("You cannot modify a deleted library. Undelete it first.")
        if name is not None:
            library.name = name
            changed = True
            #  When library is renamed the root folder has to be renamed too.
            folder_manager = FolderManager()
            folder_manager.update(trans, library.root_folder, name=name)
        if description is not None:
            library.description = description
            changed = True
        if synopsis is not None:
            library.synopsis = synopsis
            changed = True
        if changed:
            trans.sa_session.add(library)
            with transaction(trans.sa_session):
                trans.sa_session.commit()
        return library

    def delete(self, trans, library: Library, undelete: Optional[bool] = False) -> Library:
        """
        Mark given library deleted/undeleted based on the flag.
        """
        if not trans.user_is_admin:
            raise exceptions.ItemAccessibilityException("Only administrators can delete and undelete libraries.")
        if undelete:
            library.deleted = False
        else:
            library.deleted = True
        trans.sa_session.add(library)
        with transaction(trans.sa_session):
            trans.sa_session.commit()
        return library

    def list(self, trans, deleted: Optional[bool] = False) -> Tuple[Query, Dict[str, Set]]:
        """
        Return a list of libraries from the DB.

        :param  deleted: if True, show only ``deleted`` libraries, if False show only ``non-deleted``
        :type   deleted: boolean (optional)

        :returns: iterable that will emit all accessible libraries
        :rtype:   sqlalchemy ScalarResult
        :returns: dict of 3 sets with available actions for user's accessible
                  libraries and a set of ids of all public libraries. These are
                  used for limiting the number of queries when dictifying the
                  libraries later on.
        :rtype:   dict
        """
        is_admin = trans.user_is_admin
        library_access_action = trans.app.security_agent.permitted_actions.LIBRARY_ACCESS.action
        restricted_library_ids = set(get_library_ids(trans.sa_session, library_access_action))
        prefetched_ids = {"restricted_library_ids": restricted_library_ids}

        if is_admin:
            libraries = get_libraries_for_admins(trans.sa_session, deleted=deleted)
        else:
            #  Nonadmins can't see deleted libraries
            if deleted:
                raise exceptions.AdminRequiredException()
            current_user_role_ids = [role.id for role in trans.get_current_user_roles()]
            library_add_action = trans.app.security_agent.permitted_actions.LIBRARY_ADD.action
            library_modify_action = trans.app.security_agent.permitted_actions.LIBRARY_MODIFY.action
            library_manage_action = trans.app.security_agent.permitted_actions.LIBRARY_MANAGE.action
            accessible_restricted_library_ids = set()
            allowed_library_add_ids = set()
            allowed_library_modify_ids = set()
            allowed_library_manage_ids = set()
            for action in get_library_permissions_by_role(trans.sa_session, current_user_role_ids):
                if action.action == library_access_action:
                    accessible_restricted_library_ids.add(action.library_id)
                if action.action == library_add_action:
                    allowed_library_add_ids.add(action.library_id)
                if action.action == library_modify_action:
                    allowed_library_modify_ids.add(action.library_id)
                if action.action == library_manage_action:
                    allowed_library_manage_ids.add(action.library_id)
            prefetched_ids["allowed_library_add_ids"] = allowed_library_add_ids
            prefetched_ids["allowed_library_modify_ids"] = allowed_library_modify_ids
            prefetched_ids["allowed_library_manage_ids"] = allowed_library_manage_ids
            libraries = get_libraries_for_nonadmins(
                trans.sa_session, restricted_library_ids, accessible_restricted_library_ids
            )

        return libraries, prefetched_ids

    def secure(self, trans, library: Library, check_accessible: bool = True) -> Library:
        """
        Check if library is accessible to user.

        :param  library:                 library
        :type   library:                 galaxy.model.Library
        :param  check_accessible:        flag whether to check that user can access library
        :type   check_accessible:        bool

        :returns:   the original library
        :rtype:     galaxy.model.Library
        """
        # all libraries are accessible to an admin
        if trans.user_is_admin:
            return library
        if check_accessible:
            library = self.check_accessible(trans, library)
        return library

    def check_accessible(self, trans, library: Library) -> Library:
        """
        Check whether the library is accessible to current user.
        """
        if not trans.app.security_agent.can_access_library(trans.get_current_user_roles(), library):
            raise exceptions.ObjectNotFound("Library with the id provided was not found.")
        elif library.deleted:
            raise exceptions.ObjectNotFound("Library with the id provided is deleted.")
        else:
            return library

    def get_library_dict(self, trans, library: Library, prefetched_ids: Optional[Dict[str, Set]] = None) -> dict:
        """
        Return library data in the form of a dictionary.

        :param  library:         library
        :type   library:         galaxy.model.Library
        :param  prefetched_ids:  dict of 3 sets with available actions for user's accessible
                                 libraries and a set of ids of all public libraries. These are
                                 used for limiting the number of queries when dictifying a
                                 set of libraries.
        :type   prefetched_ids:  dict

        :returns:   dict with data about the library
        :rtype:     dictionary
        """
        restricted_library_ids = prefetched_ids.get("restricted_library_ids", None) if prefetched_ids else None
        allowed_library_add_ids = prefetched_ids.get("allowed_library_add_ids", None) if prefetched_ids else None
        allowed_library_modify_ids = prefetched_ids.get("allowed_library_modify_ids", None) if prefetched_ids else None
        allowed_library_manage_ids = prefetched_ids.get("allowed_library_manage_ids", None) if prefetched_ids else None
        library_dict = library.to_dict(view="element")
        library_dict["public"] = False if (restricted_library_ids and library.id in restricted_library_ids) else True
        library_dict["create_time_pretty"] = pretty_print_time_interval(library.create_time, precise=True)
        if not trans.user_is_admin:
            if prefetched_ids:
                library_dict["can_user_add"] = (
                    True if (allowed_library_add_ids and library.id in allowed_library_add_ids) else False
                )
                library_dict["can_user_modify"] = (
                    True if (allowed_library_modify_ids and library.id in allowed_library_modify_ids) else False
                )
                library_dict["can_user_manage"] = (
                    True if (allowed_library_manage_ids and library.id in allowed_library_manage_ids) else False
                )
            else:
                current_user_roles = trans.get_current_user_roles()
                library_dict["can_user_add"] = trans.app.security_agent.can_add_library_item(
                    current_user_roles, library
                )
                library_dict["can_user_modify"] = trans.app.security_agent.can_modify_library_item(
                    current_user_roles, library
                )
                library_dict["can_user_manage"] = trans.app.security_agent.can_manage_library_item(
                    current_user_roles, library
                )
        else:
            library_dict["can_user_add"] = True
            library_dict["can_user_modify"] = True
            library_dict["can_user_manage"] = True
        return library_dict

    def get_current_roles(self, trans, library: Library) -> dict:
        """
        Load all permissions currently related to the given library.

        :param  library:      the model object
        :type   library:      galaxy.model.Library

        :rtype:     dictionary
        :returns:   dict of current roles for all available permission types
        """
        access_library_role_list = [
            (access_role.name, trans.security.encode_id(access_role.id))
            for access_role in self.get_access_roles(trans, library)
        ]
        modify_library_role_list = [
            (modify_role.name, trans.security.encode_id(modify_role.id))
            for modify_role in self.get_modify_roles(trans, library)
        ]
        manage_library_role_list = [
            (manage_role.name, trans.security.encode_id(manage_role.id))
            for manage_role in self.get_manage_roles(trans, library)
        ]
        add_library_item_role_list = [
            (add_role.name, trans.security.encode_id(add_role.id)) for add_role in self.get_add_roles(trans, library)
        ]
        return dict(
            access_library_role_list=access_library_role_list,
            modify_library_role_list=modify_library_role_list,
            manage_library_role_list=manage_library_role_list,
            add_library_item_role_list=add_library_item_role_list,
        )

    def get_access_roles(self, trans, library: Library) -> Set[Role]:
        """
        Load access roles for all library permissions
        """
        return set(library.get_access_roles(trans.app.security_agent))

    def get_modify_roles(self, trans, library: Library) -> Set[Role]:
        """
        Load modify roles for all library permissions
        """
        return set(
            trans.app.security_agent.get_roles_for_action(
                library, trans.app.security_agent.permitted_actions.LIBRARY_MODIFY
            )
        )

    def get_manage_roles(self, trans, library: Library) -> Set[Role]:
        """
        Load manage roles for all library permissions
        """
        return set(
            trans.app.security_agent.get_roles_for_action(
                library, trans.app.security_agent.permitted_actions.LIBRARY_MANAGE
            )
        )

    def get_add_roles(self, trans, library: Library) -> Set[Role]:
        """
        Load add roles for all library permissions
        """
        return set(
            trans.app.security_agent.get_roles_for_action(
                library, trans.app.security_agent.permitted_actions.LIBRARY_ADD
            )
        )

    def make_public(self, trans, library: Library) -> bool:
        """
        Makes the given library public (removes all access roles)
        """
        trans.app.security_agent.make_library_public(library)
        return self.is_public(trans, library)

    def is_public(self, trans, library: Library) -> bool:
        """
        Return true if lib is public.
        """
        return trans.app.security_agent.library_is_public(library)


def get_containing_library_from_library_dataset(trans, library_dataset) -> Optional[Library]:
    """Given a library_dataset, get the containing library"""
    folder = library_dataset.folder
    while folder.parent:
        folder = folder.parent
    # We have folder set to the library's root folder, which has the same name as the library
    for library in get_libraries_by_name(trans.sa_session, folder.name):
        # Just to double-check
        if library.root_folder == folder:
            return library
    return None
