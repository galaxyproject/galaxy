import os
import tempfile
import StringIO
import pwd
import subprocess
from cgi import FieldStorage
from galaxy import datatypes, util
from galaxy.util.odict import odict
from galaxy.datatypes import sniff
from galaxy.util.json import dumps
from galaxy.model.orm import eagerload_all
from galaxy.exceptions import ObjectInvalid

import logging
log = logging.getLogger( __name__ )


def persist_uploads( params ):
    """
    Turn any uploads in the submitted form to persisted files.
    """
    if 'files' in params:
        new_files = []
        for upload_dataset in params['files']:
            f = upload_dataset['file_data']
            if isinstance( f, FieldStorage ):
                assert not isinstance( f.file, StringIO.StringIO )
                assert f.file.name != '<fdopen>'
                local_filename = util.mkstemp_ln( f.file.name, 'upload_file_data_' )
                f.file.close()
                upload_dataset['file_data'] = dict( filename=f.filename,
                                                    local_filename=local_filename )
            elif type( f ) == dict and 'filename' and 'local_filename' not in f:
                raise Exception( 'Uploaded file was encoded in a way not understood by Galaxy.' )
            if upload_dataset['url_paste'] and upload_dataset['url_paste'].strip() != '':
                upload_dataset['url_paste'], is_multi_byte = datatypes.sniff.stream_to_file( StringIO.StringIO( upload_dataset['url_paste'] ), prefix="strio_url_paste_" )
            else:
                upload_dataset['url_paste'] = None
            new_files.append( upload_dataset )
        params['files'] = new_files
    return params


def handle_library_params( trans, params, folder_id, replace_dataset=None ):
    # FIXME: the received params has already been parsed by util.Params() by the time it reaches here,
    # so no complex objects remain.  This is not good because it does not allow for those objects to be
    # manipulated here.  The received params should be the original kwd from the initial request.
    library_bunch = util.bunch.Bunch()
    library_bunch.replace_dataset = replace_dataset
    library_bunch.message = params.get( 'ldda_message', '' )
    # See if we have any template field contents
    library_bunch.template_field_contents = {}
    template_id = params.get( 'template_id', None )
    library_bunch.folder = trans.sa_session.query( trans.app.model.LibraryFolder ).get( trans.security.decode_id( folder_id ) )
    # We are inheriting the folder's info_association, so we may have received inherited contents or we may have redirected
    # here after the user entered template contents ( due to errors ).
    if template_id not in [ None, 'None' ]:
        library_bunch.template = trans.sa_session.query( trans.app.model.FormDefinition ).get( template_id )
        for field in library_bunch.template.fields:
            field_name = field[ 'name' ]
            if params.get( field_name, False ):
                field_value = util.restore_text( params.get( field_name, ''  ) )
                library_bunch.template_field_contents[ field_name ] = field_value
    else:
        library_bunch.template = None
    library_bunch.roles = []
    for role_id in util.listify( params.get( 'roles', [] ) ):
        role = trans.sa_session.query( trans.app.model.Role ).get( role_id )
        library_bunch.roles.append( role )
    return library_bunch


def get_precreated_datasets( trans, params, data_obj, controller='root' ):
    """
    Get any precreated datasets (when using asynchronous uploads).
    """
    rval = []
    async_datasets = []
    if params.get( 'async_datasets', None ) not in ["None", "", None]:
        async_datasets = params['async_datasets'].split(',')
    current_user_roles = trans.get_current_user_roles()
    for id in async_datasets:
        try:
            data = trans.sa_session.query( data_obj ).get( int( id ) )
        except:
            log.exception( 'Unable to load precreated dataset (%s) sent in upload form' % id )
            continue
        if data_obj is trans.app.model.HistoryDatasetAssociation:
            if trans.user is None and trans.galaxy_session.current_history != data.history:
                log.error( 'Got a precreated dataset (%s) but it does not belong to anonymous user\'s current session (%s)' % ( data.id, trans.galaxy_session.id ) )
            elif data.history.user != trans.user:
                log.error( 'Got a precreated dataset (%s) but it does not belong to current user (%s)' % ( data.id, trans.user.id ) )
            else:
                rval.append( data )
        elif data_obj is trans.app.model.LibraryDatasetDatasetAssociation:
            if controller == 'library' and not trans.app.security_agent.can_add_library_item( current_user_roles, data.library_dataset.folder ):
                log.error( 'Got a precreated dataset (%s) but this user (%s) is not allowed to write to it' % ( data.id, trans.user.id ) )
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


