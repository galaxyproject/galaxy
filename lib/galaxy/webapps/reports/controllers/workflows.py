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
    class WorkflowNameColumn( grids.TextColumn ):
        def get_value( self, trans, grid, stored_workflow ):
            return stored_workflow.name
    class CreateTimeColumn( grids.DateTimeColumn ):
        def get_value( self, trans, grid, stored_workflow ):
            return stored_workflow.create_time
    class UserColumn( grids.TextColumn ):
        def get_value( self, trans, grid, stored_workflow ):
            if stored_workflow.user:
                return stored_workflow.user.email
            return 'unknown'
    class EmailColumn( grids.GridColumn ):
        def filter( self, trans, user, query, column_filter ):
            if column_filter == 'All':
                return query
            return query.filter( and_( model.StoredWorkflow.table.c.user_id == model.User.table.c.id,
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
    model_class = model.StoredWorkflow
    title = "Workflows"
    template='/webapps/reports/grid.mako'
    default_sort_key = "name"
    columns = [
        WorkflowNameColumn( "Name",
                            key="name",
                            #link=( lambda item: dict( operation="workflow_info", id=item.id, webapp="reports" ) ),
                            attach_popup=False,
                            filterable="advanced" ),
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
    ]
    columns.append( grids.MulticolFilterColumn( "Search", 
                                                cols_to_filter=[ columns[0], columns[2] ], 
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

class Workflows( BaseUIController ):

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
            if operation == "workflow_per_month":
                # The received id is the stored_workflow id.
                return trans.response.send_redirect( web.url_for( controller='workflows',
                                                                  action='workflow_per_month',
                                                                  **kwd ) )
            elif operation == "user_per_month":
                stored_workflow_id = kwd.get( 'id', None )
                workflow = get_workflow( trans, workflow_id )
                if workflow.user:
                    kwd[ 'email' ] = workflow.user.email
                else:
                    kwd[ 'email' ] = None # For anonymous users ( shouldn't happen with workflows )
                return trans.response.send_redirect( web.url_for( controller='workflows',
                                                                  action='user_per_month',
                                                                  **kwd ) )
        return self.specified_date_list_grid( trans, **kwd )
    @web.expose
    def per_month_all( self, trans, **kwd ):
        params = util.Params( kwd )
        message = ''
        q = sa.select( ( sa.func.date_trunc( 'month', sa.func.date( model.StoredWorkflow.table.c.create_time ) ).label( 'date' ),sa.func.count( model.StoredWorkflow.table.c.id ).label( 'total_workflows' ) ),
                       from_obj = [ sa.outerjoin( model.StoredWorkflow.table, model.User.table ) ],
                       group_by = [ sa.func.date_trunc( 'month', sa.func.date( model.StoredWorkflow.table.c.create_time ) ) ],
                       order_by = [ sa.desc( 'date' ) ] )
        workflows = []
        for row in q.execute():
            workflows.append( ( row.date.strftime( "%Y-%m" ),
                                row.total_workflows,
                                row.date.strftime( "%B" ),
                                row.date.strftime( "%Y" ) ) )
        return trans.fill_template( '/webapps/reports/workflows_per_month_all.mako',
                                    workflows=workflows,
                                    message=message )
    @web.expose
    def per_user( self, trans, **kwd ):
        params = util.Params( kwd )
        message = ''
        workflows = []
        q = sa.select( ( model.User.table.c.email.label( 'user_email' ),
                         sa.func.count( model.StoredWorkflow.table.c.id ).label( 'total_workflows' ) ),
                       from_obj = [ sa.outerjoin( model.StoredWorkflow.table, model.User.table ) ],
                       group_by = [ 'user_email' ],
                       order_by = [ sa.desc( 'total_workflows' ), 'user_email' ] )
        for row in q.execute():
            workflows.append( ( row.user_email, 
                                row.total_workflows ) )
        return trans.fill_template( '/webapps/reports/workflows_per_user.mako', workflows=workflows, message=message )
    @web.expose
    def user_per_month( self, trans, **kwd ):
        params = util.Params( kwd )
        message = ''
        email = util.restore_text( params.get( 'email', '' ) )
        user_id = trans.security.decode_id( params.get( 'id', '' ) )
        q = sa.select( ( sa.func.date_trunc( 'month', sa.func.date( model.StoredWorkflow.table.c.create_time ) ).label( 'date' ),
                         sa.func.count( model.StoredWorkflow.table.c.id ).label( 'total_workflows' ) ),
                       whereclause = model.StoredWorkflow.table.c.user_id == user_id,
                       from_obj = [ model.StoredWorkflow.table ],
                       group_by = [ sa.func.date_trunc( 'month', sa.func.date( model.StoredWorkflow.table.c.create_time ) ) ],
                       order_by = [ sa.desc( 'date' ) ] )
        workflows = []
        for row in q.execute():
            workflows.append( ( row.date.strftime( "%Y-%m" ), 
                                row.total_workflows,
                                row.date.strftime( "%B" ),
                                row.date.strftime( "%Y" ) ) )
        return trans.fill_template( '/webapps/reports/workflows_user_per_month.mako',
                                    email=util.sanitize_text( email ),
                                    workflows=workflows,
                                    message=message )

## ---- Utility methods -------------------------------------------------------

def get_workflow( trans, id ):
    return trans.sa_session.query( trans.model.Workflow ).get( trans.security.decode_id( id ) )
