from datetime import *
import calendar
from galaxy.webapps.reports.base.controller import *
import galaxy.model
import pkg_resources
pkg_resources.require( "sqlalchemy>=0.3" )
import sqlalchemy as sa
import logging
log = logging.getLogger( __name__ )

class Users( BaseController ):
    @web.expose
    def registered_users( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = ''
        engine = galaxy.model.mapping.metadata.engine
        s = """
        SELECT
            count(id) AS num_users
        FROM
            galaxy_user
         """
        rows = engine.text( s ).execute().fetchall()
        num_users = rows[0].num_users
        return trans.fill_template( 'registered_users.mako', num_users=num_users, msg=msg )
    @web.expose
    def registered_users_per_month( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = ''
        q = sa.select( ( sa.func.date_trunc( 'month', sa.func.date( galaxy.model.User.table.c.create_time ) ).label( 'date' ),
                         sa.func.count( galaxy.model.User.table.c.id ).label( 'num_users' ) ),
                       from_obj = [ galaxy.model.User.table ],
                       group_by = [ sa.func.date_trunc( 'month', sa.func.date( galaxy.model.User.table.c.create_time ) ) ],
                       order_by = [ sa.desc( 'date' ) ] )
        users = []
        for row in q.execute():
            users.append( ( row.date.strftime( "%Y-%m" ), 
                           row.num_users,
                           row.date.strftime( "%B" ),
                           row.date.strftime( "%Y" ) ) )
        return trans.fill_template( 'registered_users_per_month.mako', users=users, msg=msg )
    @web.expose
    def specified_month( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = ''
        year, month = map( int, params.get( 'month', datetime.utcnow().strftime( "%Y-%m" ) ).split( "-" ) )
        start_date = date( year, month, 1 )
        end_date = start_date + timedelta( days=calendar.monthrange( year, month )[1] )
        month_label = start_date.strftime( "%B" )
        year_label = start_date.strftime( "%Y" )
        q = sa.select( ( sa.func.date_trunc( 'day', sa.func.date( galaxy.model.User.table.c.create_time ) ).label( 'date' ),
                         sa.func.count( galaxy.model.User.table.c.id ).label( 'num_users' ) ),
                       from_obj = [ galaxy.model.User.table ],
                       group_by = [ sa.func.date_trunc( 'day', sa.func.date( galaxy.model.User.table.c.create_time ) ) ],
                       order_by = [ sa.desc( 'date' ) ] )
        users = []
        for row in q.execute():
            users.append( ( row.date.strftime( "%Y-%m-%d" ),
                            row.date.strftime( "%d" ), 
                            row.num_users, 
                            row.date.strftime( "%A" ) ) )
        return trans.fill_template( 'registered_users_specified_month.mako', 
                                    month_label=month_label, 
                                    year_label=year_label, 
                                    month=month, 
                                    users=users, 
                                    msg=msg )
    @web.expose
    def specified_date( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = ''
        year, month, day = map( int, params.get( 'specified_date', datetime.utcnow().strftime( "%Y-%m-%d" ) ).split( "-" ) )
        start_date = date( year, month, day )
        end_date = start_date + timedelta( days=1 )
        day_of_month = start_date.strftime( "%d" )
        day_label = start_date.strftime( "%A" )
        month_label = start_date.strftime( "%B" )
        year_label = start_date.strftime( "%Y" )
        q = sa.select( ( sa.func.date_trunc( 'month', sa.func.date( galaxy.model.User.table.c.create_time ) ).label( 'date' ),
                         galaxy.model.User.table.c.email ),
                       whereclause = sa.and_( galaxy.model.User.table.c.create_time >= start_date,
                                              galaxy.model.User.table.c.create_time < end_date ),
                       from_obj = [ galaxy.model.User.table ],
                       order_by = [ sa.desc( galaxy.model.User.table.c.email ) ] )
        users = []
        for row in q.execute():
            users.append( ( row.email ) )
        return trans.fill_template( 'registered_users_specified_date.mako', 
                                    specified_date=start_date, 
                                    day_label=day_label, 
                                    month_label=month_label, 
                                    year_label=year_label, 
                                    day_of_month=day_of_month, 
                                    users=users, 
                                    msg=msg )