def __new_history_upload( trans, uploaded_dataset, history=None, state=None ):
    if not history:
        history = trans.history
    hda = trans.app.model.HistoryDatasetAssociation( name=uploaded_dataset.name,
                                                     extension=uploaded_dataset.file_type,
                                                     dbkey=uploaded_dataset.dbkey,
                                                     history=history,
                                                     create_dataset=True,
                                                     sa_session=trans.sa_session )
    if state:
        hda.state = state
    else:
        hda.state = hda.states.QUEUED
    trans.sa_session.add( hda )
    trans.sa_session.flush()
    history.add_dataset( hda, genome_build=uploaded_dataset.dbkey )
    permissions = trans.app.security_agent.history_get_default_permissions( history )
    trans.app.security_agent.set_all_dataset_permissions( hda.dataset, permissions )
    trans.sa_session.flush()
    return hda


def __new_library_upload( trans, cntrller, uploaded_dataset, library_bunch, state=None ):
    current_user_roles = trans.get_current_user_roles()
    if not ( ( trans.user_is_admin() and cntrller in [ 'library_admin', 'api' ] ) or trans.app.security_agent.can_add_library_item( current_user_roles, library_bunch.folder ) ):
        # This doesn't have to be pretty - the only time this should happen is if someone's being malicious.
        raise Exception( "User is not authorized to add datasets to this library." )
    folder = library_bunch.folder
    if uploaded_dataset.get( 'in_folder', False ):
        # Create subfolders if desired
        for name in uploaded_dataset.in_folder.split( os.path.sep ):
            trans.sa_session.refresh( folder )
            matches = filter( lambda x: x.name == name, active_folders( trans, folder ) )
            if matches:
                folder = matches[0]
            else:
                new_folder = trans.app.model.LibraryFolder( name=name, description='Automatically created by upload tool' )
                new_folder.genome_build = trans.app.genome_builds.default_value
                folder.add_folder( new_folder )
                trans.sa_session.add( new_folder )
                trans.sa_session.flush()
                trans.app.security_agent.copy_library_permissions( trans, folder, new_folder )
                folder = new_folder
    if library_bunch.replace_dataset:
        ld = library_bunch.replace_dataset
    else:
        ld = trans.app.model.LibraryDataset( folder=folder, name=uploaded_dataset.name )
        trans.sa_session.add( ld )
        trans.sa_session.flush()
        trans.app.security_agent.copy_library_permissions( trans, folder, ld )
    ldda = trans.app.model.LibraryDatasetDatasetAssociation( name=uploaded_dataset.name,
                                                             extension=uploaded_dataset.file_type,
                                                             dbkey=uploaded_dataset.dbkey,
                                                             library_dataset=ld,
                                                             user=trans.user,
                                                             create_dataset=True,
                                                             sa_session=trans.sa_session )
    trans.sa_session.add( ldda )
    if state:
        ldda.state = state
    else:
        ldda.state = ldda.states.QUEUED
    ldda.message = library_bunch.message
    trans.sa_session.flush()
    # Permissions must be the same on the LibraryDatasetDatasetAssociation and the associated LibraryDataset
    trans.app.security_agent.copy_library_permissions( trans, ld, ldda )
    if library_bunch.replace_dataset:
        # Copy the Dataset level permissions from replace_dataset to the new LibraryDatasetDatasetAssociation.dataset
        trans.app.security_agent.copy_dataset_permissions( library_bunch.replace_dataset.library_dataset_dataset_association.dataset, ldda.dataset )
    else:
        # Copy the current user's DefaultUserPermissions to the new LibraryDatasetDatasetAssociation.dataset
        trans.app.security_agent.set_all_dataset_permissions( ldda.dataset, trans.app.security_agent.user_get_default_permissions( trans.user ) )
        folder.add_library_dataset( ld, genome_build=uploaded_dataset.dbkey )
        trans.sa_session.add( folder )
        trans.sa_session.flush()
    ld.library_dataset_dataset_association_id = ldda.id
    trans.sa_session.add( ld )
    trans.sa_session.flush()
    # Handle template included in the upload form, if any.  If the upload is not asynchronous ( e.g., URL paste ),
    # then the template and contents will be included in the library_bunch at this point.  If the upload is
    # asynchronous ( e.g., uploading a file ), then the template and contents will be included in the library_bunch
    # in the get_uploaded_datasets() method below.
    if library_bunch.template and library_bunch.template_field_contents:
        # Since information templates are inherited, the template fields can be displayed on the upload form.
        # If the user has added field contents, we'll need to create a new form_values and info_association
        # for the new library_dataset_dataset_association object.
        # Create a new FormValues object, using the template we previously retrieved
        form_values = trans.app.model.FormValues( library_bunch.template, library_bunch.template_field_contents )
        trans.sa_session.add( form_values )
        trans.sa_session.flush()
        # Create a new info_association between the current ldda and form_values
        # TODO: Currently info_associations at the ldda level are not inheritable to the associated LibraryDataset,
        # we need to figure out if this is optimal
        info_association = trans.app.model.LibraryDatasetDatasetInfoAssociation( ldda, library_bunch.template, form_values )
        trans.sa_session.add( info_association )
        trans.sa_session.flush()
    # If roles were selected upon upload, restrict access to the Dataset to those roles
    if library_bunch.roles:
        for role in library_bunch.roles:
            dp = trans.app.model.DatasetPermissions( trans.app.security_agent.permitted_actions.DATASET_ACCESS.action, ldda.dataset, role )
            trans.sa_session.add( dp )
            trans.sa_session.flush()
    return ldda


