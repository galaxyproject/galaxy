
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
        if user:
            # Only display libraries that contain datasets associated with the user's groups
            group_ids = []
            for user_group_assoc in user.groups:
                group = trans.app.model.Group.get( user_group_assoc.group_id )
                group_ids.append( group.id )
            libs = trans.app.model.Library.select()
            for library in libs:
                user_can_access = False
                # Check for public datasets in the Library's root folder
                for library_folder_dataset_assoc in library.root_folder.datasets:
                    if user_can_access:
                        break
                    dataset = trans.app.model.Dataset.get( library_folder_dataset_assoc.dataset_id )
                    for group_dataset_assoc in dataset.groups:
                        if group_dataset_assoc.group_id in group_ids:
                            libraries.append( library )
                            user_can_access = True
                            break
                for folder in library.root_folder.folders:
                    if user_can_access:
                        break
                    for library_folder_dataset_assoc in folder.datasets:
                        if user_can_access:
                            break
                        dataset = trans.app.model.Dataset.get( library_folder_dataset_assoc.dataset_id )
                        for group_dataset_assoc in dataset.groups:
                            if group_dataset_assoc.group_id in group_ids:
                                libraries.append( library )
                                user_can_access = True
                                break
        else:       
            # Only display libraries that contain datasets associated with the public group
            group_ids = [ trans.app.model.Group.select_by( name='public' )[0].id ]
            libs = trans.app.model.Library.select()
            for library in libs:
                public_library = False
                # Check for public datasets in the Library's root folder
                for library_folder_dataset_assoc in library.root_folder.datasets:
                    if public_library:
                        break
                    dataset = trans.app.model.Dataset.get( library_folder_dataset_assoc.dataset_id )
                    for group_dataset_assoc in dataset.groups:
                        if group_dataset_assoc.group_id in group_ids:
                            libraries.append( library )
                            public_library = True
                            break
                # Check for public datasets in the root folder's sub-folders
                for folder in library.root_folder.folders:
                    if public_library:
                        break
                    for library_folder_dataset_assoc in folder.datasets:
                        if public_library:
                            break
                        dataset = trans.app.model.Dataset.get( library_folder_dataset_assoc.dataset_id )
                        for group_dataset_assoc in dataset.groups:
                            if group_dataset_assoc.group_id in group_ids:
                                libraries.append( library )
                                public_library = True
                                break
        return trans.fill_template( '/library/libraries.mako', group_ids=group_ids, libraries=libraries )
