"""
API operations on the contents of a history.
"""

from galaxy import exceptions
from galaxy import util

from galaxy.web import _future_expose_api as expose_api
from galaxy.web import _future_expose_api_anonymous as expose_api_anonymous

from galaxy.web.base.controller import BaseAPIController
from galaxy.web.base.controller import UsesLibraryMixin
from galaxy.web.base.controller import UsesLibraryMixinItems
from galaxy.web.base.controller import UsesTagsMixin

from galaxy.managers import histories
from galaxy.managers import hdas
from galaxy.managers import folders
from galaxy.managers.collections_util import api_payload_to_create_params
from galaxy.managers.collections_util import dictify_dataset_collection_instance

import logging
log = logging.getLogger( __name__ )


class HistoryContentsController( BaseAPIController, UsesLibraryMixin, UsesLibraryMixinItems, UsesTagsMixin ):

    def __init__( self, app ):
        super( HistoryContentsController, self ).__init__( app )
        self.hda_manager = hdas.HDAManager( app )
        self.history_manager = histories.HistoryManager( app )
        self.folder_manager = folders.FolderManager()
        self.hda_serializer = hdas.HDASerializer( app )
        self.hda_deserializer = hdas.HDADeserializer( app )

    def _parse_serialization_params( self, kwd, default_view ):
        view = kwd.get( 'view', None )
        keys = kwd.get( 'keys' )
        if isinstance( keys, basestring ):
            keys = keys.split( ',' )
        return dict( view=view, keys=keys, default_view=default_view )

    @expose_api_anonymous
    def index( self, trans, history_id, ids=None, **kwd ):
        """
        index( self, trans, history_id, ids=None, **kwd )
        * GET /api/histories/{history_id}/contents
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
        rval = []

        history = self.history_manager.get_accessible( self.decode_id( history_id ), trans.user, current_history=trans.history )

        # Allow passing in type or types - for continuity rest of methods
        # take in type - but this one can be passed multiple types and
        # type=dataset,dataset_collection is a bit silly.
        types = kwd.get( 'type', kwd.get( 'types', None ) ) or []
        if types:
            types = util.listify(types)
        else:
            types = [ 'dataset', "dataset_collection" ]

        contents_kwds = { 'types': types }
        if ids:
            ids = map( lambda id: self.decode_id( id ), ids.split( ',' ) )
            contents_kwds[ 'ids' ] = ids
            # If explicit ids given, always used detailed result.
            details = 'all'
        else:
            contents_kwds[ 'deleted' ] = kwd.get( 'deleted', None )
            contents_kwds[ 'visible' ] = kwd.get( 'visible', None )
            # details param allows a mixed set of summary and detailed hdas
            # Ever more convoluted due to backwards compat..., details
            # should be considered deprecated in favor of more specific
            # dataset_details (and to be implemented dataset_collection_details).
            details = kwd.get( 'details', None ) or kwd.get( 'dataset_details', None ) or []
            if details and details != 'all':
                details = util.listify( details )

        for content in history.contents_iter( **contents_kwds ):
            encoded_content_id = trans.security.encode_id( content.id )
            detailed = details == 'all' or ( encoded_content_id in details )

            if isinstance( content, trans.app.model.HistoryDatasetAssociation ):
                view = 'detailed' if detailed else 'summary'
                hda_dict = self.hda_serializer.serialize_to_view( content, view=view, user=trans.user, trans=trans )
                rval.append( hda_dict )

            elif isinstance( content, trans.app.model.HistoryDatasetCollectionAssociation ):
                view = 'element' if detailed else 'collection'
                collection_dict = self.__collection_dict( trans, content, view=view )
                rval.append( collection_dict )

        return rval

    def __collection_dict( self, trans, dataset_collection_instance, view="collection" ):
        return dictify_dataset_collection_instance( dataset_collection_instance,
                                                    security=trans.security, parent=dataset_collection_instance.history, view=view )

    @expose_api_anonymous
    def show( self, trans, id, history_id, **kwd ):
        """
        show( self, trans, id, history_id, **kwd )
        * GET /api/histories/{history_id}/contents/{id}
            return detailed information about an HDA within a history
        .. note:: Anonymous users are allowed to get their current history contents

        :type   id:         str
        :param  ids:        the encoded id of the HDA to return
        :type   history_id: str
        :param  history_id: encoded id string of the HDA's History

        :rtype:     dict
        :returns:   dictionary containing detailed HDA information
        """
        contents_type = kwd.get('type', 'dataset')
        if contents_type == 'dataset':
            return self.__show_dataset( trans, id, **kwd )
        elif contents_type == 'dataset_collection':
            return self.__show_dataset_collection( trans, id, history_id, **kwd )
        else:
            return self.__handle_unknown_contents_type( trans, contents_type )

    def __show_dataset( self, trans, id, **kwd ):
        hda = self.hda_manager.get_accessible( self.decode_id( id ), trans.user )
        return self.hda_serializer.serialize_to_view( hda,
                                                      user=trans.user, trans=trans, **self._parse_serialization_params( kwd, 'detailed' ) )

    def __show_dataset_collection( self, trans, id, history_id, **kwd ):
        try:
            service = trans.app.dataset_collections_service
            dataset_collection_instance = service.get_dataset_collection_instance(
                trans=trans,
                instance_type='history',
                id=id,
            )
            return self.__collection_dict( trans, dataset_collection_instance, view="element" )
        except Exception, e:
            log.exception( "Error in history API at listing dataset collection: %s", e )
            trans.response.status = 500
            return { 'error': str( e ) }

    @expose_api_anonymous
    def create( self, trans, history_id, payload, **kwd ):
        """
        create( self, trans, history_id, payload, **kwd )
        * POST /api/histories/{history_id}/contents/{type}
            create a new HDA by copying an accessible LibraryDataset

        :type   history_id: str
        :param  history_id: encoded id string of the new HDA's History
        :type   type: str
        :param  type: Type of history content - 'dataset' (default) or
                      'dataset_collection'.
        :type   payload:    dict
        :param  payload:    dictionary structure containing::
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

            create new history dataset collection (for type 'dataset_collection')
            'source'              = 'new_collection' (default 'source' if type is
                                    'dataset_collection' - no need to specify this)
            'collection_type'     = For example, "list", "paired", "list:paired".
            'name'                = Name of new dataset collection.
            'element_identifiers' = Recursive list structure defining collection.
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
        # TODO: Flush out create new collection documentation above, need some
        # examples. See also bioblend and API tests for specific examples.

        history = self.history_manager.get_owned( self.decode_id( history_id ), trans.user,
                                                  current_history=trans.history )

        type = payload.get( 'type', 'dataset' )
        if type == 'dataset':
            source = payload.get( 'source', None )
            if source == 'library_folder':
                return self.__create_datasets_from_library_folder( trans, history, payload, **kwd )
            else:
                return self.__create_dataset( trans, history, payload, **kwd )
        elif type == 'dataset_collection':
            return self.__create_dataset_collection( trans, history, payload, **kwd )
        else:
            return self.__handle_unknown_contents_type( trans, type )

    def __create_dataset( self, trans, history, payload, **kwd ):
        source = payload.get( 'source', None )
        if source not in ( 'library', 'hda' ):
            raise exceptions.RequestParameterInvalidException(
                "'source' must be either 'library' or 'hda': %s" % ( source ) )
        content = payload.get( 'content', None )
        if content is None:
            raise exceptions.RequestParameterMissingException( "'content' id of lda or hda is missing" )

        # copy from library dataset
        hda = None
        if source == 'library':
            ld = self.get_library_dataset( trans, content, check_ownership=False, check_accessible=False )
            # TODO: why would get_library_dataset NOT return a library dataset?
            if type( ld ) is not trans.app.model.LibraryDataset:
                raise exceptions.RequestParameterInvalidException(
                    "Library content id ( %s ) is not a dataset" % content )
            # insert into history
            hda = ld.library_dataset_dataset_association.to_history_dataset_association( history, add_to_history=True )

        # copy an existing, accessible hda
        elif source == 'hda':
            unencoded_hda_id = self.decode_id( content )
            original = self.hda_manager.get_accessible( unencoded_hda_id, trans.user )
            # check for access on history that contains the original hda as well
            self.history_manager.error_unless_accessible( original.history, trans.user, current_history=trans.history )
            hda = self.hda_manager.copy( original, history=history )

            # data_copy = original.copy( copy_children=True )
            # hda = history.add_dataset( data_copy )

        trans.sa_session.flush()
        if not hda:
            return None
        return self.hda_serializer.serialize_to_view( hda,
            user=trans.user, trans=trans, **self._parse_serialization_params( kwd, 'detailed' ) )

    def __create_datasets_from_library_folder( self, trans, history, payload, **kwd ):
        rval = []

        source = payload.get( 'source', None )
        if source == 'library_folder':
            content = payload.get( 'content', None )
            if content is None:
                raise exceptions.RequestParameterMissingException( "'content' id of lda or hda is missing" )

            folder_id = self.folder_manager.cut_and_decode( trans, content )
            folder = self.folder_manager.get( trans, folder_id )

            current_user_roles = trans.get_current_user_roles()

            def traverse( folder ):
                admin = trans.user_is_admin()
                rval = []
                for subfolder in folder.active_folders:
                    if not admin:
                        can_access, folder_ids = trans.app.security_agent.check_folder_contents( trans.user, current_user_roles, subfolder )
                    if (admin or can_access) and not subfolder.deleted:
                        rval.extend( traverse( subfolder ) )
                for ld in folder.datasets:
                    if not admin:
                        can_access = trans.app.security_agent.can_access_dataset(
                            current_user_roles,
                            ld.library_dataset_dataset_association.dataset
                        )
                    if (admin or can_access) and not ld.deleted:
                        rval.append( ld )
                return rval

            for ld in traverse( folder ):
                hda = ld.library_dataset_dataset_association.to_history_dataset_association( history, add_to_history=True )
                hda_dict = self.hda_serializer.serialize_to_view( hda,
            user=trans.user, trans=trans, **self._parse_serialization_params( kwd, 'detailed' ) )
                rval.append( hda_dict )
        else:
            message = "Invalid 'source' parameter in request %s" % source
            raise exceptions.RequestParameterInvalidException(message)

        trans.sa_session.flush()
        return rval

    def __create_dataset_collection( self, trans, history, payload, **kwd ):
        source = kwd.get("source", "new_collection")
        service = trans.app.dataset_collections_service
        if source == "new_collection":
            create_params = api_payload_to_create_params( payload )
            dataset_collection_instance = service.create(
                trans,
                parent=history,
                **create_params
            )
        elif source == "hdca":
            content = payload.get( 'content', None )
            if content is None:
                raise exceptions.RequestParameterMissingException( "'content' id of target to copy is missing" )
            dataset_collection_instance = service.copy(
                trans=trans,
                parent=history,
                source="hdca",
                encoded_source_id=content,
            )
        else:
            message = "Invalid 'source' parameter in request %s" % source
            raise exceptions.RequestParameterInvalidException(message)
        return self.__collection_dict( trans, dataset_collection_instance, view="element" )

    @expose_api_anonymous
    def update( self, trans, history_id, id, payload, **kwd ):
        """
        update( self, trans, history_id, id, payload, **kwd )
        * PUT /api/histories/{history_id}/contents/{id}
            updates the values for the HDA with the given ``id``

        :type   history_id: str
        :param  history_id: encoded id string of the HDA's History
        :type   id:         str
        :param  id:         the encoded id of the history to undelete
        :type   payload:    dict
        :param  payload:    a dictionary containing any or all the
            fields in :func:`galaxy.model.HistoryDatasetAssociation.to_dict`
            and/or the following:

            * annotation: an annotation for the HDA

        :rtype:     dict
        :returns:   an error object if an error occurred or a dictionary containing
            any values that were different from the original and, therefore, updated
        """
        # TODO: PUT /api/histories/{encoded_history_id} payload = { rating: rating } (w/ no security checks)
        contents_type = kwd.get('type', 'dataset')
        if contents_type == "dataset":
            return self.__update_dataset( trans, history_id, id, payload, **kwd )
        elif contents_type == "dataset_collection":
            return self.__update_dataset_collection( trans, history_id, id, payload, **kwd )
        else:
            return self.__handle_unknown_contents_type( trans, contents_type )

    def __update_dataset( self, trans, history_id, id, payload, **kwd ):
        # anon user: ensure that history ids match up and the history is the current,
        #   check for uploading, and use only the subset of attribute keys manipulatable by anon users
        if trans.user is None:
            hda = self.hda_manager.by_id( self.decode_id( id ) )
            if hda.history != trans.history:
                raise exceptions.AuthenticationRequired( 'API authentication required for this request' )
            hda = self.hda_manager.error_if_uploading( hda )

            anon_allowed_payload = {}
            if 'deleted' in payload:
                anon_allowed_payload[ 'deleted' ] = payload[ 'deleted' ]
            if 'visible' in payload:
                anon_allowed_payload[ 'visible' ] = payload[ 'visible' ]
            payload = anon_allowed_payload

        # logged in user: use full payload, check state if deleting, and make sure the history is theirs
        else:
            hda = self.hda_manager.get_owned( self.decode_id( id ), trans.user, current_history=trans.history )

            # only check_state if not deleting, otherwise cannot delete uploading files
            check_state = not payload.get( 'deleted', False )
            if check_state:
                hda = self.hda_manager.error_if_uploading( hda )

        # make the actual changes
        # TODO: is this if still needed?
        if hda and isinstance( hda, trans.model.HistoryDatasetAssociation ):
            self.hda_deserializer.deserialize( hda, payload, user=trans.user, trans=trans )
            # TODO: this should be an effect of deleting the hda
            if payload.get( 'deleted', False ):
                self.hda_manager.stop_creating_job( hda )
            return self.hda_serializer.serialize_to_view( hda,
                                                          user=trans.user, trans=trans, **self._parse_serialization_params( kwd, 'detailed' ) )

        return {}

    def __update_dataset_collection( self, trans, history_id, id, payload, **kwd ):
        return trans.app.dataset_collections_service.update( trans, "history", id, payload )

    # TODO: allow anonymous del/purge and test security on this
    @expose_api
    def delete( self, trans, history_id, id, purge=False, **kwd ):
        """
        delete( self, trans, history_id, id, **kwd )
        * DELETE /api/histories/{history_id}/contents/{id}
            delete the HDA with the given ``id``
        .. note:: Currently does not stop any active jobs for which this dataset is an output.

        :type   id:     str
        :param  id:     the encoded id of the history to delete
        :type   purge:  bool
        :param  purge:  if True, purge the HDA
        :type   kwd:    dict
        :param  kwd:    (optional) dictionary structure containing:

            * payload:     a dictionary itself containing:
                * purge:   if True, purge the HDA

        .. note:: that payload optionally can be placed in the query string of the request.
            This allows clients that strip the request body to still purge the dataset.

        :rtype:     dict
        :returns:   an error object if an error occurred or a dictionary containing:
            * id:         the encoded id of the history,
            * deleted:    if the history was marked as deleted,
            * purged:     if the history was purged
        """
        contents_type = kwd.get('type', 'dataset')
        if contents_type == "dataset":
            return self.__delete_dataset( trans, history_id, id, purge=purge, **kwd )
        elif contents_type == "dataset_collection":
            trans.app.dataset_collections_service.delete( trans, "history", id )
            return { 'id' : id, "deleted": True }
        else:
            return self.__handle_unknown_contents_type( trans, contents_type )

    def __delete_dataset( self, trans, history_id, id, purge, **kwd ):
        # get purge from the query or from the request body payload (a request body is optional here)
        purge = util.string_as_bool( purge )
        if kwd.get( 'payload', None ):
            # payload takes priority
            purge = util.string_as_bool( kwd['payload'].get( 'purge', purge ) )

        hda = self.hda_manager.get_owned( self.decode_id( id ), trans.user, current_history=trans.history )
        self.hda_manager.error_if_uploading( hda )

        if purge:
            self.hda_manager.purge( hda )
        else:
            self.hda_manager.delete( hda )
        return self.hda_serializer.serialize_to_view( hda,
                                                      user=trans.user, trans=trans, **self._parse_serialization_params( kwd, 'detailed' ) )

    def __handle_unknown_contents_type( self, trans, contents_type ):
        raise exceptions.UnknownContentsType('Unknown contents type: %s' % type)
