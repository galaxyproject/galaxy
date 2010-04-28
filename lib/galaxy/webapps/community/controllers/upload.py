import sys, os, shutil, logging, urllib2
from galaxy.web.base.controller import *
from galaxy.web.framework.helpers import time_ago, iff, grids
from galaxy.model.orm import *
from galaxy.webapps.community import datatypes
from common import get_categories, get_category

log = logging.getLogger( __name__ )

# States for passing messages
SUCCESS, INFO, WARNING, ERROR = "done", "info", "warning", "error"

class UploadController( BaseController ):
    
    @web.expose
    def upload( self, trans, **kwd ):
        params = util.Params( kwd )
        message = util.restore_text( params.get( 'message', ''  ) )
        status = params.get( 'status', 'done' )
        category_ids = util.listify( params.get( 'category_id', '' ) )
        uploaded_file = None
        if params.file_data == '' and params.url.strip() == '':
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
                except datatypes.DatatypeVerificationError, e:
                    message = str( e )
                    status = 'error'
                except sqlalchemy.exc.IntegrityError:
                    message = 'A tool with the same ID already exists.  If you are trying to update this tool to a new version, please use the upload form on the "Edit Tool" page.  Otherwise, please choose a new ID.'
                    status = 'error'
                uploaded_file.close()
        selected_upload_type = params.get( 'type', 'tool' )
        selected_categories = [ trans.security.decode_id( id ) for id in category_ids ]
        return trans.fill_template( '/webapps/community/upload/upload.mako',
                                    message=message,
                                    status=status,
                                    selected_upload_type=selected_upload_type,
                                    upload_types=trans.app.datatypes_registry.get_datatypes_for_select_list(),
                                    selected_categories=selected_categories,
                                    categories=get_categories( trans ) )
