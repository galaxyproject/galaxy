import calendar, operator, os, socket
from datetime import *
from time import mktime, strftime, localtime
from galaxy.web.base.controller import *
from galaxy import model, util
from galaxy.web.framework.helpers import time_ago, iff, grids
from galaxy.model.orm import *
import pkg_resources
pkg_resources.require( "SQLAlchemy >= 0.4" )
import sqlalchemy as sa
import logging
log = logging.getLogger( __name__ )

class SpecifiedDateListGrid( grids.Grid ):
    class JobIdColumn( grids.IntegerColumn ):
        def get_value( self, trans, grid, job ):
            return job.id
    class StateColumn( grids.TextColumn ):
        def get_value( self, trans, grid, job ):
            return job.state
    class ToolColumn( grids.TextColumn ):
        def get_value( self, trans, grid, job ):
            return job.tool_id
    class CreateTimeColumn( grids.TextColumn ):
        def get_value( self, trans, grid, job ):
            return job.create_time
    class UserColumn( grids.TextColumn ):
        def get_value( self, trans, grid, job ):
            if job.history:
                if job.history.user:
                    return job.history.user.email
                return 'anonymous'
            # TODO: handle libraries...
            return 'no history'
    # Grid definition
    use_async = False
    model_class = model.Job
    title = "Jobs By Date"
    template='/webapps/reports/grid.mako'
    default_sort_key = "id"
    columns = [
        JobIdColumn( "Id",
                     key="id",
                     model_class=model.Job,
                     link=( lambda item: dict( operation="job_info", id=item.id, webapp="reports" ) ),
                     attach_popup=False,
                     filterable="advanced" ),
        StateColumn( "State",
                      key="state",
                      model_class=model.Job,
                      attach_popup=False ),
        ToolColumn( "Tool Id",
                    key="tool_id",
                    model_class=model.Job,
                    link=( lambda item: dict( operation="tool_per_month", id=item.id, webapp="reports" ) ),
                    attach_popup=False ),
        CreateTimeColumn( "create_time",
                          key="create_time",
                          model_class=model.Job,
                          attach_popup=False ),
        UserColumn( "user",
                    # Can't sort on this column since it is not a column in self.model_class
                    model_class=model.User,
                    link=( lambda item: dict( operation="user_per_month", id=item.id, webapp="reports" ) ),
                    attach_popup=False ),
        grids.StateColumn( "All", key="state", model_class=model.Job, visible=False, filterable="advanced" )
    ]
    columns.append( grids.MulticolFilterColumn( "Search", 
                                                cols_to_filter=[ columns[1], columns[2] ], 
                                                key="free-text-search",
                                                visible=False,
                                                filterable="standard" ) )
    standard_filters = []
    default_filter = { 'specified_date' : 'All' }
    num_rows_per_page = 50
    preserve_state = False
    use_paging = True
    def build_initial_query( self, trans, **kwd ):
        specified_date = kwd.get( 'specified_date', 'All' )
        if specified_date == 'All':
            return trans.sa_session.query( self.model_class )
        year, month, day = map( int, specified_date.split( "-" ) )
        start_date = date( year, month, day )
        end_date = start_date + timedelta( days=1 )
        return trans.sa_session.query( self.model_class ).filter( and_( self.model_class.table.c.create_time >= start_date,
                                                                        self.model_class.table.c.create_time < end_date ) )

class SpecifiedDateInErrorListGrid( SpecifiedDateListGrid ):
    def build_initial_query( self, trans, **kwd ):
        specified_date = kwd.get( 'specified_date', 'All' )
        if specified_date == 'All':
            return trans.sa_session.query( self.model_class ).filter( self.model_class.table.c.state == model.Job.states.ERROR )
        year, month, day = map( int, specified_date.split( "-" ) )
        start_date = date( year, month, day )
        end_date = start_date + timedelta( days=1 )
        return trans.sa_session.query( self.model_class ).filter( and_( self.model_class.table.c.state == model.Job.states.ERROR,
                                                                        self.model_class.table.c.create_time >= start_date,
                                                                        self.model_class.table.c.create_time < end_date ) )

