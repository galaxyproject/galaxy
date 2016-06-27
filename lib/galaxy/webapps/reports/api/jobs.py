from __future__ import print_function
import calendar
import logging
from collections import namedtuple
from datetime import datetime, date, timedelta

import sqlalchemy as sa
from sqlalchemy import and_, not_, or_

from markupsafe import escape

from galaxy import model, util
from galaxy.web.base.controller import BaseAPIController, web
from galaxy.web.framework.helpers import grids
import re
from math import ceil, floor
from galaxy.webapps.reports.controllers.query import ReportQueryBuilder
from galaxy.webapps.reports.api.util import date_filter, state_filter

log = logging.getLogger( __name__ )


class JobsAPIController( BaseAPIController, ReportQueryBuilder ):

    @web.json
    @web.expose
    def jobs_per_date(self, trans, **kwd):
        """
        Queries the DB for all jobs in given month

        /jobs/date/
        /jobs/date/?state={error,ok}

        /jobs/date/:year/
        /jobs/date/:year/?state={error,ok}

        /jobs/date/:year/:month/
        /jobs/date/:year/:month/?state={error,ok}
        """

        strftime, where_date, select, start_date, end_date = date_filter(self, kwd, model.Job.table.c.create_time)
        where_state = state_filter(kwd, model.Job.table.c.state)

        where_clauses = []
        if where_date:
            where_clauses += where_date

        if where_state:
            where_clauses += where_state


        month_jobs = sa.select(
            (
                select.label('date'),
                sa.func.count(model.Job.table.c.id).label('total_jobs')
            ),
            whereclause=sa.and_(*where_clauses),
            from_obj=[model.Job.table],
            group_by=['date'],
            order_by=['date'],
        )

        jobs = []
        for row in month_jobs.execute():
            jobs.append((
                row.date.strftime(strftime),
                row.total_jobs,
            ))

        return jobs

    @web.json
    @web.expose
    def jobs_group_users(self, trans, **kwd):
        """
        Queries the DB for all jobs grouped by users
        /jobs/user/
        /jobs/user/date/2016/
        /jobs/user/date/2016/06/
        """
        strftime, where_date, select, start_date, end_date = date_filter(self, kwd, model.Job.table.c.create_time)
        where_state = state_filter(kwd, model.Job.table.c.state)

        where_clauses = []

        if where_date:
            where_clauses += where_date

        if where_state:
            where_clauses += where_state


        all_jobs_per_user = sa.select(
            (
                select.label('date'),
                sa.func.count(model.Job.table.c.id).label('total_jobs'),
                model.User.table.c.email.label( 'user_email' )
            ),
            from_obj=[sa.outerjoin(model.Job.table, model.User.table)],
            whereclause=sa.and_(*where_clauses),
            group_by=['date', 'user_email'],
            order_by=['date']
        )

        results = {}
        for row in all_jobs_per_user.execute():
            if row.user_email not in results:
                results[row.user_email] = []

            results[row.user_email].append((
                row.date.strftime(strftime),
                row.total_jobs,
            ))

        return results

    @web.json
    @web.expose
    def jobs_per_user(self, trans, **kwd):
        """
        Queries the DB for all jobs run by a given user
        /jobs/user/:user/
        /jobs/user/:user/date/:year/
        /jobs/user/:user/date/:year/:month/
        """
        strftime, where_date, select, start_date, end_date = date_filter(self, kwd, model.Job.table.c.create_time)
        where_state = state_filter(kwd, model.Job.table.c.state)

        where_clauses = [
            model.User.table.c.email == kwd['user']
        ]

        if where_date:
            where_clauses += where_date

        if where_state:
            where_clauses += where_state


        all_jobs_per_user = sa.select(
            (
                select.label('date'),
                sa.func.count(model.Job.table.c.id).label('total_jobs'),
                model.User.table.c.email.label( 'user_email' )
            ),
            from_obj=[sa.outerjoin(model.Job.table, model.User.table)],
            whereclause=sa.and_(*where_clauses),
            group_by=['date', 'user_email'],
            order_by=['date']
        )

        results = []
        for row in all_jobs_per_user.execute():
            results.append((
                row.date.strftime(strftime),
                row.total_jobs,
            ))

        return results

    # /jobs/tool/tool_id
    # /jobs/tool/tool_id?state=error
    # /jobs/tool/tool_id/2016/06
    # /jobs/info/job_id

    @web.json
    @web.expose
    def jobs_per_tool(self, trans, **kwd):
        """
        Queries the DB for all jobs run by a given user
        /jobs/tool/:tool/
        /jobs/tool/:tool/:year/
        /jobs/tool/:tool/:year/:month/
        """
        strftime, where_date, select, start_date, end_date = date_filter(self, kwd, model.Job.table.c.create_time)
        where_state = state_filter(kwd, model.Job.table.c.state)

        where_clauses = []

        if 'tool_id' in kwd:
            where_clauses.append(model.Job.table.c.tool_id == kwd['tool_id'])

        if where_date:
            where_clauses += where_date

        if where_state:
            where_clauses += where_state

        tool_jobs = sa.select(
            (
                select.label('date'),
                model.Job.table.c.tool_id.label( 'tool_id' ),
                sa.func.count( model.Job.table.c.id ).label( 'total_jobs' )
            ),
            whereclause=sa.and_(*where_clauses),
            from_obj=[model.Job.table],
            group_by=['tool_id', 'date'],
            order_by=['tool_id']
        )

        if 'tool_id' not in kwd:
            results = {}
            for row in tool_jobs.execute():
                if row.tool_id not in results:
                    results[row.tool_id] = []

                results[row.tool_id].append((
                    row.date.strftime(strftime),
                    row.total_jobs,
                ))
        else:
            results = []
            for row in tool_jobs.execute():
                results.append((
                    row.date.strftime(strftime),
                    row.total_jobs,
                ))

        return results
