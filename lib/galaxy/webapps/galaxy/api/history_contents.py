"""
API operations on the contents of a history.
"""
import logging
from typing import (
    Any,
    Dict,
)

import dateutil.parser

from galaxy import (
    util
)
from galaxy.managers import (
    hdas,
    hdcas,
    histories,
    history_contents
)
from galaxy.schema.schema import (
    DatasetPermissionAction,
    HistoryContentType,
    UpdateDatasetPermissionsPayload,
    UpdateHistoryContentsBatchPayload,
)
from galaxy.web import (
    expose_api,
    expose_api_anonymous,
    expose_api_raw,
    expose_api_raw_anonymous
)
from galaxy.webapps.base.controller import (
    UsesLibraryMixinItems,
    UsesTagsMixin
)
from galaxy.webapps.galaxy.api.common import parse_serialization_params
from galaxy.webapps.galaxy.services.history_contents import (
    CreateHistoryContentPayload,
    HistoriesContentsService,
    HistoryContentsFilterList,
    HistoryContentsFilterQueryParams,
    HistoryContentsIndexLegacyParams
)
from . import BaseGalaxyAPIController, depends

log = logging.getLogger(__name__)


class HistoryContentsController(BaseGalaxyAPIController, UsesLibraryMixinItems, UsesTagsMixin):
    hda_manager: hdas.HDAManager = depends(hdas.HDAManager)
    history_manager: histories.HistoryManager = depends(histories.HistoryManager)
    history_contents_manager: history_contents.HistoryContentsManager = depends(history_contents.HistoryContentsManager)
    hda_serializer: hdas.HDASerializer = depends(hdas.HDASerializer)
    hdca_serializer: hdcas.HDCASerializer = depends(hdcas.HDCASerializer)
    history_contents_filters: history_contents.HistoryContentsFilters = depends(history_contents.HistoryContentsFilters)

    service: HistoriesContentsService = depends(HistoriesContentsService)

    @expose_api_anonymous
    def index(self, trans, history_id, **kwd):
        """
        GET /api/histories/{history_id}/contents

        return a list of HDA data for the history with the given ``id``

        .. note:: Anonymous users are allowed to get their current history contents

        If Ids is not given, index returns a list of *summary* objects for
        every HDA associated with the given `history_id`.

        If ids is given, index returns a *more complete* json object for each
        HDA in the ids list.

        :type   history_id: str
        :param  history_id: encoded id string of the HDA's History
        :type   ids:        str
        :param  ids:        (optional) a comma separated list of encoded `HDA` ids
        :param  types:      (optional) kinds of contents to index (currently just
                            dataset, but dataset_collection will be added shortly).
        :type   types:      str

        :rtype:     list
        :returns:   dictionaries containing summary or detailed HDA information
        """
        legacy_params = HistoryContentsIndexLegacyParams(**kwd)
        serialization_params = parse_serialization_params(**kwd)
        filter_parameters = HistoryContentsFilterQueryParams(**kwd)
        return self.service.index(
            trans, history_id,
            legacy_params,
            serialization_params, filter_parameters
        )

    @expose_api_anonymous
    def show(self, trans, id, history_id, **kwd):
        """
        GET /api/histories/{history_id}/contents/{id}
        GET /api/histories/{history_id}/contents/{type}/{id}

        return detailed information about an HDA or HDCA within a history

        .. note:: Anonymous users are allowed to get their current history contents

        :type   id:         str
        :param  id:         the encoded id of the HDA or HDCA to return
        :type   type:       str
        :param  id:         'dataset' or 'dataset_collection'
        :type   history_id: str
        :param  history_id: encoded id string of the HDA's or HDCA's History
        :type   view:       str
        :param  view:       if fetching a dataset collection - the view style of
                            the dataset collection to produce.
                            'collection' returns no element information, 'element'
                            returns detailed element information for all datasets,
                            'element-reference' returns a minimal set of information
                            about datasets (for instance id, type, and state but not
                            metadata, peek, info, or name). The default is 'element'.
        :type  fuzzy_count: int
        :param fuzzy_count: this value can be used to broadly restrict the magnitude
                            of the number of elements returned via the API for large
                            collections. The number of actual elements returned may
                            be "a bit" more than this number or "a lot" less - varying
                            on the depth of nesting, balance of nesting at each level,
                            and size of target collection. The consumer of this API should
                            not expect a stable number or pre-calculable number of
                            elements to be produced given this parameter - the only
                            promise is that this API will not respond with an order
                            of magnitude more elements estimated with this value.
                            The UI uses this parameter to fetch a "balanced" concept of
                            the "start" of large collections at every depth of the
                            collection.

        :rtype:     dict
        :returns:   dictionary containing detailed HDA or HDCA information
        """
        serialization_params = parse_serialization_params(**kwd)
        contents_type = self.__get_contents_type(kwd)
        fuzzy_count = kwd.get("fuzzy_count", None)
        if fuzzy_count:
            fuzzy_count = int(fuzzy_count)
        return self.service.show(trans, id, serialization_params, contents_type, fuzzy_count)

    @expose_api_anonymous
    def index_jobs_summary(self, trans, history_id, **kwd):
        """
        * GET /api/histories/{history_id}/jobs_summary
            return job state summary info for jobs, implicit groups jobs for collections or workflow invocations

        Warning: We allow anyone to fetch job state information about any object they
        can guess an encoded ID for - it isn't considered protected data. This keeps
        polling IDs as part of state calculation for large histories and collections as
        efficient as possible.

        :type   history_id: str
        :param  history_id: encoded id string of the target history
        :type   ids:        str[]
        :param  ids:        the encoded ids of job summary objects to return - if ids
                            is specified types must also be specified and have same length.
        :type   types:      str[]
        :param  types:      type of object represented by elements in the ids array - any of
                            Job, ImplicitCollectionJob, or WorkflowInvocation.

        :rtype:     dict[]
        :returns:   an array of job summary object dictionaries.
        """
        ids = util.listify(kwd.get("ids", None))
        types = util.listify(kwd.get("types", None))
        return self.service.index_jobs_summary(trans, ids, types)

    @expose_api_anonymous
    def show_jobs_summary(self, trans, id, history_id, **kwd):
        """
        * GET /api/histories/{history_id}/contents/{type}/{id}/jobs_summary
            return detailed information about an HDA or HDCAs jobs

        Warning: We allow anyone to fetch job state information about any object they
        can guess an encoded ID for - it isn't considered protected data. This keeps
        polling IDs as part of state calculation for large histories and collections as
        efficient as possible.

        :type   id:         str
        :param  id:         the encoded id of the HDA to return
        :type   history_id: str
        :param  history_id: encoded id string of the HDA's or the HDCA's History

        :rtype:     dict
        :returns:   dictionary containing jobs summary object
        """
        contents_type = self.__get_contents_type(kwd)
        return self.service.show_jobs_summary(trans, id, contents_type)

    def __get_contents_type(self, kwd: dict) -> HistoryContentType:
        contents_type = kwd.get('type', 'dataset')
        return HistoryContentType(contents_type)

    @expose_api_raw_anonymous
    def download_dataset_collection(self, trans, id, history_id=None, **kwd):
        """
        GET /api/histories/{history_id}/contents/dataset_collections/{id}/download
        GET /api/dataset_collection/{id}/download

        Download the content of a HistoryDatasetCollection as a tgz archive
        while maintaining approximate collection structure.

        :param id: encoded HistoryDatasetCollectionAssociation (HDCA) id
        :param history_id: encoded id string of the HDCA's History
        """
        return self.service.download_dataset_collection(trans, id)

    @expose_api_anonymous
    def create(self, trans, history_id, payload, **kwd):
        """
        POST /api/histories/{history_id}/contents/{type}s
        POST /api/histories/{history_id}/contents

        create a new HDA or HDCA

        :type   history_id: str
        :param  history_id: encoded id string of the new HDA's History
        :type   type: str
        :param  type: Type of history content - 'dataset' (default) or
                      'dataset_collection'. This can be passed in via payload
                      or parsed from the route.
        :type   payload:    dict
        :param  payload:    dictionary structure containing:

            copy from library (for type 'dataset'):
            'source'    = 'library'
            'content'   = [the encoded id from the library dataset]

            copy from library folder
            'source'    = 'library_folder'
            'content'   = [the encoded id from the library folder]

            copy from history dataset (for type 'dataset'):
            'source'    = 'hda'
            'content'   = [the encoded id from the HDA]

            copy from history dataset collection (for type 'dataset_collection')
            'source'    = 'hdca'
            'content'   = [the encoded id from the HDCA]
            'copy_elements'

                Copy child HDAs into the target history as well,
                defaults to False but this is less than ideal and may
                be changed in future releases.

            create new history dataset collection (for type 'dataset_collection')

            'source'
                'new_collection' (default 'source' if type is
                'dataset_collection' - no need to specify this)

            'collection_type'

                For example, "list", "paired", "list:paired".

            'copy_elements'

                Copy child HDAs when creating new collection,
                defaults to False in the API but is set to True in the UI,
                so that we can modify HDAs with tags when creating collections.

            'name'

                Name of new dataset collection.

            'element_identifiers'

                Recursive list structure defining collection.
                Each element must have 'src' which can be
                'hda', 'ldda', 'hdca', or 'new_collection',
                as well as a 'name' which is the name of
                element (e.g. "forward" or "reverse" for
                paired datasets, or arbitrary sample names
                for instance for lists). For all src's except
                'new_collection' - a encoded 'id' attribute
                must be included wiht element as well.
                'new_collection' sources must defined a
                'collection_type' and their own list of
                (potentially) nested 'element_identifiers'.

        ..note:
            Currently, a user can only copy an HDA from a history that the user owns.

        :rtype:     dict
        :returns:   dictionary containing detailed information for the new HDA

        """
        serialization_params = parse_serialization_params(**kwd)
        create_payload = CreateHistoryContentPayload(**payload)
        create_payload.type = kwd.get("type") or create_payload.type
        return self.service.create(trans, history_id, create_payload, serialization_params)

    @expose_api
    def show_roles(self, trans, encoded_dataset_id, **kwd):
        """
        Display information about current or available roles for a given dataset permission.

        * GET /api/histories/{history_id}/contents/datasets/{encoded_dataset_id}/permissions

        :param  encoded_dataset_id:      the encoded id of the dataset to query
        :type   encoded_dataset_id:      an encoded id string

        :returns:   either dict of current roles for all permission types
                    or dict of available roles to choose from (is the same for any permission type)
        :rtype:     dictionary

        :raises: InsufficientPermissionsException
        """
        raise NotImplementedError()  # TODO: This endpoint doesn't seem to be in use, remove?
        # hda = self.hda_manager.get_owned(self.decode_id(encoded_dataset_id), trans.user, current_history=trans.history, trans=trans)
        # return self.hda_manager.serialize_dataset_association_roles(trans, hda)

    @expose_api
    def update_permissions(self, trans, history_id, history_content_id, payload: Dict[str, Any] = None, **kwd):
        """
        Set permissions of the given library dataset to the given role ids.

        PUT /api/histories/{history_id}/contents/datasets/{encoded_dataset_id}/permissions

        :param  encoded_dataset_id:      the encoded id of the dataset to update permissions of
        :type   encoded_dataset_id:      an encoded id string
        :param   payload: dictionary structure containing:

            :param  action:     (required) describes what action should be performed
                                available actions: make_private, remove_restrictions, set_permissions
            :type   action:     string
            :param  access_ids[]:      list of Role.id defining roles that should have access permission on the dataset
            :type   access_ids[]:      string or list
            :param  manage_ids[]:      list of Role.id defining roles that should have manage permission on the dataset
            :type   manage_ids[]:      string or list
            :param  modify_ids[]:      list of Role.id defining roles that should have modify permission on the library dataset item
            :type   modify_ids[]:      string or list

        :type:      dictionary

        :returns:   dict of current roles for all available permission types
        :rtype:     dictionary

        :raises: RequestParameterInvalidException, ObjectNotFound, InsufficientPermissionsException, InternalServerError
                    RequestParameterMissingException
        """
        if payload:
            kwd.update(payload)
        update_payload = self._get_update_permission_payload(kwd)
        return self.service.update_permissions(trans, history_content_id, update_payload)

    def _get_update_permission_payload(self, payload: Dict[str, Any]) -> UpdateDatasetPermissionsPayload:
        """Coverts the payload dictionary into a UpdateDatasetPermissionsPayload model with custom parsing.

        This is an attempt on supporting multiple aliases for the permissions params."""
        # There are several allowed names for the same role list parameter, i.e.: `access`, `access_ids`, `access_ids[]`
        # The `access_ids[]` name is not pydantic friendly, so this will be modelled as an alias but we can only set one alias
        # TODO: Maybe we should choose only one way and deprecate the others?
        payload["access_ids[]"] = payload.get("access_ids[]") or payload.get("access")
        payload["manage_ids[]"] = payload.get("manage_ids[]") or payload.get("manage")
        payload["modify_ids[]"] = payload.get("modify_ids[]") or payload.get("modify")
        # The action is required, so the default will be used if none is specified
        payload["action"] = payload.get("action", DatasetPermissionAction.set_permissions)
        update_payload = UpdateDatasetPermissionsPayload(**payload)
        return update_payload

    @expose_api_anonymous
    def update_batch(self, trans, history_id, payload, **kwd):
        """
        PUT /api/histories/{history_id}/contents

        :type   history_id: str
        :param  history_id: encoded id string of the history containing supplied items
        :type   id:         str
        :param  id:         the encoded id of the history to update
        :type   payload:    dict
        :param  payload:    a dictionary containing any or all the

        :rtype:     dict
        :returns:   an error object if an error occurred or a dictionary containing
                    any values that were different from the original and, therefore, updated
        """
        serialization_params = parse_serialization_params(**kwd)
        update_payload = UpdateHistoryContentsBatchPayload.parse_obj(payload)
        return self.service.update_batch(trans, history_id, update_payload, serialization_params)

    @expose_api_anonymous
    def update(self, trans, history_id, id, payload, **kwd):
        """
        update( self, trans, history_id, id, payload, **kwd )
        * PUT /api/histories/{history_id}/contents/{id}
            updates the values for the history content item with the given ``id``

        :type   history_id: str
        :param  history_id: encoded id string of the items's History
        :type   id:         str
        :param  id:         the encoded id of the history item to update
        :type   payload:    dict
        :param  payload:    a dictionary containing any or all the
            fields in :func:`galaxy.model.HistoryDatasetAssociation.to_dict`
            and/or the following:

            * annotation: an annotation for the HDA

        :rtype:     dict
        :returns:   an error object if an error occurred or a dictionary containing
            any values that were different from the original and, therefore, updated
        """
        serialization_params = parse_serialization_params(**kwd)
        contents_type = self.__get_contents_type(kwd)
        return self.service.update(
            trans, history_id, id, payload, serialization_params, contents_type
        )

    @expose_api_anonymous
    def validate(self, trans, history_id, history_content_id, payload=None, **kwd):
        """
        PUT /api/histories/{history_id}/contents/{id}/validate

        updates the values for the history content item with the given ``id``

        :type   history_id: str
        :param  history_id: encoded id string of the items's History
        :type   id:         str
        :param  id:         the encoded id of the history item to validate

        :rtype:     dict
        :returns:   TODO
        """
        return self.service.validate(trans, history_id, history_content_id)

    @expose_api_anonymous
    def delete(self, trans, history_id, id, purge=False, recursive=False, **kwd):
        """
        DELETE /api/histories/{history_id}/contents/{id}
        DELETE /api/histories/{history_id}/contents/{type}s/{id}

        delete the history content with the given ``id`` and specified type (defaults to dataset)

        .. note:: Currently does not stop any active jobs for which this dataset is an output.

        :type   id:     str
        :param  id:     the encoded id of the history to delete
        :type   recursive:  bool
        :param  recursive:  if True, and deleted an HDCA also delete containing HDAs
        :type   purge:  bool
        :param  purge:  if True, purge the target HDA or child HDAs of the target HDCA
        :type   kwd:    dict
        :param  kwd:    (optional) dictionary structure containing:

            * payload:     a dictionary itself containing:
                * purge:   if True, purge the HDA
                * recursive: if True, see above.

        .. note:: that payload optionally can be placed in the query string of the request.
            This allows clients that strip the request body to still purge the dataset.

        :rtype:     dict
        :returns:   an error object if an error occurred or a dictionary containing:
            * id:         the encoded id of the history,
            * deleted:    if the history content was marked as deleted,
            * purged:     if the history content was purged
        """
        serialization_params = parse_serialization_params(**kwd)
        contents_type = self.__get_contents_type(kwd)
        purge = util.string_as_bool(purge)
        recursive = util.string_as_bool(recursive)
        if kwd.get('payload', None):
            # payload takes priority
            purge = util.string_as_bool(kwd['payload'].get('purge', purge))
            recursive = util.string_as_bool(kwd['payload'].get('recursive', recursive))
        return self.service.delete(trans, id, serialization_params, contents_type, purge, recursive)

    @expose_api_raw
    def archive(self, trans, history_id, filename='', format='zip', dry_run=True, **kwd):
        """
        archive( self, trans, history_id, filename='', format='zip', dry_run=True, **kwd )
        * GET /api/histories/{history_id}/contents/archive/{id}
        * GET /api/histories/{history_id}/contents/archive/{filename}.{format}
            build and return a compressed archive of the selected history contents

        :type   filename:  string
        :param  filename:  (optional) archive name (defaults to history name)
        :type   dry_run:   boolean
        :param  dry_run:   (optional) if True, return the archive and file paths only
                           as json and not an archive file

        :returns:   archive file for download

        .. note:: this is a volatile endpoint and settings and behavior may change.
        """
        dry_run = util.string_as_bool(dry_run)
        filter_parameters = HistoryContentsFilterQueryParams(**kwd)
        return self.service.archive(trans, history_id, filter_parameters, filename, dry_run)

    @expose_api_raw_anonymous
    def contents_near(self, trans, history_id, direction, hid, limit, **kwd):
        """
        Returns the following data:

        a) item counts:
        - total matches-up:   hid < {hid}
        - total matches-down: hid > {hid}
        - total matches:      total matches-up + total matches-down + 1 (+1 for hid == {hid})
        - displayed matches-up:   hid <= {hid} (hid == {hid} is included)
        - displayed matches-down: hid > {hid}
        - displayed matches:      displayed matches-up + displayed matches-down

        b) {limit} history items:
        - if direction == before: hid <= {hid}
        - if direction == after:  hid > {hid}
        - if direction == near:   "near" {hid}, so that |before| <= limit // 2, |after| <= limit // 2 + 1.

        Intended purpose: supports scroller functionality.

        GET /api/histories/{history_id}/contents/{direction:near|before|after}/{hid}/{limit}
        """
        serialization_params = parse_serialization_params(default_view='betawebclient', **kwd)

        since_str = kwd.pop('since', None)
        if since_str:
            since = dateutil.parser.isoparse(since_str)
        else:
            since = None

        filter_params = self._parse_rest_params(kwd)
        hid = int(hid)
        limit = int(limit)

        return self.service.contents_near(
            trans, history_id, serialization_params, filter_params, direction, hid, limit, since,
        )

    # Parsing query string according to REST standards.
    def _parse_rest_params(self, qdict: Dict[str, Any]) -> HistoryContentsFilterList:
        DEFAULT_OP = 'eq'
        splitchar = '-'

        result = []
        for key, val in qdict.items():
            attr = key
            op = DEFAULT_OP
            if splitchar in key:
                attr, op = key.rsplit(splitchar, 1)
            result.append([attr, op, val])

        return result
