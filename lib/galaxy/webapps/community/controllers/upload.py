import sys, os, shutil, logging, urllib2
from galaxy.web.base.controller import *
from galaxy.web.framework.helpers import time_ago, iff, grids
from galaxy.model.orm import *
from galaxy.webapps.community import datatypes
from common import get_categories, get_category, get_versions

log = logging.getLogger( __name__ )

# States for passing messages
SUCCESS, INFO, WARNING, ERROR = "done", "info", "warning", "error"

class UploadError( Exception ):
    pass

class UploadController( BaseController ):
    
    @web.expose
    @web.require_login( 'upload', use_panels=True, webapp='community' )
    def upload( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        category_ids = util.listify( params.get( 'category_id', '' ) )
        replace_id = params.get( 'replace_id', None )
        replace_version = None
        uploaded_file = None
        categories = get_categories( trans )
        if not get_categories( trans ):
            return trans.response.send_redirect( web.url_for( controller='tool',
                                                              action='browse_tools',
                                                              cntrller='tool',
                                                              message='No categories have been configured in this instance of the Galaxy Community.  An administrator needs to create some via the Administrator control panel before anything can be uploaded',
                                                              status='error' ) )
        elif params.file_data == '' and params.url.strip() == '':
            message = 'No files were entered on the upload form.'
            status = 'error'
        elif params.file_data == '':
            try:
                uploaded_file = urllib2.urlopen( params.url.strip() )
            except ( ValueError, urllib2.HTTPError ), e:
                message = 'An error occurred trying to retrieve the URL entered on the upload form: %s' % e
                status = 'error'
            except urllib2.URLError, e:
                message = 'An error occurred trying to retrieve the URL entered on the upload form: %s' % e.reason
                status = 'error'
        elif params.file_data not in ( '', None ):
            uploaded_file = params.file_data.file
        if params.upload_button and uploaded_file:
            datatype = trans.app.datatypes_registry.get_datatype_by_extension( params.upload_type )
            if datatype is None:
                message = 'An unknown file type was selected.  This should not be possible, please report the error.'
                status = 'error'
            else:
                try:
                    # Initialize the tool object
                    meta = datatype.verify( uploaded_file )
                    meta.user = trans.user
                    meta.guid = trans.app.security.get_new_guid()
                    obj = datatype.create_model_object( meta )
                    trans.sa_session.add( obj )
                    if isinstance( obj, trans.app.model.Tool ):
                        existing = trans.sa_session.query( trans.app.model.Tool ).filter_by( tool_id = meta.id ).all()
                        if existing and replace_id is None:
                            raise UploadError( 'A tool with the same ID already exists.  If you are trying to update this tool to a new version, please use the upload form on the "Edit Tool" page.  Otherwise, please choose a new ID.' )
                        elif existing:
                            replace_version = trans.sa_session.query( trans.app.model.Tool ).get( int( trans.app.security.decode_id( replace_id ) ) )
                            if replace_version.newer_version:
                                # If the user has picked an old version, switch to the newest version
                                replace_version = get_versions( trans, replace_version )[0]
                            if trans.user != replace_version.user:
                                raise UploadError( 'You are not the owner of this tool and may not upload new versions of it.' )
                            if replace_version.tool_id != meta.id:
                                raise UploadError( 'The new tool id (%s) does not match the old tool id (%s).  Please check the tool XML file' % ( meta.id, replace_version.tool_id ) )
                            for old_version in get_versions( trans, replace_version ):
                                if old_version.version == meta.version:
                                    raise UploadError( 'The new version (%s) matches an old version.  Please check your version in the tool XML file' % meta.version )
                                if old_version.is_new():
                                    raise UploadError( 'There is an existing version of this tool which is unsubmitted.  Please either <a href="%s">submit or delete it</a> before uploading a new version.' % url_for( controller='common',
                                                                                                                                                                                                                        action='view_tool',
                                                                                                                                                                                                                        cntrller='tool',
                                                                                                                                                                                                                        id=trans.app.security.encode_id( old_version.id ) ) )
                                if old_version.is_waiting():
                                    raise UploadError( 'There is an existing version of this tool which is waiting for administrative approval.  Please contact an administrator for help.' )
                            # Defer setting the id since the newer version id doesn't exist until the new Tool object is flushed
                        if category_ids:
                            for category_id in category_ids:
                                category = trans.app.model.Category.get( trans.security.decode_id( category_id ) )
                                # Initialize the tool category
                                tca = trans.app.model.ToolCategoryAssociation( obj, category )
                                trans.sa_session.add( tca )
                        # Initialize the tool event
                        event = trans.app.model.Event( state=trans.app.model.Tool.states.NEW )
                        tea = trans.app.model.ToolEventAssociation( obj, event )
                        trans.sa_session.add_all( ( event, tea ) )
                    trans.sa_session.flush()
                    if replace_version and replace_id:
                        replace_version.newer_version_id = obj.id
                        trans.sa_session.flush()
                    try:
                        os.link( uploaded_file.name, obj.file_name )
                    except OSError:
                        shutil.copy( uploaded_file.name, obj.file_name )
                    # We're setting cntrller to 'tool' since that is the only controller from which we can upload
                    return trans.response.send_redirect( web.url_for( controller='common',
                                                                      action='edit_tool',
                                                                      cntrller='tool',
                                                                      id=trans.app.security.encode_id( obj.id ),
                                                                      message='Uploaded %s' % meta.message,
                                                                      status='done' ) )
                except ( datatypes.DatatypeVerificationError, UploadError ), e:
                    message = str( e )
                    status = 'error'
                uploaded_file.close()
        elif replace_id is not None:
            replace_version = trans.sa_session.query( trans.app.model.Tool ).get( int( trans.app.security.decode_id( replace_id ) ) )
            old_version = None
            for old_version in get_versions( trans, replace_version ):
                if old_version.is_new():
                    message = 'There is an existing version of this tool which is unsubmitted.  Please either submit or delete it before uploading a new version.'
                    break
                if old_version.is_waiting():
                    message = 'There is an existing version of this tool which is waiting for administrative approval.  Please contact an administrator for help.'
                    break
            else:
                old_version = None
            if old_version is not None:
                return trans.response.send_redirect( web.url_for( controller='common',
                                                                  action='view_tool',
                                                                  cntrller='tool',
                                                                  id=trans.app.security.encode_id( old_version.id ),
                                                                  message=message,
                                                                  status='error' ) )
        selected_upload_type = params.get( 'type', 'tool' )
        selected_categories = [ trans.security.decode_id( id ) for id in category_ids ]
        return trans.fill_template( '/webapps/community/upload/upload.mako',
                                    message=message,
                                    status=status,
                                    selected_upload_type=selected_upload_type,
                                    upload_types=trans.app.datatypes_registry.get_datatypes_for_select_list(),
                                    replace_id=replace_id,
                                    selected_categories=selected_categories,
                                    categories=get_categories( trans ) )
