from galaxy.web.base.controller import *

import logging, os, sets, string, shutil, tempfile, StringIO, urllib
import re, socket
import mimetypes

from galaxy import util, datatypes, jobs, web, util, model
from galaxy.datatypes import sniff
from galaxy.security import RBACAgent
from cgi import escape, FieldStorage

import smtplib
from email.MIMEText import MIMEText

import pkg_resources; 
pkg_resources.require( "Paste" )
import paste.httpexceptions

log = logging.getLogger( __name__ )

error_report_template = """
GALAXY TOOL ERROR REPORT
------------------------

This error report is in reference to output dataset ${dataset_id}.
-----------------------------------------------------------------------------
The user '${email}' provided the following information:
${message}
-----------------------------------------------------------------------------
job id: ${job_id}
tool id: ${tool_id}
-----------------------------------------------------------------------------
job stderr:
${stderr}
-----------------------------------------------------------------------------
job stdout:
${stdout}
-----------------------------------------------------------------------------
job info:
${info}
-----------------------------------------------------------------------------
(This is an automated message).
"""

class DatasetInterface( BaseController ):

    @web.expose
    def errors( self, trans, id ):
        dataset = model.HistoryDatasetAssociation.get( id )
        return trans.fill_template( "dataset/errors.tmpl", dataset=dataset )
    
    @web.expose
    def stderr( self, trans, id ):
        dataset = model.HistoryDatasetAssociation.get( id )
        job = dataset.creating_job_associations[0].job
        trans.response.set_content_type( 'text/plain' )
        return job.stderr

    @web.expose
    def report_error( self, trans, id, email="no email provided", message="" ):
        smtp_server = trans.app.config.smtp_server
        if smtp_server is None:
            return trans.show_error_message( "Sorry, mail is not configured for this galaxy instance" )
        to_address = trans.app.config.error_email_to
        if to_address is None:
            return trans.show_error_message( "Sorry, error reporting has been disabled for this galaxy instance" )
        # Get the dataset and associated job
        dataset = model.HistoryDatasetAssociation.get( id )
        job = dataset.creating_job_associations[0].job
        # Build the email message
        msg = MIMEText( string.Template( error_report_template )
            .safe_substitute( dataset_id=dataset.id,
                              email=email, 
                              message=message,
                              job_id=job.id,
                              tool_id=job.tool_id,
                              stderr=job.stderr,
                              stdout=job.stdout,
                              info=job.info ) )
        frm = to_address
        # Check email a bit
        email = email.strip()
        parts = email.split()
        if len( parts ) == 1 and len( email ) > 0:
            to = to_address + ", " + email
        else:
            to = to_address
        msg[ 'To' ] = to
        msg[ 'From' ] = frm
        msg[ 'Subject' ] = "Galaxy tool error report from " + email
        # Send it
        try:
            s = smtplib.SMTP()
            s.connect( smtp_server )
            s.sendmail( frm, [ to ], msg.as_string() )
            s.close()
            return trans.show_ok_message( "Your error report has been sent" )
        except:
            return trans.show_error_message( "An error occurred sending the report by email" )
    
    @web.expose
    def default(self, trans, dataset_id=None, **kwd):
        return 'This link may not be followed from within Galaxy.'
    
    @web.expose
    def display(self, trans, dataset_id=None, filename=None, **kwd):
        """Catches the dataset id and displays file contents as directed"""
        data = trans.app.model.HistoryDatasetAssociation.get( dataset_id )
        if not data:
            raise paste.httpexceptions.HTTPRequestRangeNotSatisfiable( "Invalid reference dataset id: %s." % str( dataset_id ) )
        if trans.app.security_agent.allow_action( trans.user, data.permitted_actions.DATASET_ACCESS, dataset = data ):
            if filename is None or filename.lower() == "index":
                mime = trans.app.datatypes_registry.get_mimetype_by_extension( data.extension.lower() )
                trans.response.set_content_type(mime)
                trans.log_event( "Display dataset id: %s" % str( dataset_id ) )
                try:
                    return open( data.file_name )
                except:
                    raise paste.httpexceptions.HTTPNotFound( "File Not Found (%s)." % ( filename ) )
            else:
                file_path = os.path.join( data.extra_files_path, filename )
                mime, encoding = mimetypes.guess_type( file_path )
                if mime is None:
                    mime = trans.app.datatypes_registry.get_mimetype_by_extension( ".".split( file_path )[-1] )
                trans.response.set_content_type( mime )
                try:
                    return open( file_path )
                except:
                    raise paste.httpexceptions.HTTPNotFound( "File Not Found (%s)." % ( filename ) )
        else:
            return trans.show_error_message( "You are not allowed to access this dataset" )
    
    def _undelete( self, trans, id ):
        history = trans.get_history()
        data = self.app.model.HistoryDatasetAssociation.get( id )
        if data and data.undeletable:
            # Walk up parent datasets to find the containing history
            topmost_parent = data
            while topmost_parent.parent:
                topmost_parent = topmost_parent.parent
            assert topmost_parent in history.datasets, "Data does not belong to current history"
            # Mark undeleted
            data.mark_undeleted()
            self.app.model.flush()
            trans.log_event( "Dataset id %s has been undeleted" % str(id) )
            return True
        return False
    
    @web.expose
    def undelete( self, trans, id ):
        self._undelete( trans, id )
        return trans.response.send_redirect( web.url_for( controller='root', action='history', show_deleted = True ) )
    
    @web.expose
    def undelete_async( self, trans, id ):
        if self._undelete( trans, id ):
            return "OK"
        raise "Error undeleting"
    
    @web.expose
    def copy_datasets( self, trans, source_dataset_ids = "", target_history_ids = "", new_history_name="", do_copy = False ):
        user = trans.get_user()
        history = trans.get_history()
        create_new_history = False
        if source_dataset_ids:
            if not isinstance( source_dataset_ids, list ):
                source_dataset_ids = source_dataset_ids.split( "," )
            source_dataset_ids = map( int, source_dataset_ids )
        else:
            source_dataset_ids = []
        if target_history_ids:
            if not isinstance( target_history_ids, list ):
                target_history_ids = target_history_ids.split( "," )
            if "create_new_history" in target_history_ids:
                create_new_history = True
                target_history_ids.remove( "create_new_history" )
            target_history_ids = map( int, target_history_ids )
        else:
            target_history_ids = []
        done_msg = error_msg = ""
        if do_copy:
            invalid_datasets = 0
            if not source_dataset_ids or not ( target_history_ids or create_new_history ):
                error_msg = "You must provide both source datasets and target histories."
                if create_new_history:
                    target_history_ids.append( "create_new_history" )
            else:
                if create_new_history:
                    new_history = trans.app.model.History()
                    if new_history_name:
                        new_history.name = new_history_name
                    new_history.user = user
                    new_history.flush()
                    target_history_ids.append( new_history.id )
                if user:
                    target_histories = [ hist for hist in map( trans.app.model.History.get, target_history_ids ) if ( hist is not None and hist.user == user )]
                else:
                    target_histories = [ history ]
                if len( target_histories ) != len( target_history_ids ):
                    error_msg = error_msg + "You do not have permission to add datasets to %i requested histories.  " % ( len( target_history_ids ) - len( target_histories ) )
                for data in map( trans.app.model.HistoryDatasetAssociation.get, source_dataset_ids ):
                    if data is None:
                        error_msg = error_msg + "You tried to copy a non-existant dataset.  "
                        invalid_datasets += 1
                    elif data.history != history:
                        error_msg = error_msg + "You tried to copy a dataset which is not in your current history.  "
                        invalid_datasets += 1
                    else:
                        for hist in target_histories:
                            hist.add_dataset( data.copy( copy_children = True ) )
                trans.app.model.flush()
                done_msg = "%i datasets copied to %i histories." % ( len( source_dataset_ids ) - invalid_datasets, len( target_histories ) )
                history.refresh()
        elif create_new_history:
            target_history_ids.append( "create_new_history" )
        source_datasets = history.active_datasets
        target_histories = [history]
        if user:
           target_histories = user.histories 
        
        return trans.fill_template( "/dataset/copy_view.mako",
                                    source_dataset_ids = source_dataset_ids,
                                    target_history_ids = target_history_ids,
                                    source_datasets = source_datasets,
                                    target_histories = target_histories,
                                    new_history_name = new_history_name,
                                    done_msg = done_msg,
                                    error_msg = error_msg )

