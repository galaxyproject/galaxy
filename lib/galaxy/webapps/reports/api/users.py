import calendar
import logging
from datetime import datetime, date, timedelta

import sqlalchemy as sa

import galaxy.model
from galaxy.web.base.controller import BaseAPIController, web
from galaxy.webapps.reports.controllers.query import ReportQueryBuilder

log = logging.getLogger( __name__ )


class UserAPIController( BaseAPIController, ReportQueryBuilder ):

    @web.expose
    @web.json
    def registered_users_total( self, trans, **kwd ):
        """
        GET /api/users/registered/total """
        num_users = trans.sa_session.query( galaxy.model.User ).count()
        return num_users

    @web.expose
    @web.json
    def registered_users( self, trans, **kwd ):
        """
        GET /api/users/registered
        """
        q = sa.select( ( self.select_month( galaxy.model.User.table.c.create_time ).label( 'date' ),
                         sa.func.count( galaxy.model.User.table.c.id ).label( 'num_users' ) ),
                       from_obj=[ galaxy.model.User.table ],
                       group_by=self.group_by_month( galaxy.model.User.table.c.create_time ))

        users = []
        for row in q.execute():
            users.append((
                row.date.strftime("%s"),
                row.num_users,
            ))

        return users

    @web.expose
    @web.json
    def registered_users_in_month( self, trans, **kwd ):
        """
        GET /api/users/registered/:month
        """
        specified_date = kwd.get( 'specified_date', datetime.utcnow().strftime( "%Y-%m-%d" ) )
        specified_month = specified_date[ :7 ]
        year, month = map( int, specified_month.split( "-" ) )
        start_date = date( year, month, 1 )
        end_date = start_date + timedelta( days=calendar.monthrange( year, month )[1] )
        q = sa.select( ( self.select_day( galaxy.model.User.table.c.create_time ).label( 'date' ),
                         sa.func.count( galaxy.model.User.table.c.id ).label( 'num_users' ) ),
                       whereclause=sa.and_( galaxy.model.User.table.c.create_time >= start_date,
                                            galaxy.model.User.table.c.create_time < end_date ),
                       from_obj=[ galaxy.model.User.table ],
                       group_by=self.group_by_day( galaxy.model.User.table.c.create_time ),
                       order_by=[ sa.desc( 'date' ) ] )
        users = []
        for row in q.execute():
            users.append((
                row.date.strftime("%s"),
                row.num_users,
            ))

        return users
