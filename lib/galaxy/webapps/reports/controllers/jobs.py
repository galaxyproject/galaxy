import operator, os, socket
from datetime import *
from time import mktime, strftime, localtime
import calendar
from galaxy.webapps.reports.base.controller import *
import galaxy.model
import pkg_resources
pkg_resources.require( "SQLAlchemy >= 0.4" )
import sqlalchemy as sa
import logging
log = logging.getLogger( __name__ )

class Jobs( BaseController ):
    @web.expose
    def today_all( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = ''
        monitor_email = params.get( 'monitor_email', 'monitor@bx.psu.edu' )
        year, month, day = map( int, datetime.utcnow().strftime( "%Y-%m-%d" ).split( "-" ) )
        start_date = date( year, month, day )
        end_date = start_date + timedelta( days=1 )
        day_label = start_date.strftime( "%A" )
        month_label = start_date.strftime( "%B" )
        year_label = start_date.strftime( "%Y" )
        day_of_month = start_date.strftime( "%d" )
        q = sa.select( ( sa.func.date( galaxy.model.Job.table.c.create_time ).label( 'date' ),
                         sa.func.sum( sa.case( [( galaxy.model.User.table.c.email == monitor_email, 1 )], else_=0 ) ).label( 'monitor_jobs' ),
                         sa.func.count( galaxy.model.Job.table.c.id ).label( 'total_jobs' ) ),
                       whereclause = sa.and_( galaxy.model.Job.table.c.create_time >= start_date,
                                              galaxy.model.Job.table.c.create_time < end_date ),
                       from_obj = [ sa.outerjoin( galaxy.model.Job.table, 
                                                  galaxy.model.History.table ).outerjoin( galaxy.model.User.table ) ],
                       group_by = [ 'date' ] )
        jobs = []
        for row in q.execute():
            jobs.append( ( row.date.strftime( "%A" ),
                           row.date,
                           row.total_jobs - row.monitor_jobs,
                           row.monitor_jobs,
                           row.total_jobs,
                           row.date.strftime( "%d" ) ) )
        return trans.fill_template( 'jobs_today_all.mako', 
                                    day_label=day_label, 
                                    month_label=month_label, 
                                    year_label=year_label, 
                                    day_of_month=day_of_month, 
                                    month=month, 
                                    jobs=jobs, 
                                    msg=msg )
    @web.expose
    def specified_month_all( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = ''
        monitor_email = params.get( 'monitor_email', 'monitor@bx.psu.edu' )
        year, month = map( int, params.get( 'month', datetime.utcnow().strftime( "%Y-%m" ) ).split( "-" ) )
        start_date = date( year, month, 1 )
        end_date = start_date + timedelta( days=calendar.monthrange( year, month )[1] )
        month_label = start_date.strftime( "%B" )
        year_label = start_date.strftime( "%Y" )
        q = sa.select( ( sa.func.date( galaxy.model.Job.table.c.create_time ).label( 'date' ),
                         sa.func.sum( sa.case( [( galaxy.model.User.table.c.email == monitor_email, 1 )], else_=0 ) ).label( 'monitor_jobs' ),
                         sa.func.count( galaxy.model.Job.table.c.id ).label( 'total_jobs' ) ),
                       whereclause = sa.and_( galaxy.model.Job.table.c.create_time >= start_date,
                                              galaxy.model.Job.table.c.create_time < end_date ),
                       from_obj = [ sa.outerjoin( galaxy.model.Job.table, 
                                                  galaxy.model.History.table ).outerjoin( galaxy.model.User.table ) ],
                       group_by = [ 'date' ],
                       order_by = [ sa.desc( 'date' ) ] )
        jobs = []
        for row in q.execute():
            jobs.append( ( row.date.strftime( "%A" ),
                           row.date,
                           row.total_jobs - row.monitor_jobs,
                           row.monitor_jobs,
                           row.total_jobs,
                           row.date.strftime( "%d" ) ) )
        return trans.fill_template( 'jobs_specified_month_all.mako', 
                                    month_label=month_label, 
                                    year_label=year_label, 
                                    month=month, 
                                    jobs=jobs, 
                                    msg=msg ) 
    @web.expose
    def specified_month_in_error( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = ''
        year, month = map( int, params.get( 'month', datetime.utcnow().strftime( "%Y-%m" ) ).split( "-" ) )
        start_date = date( year, month, 1 )
        end_date = start_date + timedelta( days=calendar.monthrange( year, month )[1] )
        month_label = start_date.strftime( "%B" )
        year_label = start_date.strftime( "%Y" )
        q = sa.select( ( sa.func.date( galaxy.model.Job.table.c.create_time ).label( 'date' ),
                         sa.func.count( galaxy.model.Job.table.c.id ).label( 'total_jobs' ) ),
                       whereclause = sa.and_( sa.or_( galaxy.model.Job.table.c.state == 'error', 
                                                      galaxy.model.Job.table.c.state == 'deleted' ),
                                              galaxy.model.Job.table.c.create_time >= start_date, 
                                              galaxy.model.Job.table.c.create_time < end_date ),
                       from_obj = [ sa.outerjoin( galaxy.model.Job.table, 
                                                  galaxy.model.History.table ).outerjoin( galaxy.model.User.table ) ],
                       group_by = [ 'date' ],
                       order_by = [ sa.desc( 'date' ) ] )
        jobs = []
        for row in q.execute():
            jobs.append( ( row.date.strftime( "%A" ),
                           row.date,
                           row.total_jobs,
                           row.date.strftime( "%d" ) ) )
        return trans.fill_template( 'jobs_specified_month_in_error.mako', 
                                    month_label=month_label, 
                                    year_label=year_label, 
                                    month=month, 
                                    jobs=jobs, 
                                    msg=msg )
    @web.expose
    def specified_date_in_error( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = ''
        year, month, day = map( int, params.get( 'specified_date', datetime.utcnow().strftime( "%Y-%m-%d" ) ).split( "-" ) )
        start_date = date( year, month, day )
        end_date = start_date + timedelta( days=1 )
        day_label = start_date.strftime( "%A" )
        month_label = start_date.strftime( "%B" )
        year_label = start_date.strftime( "%Y" )
        day_of_month = start_date.strftime( "%d" )
        q = sa.select( ( galaxy.model.Job.table.c.id,
                         galaxy.model.Job.table.c.state,
                         galaxy.model.Job.table.c.create_time,
                         galaxy.model.Job.table.c.update_time,
                         galaxy.model.Job.table.c.tool_id,
                         galaxy.model.Job.table.c.command_line,
                         galaxy.model.Job.table.c.stderr,
                         galaxy.model.Job.table.c.session_id,
                         ( galaxy.model.Job.table.c.traceback ).label( 'stack_trace' ),
                         galaxy.model.Job.table.c.info,
                         ( galaxy.model.User.table.c.email ).label( 'user_email' ),
                         galaxy.model.GalaxySession.table.c.remote_addr ),
                       whereclause = sa.and_( sa.or_( galaxy.model.Job.table.c.state == 'error', 
                                                      galaxy.model.Job.table.c.state == 'deleted' ),
                                              galaxy.model.Job.table.c.create_time >= start_date, 
                                              galaxy.model.Job.table.c.create_time < end_date ),
                       from_obj = [ sa.outerjoin( galaxy.model.Job.table, 
                                                  galaxy.model.History.table ).outerjoin( galaxy.model.User.table ).outerjoin( galaxy.model.GalaxySession.table,
                                                                                                                               galaxy.model.Job.table.c.session_id == galaxy.model.GalaxySession.table.c.id ) ],
                       order_by = [ sa.desc( galaxy.model.Job.table.c.id ) ] )
        jobs = []
        for row in q.execute():
            remote_host = row.remote_addr
            if row.remote_addr:
                try:
                    remote_host = socket.gethostbyaddr( row.remote_addr )[0]
                except:
                    pass
            jobs.append( ( row.state,
                           row.id,
                           row.create_time,
                           row.update_time,
                           row.session_id,
                           row.tool_id,
                           row.user_email,
                           remote_host,
                           row.command_line,
                           row.stderr,
                           row.stack_trace,
                           row.info ) )
        return trans.fill_template( 'jobs_specified_date_in_error.mako', 
                                    specified_date=start_date, 
                                    day_label=day_label, 
                                    month_label=month_label, 
                                    year_label=year_label, 
                                    day_of_month=day_of_month, 
                                    jobs=jobs, 
                                    msg=msg )
    @web.expose
    def specified_date_all( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = ''
        monitor_email = params.get( 'monitor_email', 'monitor@bx.psu.edu' )
        year, month, day = map( int, params.get( 'specified_date', datetime.utcnow().strftime( "%Y-%m-%d" ) ).split( "-" ) )
        start_date = date( year, month, day )
        end_date = start_date + timedelta( days=1 )
        day_label = start_date.strftime( "%A" )
        month_label = start_date.strftime( "%B" )
        year_label = start_date.strftime( "%Y" )
        day_of_month = start_date.strftime( "%d" )
        q = sa.select( ( galaxy.model.Job.table.c.id,
                         galaxy.model.Job.table.c.state,
                         galaxy.model.Job.table.c.create_time,
                         galaxy.model.Job.table.c.update_time,
                         galaxy.model.Job.table.c.tool_id,
                         galaxy.model.Job.table.c.command_line,
                         galaxy.model.Job.table.c.stderr,
                         galaxy.model.Job.table.c.session_id,
                         ( galaxy.model.Job.table.c.traceback ).label( 'stack_trace' ),
                         galaxy.model.Job.table.c.info,
                         ( galaxy.model.User.table.c.email ).label( 'user_email' ),
                         galaxy.model.GalaxySession.table.c.remote_addr ),
                       whereclause = sa.and_( galaxy.model.Job.table.c.create_time >= start_date, 
                                              galaxy.model.Job.table.c.create_time < end_date ),
                       from_obj = [ sa.outerjoin( galaxy.model.Job.table, 
                                                  galaxy.model.History.table ).outerjoin( galaxy.model.User.table ).outerjoin( galaxy.model.GalaxySession.table,
                                                                                                                               galaxy.model.Job.table.c.session_id == galaxy.model.GalaxySession.table.c.id ) ],
                       order_by = [ sa.desc( galaxy.model.Job.table.c.id ) ] )
        jobs = []
        for row in q.execute():
            remote_host = row.remote_addr
            if row.remote_addr:
                try:
                    remote_host = socket.gethostbyaddr( row.remote_addr )[0]
                except:
                    pass
            jobs.append( ( row.state, 
                           row.id, 
                           row.create_time, 
                           row.update_time, 
                           row.session_id, 
                           row.tool_id, 
                           row.user_email, 
                           remote_host, 
                           row.command_line, 
                           row.stderr, 
                           row.stack_trace, 
                           row.info ) )
        return trans.fill_template( 'jobs_specified_date_all.mako', 
                                    specified_date=start_date, 
                                    day_label=day_label, 
                                    month_label=month_label, 
                                    year_label=year_label, 
                                    day_of_month=day_of_month, 
                                    jobs=jobs, 
                                    msg=msg )
    @web.expose
    def all_unfinished( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = ''
        jobs = []
        q = sa.select( ( galaxy.model.Job.table.c.id,
                         galaxy.model.Job.table.c.state,
                         galaxy.model.Job.table.c.create_time,
                         galaxy.model.Job.table.c.update_time,
                         galaxy.model.Job.table.c.tool_id,
                         galaxy.model.Job.table.c.command_line,
                         galaxy.model.Job.table.c.stderr,
                         galaxy.model.Job.table.c.session_id,
                         ( galaxy.model.Job.table.c.traceback ).label( 'stack_trace' ),
                         galaxy.model.Job.table.c.info,
                         ( galaxy.model.User.table.c.email ).label( 'user_email' ),
                         galaxy.model.GalaxySession.table.c.remote_addr ),
                       whereclause = sa.or_( galaxy.model.Job.table.c.state == 'running', 
                                             galaxy.model.Job.table.c.state == 'queued',
                                             galaxy.model.Job.table.c.state == 'waiting', 
                                             galaxy.model.Job.table.c.state == 'new' ),
                       from_obj = [ sa.outerjoin( galaxy.model.Job.table, 
                                                  galaxy.model.History.table ).outerjoin( galaxy.model.User.table ).outerjoin( galaxy.model.GalaxySession.table,
                                                                                                                               galaxy.model.Job.table.c.session_id == galaxy.model.GalaxySession.table.c.id ) ],
                       order_by = [ sa.desc( galaxy.model.Job.table.c.id ) ] )
        for row in q.execute():
            remote_host = row.remote_addr
            if row.remote_addr:
                try:
                    remote_host = socket.gethostbyaddr( row.remote_addr )[0]
                except:
                    pass
            jobs.append( ( row.state, 
                           row.id, 
                           row.create_time, 
                           row.update_time, 
                           row.session_id, 
                           row.tool_id, 
                           row.user_email, 
                           remote_host, 
                           row.command_line, 
                           row.stderr, 
                           row.stack_trace, 
                           row.info ) )
        return trans.fill_template( 'jobs_all_unfinished.mako', jobs=jobs, msg=msg )
    @web.expose
    def per_month_all( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = ''
        monitor_email = params.get( 'monitor_email', 'monitor@bx.psu.edu' )
        q = sa.select( ( sa.func.date_trunc( 'month', sa.func.date( galaxy.model.Job.table.c.create_time ) ).label( 'date' ),
                         sa.func.sum( sa.case( [( galaxy.model.User.table.c.email == monitor_email, 1 )], else_=0 ) ).label( 'monitor_jobs' ),
                         sa.func.count( galaxy.model.Job.table.c.id ).label( 'total_jobs' ) ),
                       from_obj = [ sa.outerjoin( galaxy.model.Job.table, 
                                                  galaxy.model.History.table ).outerjoin( galaxy.model.User.table ) ],
                       group_by = [ sa.func.date_trunc( 'month', sa.func.date( galaxy.model.Job.table.c.create_time ) ) ],
                       order_by = [ sa.desc( 'date' ) ] )
        jobs = []
        for row in q.execute():
            jobs.append( ( row.date.strftime( "%Y-%m" ),
                           row.total_jobs - row.monitor_jobs,
                           row.monitor_jobs, 
                           row.total_jobs,
                           row.date.strftime( "%B" ),
                           row.date.strftime( "%Y" ) ) )
        return trans.fill_template( 'jobs_per_month_all.mako', jobs=jobs, msg=msg )
    @web.expose
    def per_month_in_error( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = ''
        q = sa.select( ( sa.func.date_trunc( 'month', sa.func.date( galaxy.model.Job.table.c.create_time ) ).label( 'date' ),
                         sa.func.count( galaxy.model.Job.table.c.id ).label( 'total_jobs' ) ),
                       whereclause = sa.or_( galaxy.model.Job.table.c.state == 'error', 
                                             galaxy.model.Job.table.c.state == 'deleted' ),
                       from_obj = [ galaxy.model.Job.table ],
                       group_by = [ sa.func.date_trunc( 'month', sa.func.date( galaxy.model.Job.table.c.create_time ) ) ],
                       order_by = [ sa.desc( 'date' ) ] )
        jobs = []
        for row in q.execute():
            jobs.append( ( row.date.strftime( "%Y-%m" ), 
                           row.total_jobs,
                           row.date.strftime( "%B" ),
                           row.date.strftime( "%Y" ) ) )
        return trans.fill_template( 'jobs_per_month_in_error.mako', jobs=jobs, msg=msg )
    @web.expose
    def per_user( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = ''
        jobs = []
        q = sa.select( ( galaxy.model.User.table.c.email.label( 'user_email' ),
                         sa.func.count( galaxy.model.Job.table.c.id ).label( 'total_jobs' ) ),
                       from_obj = [ sa.outerjoin( galaxy.model.Job.table, 
                                                  galaxy.model.GalaxySession.table ).outerjoin( galaxy.model.User.table ) ],
                       group_by = [ 'user_email' ],
                       order_by = [ sa.desc( 'total_jobs' ), 'user_email' ] )
        for row in q.execute():
            jobs.append( ( row.user_email, 
                           row.total_jobs ) )
        return trans.fill_template( 'jobs_per_user.mako', jobs=jobs, msg=msg )
    @web.expose
    def user_per_month( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = ''
        email = params.get( 'email', None )
        if email is not None:
            # The @ char has been converted to an 'X'
            email = email.replace( 'X', '@' )
        q = sa.select( ( sa.func.date_trunc( 'month', sa.func.date( galaxy.model.Job.table.c.create_time ) ).label( 'date' ),
                         sa.func.count( galaxy.model.Job.table.c.id ).label( 'total_jobs' ) ),
                       whereclause = galaxy.model.User.table.c.email == email, 
                       from_obj = [ sa.outerjoin( galaxy.model.Job.table, 
                                                  galaxy.model.GalaxySession.table ).outerjoin( galaxy.model.User.table ) ],
                       group_by = [ sa.func.date_trunc( 'month', sa.func.date( galaxy.model.Job.table.c.create_time ) ) ],
                       order_by = [ sa.desc( 'date' ) ] )
        jobs = []
        for row in q.execute():
            jobs.append( ( row.date.strftime( "%Y-%m" ), 
                           row.total_jobs,
                           row.date.strftime( "%B" ),
                           row.date.strftime( "%Y" ) ) )
        return trans.fill_template( 'jobs_user_per_month.mako', email=email, jobs=jobs, msg=msg )
    @web.expose
    def user_for_month( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = ''
        email = params.get( 'email', None )
        if email is not None:
            # The @ char has been converted to an 'X'
            email = email.replace( 'X', '@' )
        year, month = map( int, params.get( 'month', datetime.utcnow().strftime( "%Y-%m" ) ).split( "-" ) )
        start_date = date( year, month, 1 )
        end_date = start_date + timedelta( days=calendar.monthrange( year, month )[1] )
        month_label = start_date.strftime( "%B" )
        year_label = start_date.strftime( "%Y" )
        jobs = []
        q = sa.select( ( galaxy.model.Job.table.c.id,
                         galaxy.model.Job.table.c.state,
                         galaxy.model.Job.table.c.create_time,
                         galaxy.model.Job.table.c.update_time,
                         galaxy.model.Job.table.c.tool_id,
                         galaxy.model.Job.table.c.command_line,
                         galaxy.model.Job.table.c.stderr,
                         galaxy.model.Job.table.c.session_id,
                         ( galaxy.model.Job.table.c.traceback ).label( 'stack_trace' ),
                         galaxy.model.Job.table.c.info,
                         ( galaxy.model.User.table.c.email ).label( 'user_email' ),
                         galaxy.model.GalaxySession.table.c.remote_addr ),
                       whereclause = sa.and_( galaxy.model.User.table.c.email == email, 
                                              galaxy.model.Job.table.c.create_time >= start_date, 
                                              galaxy.model.Job.table.c.create_time < end_date ),
                       from_obj = [ sa.outerjoin( galaxy.model.Job.table, 
                                                  galaxy.model.History.table ).outerjoin( galaxy.model.User.table ).outerjoin( galaxy.model.GalaxySession.table,
                                                                                                                               galaxy.model.Job.table.c.session_id == galaxy.model.GalaxySession.table.c.id ) ],
                       order_by = [ sa.desc( galaxy.model.Job.table.c.id ) ] )
        for row in q.execute():
            remote_host = row.remote_addr
            if row.remote_addr:
                try:
                    remote_host = socket.gethostbyaddr( row.remote_addr )[0]
                except:
                    pass
            jobs.append( ( row.state,
                           row.id,
                           row.create_time,
                           row.update_time,
                           row.session_id,
                           row.tool_id,
                           row.user_email,
                           remote_host,
                           row.command_line,
                           row.stderr,
                           row.stack_trace,
                           row.info ) )
        return trans.fill_template( 'jobs_user_for_month.mako', 
                                    email=email, 
                                    month=month, 
                                    month_label=month_label, 
                                    year_label=year_label, 
                                    jobs=jobs, 
                                    msg=msg )
    @web.expose
    def per_tool( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = ''
        jobs = []
        q = sa.select( ( galaxy.model.Job.table.c.tool_id.label( 'tool_id' ),
                         sa.func.count( galaxy.model.Job.table.c.id ).label( 'total_jobs' ) ),
                       from_obj = [ galaxy.model.Job.table ],
                       group_by = [ 'tool_id' ],
                       order_by = [ 'tool_id' ] )
        for row in q.execute():
            jobs.append( ( row.tool_id, 
                           row.total_jobs ) )
        return trans.fill_template( 'jobs_per_tool.mako', jobs=jobs, msg=msg )
    @web.expose
    def tool_per_month( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = ''
        tool_id = params.get( 'tool_id', 'Add a column1' )
        q = sa.select( ( sa.func.date_trunc( 'month', sa.func.date( galaxy.model.Job.table.c.create_time ) ).label( 'date' ),
                         sa.func.count( galaxy.model.Job.table.c.id ).label( 'total_jobs' ) ),
                       whereclause = galaxy.model.Job.table.c.tool_id == tool_id, 
                       from_obj = [ galaxy.model.Job.table ],
                       group_by = [ sa.func.date_trunc( 'month', sa.func.date( galaxy.model.Job.table.c.create_time ) ) ],
                       order_by = [ sa.desc( 'date' ) ] )
        jobs = []
        for row in q.execute():
            jobs.append( ( row.date.strftime( "%Y-%m" ), 
                           row.total_jobs,
                           row.date.strftime( "%B" ),
                           row.date.strftime( "%Y" ) ) )
        return trans.fill_template( 'jobs_tool_per_month.mako', tool_id=tool_id, jobs=jobs, msg=msg )
    @web.expose
    def tool_for_month( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = ''
        tool_id = params.get( 'tool_id', 'Add a column1' )
        year, month = map( int, params.get( 'month', datetime.utcnow().strftime( "%Y-%m" ) ).split( "-" ) )
        start_date = date( year, month, 1 )
        end_date = start_date + timedelta( days=calendar.monthrange( year, month )[1] )
        month_label = start_date.strftime( "%B" )
        year_label = start_date.strftime( "%Y" )
        jobs = []
        q = sa.select( ( galaxy.model.Job.table.c.id,
                         galaxy.model.Job.table.c.state,
                         galaxy.model.Job.table.c.create_time,
                         galaxy.model.Job.table.c.update_time,
                         galaxy.model.Job.table.c.tool_id,
                         galaxy.model.Job.table.c.command_line,
                         galaxy.model.Job.table.c.stderr,
                         galaxy.model.Job.table.c.session_id,
                         ( galaxy.model.Job.table.c.traceback ).label( 'stack_trace' ),
                         galaxy.model.Job.table.c.info,
                         ( galaxy.model.User.table.c.email ).label( 'user_email' ),
                         galaxy.model.GalaxySession.table.c.remote_addr ),
                       whereclause = sa.and_( galaxy.model.Job.table.c.tool_id == tool_id, 
                                              galaxy.model.Job.table.c.create_time >= start_date, 
                                              galaxy.model.Job.table.c.create_time < end_date ),
                       from_obj = [ sa.outerjoin( galaxy.model.Job.table, 
                                                  galaxy.model.History.table ).outerjoin( galaxy.model.User.table ).outerjoin( galaxy.model.GalaxySession.table,
                                                                                                                               galaxy.model.Job.table.c.session_id == galaxy.model.GalaxySession.table.c.id ) ],
                       order_by = [ sa.desc( galaxy.model.Job.table.c.id ) ] )
        for row in q.execute():
            remote_host = row.remote_addr
            if row.remote_addr:
                try:
                    remote_host = socket.gethostbyaddr( row.remote_addr )[0]
                except:
                    pass
            jobs.append( ( row.state,
                           row.id,
                           row.create_time,
                           row.update_time,
                           row.session_id,
                           row.tool_id,
                           row.user_email,
                           remote_host,
                           row.command_line,
                           row.stderr,
                           row.stack_trace,
                           row.info ) )
        return trans.fill_template( 'jobs_tool_for_month.mako', 
                                    tool_id=tool_id, 
                                    month=month, 
                                    month_label=month_label, 
                                    year_label=year_label, 
                                    jobs=jobs, 
                                    msg=msg )
    @web.expose
    def per_domain( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = ''
        engine = galaxy.model.mapping.metadata.engine
        jobs = []
        s = """
        SELECT
            substr(bar.first_pass_domain, bar.dot_position, 4) AS domain,
            count(job_id) AS total_jobs
        FROM
            (SELECT
                user_email AS user_email,
                first_pass_domain,
                position('.' in first_pass_domain) AS dot_position,
                job_id AS job_id
            FROM
                (SELECT
                    email AS user_email,
                    substr(email, char_length(email)-3, char_length(email)) AS first_pass_domain,
                    job.id AS job_id
                FROM
                    job
                LEFT OUTER JOIN galaxy_session ON galaxy_session.id = job.session_id
                LEFT OUTER JOIN galaxy_user ON galaxy_session.user_id = galaxy_user.id
                WHERE
                    job.session_id = galaxy_session.id
                AND
                    galaxy_session.user_id = galaxy_user.id
                ) AS foo
            ) AS bar
        GROUP BY
            domain
        ORDER BY
            total_jobs DESC
        """
        job_rows = engine.text( s ).execute().fetchall()
        for job in job_rows:
            jobs.append( ( job.domain, job.total_jobs ) )
        return trans.fill_template( 'jobs_per_domain.mako', jobs=jobs, msg=msg )
