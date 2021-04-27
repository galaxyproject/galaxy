"""
API operations on a history.

.. seealso:: :class:`galaxy.model.History`
"""
import logging
from typing import Optional

from fastapi import (
    Body,
    Path,
    status,
)

from galaxy import (
    util
)
from galaxy.managers import (
    histories,
    sharable,
)
from galaxy.managers.context import ProvidesUserContext
from galaxy.schema import FilterQueryParams
from galaxy.schema.fields import (
    EncodedDatabaseIdField,
    OrderParamField,
)
from galaxy.schema.schema import (
    CreateHistoryPayload,
    ExportHistoryArchivePayload,
)
from galaxy.util import (
    string_as_bool
)
from galaxy.web import (
    expose_api,
    expose_api_anonymous,
    expose_api_anonymous_and_sessionless,
    expose_api_raw,
)
from galaxy.webapps.galaxy.api.configuration import parse_serialization_params
from . import (
    BaseGalaxyAPIController,
    depends,
    DependsOnTrans,
    Router,
)

log = logging.getLogger(__name__)

router = Router(tags=['histories'])

HistoryIdPathParam: EncodedDatabaseIdField = Path(
    ...,
    title="History ID",
    description="The encoded database identifier of the History."
)


@router.cbv
class FastAPIHistories:
    service: histories.HistoriesService = depends(histories.HistoriesService)

    @router.get(
        '/api/histories/{id}/sharing',
        summary="Get the current sharing status of the given item.",
    )
    def sharing(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        id: EncodedDatabaseIdField = HistoryIdPathParam,
    ) -> sharable.SharingStatus:
        """Return the sharing status of the item."""
        return self.service.shareable_service.sharing(trans, id)

    @router.put(
        '/api/histories/{id}/enable_link_access',
        summary="Makes this item accessible by a URL link.",
    )
    def enable_link_access(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        id: EncodedDatabaseIdField = HistoryIdPathParam,
    ) -> sharable.SharingStatus:
        """Makes this item accessible by a URL link and return the current sharing status."""
        return self.service.shareable_service.enable_link_access(trans, id)

    @router.put(
        '/api/histories/{id}/disable_link_access',
        summary="Makes this item inaccessible by a URL link.",
    )
    def disable_link_access(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        id: EncodedDatabaseIdField = HistoryIdPathParam,
    ) -> sharable.SharingStatus:
        """Makes this item inaccessible by a URL link and return the current sharing status."""
        return self.service.shareable_service.disable_link_access(trans, id)

    @router.put(
        '/api/histories/{id}/publish',
        summary="Makes this item public and accessible by a URL link.",
    )
    def publish(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        id: EncodedDatabaseIdField = HistoryIdPathParam,
    ) -> sharable.SharingStatus:
        """Makes this item publicly available by a URL link and return the current sharing status."""
        return self.service.shareable_service.publish(trans, id)

    @router.put(
        '/api/histories/{id}/unpublish',
        summary="Removes this item from the published list.",
    )
    def unpublish(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        id: EncodedDatabaseIdField = HistoryIdPathParam,
    ) -> sharable.SharingStatus:
        """Removes this item from the published list and return the current sharing status."""
        return self.service.shareable_service.unpublish(trans, id)

    @router.put(
        '/api/histories/{id}/share',
        summary="Share this item with specific users.",
    )
    def share(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        id: EncodedDatabaseIdField = HistoryIdPathParam,
        payload: sharable.UserIdsPayload = Body(...)
    ) -> sharable.ShareWithStatus:
        """Shares this item with specific users and return the current sharing status."""
        return self.service.shareable_service.share_with(trans, id, payload)

    @router.put(
        '/api/histories/{id}/unshare',
        summary="Stop sharing this item with specific users.",
    )
    def unshare(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        id: EncodedDatabaseIdField = HistoryIdPathParam,
        payload: sharable.UserIdsPayload = Body(...)
    ) -> sharable.ShareWithStatus:
        """Stops sharing this item with specific users and return the current sharing status."""
        return self.service.shareable_service.unshare_with(trans, id, payload)

    @router.put(
        '/api/histories/{id}/slug',
        summary="Set a new slug for this shared item.",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def set_slug(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        id: EncodedDatabaseIdField = HistoryIdPathParam,
        payload: sharable.SetSlugPayload = Body(...),
    ):
        """Sets a new slug to access this item by URL. The new slug must be unique."""
        self.service.shareable_service.set_slug(trans, id, payload)


class HistoryFilterQueryParams(FilterQueryParams):
    order: Optional[str] = OrderParamField(default_order="create_time-dsc")


class HistoriesController(BaseGalaxyAPIController):
    service: histories.HistoriesService = depends(histories.HistoriesService)

    @expose_api_anonymous
    def index(self, trans, deleted='False', **kwd):
        """
        GET /api/histories

        return undeleted histories for the current user

        GET /api/histories/deleted

        return deleted histories for the current user

        .. note:: Anonymous users are allowed to get their current history

        :type   deleted: boolean
        :param  deleted: if True, show only deleted histories, if False, non-deleted

        :rtype:     list
        :returns:   list of dictionaries containing summary history information

        The following are optional parameters:

            view:   string, one of ('summary','detailed'), defaults to 'summary'
                    controls which set of properties to return
            keys:   comma separated strings, unused by default
                    keys/names of individual properties to return
            all:    boolean, defaults to 'false', admin-only
                    returns all histories, not just current user's

        If neither keys or views are sent, the default view (set of keys) is returned.
        If both a view and keys are sent, the key list and the view's keys are
        combined.

        If keys are send and no view, only those properties in keys are returned.

        For which properties are available see

            galaxy/managers/histories/HistorySerializer

        The list returned can be filtered by using two optional parameters:

            :q:

                string, generally a property name to filter by followed
                by an (often optional) hyphen and operator string.

            :qv:

                string, the value to filter by

        ..example::

            To filter the list to only those created after 2015-01-29,
            the query string would look like:

                '?q=create_time-gt&qv=2015-01-29'

            Multiple filters can be sent in using multiple q/qv pairs:

                '?q=create_time-gt&qv=2015-01-29&q=tag-has&qv=experiment-1'

        The list returned can be paginated using two optional parameters:

            limit:  integer, defaults to no value and no limit (return all)
                    how many items to return
            offset: integer, defaults to 0 and starts at the beginning
                    skip the first ( offset - 1 ) items and begin returning
                    at the Nth item

        ..example:

            limit and offset can be combined. Skip the first two and return five:
                '?limit=5&offset=3'

        The list returned can be ordered using the optional parameter:

            order:  string containing one of the valid ordering attributes followed
                    (optionally) by '-asc' or '-dsc' for ascending and descending
                    order respectively. Orders can be stacked as a comma-
                    separated list of values.

        ..example:
            To sort by name descending then create time descending:
                '?order=name-dsc,create_time'

        The ordering attributes and their default orders are:

            create_time defaults to 'create_time-dsc'
            update_time defaults to 'update_time-dsc'
            name    defaults to 'name-asc'

        'order' defaults to 'create_time-dsc'
        """
        deleted_only = util.string_as_bool(deleted)
        all_histories = util.string_as_bool(kwd.get('all', False))
        serialization_params = parse_serialization_params(**kwd)
        filter_parameters = HistoryFilterQueryParams(**kwd)
        return self.service.index(trans, serialization_params, filter_parameters, deleted_only, all_histories)

    @expose_api_anonymous
    def show(self, trans, id, deleted='False', **kwd):
        """
        show( trans, id, deleted='False' )
        * GET /api/histories/{id}:
            return the history with ``id``
        * GET /api/histories/deleted/{id}:
            return the deleted history with ``id``
        * GET /api/histories/most_recently_used:
            return the most recently used history

        :type   id:      an encoded id string
        :param  id:      the encoded id of the history to query or the string 'most_recently_used'
        :type   deleted: boolean
        :param  deleted: if True, allow information on a deleted history to be shown.

        :param  keys: same as the use of `keys` in the `index` function above
        :param  view: same as the use of `view` in the `index` function above

        :rtype:     dictionary
        :returns:   detailed history information
        """
        history_id = id
        if history_id == "most_recently_used":
            history_id = None  # Will default to the most recently used
        serialization_params = parse_serialization_params(**kwd)
        return self.service.show(trans, serialization_params, history_id)

    @expose_api_anonymous
    def citations(self, trans, history_id, **kwd):
        """
        GET /api/histories/{id}/citations
        Return all the citations for the tools used to produce the datasets in
        the history.
        """
        return self.service.citations(trans, history_id)

    @expose_api_anonymous_and_sessionless
    def published(self, trans, **kwd):
        """
        GET /api/histories/published

        return all histories that are published

        :rtype:     list
        :returns:   list of dictionaries containing summary history information

        Follows the same filtering logic as the index() method above.
        """
        serialization_params = parse_serialization_params(**kwd)
        filter_parameters = HistoryFilterQueryParams(**kwd)
        return self.service.published(trans, serialization_params, filter_parameters)

    @expose_api
    def shared_with_me(self, trans, **kwd):
        """
        shared_with_me( self, trans, **kwd )
        * GET /api/histories/shared_with_me:
            return all histories that are shared with the current user

        :rtype:     list
        :returns:   list of dictionaries containing summary history information

        Follows the same filtering logic as the index() method above.
        """
        serialization_params = parse_serialization_params(**kwd)
        filter_parameters = HistoryFilterQueryParams(**kwd)
        return self.service.shared_with_me(trans, serialization_params, filter_parameters)

    @expose_api_anonymous
    def create(self, trans, payload, **kwd):
        """
        create( trans, payload )
        * POST /api/histories:
            create a new history

        :type   payload: dict
        :param  payload: (optional) dictionary structure containing:
            * name:             the new history's name
            * history_id:       the id of the history to copy
            * all_datasets:     copy deleted hdas/hdcas? 'True' or 'False', defaults to True
            * archive_source:   the url that will generate the archive to import
            * archive_type:     'url' (default)

        :param  keys: same as the use of `keys` in the `index` function above
        :param  view: same as the use of `view` in the `index` function above

        :rtype:     dict
        :returns:   element view of new history
        """
        create_payload = CreateHistoryPayload(**payload)
        serialization_params = parse_serialization_params(**kwd)
        return self.service.create(trans, create_payload, serialization_params)

    @expose_api
    def delete(self, trans, id, **kwd):
        """
        DELETE /api/histories/{id}

        delete the history with the given ``id``

        .. note:: Stops all active jobs in the history if purge is set.

        :type   id:     str
        :param  id:     the encoded id of the history to delete
        :type   kwd:    dict
        :param  kwd:    (optional) dictionary structure containing extra parameters

        You can purge a history, removing all it's datasets from disk (if unshared),
        by passing in ``purge=True`` in the url.

        :param  keys: same as the use of `keys` in the `index` function above
        :param  view: same as the use of `view` in the `index` function above

        :rtype:     dict
        :returns:   the deleted or purged history
        """
        history_id = id
        # a request body is optional here
        purge = string_as_bool(kwd.get('purge', False))
        # for backwards compat, keep the payload sub-dictionary
        if kwd.get('payload', None):
            purge = string_as_bool(kwd['payload'].get('purge', purge))

        serialization_params = parse_serialization_params(**kwd)
        return self.service.delete(trans, history_id, serialization_params, purge)

    @expose_api
    def undelete(self, trans, id, **kwd):
        """
        undelete( self, trans, id, **kwd )
        * POST /api/histories/deleted/{id}/undelete:
            undelete history (that hasn't been purged) with the given ``id``

        :type   id:     str
        :param  id:     the encoded id of the history to undelete

        :param  keys: same as the use of `keys` in the `index` function above
        :param  view: same as the use of `view` in the `index` function above

        :rtype:     str
        :returns:   'OK' if the history was undeleted
        """
        serialization_params = parse_serialization_params(**kwd)
        return self.service.undelete(trans, id, serialization_params)

    @expose_api
    def update(self, trans, id, payload, **kwd):
        """
        update( self, trans, id, payload, **kwd )
        * PUT /api/histories/{id}
            updates the values for the history with the given ``id``

        :type   id:      str
        :param  id:      the encoded id of the history to update
        :type   payload: dict
        :param  payload: a dictionary containing any or all the
            fields in :func:`galaxy.model.History.to_dict` and/or the following:

            * annotation: an annotation for the history

        :param  keys: same as the use of `keys` in the `index` function above
        :param  view: same as the use of `view` in the `index` function above

        :rtype:     dict
        :returns:   an error object if an error occurred or a dictionary containing
            any values that were different from the original and, therefore, updated
        """
        # TODO: PUT /api/histories/{encoded_history_id} payload = { rating: rating } (w/ no security checks)
        serialization_params = parse_serialization_params(**kwd)
        return self.service.update(trans, id, payload, serialization_params)

    @expose_api
    def index_exports(self, trans, id):
        """
        GET /api/histories/{id}/exports

        Get previous history exports (to links). Effectively returns serialized
        JEHA objects.
        """
        return self.service.index_exports(trans, id)

    @expose_api
    def archive_export(self, trans, id, payload=None, **kwds):
        """
        PUT /api/histories/{id}/exports

        start job (if needed) to create history export for corresponding
        history.

        :type   id:     str
        :param  id:     the encoded id of the history to export

        :rtype:     dict
        :returns:   object containing url to fetch export from.
        """
        # PUT instead of POST because multiple requests should just result
        # in one object being created.
        payload = payload or {}
        payload.update(kwds or {})
        export_payload = ExportHistoryArchivePayload(**payload)
        return self.service.archive_export(trans, id, export_payload)

    @expose_api_raw
    def archive_download(self, trans, id, jeha_id, **kwds):
        """
        GET /api/histories/{id}/exports/{jeha_id}

        If ready and available, return raw contents of exported history.
        Use/poll ``PUT /api/histories/{id}/exports`` to initiate the creation
        of such an export - when ready that route will return 200 status
        code (instead of 202) with a JSON dictionary containing a
        ``download_url``.
        """
        return self.service.archive_download(trans, id, jeha_id)

    @expose_api
    def get_custom_builds_metadata(self, trans, id, payload=None, **kwd):
        """
        GET /api/histories/{id}/custom_builds_metadata
        Returns meta data for custom builds.

        :param id: the encoded history id
        :type  id: str
        """
        return self.service.get_custom_builds_metadata(trans, id)

    @expose_api
    def sharing(self, trans, id, **kwd):
        """
        * GET /api/histories/{id}/sharing
        """
        return self.service.shareable_service.sharing(trans, id)

    @expose_api
    def enable_link_access(self, trans, id, **kwd):
        """
        * PUT /api/histories/{id}/enable_link_access
        """
        return self.service.shareable_service.enable_link_access(trans, id)

    @expose_api
    def disable_link_access(self, trans, id, **kwd):
        """
        * PUT /api/histories/{id}/disable_link_access
        """
        return self.service.shareable_service.disable_link_access(trans, id)

    @expose_api
    def publish(self, trans, id, **kwd):
        """
        * PUT /api/histories/{id}/publish
        """
        return self.service.shareable_service.publish(trans, id)

    @expose_api
    def unpublish(self, trans, id, **kwd):
        """
        * PUT /api/histories/{id}/unpublish
        """
        return self.service.shareable_service.unpublish(trans, id)

    @expose_api
    def share(self, trans, id, payload, **kwd):
        """
        * PUT /api/histories/{id}/share
        """
        payload = sharable.UserIdsPayload(**payload)
        return self.service.shareable_service.share_with(trans, id, payload)

    @expose_api
    def unshare(self, trans, id, payload, **kwd):
        """
        * PUT /api/histories/{id}/unshare
        """
        payload = sharable.UserIdsPayload(**payload)
        return self.service.shareable_service.unshare_with(trans, id, payload)

    @expose_api
    def set_slug(self, trans, id, payload, **kwd):
        """
        * PUT /api/histories/{id}/slug
        """
        payload = sharable.SetSlugPayload(**payload)
        self.service.shareable_service.set_slug(trans, id, payload)
