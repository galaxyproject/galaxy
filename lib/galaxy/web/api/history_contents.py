"""
API operations on the contents of a history.
"""
import logging
from galaxy import web
from galaxy.web.base.controller import *
from galaxy.model.orm import *

import pkg_resources
pkg_resources.require( "Routes" )
import routes

log = logging.getLogger( __name__ )

class HistoryContentsController( BaseAPIController, UsesHistoryDatasetAssociation, UsesHistory, UsesLibrary, UsesLibraryItems ):

    @web.expose_api
    def index( self, trans, history_id, **kwd ):
        """
        GET /api/histories/{encoded_history_id}/contents
        Displays a collection (list) of history contents
        """
        try:
            history = self.get_history( trans, history_id, check_ownership=True, check_accessible=True )
        except Exception, e:
            return str( e )
        rval = []
        try:
            for dataset in history.datasets:
                api_type = "file"
                encoded_id = trans.security.encode_id( dataset.id )
                rval.append( dict( id = encoded_id,
                                   type = api_type,
                                   name = dataset.name,
                                   url = url_for( 'history_content', history_id=history_id, id=encoded_id, ) ) )
        except Exception, e:
            rval = "Error in history API at listing contents"
            log.error( rval + ": %s" % str(e) )
            trans.response.status = 500
        return rval

    @web.expose_api
    def show( self, trans, id, history_id, **kwd ):
        """
        GET /api/histories/{encoded_history_id}/contents/{encoded_content_id}
        Displays information about a history content (dataset).
        """
        content_id = id
        try:
            # get the history just for the access checks
            history = self.get_history( trans, history_id, check_ownership=True, check_accessible=True, deleted=False )
            content = self.get_history_dataset_association( trans, history, content_id, check_ownership=True, check_accessible=True )
        except Exception, e:
            return str( e )
        try:
            item = content.get_api_value( view='element' )
            if trans.user_is_admin() or trans.app.config.expose_dataset_path:
                 item['file_name'] = content.file_name
            if not item['deleted']:
                # Problem: Method url_for cannot use the dataset controller
                # Get the environment from DefaultWebTransaction and use default webapp mapper instead of webapp API mapper
                url = routes.URLGenerator(trans.webapp.mapper, trans.environ)
                # http://routes.groovie.org/generating.html
                # url_for is being phased out, so new applications should use url
                item['download_url'] = url(controller='dataset', action='display', dataset_id=trans.security.encode_id(content.id), to_ext=content.ext)
                item = self.encode_all_ids( trans, item )
        except Exception, e:
            item = "Error in history API at listing dataset"
            log.error( item + ": %s" % str(e) )
            trans.response.status = 500
        return item

    @web.expose_api
    def create( self, trans, history_id, payload, **kwd ):
        """
        POST /api/libraries/{encoded_history_id}/contents
        Creates a new history content item (file, aka HistoryDatasetAssociation).
        """
        from_ld_id = payload.get( 'from_ld_id', None )

        try:
            history = self.get_history( trans, history_id, check_ownership=True, check_accessible=False )
        except Exception, e:
            return str( e )

        if from_ld_id:
            try:
                ld = self.get_library_dataset( trans, from_ld_id, check_ownership=False, check_accessible=False )
                assert type( ld ) is trans.app.model.LibraryDataset, "Library content id ( %s ) is not a dataset" % from_ld_id
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
            trans.response.status = 403
            return "Not implemented."