class AllUnfinishedListGrid( SpecifiedDateListGrid ):
    def build_initial_query( self, trans, **kwd ):
        specified_date = kwd.get( 'specified_date', 'All' )
        if specified_date == 'All':
            return trans.sa_session.query( self.model_class ).filter( not_( or_( model.Job.table.c.state == model.Job.states.OK, 
                                                                                 model.Job.table.c.state == model.Job.states.ERROR, 
                                                                                 model.Job.table.c.state == model.Job.states.DELETED ) ) )
        year, month, day = map( int, specified_date.split( "-" ) )
        start_date = date( year, month, day )
        end_date = start_date + timedelta( days=1 )
        return trans.sa_session.query( self.model_class ).filter( and_( not_( or_( model.Job.table.c.state == model.Job.states.OK, 
                                                                                   model.Job.table.c.state == model.Job.states.ERROR, 
                                                                                   model.Job.table.c.state == model.Job.states.DELETED ) ),
                                                                        self.model_class.table.c.create_time >= start_date,
                                                                        self.model_class.table.c.create_time < end_date ) )

class UserForMonthListGrid( SpecifiedDateListGrid ):
    def build_initial_query( self, trans, **kwd ):
        email = util.restore_text( kwd.get( 'email', '' ) )
        year, month = map( int, kwd.get( 'month', datetime.utcnow().strftime( "%Y-%m" ) ).split( "-" ) )
        start_date = date( year, month, 1 )
        end_date = start_date + timedelta( days=calendar.monthrange( year, month )[1] )
        return trans.sa_session.query( model.Job ) \
                               .join( model.GalaxySession ) \
                               .join( model.User ) \
                               .filter( and_( model.Job.table.c.session_id == model.GalaxySession.table.c.id,
                                              model.GalaxySession.table.c.user_id == model.User.table.c.id,
                                              model.User.table.c.email == email,
                                              model.Job.table.c.create_time >= start_date,
                                              model.Job.table.c.create_time < end_date ) ) \
                               .order_by( desc( model.Job.table.c.create_time ) )

class ToolForMonthListGrid( SpecifiedDateListGrid ):
    def build_initial_query( self, trans, **kwd ):
        tool_id = util.restore_text( kwd.get( 'tool_id', '' ) )
        year, month = map( int, kwd.get( 'month', datetime.utcnow().strftime( "%Y-%m" ) ).split( "-" ) )
        start_date = date( year, month, 1 )
        end_date = start_date + timedelta( days=calendar.monthrange( year, month )[1] )
        return trans.sa_session.query( model.Job ) \
                               .filter( and_( model.Job.table.c.tool_id == tool_id,
                                              model.Job.table.c.create_time >= start_date,
                                              model.Job.table.c.create_time < end_date ) ) \
                               .order_by( desc( model.Job.table.c.create_time ) )

