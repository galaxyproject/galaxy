from galaxy.web.base.controller import *
from galaxy.model.orm import *
import logging

log = logging.getLogger( __name__ )

class Library( BaseController ):
    @web.expose
    def browse( self, trans, **kwd ):
        libraries = trans.app.model.Library.filter( trans.app.model.Library.table.c.deleted==False ) \
                                           .order_by( trans.app.model.Library.table.c.name ).all()
        return trans.fill_template( '/library/browser.mako', libraries=libraries )
    index = browse
    @web.expose
    def import_datasets( self, trans, import_ids=[], **kwd ):
        if not import_ids:
            return trans.show_error_message( "You must select at least one dataset to import" )
        if not isinstance( import_ids, list ):
            import_ids = [ import_ids ]
        history = trans.get_history()
        for id in import_ids:
            dataset = trans.app.model.LibraryFolderDatasetAssociation.get( id ).to_history_dataset_association()
            history.add_dataset( dataset )
            dataset.flush()
        history.flush()
        return trans.show_ok_message( "%i dataset(s) have been imported in to your history" % len( import_ids ), refresh_frames=['history'] )
    @web.expose
    def download_dataset_from_folder(self, trans, id, **kwd):
        """Catches the dataset id and displays file contents as directed"""
        # id refers to a LibraryFolderDatasetAssociation object
        lfda = trans.app.model.LibraryFolderDatasetAssociation.get( id )
        dataset = trans.app.model.Dataset.get( lfda.dataset_id )
        if not dataset:
            msg = 'Invalid id %s received for file downlaod' % str( id )
            return trans.response.send_redirect( web.url_for( action='library_browser', msg=msg, messagetype='error' ) )
        mime = trans.app.datatypes_registry.get_mimetype_by_extension( lfda.extension.lower() )
        trans.response.set_content_type( mime )
        fStat = os.stat( lfda.file_name )
        trans.response.headers[ 'Content-Length' ] = int( fStat.st_size )
        valid_chars = '.,^_-()[]0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
        fname = lfda.name
        fname = ''.join( c in valid_chars and c or '_' for c in fname )[ 0:150 ]
        trans.response.headers[ "Content-Disposition" ] = "attachment; filename=GalaxyLibraryDataset-%s-[%s]" % ( str( id ), fname )
        try:
            return open( lfda.file_name )
        except: 
            msg = 'This dataset contains no content'
            return trans.response.send_redirect( web.url_for( action='library_browser', msg=msg, messagetype='error' ) )
