"""
API operations on library folders.
"""
import logging

from galaxy import (
    exceptions,
    util
)
from galaxy.managers.folders import FoldersService
from galaxy.web import expose_api
from . import (
    BaseGalaxyAPIController,
    depends,
)

log = logging.getLogger(__name__)


class FoldersController(BaseGalaxyAPIController):

    service: FoldersService = depends(FoldersService)

    @expose_api
    def index(self, trans, **kwd):
        """
        GET /api/folders/

        This would normally display a list of folders. However, that would
        be across multiple libraries, so it's not implemented.
        """
        raise exceptions.NotImplemented('Listing all accessible library folders is not implemented.')

    @expose_api
    def show(self, trans, id, **kwd):
        """
        GET /api/folders/{encoded_folder_id}

        Displays information about a folder.

        :param  id:      the folder's encoded id (required)
        :type   id:      an encoded id string (has to be prefixed by 'F')

        :returns:   dictionary including details of the folder
        :rtype:     dict
        """
        return self.service.show(trans, id)

    @expose_api
    def create(self, trans, encoded_parent_folder_id, payload, **kwd):
        """
        POST /api/folders/{encoded_parent_folder_id}

        Create a new folder object underneath the one specified in the parameters.

        :param  encoded_parent_folder_id:      (required) the parent folder's id
        :type   encoded_parent_folder_id:      an encoded id string (should be prefixed by 'F')
        :param   payload: dictionary structure containing:

            :param  name:                          (required) the name of the new folder
            :type   name:                          str
            :param  description:                   the description of the new folder
            :type   description:                   str

        :type       dictionary
        :returns:   information about newly created folder, notably including ID
        :rtype:     dictionary
        :raises: RequestParameterMissingException
        """
        return self.service.create(trans, encoded_parent_folder_id, payload)

    @expose_api
    def get_permissions(self, trans, encoded_folder_id, **kwd):
        """
        GET /api/folders/{id}/permissions

        Load all permissions for the given folder id and return it.

        :param  encoded_folder_id:     the encoded id of the folder
        :type   encoded_folder_id:     an encoded id string

        :param  scope:      either 'current' or 'available'
        :type   scope:      string

        :returns:   dictionary with all applicable permissions' values
        :rtype:     dictionary

        :raises: InsufficientPermissionsException
        """
        scope = kwd.get('scope', None)
        page = kwd.get('page', None)
        page_limit = kwd.get('page_limit', None)
        query = kwd.get('q', None)
        return self.service.get_permissions(trans, encoded_folder_id, scope, page, page_limit, query)

    @expose_api
    def set_permissions(self, trans, encoded_folder_id, payload, **kwd):
        """
        POST /api/folders/{encoded_folder_id}/permissions

        Set permissions of the given folder to the given role ids.

        :param  encoded_folder_id:      the encoded id of the folder to set the permissions of
        :type   encoded_folder_id:      an encoded id string
        :param   payload: dictionary structure containing:

            :param  action:            (required) describes what action should be performed
            :type   action:            string
            :param  add_ids[]:         list of Role.id defining roles that should have add item permission on the folder
            :type   add_ids[]:         string or list
            :param  manage_ids[]:      list of Role.id defining roles that should have manage permission on the folder
            :type   manage_ids[]:      string or list
            :param  modify_ids[]:      list of Role.id defining roles that should have modify permission on the folder
            :type   modify_ids[]:      string or list

        :type       dictionary
        :returns:   dict of current roles for all available permission types.
        :rtype:     dictionary
        :raises: RequestParameterInvalidException, InsufficientPermissionsException, RequestParameterMissingException
        """
        return self.service.set_permissions(trans, encoded_folder_id, payload)

    @expose_api
    def delete(self, trans, encoded_folder_id, **kwd):
        """
        DELETE /api/folders/{encoded_folder_id}

        Mark the folder with the given ``encoded_folder_id`` as `deleted`
        (or remove the `deleted` mark if the `undelete` param is true).

        .. note:: Currently, only admin users can un/delete folders.

        :param  encoded_folder_id:     the encoded id of the folder to un/delete
        :type   encoded_folder_id:     an encoded id string

        :param  undelete:    (optional) flag specifying whether the item should be deleted or undeleted, defaults to false:
        :type   undelete:    bool

        :returns:   detailed folder information
        :rtype:     dictionary

        """
        undelete = util.string_as_bool(kwd.get('undelete', False))
        return self.service.delete(trans, encoded_folder_id, undelete)

    @expose_api
    def update(self, trans, encoded_folder_id, payload, **kwd):
        """
        PATCH /api/folders/{encoded_folder_id}

        Update the folder defined by an ``encoded_folder_id``
        with the data in the payload.

       .. note:: Currently, only admin users can update library folders. Also the folder must not be `deleted`.

        :param  id:      the encoded id of the folder
        :type   id:      an encoded id string

        :param  payload: (required) dictionary structure containing::
            'name':         new folder's name, cannot be empty
            'description':  new folder's description
        :type   payload: dict

        :returns:   detailed folder information
        :rtype:     dict

        :raises: RequestParameterMissingException
        """
        return self.service.update(trans, encoded_folder_id, payload)
