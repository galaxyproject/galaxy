from datetime import *
from time import strftime
import calendar, operator
from galaxy.web.base.controller import *
import galaxy.model
from galaxy.model.orm import *
import pkg_resources
pkg_resources.require( "SQLAlchemy >= 0.4" )
import sqlalchemy as sa
import logging
log = logging.getLogger( __name__ )

class Users( BaseUIController ):
    @web.expose
    def registered_users( self, trans, **kwd ):
        message = util.restore_text( kwd.get( 'message', '' ) )
        num_users = trans.sa_session.query( galaxy.model.User ).count()
        return trans.fill_template( '/webapps/reports/registered_users.mako', num_users=num_users, message=message )
    @web.expose
    def registered_users_per_month( self, trans, **kwd ):
        message = util.restore_text( kwd.get( 'message', '' ) )
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
        return trans.fill_template( '/webapps/reports/registered_users_per_month.mako',
                                    users=users,
                                    message=message )
    @web.expose
    def specified_month( self, trans, **kwd ):
        message = util.restore_text( kwd.get( 'message', '' ) )
        # If specified_date is not received, we'll default to the current month
        specified_date = kwd.get( 'specified_date', datetime.utcnow().strftime( "%Y-%m-%d" ) )
        specified_month = specified_date[ :7 ]
        year, month = map( int, specified_month.split( "-" ) )
        start_date = date( year, month, 1 )
        end_date = start_date + timedelta( days=calendar.monthrange( year, month )[1] )
        month_label = start_date.strftime( "%B" )
        year_label = start_date.strftime( "%Y" )
        q = sa.select( ( sa.func.date_trunc( 'day', sa.func.date( galaxy.model.User.table.c.create_time ) ).label( 'date' ),
                         sa.func.count( galaxy.model.User.table.c.id ).label( 'num_users' ) ),
                       whereclause = sa.and_( galaxy.model.User.table.c.create_time >= start_date,
                                              galaxy.model.User.table.c.create_time < end_date ),
                       from_obj = [ galaxy.model.User.table ],
                       group_by = [ sa.func.date_trunc( 'day', sa.func.date( galaxy.model.User.table.c.create_time ) ) ],
                       order_by = [ sa.desc( 'date' ) ] )
        users = []
        for row in q.execute():
            users.append( ( row.date.strftime( "%Y-%m-%d" ),
                            row.date.strftime( "%d" ), 
                            row.num_users, 
                            row.date.strftime( "%A" ) ) )
        return trans.fill_template( '/webapps/reports/registered_users_specified_month.mako', 
                                    month_label=month_label, 
                                    year_label=year_label, 
                                    month=month, 
                                    users=users, 
                                    message=message )
    @web.expose
    def specified_date( self, trans, **kwd ):
        message = util.restore_text( kwd.get( 'message', '' ) )
        # If specified_date is not received, we'll default to the current month
        specified_date = kwd.get( 'specified_date', datetime.utcnow().strftime( "%Y-%m-%d" ) )
        year, month, day = map( int, specified_date.split( "-" ) )
        start_date = date( year, month, day )
        end_date = start_date + timedelta( days=1 )
        day_of_month = start_date.strftime( "%d" )
        day_label = start_date.strftime( "%A" )
        month_label = start_date.strftime( "%B" )
        year_label = start_date.strftime( "%Y" )
        q = sa.select( ( sa.func.date_trunc( 'day', sa.func.date( galaxy.model.User.table.c.create_time ) ).label( 'date' ),
                         galaxy.model.User.table.c.email ),
                       whereclause = sa.and_( galaxy.model.User.table.c.create_time >= start_date,
                                              galaxy.model.User.table.c.create_time < end_date ),
                       from_obj = [ galaxy.model.User.table ],
                       order_by = [ galaxy.model.User.table.c.email ] )
        users = []
        for row in q.execute():
            users.append( ( row.email ) )
        return trans.fill_template( '/webapps/reports/registered_users_specified_date.mako', 
                                    specified_date=start_date, 
                                    day_label=day_label, 
                                    month_label=month_label, 
                                    year_label=year_label, 
                                    day_of_month=day_of_month, 
                                    users=users, 
                                    message=message )
    @web.expose
    def last_access_date( self, trans, **kwd ):
        message = util.restore_text( kwd.get( 'message', '' ) )
        not_logged_in_for_days = kwd.get( 'not_logged_in_for_days', 90 )
        if not not_logged_in_for_days:
            not_logged_in_for_days = 0
        cutoff_time = datetime.utcnow() - timedelta( days=int( not_logged_in_for_days ) )
        now = strftime( "%Y-%m-%d %H:%M:%S" )
        users = []
        for user in trans.sa_session.query( galaxy.model.User ) \
                                    .filter( galaxy.model.User.table.c.deleted==False ) \
                                    .order_by( galaxy.model.User.table.c.email ):
            if user.galaxy_sessions:
                last_galaxy_session = user.galaxy_sessions[ 0 ]
                if last_galaxy_session.update_time < cutoff_time:
                    users.append( ( user.email, last_galaxy_session.update_time.strftime( "%Y-%m-%d" ) ) )
            else:
                # The user has never logged in
                users.append( ( user.email, "never logged in" ) )
        users = sorted( users, key=operator.itemgetter( 1 ), reverse=True )
        return trans.fill_template( '/webapps/reports/users_last_access_date.mako',
                                    users=users,
                                    not_logged_in_for_days=not_logged_in_for_days,
                                    message=message )

    @web.expose
    def user_disk_usage( self, trans, **kwd ):
        message = util.restore_text( kwd.get( 'message', '' ) )
        user_cutoff = int( kwd.get( 'user_cutoff', 60 ) )
        # disk_usage isn't indexed
        users = sorted( trans.sa_session.query( galaxy.model.User ).all(), key=operator.attrgetter( 'disk_usage' ), reverse=True )
        if user_cutoff:
            users = users[:user_cutoff]
        return trans.fill_template( '/webapps/reports/users_user_disk_usage.mako',
                                    users=users,
                                    user_cutoff=user_cutoff,
                                    message=message )