def new_upload( trans, cntrller, uploaded_dataset, library_bunch=None, history=None, state=None ):
    if library_bunch:
        return __new_library_upload( trans, cntrller, uploaded_dataset, library_bunch, state )
    else:
        return __new_history_upload( trans, uploaded_dataset, history=history, state=state )


def get_uploaded_datasets( trans, cntrller, params, precreated_datasets, dataset_upload_inputs, library_bunch=None, history=None ):
    uploaded_datasets = []
    for dataset_upload_input in dataset_upload_inputs:
        uploaded_datasets.extend( dataset_upload_input.get_uploaded_datasets( trans, params ) )
    for uploaded_dataset in uploaded_datasets:
        data = get_precreated_dataset( precreated_datasets, uploaded_dataset.name )
        if not data:
            data = new_upload( trans, cntrller, uploaded_dataset, library_bunch=library_bunch, history=history )
        else:
            data.extension = uploaded_dataset.file_type
            data.dbkey = uploaded_dataset.dbkey
            data.uuid = uploaded_dataset.uuid
            trans.sa_session.add( data )
            trans.sa_session.flush()
            if library_bunch:
                library_bunch.folder.genome_build = uploaded_dataset.dbkey
                trans.sa_session.add( library_bunch.folder )
                # Handle template included in the upload form, if any.  If the upload is asynchronous ( e.g., file upload ),
                # then the template and contents will be included in the library_bunch at this point.  If the upload is
                # not asynchronous ( e.g., URL paste ), then the template and contents will be included in the library_bunch
                # in the new_library_upload() method above.
                if library_bunch.template and library_bunch.template_field_contents:
                    # Since information templates are inherited, the template fields can be displayed on the upload form.
                    # If the user has added field contents, we'll need to create a new form_values and info_association
                    # for the new library_dataset_dataset_association object.
                    # Create a new FormValues object, using the template we previously retrieved
                    form_values = trans.app.model.FormValues( library_bunch.template, library_bunch.template_field_contents )
                    trans.sa_session.add( form_values )
                    trans.sa_session.flush()
                    # Create a new info_association between the current ldda and form_values
                    # TODO: Currently info_associations at the ldda level are not inheritable to the associated LibraryDataset,
                    # we need to figure out if this is optimal
                    info_association = trans.app.model.LibraryDatasetDatasetInfoAssociation( data, library_bunch.template, form_values )
                    trans.sa_session.add( info_association )
                trans.sa_session.flush()
            else:
                if not history:
                    history = trans.history
                history.genome_build = uploaded_dataset.dbkey
        uploaded_dataset.data = data
    return uploaded_datasets


