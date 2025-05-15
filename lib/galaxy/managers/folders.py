"""
Manager and Serializer for Library Folders.
"""

import logging
from dataclasses import dataclass
from typing import (
    List,
    Optional,
    Set,
    Tuple,
    TYPE_CHECKING,
    Union,
)

from sqlalchemy import (
    and_,
    exists,
    false,
    func,
    not_,
    or_,
    select,
)
from sqlalchemy.exc import (
    MultipleResultsFound,
    NoResultFound,
)
from sqlalchemy.orm import aliased

from galaxy import (
    model,
    util,
)
from galaxy.exceptions import (
    AuthenticationRequired,
    InconsistentDatabase,
    InsufficientPermissionsException,
    InternalServerError,
    ItemAccessibilityException,
    MalformedId,
    RequestParameterInvalidException,
)
from galaxy.model import (
    Dataset,
    DatasetPermissions,
    LibraryDataset,
    LibraryDatasetDatasetAssociation,
    LibraryDatasetPermissions,
    LibraryFolder,
    LibraryFolderPermissions,
)
from galaxy.model.db.role import get_private_role_user_emails_dict
from galaxy.model.scoped_session import galaxy_scoped_session
from galaxy.schema.schema import LibraryFolderContentsIndexQueryPayload
from galaxy.security import RBACAgent

if TYPE_CHECKING:
    from galaxy.managers.context import ProvidesUserContext

log = logging.getLogger(__name__)


@dataclass
class SecurityParams:
    """Contains security data bundled for reusability."""

    user_role_ids: List[model.Role]
    security_agent: RBACAgent
    is_admin: bool


LDDA_SORT_COLUMN_MAP = {
    "name": lambda ldda, dataset: ldda.name,
    "description": lambda ldda, dataset: ldda.message,
    "type": lambda ldda, dataset: ldda.extension,
    "size": lambda ldda, dataset: dataset.file_size,
    "update_time": lambda ldda, dataset: ldda.update_time,
}

FOLDER_SORT_COLUMN_MAP = {
    "name": lambda folder: folder.name,
    "description": lambda folder: folder.description,
    "update_time": lambda folder: folder.update_time,
}


