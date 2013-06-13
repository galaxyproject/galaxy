"""
API operations on the contents of a history.
"""

from galaxy import web, util
from galaxy.web.base.controller import BaseAPIController, url_for
from galaxy.web.base.controller import UsesHistoryDatasetAssociationMixin, UsesHistoryMixin
from galaxy.web.base.controller import UsesLibraryMixin, UsesLibraryMixinItems

import logging
log = logging.getLogger( __name__ )

class HistoryContentsController( BaseAPIController, UsesHistoryDatasetAssociationMixin, UsesHistoryMixin,
                                 UsesLibraryMixin, UsesLibraryMixinItems ):
    @web.expose_api_anonymous
    def index( self, trans, history_id, ids=None, **kwd ):
        """
        GET /api/histories/{encoded_history_id}/contents
        Displays a collection (list) of history contents (HDAs)

        :param history_id: an encoded id string of the `History` to search
        :param ids: (optional) a comma separated list of encoded `HDA` ids

        If Ids is not given, index returns a list of *summary* json objects for
        every `HDA` associated with the given `history_id`.
        See _summary_hda_dict.

        If ids is given, index returns a *more complete* json object for each
        HDA in the ids list.

        Note: Anonymous users are allowed to get their current history contents
        (generally useful for browser UI access of the api)
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

            # if ids, return _FULL_ data (as show) for each id passed
            if ids:
                ids = ids.split( ',' )
                for index, hda in enumerate( history.datasets ):
                    encoded_hda_id = trans.security.encode_id( hda.id )
                    if encoded_hda_id in ids:
                        #TODO: share code with show
                        try:
                            hda_dict = self.get_hda_dict( trans, hda )
                            hda_dict[ 'display_types' ] = self.get_old_display_applications( trans, hda )
                            hda_dict[ 'display_apps' ] = self.get_display_apps( trans, hda )
                            rval.append( hda_dict )

                        except Exception, exc:
                            # don't fail entire list if hda err's, record and move on
                            log.error( "Error in history API at listing contents with history %s, hda %s: (%s) %s",
                                history_id, encoded_hda_id, type( exc ), str( exc ), exc_info=True )
                            rval.append( self.get_hda_dict_with_error( trans, hda, str( exc ) ) )

            # if no ids passed, return a _SUMMARY_ of _all_ datasets in the history
            else:
                for hda in history.datasets:
                    rval.append( self._summary_hda_dict( trans, history_id, hda ) )

        except Exception, e:
            # for errors that are not specific to one hda (history lookup or summary list)
            rval = "Error in history API at listing contents: " + str( e )
            log.error( rval + ": %s, %s" % ( type( e ), str( e ) ), exc_info=True )
            trans.response.status = 500

        return rval

    #TODO: move to model or Mixin
    def _summary_hda_dict( self, trans, history_id, hda ):
        """
        Returns a dictionary based on the HDA in .. _summary form::
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
            'name'  : hda.name,
            'type'  : api_type,
            'url'   : url_for( 'history_content', history_id=history_id, id=encoded_id, ),
        }

    @web.expose_api_anonymous
    def show( self, trans, id, history_id, **kwd ):
        """
        GET /api/histories/{encoded_history_id}/contents/{encoded_content_id}
        Displays information about a history content (dataset).
        """
        hda_dict = {}
        try:
            # for anon users:
            #TODO: check login_required?
            #TODO: this isn't actually most_recently_used (as defined in histories)
            if( ( trans.user == None )
            and ( history_id == trans.security.encode_id( trans.history.id ) ) ):
                history = trans.history
                #TODO: dataset/hda by id (from history) OR check_ownership for anon user
                hda = self.get_history_dataset_association( trans, history, id,
                    check_ownership=False, check_accessible=True )

            else:
                #TODO: do we really need the history?
                history = self.get_history( trans, history_id,
                    check_ownership=True, check_accessible=True, deleted=False )
                hda = self.get_history_dataset_association( trans, history, id,
                    check_ownership=True, check_accessible=True )

            hda_dict = self.get_hda_dict( trans, hda )
            hda_dict[ 'display_types' ] = self.get_old_display_applications( trans, hda )
            hda_dict[ 'display_apps' ] = self.get_display_apps( trans, hda )

        except Exception, e:
            msg = "Error in history API at listing dataset: %s" % ( str(e) )
            log.error( msg, exc_info=True )
            trans.response.status = 500
            return msg

        return hda_dict

    @web.expose_api
    def create( self, trans, history_id, payload, **kwd ):
        """
        POST /api/histories/{encoded_history_id}/contents
        Creates a new history content item (file, aka HistoryDatasetAssociation).
        """
        #TODO: copy existing, accessible hda - dataset controller, copy_datasets
        #TODO: convert existing, accessible hda - model.DatasetInstance(or hda.datatype).get_converter_types
        from_ld_id = payload.get( 'from_ld_id', None )
        try:
            history = self.get_history( trans, history_id, check_ownership=True, check_accessible=False )
        except Exception, e:
            #TODO: no way to tell if it failed bc of perms or other (all MessageExceptions)
            trans.response.status = 500
            return str( e )

        if from_ld_id:
            try:
                ld = self.get_library_dataset( trans, from_ld_id, check_ownership=False, check_accessible=False )
                assert type( ld ) is trans.app.model.LibraryDataset, (
                    "Library content id ( %s ) is not a dataset" % from_ld_id )

            except AssertionError, e:
                trans.response.status = 400
                return str( e )

            except Exception, e:
                return str( e )

            hda = ld.library_dataset_dataset_association.to_history_dataset_association( history, add_to_history=True )
            trans.sa_session.flush()
            return hda.get_api_value()

        else:
            # TODO: implement other "upload" methods here.
            trans.response.status = 501
            return "Not implemented."

    @web.expose_api
    def update( self, trans, history_id, id, payload, **kwd ):
        """
        PUT /api/histories/{encoded_history_id}/contents/{encoded_content_id}
        Changes an existing history dataset.
        """
        #TODO: PUT /api/histories/{encoded_history_id} payload = { rating: rating } (w/ no security checks)
        changed = {}
        try:
            hda = self.get_dataset( trans, id,
                check_ownership=True, check_accessible=True, check_state=True )
            # validation handled here and some parsing, processing, and conversion
            payload = self._validate_and_parse_update_payload( payload )
            # additional checks here (security, etc.)
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
            # TODO: lots of boilerplate here, but overhead on abstraction is equally onerous
            # typecheck, parse, remap key
            if   key == 'name':
                if not ( isinstance( val, str ) or isinstance( val, unicode ) ):
                    raise ValueError( 'name must be a string or unicode: %s' %( str( type( val ) ) ) )
                validated_payload[ 'name' ] = util.sanitize_html.sanitize_html( val, 'utf-8' )
                #TODO:?? if sanitized != val: log.warn( 'script kiddie' )
            elif key == 'deleted':
                if not isinstance( val, bool ):
                    raise ValueError( 'deleted must be a boolean: %s' %( str( type( val ) ) ) )
                validated_payload[ 'deleted' ] = val
            elif key == 'visible':
                if not isinstance( val, bool ):
                    raise ValueError( 'visible must be a boolean: %s' %( str( type( val ) ) ) )
                validated_payload[ 'visible' ] = val
            elif key == 'genome_build':
                if not ( isinstance( val, str ) or isinstance( val, unicode ) ):
                    raise ValueError( 'genome_build must be a string: %s' %( str( type( val ) ) ) )
                validated_payload[ 'dbkey' ] = util.sanitize_html.sanitize_html( val, 'utf-8' )
            elif key == 'annotation':
                if not ( isinstance( val, str ) or isinstance( val, unicode ) ):
                    raise ValueError( 'annotation must be a string or unicode: %s' %( str( type( val ) ) ) )
                validated_payload[ 'annotation' ] = util.sanitize_html.sanitize_html( val, 'utf-8' )
            elif key == 'misc_info':
                if not ( isinstance( val, str ) or isinstance( val, unicode ) ):
                    raise ValueError( 'misc_info must be a string or unicode: %s' %( str( type( val ) ) ) )
                validated_payload[ 'info' ] = util.sanitize_html.sanitize_html( val, 'utf-8' )
            elif key not in valid_but_uneditable_keys:
                raise AttributeError( 'unknown key: %s' %( str( key ) ) )
        return validated_payload