def add_file( trans, file_obj, name, extension, dbkey, roles, info='no info', space_to_tab=False,
              replace_dataset=None, permission_source=None, folder_id=None ):
    def check_gzip( temp_name ):
        # Utility method to check gzipped uploads
        temp = open( temp_name, "U" )
        magic_check = temp.read( 2 )
        temp.close()
        if magic_check != util.gzip_magic:
            return ( False, False )
        CHUNK_SIZE = 2**15 # 32Kb
        gzipped_file = gzip.GzipFile( temp_name )
        chunk = gzipped_file.read( CHUNK_SIZE )
        gzipped_file.close()
        return ( True, True )
    data_type = None
    temp_name = sniff.stream_to_file( file_obj )
    # See if we have a gzipped file, which, if it passes our restrictions, we'll uncompress on the fly.
    is_gzipped, is_valid = check_gzip( temp_name )
    if is_gzipped and not is_valid:
        raise BadFileException( "you attempted to upload an inappropriate file." )
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
                raise BadFileException( 'problem uncompressing gzipped data.' )
            if not chunk:
                break
            os.write( fd, chunk )
        os.close( fd )
        gzipped_file.close()
        # Replace the gzipped file with the decompressed file
        shutil.move( uncompressed, temp_name )
        name = name.rstrip( '.gz' )
        data_type = 'gzip'
    if space_to_tab:
        line_count = sniff.convert_newlines_sep2tabs( temp_name )
    elif os.stat( temp_name ).st_size < 262144000: # 250MB
        line_count = sniff.convert_newlines( temp_name )
    else:
        if sniff.check_newlines( temp_name ):
            line_count = sniff.convert_newlines( temp_name )
        else:
            line_count = None
    if extension == 'auto':
        data_type = sniff.guess_ext( temp_name, sniff_order=trans.app.datatypes_registry.sniff_order )    
    else:
        data_type = extension
    if replace_dataset:
        library_dataset = replace_dataset
    else:
        library_dataset = trans.app.model.LibraryDataset( name=name, info=info, extension=data_type, dbkey=dbkey )
        library_dataset.flush()
        if permission_source:
            trans.app.security_agent.copy_library_permissions( permission_source, library_dataset, user=trans.get_user() )
    ldda = trans.app.model.LibraryDatasetDatasetAssociation( name=name, 
                                                             info=info, 
                                                             extension=data_type, 
                                                             dbkey=dbkey, 
                                                             library_dataset = library_dataset,
                                                             create_dataset=True )
    ldda.flush()
    if permission_source:
        trans.app.security_agent.copy_library_permissions( permission_source, ldda, user=trans.get_user() )
    if not replace_dataset:
        folder = trans.app.model.LibraryFolder.get( folder_id )
        folder.add_dataset( library_dataset, genome_build=dbkey )
    library_dataset.library_dataset_dataset_association_id = ldda.id
    library_dataset.flush()
    if roles:
        for role in roles:
            dp = trans.app.model.DatasetPermissions( RBACAgent.permitted_actions.DATASET_ACCESS.action, ldda.dataset, role )
            dp.flush()
    shutil.move( temp_name, ldda.dataset.file_name )
    ldda.dataset.state = ldda.dataset.states.OK
    ldda.init_meta()
    if line_count is not None:
        try:
            ldda.set_peek( line_count=line_count )
        except:
            ldda.set_peek()
    else:
        ldda.set_peek()
    ldda.set_size()
    if ldda.missing_meta():
        ldda.datatype.set_meta( ldda )
    trans.app.model.flush()
    return ldda

