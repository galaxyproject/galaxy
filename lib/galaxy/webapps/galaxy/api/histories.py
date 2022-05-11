"""
API operations on a history.

.. seealso:: :class:`galaxy.model.History`
"""
import glob
import logging
import os

from sqlalchemy import (
    false,
    true
)

from galaxy import (
    exceptions,
    model,
    util
)
from galaxy.managers import (
    citations,
    histories,
    sharable,
    users,
    workflows,
)
from galaxy.util import (
    restore_text,
    string_as_bool
)
from galaxy.web import (
    expose_api,
    expose_api_anonymous,
    expose_api_anonymous_and_sessionless,
    expose_api_raw,
)
from galaxy.webapps.base.controller import (
    ExportsHistoryMixin,
    ImportsHistoryMixin,
)
from . import BaseGalaxyAPIController, depends

log = logging.getLogger(__name__)


class HistoriesController(BaseGalaxyAPIController, ExportsHistoryMixin, ImportsHistoryMixin):
    citations_manager: citations.CitationsManager = depends(citations.CitationsManager)
    user_manager: users.UserManager = depends(users.UserManager)
    workflow_manager: workflows.WorkflowsManager = depends(workflows.WorkflowsManager)
    manager: histories.HistoryManager = depends(histories.HistoryManager)
    history_export_view: histories.HistoryExportView = depends(histories.HistoryExportView)
    serializer: histories.HistorySerializer = depends(histories.HistorySerializer)
    deserializer: histories.HistoryDeserializer = depends(histories.HistoryDeserializer)
    filters: histories.HistoryFilters = depends(histories.HistoryFilters)
    # TODO move all managers above and the actions logic to the HistoriesService
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
        serialization_params = self._parse_serialization_params(kwd, 'summary')
        limit, offset = self.parse_limit_offset(kwd)
        filter_params = self.parse_filter_params(kwd)

        # bail early with current history if user is anonymous
        current_user = self.user_manager.current_user(trans)
        if self.user_manager.is_anonymous(current_user):
            current_history = self.manager.get_current(trans)
            if not current_history:
                return []
            # note: ignores filters, limit, offset
            return [self.serializer.serialize_to_view(current_history,
                     user=current_user, trans=trans, **serialization_params)]

        filters = []
        # support the old default of not-returning/filtering-out deleted histories
        filters += self._get_deleted_filter(deleted, filter_params)
        # get optional parameter 'all'
        all_histories = util.string_as_bool(kwd.get('all', False))
        # if parameter 'all' is true, throw exception if not admin
        # else add current user filter to query (default behaviour)
        if all_histories:
            if not trans.user_is_admin:
                message = "Only admins can query all histories"
                raise exceptions.AdminRequiredException(message)
        else:
            filters += [self.app.model.History.user == current_user]
        # and any sent in from the query string
        filters += self.filters.parse_filters(filter_params)

        order_by = self._parse_order_by(manager=self.manager, order_by_string=kwd.get('order', 'create_time-dsc'))
        histories = self.manager.list(filters=filters, order_by=order_by, limit=limit, offset=offset)

        rval = []
        for history in histories:
            history_dict = self.serializer.serialize_to_view(history, user=trans.user, trans=trans, **serialization_params)
            rval.append(history_dict)
        return rval

    def _get_deleted_filter(self, deleted, filter_params):
        # TODO: this should all be removed (along with the default) in v2
        # support the old default of not-returning/filtering-out deleted histories
        try:
            # the consumer must explicitly ask for both deleted and non-deleted
            #   but pull it from the parsed params (as the filter system will error on None)
            deleted_filter_index = filter_params.index(('deleted', 'eq', 'None'))
            filter_params.pop(deleted_filter_index)
            return []
        except ValueError:
            pass

        # the deleted string bool was also used as an 'include deleted' flag
        if deleted in ('True', 'true'):
            return [self.app.model.History.deleted == true()]

        # the third option not handled here is 'return only deleted'
        #   if this is passed in (in the form below), simply return and let the filter system handle it
        if ('deleted', 'eq', 'True') in filter_params:
            return []

        # otherwise, do the default filter of removing the deleted histories
        return [self.app.model.History.deleted == false()]

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
        deleted = string_as_bool(deleted)

        if history_id == "most_recently_used":
            history = self.manager.most_recent(trans.user,
                filters=(self.app.model.History.deleted == false()), current_history=trans.history)
        else:
            history = self.manager.get_accessible(self.decode_id(history_id), trans.user, current_history=trans.history)

        return self.serializer.serialize_to_view(history,
            user=trans.user, trans=trans, **self._parse_serialization_params(kwd, 'detailed'))

    @expose_api_anonymous
    def citations(self, trans, history_id, **kwd):
        """
        GET /api/histories/{id}/citations
        Return all the citations for the tools used to produce the datasets in
        the history.
        """
        history = self.manager.get_accessible(self.decode_id(history_id), trans.user, current_history=trans.history)
        tool_ids = set()
        for dataset in history.datasets:
            job = dataset.creating_job
            if not job:
                continue
            tool_id = job.tool_id
            if not tool_id:
                continue
            tool_ids.add(tool_id)
        return [citation.to_dict("bibtex") for citation in self.citations_manager.citations_for_tool_ids(tool_ids)]

    @expose_api_anonymous_and_sessionless
    def published(self, trans, **kwd):
        """
        GET /api/histories/published

        return all histories that are published

        :rtype:     list
        :returns:   list of dictionaries containing summary history information

        Follows the same filtering logic as the index() method above.
        """
        limit, offset = self.parse_limit_offset(kwd)
        filter_params = self.parse_filter_params(kwd)
        filters = self.filters.parse_filters(filter_params)
        order_by = self._parse_order_by(manager=self.manager, order_by_string=kwd.get('order', 'create_time-dsc'))
        histories = self.manager.list_published(filters=filters, order_by=order_by, limit=limit, offset=offset)
        rval = []
        for history in histories:
            history_dict = self.serializer.serialize_to_view(history, user=trans.user, trans=trans,
                **self._parse_serialization_params(kwd, 'summary'))
            rval.append(history_dict)
        return rval

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
        current_user = trans.user
        limit, offset = self.parse_limit_offset(kwd)
        filter_params = self.parse_filter_params(kwd)
        filters = self.filters.parse_filters(filter_params)
        order_by = self._parse_order_by(manager=self.manager, order_by_string=kwd.get('order', 'create_time-dsc'))
        histories = self.manager.list_shared_with(current_user,
            filters=filters, order_by=order_by, limit=limit, offset=offset)
        rval = []
        for history in histories:
            history_dict = self.serializer.serialize_to_view(history, user=current_user, trans=trans,
                **self._parse_serialization_params(kwd, 'summary'))
            rval.append(history_dict)
        return rval

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
        if trans.user and trans.user.bootstrap_admin_user:
            raise exceptions.RealUserRequiredException("Only real users can create histories.")
        hist_name = None
        if payload.get('name', None):
            hist_name = restore_text(payload['name'])
        copy_this_history_id = payload.get('history_id', None)

        all_datasets = util.string_as_bool(payload.get('all_datasets', True))

        if "archive_source" in payload:
            archive_source = payload["archive_source"]
            archive_file = payload.get("archive_file")
            if archive_source:
                archive_type = payload.get("archive_type", "url")
            elif hasattr(archive_file, "file"):
                archive_source = payload["archive_file"].file.name
                archive_type = "file"
            else:
                raise exceptions.MessageException("Please provide a url or file.")
            job = self.queue_history_import(trans, archive_type=archive_type, archive_source=archive_source)
            job_dict = job.to_dict()
            job_dict["message"] = "Importing history from source '%s'. This history will be visible when the import is complete." % archive_source
            return trans.security.encode_all_ids(job_dict)

        new_history = None
        # if a history id was passed, copy that history
        if copy_this_history_id:
            decoded_id = self.decode_id(copy_this_history_id)
            original_history = self.manager.get_accessible(decoded_id, trans.user, current_history=trans.history)
            hist_name = hist_name or ("Copy of '%s'" % original_history.name)
            new_history = original_history.copy(name=hist_name, target_user=trans.user, all_datasets=all_datasets)

        # otherwise, create a new empty history
        else:
            new_history = self.manager.create(user=trans.user, name=hist_name)

        trans.app.security_agent.history_set_default_permissions(new_history)
        trans.sa_session.add(new_history)
        trans.sa_session.flush()

        # an anonymous user can only have one history
        if self.user_manager.is_anonymous(trans.user):
            self.manager.set_current(trans, new_history)

        return self.serializer.serialize_to_view(new_history,
            user=trans.user, trans=trans, **self._parse_serialization_params(kwd, 'detailed'))

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

        history = self.manager.get_owned(self.decode_id(history_id), trans.user, current_history=trans.history)
        if purge:
            self.manager.purge(history)
        else:
            self.manager.delete(history)

        return self.serializer.serialize_to_view(history,
            user=trans.user, trans=trans, **self._parse_serialization_params(kwd, 'detailed'))

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
        # TODO: remove at v2
        history_id = id
        history = self.manager.get_owned(self.decode_id(history_id), trans.user, current_history=trans.history)
        self.manager.undelete(history)

        return self.serializer.serialize_to_view(history,
            user=trans.user, trans=trans, **self._parse_serialization_params(kwd, 'detailed'))

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
        history = self.manager.get_owned(self.decode_id(id), trans.user, current_history=trans.history)

        self.deserializer.deserialize(history, payload, user=trans.user, trans=trans)
        return self.serializer.serialize_to_view(history,
            user=trans.user, trans=trans, **self._parse_serialization_params(kwd, 'detailed'))

    @expose_api
    def index_exports(self, trans, id):
        """
        GET /api/histories/{id}/exports

        Get previous history exports (to links). Effectively returns serialized
        JEHA objects.
        """
        return self.history_export_view.get_exports(trans, id)

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
        kwds.update(payload or {})
        # PUT instead of POST because multiple requests should just result
        # in one object being created.
        history = self.manager.get_accessible(self.decode_id(id), trans.user, current_history=trans.history)
        jeha = history.latest_export
        force = 'force' in kwds  # Hack to force rebuild everytime during dev
        exporting_to_uri = 'directory_uri' in kwds
        # always just issue a new export when exporting to a URI.
        up_to_date = not force and not exporting_to_uri and (jeha and jeha.up_to_date)
        job = None
        if not up_to_date:
            # Need to create new JEHA + job.
            gzip = kwds.get("gzip", True)
            include_hidden = kwds.get("include_hidden", False)
            include_deleted = kwds.get("include_deleted", False)
            directory_uri = kwds.get("directory_uri", None)
            file_name = kwds.get("file_name", None)
            job = self.queue_history_export(
                trans,
                history,
                gzip=gzip,
                include_hidden=include_hidden,
                include_deleted=include_deleted,
                directory_uri=directory_uri,
                file_name=file_name,
            )
        else:
            job = jeha.job

        if exporting_to_uri:
            # we don't have a jeha, there will never be a download_url. Just let
            # the client poll on the created job_id to determine when the file has been
            # written.
            job_id = trans.security.encode_id(job.id)
            return dict(job_id=job_id)

        if up_to_date and jeha.ready:
            return self.history_export_view.serialize(trans, id, jeha)
        else:
            # Valid request, just resource is not ready yet.
            trans.response.status = "202 Accepted"
            if jeha:
                return self.history_export_view.serialize(trans, id, jeha)
            else:
                assert job is not None, "logic error, don't have a jeha or a job"
                job_id = trans.security.encode_id(job.id)
                return dict(job_id=job_id)

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
        jeha = self.history_export_view.get_ready_jeha(trans, id, jeha_id)
        return self.serve_ready_history_export(trans, jeha)

    @expose_api
    def get_custom_builds_metadata(self, trans, id, payload=None, **kwd):
        """
        GET /api/histories/{id}/custom_builds_metadata
        Returns meta data for custom builds.

        :param id: the encoded history id
        :type  id: str
        """
        if payload is None:
            payload = {}
        history = self.manager.get_accessible(self.decode_id(id), trans.user, current_history=trans.history)
        installed_builds = []
        for build in glob.glob(os.path.join(trans.app.config.len_file_path, "*.len")):
            installed_builds.append(os.path.basename(build).split(".len")[0])
        fasta_hdas = trans.sa_session.query(model.HistoryDatasetAssociation) \
            .filter_by(history=history, extension="fasta", deleted=False) \
            .order_by(model.HistoryDatasetAssociation.hid.desc())
        return {
            'installed_builds': [{'label': ins, 'value': ins} for ins in installed_builds],
            'fasta_hdas': [{'label': f'{hda.hid}: {hda.name}', 'value': trans.security.encode_id(hda.id)} for hda in fasta_hdas],
        }

    @expose_api
    def sharing(self, trans, id, payload=None, **kwd):
        """
        * GET/POST /api/pages/{id}/sharing
            View/modify sharing options for the page with the given id.
        """
        if payload:
            payload = sharable.SharingPayload(**payload)
        return self.service.sharing(trans, id, payload)
