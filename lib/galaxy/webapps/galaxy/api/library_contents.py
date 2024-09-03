"""
API operations on the contents of a data library.
"""

import logging
from typing import Optional

from galaxy import (
    exceptions,
    managers,
    util,
)
from galaxy.actions.library import (
    LibraryActions,
    validate_path_upload,
)
from galaxy.managers.collections_util import (
    api_payload_to_create_params,
    dictify_dataset_collection_instance,
)
from galaxy.model import (
    ExtendedMetadata,
    ExtendedMetadataIndex,
    Library,
    LibraryDataset,
    LibraryFolder,
    tags,
)
from galaxy.model.base import transaction
from galaxy.structured_app import StructuredApp
from galaxy.web import expose_api
from galaxy.webapps.base.controller import (
    HTTPBadRequest,
    url_for,
    UsesFormDefinitionsMixin,
    UsesLibraryMixinItems,
)
from galaxy.webapps.galaxy.api import BaseGalaxyAPIController

log = logging.getLogger(__name__)


class LibraryContentsController(
    BaseGalaxyAPIController, UsesLibraryMixinItems, UsesFormDefinitionsMixin, LibraryActions
):
    def __init__(self, app: StructuredApp, hda_manager: managers.hdas.HDAManager):
        super().__init__(app)
        self.hda_manager = hda_manager

    @expose_api
    def index(self, trans, library_id, **kwd):
        """
        GET /api/libraries/{library_id}/contents:

        Return a list of library files and folders.

        .. note:: This endpoint is slow for large libraries. Returns all content traversing recursively through all folders.
        .. seealso:: :class:`galaxy.webapps.galaxy.api.FolderContentsController.index` for a faster non-recursive solution

        :param  library_id: the encoded id of the library
        :type   library_id: str

        :returns:   list of dictionaries of the form:

            * id:   the encoded id of the library item
            * name: the 'library path'
                or relationship of the library item to the root
            * type: 'file' or 'folder'
            * url:  the url to get detailed information on the library item

        :rtype:     list

        :raises:  MalformedId, InconsistentDatabase, RequestParameterInvalidException, InternalServerError
        """
        rval = []
        current_user_roles = trans.get_current_user_roles()

        def traverse(folder):
            admin = trans.user_is_admin
            rval = []
            for subfolder in folder.active_folders:
                if not admin:
                    can_access, folder_ids = trans.app.security_agent.check_folder_contents(
                        trans.user, current_user_roles, subfolder
                    )
                if (admin or can_access) and not subfolder.deleted:
                    subfolder.api_path = f"{folder.api_path}/{subfolder.name}"
                    subfolder.api_type = "folder"
                    rval.append(subfolder)
                    rval.extend(traverse(subfolder))
            for ld in folder.datasets:
                if not admin:
                    can_access = trans.app.security_agent.can_access_dataset(
                        current_user_roles, ld.library_dataset_dataset_association.dataset
                    )
                if (admin or can_access) and not ld.deleted:
                    ld.api_path = f"{folder.api_path}/{ld.name}"
                    ld.api_type = "file"
                    rval.append(ld)
            return rval

        library = trans.sa_session.get(Library, self.decode_id(library_id))
        if not library:
            raise exceptions.RequestParameterInvalidException("No library found with the id provided.")
        if not (trans.user_is_admin or trans.app.security_agent.can_access_library(current_user_roles, library)):
            raise exceptions.RequestParameterInvalidException("No library found with the id provided.")
        encoded_id = f"F{trans.security.encode_id(library.root_folder.id)}"
        # appending root folder
        rval.append(
            dict(
                id=encoded_id,
                type="folder",
                name="/",
                url=url_for("library_content", library_id=library_id, id=encoded_id),
            )
        )
        library.root_folder.api_path = ""
        # appending all other items in the library recursively
        for content in traverse(library.root_folder):
            encoded_id = trans.security.encode_id(content.id)
            if content.api_type == "folder":
                encoded_id = f"F{encoded_id}"
            rval.append(
                dict(
                    id=encoded_id,
                    type=content.api_type,
                    name=content.api_path,
                    url=url_for(
                        "library_content",
                        library_id=library_id,
                        id=encoded_id,
                    ),
                )
            )
        return rval

    @expose_api
    def show(self, trans, id, library_id, **kwd):
        """
        GET /api/libraries/{library_id}/contents/{id}

        Returns information about library file or folder.

        :param  id:         the encoded id of the library item to return
        :type   id:         str

        :param  library_id: the encoded id of the library that contains this item
        :type   library_id: str

        :returns:   detailed library item information
        :rtype:     dict

        .. seealso::
            :func:`galaxy.model.LibraryDataset.to_dict` and
            :attr:`galaxy.model.LibraryFolder.dict_element_visible_keys`
        """
        class_name, content_id = self._decode_library_content_id(id)
        if class_name == "LibraryFolder":
            content = self.get_library_folder(trans, content_id, check_ownership=False, check_accessible=True)
            rval = content.to_dict(view="element", value_mapper={"id": trans.security.encode_id})
            rval["id"] = f"F{str(rval['id'])}"
            if rval["parent_id"] is not None:  # This can happen for root folders.
                rval["parent_id"] = f"F{str(trans.security.encode_id(rval['parent_id']))}"
            rval["parent_library_id"] = trans.security.encode_id(rval["parent_library_id"])
        else:
            content = self.get_library_dataset(trans, content_id, check_ownership=False, check_accessible=True)
            rval = content.to_dict(view="element")
            rval["id"] = trans.security.encode_id(rval["id"])
            rval["ldda_id"] = trans.security.encode_id(rval["ldda_id"])
            rval["folder_id"] = f"F{str(trans.security.encode_id(rval['folder_id']))}"
            rval["parent_library_id"] = trans.security.encode_id(rval["parent_library_id"])

            tag_manager = tags.GalaxyTagHandler(trans.sa_session)
            rval["tags"] = tag_manager.get_tags_list(content.library_dataset_dataset_association.tags)
        return rval

    @expose_api
    def create(self, trans, library_id, payload, **kwd):
        """
        POST /api/libraries/{library_id}/contents:

        Create a new library file or folder.

        To copy an HDA into a library send ``create_type`` of 'file' and
        the HDA's encoded id in ``from_hda_id`` (and optionally ``ldda_message``).

        To copy an HDCA into a library send ``create_type`` of 'file' and
        the HDCA's encoded id in ``from_hdca_id`` (and optionally ``ldda_message``).

        :type   library_id: str
        :param  library_id: the encoded id of the library where to create the new item
        :type   payload:    dict
        :param  payload:    dictionary structure containing:

            * folder_id:    the encoded id of the parent folder of the new item
            * create_type:  the type of item to create ('file', 'folder' or 'collection')
            * from_hda_id:  (optional, only if create_type is 'file') the
                encoded id of an accessible HDA to copy into the library
            * ldda_message: (optional) the new message attribute of the LDDA created
            * extended_metadata: (optional) sub-dictionary containing any extended
                metadata to associate with the item
            * upload_option: (optional) one of 'upload_file' (default), 'upload_directory' or 'upload_paths'
            * server_dir: (optional, only if upload_option is
                'upload_directory') relative path of the subdirectory of Galaxy
                ``library_import_dir`` (if admin) or ``user_library_import_dir``
                (if non-admin) to upload. All and only the files (i.e.
                no subdirectories) contained in the specified directory will be
                uploaded.
            * filesystem_paths: (optional, only if upload_option is
                'upload_paths' and the user is an admin) file paths on the
                Galaxy server to upload to the library, one file per line
            * link_data_only: (optional, only when upload_option is
                'upload_directory' or 'upload_paths') either 'copy_files'
                (default) or 'link_to_files'. Setting to 'link_to_files'
                symlinks instead of copying the files
            * name: (optional, only if create_type is 'folder') name of the
                folder to create
            * description: (optional, only if create_type is 'folder')
                description of the folder to create
            * tag_using_filenames: (optional)
                create tags on datasets using the file's original name
            * tags: (optional)
                create the given list of tags on datasets

        :returns:   a dictionary describing the new item unless ``from_hdca_id`` is supplied,
                    in that case a list of such dictionaries is returned.
        :rtype:     object
        """
        if trans.user_is_bootstrap_admin:
            raise exceptions.RealUserRequiredException("Only real users can create a new library file or folder.")
        if "create_type" not in payload:
            raise exceptions.RequestParameterMissingException("Missing required 'create_type' parameter.")
        create_type = payload.pop("create_type")
        if create_type not in ("file", "folder", "collection"):
            raise exceptions.RequestParameterInvalidException(
                f"Invalid value for 'create_type' parameter ( {create_type} ) specified."
            )
        if "upload_option" in payload and payload["upload_option"] not in (
            "upload_file",
            "upload_directory",
            "upload_paths",
        ):
            raise exceptions.RequestParameterInvalidException(
                f"Invalid value for 'upload_option' parameter ( {payload['upload_option']} ) specified."
            )
        if "folder_id" not in payload:
            raise exceptions.RequestParameterMissingException("Missing required 'folder_id' parameter.")
        folder_id = payload.pop("folder_id")
        _, folder_id = self._decode_library_content_id(folder_id)
        folder_id = trans.security.decode_id(folder_id)
        # security is checked in the downstream controller
        parent = self.get_library_folder(trans, folder_id, check_ownership=False, check_accessible=False)
        # The rest of the security happens in the library_common controller.

        payload["tag_using_filenames"] = util.string_as_bool(payload.get("tag_using_filenames", None))
        payload["tags"] = util.listify(payload.get("tags", None))

        # are we copying an HDA to the library folder?
        #   we'll need the id and any message to attach, then branch to that private function
        from_hda_id, from_hdca_id, ldda_message = (
            payload.pop("from_hda_id", None),
            payload.pop("from_hdca_id", None),
            payload.pop("ldda_message", ""),
        )
        if create_type == "file":
            if from_hda_id:
                return self._copy_hda_to_library_folder(
                    trans, self.hda_manager, self.decode_id(from_hda_id), folder_id, ldda_message
                )
            if from_hdca_id:
                return self._copy_hdca_to_library_folder(
                    trans, self.hda_manager, self.decode_id(from_hdca_id), folder_id, ldda_message
                )

        # check for extended metadata, store it and pop it out of the param
        # otherwise sanitize_param will have a fit
        ex_meta_payload = payload.pop("extended_metadata", None)

        # Now create the desired content object, either file or folder.
        if create_type == "file":
            status, output = self._upload_library_dataset(trans, folder_id, **payload)
        elif create_type == "folder":
            status, output = self._create_folder(trans, folder_id, **payload)
        elif create_type == "collection":
            # Not delegating to library_common, so need to check access to parent
            # folder here.
            self.check_user_can_add_to_library_item(trans, parent, check_accessible=True)
            create_params = api_payload_to_create_params(payload)
            create_params["parent"] = parent
            dataset_collection_manager = trans.app.dataset_collection_manager
            dataset_collection_instance = dataset_collection_manager.create(**create_params)
            return [
                dictify_dataset_collection_instance(
                    dataset_collection_instance, security=trans.security, url_builder=trans.url_builder, parent=parent
                )
            ]
        if status != 200:
            trans.response.status = status
            return output
        else:
            rval = []
            for v in output.values():
                if ex_meta_payload is not None:
                    # If there is extended metadata, store it, attach it to the dataset, and index it
                    ex_meta = ExtendedMetadata(ex_meta_payload)
                    trans.sa_session.add(ex_meta)
                    v.extended_metadata = ex_meta
                    trans.sa_session.add(v)
                    with transaction(trans.sa_session):
                        trans.sa_session.commit()
                    for path, value in self._scan_json_block(ex_meta_payload):
                        meta_i = ExtendedMetadataIndex(ex_meta, path, value)
                        trans.sa_session.add(meta_i)
                    with transaction(trans.sa_session):
                        trans.sa_session.commit()
                if isinstance(v, trans.app.model.LibraryDatasetDatasetAssociation):
                    v = v.library_dataset
                encoded_id = trans.security.encode_id(v.id)
                if create_type == "folder":
                    encoded_id = f"F{encoded_id}"
                rval.append(
                    dict(
                        id=encoded_id, name=v.name, url=url_for("library_content", library_id=library_id, id=encoded_id)
                    )
                )
            return rval

    def _upload_library_dataset(self, trans, folder_id: int, **kwd):
        replace_dataset: Optional[LibraryDataset] = None
        upload_option = kwd.get("upload_option", "upload_file")
        dbkey = kwd.get("dbkey", "?")
        if isinstance(dbkey, list):
            last_used_build = dbkey[0]
        else:
            last_used_build = dbkey
        is_admin = trans.user_is_admin
        current_user_roles = trans.get_current_user_roles()
        folder = trans.sa_session.get(LibraryFolder, folder_id)
        self._check_access(trans, is_admin, folder, current_user_roles)
        self._check_add(trans, is_admin, folder, current_user_roles)
        library = folder.parent_library
        if folder and last_used_build in ["None", None, "?"]:
            last_used_build = folder.genome_build
        error = False
        if upload_option == "upload_paths":
            validate_path_upload(trans)  # Duplicate check made in _upload_dataset.
        elif roles := kwd.get("roles", ""):
            # Check to see if the user selected roles to associate with the DATASET_ACCESS permission
            # on the dataset that would cause accessibility issues.
            vars = dict(DATASET_ACCESS_in=roles)
            permissions, in_roles, error, message = trans.app.security_agent.derive_roles_from_access(
                trans, library.id, "api", library=True, **vars
            )
        if error:
            return 400, message
        else:
            created_outputs_dict = self._upload_dataset(
                trans, folder_id=folder.id, replace_dataset=replace_dataset, **kwd
            )
            if created_outputs_dict:
                if isinstance(created_outputs_dict, str):
                    return 400, created_outputs_dict
                elif isinstance(created_outputs_dict, tuple):
                    return created_outputs_dict[0], created_outputs_dict[1]
                return 200, created_outputs_dict
            else:
                return 400, "Upload failed"

    def _scan_json_block(self, meta, prefix=""):
        """
        Scan a json style data structure, and emit all fields and their values.
        Example paths

        Data
        { "data" : [ 1, 2, 3 ] }

        Path:
        /data == [1,2,3]

        /data/[0] == 1

        """
        if isinstance(meta, dict):
            for a in meta:
                yield from self._scan_json_block(meta[a], f"{prefix}/{a}")
        elif isinstance(meta, list):
            for i, a in enumerate(meta):
                yield from self._scan_json_block(a, prefix + "[%d]" % (i))
        else:
            # BUG: Everything is cast to string, which can lead to false positives
            # for cross type comparisions, ie "True" == True
            yield prefix, (f"{meta}").encode()

    @expose_api
    def update(self, trans, id, library_id, payload, **kwd):
        """
        PUT /api/libraries/{library_id}/contents/{id}

        Create an ImplicitlyConvertedDatasetAssociation.

        .. seealso:: :class:`galaxy.model.ImplicitlyConvertedDatasetAssociation`

        :type   id:         str
        :param  id:         the encoded id of the library item to return
        :type   library_id: str
        :param  library_id: the encoded id of the library that contains this item
        :type   payload:    dict
        :param  payload:    dictionary structure containing::
            'converted_dataset_id':

        :rtype:     None
        :returns:   None
        """
        if "converted_dataset_id" in payload:
            converted_id = payload.pop("converted_dataset_id")
            content = self.get_library_dataset(trans, id, check_ownership=False, check_accessible=False)
            content_conv = self.get_library_dataset(trans, converted_id, check_ownership=False, check_accessible=False)
            assoc = trans.app.model.ImplicitlyConvertedDatasetAssociation(
                parent=content.library_dataset_dataset_association,
                dataset=content_conv.library_dataset_dataset_association,
                file_type=content_conv.library_dataset_dataset_association.extension,
                metadata_safe=True,
            )
            trans.sa_session.add(assoc)
            with transaction(trans.sa_session):
                trans.sa_session.commit()

    def _decode_library_content_id(self, content_id):
        if len(content_id) % 16 == 0:
            return "LibraryDataset", content_id
        elif content_id.startswith("F"):
            return "LibraryFolder", content_id[1:]
        else:
            raise HTTPBadRequest(f"Malformed library content id ( {str(content_id)} ) specified, unable to decode.")

    @expose_api
    def delete(self, trans, library_id, id, **kwd):
        """
        DELETE /api/libraries/{library_id}/contents/{id}

        Delete the LibraryDataset with the given ``id``.

        :type   id:     str
        :param  id:     the encoded id of the library dataset to delete
        :type   kwd:    dict
        :param  kwd:    (optional) dictionary structure containing:

            * payload:     a dictionary itself containing:
                * purge:   if True, purge the LD

        :rtype:     dict
        :returns:   an error object if an error occurred or a dictionary containing:
            * id:         the encoded id of the library dataset,
            * deleted:    if the library dataset was marked as deleted,
            * purged:     if the library dataset was purged
        """
        purge = False
        if kwd.get("payload", None):
            purge = util.string_as_bool(kwd["payload"].get("purge", False))

        rval = {"id": id}
        try:
            ld = self.get_library_dataset(trans, id, check_ownership=False, check_accessible=True)
            user_is_admin = trans.user_is_admin
            can_modify = trans.app.security_agent.can_modify_library_item(trans.user.all_roles(), ld)
            log.debug("is_admin: %s, can_modify: %s", user_is_admin, can_modify)
            if not (user_is_admin or can_modify):
                trans.response.status = 403
                rval.update({"error": "Unauthorized to delete or purge this library dataset"})
                return rval

            ld.deleted = True
            if purge:
                ld.purged = True
                trans.sa_session.add(ld)
                with transaction(trans.sa_session):
                    trans.sa_session.commit()

                # TODO: had to change this up a bit from Dataset.user_can_purge
                dataset = ld.library_dataset_dataset_association.dataset
                no_history_assoc = len(dataset.history_associations) == len(dataset.purged_history_associations)
                no_library_assoc = dataset.library_associations == [ld.library_dataset_dataset_association]
                can_purge_dataset = not dataset.purged and no_history_assoc and no_library_assoc

                if can_purge_dataset:
                    try:
                        ld.library_dataset_dataset_association.dataset.full_delete()
                        trans.sa_session.add(ld.dataset)
                    except Exception:
                        pass
                    # flush now to preserve deleted state in case of later interruption
                    with transaction(trans.sa_session):
                        trans.sa_session.commit()
                rval["purged"] = True
            with transaction(trans.sa_session):
                trans.sa_session.commit()
            rval["deleted"] = True

        except exceptions.httpexceptions.HTTPInternalServerError:
            log.exception("Library_contents API, delete: uncaught HTTPInternalServerError: %s, %s", id, str(kwd))
            raise
        except exceptions.httpexceptions.HTTPException:
            raise
        except Exception as exc:
            log.exception("library_contents API, delete: uncaught exception: %s, %s", id, str(kwd))
            trans.response.status = 500
            rval.update({"error": util.unicodify(exc)})
        return rval
