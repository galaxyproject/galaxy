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
            return '<div class="count-box state-color-%s">%s</div>' % ( job.state, job.state )
        def filter( self, trans, user, query, column_filter ):
            if column_filter == 'Unfinished':
                return query.filter( not_( or_( model.Job.table.c.state == model.Job.states.OK, 
                                                model.Job.table.c.state == model.Job.states.ERROR, 
                                                model.Job.table.c.state == model.Job.states.DELETED ) ) )
            return query
    class ToolColumn( grids.TextColumn ):
        def get_value( self, trans, grid, job ):
            return job.tool_id
    class CreateTimeColumn( grids.DateTimeColumn ):
        def get_value( self, trans, grid, job ):
            return job.create_time
    class UserColumn( grids.GridColumn ):
        def get_value( self, trans, grid, job ):
            if job.user:
                return job.user.email
            return 'anonymous'
    class EmailColumn( grids.GridColumn ):
        def filter( self, trans, user, query, column_filter ):
            if column_filter == 'All':
                return query
            return query.filter( and_( model.Job.table.c.user_id == model.User.table.c.id,
                                       model.User.table.c.email == column_filter ) )
    class SpecifiedDateColumn( grids.GridColumn ):
        def filter( self, trans, user, query, column_filter ):
            if column_filter == 'All':
                return query
            # We are either filtering on a date like YYYY-MM-DD or on a month like YYYY-MM,
            # so we need to figure out which type of date we have
            if column_filter.count( '-' ) == 2:
                # We are filtering on a date like YYYY-MM-DD
                year, month, day = map( int, column_filter.split( "-" ) )
                start_date = date( year, month, day )
                end_date = start_date + timedelta( days=1 )
                return query.filter( and_( self.model_class.table.c.create_time >= start_date,
                                           self.model_class.table.c.create_time < end_date ) )
            if column_filter.count( '-' ) == 1:
                # We are filtering on a month like YYYY-MM
                year, month = map( int, column_filter.split( "-" ) )
                start_date = date( year, month, 1 )
                end_date = start_date + timedelta( days=calendar.monthrange( year, month )[1] )
                return query.filter( and_( self.model_class.table.c.create_time >= start_date,
                                           self.model_class.table.c.create_time < end_date ) )

    # Grid definition
    use_async = False
    model_class = model.Job
    title = "Jobs"
    template='/webapps/reports/grid.mako'
    default_sort_key = "id"
    columns = [
        JobIdColumn( "Id",
                     key="id",
                     link=( lambda item: dict( operation="job_info", id=item.id, webapp="reports" ) ),
                     attach_popup=False,
                     filterable="advanced" ),
        StateColumn( "State",
                      key="state",
                      attach_popup=False ),
        ToolColumn( "Tool Id",
                    key="tool_id",
                    link=( lambda item: dict( operation="tool_per_month", id=item.id, webapp="reports" ) ),
                    attach_popup=False ),
        CreateTimeColumn( "Creation Time",
                          key="create_time",
                          attach_popup=False ),
        UserColumn( "User",
                    key="email",
                    model_class=model.User,
                    link=( lambda item: dict( operation="user_per_month", id=item.id, webapp="reports" ) ),
                    attach_popup=False ),
        # Columns that are valid for filtering but are not visible.
        SpecifiedDateColumn( "Specified Date",
                             key="specified_date",
                             visible=False ),
        EmailColumn( "Email",
                     key="email",
                     model_class=model.User,
                     visible=False ),
        grids.StateColumn( "State",
                           key="state",
                           visible=False,
                           filterable="advanced" )
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
        return trans.sa_session.query( self.model_class ) \
                               .join( model.User ) \
                               .enable_eagerloads( False )

class Jobs( BaseUIController ):

    specified_date_list_grid = SpecifiedDateListGrid()

    @web.expose
    def specified_date_handler( self, trans, **kwd ):
        # We add params to the keyword dict in this method in order to rename the param
        # with an "f-" prefix, simulating filtering by clicking a search link.  We have
        # to take this approach because the "-" character is illegal in HTTP requests.
        if 'f-specified_date' in kwd and 'specified_date' not in kwd:
            # The user clicked a State link in the Advanced Search box, so 'specified_date'
            # will have been eliminated.
            pass
        elif 'specified_date' not in kwd:
            kwd[ 'f-specified_date' ] = 'All'
        else:
            kwd[ 'f-specified_date' ] = kwd[ 'specified_date' ]
        if 'operation' in kwd:
            operation = kwd['operation'].lower()
            if operation == "job_info":
                return trans.response.send_redirect( web.url_for( controller='jobs',
                                                                  action='job_info',
                                                                  **kwd ) )
            elif operation == "tool_for_month":
                kwd[ 'f-tool_id' ] = kwd[ 'tool_id' ]
            elif operation == "tool_per_month":
                # The received id is the job id, so we need to get the job's tool_id.
                job_id = kwd.get( 'id', None )
                job = get_job( trans, job_id )
                kwd[ 'tool_id' ] = job.tool_id
                return trans.response.send_redirect( web.url_for( controller='jobs',
                                                                  action='tool_per_month',
                                                                  **kwd ) )
            elif operation == "user_for_month":
                kwd[ 'f-email' ] = util.restore_text( kwd[ 'email' ] )
            elif operation == "user_per_month":
                # The received id is the job id, so we need to get the id of the user
                # that submitted the job.
                job_id = kwd.get( 'id', None )
                job = get_job( trans, job_id )
                if job.user:
                    kwd[ 'email' ] = job.user.email
                else:
                    kwd[ 'email' ] = None # For anonymous users
                return trans.response.send_redirect( web.url_for( controller='jobs',
                                                                  action='user_per_month',
                                                                  **kwd ) )
            elif operation == "specified_date_in_error":
                kwd[ 'f-state' ] = 'error'
            elif operation == "unfinished":
                kwd[ 'f-state' ] = 'Unfinished'
        return self.specified_date_list_grid( trans, **kwd )
    @web.expose
    def specified_month_all( self, trans, **kwd ):
        params = util.Params( kwd )
        message = ''
        monitor_email = params.get( 'monitor_email', 'monitor@bx.psu.edu' )
        # If specified_date is not received, we'll default to the current month
        specified_date = kwd.get( 'specified_date', datetime.utcnow().strftime( "%Y-%m-%d" ) )
        specified_month = specified_date[ :7 ]
        year, month = map( int, specified_month.split( "-" ) )
        start_date = date( year, month, 1 )
        end_date = start_date + timedelta( days=calendar.monthrange( year, month )[1] )
        month_label = start_date.strftime( "%B" )
        year_label = start_date.strftime( "%Y" )
        q = sa.select( ( sa.func.date( model.Job.table.c.create_time ).label( 'date' ),
                         sa.func.sum( sa.case( [ ( model.User.table.c.email == monitor_email, 1 ) ], else_=0 ) ).label( 'monitor_jobs' ),
                         sa.func.count( model.Job.table.c.id ).label( 'total_jobs' ) ),
                       whereclause = sa.and_( model.Job.table.c.create_time >= start_date,
                                              model.Job.table.c.create_time < end_date ),
                       from_obj = [ sa.outerjoin( model.Job.table, model.User.table ) ],
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
        # If specified_date is not received, we'll default to the current month
        specified_date = kwd.get( 'specified_date', datetime.utcnow().strftime( "%Y-%m-%d" ) )
        specified_month = specified_date[ :7 ]
        year, month = map( int, specified_month.split( "-" ) )
        start_date = date( year, month, 1 )
        end_date = start_date + timedelta( days=calendar.monthrange( year, month )[1] )
        month_label = start_date.strftime( "%B" )
        year_label = start_date.strftime( "%Y" )
        q = sa.select( ( sa.func.date( model.Job.table.c.create_time ).label( 'date' ),
                         sa.func.count( model.Job.table.c.id ).label( 'total_jobs' ) ),
                       whereclause = sa.and_( model.Job.table.c.state == 'error',
                                              model.Job.table.c.create_time >= start_date, 
                                              model.Job.table.c.create_time < end_date ),
                       from_obj = [ sa.outerjoin( model.Job.table, model.User.table ) ],
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
    def per_month_all( self, trans, **kwd ):
        params = util.Params( kwd )
        message = ''
        monitor_email = params.get( 'monitor_email', 'monitor@bx.psu.edu' )
        q = sa.select( ( sa.func.date_trunc( 'month', sa.func.date( model.Job.table.c.create_time ) ).label( 'date' ),
                         sa.func.sum( sa.case( [( model.User.table.c.email == monitor_email, 1 )], else_=0 ) ).label( 'monitor_jobs' ),
                         sa.func.count( model.Job.table.c.id ).label( 'total_jobs' ) ),
                       from_obj = [ sa.outerjoin( model.Job.table, model.User.table ) ],
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
        return trans.fill_template( '/webapps/reports/jobs_per_month_all.mako',
                                    jobs=jobs,
                                    message=message )
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
        return trans.fill_template( '/webapps/reports/jobs_per_month_in_error.mako',
                                    jobs=jobs,
                                    message=message )
    @web.expose
    def per_user( self, trans, **kwd ):
        params = util.Params( kwd )
        message = ''
        jobs = []
        q = sa.select( ( model.User.table.c.email.label( 'user_email' ),
                         sa.func.count( model.Job.table.c.id ).label( 'total_jobs' ) ),
                       from_obj = [ sa.outerjoin( model.Job.table, model.User.table ) ],
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
                       from_obj = [ sa.join( model.Job.table, model.User.table ) ],
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
        return trans.fill_template( '/webapps/reports/jobs_per_tool.mako',
                                    jobs=jobs,
                                    message=message )
    @web.expose
    def tool_per_month( self, trans, **kwd ):
        params = util.Params( kwd )
        message = ''
        tool_id = params.get( 'tool_id', 'Add a column1' )
        specified_date = params.get( 'specified_date', datetime.utcnow().strftime( "%Y-%m-%d" ) )
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
        return trans.fill_template( '/webapps/reports/jobs_tool_per_month.mako',
                                    specified_date=specified_date,
                                    tool_id=tool_id,
                                    jobs=jobs,
                                    message=message )
    @web.expose
    def job_info( self, trans, **kwd ):
        params = util.Params( kwd )
        message = ''
        job = trans.sa_session.query( model.Job ) \
                              .get( trans.security.decode_id( kwd.get( 'id', '' ) ) )
        return trans.fill_template( '/webapps/reports/job_info.mako',
                                    job=job,
                                    message=message )
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
