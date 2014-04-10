"""
Functionality for dealing with tool errors.
"""
import string
from galaxy import model, util, web

error_report_template = """
GALAXY TOOL ERROR REPORT
------------------------

This error report was sent from the Galaxy instance hosted on the server
"${host}"
-----------------------------------------------------------------------------
This is in reference to dataset id ${dataset_id} from history id ${history_id}
-----------------------------------------------------------------------------
You should be able to view the history containing the related history item

${hid}: ${history_item_name}

by logging in as a Galaxy admin user to the Galaxy instance referenced above
and pointing your browser to the following link.

${history_view_link}
-----------------------------------------------------------------------------
The user '${email}' provided the following information:

${message}
-----------------------------------------------------------------------------
job id: ${job_id}
tool id: ${job_tool_id}
tool version: ${tool_version}
job pid or drm id: ${job_runner_external_id}
job tool version: ${job_tool_version}
-----------------------------------------------------------------------------
job command line:
${job_command_line}
-----------------------------------------------------------------------------
job stderr:
${job_stderr}
-----------------------------------------------------------------------------
job stdout:
${job_stdout}
-----------------------------------------------------------------------------
job info:
${job_info}
-----------------------------------------------------------------------------
job traceback:
${job_traceback}
-----------------------------------------------------------------------------
(This is an automated message).
"""

class ErrorReporter( object ):
    def __init__( self, hda, app ):
         # Get the dataset
        sa_session = app.model.context
        if not isinstance( hda, model.HistoryDatasetAssociation ):
            hda_id = hda
            try:
                hda = sa_session.query( model.HistoryDatasetAssociation ).get( hda_id )
                assert hda is not None, ValueError( "No HDA yet" )
            except:
                hda = sa_session.query( model.HistoryDatasetAssociation ).get( app.security.decode_id( hda_id ) )
        assert isinstance( hda, model.HistoryDatasetAssociation ), ValueError( "Bad value provided for HDA (%s)." % ( hda ) )
        self.hda = hda
        # Get the associated job
        self.job = hda.creating_job
        self.app = app
        self.tool_id = self.job.tool_id
        self.report = None
    def _can_access_dataset( self, user ):
        if user:
            roles = user.all_roles()
        else:
            roles = []
        return self.app.security_agent.can_access_dataset( roles, self.hda.dataset )
    def create_report( self, email='', message='', **kwd ):
        hda = self.hda
        job = self.job
        host = web.url_for( '/', qualified=True )
        history_view_link = web.url_for( controller="history", action="view", id=self.app.security.encode_id( hda.history_id ), qualified=True )
        # Build the email message
        self.report = string.Template( error_report_template ) \
            .safe_substitute( host=host,
                              dataset_id=hda.dataset_id,
                              history_id=hda.history_id,
                              hid=hda.hid,
                              history_item_name=hda.get_display_name(),
                              history_view_link=history_view_link,
                              job_id=job.id,
                              tool_version=job.tool_version,
                              job_tool_id=job.tool_id,
                              job_tool_version=hda.tool_version,
                              job_runner_external_id=job.job_runner_external_id,
                              job_command_line=job.command_line,
                              job_stderr=util.unicodify( job.stderr ),
                              job_stdout=util.unicodify( job.stdout ),
                              job_info=util.unicodify( job.info ),
                              job_traceback=util.unicodify( job.traceback ),
                              email=email,
                              message=util.unicodify( message ) )
    def _send_report( self, user, email=None, message=None, **kwd ):
        return self.report
    def send_report( self, user, email=None, message=None, **kwd ):
        if self.report is None:
            self.create_report( email=email, message=message, **kwd )
        return self._send_report( user, email=email, message=message, **kwd )
        
class EmailErrorReporter( ErrorReporter ):
    def _send_report( self, user, email=None, message=None, **kwd ):
        smtp_server = self.app.config.smtp_server
        assert smtp_server, ValueError( "Mail is not configured for this galaxy instance" )
        to_address = self.app.config.error_email_to
        assert to_address, ValueError( "Error reporting has been disabled for this galaxy instance" )
        
        frm = to_address
        # Check email a bit
        email = email or ''
        email = email.strip()
        parts = email.split()
        if len( parts ) == 1 and len( email ) > 0 and self._can_access_dataset( user ):
            to = to_address + ", " + email
        else:
            to = to_address
        subject = "Galaxy tool error report from %s" % email
        # Send it
        return util.send_mail( frm, to, subject, self.report, self.app.config )
