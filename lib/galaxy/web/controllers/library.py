
from galaxy.web.base.controller import *
from galaxy.datatypes import sniff
import logging, shutil, StringIO

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
            return trans.fill_template( 'library/user_view_library.mako', library = trans.app.model.Library.get( library_id ) )
        return trans.fill_template( 'library/user_list_libraries.mako', libraries = trans.app.model.Library.select() )

    #make admin only
    @web.expose
    def manage_libraries( self, trans, **kwd ):
        return trans.fill_template( 'library/admin_list_libraries.mako', libraries = trans.app.model.Library.select() )

    #make admin only
    @web.expose
    def manage_library( self, trans, id=None, name="Unnamed", description=None, **kwd ):
        if 'create_library' in kwd:
            library = trans.app.model.Library( name = name, description = description )
            root_folder = trans.app.model.LibraryFolder( name = name, description = description )
            root_folder.flush()
            library.root_folder = root_folder
            library.flush()
            trans.response.send_redirect( web.url_for( action='manage_folder', id = root_folder.id ) )
        elif id is None:
            return trans.show_form( 
                web.FormBuilder( action = web.url_for(), title = "Create a new Library", name = "create_library", submit_text = "Submit" )
                    .add_text( name = "name", label = "Name", value = "Unnamed", error = None, help = None )
                    .add_text( name = "description", label = "Description", value = None, error = None, help = None )
                    .add_input( 'hidden', "Create Library", 'create_library', use_label = False  ) )
        library = trans.app.model.Library.get( id )
        if library:
            return trans.fill_template( 'library/manage_library.mako', library = library )
        else:
            return trans.show_error_message( "Invalid library specified" )

    #make admin only
    @web.expose
    def manage_folder( self, trans, id=None, name="Unnamed", description=None, parent_id = None, **kwd ):
        if 'create_folder' in kwd:
            folder = trans.app.model.LibraryFolder( name = name, description = description )
            if parent_id:
                parent_folder = trans.app.model.LibraryFolder.get( parent_id )
                parent_folder.add_folder( folder )
            folder.flush()
            trans.response.send_redirect( web.url_for( action='manage_folder', id = folder.id ) )
        elif id is None:
            return trans.show_form( 
                web.FormBuilder( action = web.url_for(), title = "Create a new Folder", name = "create_folder", submit_text = "Submit" )
                    .add_text( name = "name", label = "Name", value = "Unnamed", error = None, help = None )
                    .add_text( name = "description", label = "Description", value = None, error = None, help = None )
                    .add_input( 'hidden', None, 'parent_id', value = parent_id, use_label = False  )
                    .add_input( 'hidden', "Create Folder", 'create_folder', use_label = False  ) )
        folder = trans.app.model.LibraryFolder.get( id )
        if folder:
            msg = ''
            if 'rename_folder' in kwd:
                folder.name = name
                folder.description = description
                folder.flush()
                msg = 'Folder has been renamed.'
            return trans.fill_template( 'library/manage_folder.mako', folder = folder, msg = msg )
        else:
            return trans.show_error_message( "Invalid folder specified" )


    #make admin only
    @web.expose
    def manage_dataset( self, trans, id=None, name="Unnamed", info = 'no info', extension = None, folder_id = None, dbkey = None, **kwd ):
        data_files = []
        def add_file( file_obj, name, extension, dbkey, info = 'no info', space_to_tab = False ):
            data_type = None
            temp_name = sniff.stream_to_file( file_obj )
            if space_to_tab:
                line_count = sniff.convert_newlines_sep2tabs( temp_name )
            else:
                line_count = sniff.convert_newlines( temp_name )
            if extension == 'auto':
                data_type = sniff.guess_ext( temp_name, sniff_order=trans.app.datatypes_registry.sniff_order )    
            else:
                data_type = extension
            dataset = trans.app.model.LibraryFolderDatasetAssociation( name = name, info = info, extension = data_type, dbkey = dbkey, create_dataset = True )
            folder = trans.app.model.LibraryFolder.get( folder_id )
            folder.add_dataset( dataset )
            dataset.flush()
            # TODO, SET SECURTY INTERACTIVELY ON DATASET, right now everything is public
            trans.app.security_agent.set_dataset_groups( dataset.dataset, [trans.app.security_agent.get_public_group()] )
            shutil.move( temp_name, dataset.dataset.file_name )
            dataset.dataset.state = dataset.dataset.states.OK
            dataset.init_meta()
            if line_count is not None:
                try:
                    dataset.set_peek( line_count=line_count )
                except:
                    dataset.set_peek()
            else:
                dataset.set_peek()
            dataset.set_size()

            if dataset.missing_meta():
                dataset.datatype.set_meta( dataset )
            trans.app.model.flush()

            return dataset
        if 'create_dataset' in kwd:
            #copied from upload tool action
            last_dataset_created = None
            data_file = kwd['file_data']
            url_paste = kwd['url_paste']
            space_to_tab = False 
            if 'space_to_tab' in kwd:
                if kwd['space_to_tab'] not in ["None", None]:
                    space_to_tab = True
            temp_name = ""
            data_list = []

            if 'filename' in dir( data_file ):
                file_name = data_file.filename
                file_name = file_name.split( '\\' )[-1]
                file_name = file_name.split( '/' )[-1]
                last_dataset_created = add_file( data_file.file, file_name, extension, dbkey, info="uploaded file", space_to_tab = space_to_tab )
            elif url_paste not in [ None, "" ]:
                if url_paste.lower().find( 'http://' ) >= 0 or url_paste.lower().find( 'ftp://' ) >= 0:
                    url_paste = url_paste.replace( '\r', '' ).split( '\n' )
                    for line in url_paste:
                        line = line.rstrip( '\r\n' )
                        if line:
                            last_dataset_created = add_file( urllib.urlopen( line ), line, extension, dbkey, info="uploaded url", space_to_tab=space_to_tab )
                else:
                    is_valid = False
                    for line in url_paste:
                        line = line.rstrip( '\r\n' )
                        if line:
                            is_valid = True
                            break
                    if is_valid:
                        last_dataset_created = add_file( StringIO.StringIO( url_paste ), 'Pasted Entry', extension, dbkey, info="pasted entry", space_to_tab=space_to_tab )
            trans.response.send_redirect( web.url_for( action='manage_dataset', id = last_dataset_created.id ) )
            #return self.manage_dataset( trans, id = last_dataset_created.id )
        elif id is None:
            return trans.fill_template( 'library/new_dataset.mako', folder_id = folder_id )
        dataset = trans.app.model.LibraryFolderDatasetAssociation.get( id )
        if dataset:
            #copied from edit attributes for 'regular' datasets
            p = util.Params(kwd, safe=False)
            if p.change:
                # The user clicked the Save button on the 'Change data type' form
                trans.app.datatypes_registry.change_datatype( dataset, p.datatype )
                trans.app.model.flush()
            elif p.save:
                # The user clicked the Save button on the 'Edit Attributes' form
                dataset.name  = name
                dataset.info  = info
                
                # The following for loop will save all metadata_spec items
                for name, spec in dataset.datatype.metadata_spec.items():
                    if spec.get("readonly"):
                        continue
                    optional = p.get("is_"+name, None)
                    if optional and optional == 'true':
                        # optional element... == 'true' actually means it is NOT checked (and therefore ommitted)
                        setattr(dataset.metadata,name,None)
                    else:
                        setattr(dataset.metadata,name,spec.unwrap(p.get(name, None), p))

                dataset.datatype.after_edit( dataset )
                trans.app.model.flush()
                return trans.show_ok_message( "Attributes updated" )
            elif p.detect:
                # The user clicked the Auto-detect button on the 'Edit Attributes' form
                for name, spec in dataset.datatype.metadata_spec.items():
                    # We need to be careful about the attributes we are resetting
                    if name != 'name' and name != 'info' and name != 'dbkey':
                        if spec.get( 'default' ):
                            setattr( dataset.metadata,name,spec.unwrap( spec.get( 'default' ), spec ))
                dataset.datatype.set_meta( dataset )
                dataset.datatype.after_edit( dataset )
                trans.app.model.flush()
                return trans.show_ok_message( "Attributes updated" )
            
            dataset.datatype.before_edit( dataset )
            
            if "dbkey" in dataset.datatype.metadata_spec and not dataset.metadata.dbkey:
                # Copy dbkey into metadata, for backwards compatability
                # This looks like it does nothing, but getting the dbkey
                # returns the metadata dbkey unless it is None, in which
                # case it resorts to the old dbkey.  Setting the dbkey
                # sets it properly in the metadata
                dataset.metadata.dbkey = dataset.dbkey
            metadata = list()
            # a list of MetadataParemeters
            for name, spec in dataset.datatype.metadata_spec.items():
                if spec.visible:
                    metadata.append( spec.wrap( dataset.metadata.get(name), dataset ) )
            # let's not overwrite the imported datatypes module with the variable datatypes?
            ldatatypes = [x for x in trans.app.datatypes_registry.datatypes_by_extension.iterkeys()]
            ldatatypes.sort()
            return trans.fill_template( "/library/manage_dataset.mako", dataset=dataset, metadata=metadata,
                                        datatypes=ldatatypes, err=None )
        else:
            return trans.show_error_message( "Invalid dataset specified" )
