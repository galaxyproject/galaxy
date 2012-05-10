import logging
import mimetypes
import os
import string
import sys
import tempfile
import urllib
import zipfile

from galaxy.web.base.controller import *
from galaxy.web.framework.helpers import time_ago, iff, grids
from galaxy import util, datatypes, web, model
from galaxy.datatypes.display_applications.util import encode_dataset_user, decode_dataset_user
from galaxy.util.sanitize_html import sanitize_html
from galaxy.util import inflector
from galaxy.model.item_attrs import *
from galaxy.web.framework.helpers import to_unicode

import pkg_resources;
pkg_resources.require( "Paste" )
import paste.httpexceptions

if sys.version_info[:2] < ( 2, 6 ):
    zipfile.BadZipFile = zipfile.error
if sys.version_info[:2] < ( 2, 5 ):
    zipfile.LargeZipFile = zipfile.error

tmpd = tempfile.mkdtemp()
comptypes=[]
ziptype = '32'
tmpf = os.path.join( tmpd, 'compression_test.zip' )
try:
    archive = zipfile.ZipFile( tmpf, 'w', zipfile.ZIP_DEFLATED, True )
    archive.close()
    comptypes.append( 'zip' )
    ziptype = '64'
except RuntimeError:
    log.exception( "Compression error when testing zip compression. This option will be disabled for library downloads." )
except (TypeError, zipfile.LargeZipFile):    # ZIP64 is only in Python2.5+.  Remove TypeError when 2.4 support is dropped
    log.warning( 'Max zip file size is 2GB, ZIP64 not supported' )
    comptypes.append( 'zip' )
try:
    os.unlink( tmpf )
except OSError:
    pass
os.rmdir( tmpd )

log = logging.getLogger( __name__ )

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

class HistoryDatasetAssociationListGrid( grids.Grid ):
    # Custom columns for grid.
    class HistoryColumn( grids.GridColumn ):
        def get_value( self, trans, grid, hda):
            return hda.history.name

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
    title = "Saved Datasets"
    model_class = model.HistoryDatasetAssociation
    template='/dataset/grid.mako'
    default_sort_key = "-update_time"
    columns = [
        grids.TextColumn( "Name", key="name",
                            # Link name to dataset's history.
                            link=( lambda item: iff( item.history.deleted, None, dict( operation="switch", id=item.id ) ) ), filterable="advanced", attach_popup=True ),
        HistoryColumn( "History", key="history",
                        link=( lambda item: iff( item.history.deleted, None, dict( operation="switch_history", id=item.id ) ) ) ),
        grids.IndividualTagsColumn( "Tags", key="tags", model_tag_association_class=model.HistoryDatasetAssociationTagAssociation, filterable="advanced", grid_name="HistoryDatasetAssocationListGrid" ),
        StatusColumn( "Status", key="deleted", attach_popup=False ),
        grids.GridColumn( "Last Updated", key="update_time", format=time_ago ),
    ]
    columns.append(
        grids.MulticolFilterColumn(
        "Search",
        cols_to_filter=[ columns[0], columns[2] ],
        key="free-text-search", visible=False, filterable="standard" )
                )
    operations = [
        grids.GridOperation( "Copy to current history", condition=( lambda item: not item.deleted ), async_compatible=False ),
    ]
    standard_filters = []
    default_filter = dict( name="All", deleted="False", tags="All" )
    preserve_state = False
    use_paging = True
    num_rows_per_page = 50
    def build_initial_query( self, trans, **kwargs ):
        # Show user's datasets that are not deleted, not in deleted histories, and not hidden.
        # To filter HDAs by user, need to join model class/HDA and History table so that it is
        # possible to filter by user. However, for dictionary-based filtering to work, need a
        # primary table for the query.
        return trans.sa_session.query( self.model_class ).select_from( self.model_class.table.join( model.History.table ) ) \
                .filter( model.History.user == trans.user ) \
                .filter( self.model_class.deleted==False ) \
                .filter( model.History.deleted==False ) \
                .filter( self.model_class.visible==True )

