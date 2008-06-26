from datetime import datetime
from calendar import day_name, month_name
from galaxy.webapps.reports.base.controller import *
import galaxy.model
import pkg_resources
pkg_resources.require( "sqlalchemy>=0.3" )
#from sqlalchemy import eagerload, desc
import sqlalchemy
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
        engine = galaxy.model.mapping.metadata.engine
        users = []
        s = """
        SELECT
            num_users AS num_users,
            year_month AS year_month,
            to_char(a_timestamp, 'Month') AS month_label,
            to_char(a_timestamp, 'YYYY') AS year_label
        FROM
            (SELECT
                num_users AS num_users,
                year_month AS year_month,
                to_timestamp(year_month, 'YYYY-MM-DD') AS a_timestamp
            FROM
                (SELECT
                    count(id) AS num_users,
                    substr(create_time, 1, 7) AS year_month
                FROM
                    galaxy_user
                GROUP BY
                    year_month
                ORDER BY
                    year_month DESC) AS foo) AS bar
        """
        user_rows = engine.text( s ).execute().fetchall()
        for user in user_rows:
            users.append( ( user.year_month, user.num_users, user.month_label, user.year_label ) )
        return trans.fill_template( 'registered_users_per_month.mako', users=users, msg=msg )
    @web.expose
    def specified_month( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = ''
        year_month = datetime.utcnow().strftime( "%Y-%m" )
        month = params.get( 'month', year_month )
        engine = galaxy.model.mapping.metadata.engine
        users = []
        monitor_email = params.get( 'monitor_email', 'monitor@bx.psu.edu' )
        month_label = params.get( 'month_label', month_name[ int( datetime.utcnow().strftime( "%m" ) ) ] )
        year_label = params.get( 'year_label', datetime.utcnow().strftime( "%Y" ) )
        s = """
        SELECT
            year_month_day AS year_month_day,
            day_of_month AS day_of_month,
            num_users AS num_users,
            to_char(a_timestamp, 'Day') AS day_label
        FROM
            (SELECT
                foo.create_time AS year_month_day,
                foo.day_of_month AS day_of_month,
                count(foo.create_time) AS num_users,
                to_timestamp(foo.create_time, 'YYYY-MM-DD') AS a_timestamp
            FROM
                (SELECT
                    substr(create_time, 1, 10) AS create_time,
                    substr(create_time, 9, 2) AS day_of_month
                FROM
                    galaxy_user
                WHERE
                    substr(create_time, 1, 7) = '%s'
                GROUP BY
                    day_of_month,
                    create_time) AS foo
            GROUP BY
                day_of_month,
                create_time
            ORDER BY
                create_time DESC) AS bar
        """ % month
        user_rows = engine.text( s ).execute().fetchall()
        for user in user_rows:
            users.append( ( user.year_month_day, user.day_of_month, user.num_users, user.day_label ) )
        return trans.fill_template( 'registered_users_specified_month.mako', month_label=month_label, year_label=year_label, month=month, users=users, msg=msg )
    @web.expose
    def specified_date( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = ''
        engine = galaxy.model.mapping.metadata.engine
        users = []
        today = datetime.utcnow().strftime( "%Y-%m-%d" )
        specified_date = params.get( 'specified_date', today )
        day_label = params.get( 'day_label', datetime.utcnow().strftime( "%d" ) )
        month_label = params.get( 'month_label', month_name[ int( datetime.utcnow().strftime( "%m" ) ) ] )
        year_label = params.get( 'year_label', datetime.utcnow().strftime( "%Y" ) )
        day_of_month = params.get( 'day_of_month', datetime.utcnow().strftime( "%d" ) )
        s = """
        SELECT
            email AS email
        FROM
            galaxy_user
        WHERE
            substr(create_time, 1, 10) = '%s'
        ORDER BY
            email
        """ % ( specified_date )
        user_rows = engine.text( s ).execute().fetchall()
        for user in user_rows:
            users.append( ( user.email ) )
        return trans.fill_template( 'registered_users_specified_date.mako', specified_date=specified_date, day_label=day_label, month_label=month_label, year_label=year_label, day_of_month=day_of_month, users=users, msg=msg )
