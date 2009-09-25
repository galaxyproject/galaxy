import os, tempfile, StringIO
from cgi import FieldStorage
from galaxy import datatypes, util
from galaxy.datatypes import sniff
from galaxy.util.json import to_json_string

import logging
log = logging.getLogger( __name__ )

def persist_uploads( params ):
    """
    Turn any uploads in the submitted form to persisted files.
    """
    if 'files' in params:
        new_files = []
        temp_files = []
        for upload_dataset in params['files']:
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
        params['files'] = new_files
    return params

def get_precreated_datasets( trans, params, data_obj ):
    """
    Get any precreated datasets (when using asynchronous uploads).
    """
    rval = []
    async_datasets = []
    if params.get( 'async_datasets', None ) not in ["None", "", None]:
        async_datasets = params['async_datasets'].split(',')
    user, roles = trans.get_user_and_roles()
    for id in async_datasets:
        try:
            data = data_obj.get( int( id ) )
        except:
            log.exception( 'Unable to load precreated dataset (%s) sent in upload form' % id )
            continue
        if data_obj is trans.app.model.HistoryDatasetAssociation:
            if user is None and trans.galaxy_session.current_history != data.history:
                log.error( 'Got a precreated dataset (%s) but it does not belong to anonymous user\'s current session (%s)' % ( data.id, trans.galaxy_session.id ) )
            elif data.history.user != user:
                log.error( 'Got a precreated dataset (%s) but it does not belong to current user (%s)' % ( data.id, user.id ) )
            else:
                rval.append( data )
        elif data_obj is trans.app.model.LibraryDatasetDatasetAssociation:
            if not trans.app.security_agent.can_add_library_item( user, roles, data.library_dataset.folder ):
                log.error( 'Got a precreated dataset (%s) but this user (%s) is not allowed to write to it' % ( data.id, user.id ) )
            else:
                rval.append( data )
    return rval

def get_precreated_dataset( precreated_datasets, name ):
    """
    Return a dataset matching a name from the list of precreated (via async
    upload) datasets. If there's more than one upload with the exact same
    name, we need to pop one (the first) so it isn't chosen next time.
    """
    names = [ d.name for d in precreated_datasets ]
    if names.count( name ) > 0:
        return precreated_datasets.pop( names.index( name ) )
    else:
        return None

def cleanup_unused_precreated_datasets( precreated_datasets ):
    for data in precreated_datasets:
        log.info( 'Cleaned up unclaimed precreated dataset (%s).' % ( data.id ) )
        data.state = data.states.ERROR
        data.info = 'No file contents were available.'

def new_history_upload( trans, uploaded_dataset ):
    hda = trans.app.model.HistoryDatasetAssociation( name = uploaded_dataset.name,
                                                     extension = uploaded_dataset.file_type,
                                                     dbkey = uploaded_dataset.dbkey, 
                                                     history = trans.history,
                                                     create_dataset = True )
    hda.state = hda.states.QUEUED
    hda.flush()
    trans.history.add_dataset( hda, genome_build = uploaded_dataset.dbkey )
    permissions = trans.app.security_agent.history_get_default_permissions( trans.history )
    trans.app.security_agent.set_all_dataset_permissions( hda.dataset, permissions )
    return hda