# =============================================================================
class FolderManager:
    """
    Interface/service object for interacting with folders.
    """

    def get(
        self,
        trans: "ProvidesUserContext",
        decoded_folder_id: int,
        check_manageable: bool = False,
        check_accessible: bool = True,
    ):
        """
        Get the folder from the DB.

        :param  decoded_folder_id:       decoded folder id
        :param  check_manageable:        flag whether the check that user can manage item
        :param  check_accessible:        flag whether to check that user can access item

        :returns:   the requested folder
        :rtype:     LibraryFolder

        :raises: InconsistentDatabase, RequestParameterInvalidException, InternalServerError
        """
        try:
            folder = get_folder(trans.sa_session, decoded_folder_id)
        except MultipleResultsFound:
            raise InconsistentDatabase("Multiple folders found with the same id.")
        except NoResultFound:
            raise RequestParameterInvalidException("No folder found with the id provided.")
        except Exception as e:
            raise InternalServerError(f"Error loading from the database.{util.unicodify(e)}")
        folder = self.secure(trans, folder, check_manageable, check_accessible)
        return folder

    def secure(
        self,
        trans: "ProvidesUserContext",
        folder: LibraryFolder,
        check_manageable: bool = True,
        check_accessible: bool = True,
    ):
        """
        Check if (a) user can manage folder or (b) folder is accessible to user.

        :param  folder:                  folder item
        :type   folder:                  LibraryFolder
        :param  check_manageable:        flag whether to check that user can manage item
        :type   check_manageable:        bool
        :param  check_accessible:        flag whether to check that user can access item
        :type   check_accessible:        bool

        :returns:   the original folder
        :rtype:     LibraryFolder
        """
        # all folders are accessible to an admin
        if trans.user_is_admin:
            return folder
        if check_manageable:
            folder = self.check_manageable(trans, folder)
        if check_accessible:
            folder = self.check_accessible(trans, folder)
        return folder

    def check_modifyable(self, trans, folder):
        """
        Check whether the user can modify the folder (name and description).

        :returns:   the original folder
        :rtype:     LibraryFolder

        :raises: AuthenticationRequired, InsufficientPermissionsException
        """
        if not trans.user:
            raise AuthenticationRequired("Must be logged in to manage Galaxy items.", type="error")
        current_user_roles = trans.get_current_user_roles()
        if not trans.app.security_agent.can_modify_library_item(current_user_roles, folder):
            raise InsufficientPermissionsException("You don't have permissions to modify this folder.", type="error")
        else:
            return folder

    def check_manageable(self, trans, folder):
        """
        Check whether the user can manage the folder.

        :returns:   the original folder
        :rtype:     LibraryFolder

        :raises: AuthenticationRequired, InsufficientPermissionsException
        """
        if not trans.user:
            raise AuthenticationRequired("Must be logged in to manage Galaxy items.", type="error")
        current_user_roles = trans.get_current_user_roles()
        if not trans.app.security_agent.can_manage_library_item(current_user_roles, folder):
            raise InsufficientPermissionsException("You don't have permissions to manage this folder.", type="error")
        else:
            return folder

    def check_accessible(self, trans, folder):
        """
        Check whether the folder is accessible to current user.
        By default every folder is accessible (contents have their own permissions).
        """
        return folder

    def get_folder_dict(self, trans, folder):
        """
        Return folder data in the form of a dictionary.

        :param  folder:       folder item
        :type   folder:       LibraryFolder

        :returns:   dict with data about the folder
        :rtype:     dictionary

        """
        folder_dict = folder.to_dict(view="element")
        folder_dict["update_time"] = folder.update_time
        return folder_dict

    def create(self, trans, parent_folder_id: int, new_folder_name: str, new_folder_description: Optional[str] = None):
        """
        Create a new folder under the given folder.

        :param  parent_folder_id:       decoded id
        :type   parent_folder_id:       int
        :param  new_folder_name:        name of the new folder
        :type   new_folder_name:        str
        :param  new_folder_description: description of the folder (optional, defaults to empty string)
        :type   new_folder_description: str

        :returns:   the new folder
        :rtype:     LibraryFolder

        :raises: InsufficientPermissionsException
        """
        parent_folder = self.get(trans, parent_folder_id)
        current_user_roles = trans.get_current_user_roles()
        if not (
            trans.user_is_admin or trans.app.security_agent.can_add_library_item(current_user_roles, parent_folder)
        ):
            raise InsufficientPermissionsException(
                "You do not have proper permission to create folders under given folder."
            )
        new_folder = LibraryFolder(name=new_folder_name, description=new_folder_description)
        # We are associating the last used genome build with folders, so we will always
        # initialize a new folder with the first dbkey in genome builds list which is currently
        # ?    unspecified (?)
        new_folder.genome_build = trans.app.genome_builds.default_value
        parent_folder.add_folder(new_folder)
        trans.sa_session.add(new_folder)
        trans.sa_session.commit()
        # New folders default to having the same permissions as their parent folder
        trans.app.security_agent.copy_library_permissions(trans, parent_folder, new_folder)
        return new_folder

    def update(self, trans, folder, name=None, description=None):
        """
        Update the given folder's name or description.

        :param  folder:        the model object
        :type   folder:        LibraryFolder
        :param  name:          new name for the library folder
        :type   name:          str
        :param  description:   new description for the library folder
        :type   description:   str

        :returns:   the folder
        :rtype:     LibraryFolder

        :raises: ItemAccessibilityException, InsufficientPermissionsException
        """
        changed = False
        if not trans.user_is_admin:
            folder = self.check_modifyable(trans, folder)
        if folder.deleted is True:
            raise ItemAccessibilityException("You cannot update a deleted library folder. Undelete it first.")
        if name is not None and name != folder.name:
            folder.name = name
            changed = True
        if description is not None and description != folder.description:
            folder.description = description
            changed = True
        if changed:
            trans.sa_session.add(folder)
            trans.sa_session.commit()
        return folder

    def delete(self, trans, folder, undelete=False):
        """
        Mark given folder deleted/undeleted based on the flag.

        :param  folder:        the model object
        :type   folder:        LibraryFolder
        :param  undelete:      flag whether to delete (when False) or undelete
        :type   undelete:      Bool

        :returns:   the folder
        :rtype:     LibraryFolder

        :raises: ItemAccessibilityException
        """
        if not trans.user_is_admin:
            folder = self.check_manageable(trans, folder)
        if undelete:
            folder.deleted = False
        else:
            folder.deleted = True
        trans.sa_session.add(folder)
        trans.sa_session.commit()
        return folder

    def get_current_roles(self, trans, folder):
        """
        Find all roles currently connected to relevant permissions
        on the folder.

        :param  folder:      the model object
        :type   folder:      LibraryFolder

        :returns:   dict of current roles for all available permission types
        :rtype:     dictionary
        """
        private_role_emails = get_private_role_user_emails_dict(trans.sa_session)

        # Omit duplicated roles by converting to set
        modify_roles = set(
            trans.app.security_agent.get_roles_for_action(
                folder, trans.app.security_agent.permitted_actions.LIBRARY_MODIFY
            )
        )
        manage_roles = set(
            trans.app.security_agent.get_roles_for_action(
                folder, trans.app.security_agent.permitted_actions.LIBRARY_MANAGE
            )
        )
        add_roles = set(
            trans.app.security_agent.get_roles_for_action(
                folder, trans.app.security_agent.permitted_actions.LIBRARY_ADD
            )
        )

        def make_tuples(roles: Set):
            tuples = []
            for role in roles:
                # use role name for non-private roles, and user.email from private rules
                displayed_name = private_role_emails.get(role.id, role.name)
                role_tuple = (displayed_name, trans.security.encode_id(role.id))
                tuples.append(role_tuple)
            return tuples

        return dict(
            modify_folder_role_list=make_tuples(modify_roles),
            manage_folder_role_list=make_tuples(manage_roles),
            add_library_item_role_list=make_tuples(add_roles),
        )

    def can_add_item(self, trans, folder):
        """
        Return true if the user has permissions to add item to the given folder.
        """
        if trans.user_is_admin:
            return True
        current_user_roles = trans.get_current_user_roles()
        add_roles = set(
            trans.app.security_agent.get_roles_for_action(
                folder, trans.app.security_agent.permitted_actions.LIBRARY_ADD
            )
        )
        for role in current_user_roles:
            if role in add_roles:
                return True
        return False

    def cut_the_prefix(self, encoded_folder_id):
        """
        Remove the prefix from the encoded folder id.

        :param encoded_folder_id: encoded id of the Folder object with 'F' prepended
        :type  encoded_folder_id: string

        :returns:  encoded Folder id without the 'F' prefix
        :rtype:    string

        :raises: MalformedId
        """
        if (len(encoded_folder_id) % 16 == 1) and encoded_folder_id.startswith("F"):
            cut_id = encoded_folder_id[1:]
        else:
            raise MalformedId(f"Malformed folder id ( {str(encoded_folder_id)} ) specified, unable to decode.")
        return cut_id

    def decode_folder_id(self, trans, encoded_folder_id):
        """
        Decode the folder id given that it has already lost the prefixed 'F'.

        :param encoded_folder_id: encoded id of the Folder object
        :type  encoded_folder_id: string

        :returns:  decoded Folder id
        :rtype:    int

        :raises: MalformedId
        """
        return trans.security.decode_id(encoded_folder_id, object_name="folder")

    def cut_and_decode(self, trans, encoded_folder_id):
        """
        Cuts the folder prefix (the prepended 'F') and returns the decoded id.

        :param encoded_folder_id: encoded id of the Folder object
        :type  encoded_folder_id: string

        :returns:  decoded Folder id
        :rtype:    int
        """
        return self.decode_folder_id(trans, self.cut_the_prefix(encoded_folder_id))

    def get_contents(
        self,
        trans,
        folder: LibraryFolder,
        payload: LibraryFolderContentsIndexQueryPayload,
    ) -> Tuple[List[Union[LibraryFolder, LibraryDataset]], int]:
        """Retrieves the contents of the given folder that match the provided filters and pagination parameters.
        Returns a tuple with the list of paginated contents and the total number of items contained in the folder."""
        limit = payload.limit
        offset = payload.offset
        sa_session = trans.sa_session
        security_params = SecurityParams(
            user_role_ids=[role.id for role in trans.get_current_user_roles()],
            security_agent=trans.app.security_agent,
            is_admin=trans.user_is_admin,
        )

        content_items: List[Union[LibraryFolder, LibraryDataset]] = []
        sub_folders_stmt = self._get_sub_folders_statement(sa_session, folder, security_params, payload)
        total_sub_folders = get_count(sa_session, sub_folders_stmt)
        if payload.order_by in FOLDER_SORT_COLUMN_MAP:
            sort_column = FOLDER_SORT_COLUMN_MAP[payload.order_by](LibraryFolder)
            sub_folders_stmt = sub_folders_stmt.order_by(sort_column.desc() if payload.sort_desc else sort_column)
        else:  # Sort by name alphabetically by default
            sub_folders_stmt = sub_folders_stmt.order_by(LibraryFolder.name)
        if limit is not None and limit > 0:
            sub_folders_stmt = sub_folders_stmt.limit(limit)
        if offset is not None:
            sub_folders_stmt = sub_folders_stmt.offset(offset)
        folders = sa_session.scalars(sub_folders_stmt).all()
        content_items.extend(folders)

        # Update pagination
        num_folders_returned = len(folders)
        num_folders_skipped = total_sub_folders - num_folders_returned
        if limit is not None and limit > 0:
            limit -= num_folders_returned
        if offset:
            offset -= num_folders_skipped
            offset = max(0, offset)

        datasets_stmt = self._get_contained_datasets_statement(sa_session, folder, security_params, payload)
        total_datasets = get_count(sa_session, datasets_stmt)
        if limit is not None and limit > 0:
            datasets_stmt = datasets_stmt.limit(limit)
        if offset is not None:
            datasets_stmt = datasets_stmt.offset(offset)
        datasets = sa_session.scalars(datasets_stmt).all()
        content_items.extend(datasets)
        return (content_items, total_sub_folders + total_datasets)

    def _get_sub_folders_statement(
        self,
        sa_session: galaxy_scoped_session,
        folder: LibraryFolder,
        security: SecurityParams,
        payload: LibraryFolderContentsIndexQueryPayload,
    ):
        """Builds a query to retrieve all the sub-folders contained in the given folder applying filters."""
        search_text = payload.search_text
        stmt = select(LibraryFolder).where(LibraryFolder.parent_id == folder.id)
        stmt = self._filter_by_include_deleted(
            stmt, LibraryFolder, LibraryFolderPermissions, payload.include_deleted, security
        )
        if search_text:
            search_text = search_text.lower()
            stmt = stmt.where(
                or_(
                    func.lower(LibraryFolder.name).contains(search_text, autoescape=True),
                    func.lower(LibraryFolder.description).contains(search_text, autoescape=True),
                )
            )
        stmt = stmt.group_by(LibraryFolder.id)
        return stmt

    def _get_contained_datasets_statement(
        self,
        sa_session: galaxy_scoped_session,
        folder: LibraryFolder,
        security: SecurityParams,
        payload: LibraryFolderContentsIndexQueryPayload,
    ):
        """Builds a query to retrieve all the datasets contained in the given folder applying filters."""
        search_text = payload.search_text
        access_action = security.security_agent.permitted_actions.DATASET_ACCESS.action

        stmt = select(LibraryDataset).where(LibraryDataset.folder_id == folder.id)
        stmt = self._filter_by_include_deleted(
            stmt, LibraryDataset, LibraryDatasetPermissions, payload.include_deleted, security
        )
        ldda = aliased(LibraryDatasetDatasetAssociation)
        associated_dataset = aliased(Dataset)
        stmt = stmt.outerjoin(LibraryDataset.library_dataset_dataset_association.of_type(ldda))
        if not security.is_admin:  # Non-admin users require ACCESS permission
            # We check against the actual dataset and not the ldda (for now?)
            dataset_permission = aliased(DatasetPermissions)
            is_public_dataset = not_(
                exists()
                .where(DatasetPermissions.dataset_id == associated_dataset.id)
                .where(DatasetPermissions.action == access_action)
            )
            stmt = stmt.outerjoin(ldda.dataset.of_type(associated_dataset))
            stmt = stmt.outerjoin(associated_dataset.actions.of_type(dataset_permission))
            stmt = stmt.where(
                or_(
                    # The dataset is public
                    is_public_dataset,
                    # The user has explicit access
                    and_(
                        dataset_permission.action == access_action,
                        dataset_permission.role_id.in_(security.user_role_ids),
                    ),
                )
            )
        if search_text:
            search_text = search_text.lower()
            stmt = stmt.where(
                or_(
                    func.lower(ldda.name).contains(search_text, autoescape=True),
                    func.lower(ldda.message).contains(search_text, autoescape=True),
                )
            )
        sort_column = LDDA_SORT_COLUMN_MAP[payload.order_by](ldda, associated_dataset)
        stmt = stmt.order_by(sort_column.desc() if payload.sort_desc else sort_column)
        stmt = stmt.group_by(LibraryDataset.id, sort_column)
        return stmt

    def _filter_by_include_deleted(
        self, stmt, item_model, item_permissions_model, include_deleted: Optional[bool], security: SecurityParams
    ):
        if include_deleted:  # Admins or users with MODIFY permissions can see deleted contents
            if not security.is_admin:
                item_permission = aliased(item_permissions_model)
                stmt = stmt.outerjoin(item_model.actions.of_type(item_permission))
                stmt = stmt.where(
                    or_(
                        item_model.deleted == false(),  # Is not deleted
                        # User has MODIFY permission
                        and_(
                            item_permission.action == security.security_agent.permitted_actions.LIBRARY_MODIFY.action,
                            item_permission.role_id.in_(security.user_role_ids),
                        ),
                    )
                )
        else:
            stmt = stmt.where(item_model.deleted == false())
        return stmt

    def build_folder_path(
        self, sa_session: galaxy_scoped_session, folder: model.LibraryFolder
    ) -> List[Tuple[int, Optional[str]]]:
        """
        Returns the folder path from root to the given folder.

        The path items are tuples with the name and id of each folder for breadcrumb building purposes.
        """
        current_folder = folder
        path_to_root = [(current_folder.id, current_folder.name)]
        while current_folder.parent_id is not None:
            parent_folder = sa_session.get(LibraryFolder, current_folder.parent_id)
            assert parent_folder
            current_folder = parent_folder
            path_to_root.insert(0, (current_folder.id, current_folder.name))
        return path_to_root


def get_folder(session, folder_id):
    stmt = select(LibraryFolder).where(LibraryFolder.id == folder_id)
    return session.execute(stmt).scalar_one()


def get_count(session, statement):
    stmt = select(func.count()).select_from(statement)
    return session.scalar(stmt)
