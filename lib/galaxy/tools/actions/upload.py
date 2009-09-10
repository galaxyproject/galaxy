import os, shutil, urllib, StringIO, re, gzip, tempfile, shutil, zipfile
from cgi import FieldStorage
from __init__ import ToolAction
from galaxy import datatypes, jobs
from galaxy.datatypes import sniff
from galaxy import model, util
from galaxy.util.json import to_json_string

import sys, traceback

import logging
log = logging.getLogger( __name__ )

class UploadToolAction( ToolAction ):
    # Action for uploading files
    def persist_uploads( self, incoming ):
        if 'files' in incoming:
            new_files = []
            temp_files = []
            for upload_dataset in incoming['files']:
                f = upload_dataset['file_data']
                if isinstance( f, FieldStorage ): 
                    assert not isinstance( f.file, StringIO.StringIO )
                    assert f.file.name != '<fdopen>'
                    local_filename = util.mkstemp_ln( f.file.name, 'upload_file_data_' )
                    f.file.close()
                    upload_dataset['file_data'] = dict( filename = f.filename,
                                                        local_filename = local_filename )
                if upload_dataset['url_paste'].strip() != '':
                    upload_dataset['url_paste'] = datatypes.sniff.stream_to_file( StringIO.StringIO( upload_dataset['url_paste'] ), prefix="strio_url_paste_" )[0]
                else:
                    upload_dataset['url_paste'] = None
                new_files.append( upload_dataset )
            incoming['files'] = new_files
        return incoming
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

        incoming = self.persist_uploads( incoming )

        json_file = tempfile.mkstemp()
        json_file_path = json_file[1]
        json_file = os.fdopen( json_file[0], 'w' )
        for dataset_upload_input in dataset_upload_inputs:
            uploaded_datasets = dataset_upload_input.get_uploaded_datasets( trans, incoming )
            for uploaded_dataset in uploaded_datasets:
                data = self.get_precreated_dataset( uploaded_dataset.name )
                if not data:
                    data = trans.app.model.HistoryDatasetAssociation( history = trans.history, create_dataset = True )
                    data.name = uploaded_dataset.name
                    data.state = data.states.QUEUED
                    data.extension = uploaded_dataset.file_type
                    data.dbkey = uploaded_dataset.dbkey
                    data.flush()
                    trans.history.add_dataset( data, genome_build = uploaded_dataset.dbkey )
                    permissions = trans.app.security_agent.history_get_default_permissions( trans.history )
                    trans.app.security_agent.set_all_dataset_permissions( data.dataset, permissions )
                else:
                    data.extension = uploaded_dataset.file_type
                    data.dbkey = uploaded_dataset.dbkey
                    data.flush()
                    trans.history.genome_build = uploaded_dataset.dbkey
                if uploaded_dataset.type == 'composite':
                    # we need to init metadata before the job is dispatched
                    data.init_meta()
                    for meta_name, meta_value in uploaded_dataset.metadata.iteritems():
                        setattr( data.metadata, meta_name, meta_value )
                    data.flush()
                    json = dict( file_type = uploaded_dataset.file_type,
                                 dataset_id = data.dataset.id,
                                 dbkey = uploaded_dataset.dbkey,
                                 type = uploaded_dataset.type,
                                 metadata = uploaded_dataset.metadata,
                                 primary_file = uploaded_dataset.primary_file,
                                 extra_files_path = data.extra_files_path,
                                 composite_file_paths = uploaded_dataset.composite_files,
                                 composite_files = dict( [ ( k, v.__dict__ ) for k, v in data.datatype.get_composite_files( data ).items() ] ) )
                else:
                    try:
                        is_binary = uploaded_dataset.datatype.is_binary
                    except:
                        is_binary = None
                    json = dict( file_type = uploaded_dataset.file_type,
                                 ext = uploaded_dataset.ext,
                                 name = uploaded_dataset.name,
                                 dataset_id = data.dataset.id,
                                 dbkey = uploaded_dataset.dbkey,
                                 type = uploaded_dataset.type,
                                 is_binary = is_binary,
                                 space_to_tab = uploaded_dataset.space_to_tab,
                                 path = uploaded_dataset.path )
                json_file.write( to_json_string( json ) + '\n' )
                data_list.append( data )
        json_file.close()

        #cleanup unclaimed precreated datasets:
        for data in self.precreated_datasets:
            log.info( 'Cleaned up unclaimed precreated dataset (%s).' % ( data.id ) )
            data.state = data.states.ERROR
            data.info = 'No file contents were available.'
        
        if not data_list:
            try:
                os.remove( json_file_path )
            except:
                pass
            return 'No data was entered in the upload form, please go back and choose data to upload.'
        
        # Create the job object
        job = trans.app.model.Job()
        job.session_id = trans.get_galaxy_session().id
        job.history_id = trans.history.id
        job.tool_id = tool.id
        job.tool_version = tool.version
        job.state = trans.app.model.Job.states.UPLOAD
        job.flush()
        log.info( 'tool %s created job id %d' % ( tool.id, job.id ) )
        trans.log_event( 'created job id %d' % job.id, tool_id=tool.id )

        for name, value in tool.params_to_strings( incoming, trans.app ).iteritems():
            job.add_parameter( name, value )
        job.add_parameter( 'paramfile', to_json_string( json_file_path ) )
        for i, dataset in enumerate( data_list ):
            job.add_output_dataset( 'output%i' % i, dataset )
        job.state = trans.app.model.Job.states.NEW
        trans.app.model.flush()
        
        # Queue the job for execution
        trans.app.job_queue.put( job.id, tool )
        trans.log_event( "Added job to the job queue, id: %s" % str(job.id), tool_id=job.tool_id )
        return dict( [ ( i, v ) for i, v in enumerate( data_list ) ] )

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
