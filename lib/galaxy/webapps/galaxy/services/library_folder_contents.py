import logging

from galaxy import (
    exceptions,
    util,
)
from galaxy.managers import base as managers_base
from galaxy.managers.folders import FolderManager
from galaxy.managers.hdas import HDAManager
from galaxy.model import tags
from galaxy.security.idencoding import IdEncodingHelper
from galaxy.webapps.base.controller import UsesLibraryMixinItems
from galaxy.webapps.galaxy.services.base import ServiceBase

log = logging.getLogger(__name__)

FOLDER_TYPE_NAME = "folder"
FILE_TYPE_NAME = "file"


class LibraryFolderContentsService(ServiceBase, UsesLibraryMixinItems):
    """
    Interface/service shared by controllers for interacting with the contents of a library folder.
    """

    def __init__(self, security: IdEncodingHelper, hda_manager: HDAManager, folder_manager: FolderManager):
        super().__init__(security)
        self.hda_manager = hda_manager
        self.folder_manager = folder_manager

    def get_object(self, trans, id, class_name, check_ownership=False, check_accessible=False, deleted=None):
        """
        Convenience method to get a model object with the specified checks.
        """
        return managers_base.get_object(
            trans, id, class_name, check_ownership=check_ownership, check_accessible=check_accessible, deleted=deleted
        )

    def index(self, trans, folder_id, limit=None, offset=None, search_text=None, include_deleted=False):
        """
        Displays a collection (list) of a folder's contents (files and folders). Encoded folder ID is prepended
        with 'F' if it is a folder as opposed to a data set which does not have it. Full path is provided in
        response as a separate object providing data for breadcrumb path building.

        ..example:
            limit and offset can be combined. Skip the first two and return five:
                '?offset=2&limit=5'

        :param  folder_id: encoded ID of the folder which contents should be library_dataset_dict
        :type   folder_id: encoded string

        :param  offset: number of folder contents to skip
        :type   offset: optional int

        :param  limit: maximum number of folder contents to return
        :type   limit: optional int

        :param  include_deleted: whether to include deleted items in the results
        :type   include_deleted: optional bool (default False)

        :returns: dictionary containing all items and metadata
        :type:    dict

        :raises: MalformedId, InconsistentDatabase, ObjectNotFound,
             InternalServerError
        """
        is_admin = trans.user_is_admin
        current_user_roles = trans.get_current_user_roles()

        decoded_folder_id = self.folder_manager.cut_and_decode(trans, folder_id)
        folder = self.folder_manager.get(trans, decoded_folder_id)

        # Special level of security on top of libraries.
        if trans.app.security_agent.can_access_library(current_user_roles, folder.parent_library) or is_admin:
            pass
        else:
            if trans.user:
                log.warning(
                    f"SECURITY: User (id: {trans.user.id}) without proper access rights is trying to load folder with ID of {decoded_folder_id}"
                )
            else:
                log.warning(
                    f"SECURITY: Anonymous user is trying to load restricted folder with ID of {decoded_folder_id}"
                )
            raise exceptions.ObjectNotFound(f"Folder with the id provided ( {folder_id} ) was not found")

        folder_contents = []
        update_time = ""
        create_time = ""

        folders, datasets = self._apply_preferences(folder, include_deleted, search_text)

        #  Go through every accessible item (folders, datasets) in the folder and include its metadata.
        for content_item in self._load_folder_contents(trans, folders, datasets, offset, limit):
            return_item = {}
            encoded_id = trans.security.encode_id(content_item.id)
            create_time = content_item.create_time.isoformat()

            if content_item.api_type == FOLDER_TYPE_NAME:
                encoded_id = f"F{encoded_id}"
                can_modify = is_admin or (
                    trans.user and trans.app.security_agent.can_modify_library_item(current_user_roles, folder)
                )
                can_manage = is_admin or (
                    trans.user and trans.app.security_agent.can_manage_library_item(current_user_roles, folder)
                )
                update_time = content_item.update_time.isoformat()
                return_item.update(dict(can_modify=can_modify, can_manage=can_manage))
                if content_item.description:
                    return_item.update(dict(description=content_item.description))

            elif content_item.api_type == FILE_TYPE_NAME:
                #  Is the dataset public or private?
                #  When both are False the dataset is 'restricted'
                #  Access rights are checked on the dataset level, not on the ld or ldda level to maintain consistency
                dataset = content_item.library_dataset_dataset_association.dataset
                is_unrestricted = trans.app.security_agent.dataset_is_public(dataset)
                is_private = (
                    not is_unrestricted
                    and trans.user
                    and trans.app.security_agent.dataset_is_private_to_user(trans, dataset)
                )

                # Can user manage the permissions on the dataset?
                can_manage = is_admin or (
                    trans.user
                    and trans.app.security_agent.can_manage_dataset(
                        current_user_roles, content_item.library_dataset_dataset_association.dataset
                    )
                )
                raw_size = int(content_item.library_dataset_dataset_association.get_size(calculate_size=False))
                nice_size = util.nice_size(raw_size)
                update_time = content_item.library_dataset_dataset_association.update_time.isoformat()

                library_dataset_dict = content_item.to_dict()
                encoded_ldda_id = trans.security.encode_id(content_item.library_dataset_dataset_association.id)

                tag_manager = tags.GalaxyTagHandler(trans.sa_session)
                ldda_tags = tag_manager.get_tags_str(content_item.library_dataset_dataset_association.tags)

                return_item.update(
                    dict(
                        file_ext=library_dataset_dict["file_ext"],
                        date_uploaded=library_dataset_dict["date_uploaded"],
                        update_time=update_time,
                        is_unrestricted=is_unrestricted,
                        is_private=is_private,
                        can_manage=can_manage,
                        state=library_dataset_dict["state"],
                        file_size=nice_size,
                        raw_size=raw_size,
                        ldda_id=encoded_ldda_id,
                        tags=ldda_tags,
                    )
                )
                if content_item.library_dataset_dataset_association.message:
                    return_item.update(dict(message=content_item.library_dataset_dataset_association.message))
                elif content_item.library_dataset_dataset_association.info:
                    # There is no message but ldda info contains something so we display that instead.
                    return_item.update(dict(message=content_item.library_dataset_dataset_association.info))

            # For every item include the default metadata
            return_item.update(
                dict(
                    id=encoded_id,
                    type=content_item.api_type,
                    name=content_item.name,
                    update_time=update_time,
                    create_time=create_time,
                    deleted=content_item.deleted,
                )
            )
            folder_contents.append(return_item)

        # Return the reversed path so it starts with the library node.
        full_path = self._build_path(trans, folder)[::-1]

        user_can_add_library_item = is_admin or trans.app.security_agent.can_add_library_item(
            current_user_roles, folder
        )

        user_can_modify_folder = is_admin or trans.app.security_agent.can_modify_library_item(
            current_user_roles, folder
        )

        parent_library_id = None
        if folder.parent_library is not None:
            parent_library_id = trans.security.encode_id(folder.parent_library.id)

        total_rows = len(folders) + len(datasets)

        metadata = dict(
            full_path=full_path,
            total_rows=total_rows,
            can_add_library_item=user_can_add_library_item,
            can_modify_folder=user_can_modify_folder,
            folder_name=folder.name,
            folder_description=folder.description,
            parent_library_id=parent_library_id,
        )
        folder_container = dict(metadata=metadata, folder_contents=folder_contents)
        return folder_container

    def create(self, trans, encoded_folder_id, payload, **kwd):
        """
        Create a new library file from an HDA.

        :param  encoded_folder_id:      the encoded id of the folder to import dataset(s) to
        :type   encoded_folder_id:      an encoded id string
        :param  payload:    dictionary structure containing:
            :param from_hda_id:         (optional) the id of an accessible HDA to copy into the library
            :type  from_hda_id:         encoded id
            :param from_hdca_id:         (optional) the id of an accessible HDCA to copy into the library
            :type  from_hdca_id:         encoded id
            :param ldda_message:        (optional) the new message attribute of the LDDA created
            :type   ldda_message:       str
            :param extended_metadata:   (optional) dub-dictionary containing any extended metadata to associate with the item
            :type  extended_metadata:   dict
        :type   payload:    dict

        :returns:   a dictionary describing the new item if ``from_hda_id`` is supplied or a list of
                    such dictionaries describing the new items if ``from_hdca_id`` is supplied.
        :rtype:     object

        :raises:    ObjectAttributeInvalidException,
            InsufficientPermissionsException, ItemAccessibilityException,
            InternalServerError
        """
        if trans.user_is_bootstrap_admin:
            raise exceptions.RealUserRequiredException("Only real users can create a new library file.")
        encoded_folder_id_16 = self.__decode_library_content_id(trans, encoded_folder_id)
        from_hda_id = payload.pop("from_hda_id", None)
        from_hdca_id = payload.pop("from_hdca_id", None)
        ldda_message = payload.pop("ldda_message", "")
        try:
            if from_hda_id:
                decoded_hda_id = self.decode_id(from_hda_id)
                return self._copy_hda_to_library_folder(
                    trans, self.hda_manager, decoded_hda_id, encoded_folder_id_16, ldda_message
                )
            if from_hdca_id:
                decoded_hdca_id = self.decode_id(from_hdca_id)
                return self._copy_hdca_to_library_folder(
                    trans, self.hda_manager, decoded_hdca_id, encoded_folder_id_16, ldda_message
                )
        except Exception as exc:
            # TODO handle exceptions better within the mixins
            exc_message = util.unicodify(exc)
            if (
                "not accessible to the current user" in exc_message
                or "You are not allowed to access this dataset" in exc_message
            ):
                raise exceptions.ItemAccessibilityException("You do not have access to the requested item")
            else:
                log.exception(exc)
                raise exc

    def __decode_library_content_id(self, trans, encoded_folder_id):
        """
        Identify whether the id provided is properly encoded LibraryFolder.

        :param  encoded_folder_id:  encoded id of Galaxy LibraryFolder
        :type   encoded_folder_id:  encoded string

        :returns:   encoded id of Folder (had 'F' prepended)
        :type:  string

        :raises:    MalformedId
        """
        if (len(encoded_folder_id) % 16 == 1) and encoded_folder_id.startswith("F"):
            return encoded_folder_id[1:]
        else:
            raise exceptions.MalformedId(
                f"Malformed folder id ( {str(encoded_folder_id)} ) specified, unable to decode."
            )

    def _build_path(self, trans, folder):
        """
        Search the path upwards recursively and load the whole route of
        names and ids for breadcrumb building purposes.

        :param folder: current folder for navigating up
        :param type:   Galaxy LibraryFolder

        :returns:   list consisting of full path to the library
        :type:      list
        """
        path_to_root = []
        # We are almost in root
        encoded_id = trans.security.encode_id(folder.id)
        path_to_root.append((f"F{encoded_id}", folder.name))
        if folder.parent_id is not None:
            # We add the current folder and traverse up one folder.
            upper_folder = trans.sa_session.query(trans.app.model.LibraryFolder).get(folder.parent_id)
            path_to_root.extend(self._build_path(trans, upper_folder))
        return path_to_root

    def _load_folder_contents(self, trans, folders, datasets, offset=None, limit=None):
        """
        Loads all contents of the folder (folders and data sets) but only
        in the first level. Include deleted if the flag is set and if the
        user has access to undelete it.

        :param  folder:          the folder which contents are being loaded
        :type   folder:          Galaxy LibraryFolder

        :param  include_deleted: flag, when true the items that are deleted
            and can be undeleted by current user are shown
        :type   include_deleted: boolean

        :returns:   a list containing the requested items
        :type:      list
        """
        current_user_roles = trans.get_current_user_roles()
        is_admin = trans.user_is_admin
        content_items = []

        offset = 0 if offset is None else int(offset)
        limit = 0 if limit is None else int(limit)

        current_folders = self._calculate_pagination(folders, offset, limit)

        for subfolder in current_folders:
            if (
                not subfolder.deleted
                or is_admin
                or trans.app.security_agent.can_modify_library_item(current_user_roles, subfolder)
            ):
                # Undeleted folders are non-restricted for now.
                # Admins or users with MODIFY permissions can see deleted folders.
                subfolder.api_type = FOLDER_TYPE_NAME
                content_items.append(subfolder)

        limit -= len(content_items)
        offset -= len(folders)
        offset = max(0, offset)

        current_datasets = self._calculate_pagination(datasets, offset, limit)

        for dataset in current_datasets:
            if dataset.deleted:
                if is_admin or trans.app.security_agent.can_modify_library_item(current_user_roles, dataset):
                    # Admins or users with MODIFY permissions can see deleted folders.
                    dataset.api_type = FILE_TYPE_NAME
                    content_items.append(dataset)
            else:
                if is_admin or trans.app.security_agent.can_access_dataset(
                    current_user_roles, dataset.library_dataset_dataset_association.dataset
                ):
                    # Admins or users with ACCESS permissions can see datasets.
                    dataset.api_type = FILE_TYPE_NAME
                    content_items.append(dataset)

        return content_items

    def _calculate_pagination(self, items, offset: int, limit: int):
        if limit > 0:
            paginated_items = items[offset : offset + limit]
        else:
            paginated_items = items[offset:]
        return paginated_items

    def _apply_preferences(self, folder, include_deleted: bool, search_text: str):
        def check_deleted(array, include_deleted):
            if include_deleted:
                result_array = array
            else:
                result_array = [data for data in array if data.deleted == include_deleted]
            return result_array

        def filter_searched_datasets(dataset):
            if dataset.library_dataset_dataset_association.message:
                description = dataset.library_dataset_dataset_association.message
            elif dataset.library_dataset_dataset_association.info:
                description = dataset.library_dataset_dataset_association.info
            else:
                description = ""

            return search_text in dataset.name or search_text in description

        datasets = check_deleted(folder.datasets, include_deleted)
        folders = check_deleted(folder.folders, include_deleted)

        if search_text is not None:
            folders = [item for item in folders if search_text in item.name or search_text in item.description]
            datasets = list(filter(filter_searched_datasets, datasets))

        return folders, datasets
