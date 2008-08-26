
from galaxy.web.base.controller import *
import logging

log = logging.getLogger( __name__ )

class Library( BaseController ):
    @web.expose
    def index( self, trans, library_id=None, import_ids=[], **kwd ):
        # Need user to get associated Groups and Datasets
        user = trans.get_user()
        libraries = []
        if import_ids:
            # Used for importing a dataset into a user's history
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
            # Since permitted_actions are kept with the GroupDatasetAssociation, each accessible Library will only
            # display the subset of [ it's complete set of ] datasets that the user has permission to access.  We
            # pass group_ids so this can be handled in the template.
            if not user:
                group_ids = [ trans.app.model.Group.select_by( name='public' )[0].id ]
            else:
                group_ids = []
                for user_group_assoc in user.groups:
                    group_ids.append( user_group_assoc.group_id )
            library = trans.app.model.Library.get( library_id )
            return trans.fill_template( '/library/library.mako', library=library, group_ids=group_ids )
        else:
            if user:
                # Only display libraries that contain datasets associated with the user's groups
                group_ids = []
                for user_group_assoc in user.groups:
                    group = trans.app.model.Group.get( user_group_assoc.group_id )
                    group_ids.append( group.id )
            else:       
                # Only display libraries that contain datasets associated with the public group
                group_ids = [ trans.app.model.Group.select_by( name='public' )[0].id ]
            libs = trans.app.model.Library.select()
            for library in libs:
                folder = library.root_folder
                components = list( folder.folders ) + list( folder.datasets )
                for component in components:
                    if self.renderable( trans, component, group_ids ):
                        libraries.append( library )
                        break
        return trans.fill_template( '/library/libraries.mako', group_ids=group_ids, libraries=libraries )
    def renderable( self, trans, component, group_ids ):
        render = False
        if isinstance( component, trans.app.model.LibraryFolder ):
            # Check the folder's datasets to see what can be rendered
            for library_folder_dataset_assoc in component.datasets:
                if render:
                    break
                dataset = trans.app.model.Dataset.get( library_folder_dataset_assoc.dataset_id )
                for group_dataset_assoc in dataset.groups:
                    if group_dataset_assoc.group_id in group_ids:
                        render = True
                        break
            # Check the folder's sub-folders to see what can be rendered
            if not render:
                for library_folder in component.folders:
                    self.renderable( trans, library_folder, group_ids )
        elif isinstance( component, trans.app.model.LibraryFolderDatasetAssociation ):
            render = False
            dataset = trans.app.model.Dataset.get( component.dataset_id )
            for group_dataset_assoc in dataset.groups:
                if group_dataset_assoc.group_id in group_ids:
                    render = True
                    break
        return render
