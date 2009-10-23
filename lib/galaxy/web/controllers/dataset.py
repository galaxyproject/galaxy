import logging, os, string, shutil, re, socket, mimetypes, smtplib, urllib

from galaxy.web.base.controller import *
from galaxy.tags.tag_handler import TagHandler
from galaxy.web.framework.helpers import time_ago, iff, grids
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

This error report was sent from the Galaxy instance hosted on the server
"${host}"
-----------------------------------------------------------------------------
This is in reference to output dataset ${dataset_id}.
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
job traceback:
${traceback}
-----------------------------------------------------------------------------
(This is an automated message).
"""

class HistoryDatasetAssociationListGrid( grids.Grid ):
    class StatusColumn( grids.GridColumn ):
        def get_value( self, trans, grid, hda ):
            if hda.deleted:
                return "deleted"
            return ""
        def get_link( self, trans, grid, hda ):
            return None
    class TagsColumn( grids.GridColumn ):
        def __init__(self, col_name, key, filterable):
            grids.GridColumn.__init__(self, col_name, key=key, filterable=filterable)
            # Tags cannot be sorted.
            self.sortable = False
            self.tag_elt_id_gen = 0
        def get_value( self, trans, grid, hda ):
            self.tag_elt_id_gen += 1
            elt_id="tagging-elt" + str( self.tag_elt_id_gen )
            div_elt = "<div id=%s></div>" % elt_id
            return div_elt + trans.fill_template( "/tagging_common.mako", trans=trans, tagged_item=hda, 
                                                    elt_id = elt_id, in_form="true", input_size="20", tag_click_fn="add_tag_to_grid_filter" )
        def filter( self, db_session, query, column_filter ):
            """ Modify query to include only hdas with tags in column_filter. """
            if column_filter == "All":
                pass
            elif column_filter:
                # Parse filter to extract multiple tags.
                tag_handler = TagHandler()
                raw_tags = tag_handler.parse_tags( column_filter.encode("utf-8") )
                for name, value in raw_tags.items():
                    tag = tag_handler.get_tag_by_name( db_session, name )
                    if tag:
                        query = query.filter( model.HistoryDatasetAssociation.tags.any( tag_id=tag.id ) )
                        if value:
                            query = query.filter( model.HistoryDatasetAssociation.tags.any( value=value.lower() ) )
                    else: 
                        # Tag doesn't exist; unclear what to do here, but the literal thing to do is add the criterion, which
                        # will then yield a query that returns no results.
                        query = query.filter( model.HistoryDatasetAssociation.tags.any( user_tname=name ) )
            return query
        def get_accepted_filters( self ):
               """ Returns a list of accepted filters for this column. """
               accepted_filter_labels_and_vals = { "All": "All" }
               accepted_filters = []
               for label, val in accepted_filter_labels_and_vals.items():
                   args = { self.key: val }
                   accepted_filters.append( grids.GridColumnFilter( label, args) )
               return accepted_filters
             
    class StatusColumn( grids.GridColumn ):
        def get_value( self, trans, grid, hda ):
            if hda.deleted:
                return "deleted"
            return ""
        def get_accepted_filters( self ):
            """ Returns a list of accepted filters for this column. """
            accepted_filter_labels_and_vals = { "Active" : "False", "Deleted" : "True", "All": "All" }
            accepted_filters = []
            for label, val in accepted_filter_labels_and_vals.items():
               args = { self.key: val }
               accepted_filters.append( grids.GridColumnFilter( label, args) )
            return accepted_filters

    # Grid definition
    title = "Stored Datasets"
    model_class = model.HistoryDatasetAssociation
    template='/dataset/grid.mako'
    default_sort_key = "-create_time"
    columns = [
         grids.GridColumn( "Name", key="name",
                                # Link name to dataset's history.
                              link=( lambda item: iff( item.history.deleted, None, dict( operation="switch", id=item.id ) ) ) ),
        TagsColumn( "Tags", key="tags", filterable=True ),
        StatusColumn( "Status", key="deleted", attach_popup=False ),
        grids.GridColumn( "Created", key="create_time", format=time_ago ),
        grids.GridColumn( "Last Updated", key="update_time", format=time_ago ),
    ]
    operations = []
    standard_filters = []
    default_filter = dict( deleted="False", tags="All" )
    preserve_state = False
    use_paging = True
    num_rows_per_page = 50
    def apply_default_filter( self, trans, query, **kwargs ):
        # This is a somewhat obtuse way to join the History and HDA tables. However, it's necessary 
        # because the initial query in build_initial_query is specificied on the HDA table (this is reasonable) 
        # and there's no simple property in the HDA to do the join.
        return query.select_from( model.HistoryDatasetAssociation.table.join( model.History.table ) ).filter( model.History.user == trans.user )

class DatasetInterface( BaseController ):
        
    stored_list_grid = HistoryDatasetAssociationListGrid()

    @web.expose
    def errors( self, trans, id ):
        dataset = trans.sa_session.query( model.HistoryDatasetAssociation ).get( id )
        return trans.fill_template( "dataset/errors.mako", dataset=dataset )
    
    @web.expose
    def stderr( self, trans, id ):
        dataset = trans.sa_session.query( model.HistoryDatasetAssociation ).get( id )
        job = dataset.creating_job_associations[0].job
        trans.response.set_content_type( 'text/plain' )
        return job.stderr

    @web.expose
    def report_error( self, trans, id, email='', message="" ):
        smtp_server = trans.app.config.smtp_server
        if smtp_server is None:
            return trans.show_error_message( "Sorry, mail is not configured for this galaxy instance" )
        to_address = trans.app.config.error_email_to
        if to_address is None:
            return trans.show_error_message( "Sorry, error reporting has been disabled for this galaxy instance" )
        # Get the dataset and associated job
        dataset = trans.sa_session.query( model.HistoryDatasetAssociation ).get( id )
        job = dataset.creating_job_associations[0].job
        # Get the name of the server hosting the Galaxy instance from which this report originated
        host = trans.request.host
        # Build the email message
        msg = MIMEText( string.Template( error_report_template )
            .safe_substitute( host=host,
                              dataset_id=dataset.id,
                              email=email, 
                              message=message,
                              job_id=job.id,
                              tool_id=job.tool_id,
                              stderr=job.stderr,
                              stdout=job.stdout,
                              traceback=job.traceback,
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
    def display(self, trans, dataset_id=None, preview=False, filename=None, to_ext=None, **kwd):
        """Catches the dataset id and displays file contents as directed"""
        
        # DEPRECATION: We still support unencoded ids for backward compatibility
        try:
            dataset_id = int( dataset_id )
        except ValueError:
            dataset_id = trans.security.decode_id( dataset_id )
        data = data = trans.sa_session.query( trans.app.model.HistoryDatasetAssociation ).get( dataset_id )
        if not data:
            raise paste.httpexceptions.HTTPRequestRangeNotSatisfiable( "Invalid reference dataset id: %s." % str( dataset_id ) )
        user, roles = trans.get_user_and_roles()
        if trans.app.security_agent.can_access_dataset( roles, data.dataset ):
            if data.state == trans.model.Dataset.states.UPLOAD:
                return trans.show_error_message( "Please wait until this dataset finishes uploading before attempting to view it." )
            
            if filename and filename != "index":
                file_path = os.path.join( data.extra_files_path, filename )
                if os.path.exists( file_path ):
                    mime, encoding = mimetypes.guess_type( file_path )
                    if not mime:
                        try:
                            mime = trans.app.datatypes_registry.get_mimetype_by_extension( ".".split( file_path )[-1] )
                        except:
                            mime = "txt"
                
                    trans.response.set_content_type( mime )
                    return open( file_path )
                else:
                    return "Could not find '%s' on the extra files path." % filename
            
            mime = trans.app.datatypes_registry.get_mimetype_by_extension( data.extension.lower() )
            trans.response.set_content_type(mime)
            trans.log_event( "Display dataset id: %s" % str( dataset_id ) )
            
            if to_ext: # Saving the file
                trans.response.headers['Content-Length'] = int( os.stat( data.file_name ).st_size )
                if to_ext[0] != ".":
                    to_ext = "." + to_ext
                valid_chars = '.,^_-()[]0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
                fname = data.name
                fname = ''.join(c in valid_chars and c or '_' for c in fname)[0:150]
                trans.response.headers["Content-Disposition"] = "attachment; filename=GalaxyHistoryItem-%s-[%s]%s" % (data.hid, fname, to_ext)
                return open( data.file_name )
                
            if os.path.exists( data.file_name ):
                max_peek_size = 1000000 # 1 MB
                if preview and os.stat( data.file_name ).st_size > max_peek_size:
                    trans.response.set_content_type( "text/html" )
                    return trans.stream_template_mako( "/dataset/large_file.mako",
                                                    truncated_data = open( data.file_name ).read(max_peek_size),
                                                    data = data )
                else:
                    return open( data.file_name )
            else:
                raise paste.httpexceptions.HTTPNotFound( "File Not Found (%s)." % data.file_name )
        else:
            return trans.show_error_message( "You are not allowed to access this dataset" )
            
    @web.expose
    @web.require_login( "see all available datasets" )
    def list( self, trans, **kwargs ):
        """List all available datasets"""
        status = message = None

        if 'operation' in kwargs:
            operation = kwargs['operation'].lower()
            hda_ids = util.listify( kwargs.get( 'id', [] ) )
            
            # Display no message by default
            status, message = None, None

            # Load the hdas and ensure they all belong to the current user
            hdas = []
            for encoded_hda_id in hda_ids:
                hda_id = trans.security.decode_id( encoded_hda_id )
                hda = trans.sa_session.query( model.HistoryDatasetAssociation ).filter_by( id=hda_id ).first()
                if hda:
                    # Ensure history is owned by current user
                    if hda.history.user_id != None and trans.user:
                        assert trans.user.id == hda.history.user_id, "HistoryDatasetAssocation does not belong to current user"
                    hdas.append( hda )
                else:
                    log.warn( "Invalid history_dataset_association id '%r' passed to list", hda_id )

            if hdas:
                
                if operation == "switch":
                    # Convert hda to histories.
                    histories = []
                    for hda in hdas:
                        histories.append( hda.history )
                        
                    # Use history controller to switch the history. TODO: is this reasonable?
                    status, message = trans.webapp.controllers['history']._list_switch( trans, histories )
                    
                    # Current history changed, refresh history frame
                    trans.template_context['refresh_frames'] = ['history']        

        # Render the list view
        return self.stored_list_grid( trans, status=status, message=message, **kwargs )

    @web.expose
    def display_at( self, trans, dataset_id, filename=None, **kwd ):
        """Sets up a dataset permissions so it is viewable at an external site"""
        site = filename
        data = trans.sa_session.query( trans.app.model.HistoryDatasetAssociation ).get( dataset_id )
        if not data:
            raise paste.httpexceptions.HTTPRequestRangeNotSatisfiable( "Invalid reference dataset id: %s." % str( dataset_id ) )
        if 'display_url' not in kwd or 'redirect_url' not in kwd:
            return trans.show_error_message( 'Invalid parameters specified for "display at" link, please contact a Galaxy administrator' )
        redirect_url = kwd['redirect_url'] % urllib.quote_plus( kwd['display_url'] )
        user, roles = trans.get_user_and_roles()
        if trans.app.security_agent.dataset_is_public( data.dataset ):
            return trans.response.send_redirect( redirect_url ) # anon access already permitted by rbac
        if trans.app.security_agent.can_access_dataset( roles, data.dataset ):
            trans.app.host_security_agent.set_dataset_permissions( data, trans.user, site )
            return trans.response.send_redirect( redirect_url )
        else:
            return trans.show_error_message( "You are not allowed to view this dataset at external sites.  Please contact your Galaxy administrator to acquire management permissions for this dataset." )

    def _undelete( self, trans, id ):
        try:
            id = int( id )
        except ValueError, e:
            return False
        history = trans.get_history()
        data = trans.sa_session.query( self.app.model.HistoryDatasetAssociation ).get( id )
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
        if self._undelete( trans, id ):
            return trans.response.send_redirect( web.url_for( controller='root', action='history', show_deleted = True ) )
        raise "Error undeleting"

    @web.expose
    def undelete_async( self, trans, id ):
        if self._undelete( trans, id ):
            return "OK"
        raise "Error undeleting"
    
    @web.expose
    def copy_datasets( self, trans, source_dataset_ids="", target_history_ids="", new_history_name="", do_copy=False, **kwd ):
        params = util.Params( kwd )
        user = trans.get_user()
        history = trans.get_history()
        create_new_history = False
        refresh_frames = []
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
                    target_histories = [ hist for hist in map( trans.sa_session.query( trans.app.model.History ).get, target_history_ids ) if ( hist is not None and hist.user == user )]
                else:
                    target_histories = [ history ]
                if len( target_histories ) != len( target_history_ids ):
                    error_msg = error_msg + "You do not have permission to add datasets to %i requested histories.  " % ( len( target_history_ids ) - len( target_histories ) )
                for data in map( trans.sa_session.query( trans.app.model.HistoryDatasetAssociation ).get, source_dataset_ids ):
                    if data is None:
                        error_msg = error_msg + "You tried to copy a dataset that does not exist.  "
                        invalid_datasets += 1
                    elif data.history != history:
                        error_msg = error_msg + "You tried to copy a dataset which is not in your current history.  "
                        invalid_datasets += 1
                    else:
                        for hist in target_histories:
                            hist.add_dataset( data.copy( copy_children = True ) )
                if history in target_histories:
                    refresh_frames = ['history']
                trans.app.model.flush()
                done_msg = "%i datasets copied to %i histories." % ( len( source_dataset_ids ) - invalid_datasets, len( target_histories ) )
                trans.sa_session.refresh( history )
        elif create_new_history:
            target_history_ids.append( "create_new_history" )
        source_datasets = history.active_datasets
        target_histories = [history]
        if user:
           target_histories = user.active_histories 
        return trans.fill_template( "/dataset/copy_view.mako",
                                    source_dataset_ids = source_dataset_ids,
                                    target_history_ids = target_history_ids,
                                    source_datasets = source_datasets,
                                    target_histories = target_histories,
                                    new_history_name = new_history_name,
                                    done_msg = done_msg,
                                    error_msg = error_msg,
                                    refresh_frames = refresh_frames )
