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
    def jobs_group_user(self, trans, **kwd):
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

        results = []
        for row in all_jobs_per_user.execute():
            results.append((
                row.user_email,
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

#
#    @web.expose
#    def per_tool( self, trans, **kwd ):
#        message = ''
#        PageSpec = namedtuple('PageSpec', ['entries', 'offset', 'page', 'pages_found'])
#
#        params = util.Params( kwd )
#        monitor_email = params.get( 'monitor_email', 'monitor@bx.psu.edu' )
#        specs = sorter( 'tool_id', kwd )
#        sort_id = specs.sort_id
#        order = specs.order
#        arrow = specs.arrow
#        _order = specs.exc_order
#        time_period = kwd.get('spark_time')
#        time_period, _time_period = get_spark_time( time_period )
#        spark_limit = 30
#        offset = 0
#        limit = 10
#
#        if "entries" in kwd:
#            entries = int(kwd.get( 'entries' ))
#        else:
#            entries = 10
#        limit = entries * 4
#
#        if "offset" in kwd:
#            offset = int(kwd.get( 'offset' ))
#        else:
#            offset = 0
#
#        if "page" in kwd:
#            page = int(kwd.get( 'page' ))
#        else:
#            page = 1
#
#        # In case we don't know which is the monitor user we will query for all jobs
#        monitor_user_id = get_monitor_id( trans, monitor_email )
#
#        jobs = []
#        q = sa.select( ( model.Job.table.c.tool_id.label( 'tool_id' ),
#                         sa.func.count( model.Job.table.c.id ).label( 'total_jobs' ) ),
#                       whereclause=model.Job.table.c.user_id != monitor_user_id,
#                       from_obj=[ model.Job.table ],
#                       group_by=[ 'tool_id' ],
#                       order_by=[ _order ],
#                       offset=offset,
#                       limit=limit )
#
#        all_jobs_per_tool = sa.select( ( model.Job.table.c.tool_id.label( 'tool_id' ),
#                                        model.Job.table.c.id.label( 'id' ),
#                                        self.select_day( model.Job.table.c.create_time ).label( 'date' ) ),
#                                      whereclause=model.Job.table.c.user_id != monitor_user_id,
#                                      from_obj=[ model.Job.table ] )
#
#        currday = date.today()
#        trends = dict()
#        for job in all_jobs_per_tool.execute():
#            curr_tool = re.sub(r'\W+', '', str(job.tool_id))
#            try:
#                day = currday - job.date
#            except TypeError:
#                day = currday - datetime.date(job.date)
#
#            day = day.days
#            container = floor(day / _time_period)
#            container = int(container)
#            try:
#                if container < spark_limit:
#                    trends[curr_tool][container] += 1
#            except KeyError:
#                trends[curr_tool] = [0] * spark_limit
#                if container < spark_limit:
#                    trends[curr_tool][container] += 1
#
#        for row in q.execute():
#            jobs.append( ( row.tool_id,
#                           row.total_jobs ) )
#
#        pages_found = ceil(len(jobs) / float(entries))
#        page_specs = PageSpec(entries, offset, page, pages_found)
#
#        return trans.fill_template( '/webapps/reports/jobs_per_tool.mako',
#                                    order=order,
#                                    arrow=arrow,
#                                    sort_id=sort_id,
#                                    spark_limit=spark_limit,
#                                    time_period=time_period,
#                                    trends=trends,
#                                    jobs=jobs,
#                                    message=message,
#                                    is_user_jobs_only=monitor_user_id,
#                                    page_specs=page_specs )
#
#    @web.expose
#    def errors_per_tool( self, trans, **kwd ):
#        """
#        Queries the DB for user jobs in error. Filters out monitor jobs.
#        """
#
#        message = ''
#        PageSpec = namedtuple('PageSpec', ['entries', 'offset', 'page', 'pages_found'])
#
#        params = util.Params( kwd )
#        monitor_email = params.get( 'monitor_email', 'monitor@bx.psu.edu' )
#        specs = sorter( 'tool_id', kwd )
#        sort_id = specs.sort_id
#        order = specs.order
#        arrow = specs.arrow
#        _order = specs.exc_order
#        time_period = kwd.get('spark_time')
#        time_period, _time_period = get_spark_time( time_period )
#        spark_limit = 30
#        offset = 0
#        limit = 10
#
#        if "entries" in kwd:
#            entries = int(kwd.get( 'entries' ))
#        else:
#            entries = 10
#        limit = entries * 4
#
#        if "offset" in kwd:
#            offset = int(kwd.get( 'offset' ))
#        else:
#            offset = 0
#
#        if "page" in kwd:
#            page = int(kwd.get( 'page' ))
#        else:
#            page = 1
#
#        # In case we don't know which is the monitor user we will query for all jobs
#        monitor_user_id = get_monitor_id( trans, monitor_email )
#
#        jobs_in_error_per_tool = sa.select( ( model.Job.table.c.tool_id.label( 'tool_id' ),
#                                              sa.func.count( model.Job.table.c.id ).label( 'total_jobs' ) ),
#                                            whereclause=sa.and_( model.Job.table.c.state == 'error',
#                                                                 model.Job.table.c.user_id != monitor_user_id ),
#                                            from_obj=[ model.Job.table ],
#                                            group_by=[ 'tool_id' ],
#                                            order_by=[ _order ],
#                                            offset=offset,
#                                            limit=limit )
#
#        all_jobs_per_tool_errors = sa.select( ( self.select_day( model.Job.table.c.create_time ).label( 'date' ),
#                                              model.Job.table.c.id.label( 'id' ),
#                                              model.Job.table.c.tool_id.label( 'tool_id' ) ),
#                                              whereclause=sa.and_( model.Job.table.c.state == 'error',
#                                                                   model.Job.table.c.user_id != monitor_user_id ),
#                                              from_obj=[ model.Job.table ]
#                                              )
#
#        currday = date.today()
#        trends = dict()
#        for job in all_jobs_per_tool_errors.execute():
#            curr_tool = re.sub(r'\W+', '', str(job.tool_id))
#            try:
#                day = currday - job.date
#            except TypeError:
#                day = currday - datetime.date(job.date)
#
#            # convert day into days/weeks/months/years
#            day = day.days
#            container = floor(day / _time_period)
#            container = int(container)
#            try:
#                if container < spark_limit:
#                    trends[curr_tool][container] += 1
#            except KeyError:
#                trends[curr_tool] = [0] * spark_limit
#                if day < spark_limit:
#                    trends[curr_tool][container] += 1
#        jobs = []
#        for row in jobs_in_error_per_tool.execute():
#            jobs.append( ( row.total_jobs, row.tool_id ) )
#
#        pages_found = ceil(len(jobs) / float(entries))
#        page_specs = PageSpec(entries, offset, page, pages_found)
#
#        return trans.fill_template( '/webapps/reports/jobs_errors_per_tool.mako',
#                                    order=order,
#                                    arrow=arrow,
#                                    sort_id=sort_id,
#                                    spark_limit=spark_limit,
#                                    time_period=time_period,
#                                    trends=trends,
#                                    jobs=jobs,
#                                    message=message,
#                                    is_user_jobs_only=monitor_user_id,
#                                    page_specs=page_specs )
#
#    @web.expose
#    def tool_per_month( self, trans, **kwd ):
#        message = ''
#
#        params = util.Params( kwd )
#        monitor_email = params.get( 'monitor_email', 'monitor@bx.psu.edu' )
#        specs = sorter( 'date', kwd )
#        sort_id = specs.sort_id
#        order = specs.order
#        arrow = specs.arrow
#        _order = specs.exc_order
#        # In case we don't know which is the monitor user we will query for all jobs
#        monitor_user_id = get_monitor_id( trans, monitor_email )
#
#        tool_id = params.get( 'tool_id', 'Add a column1' )
#        specified_date = params.get( 'specified_date', datetime.utcnow().strftime( "%Y-%m-%d" ) )
#        q = sa.select( ( self.select_month( model.Job.table.c.create_time ).label( 'date' ),
#                         sa.func.count( model.Job.table.c.id ).label( 'total_jobs' ) ),
#                       whereclause=sa.and_( model.Job.table.c.tool_id == tool_id,
#                                            model.Job.table.c.user_id != monitor_user_id ),
#                       from_obj=[ model.Job.table ],
#                       group_by=self.group_by_month( model.Job.table.c.create_time ),
#                       order_by=[ _order ] )
#
#        # Use to make sparkline
#        all_jobs_for_tool = sa.select( ( self.select_month(model.Job.table.c.create_time).label('month'),
#                                        self.select_day(model.Job.table.c.create_time).label('day'),
#                                        model.Job.table.c.id.label('id') ),
#                                      whereclause=sa.and_( model.Job.table.c.tool_id == tool_id,
#                                                          model.Job.table.c.user_id != monitor_user_id ),
#                             from_obj=[ model.Job.table ] )
#        trends = dict()
#        for job in all_jobs_for_tool.execute():
#            job_day = int(job.day.strftime("%-d")) - 1
#            job_month = int(job.month.strftime("%-m"))
#            job_month_name = job.month.strftime("%B")
#            job_year = job.month.strftime("%Y")
#            key = str( job_month_name + job_year)
#
#            try:
#                trends[key][job_day] += 1
#            except KeyError:
#                job_year = int(job_year)
#                wday, day_range = calendar.monthrange(job_year, job_month)
#                trends[key] = [0] * day_range
#                trends[key][job_day] += 1
#
#        jobs = []
#        for row in q.execute():
#            jobs.append( ( row.date.strftime( "%Y-%m" ),
#                           row.total_jobs,
#                           row.date.strftime( "%B" ),
#                           row.date.strftime( "%Y" ) ) )
#        return trans.fill_template( '/webapps/reports/jobs_tool_per_month.mako',
#                                    order=order,
#                                    arrow=arrow,
#                                    sort_id=sort_id,
#                                    specified_date=specified_date,
#                                    tool_id=tool_id,
#                                    trends=trends,
#                                    jobs=jobs,
#                                    message=message,
#                                    is_user_jobs_only=monitor_user_id )
#
#    @web.expose
#    def job_info( self, trans, **kwd ):
#        message = ''
#        job = trans.sa_session.query( model.Job ) \
#                              .get( trans.security.decode_id( kwd.get( 'id', '' ) ) )
#        return trans.fill_template( '/webapps/reports/job_info.mako',
#                                    job=job,
#                                    message=message )
#
## ---- Utility methods -------------------------------------------------------
#
#
#def get_job( trans, id ):
#    return trans.sa_session.query( trans.model.Job ).get( trans.security.decode_id( id ) )
#
#
#def get_monitor_id( trans, monitor_email ):
#    """
#    A convenience method to obtain the monitor job id.
#    """
#    monitor_user_id = None
#    monitor_row = trans.sa_session.query( trans.model.User.table.c.id ) \
#        .filter( trans.model.User.table.c.email == monitor_email ) \
#        .first()
#    if monitor_row is not None:
#        monitor_user_id = monitor_row[0]
#    return monitor_user_id
