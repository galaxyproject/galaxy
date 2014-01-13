"""
API operations on the contents of a history.
"""

import logging
from galaxy import exceptions, util, web
from galaxy.web.base.controller import ( BaseAPIController, url_for,
        UsesHistoryDatasetAssociationMixin, UsesHistoryMixin, UsesLibraryMixin,
        UsesLibraryMixinItems, UsesTagsMixin )
from galaxy.util.sanitize_html import sanitize_html

log = logging.getLogger( __name__ )


class HistoryContentsController( BaseAPIController, UsesHistoryDatasetAssociationMixin, UsesHistoryMixin,
                                 UsesLibraryMixin, UsesLibraryMixinItems, UsesTagsMixin ):

    @web.expose_api_anonymous
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

        :rtype:     list
        :returns:   dictionaries containing summary or detailed HDA information
        .. seealso::
            :func:`_summary_hda_dict` and
            :func:`galaxy.web.base.controller.UsesHistoryDatasetAssociationMixin.get_hda_dict`
        """
        rval = []
        try:
            # get the history, if anon user and requesting current history - allow it
            if( ( trans.user == None )
                and ( history_id == trans.security.encode_id( trans.history.id ) ) ):
                #TODO:?? is secure?
                history = trans.history
            # otherwise, check permissions for the history first
            else:
                history = self.get_history( trans, history_id, check_ownership=True, check_accessible=True )

            contents_kwds = {}
            if ids:
                ids = map( lambda id: trans.security.decode_id( id ), ids.split( ',' ) )
                contents_kwds[ 'ids' ] = ids
                # If explicit ids given, always used detailed result.
                details = 'all'
            else:
                contents_kwds[ 'deleted' ] = kwd.get( 'deleted', None )
                contents_kwds[ 'visible' ] = kwd.get( 'visible', None )
                # details param allows a mixed set of summary and detailed hdas
                #TODO: this is getting convoluted due to backwards compat
                details = kwd.get( 'details', None ) or []
                if details and details != 'all':
                    details = util.listify( details )

            for hda in history.contents_iter( **contents_kwds ):
                encoded_hda_id = trans.security.encode_id( hda.id )
                detailed = details == 'all' or ( encoded_hda_id in details )
                if detailed:
                    rval.append( self._detailed_hda_dict( trans, hda ) )
                else:
                    rval.append( self._summary_hda_dict( trans, history_id, hda ) )
        except Exception, e:
            # for errors that are not specific to one hda (history lookup or summary list)
            rval = "Error in history API at listing contents: " + str( e )
            log.error( rval + ": %s, %s" % ( type( e ), str( e ) ), exc_info=True )
            trans.response.status = 500
        return rval

    #TODO: move to model or Mixin
    def _summary_hda_dict( self, trans, encoded_history_id, hda ):
        """
        Returns a dictionary based on the HDA in summary form::
            {
                'id'    : < the encoded dataset id >,
                'name'  : < currently only returns 'file' >,
                'type'  : < name of the dataset >,
                'url'   : < api url to retrieve this datasets full data >,
            }
        """
        api_type = "file"
        encoded_id = trans.security.encode_id( hda.id )
        return {
            'id'    : encoded_id,
            'history_id' : encoded_history_id,
            'name'  : hda.name,
            'type'  : api_type,
            'state'  : hda.state,
            'deleted': hda.deleted,
            'visible': hda.visible,
            'purged': hda.purged,
            'hid'   : hda.hid,
            'url'   : url_for( 'history_content', history_id=encoded_history_id, id=encoded_id, ),
        }

    def _detailed_hda_dict( self, trans, hda ):
        """
        Detailed dictionary of hda values.
        """
        try:
            hda_dict = self.get_hda_dict( trans, hda )
            hda_dict[ 'display_types' ] = self.get_old_display_applications( trans, hda )
            hda_dict[ 'display_apps' ] = self.get_display_apps( trans, hda )
            return hda_dict
        except Exception, exc:
            # catch error here - returning a briefer hda_dict with an error attribute
            log.exception( "Error in history API at listing contents with history %s, hda %s: (%s) %s",
                hda.history_id, hda.id, type( exc ), str( exc ) )
            return self.get_hda_dict_with_error( trans, hda=hda, error_msg=str( exc ) )

    @web.expose_api_anonymous
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
        .. seealso:: :func:`galaxy.web.base.controller.UsesHistoryDatasetAssociationMixin.get_hda_dict`
        """
        try:
            hda = self.get_history_dataset_association_from_ids( trans, id, history_id )
            hda_dict = self.get_hda_dict( trans, hda )
            hda_dict[ 'display_types' ] = self.get_old_display_applications( trans, hda )
            hda_dict[ 'display_apps' ] = self.get_display_apps( trans, hda )
            return hda_dict
        except Exception, e:
            msg = "Error in history API at listing dataset: %s" % ( str(e) )
            log.error( msg, exc_info=True )
            trans.response.status = 500
            return msg

    @web.expose_api
    def create( self, trans, history_id, payload, **kwd ):
        """
        create( self, trans, history_id, payload, **kwd )
        * POST /api/histories/{history_id}/contents
            create a new HDA by copying an accessible LibraryDataset

        :type   history_id: str
        :param  history_id: encoded id string of the new HDA's History
        :type   payload:    dict
        :param  payload:    dictionary structure containing::
            copy from library:
            'source'    = 'library'
            'content'   = [the encoded id from the library dataset]

            copy from HDA:
            'source'    = 'hda'
            'content'   = [the encoded id from the HDA]

        ..note:
            Currently, a user can only copy an HDA from a history that the user owns.

        :rtype:     dict
        :returns:   dictionary containing detailed information for the new HDA
        """
        #TODO: copy existing, accessible hda - dataset controller, copy_datasets
        #TODO: convert existing, accessible hda - model.DatasetInstance(or hda.datatype).get_converter_types
        # check parameters
        source  = payload.get('source', None)
        content = payload.get('content', None)
        if source not in ['library', 'hda'] or content is None:
            trans.response.status = 400
            return "Please define the source ('library' or 'hda') and the content."
        # retrieve history
        try:
            history = self.get_history( trans, history_id, check_ownership=True, check_accessible=False )
        except Exception, e:
            # no way to tell if it failed bc of perms or other (all MessageExceptions)
            trans.response.status = 500
            return str( e )
        # copy from library dataset
        if source == 'library':
            # get library data set
            try:
                ld = self.get_library_dataset( trans, content, check_ownership=False, check_accessible=False )
                assert type( ld ) is trans.app.model.LibraryDataset, (
                    "Library content id ( %s ) is not a dataset" % content )
            except AssertionError, e:
                trans.response.status = 400
                return str( e )
            except Exception, e:
                return str( e )
            # insert into history
            hda = ld.library_dataset_dataset_association.to_history_dataset_association( history, add_to_history=True )
            trans.sa_session.flush()
            return hda.to_dict()
        elif source == 'hda':
            try:
                #NOTE: user currently only capable of copying one of their own datasets
                hda = self.get_dataset( trans, content )
            except ( exceptions.httpexceptions.HTTPRequestRangeNotSatisfiable,
                     exceptions.httpexceptions.HTTPBadRequest ), id_exc:
                # wot...
                trans.response.status = 400
                return str( id_exc )
            except exceptions.MessageException, msg_exc:
                #TODO: covers most but not all user exceptions, too generic (403 v.401)
                trans.response.status = 403
                return str( msg_exc )
            except Exception, exc:
                trans.response.status = 500
                log.exception( "history: %s, source: %s, content: %s", history_id, source, content )
                return str( exc )
            data_copy=hda.copy( copy_children=True )
            result=history.add_dataset( data_copy )
            trans.sa_session.flush()
            return result.to_dict()
        else:
            # other options
            trans.response.status = 501
            return

    @web.expose_api_anonymous
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
        #TODO: PUT /api/histories/{encoded_history_id} payload = { rating: rating } (w/ no security checks)
        changed = {}
        try:
            # anon user
            if trans.user == None:
                if history_id != trans.security.encode_id( trans.history.id ):
                    trans.response.status = 401
                    return { 'error': 'Anonymous users cannot edit histories other than their current history' }
                anon_allowed_payload = {}
                if 'deleted' in payload:
                    anon_allowed_payload[ 'deleted' ] = payload[ 'deleted' ]
                if 'visible' in payload:
                    anon_allowed_payload[ 'visible' ] = payload[ 'visible' ]
                payload = self._validate_and_parse_update_payload( anon_allowed_payload )
                hda = self.get_dataset( trans, id, check_ownership=False, check_accessible=False, check_state=True )
                if hda.history != trans.history:
                    trans.response.status = 401
                    return { 'error': 'Anonymous users cannot edit datasets outside their current history' }
            else:
                payload = self._validate_and_parse_update_payload( payload )
                hda = self.get_dataset( trans, id, check_ownership=True, check_accessible=True, check_state=True )
            # get_dataset can return a string during an error
            if hda and isinstance( hda, trans.model.HistoryDatasetAssociation ):
                changed = self.set_hda_from_dict( trans, hda, payload )
        except Exception, exception:
            log.error( 'Update of history (%s), HDA (%s) failed: %s',
                        history_id, id, str( exception ), exc_info=True )
            # convert to appropo HTTP code
            if( isinstance( exception, ValueError )
            or  isinstance( exception, AttributeError ) ):
                # bad syntax from the validater/parser
                trans.response.status = 400
            else:
                trans.response.status = 500
            return { 'error': str( exception ) }
        return changed

    #TODO: allow anonymous del/purge and test security on this
    @web.expose_api
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
        # get purge from the query or from the request body payload (a request body is optional here)
        purge = util.string_as_bool( purge )
        if kwd.get( 'payload', None ):
            # payload takes priority
            purge = util.string_as_bool( kwd['payload'].get( 'purge', purge ) )

        rval = { 'id' : id }
        try:
            hda = self.get_dataset( trans, id,
                check_ownership=True, check_accessible=True, check_state=True )
            hda.deleted = True
            if purge:
                if not trans.app.config.allow_user_dataset_purge:
                    raise exceptions.httpexceptions.HTTPForbidden(
                        detail='This instance does not allow user dataset purging' )
                hda.purged = True
                trans.sa_session.add( hda )
                trans.sa_session.flush()
                if hda.dataset.user_can_purge:
                    try:
                        hda.dataset.full_delete()
                        trans.sa_session.add( hda.dataset )
                    except:
                        pass
                    # flush now to preserve deleted state in case of later interruption
                    trans.sa_session.flush()
                rval[ 'purged' ] = True

            trans.sa_session.flush()
            rval[ 'deleted' ] = True

        except exceptions.httpexceptions.HTTPInternalServerError, http_server_err:
            log.exception( 'HDA API, delete: uncaught HTTPInternalServerError: %s, %s\n%s',
                           id, str( kwd ), str( http_server_err ) )
            raise
        except exceptions.httpexceptions.HTTPException:
            raise
        except Exception, exc:
            log.exception( 'HDA API, delete: uncaught exception: %s, %s\n%s',
                           id, str( kwd ), str( exc ) )
            trans.response.status = 500
            rval.update({ 'error': str( exc ) })
        return rval

    def _validate_and_parse_update_payload( self, payload ):
        """
        Validate and parse incomming data payload for an HDA.
        """
        # This layer handles (most of the stricter idiot proofing):
        #   - unknown/unallowed keys
        #   - changing data keys from api key to attribute name
        #   - protection against bad data form/type
        #   - protection against malicious data content
        # all other conversions and processing (such as permissions, etc.) should happen down the line

        # keys listed here don't error when attempting to set, but fail silently
        #   this allows PUT'ing an entire model back to the server without attribute errors on uneditable attrs
        valid_but_uneditable_keys = (
            'id', 'name', 'type', 'api_type', 'model_class', 'history_id', 'hid',
            'accessible', 'purged', 'state', 'data_type', 'file_ext', 'file_size', 'misc_blurb',
            'download_url', 'visualizations', 'display_apps', 'display_types',
            'metadata_dbkey', 'metadata_column_names', 'metadata_column_types', 'metadata_columns',
            'metadata_comment_lines', 'metadata_data_lines'
        )
        validated_payload = {}
        for key, val in payload.items():
            if val is None:
                continue
            if key in ( 'name', 'genome_build', 'misc_info', 'annotation' ):
                val = self.validate_and_sanitize_basestring( key, val )
                #TODO: need better remap system or eliminate the need altogether
                key = 'dbkey' if key == 'genome_build' else key
                key = 'info'  if key == 'misc_info' else key
                validated_payload[ key ] = val
            if key in ( 'deleted', 'visible' ):
                validated_payload[ key ] = self.validate_boolean( key, val )
            elif key == 'tags':
                validated_payload[ key ] = self.validate_and_sanitize_basestring_list( key, val )
            elif key not in valid_but_uneditable_keys:
                pass
                #log.warn( 'unknown key: %s', str( key ) )
        return validated_payload
