
from galaxy.web.base.controller import *
import logging

log = logging.getLogger( __name__ )

class Library( BaseController ):
    @web.expose
    def index( self, trans, library_id=None, import_ids=[], **kwd ):
        def renderable( component, group_ids ):
            #return True if component or at least one of components contents is 
            #associated with a group that is in group_ids
            if isinstance( component, trans.app.model.LibraryFolder ):
                # Check the folder's datasets to see what can be rendered
                for library_folder_dataset_assoc in component.active_datasets:
                    if renderable( library_folder_dataset_assoc, group_ids ):
                        return True
                # Check the folder's sub-folders to see what can be rendered
                for library_folder in component.active_folders:
                    if renderable( library_folder, group_ids ):
                        return True
            elif isinstance( component, trans.app.model.LibraryFolderDatasetAssociation ):
                dataset = trans.app.model.Dataset.get( component.dataset_id )
                for group_dataset_assoc in dataset.groups:
                    if group_dataset_assoc.group_id in group_ids:
                        return True
            return False
        
        if import_ids:
            # Used for importing a dataset into a user's history
            if not isinstance( import_ids, list ):
                import_ids = [import_ids]
            history = trans.get_history()
            for id in import_ids:
                dataset = trans.app.model.LibraryFolderDatasetAssociation.get( id ).to_history_dataset_association( target_history = history )
                history.add_dataset( dataset, set_hid = not dataset.hid )
                dataset.flush()
            history.flush()
            return trans.show_ok_message( "%i datasets have been imported into your history" % len( import_ids ), refresh_frames=['history'] )
        else:
            # Need user to get associated Groups and Datasets
            user = trans.get_user()
            if user:
                group_ids = [ user_group_assoc.group_id for user_group_assoc in user.groups ]
            else:
                group_ids = [ trans.app.model.Group.select_by( name='public' )[0].id ]
            
            if library_id:
                # Since permitted_actions are kept with the GroupDatasetAssociation, each accessible Library will only
                # display the subset of [ it's complete set of ] datasets that the user has permission to access.  We
                # pass group_ids so this can be handled in the template.
                library = trans.app.model.Library.get( library_id )
                return trans.fill_template( '/library/library.mako', library=library, group_ids=group_ids )
            
            #render available libraries
            libraries = [ library for library in trans.app.model.Library.select_by( deleted = False ) if renderable( library.root_folder, group_ids ) ]
            return trans.fill_template( '/library/libraries.mako', group_ids=group_ids, libraries=libraries )
