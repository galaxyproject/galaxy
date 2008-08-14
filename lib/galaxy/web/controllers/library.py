
from galaxy.web.base.controller import *
import logging

log = logging.getLogger( __name__ )

class Library( BaseController ):
    @web.expose
    def index( self, trans, library_id = None, import_ids = [], **kwd ):
        #use for importing an entry into your history
        if import_ids:
            if not isinstance( import_ids, list ):
                import_ids = [import_ids]
            history = trans.get_history()
            for id in import_ids:
                dataset = trans.app.model.LibraryFolderDatasetAssociation.get( id ).to_history_dataset_association()
                history.add_dataset( dataset )
                dataset.flush()
            history.flush()
            return trans.show_ok_message( "%i datasets have been imported into your history" % len( import_ids ), refresh_frames=['history'] )
        elif library_id:
            return trans.fill_template( '/library/library.mako', library=trans.app.model.Library.get( library_id ) )
        return trans.fill_template( '/library/libraries.mako', libraries=trans.app.model.Library.select() )