def create_paramfile( trans, uploaded_datasets ):
    """
    Create the upload tool's JSON "param" file.
    """
    def _chown( path ):
        try:
            pwent = pwd.getpwnam( trans.user.email.split('@')[0] )
            cmd = [ '/usr/bin/sudo', '-E', trans.app.config.external_chown_script, path, pwent[0], str( pwent[3] ) ]
            log.debug( 'Changing ownership of %s with: %s' % ( path, ' '.join( cmd ) ) )
            p = subprocess.Popen( cmd, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE )
            stdout, stderr = p.communicate()
            assert p.returncode == 0, stderr
        except Exception, e:
            log.warning( 'Changing ownership of uploaded file %s failed: %s' % ( path, str( e ) ) )

    # TODO: json_file should go in the working directory
    json_file = tempfile.mkstemp()
    json_file_path = json_file[1]
    json_file = os.fdopen( json_file[0], 'w' )
    for uploaded_dataset in uploaded_datasets:
        data = uploaded_dataset.data
        if uploaded_dataset.type == 'composite':
            # we need to init metadata before the job is dispatched
            data.init_meta()
            for meta_name, meta_value in uploaded_dataset.metadata.iteritems():
                setattr( data.metadata, meta_name, meta_value )
            trans.sa_session.add( data )
            trans.sa_session.flush()
            json = dict( file_type=uploaded_dataset.file_type,
                         dataset_id=data.dataset.id,
                         dbkey=uploaded_dataset.dbkey,
                         type=uploaded_dataset.type,
                         metadata=uploaded_dataset.metadata,
                         primary_file=uploaded_dataset.primary_file,
                         composite_file_paths=uploaded_dataset.composite_files,
                         composite_files=dict( [ ( k, v.__dict__ ) for k, v in data.datatype.get_composite_files( data ).items() ] ) )
        else:
            try:
                is_binary = uploaded_dataset.datatype.is_binary
            except:
                is_binary = None
            try:
                link_data_only = uploaded_dataset.link_data_only
            except:
                link_data_only = 'copy_files'
            try:
                uuid_str = uploaded_dataset.uuid
            except:
                uuid_str = None
            json = dict( file_type=uploaded_dataset.file_type,
                         ext=uploaded_dataset.ext,
                         name=uploaded_dataset.name,
                         dataset_id=data.dataset.id,
                         dbkey=uploaded_dataset.dbkey,
                         type=uploaded_dataset.type,
                         is_binary=is_binary,
                         link_data_only=link_data_only,
                         uuid=uuid_str,
                         to_posix_lines=getattr(uploaded_dataset, "to_posix_lines", True),
                         space_to_tab=uploaded_dataset.space_to_tab,
                         in_place=trans.app.config.external_chown_script is None,
                         path=uploaded_dataset.path )
            # TODO: This will have to change when we start bundling inputs.
            # Also, in_place above causes the file to be left behind since the
            # user cannot remove it unless the parent directory is writable.
            if link_data_only == 'copy_files' and trans.app.config.external_chown_script:
                _chown( uploaded_dataset.path )
        json_file.write( dumps( json ) + '\n' )
    json_file.close()
    if trans.app.config.external_chown_script:
        _chown( json_file_path )
    return json_file_path


def create_job( trans, params, tool, json_file_path, data_list, folder=None, history=None ):
    """
    Create the upload job.
    """
    job = trans.app.model.Job()
    galaxy_session = trans.get_galaxy_session()
    if type( galaxy_session ) == trans.model.GalaxySession:
        job.session_id = galaxy_session.id
    if trans.user is not None:
        job.user_id = trans.user.id
    if folder:
        job.library_folder_id = folder.id
    else:
        if not history:
            history = trans.history
        job.history_id = history.id
    job.tool_id = tool.id
    job.tool_version = tool.version
    job.state = job.states.UPLOAD
    trans.sa_session.add( job )
    trans.sa_session.flush()
    log.info( 'tool %s created job id %d' % ( tool.id, job.id ) )
    trans.log_event( 'created job id %d' % job.id, tool_id=tool.id )

    for name, value in tool.params_to_strings( params, trans.app ).iteritems():
        job.add_parameter( name, value )
    job.add_parameter( 'paramfile', dumps( json_file_path ) )
    object_store_id = None
    for i, dataset in enumerate( data_list ):
        if folder:
            job.add_output_library_dataset( 'output%i' % i, dataset )
        else:
            job.add_output_dataset( 'output%i' % i, dataset )
        # Create an empty file immediately
        if not dataset.dataset.external_filename:
            dataset.dataset.object_store_id = object_store_id
            try:
                trans.app.object_store.create( dataset.dataset )
            except ObjectInvalid:
                raise Exception('Unable to create output dataset: object store is full')
            object_store_id = dataset.dataset.object_store_id
            trans.sa_session.add( dataset )
            # open( dataset.file_name, "w" ).close()
    job.object_store_id = object_store_id
    job.state = job.states.NEW
    job.set_handler(tool.get_job_handler(None))
    trans.sa_session.add( job )
    trans.sa_session.flush()

    # Queue the job for execution
    trans.app.job_queue.put( job.id, job.tool_id )
    trans.log_event( "Added job to the job queue, id: %s" % str(job.id), tool_id=job.tool_id )
    output = odict()
    for i, v in enumerate( data_list ):
        output[ 'output%i' % i ] = v
    return job, output


def active_folders( trans, folder ):
    # Stolen from galaxy.web.controllers.library_common (importing from which causes a circular issues).
    # Much faster way of retrieving all active sub-folders within a given folder than the
    # performance of the mapper.  This query also eagerloads the permissions on each folder.
    return trans.sa_session.query( trans.app.model.LibraryFolder ) \
                           .filter_by( parent=folder, deleted=False ) \
                           .options( eagerload_all( "actions" ) ) \
                           .order_by( trans.app.model.LibraryFolder.table.c.name ) \
                           .all()
