import logging, os, sets, string, shutil, re, socket, mimetypes, smtplib

from galaxy.web.base.controller import *
from galaxy import util, datatypes, jobs, web, model
from cgi import escape, FieldStorage

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
        except Exception, e:
            return trans.show_error_message( "An error occurred sending the report by email: %s" % str( e ) )
    
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
        if isinstance( id, type( 1 ) ):
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