def upload_dataset( trans, controller=None, folder_id=None, replace_dataset=None, replace_id=None, permission_source=None, **kwd ):
    # This method is called from both the admin and library controllers
    params = util.Params( kwd )
    msg = util.restore_text( params.get( 'msg', ''  ) )
    messagetype = params.get( 'messagetype', 'done' )
    dbkey = params.get( 'dbkey', '?' )
    extension = params.get( 'extension', 'auto' )
    data_file = params.get( 'file_data', '' )
    url_paste = params.get( 'url_paste', '' )
    server_dir = params.get( 'server_dir', 'None' )
    if data_file == '' and url_paste == '' and server_dir in [ 'None', '' ]:
        if trans.app.config.library_import_dir is not None:
            msg = 'Select a file, enter a URL or Text, or select a server directory.'
        else:
            msg = 'Select a file, enter a URL or enter Text.'
        trans.response.send_redirect( web.url_for( controller=controller,
                                                   action='dataset',
                                                   folder_id=folder_id,
                                                   replace_id=replace_id, 
                                                   msg=util.sanitize_text( msg ),
                                                   messagetype='done' ) )
    space_to_tab = params.get( 'space_to_tab', False )
    if space_to_tab and space_to_tab not in [ "None", None ]:
        space_to_tab = True
    roles = []
    for role_id in util.listify( params.get( 'roles', [] ) ):
        roles.append( trans.app.model.Role.get( role_id ) )
    temp_name = ""
    data_list = []
    created_ldda_ids = ''
    if 'filename' in dir( data_file ):
        file_name = data_file.filename
        file_name = file_name.split( '\\' )[-1]
        file_name = file_name.split( '/' )[-1]
        created_ldda = add_file( trans,
                                 data_file.file,
                                 file_name,
                                 extension,
                                 dbkey,
                                 roles,
                                 info="uploaded file",
                                 space_to_tab=space_to_tab,
                                 replace_dataset=replace_dataset,
                                 permission_source=permission_source,
                                 folder_id=folder_id )
        created_ldda_ids = str( created_ldda.id )
    elif url_paste not in [ None, "" ]:
        if url_paste.lower().find( 'http://' ) >= 0 or url_paste.lower().find( 'ftp://' ) >= 0:
            url_paste = url_paste.replace( '\r', '' ).split( '\n' )
            for line in url_paste:
                line = line.rstrip( '\r\n' )
                if line:
                    created_ldda = add_file( trans,
                                             urllib.urlopen( line ),
                                             line,
                                             extension,
                                             dbkey,
                                             roles,
                                             info="uploaded url",
                                             space_to_tab=space_to_tab,
                                             replace_dataset=replace_dataset,
                                             permission_source=permission_source,
                                             folder_id=folder_id )
                    created_ldda_ids = '%s,%s' % ( created_ldda_ids, str( created_ldda.id ) )
        else:
            is_valid = False
            for line in url_paste:
                line = line.rstrip( '\r\n' )
                if line:
                    is_valid = True
                    break
            if is_valid:
                created_ldda = add_file( trans,
                                         StringIO.StringIO( url_paste ),
                                         'Pasted Entry',
                                         extension,
                                         dbkey,
                                         roles,
                                         info="pasted entry",
                                         space_to_tab=space_to_tab,
                                         replace_dataset=replace_dataset,
                                         permission_source=permission_source,
                                         folder_id=folder_id )
                created_ldda_ids = '%s,%s' % ( created_ldda_ids, str( created_ldda.id ) )
    elif server_dir not in [ None, "", "None" ]:
        full_dir = os.path.join( trans.app.config.library_import_dir, server_dir )
        try:
            files = os.listdir( full_dir )
        except:
            log.debug( "Unable to get file list for %s" % full_dir )
        for file in files:
            full_file = os.path.join( full_dir, file )
            if not os.path.isfile( full_file ):
                continue
            created_ldda = add_file( trans,
                                     open( full_file, 'rb' ),
                                     file,
                                     extension,
                                     dbkey,
                                     roles,
                                     info="imported file",
                                     space_to_tab=space_to_tab,
                                     replace_dataset=replace_dataset,
                                     permission_source=permission_source,
                                     folder_id=folder_id )
            created_ldda_ids = '%s,%s' % ( created_ldda_ids, str( created_ldda.id ) )
    if created_ldda_ids:
        created_ldda_ids = created_ldda_ids.lstrip( ',' )
        return created_ldda_ids
    else:
        return ''
