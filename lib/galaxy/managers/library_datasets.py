"""Manager and Serializer for library datasets."""

import logging
from typing import (
    Any,
    Dict,
)

from sqlalchemy import select

from galaxy import util
from galaxy.exceptions import (
    InsufficientPermissionsException,
    InternalServerError,
    ObjectNotFound,
    RequestParameterInvalidException,
)
from galaxy.managers.base import ModelManager
from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.lddas import LDDAManager
from galaxy.model import (
    LibraryDataset,
    LibraryDatasetDatasetAssociation,
    LibraryFolder,
)
from galaxy.structured_app import MinimalManagerApp
from galaxy.util import validation

log = logging.getLogger(__name__)


class LibraryDatasetsManager(ModelManager[LibraryDataset]):
    """Interface/service object for interacting with library datasets."""

    model_class = LibraryDataset

    def __init__(self, app: MinimalManagerApp):
        super().__init__(app)
        self.ldda_manager = LDDAManager(app)

    def get(self, trans, decoded_library_dataset_id, check_accessible=True) -> LibraryDataset:
        """
        Get the library dataset from the DB.

        :param  decoded_library_dataset_id: decoded library dataset id
        :type   decoded_library_dataset_id: int
        :param  check_accessible:           flag whether to check that user can access item
        :type   check_accessible:           bool

        :returns:   the requested library dataset
        :rtype:     galaxy.model.LibraryDataset
        """
        try:
            ld = get_library_dataset(trans.sa_session, decoded_library_dataset_id)
        except Exception as e:
            raise InternalServerError(f"Error loading from the database.{util.unicodify(e)}")
        ld = self.secure(trans, ld, check_accessible)
        return ld

    def update(self, item: LibraryDataset, new_values: Dict[str, Any], flush: bool = True, **kwargs) -> LibraryDataset:
        """
        Update the given library dataset - the latest linked ldda.
        Updating older lddas (versions) is not allowed.

        :param  item:               library dataset to change
        :type   item:               LibraryDataset
        :param  new_values:         dictionary structure containing::
            :param name:            new ld's name, must be longer than 0
            :type  name:            str
            :param misc_info:       new ld's misc info
            :type  misc_info:       str
            :param file_ext:        new ld's extension, must exist in the Galaxy registry
            :type  file_ext:        str
            :param genome_build:    new ld's genome build
            :type  genome_build:    str
            :param tags:            list of dataset tags
            :type  tags:            list
        :type   new_values: dict

        :returns:   the changed library dataset
        :rtype:     galaxy.model.LibraryDataset
        """
        trans = kwargs.get("trans")
        if not trans:
            raise ValueError("Missing trans parameter")
        # we are going to operate on the actual latest ldda
        ldda = item.library_dataset_dataset_association
        new_values = self._validate_and_parse_update_payload(new_values)
        self._set_from_dict(trans, ldda, new_values, flush=flush)
        return item

    def _set_from_dict(
        self,
        trans: ProvidesUserContext,
        ldda: LibraryDatasetDatasetAssociation,
        new_data: Dict[str, Any],
        flush: bool = True,
    ) -> None:
        changed = False
        new_name = new_data.get("name", None)
        if new_name is not None and new_name != ldda.name:
            ldda.name = new_name
            changed = True
        new_misc_info = new_data.get("misc_info", None)
        if new_misc_info is not None and new_misc_info != ldda.info:
            ldda.info = new_misc_info
            changed = True
        new_message = new_data.get("message", None)
        if new_message is not None and new_message != ldda.message:
            ldda.message = new_message
            changed = True
        new_file_ext = new_data.get("file_ext", None)
        if new_file_ext == "auto":
            self.ldda_manager.detect_datatype(trans, ldda)
        elif new_file_ext is not None and new_file_ext != ldda.extension:
            ldda.extension = new_file_ext
            self.ldda_manager.set_metadata(trans, ldda)
            changed = True
        new_genome_build = new_data.get("genome_build", None)
        if new_genome_build is not None and new_genome_build != ldda.dbkey:
            ldda.dbkey = new_genome_build
            changed = True
        new_tags = new_data.get("tags", None)
        if new_tags is not None and new_tags != ldda.tags:
            trans.tag_handler.delete_item_tags(item=ldda, user=trans.user)
            tag_list = trans.tag_handler.parse_tags_list(new_tags)
            for tag in tag_list:
                trans.tag_handler.apply_item_tag(item=ldda, user=trans.user, name=tag[0], value=tag[1])
            changed = True
        if changed:
            ldda.update_parent_folder_update_times()
            session = self.session()
            session.add(ldda)
            if flush:
                session.commit()

    def _validate_and_parse_update_payload(self, payload):
        MINIMUM_STRING_LENGTH = 1
        validated_payload = {}
        for key, val in payload.items():
            if val is None:
                continue
            if key in ("name",):
                if len(val) < MINIMUM_STRING_LENGTH:
                    raise RequestParameterInvalidException(
                        f"{key} must have at least length of {MINIMUM_STRING_LENGTH}"
                    )
                val = validation.validate_and_sanitize_basestring(key, val)
                validated_payload[key] = val
            if key in ("misc_info", "message"):
                val = validation.validate_and_sanitize_basestring(key, val)
                validated_payload[key] = val
            if key in ("file_ext",):
                datatype = self.app.datatypes_registry.get_datatype_by_extension(val)
                if datatype is None and val not in ("auto",):
                    raise RequestParameterInvalidException(f"This Galaxy does not recognize the datatype of: {val}")
                validated_payload[key] = val
            if key in ("genome_build",):
                if len(val) < MINIMUM_STRING_LENGTH:
                    raise RequestParameterInvalidException(
                        f"{key} must have at least length of {MINIMUM_STRING_LENGTH}"
                    )
                val = validation.validate_and_sanitize_basestring(key, val)
                validated_payload[key] = val
            if key in ("tags",):
                val = validation.validate_and_sanitize_basestring_list(key, util.listify(val))
                validated_payload[key] = val
        return validated_payload

    def secure(self, trans, ld, check_accessible=True, check_ownership=False):
        """
        Check if library dataset is accessible to current user or the user is an admin.

        :param  ld:         library dataset
        :type   ld:         galaxy.model.LibraryDataset
        :param  check_accessible:        flag whether to check that user can access library dataset
        :type   check_accessible:        bool

        :returns:   the original library dataset
        :rtype:     galaxy.model.LibraryDataset
        """
        if trans.user_is_admin:
            # all operations are available to an admin
            return ld
        if check_accessible:
            ld = self.check_accessible(trans, ld)
        return ld

    def check_accessible(self, trans, ld):
        """
        Check whether the current user has permissions to access library dataset.

        :param  ld: library dataset
        :type   ld: galaxy.model.LibraryDataset

        :returns:   the original library dataset
        :rtype:     galaxy.model.LibraryDataset

        :raises:    ObjectNotFound
        """
        if not self.app.security_agent.can_access_library_item(trans.get_current_user_roles(), ld, trans.user):
            raise ObjectNotFound("Library dataset with the id provided was not found.")
        elif ld.deleted:
            raise ObjectNotFound("Library dataset with the id provided is deleted.")
        else:
            return ld

    def check_modifiable(self, trans, ld):
        """
        Check whether the current user has permissions to modify library dataset.

        :param  ld: library dataset
        :type   ld: galaxy.model.LibraryDataset

        :returns:   the original library dataset
        :rtype:     galaxy.model.LibraryDataset

        :raises:    ObjectNotFound
        """
        if ld.deleted:
            raise ObjectNotFound("Library dataset with the id provided is deleted.")
        elif trans.user_is_admin:
            return ld
        if not self.app.security_agent.can_modify_library_item(trans.get_current_user_roles(), ld):
            raise InsufficientPermissionsException("You do not have proper permission to modify this library dataset.")
        else:
            return ld

    def serialize(self, trans, ld: LibraryDataset) -> Dict[str, Any]:
        """Serialize the library dataset into a dictionary."""
        current_user_roles = trans.get_current_user_roles()

        # Build the full path for breadcrumb purposes.
        full_path = self._build_path(trans, ld.folder)
        dataset_item = (self.app.security.encode_id(ld.id), ld.name)
        full_path.insert(0, dataset_item)
        full_path = full_path[::-1]

        # Find expired versions of the library dataset
        expired_ldda_versions = []
        for expired_ldda in ld.expired_datasets:
            expired_ldda_versions.append((self.app.security.encode_id(expired_ldda.id), expired_ldda.name))

        rval = self.app.security.encode_all_ids(ld.to_dict())
        if len(expired_ldda_versions) > 0:
            rval["has_versions"] = True
            rval["expired_versions"] = expired_ldda_versions

        ldda = ld.library_dataset_dataset_association
        if ldda.creating_job_associations:
            if ldda.creating_job_associations[0].job.stdout:
                rval["job_stdout"] = ldda.creating_job_associations[0].job.stdout.strip()
            if ldda.creating_job_associations[0].job.stderr:
                rval["job_stderr"] = ldda.creating_job_associations[0].job.stderr.strip()
        if ldda.dataset.uuid:
            rval["uuid"] = str(ldda.dataset.uuid)
        rval["deleted"] = ld.deleted
        rval["folder_id"] = f"F{rval['folder_id']}"
        rval["full_path"] = full_path
        rval["file_size"] = util.nice_size(int(ldda.get_size(calculate_size=False)))
        rval["date_uploaded"] = ldda.create_time.isoformat()
        rval["update_time"] = ldda.update_time.isoformat()
        rval["can_user_modify"] = trans.user_is_admin or self.app.security_agent.can_modify_library_item(
            current_user_roles, ld
        )
        rval["is_unrestricted"] = self.app.security_agent.dataset_is_public(ldda.dataset)
        rval["tags"] = trans.tag_handler.get_tags_list(ldda.tags)

        #  Manage dataset permission is always attached to the dataset itself, not the ld or ldda to maintain consistency
        rval["can_user_manage"] = trans.user_is_admin or self.app.security_agent.can_manage_dataset(
            current_user_roles, ldda.dataset
        )
        return rval

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
        if folder.parent_id is None:
            # We are almost in root
            path_to_root.append((f"F{self.app.security.encode_id(folder.id)}", folder.name))
        else:
            # We add the current folder and traverse up one folder.
            path_to_root.append((f"F{self.app.security.encode_id(folder.id)}", folder.name))
            upper_folder = trans.sa_session.get(LibraryFolder, folder.parent_id)
            path_to_root.extend(self._build_path(trans, upper_folder))
        return path_to_root


def get_library_dataset(session, library_dataset_id) -> LibraryDataset:
    stmt = select(LibraryDataset).where(LibraryDataset.id == library_dataset_id)
    return session.scalars(stmt).one()
