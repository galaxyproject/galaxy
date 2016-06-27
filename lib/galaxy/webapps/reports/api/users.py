import calendar
import logging
import time
from datetime import datetime, date, timedelta

import sqlalchemy as sa

from galaxy import model
from galaxy.web.base.controller import BaseAPIController, web
from galaxy.webapps.reports.controllers.query import ReportQueryBuilder
from galaxy.webapps.reports.api.util import to_epoch, date_filter, state_filter

log = logging.getLogger( __name__ )


class UserAPIController( BaseAPIController, ReportQueryBuilder ):

    @web.expose
    @web.json
    def registered_users_total( self, trans, **kwd ):
        """
        GET /api/users/registered/total """
        num_users = trans.sa_session.query( model.User ).count()
        return num_users

    @web.expose
    @web.json
    def registered_users( self, trans, **kwd ):
        """
        GET /api/users/registered
        GET /api/users/registered/:year
        GET /api/users/registered/:year/:month
        """
        strftime, where_date, select, start_date, end_date = date_filter(self, kwd, model.User.table.c.create_time)
        where_clauses = []

        if where_date:
            where_clauses += where_date


        q = sa.select(
            (
                select.label('date'),
                sa.func.count( model.User.table.c.id ).label( 'num_users' )
            ),
            whereclause=sa.and_(*where_clauses),
            from_obj=[model.User.table],
            group_by=['date'],
            order_by=['date'],
        )

        users = []
        for row in q.execute():
            users.append((
                row.date.strftime(strftime),
                row.num_users,
            ))

        return users

    @web.expose
    @web.json
    def last_login( self, trans, **kwd ):
        """
        GET /api/users/last_login
        """

        users = []

        for user in trans.sa_session.query(model.User) \
                                    .order_by(model.User.table.c.email):

            last_login = None

            if user.galaxy_sessions:
                last_galaxy_session = user.galaxy_sessions[ 0 ]
                last_login = to_epoch(last_galaxy_session.update_time)

            users.append((
                user.username,
                user.email,
                last_login
            ))

        return users
