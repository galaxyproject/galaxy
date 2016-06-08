import logging
from json import loads

import paste.httpexceptions
from markupsafe import escape
from six import string_types

import galaxy.queue_worker
from galaxy import web
from galaxy.web.base.controller import BaseUIController

log = logging.getLogger( __name__ )


class DataManager( BaseUIController ):

    @web.expose
    def index( self, trans, **kwd ):
        not_is_admin = not trans.user_is_admin()
        if not_is_admin and not trans.app.config.enable_data_manager_user_view:
            raise paste.httpexceptions.HTTPUnauthorized( "This Galaxy instance is not configured to allow non-admins to view the data manager." )
        message = escape( kwd.get( 'message', '' ) )
        status = escape( kwd.get( 'status', 'info' ) )
        return trans.fill_template( "data_manager/index.mako", data_managers=trans.app.data_managers, tool_data_tables=trans.app.tool_data_tables, view_only=not_is_admin, message=message, status=status )

    @web.expose
    def manage_data_manager( self, trans, **kwd ):
        not_is_admin = not trans.user_is_admin()
        if not_is_admin and not trans.app.config.enable_data_manager_user_view:
            raise paste.httpexceptions.HTTPUnauthorized( "This Galaxy instance is not configured to allow non-admins to view the data manager." )
        message = escape( kwd.get( 'message', '' ) )
        status = escape( kwd.get( 'status', 'info' ) )
        data_manager_id = kwd.get( 'id', None )
        data_manager = trans.app.data_managers.get_manager( data_manager_id )
        if data_manager is None:
            return trans.response.send_redirect( web.url_for( controller="data_manager", action="index", message="Invalid Data Manager (%s) was requested" % data_manager_id, status="error" ) )
        jobs = list( reversed( [ assoc.job for assoc in trans.sa_session.query( trans.app.model.DataManagerJobAssociation ).filter_by( data_manager_id=data_manager_id ) ] ) )
        return trans.fill_template( "data_manager/manage_data_manager.mako", data_manager=data_manager, jobs=jobs, view_only=not_is_admin, message=message, status=status )

    @web.expose
    def view_job( self, trans, **kwd ):
        not_is_admin = not trans.user_is_admin()
        if not_is_admin and not trans.app.config.enable_data_manager_user_view:
            raise paste.httpexceptions.HTTPUnauthorized( "This Galaxy instance is not configured to allow non-admins to view the data manager." )
        message = escape( kwd.get( 'message', '' ) )
        status = escape( kwd.get( 'status', 'info' ) )
        job_id = kwd.get( 'id', None )
        try:
            job_id = trans.security.decode_id( job_id )
            job = trans.sa_session.query( trans.app.model.Job ).get( job_id )
        except Exception as e:
            job = None
            log.error( "Bad job id (%s) passed to view_job: %s" % ( job_id, e ) )
        if not job:
            return trans.response.send_redirect( web.url_for( controller="data_manager", action="index", message="Invalid job (%s) was requested" % job_id, status="error" ) )
        data_manager_id = job.data_manager_association.data_manager_id
        data_manager = trans.app.data_managers.get_manager( data_manager_id )
        hdas = [ assoc.dataset for assoc in job.get_output_datasets() ]
        data_manager_output = []
        error_messages = []
        for hda in hdas:
            try:
                data_manager_json = loads( open( hda.get_file_name() ).read() )
            except Exception as e:
                data_manager_json = {}
                error_messages.append( escape( "Unable to obtain data_table info for hda (%s): %s" % ( hda.id, e ) ) )
            values = []
            for key, value in data_manager_json.get( 'data_tables', {} ).iteritems():
                values.append( ( key, value ) )
            data_manager_output.append( values )
        return trans.fill_template( "data_manager/view_job.mako", data_manager=data_manager, job=job, view_only=not_is_admin, hdas=hdas, data_manager_output=data_manager_output, message=message, status=status, error_messages=error_messages )

    @web.expose
    def manage_data_table( self, trans, **kwd ):
        not_is_admin = not trans.user_is_admin()
        if not_is_admin and not trans.app.config.enable_data_manager_user_view:
            raise paste.httpexceptions.HTTPUnauthorized( "This Galaxy instance is not configured to allow non-admins to view the data manager." )
        message = escape( kwd.get( 'message', '' ) )
        status = escape( kwd.get( 'status', 'info' ) )
        data_table_name = kwd.get( 'table_name', None )
        if not data_table_name:
            return trans.response.send_redirect( web.url_for( controller="data_manager", action="index" ) )
        data_table = trans.app.tool_data_tables.get( data_table_name, None )
        if data_table is None:
            return trans.response.send_redirect( web.url_for( controller="data_manager", action="index", message="Invalid Data table (%s) was requested" % data_table_name, status="error" ) )
        return trans.fill_template( "data_manager/manage_data_table.mako", data_table=data_table, view_only=not_is_admin, message=message, status=status )

    @web.expose
    @web.require_admin
    def reload_tool_data_tables( self, trans, table_name=None, **kwd ):
        if table_name and isinstance( table_name, string_types ):
            table_name = table_name.split( "," )
        # Reload the tool data tables
        table_names = self.app.tool_data_tables.reload_tables( table_names=table_name )
        galaxy.queue_worker.send_control_task(trans.app, 'reload_tool_data_tables',
                                              noop_self=True,
                                              kwargs={'table_name': table_name} )
        redirect_url = None
        if table_names:
            status = 'done'
            if len( table_names ) == 1:
                message = "The data table '%s' has been reloaded." % table_names[0]
                redirect_url = web.url_for( controller='data_manager',
                                            action='manage_data_table',
                                            table_name=table_names[0],
                                            message=message,
                                            status=status )
            else:
                message = "The data tables '%s' have been reloaded." % ', '.join( table_names )
        else:
            message = "No data tables have been reloaded."
            status = 'error'
        if redirect_url is None:
            redirect_url = web.url_for( controller='admin',
                                        action='view_tool_data_tables',
                                        message=message,
                                        status=status )
        return trans.response.send_redirect( redirect_url )
