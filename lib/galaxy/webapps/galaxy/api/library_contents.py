"""
API operations on the contents of a data library.
"""
import logging

from galaxy import (
    managers,
    util,
)
from galaxy.actions.library import LibraryActions, validate_path_upload
from galaxy.managers.collections_util import (
    api_payload_to_create_params,
    dictify_dataset_collection_instance
)
from galaxy.model import (
    ExtendedMetadata,
    ExtendedMetadataIndex
)
from galaxy.web import expose_api
from galaxy.webapps.base.controller import (
    BaseAPIController,
    HTTPBadRequest,
    url_for,
    UsesFormDefinitionsMixin,
    UsesLibraryMixin,
    UsesLibraryMixinItems
)
log = logging.getLogger(__name__)


class LibraryContentsController(BaseAPIController, UsesLibraryMixin, UsesLibraryMixinItems, UsesFormDefinitionsMixin, LibraryActions):

    def __init__(self, app):
        super(LibraryContentsController, self).__init__(app)
        self.hda_manager = managers.hdas.HDAManager(app)

    @expose_api
    def create(self, trans, library_id, payload, **kwd):
        """
        * POST /api/libraries/{library_id}/contents:
            create a new library file or folder

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
            * tag_using_filename: (optional)
                create tags on datasets using the file's original name

        :returns:   a dictionary describing the new item unless ``from_hdca_id`` is supplied,
                    in that case a list of such dictionaries is returned.
        :rtype:     object
        """
        if 'create_type' not in payload:
            trans.response.status = 400
            return "Missing required 'create_type' parameter."
        else:
            create_type = payload.pop('create_type')
        if create_type not in ('file', 'folder', 'collection'):
            trans.response.status = 400
            return "Invalid value for 'create_type' parameter ( %s ) specified." % create_type

        if 'folder_id' not in payload:
            trans.response.status = 400
            return "Missing required 'folder_id' parameter."
        else:
            folder_id = payload.pop('folder_id')
            class_name, folder_id = self._decode_library_content_id(folder_id)
        try:
            # security is checked in the downstream controller
            parent = self.get_library_folder(trans, folder_id, check_ownership=False, check_accessible=False)
        except Exception as e:
            return util.unicodify(e)
        # The rest of the security happens in the library_common controller.
        real_folder_id = trans.security.encode_id(parent.id)

        payload['tag_using_filenames'] = util.string_as_bool(payload.get('tag_using_filenames', None))

        # are we copying an HDA to the library folder?
        #   we'll need the id and any message to attach, then branch to that private function
        from_hda_id, from_hdca_id, ldda_message = (payload.pop('from_hda_id', None), payload.pop('from_hdca_id', None), payload.pop('ldda_message', ''))
        if create_type == 'file':
            if from_hda_id:
                return self._copy_hda_to_library_folder(trans, self.hda_manager, self.decode_id(from_hda_id), real_folder_id, ldda_message)
            if from_hdca_id:
                return self._copy_hdca_to_library_folder(trans, self.hda_manager, self.decode_id(from_hdca_id), real_folder_id, ldda_message)

        # check for extended metadata, store it and pop it out of the param
        # otherwise sanitize_param will have a fit
        ex_meta_payload = payload.pop('extended_metadata', None)

        # Now create the desired content object, either file or folder.
        if create_type == 'file':
            status, output = self._upload_library_dataset(trans, library_id, real_folder_id, **payload)
        elif create_type == 'folder':
            status, output = self._create_folder(trans, real_folder_id, library_id, **payload)
        elif create_type == 'collection':
            # Not delegating to library_common, so need to check access to parent
            # folder here.
            self.check_user_can_add_to_library_item(trans, parent, check_accessible=True)
            create_params = api_payload_to_create_params(payload)
            create_params['parent'] = parent
            service = trans.app.dataset_collections_service
            dataset_collection_instance = service.create(**create_params)
            return [dictify_dataset_collection_instance(dataset_collection_instance, security=trans.security, parent=parent)]
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
                    trans.sa_session.flush()
                    for path, value in self._scan_json_block(ex_meta_payload):
                        meta_i = ExtendedMetadataIndex(ex_meta, path, value)
                        trans.sa_session.add(meta_i)
                    trans.sa_session.flush()
                if type(v) == trans.app.model.LibraryDatasetDatasetAssociation:
                    v = v.library_dataset
                encoded_id = trans.security.encode_id(v.id)
                if create_type == 'folder':
                    encoded_id = 'F' + encoded_id
                rval.append(dict(id=encoded_id,
                                 name=v.name,
                                 url=url_for('library_content', library_id=library_id, id=encoded_id)))
            return rval

    def _upload_library_dataset(self, trans, library_id, folder_id, **kwd):
        replace_id = kwd.get('replace_id', None)
        replace_dataset = None
        upload_option = kwd.get('upload_option', 'upload_file')
        dbkey = kwd.get('dbkey', '?')
        if isinstance(dbkey, list):
            last_used_build = dbkey[0]
        else:
            last_used_build = dbkey
        roles = kwd.get('roles', '')
        is_admin = trans.user_is_admin
        current_user_roles = trans.get_current_user_roles()
        if replace_id not in ['', None, 'None']:
            replace_dataset = trans.sa_session.query(trans.app.model.LibraryDataset).get(trans.security.decode_id(replace_id))
            self._check_access(trans, is_admin, replace_dataset, current_user_roles)
            self._check_modify(trans, is_admin, replace_dataset, current_user_roles)
            library = replace_dataset.folder.parent_library
            folder = replace_dataset.folder
            # The name is stored - by the time the new ldda is created, replace_dataset.name
            # will point to the new ldda, not the one it's replacing.
            if not last_used_build:
                last_used_build = replace_dataset.library_dataset_dataset_association.dbkey
        else:
            folder = trans.sa_session.query(trans.app.model.LibraryFolder).get(trans.security.decode_id(folder_id))
            self._check_access(trans, is_admin, folder, current_user_roles)
            self._check_add(trans, is_admin, folder, current_user_roles)
            library = folder.parent_library
        if folder and last_used_build in ['None', None, '?']:
            last_used_build = folder.genome_build
        error = False
        if upload_option == 'upload_paths':
            validate_path_upload(trans)  # Duplicate check made in _upload_dataset.
        elif upload_option not in ('upload_file', 'upload_directory', 'upload_paths'):
            error = True
            message = 'Invalid upload_option'
        elif roles:
            # Check to see if the user selected roles to associate with the DATASET_ACCESS permission
            # on the dataset that would cause accessibility issues.
            vars = dict(DATASET_ACCESS_in=roles)
            permissions, in_roles, error, message = \
                trans.app.security_agent.derive_roles_from_access(trans, library.id, 'api', library=True, **vars)
        if error:
            return 400, message
        else:
            created_outputs_dict = self._upload_dataset(trans,
                                                        library_id=trans.security.encode_id(library.id),
                                                        folder_id=trans.security.encode_id(folder.id),
                                                        replace_dataset=replace_dataset,
                                                        **kwd)
            if created_outputs_dict:
                if type(created_outputs_dict) == str:
                    return 400, created_outputs_dict
                elif type(created_outputs_dict) == tuple:
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
                for path, value in self._scan_json_block(meta[a], prefix + "/" + a):
                    yield path, value
        elif isinstance(meta, list):
            for i, a in enumerate(meta):
                for path, value in self._scan_json_block(a, prefix + "[%d]" % (i)):
                    yield path, value
        else:
            # BUG: Everything is cast to string, which can lead to false positives
            # for cross type comparisions, ie "True" == True
            yield prefix, ("%s" % (meta)).encode("utf8", errors='replace')

    def _decode_library_content_id(self, content_id):
        if len(content_id) % 16 == 0:
            return 'LibraryDataset', content_id
        elif content_id.startswith('F'):
            return 'LibraryFolder', content_id[1:]
        else:
            raise HTTPBadRequest('Malformed library content id ( %s ) specified, unable to decode.' % str(content_id))