class Jobs( BaseController ):

    specified_date_list_grid = SpecifiedDateListGrid()
    specified_date_in_error_list_grid = SpecifiedDateInErrorListGrid()
    all_unfinished_list_grid = AllUnfinishedListGrid()
    user_for_month_list_grid = UserForMonthListGrid()
    tool_for_month_list_grid = ToolForMonthListGrid()

    @web.expose
    def specified_date( self, trans, **kwd ):
        if 'operation' in kwd:
            operation = kwd['operation'].lower()
            if operation == "job_info":
                return trans.response.send_redirect( web.url_for( controller='jobs',
                                                                  action='job_info',
                                                                  **kwd ) )
            if operation == "tool_per_month":
                # The received id is the job id, so we need to get the id of the user
                # that submitted the job.
                job_id = kwd.get( 'id', None )
                job = get_job( trans, job_id )
                kwd[ 'tool_id' ] = job.tool_id
                return trans.response.send_redirect( web.url_for( controller='jobs',
                                                                  action='tool_per_month',
                                                                  **kwd ) )
            if operation == "user_per_month":
                # The received id is the job id, so we need to get the id of the user
                # that submitted the job.
                job_id = kwd.get( 'id', None )
                job = get_job( trans, job_id )
                kwd[ 'email' ] = None # For anonymous users
                if job.history:
                    if job.history.user:
                        email = job.history.user.email
                        kwd[ 'email' ] = email
                # TODO: handle libraries
                return trans.response.send_redirect( web.url_for( controller='jobs',
                                                                  action='user_per_month',
                                                                  **kwd ) )
        return self.specified_date_list_grid( trans, **kwd )
    @web.expose
    def today_all( self, trans, **kwd ):
        kwd[ 'specified_date' ] = datetime.utcnow().strftime( "%Y-%m-%d" )
        return self.specified_date( trans, **kwd )
    @web.expose
    def specified_date_in_error( self, trans, **kwd ):
        if 'operation' in kwd:
            operation = kwd['operation'].lower()
            if operation == "job_info":
                return trans.response.send_redirect( web.url_for( controller='jobs',
                                                                  action='job_info',
                                                                  **kwd ) )
            if operation == "tool_per_month":
                # The received id is the job id, so we need to get the id of the user
                # that submitted the job.
                job_id = kwd.get( 'id', None )
                job = get_job( trans, job_id )
                kwd[ 'tool_id' ] = job.tool_id
                return trans.response.send_redirect( web.url_for( controller='jobs',
                                                                  action='tool_per_month',
                                                                  **kwd ) )
            if operation == "user_per_month":
                # The received id is the job id, so we need to get the id of the user
                # that submitted the job.
                job_id = kwd.get( 'id', None )
                job = get_job( trans, job_id )
                kwd[ 'email' ] = None # For anonymous users
                if job.history:
                    if job.history.user:
                        email = job.history.user.email
                        kwd[ 'email' ] = email
                # TODO: handle libraries
                return trans.response.send_redirect( web.url_for( controller='jobs',
                                                                  action='user_per_month',
                                                                  **kwd ) )
        return self.specified_date_in_error_list_grid( trans, **kwd )
    @web.expose
    def specified_month_all( self, trans, **kwd ):
        params = util.Params( kwd )
        message = ''
        monitor_email = params.get( 'monitor_email', 'monitor@bx.psu.edu' )
        year, month = map( int, params.get( 'month', datetime.utcnow().strftime( "%Y-%m" ) ).split( "-" ) )
        start_date = date( year, month, 1 )
        end_date = start_date + timedelta( days=calendar.monthrange( year, month )[1] )
        month_label = start_date.strftime( "%B" )
        year_label = start_date.strftime( "%Y" )
        q = sa.select( ( sa.func.date( model.Job.table.c.create_time ).label( 'date' ),
                         sa.func.sum( sa.case( [ ( model.User.table.c.email == monitor_email, 1 ) ], else_=0 ) ).label( 'monitor_jobs' ),
                         sa.func.count( model.Job.table.c.id ).label( 'total_jobs' ) ),
                       whereclause = sa.and_( model.Job.table.c.create_time >= start_date,
                                              model.Job.table.c.create_time < end_date ),
                       from_obj = [ sa.outerjoin( model.Job.table, 
                                                  model.History.table ).outerjoin( model.User.table ) ],
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
        return trans.fill_template( '/webapps/reports/jobs_specified_month_all.mako', 
                                    month_label=month_label, 
                                    year_label=year_label, 
                                    month=month, 
                                    jobs=jobs, 
                                    message=message ) 
    @web.expose
    def specified_month_in_error( self, trans, **kwd ):
        params = util.Params( kwd )
        message = ''
        year, month = map( int, params.get( 'month', datetime.utcnow().strftime( "%Y-%m" ) ).split( "-" ) )
        start_date = date( year, month, 1 )
        end_date = start_date + timedelta( days=calendar.monthrange( year, month )[1] )
        month_label = start_date.strftime( "%B" )
        year_label = start_date.strftime( "%Y" )
        q = sa.select( ( sa.func.date( model.Job.table.c.create_time ).label( 'date' ),
                         sa.func.count( model.Job.table.c.id ).label( 'total_jobs' ) ),
                       whereclause = sa.and_( model.Job.table.c.state == 'error',
                                              model.Job.table.c.create_time >= start_date, 
                                              model.Job.table.c.create_time < end_date ),
                       from_obj = [ sa.outerjoin( model.Job.table, 
                                                  model.History.table ).outerjoin( model.User.table ) ],
                       group_by = [ 'date' ],
                       order_by = [ sa.desc( 'date' ) ] )
        jobs = []
        for row in q.execute():
            jobs.append( ( row.date.strftime( "%A" ),
                           row.date,
                           row.total_jobs,
                           row.date.strftime( "%d" ) ) )
        return trans.fill_template( '/webapps/reports/jobs_specified_month_in_error.mako', 
                                    month_label=month_label, 
                                    year_label=year_label, 
                                    month=month, 
                                    jobs=jobs, 
                                    message=message )
    @web.expose
    def all_unfinished( self, trans, **kwd ):
        if 'operation' in kwd:
            operation = kwd['operation'].lower()
            if operation == "job_info":
                return trans.response.send_redirect( web.url_for( controller='jobs',
                                                                  action='job_info',
                                                                  **kwd ) )
            if operation == "tool_per_month":
                # The received id is the job id, so we need to get the id of the user
                # that submitted the job.
                job_id = kwd.get( 'id', None )
                job = get_job( trans, job_id )
                kwd[ 'tool_id' ] = job.tool_id
                return trans.response.send_redirect( web.url_for( controller='jobs',
                                                                  action='tool_per_month',
                                                                  **kwd ) )
            if operation == "user_per_month":
                # The received id is the job id, so we need to get the id of the user
                # that submitted the job.
                job_id = kwd.get( 'id', None )
                job = get_job( trans, job_id )
                kwd[ 'email' ] = None # For anonymous users
                if job.history:
                    if job.history.user:
                        email = job.history.user.email
                        kwd[ 'email' ] = email
                # TODO: handle libraries
                return trans.response.send_redirect( web.url_for( controller='jobs',
                                                                  action='user_per_month',
                                                                  **kwd ) )
        return self.all_unfinished_list_grid( trans, **kwd )
    @web.expose
    def per_month_all( self, trans, **kwd ):
        params = util.Params( kwd )
        message = ''
        monitor_email = params.get( 'monitor_email', 'monitor@bx.psu.edu' )
        q = sa.select( ( sa.func.date_trunc( 'month', sa.func.date( model.Job.table.c.create_time ) ).label( 'date' ),
                         sa.func.sum( sa.case( [( model.User.table.c.email == monitor_email, 1 )], else_=0 ) ).label( 'monitor_jobs' ),
                         sa.func.count( model.Job.table.c.id ).label( 'total_jobs' ) ),
                       from_obj = [ sa.outerjoin( model.Job.table, 
                                                  model.History.table ).outerjoin( model.User.table ) ],
                       group_by = [ sa.func.date_trunc( 'month', sa.func.date( model.Job.table.c.create_time ) ) ],
                       order_by = [ sa.desc( 'date' ) ] )
        jobs = []
        for row in q.execute():
            jobs.append( ( row.date.strftime( "%Y-%m" ),
                           row.total_jobs - row.monitor_jobs,
                           row.monitor_jobs, 
                           row.total_jobs,
                           row.date.strftime( "%B" ),
                           row.date.strftime( "%Y" ) ) )
        return trans.fill_template( '/webapps/reports/jobs_per_month_all.mako', jobs=jobs, message=message )
    @web.expose
    def per_month_in_error( self, trans, **kwd ):
        params = util.Params( kwd )
        message = ''
        q = sa.select( ( sa.func.date_trunc( 'month', sa.func.date( model.Job.table.c.create_time ) ).label( 'date' ),
                         sa.func.count( model.Job.table.c.id ).label( 'total_jobs' ) ),
                       whereclause = model.Job.table.c.state == 'error',
                       from_obj = [ model.Job.table ],
                       group_by = [ sa.func.date_trunc( 'month', sa.func.date( model.Job.table.c.create_time ) ) ],
                       order_by = [ sa.desc( 'date' ) ] )
        jobs = []
        for row in q.execute():
            jobs.append( ( row.date.strftime( "%Y-%m" ), 
                           row.total_jobs,
                           row.date.strftime( "%B" ),
                           row.date.strftime( "%Y" ) ) )
        return trans.fill_template( '/webapps/reports/jobs_per_month_in_error.mako', jobs=jobs, message=message )
    @web.expose
    def per_user( self, trans, **kwd ):
        params = util.Params( kwd )
        message = ''
        jobs = []
        q = sa.select( ( model.User.table.c.email.label( 'user_email' ),
                         sa.func.count( model.Job.table.c.id ).label( 'total_jobs' ) ),
                       from_obj = [ sa.outerjoin( model.Job.table, 
                                                  model.GalaxySession.table ).outerjoin( model.User.table ) ],
                       group_by = [ 'user_email' ],
                       order_by = [ sa.desc( 'total_jobs' ), 'user_email' ] )
        for row in q.execute():
            jobs.append( ( row.user_email, 
                           row.total_jobs ) )
        return trans.fill_template( '/webapps/reports/jobs_per_user.mako', jobs=jobs, message=message )
    @web.expose
    def user_per_month( self, trans, **kwd ):
        params = util.Params( kwd )
        message = ''
        email = util.restore_text( params.get( 'email', '' ) )
        q = sa.select( ( sa.func.date_trunc( 'month', sa.func.date( model.Job.table.c.create_time ) ).label( 'date' ),
                         sa.func.count( model.Job.table.c.id ).label( 'total_jobs' ) ),
                       whereclause = sa.and_( model.Job.table.c.session_id == model.GalaxySession.table.c.id,
                                              model.GalaxySession.table.c.user_id == model.User.table.c.id,
                                              model.User.table.c.email == email
                                            ),
                       from_obj = [ sa.join( model.Job.table, 
                                             model.GalaxySession.table ).join( model.User.table ) ],
                       group_by = [ sa.func.date_trunc( 'month', sa.func.date( model.Job.table.c.create_time ) ) ],
                       order_by = [ sa.desc( 'date' ) ] )
        jobs = []
        for row in q.execute():
            jobs.append( ( row.date.strftime( "%Y-%m" ), 
                           row.total_jobs,
                           row.date.strftime( "%B" ),
                           row.date.strftime( "%Y" ) ) )
        return trans.fill_template( '/webapps/reports/jobs_user_per_month.mako',
                                    email=util.sanitize_text( email ),
                                    jobs=jobs, message=message )
    @web.expose
    def user_for_month( self, trans, **kwd ):
        if 'operation' in kwd:
            operation = kwd['operation'].lower()
            if operation == "job_info":
                return trans.response.send_redirect( web.url_for( controller='jobs',
                                                                  action='job_info',
                                                                  **kwd ) )
            if operation == "tool_per_month":
                # The received id is the job id, so we need to get the id of the user
                # that submitted the job.
                job_id = kwd.get( 'id', None )
                job = get_job( trans, job_id )
                kwd[ 'tool_id' ] = job.tool_id
                return trans.response.send_redirect( web.url_for( controller='jobs',
                                                                  action='tool_per_month',
                                                                  **kwd ) )
            if operation == "user_per_month":
                # The received id is the job id, so we need to get the id of the user
                # that submitted the job.
                job_id = kwd.get( 'id', None )
                job = get_job( trans, job_id )
                kwd[ 'email' ] = None # For anonymous users
                if job.history:
                    if job.history.user:
                        email = job.history.user.email
                        kwd[ 'email' ] = email
                # TODO: handle libraries
                return trans.response.send_redirect( web.url_for( controller='jobs',
                                                                  action='user_per_month',
                                                                  **kwd ) )
        return self.user_for_month_list_grid( trans, **kwd )
    @web.expose
    def per_tool( self, trans, **kwd ):
        params = util.Params( kwd )
        message = ''
        jobs = []
        q = sa.select( ( model.Job.table.c.tool_id.label( 'tool_id' ),
                         sa.func.count( model.Job.table.c.id ).label( 'total_jobs' ) ),
                       from_obj = [ model.Job.table ],
                       group_by = [ 'tool_id' ],
                       order_by = [ 'tool_id' ] )
        for row in q.execute():
            jobs.append( ( row.tool_id, 
                           row.total_jobs ) )
        return trans.fill_template( '/webapps/reports/jobs_per_tool.mako', jobs=jobs, message=message )
    @web.expose
    def tool_per_month( self, trans, **kwd ):
        params = util.Params( kwd )
        message = ''
        tool_id = params.get( 'tool_id', 'Add a column1' )
        q = sa.select( ( sa.func.date_trunc( 'month', sa.func.date( model.Job.table.c.create_time ) ).label( 'date' ),
                         sa.func.count( model.Job.table.c.id ).label( 'total_jobs' ) ),
                       whereclause = model.Job.table.c.tool_id == tool_id, 
                       from_obj = [ model.Job.table ],
                       group_by = [ sa.func.date_trunc( 'month', sa.func.date( model.Job.table.c.create_time ) ) ],
                       order_by = [ sa.desc( 'date' ) ] )
        jobs = []
        for row in q.execute():
            jobs.append( ( row.date.strftime( "%Y-%m" ), 
                           row.total_jobs,
                           row.date.strftime( "%B" ),
                           row.date.strftime( "%Y" ) ) )
        return trans.fill_template( '/webapps/reports/jobs_tool_per_month.mako', tool_id=tool_id, jobs=jobs, message=message )
    @web.expose
    def tool_for_month( self, trans, **kwd ):
        if 'operation' in kwd:
            operation = kwd['operation'].lower()
            if operation == "job_info":
                return trans.response.send_redirect( web.url_for( controller='jobs',
                                                                  action='job_info',
                                                                  **kwd ) )
            if operation == "tool_per_month":
                # The received id is the job id, so we need to get the id of the user
                # that submitted the job.
                job_id = kwd.get( 'id', None )
                job = get_job( trans, job_id )
                kwd[ 'tool_id' ] = job.tool_id
                return trans.response.send_redirect( web.url_for( controller='jobs',
                                                                  action='tool_per_month',
                                                                  **kwd ) )
            if operation == "user_per_month":
                # The received id is the job id, so we need to get the id of the user
                # that submitted the job.
                job_id = kwd.get( 'id', None )
                job = get_job( trans, job_id )
                kwd[ 'email' ] = None # For anonymous users
                if job.history:
                    if job.history.user:
                        email = job.history.user.email
                        kwd[ 'email' ] = email
                # TODO: handle libraries
                return trans.response.send_redirect( web.url_for( controller='jobs',
                                                                  action='user_per_month',
                                                                  **kwd ) )
        return self.tool_for_month_list_grid( trans, **kwd )
    @web.expose
    def job_info( self, trans, **kwd ):
        params = util.Params( kwd )
        message = ''
        job_id = trans.security.decode_id( kwd.get( 'id', '' ) )
        job_info = trans.sa_session.query( model.Job.table.join( model.GalaxySession.table ).join( model.User.table ) ) \
                                   .filter( and_( model.Job.table.c.id == job_id,
                                                  model.Job.table.c.session_id == model.GalaxySession.table.c.id,
                                                  model.GalaxySession.table.c.user_id == model.User.table.c.id ) ) \
                                   .one()
        # TODO: for some reason the job_info.id is not the same as job_id in the template, so we need to pass job_id
        # This needs to be fixed ASAP!
        return trans.fill_template( '/webapps/reports/job_info.mako', job_id=job_id, job_info=job_info, message=message )
    @web.expose
    def per_domain( self, trans, **kwd ):
        # TODO: rewrite using alchemy
        params = util.Params( kwd )
        message = ''
        engine = model.mapping.metadata.engine
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
        return trans.fill_template( '/webapps/reports/jobs_per_domain.mako', jobs=jobs, message=message )

## ---- Utility methods -------------------------------------------------------

def get_job( trans, id ):
    return trans.sa_session.query( trans.model.Job ).get( trans.security.decode_id( id ) )