def new_library_upload( trans, uploaded_dataset, replace_dataset, folder,
                        template, template_field_contents, roles, message ):
    if replace_dataset:
        ld = replace_dataset
    else:
        ld = trans.app.model.LibraryDataset( folder=folder, name=uploaded_dataset.name )
        ld.flush()
        trans.app.security_agent.copy_library_permissions( folder, ld )
    ldda = trans.app.model.LibraryDatasetDatasetAssociation( name = uploaded_dataset.name,
                                                             extension = uploaded_dataset.file_type,
                                                             dbkey = uploaded_dataset.dbkey,
                                                             library_dataset = ld,
                                                             user = trans.user,
                                                             create_dataset = True )
    ldda.state = ldda.states.QUEUED
    ldda.message = message
    ldda.flush()
    # Permissions must be the same on the LibraryDatasetDatasetAssociation and the associated LibraryDataset
    trans.app.security_agent.copy_library_permissions( ld, ldda )
    if replace_dataset:
        # Copy the Dataset level permissions from replace_dataset to the new LibraryDatasetDatasetAssociation.dataset
        trans.app.security_agent.copy_dataset_permissions( replace_dataset.library_dataset_dataset_association.dataset, ldda.dataset )
    else:
        # Copy the current user's DefaultUserPermissions to the new LibraryDatasetDatasetAssociation.dataset
        trans.app.security_agent.set_all_dataset_permissions( ldda.dataset, trans.app.security_agent.user_get_default_permissions( trans.user ) )
        folder.add_library_dataset( ld, genome_build=uploaded_dataset.dbkey )
        folder.flush()
    ld.library_dataset_dataset_association_id = ldda.id
    ld.flush()
    # Handle template included in the upload form, if any
    if template and template_field_contents:
        # Since information templates are inherited, the template fields can be displayed on the upload form.
        # If the user has added field contents, we'll need to create a new form_values and info_association
        # for the new library_dataset_dataset_association object.
        # Create a new FormValues object, using the template we previously retrieved
        form_values = trans.app.model.FormValues( template, template_field_contents )
        form_values.flush()
        # Create a new info_association between the current ldda and form_values
        info_association = trans.app.model.LibraryDatasetDatasetInfoAssociation( ldda, template, form_values )
        info_association.flush()
    # If roles were selected upon upload, restrict access to the Dataset to those roles
    if roles:
        for role in roles:
            dp = trans.app.model.DatasetPermissions( trans.app.security_agent.permitted_actions.DATASET_ACCESS.action, ldda.dataset, role )
            dp.flush()
    return ldda

def create_paramfile( trans, params, precreated_datasets, dataset_upload_inputs,
                      replace_dataset=None, folder=None, template=None,
                      template_field_contents=None, roles=None, message=None ):
    """
    Create the upload tool's JSON "param" file.
    """
    data_list = []
    json_file = tempfile.mkstemp()
    json_file_path = json_file[1]
    json_file = os.fdopen( json_file[0], 'w' )
    for dataset_upload_input in dataset_upload_inputs:
        uploaded_datasets = dataset_upload_input.get_uploaded_datasets( trans, params )
        for uploaded_dataset in uploaded_datasets:
            data = get_precreated_dataset( precreated_datasets, uploaded_dataset.name )
            if not data:
                if folder:
                    data = new_library_upload( trans, uploaded_dataset, replace_dataset, folder, template, template_field_contents, roles, message )
                else:
                    data = new_history_upload( trans, uploaded_dataset )
            else:
                data.extension = uploaded_dataset.file_type
                data.dbkey = uploaded_dataset.dbkey
                data.flush()
                if folder:
                    folder.genome_build = uploaded_dataset.dbkey
                    folder.flush()
                else:
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
    return ( json_file_path, data_list )

def create_job( trans, params, tool, json_file_path, data_list, folder=None ):
    """
    Create the upload job.
    """
    job = trans.app.model.Job()
    job.session_id = trans.get_galaxy_session().id
    if folder:
        job.library_folder_id = folder.id
    else:
        job.history_id = trans.history.id
    job.tool_id = tool.id
    job.tool_version = tool.version
    job.state = job.states.UPLOAD
    job.flush()
    log.info( 'tool %s created job id %d' % ( tool.id, job.id ) )
    trans.log_event( 'created job id %d' % job.id, tool_id=tool.id )

    for name, value in tool.params_to_strings( params, trans.app ).iteritems():
        job.add_parameter( name, value )
    job.add_parameter( 'paramfile', to_json_string( json_file_path ) )
    if folder:
        for i, dataset in enumerate( data_list ):
            job.add_output_library_dataset( 'output%i' % i, dataset )
    else:
        for i, dataset in enumerate( data_list ):
            job.add_output_dataset( 'output%i' % i, dataset )
    job.state = job.states.NEW
    trans.app.model.flush()

    # Queue the job for execution
    trans.app.job_queue.put( job.id, tool )
    trans.log_event( "Added job to the job queue, id: %s" % str(job.id), tool_id=job.tool_id )
    return dict( [ ( 'output%i' % i, v ) for i, v in enumerate( data_list ) ] )