class DatasetInterface( BaseUIController, UsesAnnotations, UsesHistory, UsesHistoryDatasetAssociation, UsesItemRatings ):

    stored_list_grid = HistoryDatasetAssociationListGrid()

    @web.expose
    def errors( self, trans, id ):
        hda = trans.sa_session.query( model.HistoryDatasetAssociation ).get( id )
        return trans.fill_template( "dataset/errors.mako", hda=hda )
    @web.expose
    def stdout( self, trans, dataset_id=None, **kwargs ):
        trans.response.set_content_type( 'text/plain' )
        try:
            hda = trans.sa_session.query( trans.app.model.HistoryDatasetAssociation ).get( trans.security.decode_id( dataset_id ) )
            assert hda and trans.app.security_agent.can_access_dataset( trans.get_current_user_roles(), hda.dataset )
            job = hda.creating_job_associations[0].job
        except:
            return "Invalid dataset ID or you are not allowed to access this dataset"
        return job.stdout
    @web.expose
    def stderr( self, trans, dataset_id=None, **kwargs ):
        trans.response.set_content_type( 'text/plain' )
        try:
            hda = trans.sa_session.query( trans.app.model.HistoryDatasetAssociation ).get( trans.security.decode_id( dataset_id ) )
            assert hda and trans.app.security_agent.can_access_dataset( trans.get_current_user_roles(), hda.dataset )
            job = hda.creating_job_associations[0].job
        except:
            return "Invalid dataset ID or you are not allowed to access this dataset"
        return job.stderr
    @web.expose
    def report_error( self, trans, id, email='', message="" ):
        smtp_server = trans.app.config.smtp_server
        if smtp_server is None:
            return trans.show_error_message( "Mail is not configured for this galaxy instance" )
        to_address = trans.app.config.error_email_to
        if to_address is None:
            return trans.show_error_message( "Error reporting has been disabled for this galaxy instance" )
        # Get the dataset and associated job
        hda = trans.sa_session.query( model.HistoryDatasetAssociation ).get( id )
        job = hda.creating_job_associations[0].job
        # Get the name of the server hosting the Galaxy instance from which this report originated
        host = trans.request.host
        history_view_link = "%s/history/view?id=%s" % ( str( host ), trans.security.encode_id( hda.history_id ) )
        # Build the email message
        body = string.Template( error_report_template ) \
            .safe_substitute( host=host,
                              dataset_id=hda.dataset_id,
                              history_id=hda.history_id,
                              hid=hda.hid,
                              history_item_name=hda.get_display_name(),
                              history_view_link=history_view_link,
                              job_id=job.id,
                              job_tool_id=job.tool_id,
                              job_command_line=job.command_line,
                              job_stderr=job.stderr,
                              job_stdout=job.stdout,
                              job_info=job.info,
                              job_traceback=job.traceback,
                              email=email,
                              message=message )
        frm = to_address
        # Check email a bit
        email = email.strip()
        parts = email.split()
        if len( parts ) == 1 and len( email ) > 0:
            to = to_address + ", " + email
        else:
            to = to_address
        subject = "Galaxy tool error report from " + email
        # Send it
        try:
            util.send_mail( frm, to, subject, body, trans.app.config )
            return trans.show_ok_message( "Your error report has been sent" )
        except Exception, e:
            return trans.show_error_message( "An error occurred sending the report by email: %s" % str( e ) )

    @web.expose
    def default(self, trans, dataset_id=None, **kwd):
        return 'This link may not be followed from within Galaxy.'

    @web.expose
    def get_metadata_file(self, trans, hda_id, metadata_name):
        """ Allows the downloading of metadata files associated with datasets (eg. bai index for bam files) """
        data = trans.sa_session.query( trans.app.model.HistoryDatasetAssociation ).get( trans.security.decode_id( hda_id ) )
        if not data or not trans.app.security_agent.can_access_dataset( trans.get_current_user_roles(), data.dataset ):
            return trans.show_error_message( "You are not allowed to access this dataset" )

        valid_chars = '.,^_-()[]0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
        fname = ''.join(c in valid_chars and c or '_' for c in data.name)[0:150]

        file_ext = data.metadata.spec.get(metadata_name).get("file_ext", metadata_name)
        trans.response.headers["Content-Type"] = "application/octet-stream"
        trans.response.headers["Content-Disposition"] = 'attachment; filename="Galaxy%s-[%s].%s"' % (data.hid, fname, file_ext)
        return open(data.metadata.get(metadata_name).file_name)

    def _check_dataset(self, trans, hda_id):
        # DEPRECATION: We still support unencoded ids for backward compatibility
        try:
            data = trans.sa_session.query( trans.app.model.HistoryDatasetAssociation ).get( trans.security.decode_id( hda_id) )
            if data is None:
                raise ValueError( 'Invalid reference dataset id: %s.' % hda_id)
        except:
            try:
                data = trans.sa_session.query( trans.app.model.HistoryDatasetAssociation ).get( int( hda_id ) )
            except:
                data = None
        if not data:
            raise paste.httpexceptions.HTTPRequestRangeNotSatisfiable( "Invalid reference dataset id: %s." % str( hda_id ) )
        if not trans.app.security_agent.can_access_dataset( trans.get_current_user_roles(), data.dataset ):
            return trans.show_error_message( "You are not allowed to access this dataset" )
        if data.state == trans.model.Dataset.states.UPLOAD:
            return trans.show_error_message( "Please wait until this dataset finishes uploading before attempting to view it." )
        return data

    @web.expose
    @web.json
    def transfer_status(self, trans, dataset_id, filename=None):
        """ Primarily used for the S3ObjectStore - get the status of data transfer
        if the file is not in cache """
        data = self._check_dataset(trans, dataset_id)
        if isinstance( data, basestring ):
            return data
        log.debug( "Checking transfer status for dataset %s..." % data.dataset.id )

        # Pulling files in extra_files_path into cache is not handled via this
        # method but that's primarily because those files are typically linked to
        # through tool's output page anyhow so tying a JavaScript event that will
        # call this method does not seem doable?
        if data.dataset.external_filename:
            return True
        else:
            return trans.app.object_store.file_ready(data.dataset)

    @web.expose
    def display(self, trans, dataset_id=None, preview=False, filename=None, to_ext=None, chunk=None, **kwd):
        data = self._check_dataset(trans, dataset_id)
        return data.datatype.display_data(trans, data, preview, filename, to_ext, chunk, **kwd)

    @web.expose
    def edit(self, trans, dataset_id=None, filename=None, hid=None, **kwd):
        """Allows user to modify parameters of an HDA."""
        message = None
        status = 'done'
        refresh_frames = []
        error = False
        def __ok_to_edit_metadata( dataset_id ):
            #prevent modifying metadata when dataset is queued or running as input/output
            #This code could be more efficient, i.e. by using mappers, but to prevent slowing down loading a History panel, we'll leave the code here for now
            for job_to_dataset_association in trans.sa_session.query( self.app.model.JobToInputDatasetAssociation ) \
                                                              .filter_by( dataset_id=dataset_id ) \
                                                              .all() \
                                            + trans.sa_session.query( self.app.model.JobToOutputDatasetAssociation ) \
                                                              .filter_by( dataset_id=dataset_id ) \
                                                              .all():
                if job_to_dataset_association.job.state not in [ job_to_dataset_association.job.states.OK, job_to_dataset_association.job.states.ERROR, job_to_dataset_association.job.states.DELETED ]:
                    return False
            return True
        if hid is not None:
            history = trans.get_history()
            # TODO: hid handling
            data = history.datasets[ int( hid ) - 1 ]
            id = None
        elif dataset_id is not None:
            id = trans.app.security.decode_id( dataset_id )
            data = trans.sa_session.query( self.app.model.HistoryDatasetAssociation ).get( id )
        else:
            trans.log_event( "dataset_id and hid are both None, cannot load a dataset to edit" )
            return trans.show_error_message( "You must provide a history dataset id to edit" )
        if data is None:
            trans.log_event( "Problem retrieving dataset (encoded: %s, decoded: %s) with history id %s." % ( str( dataset_id ), str( id ), str( hid ) ) )
            return trans.show_error_message( "History dataset id is invalid" )
        if dataset_id is not None and data.history.user is not None and data.history.user != trans.user:
            trans.log_event( "User attempted to edit an HDA they do not own (encoded: %s, decoded: %s)" % ( dataset_id, id ) )
            # Do not reveal the dataset's existence
            return trans.show_error_message( "History dataset id is invalid" )
        current_user_roles = trans.get_current_user_roles()
        if data.history.user and not data.dataset.has_manage_permissions_roles( trans ):
            # Permission setting related to DATASET_MANAGE_PERMISSIONS was broken for a period of time,
            # so it is possible that some Datasets have no roles associated with the DATASET_MANAGE_PERMISSIONS
            # permission.  In this case, we'll reset this permission to the hda user's private role.
            manage_permissions_action = trans.app.security_agent.get_action( trans.app.security_agent.permitted_actions.DATASET_MANAGE_PERMISSIONS.action )
            permissions = { manage_permissions_action : [ trans.app.security_agent.get_private_user_role( data.history.user ) ] }
            trans.app.security_agent.set_dataset_permission( data.dataset, permissions )
        if trans.app.security_agent.can_access_dataset( current_user_roles, data.dataset ):
            if data.state == trans.model.Dataset.states.UPLOAD:
                return trans.show_error_message( "Please wait until this dataset finishes uploading before attempting to edit its metadata." )
            params = util.Params( kwd, sanitize=False )
            if params.change:
                # The user clicked the Save button on the 'Change data type' form
                if data.datatype.allow_datatype_change and trans.app.datatypes_registry.get_datatype_by_extension( params.datatype ).allow_datatype_change:
                    #prevent modifying datatype when dataset is queued or running as input/output
                    if not __ok_to_edit_metadata( data.id ):
                        message = "This dataset is currently being used as input or output.  You cannot change datatype until the jobs have completed or you have canceled them."
                        error = True
                    else:
                        trans.app.datatypes_registry.change_datatype( data, params.datatype, set_meta = not trans.app.config.set_metadata_externally )
                        trans.sa_session.flush()
                        if trans.app.config.set_metadata_externally:
                            trans.app.datatypes_registry.set_external_metadata_tool.tool_action.execute( trans.app.datatypes_registry.set_external_metadata_tool, trans, incoming = { 'input1':data }, overwrite = False ) #overwrite is False as per existing behavior
                        message = "Changed the type of dataset '%s' to %s" % ( to_unicode( data.name ), params.datatype )
                        refresh_frames=['history']
                else:
                    message = "You are unable to change datatypes in this manner. Changing %s to %s is not allowed." % ( data.extension, params.datatype )
                    error = True
            elif params.save:
                # The user clicked the Save button on the 'Edit Attributes' form
                data.name  = params.name
                data.info  = params.info
                message = ''
                if __ok_to_edit_metadata( data.id ):
                    # The following for loop will save all metadata_spec items
                    for name, spec in data.datatype.metadata_spec.items():
                        if spec.get("readonly"):
                            continue
                        optional = params.get("is_"+name, None)
                        other = params.get("or_"+name, None)
                        if optional and optional == 'true':
                            # optional element... == 'true' actually means it is NOT checked (and therefore omitted)
                            setattr(data.metadata, name, None)
                        else:
                            if other:
                                setattr( data.metadata, name, other )
                            else:
                                setattr( data.metadata, name, spec.unwrap( params.get (name, None) ) )
                    data.datatype.after_setting_metadata( data )
                    # Sanitize annotation before adding it.
                    if params.annotation:
                        annotation = sanitize_html( params.annotation, 'utf-8', 'text/html' )
                        self.add_item_annotation( trans.sa_session, trans.get_user(), data, annotation )
                    # If setting metadata previously failed and all required elements have now been set, clear the failed state.
                    if data._state == trans.model.Dataset.states.FAILED_METADATA and not data.missing_meta():
                        data._state = None
                    trans.sa_session.flush()
                    message = "Attributes updated%s" % message
                    refresh_frames=['history']
                else:
                    trans.sa_session.flush()
                    message = "Attributes updated, but metadata could not be changed because this dataset is currently being used as input or output. You must cancel or wait for these jobs to complete before changing metadata."
                    status = "warning"
                    refresh_frames=['history']
            elif params.detect:
                # The user clicked the Auto-detect button on the 'Edit Attributes' form
                #prevent modifying metadata when dataset is queued or running as input/output
                if not __ok_to_edit_metadata( data.id ):
                    message = "This dataset is currently being used as input or output.  You cannot change metadata until the jobs have completed or you have canceled them."
                    error = True
                else:
                    for name, spec in data.metadata.spec.items():
                        # We need to be careful about the attributes we are resetting
                        if name not in [ 'name', 'info', 'dbkey', 'base_name' ]:
                            if spec.get( 'default' ):
                                setattr( data.metadata, name, spec.unwrap( spec.get( 'default' ) ) )
                    if trans.app.config.set_metadata_externally:
                        message = 'Attributes have been queued to be updated'
                        trans.app.datatypes_registry.set_external_metadata_tool.tool_action.execute( trans.app.datatypes_registry.set_external_metadata_tool, trans, incoming = { 'input1':data } )
                    else:
                        message = 'Attributes updated'
                        data.set_meta()
                        data.datatype.after_setting_metadata( data )
                    trans.sa_session.flush()
                    refresh_frames=['history']
            elif params.convert_data:
                target_type = kwd.get("target_type", None)
                if target_type:
                    message = data.datatype.convert_dataset(trans, data, target_type)
                    refresh_frames=['history']
            elif params.update_roles_button:
                if not trans.user:
                    return trans.show_error_message( "You must be logged in if you want to change permissions." )
                if trans.app.security_agent.can_manage_dataset( current_user_roles, data.dataset ):
                    access_action = trans.app.security_agent.get_action( trans.app.security_agent.permitted_actions.DATASET_ACCESS.action )
                    manage_permissions_action = trans.app.security_agent.get_action( trans.app.security_agent.permitted_actions.DATASET_MANAGE_PERMISSIONS.action )
                    # The user associated the DATASET_ACCESS permission on the dataset with 1 or more roles.  We
                    # need to ensure that they did not associate roles that would cause accessibility problems.
                    permissions, in_roles, error, message = \
                    trans.app.security_agent.derive_roles_from_access( trans, data.dataset.id, 'root', **kwd )
                    if error:
                        # Keep the original role associations for the DATASET_ACCESS permission on the dataset.
                        permissions[ access_action ] = data.dataset.get_access_roles( trans )
                        status = 'error'
                    else:
                        error = trans.app.security_agent.set_all_dataset_permissions( data.dataset, permissions )
                        if error:
                            message += error
                            status = 'error'
                        else:
                            message = 'Your changes completed successfully.'
                    trans.sa_session.refresh( data.dataset )
                else:
                    message = "You are not authorized to change this dataset's permissions"
                    error = True
            else:
                if "dbkey" in data.datatype.metadata_spec and not data.metadata.dbkey:
                    # Copy dbkey into metadata, for backwards compatability
                    # This looks like it does nothing, but getting the dbkey
                    # returns the metadata dbkey unless it is None, in which
                    # case it resorts to the old dbkey.  Setting the dbkey
                    # sets it properly in the metadata
                    #### This is likely no longer required, since the dbkey exists entirely within metadata (the old_dbkey field is gone): REMOVE ME?
                    data.metadata.dbkey = data.dbkey
            # let's not overwrite the imported datatypes module with the variable datatypes?
            # the built-in 'id' is overwritten in lots of places as well
            ldatatypes = [ dtype_name for dtype_name, dtype_value in trans.app.datatypes_registry.datatypes_by_extension.iteritems() if dtype_value.allow_datatype_change ]
            ldatatypes.sort()
            all_roles = trans.app.security_agent.get_legitimate_roles( trans, data.dataset, 'root' )
            if error:
                status = 'error'
            return trans.fill_template( "/dataset/edit_attributes.mako",
                                        data=data,
                                        data_annotation=self.get_item_annotation_str( trans.sa_session, trans.user, data ),
                                        datatypes=ldatatypes,
                                        current_user_roles=current_user_roles,
                                        all_roles=all_roles,
                                        message=message,
                                        status=status,
                                        dataset_id=dataset_id,
                                        refresh_frames=refresh_frames )
        else:
            return trans.show_error_message( "You do not have permission to edit this dataset's ( id: %s ) information." % str( dataset_id ) )

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
                if operation == "switch" or operation == "switch_history":
                    # Switch to a history that the HDA resides in.

                    # Convert hda to histories.
                    histories = []
                    for hda in hdas:
                        histories.append( hda.history )

                    # Use history controller to switch the history. TODO: is this reasonable?
                    status, message = trans.webapp.controllers['history']._list_switch( trans, histories )

                    # Current history changed, refresh history frame; if switching to a dataset, set hda seek.
                    trans.template_context['refresh_frames'] = ['history']
                    if operation == "switch":
                        hda_ids = [ trans.security.encode_id( hda.id ) for hda in hdas ]
                        trans.template_context[ 'seek_hda_ids' ] = hda_ids
                elif operation == "copy to current history":
                    # Copy a dataset to the current history.
                    target_histories = [ trans.get_history() ]
                    status, message = self._copy_datasets( trans, hda_ids, target_histories )

                    # Current history changed, refresh history frame.
                    trans.template_context['refresh_frames'] = ['history']

        # Render the list view
        return self.stored_list_grid( trans, status=status, message=message, **kwargs )

    @web.expose
    def imp( self, trans, dataset_id=None, **kwd ):
        """ Import another user's dataset via a shared URL; dataset is added to user's current history. """
        msg = ""

        # Set referer message.
        referer = trans.request.referer
        if referer is not "":
            referer_message = "<a href='%s'>return to the previous page</a>" % referer
        else:
            referer_message = "<a href='%s'>go to Galaxy's start page</a>" % url_for( '/' )

        # Error checking.
        if not dataset_id:
            return trans.show_error_message( "You must specify a dataset to import. You can %s." % referer_message, use_panels=True )

        # Do import.
        cur_history = trans.get_history( create=True )
        status, message = self._copy_datasets( trans, [ dataset_id ], [ cur_history ], imported=True )
        message = "Dataset imported. <br>You can <a href='%s'>start using the dataset</a> or %s." % ( url_for('/'),  referer_message )
        return trans.show_message( message, type=status, use_panels=True )

    @web.expose
    @web.json
    @web.require_login( "use Galaxy datasets" )
    def get_name_and_link_async( self, trans, id=None ):
        """ Returns dataset's name and link. """
        dataset = self.get_dataset( trans, id, False, True )
        return_dict = { "name" : dataset.name, "link" : url_for( action="display_by_username_and_slug", username=dataset.history.user.username, slug=trans.security.encode_id( dataset.id ) ) }
        return return_dict

    @web.expose
    def get_embed_html_async( self, trans, id ):
        """ Returns HTML for embedding a dataset in a page. """
        dataset = self.get_dataset( trans, id, False, True )
        if dataset:
            return "Embedded Dataset '%s'" % dataset.name

    @web.expose
    @web.require_login( "use Galaxy datasets" )
    def set_accessible_async( self, trans, id=None, accessible=False ):
        """ Does nothing because datasets do not have an importable/accessible attribute. This method could potentially set another attribute. """
        return

    @web.expose
    @web.require_login( "rate items" )
    @web.json
    def rate_async( self, trans, id, rating ):
        """ Rate a dataset asynchronously and return updated community data. """

        dataset = self.get_dataset( trans, id, check_ownership=False, check_accessible=True )
        if not dataset:
            return trans.show_error_message( "The specified dataset does not exist." )

        # Rate dataset.
        dataset_rating = self.rate_item( rate_item, trans.get_user(), dataset, rating )

        return self.get_ave_item_rating_data( trans.sa_session, dataset )

    @web.expose
    def display_by_username_and_slug( self, trans, username, slug, filename=None, preview=True ):
        """ Display dataset by username and slug; because datasets do not yet have slugs, the slug is the dataset's id. """
        dataset = self.get_dataset( trans, slug, False, True )
        if dataset:
            # Filename used for composite types.
            if filename:
                return self.display( trans, dataset_id=slug, filename=filename)

            truncated, dataset_data = self.get_data( dataset, preview )
            dataset.annotation = self.get_item_annotation_str( trans.sa_session, dataset.history.user, dataset )

            # If data is binary or an image, stream without template; otherwise, use display template.
            # TODO: figure out a way to display images in display template.
            if isinstance(dataset.datatype, datatypes.binary.Binary) or isinstance(dataset.datatype, datatypes.images.Image)  or isinstance(dataset.datatype, datatypes.images.Html):
                trans.response.set_content_type( dataset.get_mime() )
                return open( dataset.file_name )
            else:
                # Get rating data.
                user_item_rating = 0
                if trans.get_user():
                    user_item_rating = self.get_user_item_rating( trans.sa_session, trans.get_user(), dataset )
                    if user_item_rating:
                        user_item_rating = user_item_rating.rating
                    else:
                        user_item_rating = 0
                ave_item_rating, num_ratings = self.get_ave_item_rating_data( trans.sa_session, dataset )

                return trans.fill_template_mako( "/dataset/display.mako", item=dataset, item_data=dataset_data, truncated=truncated,
                                                user_item_rating = user_item_rating, ave_item_rating=ave_item_rating, num_ratings=num_ratings )
        else:
            raise web.httpexceptions.HTTPNotFound()

    @web.expose
    def get_item_content_async( self, trans, id ):
        """ Returns item content in HTML format. """

        dataset = self.get_dataset( trans, id, False, True )
        if dataset is None:
            raise web.httpexceptions.HTTPNotFound()
        truncated, dataset_data = self.get_data( dataset, preview=True )
        # Get annotation.
        dataset.annotation = self.get_item_annotation_str( trans.sa_session, trans.user, dataset )
        return trans.stream_template_mako( "/dataset/item_content.mako", item=dataset, item_data=dataset_data, truncated=truncated )

    @web.expose
    def annotate_async( self, trans, id, new_annotation=None, **kwargs ):
        dataset = self.get_dataset( trans, id, False, True )
        if not dataset:
            web.httpexceptions.HTTPNotFound()
        if dataset and new_annotation:
            # Sanitize annotation before adding it.
            new_annotation = sanitize_html( new_annotation, 'utf-8', 'text/html' )
            self.add_item_annotation( trans.sa_session, trans.get_user(), dataset, new_annotation )
            trans.sa_session.flush()
            return new_annotation

    @web.expose
    def get_annotation_async( self, trans, id ):
        dataset = self.get_dataset( trans, id, False, True )
        if not dataset:
            web.httpexceptions.HTTPNotFound()
        return self.get_item_annotation_str( trans.sa_session, trans.user, dataset )

    @web.expose
    def display_at( self, trans, dataset_id, filename=None, **kwd ):
        """Sets up a dataset permissions so it is viewable at an external site"""
        site = filename
        data = trans.sa_session.query( trans.app.model.HistoryDatasetAssociation ).get( dataset_id )
        if not data:
            raise paste.httpexceptions.HTTPRequestRangeNotSatisfiable( "Invalid reference dataset id: %s." % str( dataset_id ) )
        if 'display_url' not in kwd or 'redirect_url' not in kwd:
            return trans.show_error_message( 'Invalid parameters specified for "display at" link, please contact a Galaxy administrator' )
        try:
              redirect_url = kwd['redirect_url'] % urllib.quote_plus( kwd['display_url'] )
        except:
              redirect_url = kwd['redirect_url'] # not all will need custom text
        current_user_roles = trans.get_current_user_roles()
        if trans.app.security_agent.dataset_is_public( data.dataset ):
            return trans.response.send_redirect( redirect_url ) # anon access already permitted by rbac
        if trans.app.security_agent.can_access_dataset( current_user_roles, data.dataset ):
            trans.app.host_security_agent.set_dataset_permissions( data, trans.user, site )
            return trans.response.send_redirect( redirect_url )
        else:
            return trans.show_error_message( "You are not allowed to view this dataset at external sites.  Please contact your Galaxy administrator to acquire management permissions for this dataset." )

    @web.expose
    def display_application( self, trans, dataset_id=None, user_id=None, app_name = None, link_name = None, app_action = None, action_param = None, **kwds ):
        """Access to external display applications"""
        if kwds:
            log.debug( "Unexpected Keywords passed to display_application: %s" % kwds ) #route memory?
        #decode ids
        data, user = decode_dataset_user( trans, dataset_id, user_id )
        if not data:
            raise paste.httpexceptions.HTTPRequestRangeNotSatisfiable( "Invalid reference dataset id: %s." % str( dataset_id ) )
        if user is None:
            user = trans.user
        if user:
            user_roles = user.all_roles()
        else:
            user_roles = []
        # Decode application name and link name
        app_name = urllib.unquote_plus( app_name )
        link_name = urllib.unquote_plus( link_name )
        if None in [ app_name, link_name ]:
            return trans.show_error_message( "A display application name and link name must be provided." )
        if trans.app.security_agent.can_access_dataset( user_roles, data.dataset ):
            msg = []
            refresh = False
            display_app = trans.app.datatypes_registry.display_applications.get( app_name )
            assert display_app, "Unknown display application has been requested: %s" % app_name
            dataset_hash, user_hash = encode_dataset_user( trans, data, user )
            display_link = display_app.get_link( link_name, data, dataset_hash, user_hash, trans )
            assert display_link, "Unknown display link has been requested: %s" % link_name
            if data.state == data.states.ERROR:
                msg.append( ( 'This dataset is in an error state, you cannot view it at an external display application.', 'error' ) )
            elif data.deleted:
                msg.append( ( 'This dataset has been deleted, you cannot view it at an external display application.', 'error' ) )
            elif data.state != data.states.OK:
                msg.append( ( 'You must wait for this dataset to be created before you can view it at an external display application.', 'info' ) )
                refresh = True
            else:
                #We have permissions, dataset is not deleted and is in OK state, allow access
                if display_link.display_ready():
                    if app_action in [ 'data', 'param' ]:
                        assert action_param, "An action param must be provided for a data or param action"
                        #data is used for things with filenames that could be passed off to a proxy
                        #in case some display app wants all files to be in the same 'directory',
                        #data can be forced to param, but not the other way (no filename for other direction)
                        #get param name from url param name
                        try:
                            action_param = display_link.get_param_name_by_url( action_param )
                        except ValueError, e:
                            log.debug( e )
                            return paste.httpexceptions.HTTPNotFound( str( e ) )
                        value = display_link.get_param_value( action_param )
                        assert value, "An invalid parameter name was provided: %s" % action_param
                        assert value.parameter.viewable, "This parameter is not viewable."
                        if value.parameter.type == 'data':
                            content_length = os.path.getsize( value.file_name )
                            rval = open( value.file_name )
                        else:
                            rval = str( value )
                            content_length = len( rval )
                        trans.response.set_content_type( value.mime_type() )
                        trans.response.headers[ 'Content-Length' ] = content_length
                        return rval
                    elif app_action == None:
                        #redirect user to url generated by display link
                        return trans.response.send_redirect( display_link.display_url() )
                    else:
                        msg.append( ( 'Invalid action provided: %s' % app_action, 'error' ) )
                else:
                    if app_action == None:
                        if trans.history != data.history:
                            msg.append( ( 'You must import this dataset into your current history before you can view it at the desired display application.', 'error' ) )
                        else:
                            refresh = True
                            msg.append( ( 'This display application is being prepared.', 'info' ) )
                            if not display_link.preparing_display():
                                display_link.prepare_display()
                    else:
                        raise Exception( 'Attempted a view action (%s) on a non-ready display application' % app_action )
            return trans.fill_template_mako( "dataset/display_application/display.mako", msg = msg, display_app = display_app, display_link = display_link, refresh = refresh )
        return trans.show_error_message( 'You do not have permission to view this dataset at an external display application.' )

    def _delete( self, trans, dataset_id ):
        message = None
        status = 'done'
        id = None
        try:
            id = trans.app.security.decode_id( dataset_id )
            history = trans.get_history()
            hda = trans.sa_session.query( self.app.model.HistoryDatasetAssociation ).get( id )
            assert hda, 'Invalid HDA: %s' % id
            # Walk up parent datasets to find the containing history
            topmost_parent = hda
            while topmost_parent.parent:
                topmost_parent = topmost_parent.parent
            assert topmost_parent in trans.history.datasets, "Data does not belong to current history"
            # Mark deleted and cleanup
            hda.mark_deleted()
            hda.clear_associated_files()
            trans.log_event( "Dataset id %s marked as deleted" % str(id) )
            if hda.parent_id is None and len( hda.creating_job_associations ) > 0:
                # Mark associated job for deletion
                job = hda.creating_job_associations[0].job
                if job.state in [ self.app.model.Job.states.QUEUED, self.app.model.Job.states.RUNNING, self.app.model.Job.states.NEW ]:
                    # Are *all* of the job's other output datasets deleted?
                    if job.check_if_output_datasets_deleted():
                        job.mark_deleted( self.app.config.track_jobs_in_database )
                        self.app.job_manager.job_stop_queue.put( job.id )
            trans.sa_session.flush()
        except Exception, e:
            msg = 'HDA deletion failed (encoded: %s, decoded: %s)' % ( dataset_id, id )
            log.exception( msg )
            trans.log_event( msg )
            message = 'Dataset deletion failed'
            status = 'error'
        return ( message, status )

    def _undelete( self, trans, dataset_id ):
        message = None
        status = 'done'
        id = None
        try:
            id = trans.app.security.decode_id( dataset_id )
            history = trans.get_history()
            hda = trans.sa_session.query( self.app.model.HistoryDatasetAssociation ).get( id )
            assert hda and hda.undeletable, 'Invalid HDA: %s' % id
            # Walk up parent datasets to find the containing history
            topmost_parent = hda
            while topmost_parent.parent:
                topmost_parent = topmost_parent.parent
            assert topmost_parent in history.datasets, "Data does not belong to current history"
            # Mark undeleted
            hda.mark_undeleted()
            trans.sa_session.flush()
            trans.log_event( "Dataset id %s has been undeleted" % str(id) )
        except Exception, e:
            msg = 'HDA undeletion failed (encoded: %s, decoded: %s)' % ( dataset_id, id )
            log.exception( msg )
            trans.log_event( msg )
            message = 'Dataset undeletion failed'
            status = 'error'
        return ( message, status )

    def _unhide( self, trans, dataset_id ):
        try:
            id = trans.app.security.decode_id( dataset_id )
        except:
            return False
        history = trans.get_history()
        hda = trans.sa_session.query( self.app.model.HistoryDatasetAssociation ).get( id )
        if hda:
            # Walk up parent datasets to find the containing history
            topmost_parent = hda
            while topmost_parent.parent:
                topmost_parent = topmost_parent.parent
            assert topmost_parent in history.datasets, "Data does not belong to current history"
            # Mark undeleted
            hda.mark_unhidden()
            trans.sa_session.flush()
            trans.log_event( "Dataset id %s has been unhidden" % str(id) )
            return True
        return False

    def _purge( self, trans, dataset_id ):
        message = None
        status = 'done'
        try:
            id = trans.app.security.decode_id( dataset_id )
            history = trans.get_history()
            user = trans.get_user()
            hda = trans.sa_session.query( self.app.model.HistoryDatasetAssociation ).get( id )
            # Invalid HDA
            assert hda, 'Invalid history dataset ID'
            # Walk up parent datasets to find the containing history
            topmost_parent = hda
            while topmost_parent.parent:
                topmost_parent = topmost_parent.parent
            assert topmost_parent in history.datasets, "Data does not belong to current history"
            # If the user is anonymous, make sure the HDA is owned by the current session.
            if not user:
                assert trans.galaxy_session.current_history_id == trans.history.id, 'Invalid history dataset ID'
            # If the user is known, make sure the HDA is owned by the current user.
            else:
                assert topmost_parent.history.user == trans.user, 'Invalid history dataset ID'
            # HDA is not deleted
            assert hda.deleted, 'History dataset is not marked as deleted'
            # HDA is purgeable
            # Decrease disk usage first
            if user:
                user.total_disk_usage -= hda.quota_amount( user )
            # Mark purged
            hda.purged = True
            trans.sa_session.add( hda )
            trans.log_event( "HDA id %s has been purged" % hda.id )
            trans.sa_session.flush()
            # Don't delete anything if there are active HDAs or any LDDAs, even if
            # the LDDAs are deleted.  Let the cleanup scripts get it in the latter
            # case.
            if hda.dataset.user_can_purge:
                try:
                    hda.dataset.full_delete()
                    trans.log_event( "Dataset id %s has been purged upon the the purge of HDA id %s" % ( hda.dataset.id, hda.id ) )
                    trans.sa_session.add( hda.dataset )
                except:
                    log.exception( 'Unable to purge dataset (%s) on purge of HDA (%s):' % ( hda.dataset.id, hda.id ) )
            trans.sa_session.flush()
        except Exception, e:
            msg = 'HDA purge failed (encoded: %s, decoded: %s)' % ( dataset_id, id )
            log.exception( msg )
            trans.log_event( msg )
            message = 'Dataset removal from disk failed'
            status = 'error'
        return ( message, status )

    @web.expose
    def delete( self, trans, dataset_id, filename, show_deleted_on_refresh = False ):
        message, status = self._delete( trans, dataset_id )
        return trans.response.send_redirect( web.url_for( controller='root', action='history', show_deleted=show_deleted_on_refresh, message=message, status=status ) )

    @web.expose
    def delete_async( self, trans, dataset_id, filename ):
        message, status = self._delete( trans, dataset_id )
        if status == 'done':
            return "OK"
        else:
            raise Exception( message )

    @web.expose
    def undelete( self, trans, dataset_id, filename ):
        message, status = self._undelete( trans, dataset_id )
        return trans.response.send_redirect( web.url_for( controller='root', action='history', show_deleted = True, message=message, status=status ) )

    @web.expose
    def undelete_async( self, trans, dataset_id, filename ):
        message, status =self._undelete( trans, dataset_id )
        if status == 'done':
            return "OK"
        else:
            raise Exception( message )

    @web.expose
    def unhide( self, trans, dataset_id, filename ):
        if self._unhide( trans, dataset_id ):
            return trans.response.send_redirect( web.url_for( controller='root', action='history', show_hidden = True ) )
        raise Exception( "Error unhiding" )

    @web.expose
    def purge( self, trans, dataset_id, filename, show_deleted_on_refresh = False ):
        if trans.app.config.allow_user_dataset_purge:
            message, status = self._purge( trans, dataset_id )
        else:
            message = "Removal of datasets by users is not allowed in this Galaxy instance.  Please contact your Galaxy administrator."
            status = 'error'
        return trans.response.send_redirect( web.url_for( controller='root', action='history', show_deleted=show_deleted_on_refresh, message=message, status=status ) )

    @web.expose
    def purge_async( self, trans, dataset_id, filename ):
        if trans.app.config.allow_user_dataset_purge:
            message, status = self._purge( trans, dataset_id )
        else:
            message = "Removal of datasets by users is not allowed in this Galaxy instance.  Please contact your Galaxy administrator."
            status = 'error'
        if status == 'done':
            return "OK"
        else:
            raise Exception( message )

    @web.expose
    def show_params( self, trans, dataset_id=None, from_noframe=None, **kwd ):
        """
        Show the parameters used for an HDA
        """

        def source_dataset_chain( dataset, lst ):
            try:
                cp_from_ldda = dataset.copied_from_library_dataset_dataset_association
                cp_from_hda  = dataset.copied_from_history_dataset_association
                if cp_from_ldda:
                    lst.append( (cp_from_ldda, "(Data Library)") )
                    return source_dataset_chain( cp_from_ldda, lst )
                elif cp_from_hda:
                    lst.append( (cp_from_hda, cp_from_hda.history.name) )
                    return source_dataset_chain( cp_from_hda, lst )
            except:
                pass
            return lst

        hda = trans.sa_session.query( trans.app.model.HistoryDatasetAssociation ).get( trans.security.decode_id( dataset_id ) )
        if not hda:
            raise paste.httpexceptions.HTTPRequestRangeNotSatisfiable( "Invalid reference dataset id: %s." % str( dataset_id ) )
        if not trans.app.security_agent.can_access_dataset( trans.get_current_user_roles(), hda.dataset ):
            return trans.show_error_message( "You are not allowed to access this dataset" )

        # Get the associated job, if any. If this hda was copied from another,
        # we need to find the job that created the origial hda
        params_objects = None
        tool = None
        job_hda = hda
        while job_hda.copied_from_history_dataset_association:
            job_hda = job_hda.copied_from_history_dataset_association
        if job_hda.creating_job_associations:
            job = None
            for assoc in job_hda.creating_job_associations:
                job = assoc.job
                break
            if job:
                # Get the tool object
                try:
                    # Load the tool
                    toolbox = self.get_toolbox()
                    tool = toolbox.get_tool( job.tool_id )
                    assert tool is not None, 'Requested tool has not been loaded.'
                    params_objects = job.get_param_values( trans.app )
                except:
                    pass

        inherit_chain = source_dataset_chain(hda, [])
        return trans.fill_template( "show_params.mako", inherit_chain=inherit_chain, history=trans.get_history(), hda=hda, tool=tool, params_objects=params_objects )

    @web.expose
    def copy_datasets( self, trans, source_history=None, source_dataset_ids="", target_history_id=None, target_history_ids="", new_history_name="", do_copy=False, **kwd ):
        params = util.Params( kwd )
        user = trans.get_user()
        if source_history is not None:
            history = self.get_history(trans, source_history)
        else:
            history = trans.get_history()
        refresh_frames = []
        if source_dataset_ids:
            if not isinstance( source_dataset_ids, list ):
                source_dataset_ids = source_dataset_ids.split(",")
            source_dataset_ids = set(map( trans.security.decode_id, source_dataset_ids ))
        else:
            source_dataset_ids = []
        if target_history_id:
            target_history_ids = [ trans.security.decode_id(target_history_id) ]
        elif target_history_ids:
            if not isinstance( target_history_ids, list ):
                target_history_ids = target_history_ids.split(",")
            target_history_ids = set([ trans.security.decode_id(h) for h in target_history_ids if h ])
        else:
            target_history_ids = []
        done_msg = error_msg = ""
        new_history = None
        if do_copy:
            invalid_datasets = 0
            if not source_dataset_ids or not ( target_history_ids or new_history_name ):
                error_msg = "You must provide both source datasets and target histories. "
            else:
                if new_history_name:
                    new_history = trans.app.model.History()
                    new_history.name = new_history_name
                    new_history.user = user
                    trans.sa_session.add( new_history )
                    trans.sa_session.flush()
                    target_history_ids.append( new_history.id )
                if user:
                    target_histories = [ hist for hist in map( trans.sa_session.query( trans.app.model.History ).get, target_history_ids ) if ( hist is not None and hist.user == user )]
                else:
                    target_histories = [ history ]
                if len( target_histories ) != len( target_history_ids ):
                    error_msg = error_msg + "You do not have permission to add datasets to %i requested histories.  " % ( len( target_history_ids ) - len( target_histories ) )
                source_hdas = map( trans.sa_session.query( trans.app.model.HistoryDatasetAssociation ).get, source_dataset_ids )
                source_hdas.sort(key=lambda hda: hda.hid)
                for hda in source_hdas:
                    if hda is None:
                        error_msg = error_msg + "You tried to copy a dataset that does not exist. "
                        invalid_datasets += 1
                    elif hda.history != history:
                        error_msg = error_msg + "You tried to copy a dataset which is not in your current history. "
                        invalid_datasets += 1
                    else:
                        for hist in target_histories:
                            hist.add_dataset( hda.copy( copy_children = True ) )
                if history in target_histories:
                    refresh_frames = ['history']
                trans.sa_session.flush()
                hist_names_str = ", ".join( ['<a href="%s" target="_top">%s</a>' %
                                            ( url_for( controller="history", action="switch_to_history", \
                                                        hist_id=trans.security.encode_id( hist.id ) ), hist.name ) \
                                                        for hist in target_histories ] )
                num_source = len( source_dataset_ids ) - invalid_datasets
                num_target = len(target_histories)
                done_msg = "%i %s copied to %i %s: %s." % (num_source, inflector.cond_plural(num_source, "dataset"), num_target, inflector.cond_plural(num_target, "history"), hist_names_str )
                trans.sa_session.refresh( history )
        source_datasets = history.visible_datasets
        target_histories = [history]
        if user:
           target_histories = user.active_histories
        return trans.fill_template( "/dataset/copy_view.mako",
                                    source_history = history,
                                    current_history = trans.get_history(),
                                    source_dataset_ids = source_dataset_ids,
                                    target_history_id = target_history_id,
                                    target_history_ids = target_history_ids,
                                    source_datasets = source_datasets,
                                    target_histories = target_histories,
                                    new_history_name = new_history_name,
                                    done_msg = done_msg,
                                    error_msg = error_msg,
                                    refresh_frames = refresh_frames )

    def _copy_datasets( self, trans, dataset_ids, target_histories, imported=False ):
        """ Helper method for copying datasets. """
        user = trans.get_user()
        done_msg = error_msg = ""

        invalid_datasets = 0
        if not dataset_ids or not target_histories:
            error_msg = "You must provide both source datasets and target histories."
        else:
            # User must own target histories to copy datasets to them.
            for history in target_histories:
                if user != history.user:
                    error_msg = error_msg + "You do not have permission to add datasets to %i requested histories.  " % ( len( target_histories ) )
            for dataset_id in dataset_ids:
                data = self.get_dataset( trans, dataset_id, False, True )
                if data is None:
                    error_msg = error_msg + "You tried to copy a dataset that does not exist or that you do not have access to.  "
                    invalid_datasets += 1
                else:
                    for hist in target_histories:
                        dataset_copy = data.copy( copy_children = True )
                        if imported:
                            dataset_copy.name = "imported: " + dataset_copy.name
                        hist.add_dataset( dataset_copy )
            trans.sa_session.flush()
            num_datasets_copied = len( dataset_ids ) - invalid_datasets
            done_msg = "%i dataset%s copied to %i histor%s." % \
                ( num_datasets_copied, iff( num_datasets_copied == 1, "", "s"), len( target_histories ), iff( len ( target_histories ) == 1, "y", "ies") )
            trans.sa_session.refresh( history )

        if error_msg != "":
            status = ERROR
            message = error_msg
        else:
            status = SUCCESS
            message = done_msg
        return status, message
