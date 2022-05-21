"""
API operations on the contents of a library folder.
"""
import logging

from galaxy import util
from galaxy.web import (
    expose_api,
    expose_api_anonymous,
)
from galaxy.webapps.galaxy.services.library_folder_contents import LibraryFolderContentsService
from . import (
    BaseGalaxyAPIController,
    depends,
)

log = logging.getLogger(__name__)


class FolderContentsController(BaseGalaxyAPIController):
    """
    Class controls retrieval, creation and updating of folder contents.
    """

    service: LibraryFolderContentsService = depends(LibraryFolderContentsService)

    @expose_api_anonymous
    def index(self, trans, folder_id, limit=None, offset=None, search_text=None, **kwd):
        """
        GET /api/folders/{encoded_folder_id}/contents?limit={limit}&offset={offset}

        Displays a collection (list) of a folder's contents
        (files and folders). Encoded folder ID is prepended
        with 'F' if it is a folder as opposed to a data set
        which does not have it. Full path is provided in
        response as a separate object providing data for
        breadcrumb path building.

        ..example:
            limit and offset can be combined. Skip the first two and return five:
                '?limit=3&offset=5'

        :param  folder_id: encoded ID of the folder which
            contents should be library_dataset_dict
        :type   folder_id: encoded string

        :param  offset: offset for returned library folder datasets
        :type   folder_id: encoded string

        :param  limit: limit   for returned library folder datasets
            contents should be library_dataset_dict
        :type   folder_id: encoded string

        :param kwd: keyword dictionary with other params
        :type  kwd: dict

        :returns: dictionary containing all items and metadata
        :type:    dict

        :raises: MalformedId, InconsistentDatabase, ObjectNotFound,
             InternalServerError
        """
        include_deleted = util.asbool(kwd.get("include_deleted", False))
        return self.service.index(trans, folder_id, limit, offset, search_text, include_deleted)

    @expose_api
    def create(self, trans, encoded_folder_id, payload, **kwd):
        """
        POST /api/folders/{encoded_id}/contents

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
        return self.service.create(trans, encoded_folder_id, payload)
