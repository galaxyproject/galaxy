import os, shutil, urllib, StringIO, re, gzip, tempfile, shutil, zipfile
from . import ToolAction
from galaxy import datatypes, jobs
from galaxy.datatypes import sniff
from galaxy import model, util

import sys, traceback

import logging
log = logging.getLogger( __name__ )

class UploadToolAction( ToolAction ):
    # Action for uploading files
    def __init__( self ):
        self.empty = False
        self.line_count = None
    def remove_tempfile( self, filename ):
        try:
            os.unlink( filename )
        except:
            log.exception( 'failure removing temporary file: %s' % filename )
    def execute( self, tool, trans, incoming={}, set_output_hid = True ):
        dataset_upload_inputs = []
        for input_name, input in tool.inputs.iteritems():
            if input.type == "upload_dataset":
                dataset_upload_inputs.append( input )
        assert dataset_upload_inputs, Exception( "No dataset upload groups were found." )
        # Get any precreated datasets (when using asynchronous uploads)
        async_datasets = []
        self.precreated_datasets = []
        if incoming.get( 'async_datasets', None ) not in ["None", "", None]:
            async_datasets = incoming['async_datasets'].split(',')
        for id in async_datasets:
            try:
                data = trans.app.model.HistoryDatasetAssociation.get( int( id ) )
            except:
                log.exception( 'Unable to load precreated dataset (%s) sent in upload form' % id )
                continue
            if trans.user is None and trans.galaxy_session.current_history != data.history:
               log.error( 'Got a precreated dataset (%s) but it does not belong to anonymous user\'s current session (%s)' % ( data.id, trans.galaxy_session.id ) )
            elif data.history.user != trans.user:
               log.error( 'Got a precreated dataset (%s) but it does not belong to current user (%s)' % ( data.id, trans.user.id ) )
            else:
                self.precreated_datasets.append( data )
        data_list = []
        for dataset_upload_input in dataset_upload_inputs:
            uploaded_datasets = dataset_upload_input.get_uploaded_datasets( trans, incoming )
            for uploaded_dataset in uploaded_datasets:
                precreated_dataset = self.get_precreated_dataset( uploaded_dataset.precreated_name )
                dataset = self.add_file( trans, uploaded_dataset.primary_file, uploaded_dataset.name, uploaded_dataset.file_type, uploaded_dataset.is_multi_byte, uploaded_dataset.dbkey, space_to_tab = uploaded_dataset.space_to_tab, info = uploaded_dataset.info, precreated_dataset = precreated_dataset, metadata = uploaded_dataset.metadata, uploaded_dataset = uploaded_dataset )
                #dataset state is now set, we should not do anything else to this dataset
                data_list.append( dataset )
                #clean up extra temp names
                uploaded_dataset.clean_up_temp_files()
        
        #cleanup unclaimed precreated datasets:
        for data in self.precreated_datasets:
            log.info( 'Cleaned up unclaimed precreated dataset (%s).' % ( data.id ) )
            data.state = data.states.ERROR
            data.info = 'No file contents were available.'
        
        if data_list:
            trans.app.model.flush()
        
        # Create the job object
        job = trans.app.model.Job()
        job.session_id = trans.get_galaxy_session().id
        job.history_id = trans.history.id
        job.tool_id = tool.id
        try:
            # For backward compatibility, some tools may not have versions yet.
            job.tool_version = tool.version
        except:
            job.tool_version = "1.0.1"
        job.state = trans.app.model.Job.states.UPLOAD
        job.flush()
        log.info( 'tool %s created job id %d' % ( tool.id, job.id ) )
        trans.log_event( 'created job id %d' % job.id, tool_id=tool.id )
        
        #if we could make a 'real' job here, then metadata could be set before job.finish() is called
        hda = data_list[0] #only our first hda is being added as output for the job, why?
        job.state = trans.app.model.Job.states.OK
        file_size_str = datatypes.data.nice_size( hda.dataset.file_size )
        job.info = "%s, size: %s" % ( hda.info, file_size_str )
        job.add_output_dataset( hda.name, hda )
        job.flush()
        log.info( 'job id %d ended ok, file size: %s' % ( job.id, file_size_str ) )
        trans.log_event( 'job id %d ended ok, file size: %s' % ( job.id, file_size_str ), tool_id=tool.id )
        return dict( output=hda )
        
    def upload_empty(self, trans, job, err_code, err_msg, precreated_dataset = None):
        if precreated_dataset is not None:
            data = precreated_dataset
        else:
            data = trans.app.model.HistoryDatasetAssociation( create_dataset=True )
        trans.app.security_agent.set_all_dataset_permissions( data.dataset, trans.app.security_agent.history_get_default_permissions( trans.history ) )
        data.name = err_code
        data.extension = "txt"
        data.dbkey = "?"
        data.info = err_msg
        data.file_size = 0
        data.state = data.states.EMPTY
        data.flush()
        if precreated_dataset is None:
            trans.history.add_dataset( data )
        trans.app.model.flush()
        # Indicate job failure by setting state and info
        job.state = trans.app.model.Job.states.ERROR
        job.info = err_msg
        job.add_output_dataset( data.name, data )
        job.flush()
        log.info( 'job id %d ended with errors, err_msg: %s' % ( job.id, err_msg ) )
        trans.log_event( 'job id %d ended with errors, err_msg: %s' % ( job.id, err_msg ), tool_id=job.tool_id )
        return dict( output=data )

    def add_file( self, trans, temp_name, file_name, file_type, is_multi_byte, dbkey, info=None, space_to_tab=False, precreated_dataset=None, metadata = {}, uploaded_dataset = None ):
        def dataset_no_data_error( data, message = 'there was an error uploading your file' ):
            data.info = "No data: %s." % message
            data.state = data.states.ERROR
            if data.extension is None:
                data.extension = 'data'
            return data
        data_type = None
        
        if precreated_dataset is not None:
            data = precreated_dataset
        else:
            data = trans.app.model.HistoryDatasetAssociation( history = trans.history, create_dataset = True )
        trans.app.security_agent.set_all_dataset_permissions( data.dataset, trans.app.security_agent.history_get_default_permissions( trans.history ) )
        
        # See if we have an empty file
        if not os.path.getsize( temp_name ) > 0:
            return dataset_no_data_error( data, message = 'you attempted to upload an empty file' )
            #raise BadFileException( "you attempted to upload an empty file." )
        if is_multi_byte:
            ext = sniff.guess_ext( temp_name, is_multi_byte=True )
        else:
            if not data_type: #at this point data_type is always None (just initialized above), so this is always True...lots of cleanup needed here
                # See if we have a gzipped file, which, if it passes our restrictions,
                # we'll decompress on the fly.
                is_gzipped, is_valid = self.check_gzip( temp_name )
                if is_gzipped and not is_valid:
                    return dataset_no_data_error( data, message = 'you attempted to upload an inappropriate file' )
                    #raise BadFileException( "you attempted to upload an inappropriate file." )
                elif is_gzipped and is_valid:
                    # We need to uncompress the temp_name file
                    CHUNK_SIZE = 2**20 # 1Mb   
                    fd, uncompressed = tempfile.mkstemp()   
                    gzipped_file = gzip.GzipFile( temp_name )
                    while 1:
                        try:
                            chunk = gzipped_file.read( CHUNK_SIZE )
                        except IOError:
                            os.close( fd )
                            os.remove( uncompressed )
                            return dataset_no_data_error( data, message = 'problem decompressing gzipped data' )
                            #raise BadFileException( 'problem decompressing gzipped data.' )
                        if not chunk:
                            break
                        os.write( fd, chunk )
                    os.close( fd )
                    gzipped_file.close()
                    # Replace the gzipped file with the decompressed file
                    shutil.move( uncompressed, temp_name )
                    file_name = file_name.rstrip( '.gz' )
                    data_type = 'gzip'
                ext = ''
                if not data_type:
                    # See if we have a zip archive
                    is_zipped, is_valid, test_ext = self.check_zip( temp_name )
                    if is_zipped and not is_valid:
                        return dataset_no_data_error( data, message = 'you attempted to upload an inappropriate file' )
                        #raise BadFileException( "you attempted to upload an inappropriate file." )
                    elif is_zipped and is_valid:
                        # Currently, we force specific tools to handle this case.  We also require the user
                        # to manually set the incoming file_type
                        if ( test_ext == 'ab1' or test_ext == 'scf' ) and file_type != 'binseq.zip':
                            return dataset_no_data_error( data, message = "Invalid 'File Format' for archive consisting of binary files - use 'Binseq.zip'" )
                            #raise BadFileException( "Invalid 'File Format' for archive consisting of binary files - use 'Binseq.zip'." )
                        elif test_ext == 'txt' and file_type != 'txtseq.zip':
                            return dataset_no_data_error( data, message = "Invalid 'File Format' for archive consisting of text files - use 'Txtseq.zip'" )
                            #raise BadFileException( "Invalid 'File Format' for archive consisting of text files - use 'Txtseq.zip'." )
                        if not ( file_type == 'binseq.zip' or file_type == 'txtseq.zip' ):
                            return dataset_no_data_error( data, message = "you must manually set the 'File Format' to either 'Binseq.zip' or 'Txtseq.zip' when uploading zip files" )
                            #raise BadFileException( "you must manually set the 'File Format' to either 'Binseq.zip' or 'Txtseq.zip' when uploading zip files." )
                        data_type = 'zip'
                        ext = file_type
                if not data_type:
                    if self.check_binary( temp_name ):
                        if uploaded_dataset and uploaded_dataset.datatype and uploaded_dataset.datatype.is_binary:
                            #we need a more generalized way of checking if a binary upload is of the right format for a datatype...magic number, etc
                            data_type = 'binary'
                            ext = uploaded_dataset.file_type
                        else:
                            parts = file_name.split( "." )
                            if len( parts ) > 1:
                                ext = parts[1].strip().lower()
                                if not( ext == 'ab1' or ext == 'scf' ):
                                    return dataset_no_data_error( data, message = "you attempted to upload an inappropriate file" )
                                    #raise BadFileException( "you attempted to upload an inappropriate file." )
                                if ext == 'ab1' and file_type != 'ab1':
                                    return dataset_no_data_error( data, message = "you must manually set the 'File Format' to 'Ab1' when uploading ab1 files" )
                                    #raise BadFileException( "you must manually set the 'File Format' to 'Ab1' when uploading ab1 files." )
                                elif ext == 'scf' and file_type != 'scf':
                                    return dataset_no_data_error( data, message = "you must manually set the 'File Format' to 'Scf' when uploading scf files" )
                                    #raise BadFileException( "you must manually set the 'File Format' to 'Scf' when uploading scf files." )
                            data_type = 'binary'
                if not data_type:
                    # We must have a text file
                    if trans.app.datatypes_registry.get_datatype_by_extension( file_type ).composite_type != 'auto_primary_file' and self.check_html( temp_name ):
                        return dataset_no_data_error( data, message = "you attempted to upload an inappropriate file" )
                        #raise BadFileException( "you attempted to upload an inappropriate file." )
                #if data_type != 'binary' and data_type != 'zip' and not trans.app.datatypes_registry.get_datatype_by_extension( ext ).is_binary:
                if data_type != 'binary' and data_type != 'zip':
                    if space_to_tab:
                        self.line_count = sniff.convert_newlines_sep2tabs( temp_name )
                    else:
                        self.line_count = sniff.convert_newlines( temp_name )
                    if file_type == 'auto':
                        ext = sniff.guess_ext( temp_name, sniff_order=trans.app.datatypes_registry.sniff_order )    
                    else:
                        ext = file_type
                    data_type = ext
        if info is None:
            info = 'uploaded %s file' %data_type
        data.extension = ext
        data.name = file_name
        data.dbkey = dbkey
        data.info = info
        data.flush()
        shutil.move( temp_name, data.file_name )
        dataset_state = data.states.OK #don't set actual state here, only set to OK when finished setting attributes of the dataset
        data.set_size()
        data.init_meta()
        #need to set metadata, has to be done after extention is set
        for meta_name, meta_value in metadata.iteritems():
            setattr( data.metadata, meta_name, meta_value )
        if self.line_count is not None:
            try:
                if is_multi_byte:
                    data.set_multi_byte_peek( line_count=self.line_count )
                else:
                    data.set_peek( line_count=self.line_count )
            except:
                if is_multi_byte:
                    data.set_multi_byte_peek()
                else:
                    data.set_peek()
        else:
            if is_multi_byte:
                data.set_multi_byte_peek()
            else:
                data.set_peek()

        # validate incomming data
        # Commented by greg on 3/14/07
        # for error in data.datatype.validate( data ):
        #     data.add_validation_error( 
        #         model.ValidationError( message=str( error ), err_type=error.__class__.__name__, attributes=util.object_to_string( error.__dict__ ) ) )
        if data.missing_meta():
            data.datatype.set_meta( data )
        dbkey_to_store = dbkey
        if type( dbkey_to_store ) == type( [] ):
            dbkey_to_store = dbkey[0]
        if precreated_dataset is not None:
            trans.history.genome_build = dbkey_to_store
        else:
            trans.history.add_dataset( data, genome_build=dbkey_to_store )
        #set up composite files
        if uploaded_dataset is not None:
            composite_files = data.datatype.get_composite_files( data )
            if composite_files:
                os.mkdir( data.extra_files_path ) #make extra files path
                for name, value in composite_files.iteritems():
                    if uploaded_dataset.composite_files[ value.name ] is None and not value.optional:
                        data.info = "A required composite data file was not provided (%s)" % name
                        dataset_state = data.states.ERROR
                        break
                    elif uploaded_dataset.composite_files[ value.name] is not None:
                        if not value.is_binary:
                            if uploaded_dataset.composite_files[ value.name ].space_to_tab:
                                sniff.convert_newlines_sep2tabs( uploaded_dataset.composite_files[ value.name ].filename )
                            else:
                                sniff.convert_newlines( uploaded_dataset.composite_files[ value.name ].filename )
                        shutil.move( uploaded_dataset.composite_files[ value.name ].filename, os.path.join( data.extra_files_path, name ) )
            if data.datatype.composite_type == 'auto_primary_file':
               #now that metadata was set above, we should create the primary file as required
               open( data.file_name, 'wb+' ).write( data.datatype.generate_primary_file( dataset = data ) )
        data.state = dataset_state #Always set dataset state LAST
        trans.app.model.flush()
        trans.log_event( "Added dataset %d to history %d" %( data.id, trans.history.id ), tool_id="upload" )
        return data

    def check_gzip( self, temp_name ):
        temp = open( temp_name, "U" )
        magic_check = temp.read( 2 )
        temp.close()
        if magic_check != util.gzip_magic:
            return ( False, False )
        CHUNK_SIZE = 2**15 # 32Kb
        gzipped_file = gzip.GzipFile( temp_name )
        chunk = gzipped_file.read( CHUNK_SIZE )
        gzipped_file.close()
        if self.check_html( temp_name, chunk=chunk ) or self.check_binary( temp_name, chunk=chunk ):
            return( True, False )
        return ( True, True )

    def check_zip( self, temp_name ):
        if not zipfile.is_zipfile( temp_name ):
            return ( False, False, None )
        zip_file = zipfile.ZipFile( temp_name, "r" )
        # Make sure the archive consists of valid files.  The current rules are:
        # 1. Archives can only include .ab1, .scf or .txt files
        # 2. All file extensions within an archive must be the same
        name = zip_file.namelist()[0]
        test_ext = name.split( "." )[1].strip().lower()
        if not ( test_ext == 'scf' or test_ext == 'ab1' or test_ext == 'txt' ):
            return ( True, False, test_ext )
        for name in zip_file.namelist():
            ext = name.split( "." )[1].strip().lower()
            if ext != test_ext:
                return ( True, False, test_ext )
        return ( True, True, test_ext )

    def check_html( self, temp_name, chunk=None ):
        if chunk is None:
            temp = open(temp_name, "U")
        else:
            temp = chunk
        regexp1 = re.compile( "<A\s+[^>]*HREF[^>]+>", re.I )
        regexp2 = re.compile( "<IFRAME[^>]*>", re.I )
        regexp3 = re.compile( "<FRAMESET[^>]*>", re.I )
        regexp4 = re.compile( "<META[^>]*>", re.I )
        lineno = 0
        for line in temp:
            lineno += 1
            matches = regexp1.search( line ) or regexp2.search( line ) or regexp3.search( line ) or regexp4.search( line )
            if matches:
                if chunk is None:
                    temp.close()
                return True
            if lineno > 100:
                break
        if chunk is None:
            temp.close()
        return False
    def check_binary( self, temp_name, chunk=None ):
        if chunk is None:
            temp = open( temp_name, "U" )
        else:
            temp = chunk
        lineno = 0
        for line in temp:
            lineno += 1
            line = line.strip()
            if line:
                if util.is_multi_byte( line ):
                    return False
                for char in line:
                    if ord( char ) > 128:
                        if chunk is None:
                            temp.close()
                        return True
            if lineno > 10:
                break
        if chunk is None:
            temp.close()
        return False

    def get_precreated_dataset( self, name ):
        """
        Return a dataset matching a name from the list of precreated (via async
        upload) datasets. If there's more than one upload with the exact same
        name, we need to pop one (the first) so it isn't chosen next time.
        """
        names = [ d.name for d in self.precreated_datasets ]
        if names.count( name ) > 0:
            return self.precreated_datasets.pop( names.index( name ) )
        else:
            return None

class BadFileException( Exception ):
    pass

