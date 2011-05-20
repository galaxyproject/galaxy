import sys, os, shutil, logging, urllib2
from galaxy.web.base.controller import *
from galaxy.web.framework.helpers import time_ago, iff, grids
from galaxy.model.orm import *
from galaxy.web.form_builder import SelectField, build_select_field
from galaxy.webapps.community import datatypes
from common import get_categories, get_category, get_versions

log = logging.getLogger( __name__ )

# States for passing messages
SUCCESS, INFO, WARNING, ERROR = "done", "info", "warning", "error"

class UploadError( Exception ):
    pass

class ToolUploadController( BaseController ):
    
    @web.expose
    @web.require_login( 'upload', use_panels=True, webapp='community' )
    def upload( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        category_ids = util.listify( params.get( 'category_id', '' ) )
        replace_id = params.get( 'replace_id', None )
        if replace_id:
            replace_version = trans.sa_session.query( trans.app.model.Tool ).get( trans.security.decode_id( replace_id ) )
            upload_type = replace_version.type
        else:
            replace_version = None
            upload_type = params.get( 'upload_type', 'tool' )
        uploaded_file = None
        categories = get_categories( trans )
        if not categories:
            message = 'No categories have been configured in this instance of the Galaxy Tool Shed.  ' + \
                'An administrator needs to create some via the Administrator control panel before anything can be uploaded',
            status = 'error'
            return trans.response.send_redirect( web.url_for( controller='tool',
                                                              action='browse_tools',
                                                              cntrller='tool',
                                                              message=message,
                                                              status=status ) )
        if params.get( 'upload_button', False ):
            url_paste = params.get( 'url', '' ).strip()
            file_data = params.get( 'file_data', '' )
            if file_data == '' and url_paste == '':
                message = 'No files were entered on the upload form.'
                status = 'error'
            elif file_data == '':
                try:
                    uploaded_file = urllib2.urlopen( url_paste )
                except ( ValueError, urllib2.HTTPError ), e:
                    message = 'An error occurred trying to retrieve the URL entered on the upload form: %s' % str( e )
                    status = 'error'
                except urllib2.URLError, e:
                    message = 'An error occurred trying to retrieve the URL entered on the upload form: %s' % e.reason
                    status = 'error'
            elif file_data not in ( '', None ):
                uploaded_file = file_data.file
            if uploaded_file:
                datatype = trans.app.datatypes_registry.get_datatype_by_extension( upload_type )
                if datatype is None:
                    message = 'An unknown file type was selected.  This should not be possible, please report the error.'
                    status = 'error'
                else:
                    try:
                        # Initialize the tool object
                        meta = datatype.verify( uploaded_file )
                        meta.user = trans.user
                        meta.guid = trans.app.security.get_new_guid()
                        meta.suite = upload_type == 'toolsuite'
                        obj = datatype.create_model_object( meta )
                        trans.sa_session.add( obj )
                        if isinstance( obj, trans.app.model.Tool ):
                            existing = trans.sa_session.query( trans.app.model.Tool ) \
                                                       .filter_by( tool_id = meta.id ) \
                                                       .first()
                            if existing and not replace_id:
                                raise UploadError( 'A %s with the same Id already exists.  If you are trying to update this %s to a new version, use the upload form on the "Edit Tool" page.  Otherwise, change the Id in the %s config.' % \
                                                   ( obj.label, obj.label, obj.label ) )
                            elif replace_id and not existing:
                                raise UploadError( 'The new %s id (%s) does not match the old %s id (%s).  Check the %s config files.' % \
                                                   ( obj.label, str( meta.id ), obj.label, str( replace_version.tool_id ), obj.label ) )
                            elif existing and replace_id:
                                if replace_version.newer_version:
                                    # If the user has picked an old version, switch to the newest version
                                    replace_version = get_versions( replace_version )[0]
                                if replace_version.tool_id != meta.id:
                                    raise UploadError( 'The new %s id (%s) does not match the old %s id (%s).  Check the %s config files.' % \
                                                   ( obj.label, str( meta.id ), obj.label, str( replace_version.tool_id ), obj.label ) )
                                for old_version in get_versions( replace_version ):
                                    if old_version.version == meta.version:
                                        raise UploadError( 'The new version (%s) matches an old version.  Check your version in the %s config file.' % \
                                                           ( str( meta.version ), obj.label ) )
                                    if old_version.is_new:
                                        raise UploadError( 'There is an existing version of this %s which has not yet been submitted for approval, so either <a href="%s">submit it or delete it</a> before uploading a new version.' % \
                                                           ( obj.label,
                                                             url_for( controller='common',
                                                                      action='view_tool',
                                                                      cntrller='tool',
                                                                      id=trans.security.encode_id( old_version.id ) ) ) )
                                    if old_version.is_waiting:
                                        raise UploadError( 'There is an existing version of this %s which is waiting for administrative approval, so contact an administrator for help.' % \
                                                           obj.label )
                                    # Defer setting the id since the newer version id doesn't exist until the new Tool object is flushed
                            if category_ids:
                                for category_id in category_ids:
                                    category = trans.app.model.Category.get( trans.security.decode_id( category_id ) )
                                    # Initialize the tool category
                                    tca = trans.app.model.ToolCategoryAssociation( obj, category )
                                    trans.sa_session.add( tca )
                            # Initialize the tool event
                            event = trans.app.model.Event( state=trans.app.model.Tool.states.NEW )
                            # Flush to get an event id
                            trans.sa_session.add( event )
                            trans.sa_session.flush()
                            tea = trans.app.model.ToolEventAssociation( obj, event )
                            trans.sa_session.add( tea )
                        if replace_version and replace_id:
                            replace_version.newer_version_id = obj.id
                            trans.sa_session.add( replace_version )
                            # TODO: should the state be changed to archived?  We'll leave it alone for now
                            # because if the newer version is deleted, we'll need to add logic to reset the
                            # the older version back to it's previous state ( possible approved ).
                            comment = "Replaced by new version %s" % obj.version
                            event = trans.app.model.Event( state=replace_version.state, comment=comment )
                            # Flush to get an event id
                            trans.sa_session.add( event )
                            trans.sa_session.flush()
                            tea = trans.app.model.ToolEventAssociation( replace_version, event )
                        trans.sa_session.flush()
                        try:
                            os.link( uploaded_file.name, obj.file_name )
                        except OSError:
                            shutil.copy( uploaded_file.name, obj.file_name )
                        # We're setting cntrller to 'tool' since that is the only controller from which we can upload
                        # TODO: this will need tweaking when we can upload histories or workflows
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
                old_version = None
                for old_version in get_versions( replace_version ):
                    if old_version.is_new:
                        message = 'There is an existing version of this tool which has not been submitted for approval, so either submit or delete it before uploading a new version.'
                        break
                    if old_version.is_waiting:
                        message = 'There is an existing version of this tool which is waiting for administrative approval, so contact an administrator for help.'
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
        selected_categories = [ trans.security.decode_id( id ) for id in category_ids ]
        datatype_extensions = trans.app.datatypes_registry.get_datatype_extensions()
        upload_type_select_list = build_select_field( trans,
                                                      objs=datatype_extensions,
                                                      label_attr='self',
                                                      select_field_name='upload_type',
                                                      initial_value=upload_type,
                                                      selected_value=upload_type,
                                                      refresh_on_change=True )
        return trans.fill_template( '/webapps/community/upload/upload.mako',
                                    message=message,
                                    status=status,
                                    selected_upload_type=upload_type,
                                    upload_type_select_list=upload_type_select_list,
                                    replace_id=replace_id,
                                    selected_categories=selected_categories,
                                    categories=get_categories( trans ) )
