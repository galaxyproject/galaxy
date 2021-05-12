"""
API operations on a data library.
"""
import logging
from typing import (
    Any,
    Dict,
)

from galaxy import util
from galaxy.managers import libraries
from galaxy.web import (
    expose_api,
    expose_api_anonymous,
)
from . import BaseGalaxyAPIController, depends

log = logging.getLogger(__name__)


class LibrariesController(BaseGalaxyAPIController):
    service = depends(libraries.LibrariesService)

    @expose_api_anonymous
    def index(self, trans, **kwd):
        """
        index( self, trans, **kwd )
        * GET /api/libraries:
            Returns a list of summary data for all libraries.

        :param  deleted: if True, show only ``deleted`` libraries, if False show only ``non-deleted``
        :type   deleted: boolean (optional)

        :returns:   list of dictionaries containing library information
        :rtype:     list

        .. seealso:: :attr:`galaxy.model.Library.dict_collection_visible_keys`

        """
        deleted = util.string_as_bool_or_none(kwd.get('deleted', None))
        return self.service.index(trans, deleted)

    @expose_api_anonymous
    def show(self, trans, id, deleted='False', **kwd):
        """
        show( self, trans, id, deleted='False', **kwd )
        * GET /api/libraries/{encoded_id}:
            returns detailed information about a library
        * GET /api/libraries/deleted/{encoded_id}:
            returns detailed information about a ``deleted`` library

        :param  id:      the encoded id of the library
        :type   id:      an encoded id string
        :param  deleted: if True, allow information on a ``deleted`` library
        :type   deleted: boolean

        :returns:   detailed library information
        :rtype:     dictionary

        .. seealso:: :attr:`galaxy.model.Library.dict_element_visible_keys`

        :raises: MalformedId, ObjectNotFound
        """
        return self.service.show(trans, id)

    @expose_api
    def create(self, trans, payload: Dict[str, str], **kwd):
        """
        * POST /api/libraries:
            Creates a new library.

        .. note:: Currently, only admin users can create libraries.

        :param  payload: dictionary structure containing::
            :param name:         (required) the new library's name
            :type  name:         str
            :param description:  the new library's description
            :type  description:  str
            :param synopsis:     the new library's synopsis
            :type  synopsis:     str
        :type   payload: dict
        :returns:   detailed library information
        :rtype:     dict
        :raises: RequestParameterMissingException
        """
        return self.service.create(trans, payload)

    @expose_api
    def update(self, trans, id, payload: Dict[str, str], **kwd):
        """
        * PATCH /api/libraries/{encoded_id}
           Updates the library defined by an ``encoded_id`` with the data in the payload.

       .. note:: Currently, only admin users can update libraries. Also the library must not be `deleted`.

        :param  id:      the encoded id of the library
        :type   id:      an encoded id string
        :param  payload: dictionary structure containing::
            :param name:         new library's name, cannot be empty
            :type  name:         str
            :param description:  new library's description
            :type  description:  str
            :param synopsis:     new library's synopsis
            :type  synopsis:     str
        :type   payload: dict
        :returns:   detailed library information
        :rtype:     dict
        :raises: RequestParameterMissingException
        """
        return self.service.update(trans, id, payload)

    @expose_api
    def delete(self, trans, id, payload: Dict[str, Any] = None, **kwd):
        """
        * DELETE /api/libraries/{id}
            marks the library with the given ``id`` as `deleted` (or removes the `deleted` mark if the `undelete` param is true)

        .. note:: Currently, only admin users can un/delete libraries.

        :param  id:     the encoded id of the library to un/delete
        :type   id:     an encoded id string

        :param   payload: dictionary structure containing:
            :param  undelete:    (optional) flag specifying whether the item should be deleted or undeleted, defaults to false:
            :type   undelete:    bool
        :type:     dictionary
        :returns:   detailed library information
        :rtype:     dictionary

        .. seealso:: :attr:`galaxy.model.Library.dict_element_visible_keys`
        """
        if payload:
            kwd.update(payload)
        undelete = util.string_as_bool(kwd.get('undelete', False))
        return self.service.delete(trans, id, undelete)

    @expose_api
    def get_permissions(self, trans, encoded_library_id, **kwd):
        """
        * GET /api/libraries/{encoded_library_id}/permissions

        Load all permissions for the given library id and return it.

        :param  encoded_library_id:     the encoded id of the library
        :type   encoded_library_id:     an encoded id string

        :param  scope:      either 'current' or 'available'
        :type   scope:      string

        :param  is_library_access:      indicates whether the roles available for the library access are requested
        :type   is_library_access:      bool

        :returns:   dictionary with all applicable permissions' values
        :rtype:     dictionary

        :raises: InsufficientPermissionsException
        """
        scope = kwd.get('scope', None)
        is_library_access = util.string_as_bool(kwd.get('is_library_access', False))
        page = kwd.get('page', None)
        if page is not None:
            page = int(page)
        else:
            page = 1

        page_limit = kwd.get('page_limit', None)
        if page_limit is not None:
            page_limit = int(page_limit)
        else:
            page_limit = 10

        query = kwd.get('q', None)

        return self.service.get_permissions(trans, encoded_library_id, scope, is_library_access, page, page_limit, query)

    @expose_api
    def set_permissions(self, trans, encoded_library_id, payload: Dict[str, Any], **kwd):
        """
        POST /api/libraries/{encoded_library_id}/permissions

        Set permissions of the given library to the given role ids.

        :param  encoded_library_id:      the encoded id of the library to set the permissions of
        :type   encoded_library_id:      an encoded id string
        :param   payload: dictionary structure containing:

            :param  action:            (required) describes what action should be performed
                                       available actions: remove_restrictions, set_permissions
            :type   action:            str
            :param  access_ids[]:      list of Role.id defining roles that should have access permission on the library
            :type   access_ids[]:      string or list
            :param  add_ids[]:         list of Role.id defining roles that should have add item permission on the library
            :type   add_ids[]:         string or list
            :param  manage_ids[]:      list of Role.id defining roles that should have manage permission on the library
            :type   manage_ids[]:      string or list
            :param  modify_ids[]:      list of Role.id defining roles that should have modify permission on the library
            :type   modify_ids[]:      string or list

        :type:      dictionary
        :returns:   dict of current roles for all available permission types
        :rtype:     dictionary
        :raises: RequestParameterInvalidException, InsufficientPermissionsException, InternalServerError
                    RequestParameterMissingException
        """
        return self.service.set_permissions(trans, encoded_library_id, payload)
