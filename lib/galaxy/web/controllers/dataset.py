from galaxy.web.base.controller import *

import logging, os, sets, string, shutil
import re, socket
import mimetypes

from galaxy import util, datatypes, jobs, web, util, model

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

This error report is in reference to dataset ${dataset_id}. The user 
(${email}) provided the following information:

-----------------------------------------------------------------------------
${message}
-----------------------------------------------------------------------------

The tool error was:

-----------------------------------------------------------------------------
${stderr}
-----------------------------------------------------------------------------

And the tool output was:

-----------------------------------------------------------------------------
${stdout}
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
                              stderr=job.stderr,
                              stdout=job.stdout ) )
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
            raise paste.httpexceptions.HTTPRequestRangeNotSatisfiable( "Invalid reference dataset." )
        # TODO, Nate: Make sure the following is functionally correct.
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
            raise paste.httpexceptions.HTTPForbidden( "You are not privileged to access this dataset." )
