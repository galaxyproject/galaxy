from __future__ import print_function

import calendar
import logging
import re
from collections import namedtuple
from datetime import (
    date,
    datetime,
    timedelta
)
from math import ceil, floor

import sqlalchemy as sa
from markupsafe import escape
from sqlalchemy import and_, not_, or_

from galaxy import model, util
from galaxy.web.base.controller import BaseUIController, web
from galaxy.webapps.reports.controllers.query import ReportQueryBuilder
from galaxy.webapps.reports.framework import grids

log = logging.getLogger(__name__)


class Timer(object):
    def __init__(self):
        self.start()
        self.stop()
        self.ERROR = self.time_elapsed()

    def start(self):
        self.start_time = datetime.now()

    def stop(self):
        try:
            self.stop_time = datetime.now()
            self.time_delta = self.stop_time - self.start_time
            del(self.stop_time)
            del(self.start_time)
        except NameError:
            print("You need to start before you can stop!")

    def time_elapsed(self):
        try:
            return_time = self.time_delta - self.ERROR
        except NameError:
            print("You need to start and stop before there's an elapsed time!")
        except AttributeError:
            return_time = self.time_delta

        return return_time


def sorter(default_sort_id, kwd):
    """
    Initialize sorting variables
    """
    SortSpec = namedtuple('SortSpec', ['sort_id', 'order', 'arrow', 'exc_order'])

    sort_id = kwd.get('sort_id')
    order = kwd.get('order')

    # Parse the default value
    if sort_id == "default":
        sort_id = default_sort_id

    # Create the sort
    if order == "asc":
        _order = sa.asc(sort_id)
    elif order == "desc":
        _order = sa.desc(sort_id)
    else:
        # In case of default
        order = "desc"
        _order = sa.desc(sort_id)

    # Create an arrow icon to put beside the ordered column
    up_arrow = "&#x2191;"
    down_arrow = "&#x2193;"
    arrow = " "

    if order == "asc":
        arrow += down_arrow
    else:
        arrow += up_arrow

    return SortSpec(sort_id, order, arrow, _order)


def get_spark_time(time_period):
    _time_period = 0

    if time_period == "days":
        _time_period = 1.0
    elif time_period == "weeks":
        _time_period = 7.0
    elif time_period == "months":
        _time_period = 30.0
    elif time_period == "years":
        _time_period = 365.0
    else:
        time_period = "days"
        _time_period = 1.0

    return time_period, _time_period


class SpecifiedDateListGrid(grids.Grid):

    class JobIdColumn(grids.IntegerColumn):

        def get_value(self, trans, grid, job):
            return job.id

    class StateColumn(grids.TextColumn):

        def get_value(self, trans, grid, job):
            return '<div class="count-box state-color-%s">%s</div>' % (job.state, job.state)

        def filter(self, trans, user, query, column_filter):
            if column_filter == 'Unfinished':
                return query.filter(not_(or_(model.Job.table.c.state == model.Job.states.OK,
                                             model.Job.table.c.state == model.Job.states.ERROR,
                                             model.Job.table.c.state == model.Job.states.DELETED)))
            return query

    class ToolColumn(grids.TextColumn):

        def get_value(self, trans, grid, job):
            return job.tool_id

        def filter(self, trans, user, query, column_filter):
            if column_filter is not None:
                query = query.filter(model.Job.table.c.tool_id == column_filter)

            return query

    class CreateTimeColumn(grids.DateTimeColumn):

        def get_value(self, trans, grid, job):
            return job.create_time.strftime("%b %d, %Y, %H:%M:%S")

    class UserColumn(grids.GridColumn):

        def get_value(self, trans, grid, job):
            if job.user:
                return escape(job.user.email)
            return 'anonymous'

    class EmailColumn(grids.GridColumn):

        def filter(self, trans, user, query, column_filter):
            if column_filter == 'All':
                return query
            return query.filter(and_(model.Job.table.c.user_id == model.User.table.c.id,
                                     model.User.table.c.email == column_filter))

    class SpecifiedDateColumn(grids.GridColumn):

        def filter(self, trans, user, query, column_filter):
            if column_filter == 'All':
                return query
            # We are either filtering on a date like YYYY-MM-DD or on a month like YYYY-MM,
            # so we need to figure out which type of date we have
            if column_filter.count('-') == 2:  # We are filtering on a date like YYYY-MM-DD
                year, month, day = map(int, column_filter.split("-"))
                start_date = date(year, month, day)
                end_date = start_date + timedelta(days=1)
            if column_filter.count('-') == 1:  # We are filtering on a month like YYYY-MM
                year, month = map(int, column_filter.split("-"))
                start_date = date(year, month, 1)
                end_date = start_date + timedelta(days=calendar.monthrange(year, month)[1])

            return query.filter(and_(self.model_class.table.c.create_time >= start_date,
                                     self.model_class.table.c.create_time < end_date))

    # Grid definition
    use_async = False
    model_class = model.Job
    title = "Jobs"
    default_sort_key = "id"
    columns = [
        JobIdColumn("Id",
                    key="id",
                    link=(lambda item: dict(operation="job_info", id=item.id, webapp="reports")),
                    attach_popup=False,
                    filterable="advanced"),
        StateColumn("State",
                    key="state",
                    attach_popup=False),
        ToolColumn("Tool Id",
                   key="tool_id",
                   link=(lambda item: dict(operation="tool_per_month", id=item.id, webapp="reports")),
                   attach_popup=False),
        CreateTimeColumn("Creation Time",
                         key="create_time",
                         attach_popup=False),
        UserColumn("User",
                   key="email",
                   model_class=model.User,
                   link=(lambda item: dict(operation="user_per_month", id=item.id, webapp="reports")),
                   attach_popup=False),
        # Columns that are valid for filtering but are not visible.
        SpecifiedDateColumn("Specified Date",
                            key="specified_date",
                            visible=False),
        EmailColumn("Email",
                    key="email",
                    model_class=model.User,
                    visible=False),
        grids.StateColumn("State",
                          key="state",
                          visible=False,
                          filterable="advanced")
    ]
    columns.append(grids.MulticolFilterColumn("Search",
                                              cols_to_filter=[columns[1], columns[2]],
                                              key="free-text-search",
                                              visible=False,
                                              filterable="standard"))
    standard_filters = []
    default_filter = {'specified_date': 'All'}
    num_rows_per_page = 50
    use_paging = True

    def build_initial_query(self, trans, **kwd):
        params = util.Params(kwd)
        monitor_email = params.get('monitor_email', 'monitor@bx.psu.edu')
        monitor_user_id = get_monitor_id(trans, monitor_email)
        return trans.sa_session.query(self.model_class) \
                               .join(model.User) \
                               .filter(model.Job.table.c.user_id != monitor_user_id)\
                               .enable_eagerloads(False)


class Jobs(BaseUIController, ReportQueryBuilder):

    """
    Class contains functions for querying data requested by user via the webapp. It exposes the functions and
    responds to requests with the filled .mako templates.
    """

    specified_date_list_grid = SpecifiedDateListGrid()

    @web.expose
    def specified_date_handler(self, trans, **kwd):
        # We add params to the keyword dict in this method in order to rename the param
        # with an "f-" prefix, simulating filtering by clicking a search link.  We have
        # to take this approach because the "-" character is illegal in HTTP requests.
        kwd['sort_id'] = 'default'
        kwd['order'] = 'default'

        if 'f-specified_date' in kwd and 'specified_date' not in kwd:
            # The user clicked a State link in the Advanced Search box, so 'specified_date'
            # will have been eliminated.
            pass
        elif 'specified_date' not in kwd:
            kwd['f-specified_date'] = 'All'
        else:
            kwd['f-specified_date'] = kwd['specified_date']
        if 'operation' in kwd:
            operation = kwd['operation'].lower()
            if operation == "job_info":
                return trans.response.send_redirect(web.url_for(controller='jobs',
                                                                action='job_info',
                                                                **kwd))
            elif operation == "tool_for_month":
                kwd['f-tool_id'] = kwd['tool_id']
            elif operation == "tool_per_month":
                # The received id is the job id, so we need to get the job's tool_id.
                job_id = kwd.get('id', None)
                job = get_job(trans, job_id)
                kwd['tool_id'] = job.tool_id
                return trans.response.send_redirect(web.url_for(controller='jobs',
                                                                action='tool_per_month',
                                                                **kwd))
            elif operation == "user_for_month":
                kwd['f-email'] = util.restore_text(kwd['email'])
            elif operation == "user_per_month":
                # The received id is the job id, so we need to get the id of the user
                # that submitted the job.
                job_id = kwd.get('id', None)
                job = get_job(trans, job_id)
                if job.user:
                    kwd['email'] = job.user.email
                else:
                    kwd['email'] = None  # For anonymous users
                return trans.response.send_redirect(web.url_for(controller='jobs',
                                                                action='user_per_month',
                                                                **kwd))
            elif operation == "specified_date_in_error":
                kwd['f-state'] = 'error'
            elif operation == "unfinished":
                kwd['f-state'] = 'Unfinished'
            elif operation == "specified_tool_in_error":
                kwd['f-state'] = 'error'
                kwd['f-tool_id'] = kwd['tool_id']
        return self.specified_date_list_grid(trans, **kwd)

    def _calculate_trends_for_jobs(self, jobs_query):
        trends = dict()
        for job in jobs_query.execute():
            job_day = int(job.date.strftime("%-d")) - 1
            job_month = int(job.date.strftime("%-m"))
            job_month_name = job.date.strftime("%B")
            job_year = job.date.strftime("%Y")
            key = str(job_month_name + job_year)

            try:
                trends[key][job_day] += 1
            except KeyError:
                job_year = int(job_year)
                wday, day_range = calendar.monthrange(job_year, job_month)
                trends[key] = [0] * day_range
                trends[key][job_day] += 1
        return trends

    def _calculate_job_table(self, jobs_query):
        jobs = []
        for row in jobs_query.execute():
            month_name = row.date.strftime("%B")
            year = int(row.date.strftime("%Y"))

            jobs.append((
                row.date.strftime("%Y-%m"),
                row.total_jobs,
                month_name,
                year
            ))
        return jobs

    @web.expose
    def specified_month_all(self, trans, **kwd):
        """
        Queries the DB for all jobs in given month, defaults to current month.
        """
        message = ''
        PageSpec = namedtuple('PageSpec', ['entries', 'offset', 'page', 'pages_found'])

        params = util.Params(kwd)
        monitor_email = params.get('monitor_email', 'monitor@bx.psu.edu')
        specs = sorter('date', kwd)
        offset = 0
        limit = 10
        sort_id = specs.sort_id
        order = specs.order
        arrow = specs.arrow
        _order = specs.exc_order

        if "entries" in kwd:
            entries = int(kwd.get('entries'))
        else:
            entries = 10
        limit = entries * 4

        if "offset" in kwd:
            offset = int(kwd.get('offset'))
        else:
            offset = 0

        if "page" in kwd:
            page = int(kwd.get('page'))
        else:
            page = 1

        # In case we don't know which is the monitor user we will query for all jobs
        monitor_user_id = get_monitor_id(trans, monitor_email)

        # If specified_date is not received, we'll default to the current month
        specified_date = kwd.get('specified_date', datetime.utcnow().strftime("%Y-%m-%d"))
        specified_month = specified_date[:7]

        year, month = map(int, specified_month.split("-"))
        start_date = date(year, month, 1)
        end_date = start_date + timedelta(days=calendar.monthrange(year, month)[1])
        month_label = start_date.strftime("%B")
        year_label = start_date.strftime("%Y")

        # Use to make the page table
        month_jobs = sa.select((sa.func.date(model.Job.table.c.create_time).label('date'),
                                sa.func.count(model.Job.table.c.id).label('total_jobs')),
                               whereclause=sa.and_(model.Job.table.c.user_id != monitor_user_id,
                                                   model.Job.table.c.create_time >= start_date,
                                                   model.Job.table.c.create_time < end_date),
                               from_obj=[model.Job.table],
                               group_by=['date'],
                               order_by=[_order],
                               offset=offset,
                               limit=limit)

        # Use to make trendline
        all_jobs = sa.select((model.Job.table.c.create_time.label('date'), model.Job.table.c.id.label('id')),
                             whereclause=sa.and_(model.Job.table.c.user_id != monitor_user_id,
                                                 model.Job.table.c.create_time >= start_date,
                                                 model.Job.table.c.create_time < end_date))

        trends = dict()
        for job in all_jobs.execute():
            job_hour = int(job.date.strftime("%-H"))
            job_day = job.date.strftime("%d")

            try:
                trends[job_day][job_hour] += 1
            except KeyError:
                trends[job_day] = [0] * 24
                trends[job_day][job_hour] += 1

        jobs = []
        for row in month_jobs.execute():
            row_dayname = row.date.strftime("%A")
            row_day = row.date.strftime("%d")

            jobs.append((row_dayname,
                         row_day,
                         row.total_jobs,
                         row.date))

        pages_found = ceil(len(jobs) / float(entries))
        page_specs = PageSpec(entries, offset, page, pages_found)

        return trans.fill_template('/webapps/reports/jobs_specified_month_all.mako',
                                   order=order,
                                   arrow=arrow,
                                   sort_id=sort_id,
                                   month_label=month_label,
                                   year_label=year_label,
                                   month=month,
                                   page_specs=page_specs,
                                   jobs=jobs,
                                   trends=trends,
                                   is_user_jobs_only=monitor_user_id,
                                   message=message)

    @web.expose
    def specified_month_in_error(self, trans, **kwd):
        """
        Queries the DB for the user jobs in error.
        """
        message = ''
        PageSpec = namedtuple('PageSpec', ['entries', 'offset', 'page', 'pages_found'])

        params = util.Params(kwd)
        monitor_email = params.get('monitor_email', 'monitor@bx.psu.edu')
        specs = sorter('date', kwd)
        sort_id = specs.sort_id
        order = specs.order
        arrow = specs.arrow
        _order = specs.exc_order
        offset = 0
        limit = 10

        if "entries" in kwd:
            entries = int(kwd.get('entries'))
        else:
            entries = 10
        limit = entries * 4

        if "offset" in kwd:
            offset = int(kwd.get('offset'))
        else:
            offset = 0

        if "page" in kwd:
            page = int(kwd.get('page'))
        else:
            page = 1

        # In case we don't know which is the monitor user we will query for all jobs instead
        monitor_user_id = get_monitor_id(trans, monitor_email)

        # If specified_date is not received, we'll default to the current month
        specified_date = kwd.get('specified_date', datetime.utcnow().strftime("%Y-%m-%d"))
        specified_month = specified_date[:7]
        year, month = map(int, specified_month.split("-"))
        start_date = date(year, month, 1)
        end_date = start_date + timedelta(days=calendar.monthrange(year, month)[1])
        month_label = start_date.strftime("%B")
        year_label = start_date.strftime("%Y")

        month_jobs_in_error = sa.select((sa.func.date(model.Job.table.c.create_time).label('date'),
                                         sa.func.count(model.Job.table.c.id).label('total_jobs')),
                                        whereclause=sa.and_(model.Job.table.c.user_id != monitor_user_id,
                                                            model.Job.table.c.state == 'error',
                                                            model.Job.table.c.create_time >= start_date,
                                                            model.Job.table.c.create_time < end_date),
                                        from_obj=[model.Job.table],
                                        group_by=['date'],
                                        order_by=[_order],
                                        offset=offset,
                                        limit=limit)

        # Use to make trendline
        all_jobs_in_error = sa.select((model.Job.table.c.create_time.label('date'), model.Job.table.c.id.label('id')),
                                      whereclause=sa.and_(model.Job.table.c.user_id != monitor_user_id,
                                                          model.Job.table.c.state == 'error',
                                                          model.Job.table.c.create_time >= start_date,
                                                          model.Job.table.c.create_time < end_date))

        trends = dict()
        for job in all_jobs_in_error.execute():
            job_hour = int(job.date.strftime("%-H"))
            job_day = job.date.strftime("%d")

            try:
                trends[job_day][job_hour] += 1
            except KeyError:
                trends[job_day] = [0] * 24
                trends[job_day][job_hour] += 1

        jobs = []
        for row in month_jobs_in_error.execute():
            row_dayname = row.date.strftime("%A")
            row_day = row.date.strftime("%d")

            jobs.append((row_dayname,
                         row_day,
                         row.total_jobs,
                         row.date))

        pages_found = ceil(len(jobs) / float(entries))
        page_specs = PageSpec(entries, offset, page, pages_found)

        return trans.fill_template('/webapps/reports/jobs_specified_month_in_error.mako',
                                   order=order,
                                   arrow=arrow,
                                   sort_id=sort_id,
                                   month_label=month_label,
                                   year_label=year_label,
                                   month=month,
                                   jobs=jobs,
                                   trends=trends,
                                   message=message,
                                   is_user_jobs_only=monitor_user_id,
                                   page_specs=page_specs)

    @web.expose
    def per_month_all(self, trans, **kwd):
        """
        Queries the DB for all jobs. Avoids monitor jobs.
        """

        message = ''
        PageSpec = namedtuple('PageSpec', ['entries', 'offset', 'page', 'pages_found'])

        params = util.Params(kwd)
        monitor_email = params.get('monitor_email', 'monitor@bx.psu.edu')
        specs = sorter('date', kwd)
        sort_id = specs.sort_id
        order = specs.order
        arrow = specs.arrow
        _order = specs.exc_order
        offset = 0
        limit = 10

        if "entries" in kwd:
            entries = int(kwd.get('entries'))
        else:
            entries = 10
        limit = entries * 4

        if "offset" in kwd:
            offset = int(kwd.get('offset'))
        else:
            offset = 0

        if "page" in kwd:
            page = int(kwd.get('page'))
        else:
            page = 1

        # In case we don't know which is the monitor user we will query for all jobs
        monitor_user_id = get_monitor_id(trans, monitor_email)

        # Use to make the page table
        jobs_by_month = sa.select((self.select_month(model.Job.table.c.create_time).label('date'),
                                   sa.func.count(model.Job.table.c.id).label('total_jobs')),
                                  whereclause=model.Job.table.c.user_id != monitor_user_id,
                                  from_obj=[model.Job.table],
                                  group_by=self.group_by_month(model.Job.table.c.create_time),
                                  order_by=[_order],
                                  offset=offset,
                                  limit=limit)

        # Use to make sparkline
        all_jobs = sa.select((self.select_day(model.Job.table.c.create_time).label('date'),
                              model.Job.table.c.id.label('id')))

        trends = self._calculate_trends_for_jobs(all_jobs)
        jobs = self._calculate_job_table(jobs_by_month)

        pages_found = ceil(len(jobs) / float(entries))
        page_specs = PageSpec(entries, offset, page, pages_found)

        return trans.fill_template('/webapps/reports/jobs_per_month_all.mako',
                                   order=order,
                                   arrow=arrow,
                                   sort_id=sort_id,
                                   trends=trends,
                                   jobs=jobs,
                                   is_user_jobs_only=monitor_user_id,
                                   message=message,
                                   page_specs=page_specs)

    @web.expose
    def per_month_in_error(self, trans, **kwd):
        """
        Queries the DB for user jobs in error. Filters out monitor jobs.
        """

        message = ''
        PageSpec = namedtuple('PageSpec', ['entries', 'offset', 'page', 'pages_found'])

        params = util.Params(kwd)
        monitor_email = params.get('monitor_email', 'monitor@bx.psu.edu')
        specs = sorter('date', kwd)
        sort_id = specs.sort_id
        order = specs.order
        arrow = specs.arrow
        _order = specs.exc_order
        offset = 0
        limit = 10

        if "entries" in kwd:
            entries = int(kwd.get('entries'))
        else:
            entries = 10
        limit = entries * 4

        if "offset" in kwd:
            offset = int(kwd.get('offset'))
        else:
            offset = 0

        if "page" in kwd:
            page = int(kwd.get('page'))
        else:
            page = 1

        # In case we don't know which is the monitor user we will query for all jobs
        monitor_user_id = get_monitor_id(trans, monitor_email)

        # Use to make the page table
        jobs_in_error_by_month = sa.select((self.select_month(model.Job.table.c.create_time).label('date'),
                                            sa.func.count(model.Job.table.c.id).label('total_jobs')),
                                           whereclause=sa.and_(model.Job.table.c.state == 'error',
                                                               model.Job.table.c.user_id != monitor_user_id),
                                           from_obj=[model.Job.table],
                                           group_by=self.group_by_month(model.Job.table.c.create_time),
                                           order_by=[_order],
                                           offset=offset,
                                           limit=limit)

        # Use to make trendline
        all_jobs = sa.select((self.select_day(model.Job.table.c.create_time).label('date'),
                              model.Job.table.c.id.label('id')),
                             whereclause=sa.and_(model.Job.table.c.state == 'error',
                                                 model.Job.table.c.user_id != monitor_user_id))

        trends = self._calculate_trends_for_jobs(all_jobs)
        jobs = self._calculate_job_table(jobs_in_error_by_month)

        pages_found = ceil(len(jobs) / float(entries))
        page_specs = PageSpec(entries, offset, page, pages_found)

        return trans.fill_template('/webapps/reports/jobs_per_month_in_error.mako',
                                   order=order,
                                   arrow=arrow,
                                   sort_id=sort_id,
                                   trends=trends,
                                   jobs=jobs,
                                   message=message,
                                   is_user_jobs_only=monitor_user_id,
                                   page_specs=page_specs,
                                   offset=offset,
                                   limit=limit)

    @web.expose
    def per_user(self, trans, **kwd):
        total_time = Timer()
        q_time = Timer()

        total_time.start()
        params = util.Params(kwd)
        message = ''
        PageSpec = namedtuple('PageSpec', ['entries', 'offset', 'page', 'pages_found'])

        monitor_email = params.get('monitor_email', 'monitor@bx.psu.edu')
        specs = sorter('user_email', kwd)
        sort_id = specs.sort_id
        order = specs.order
        arrow = specs.arrow
        _order = specs.exc_order
        time_period = kwd.get('spark_time')
        time_period, _time_period = get_spark_time(time_period)
        spark_limit = 30
        offset = 0
        limit = 10

        if "entries" in kwd:
            entries = int(kwd.get('entries'))
        else:
            entries = 10
        limit = entries * 4

        if "offset" in kwd:
            offset = int(kwd.get('offset'))
        else:
            offset = 0

        if "page" in kwd:
            page = int(kwd.get('page'))
        else:
            page = 1

        jobs = []
        jobs_per_user = sa.select((model.User.table.c.email.label('user_email'),
                                   sa.func.count(model.Job.table.c.id).label('total_jobs')),
                                  from_obj=[sa.outerjoin(model.Job.table, model.User.table)],
                                  group_by=['user_email'],
                                  order_by=[_order],
                                  offset=offset,
                                  limit=limit)

        q_time.start()
        for row in jobs_per_user.execute():
            if (row.user_email is None):
                jobs.append(('Anonymous',
                             row.total_jobs))
            elif (row.user_email == monitor_email):
                continue
            else:
                jobs.append((row.user_email,
                             row.total_jobs))
        q_time.stop()
        query1time = q_time.time_elapsed()

        users = sa.select([model.User.table.c.email],
                          from_obj=[model.User.table])

        all_jobs_per_user = sa.select((model.Job.table.c.id.label('id'),
                                       model.Job.table.c.create_time.label('date'),
                                       model.User.table.c.email.label('user_email')),
                                      from_obj=[sa.outerjoin(model.Job.table, model.User.table)],
                                      whereclause=model.User.table.c.email.in_(users))

        currday = datetime.today()
        trends = dict()
        q_time.start()
        for job in all_jobs_per_user.execute():
            if job.user_email is None:
                curr_user = 'Anonymous'
            else:
                curr_user = re.sub(r'\W+', '', job.user_email)

            try:
                day = currday - job.date
            except TypeError:
                day = currday - datetime.date(job.date)

            day = day.days
            container = floor(day / _time_period)
            container = int(container)
            try:
                if container < spark_limit:
                    trends[curr_user][container] += 1
            except KeyError:
                trends[curr_user] = [0] * spark_limit
                if container < spark_limit:
                    trends[curr_user][container] += 1
        q_time.stop()
        query2time = q_time.time_elapsed()

        pages_found = ceil(len(jobs) / float(entries))
        page_specs = PageSpec(entries, offset, page, pages_found)

        total_time.stop()
        ttime = total_time.time_elapsed()
        return trans.fill_template('/webapps/reports/jobs_per_user.mako',
                                   order=order,
                                   arrow=arrow,
                                   sort_id=sort_id,
                                   spark_limit=spark_limit,
                                   time_period=time_period,
                                   q1time=query1time,
                                   q2time=query2time,
                                   ttime=ttime,
                                   trends=trends,
                                   jobs=jobs,
                                   message=message,
                                   page_specs=page_specs)

    @web.expose
    def user_per_month(self, trans, **kwd):
        params = util.Params(kwd)
        message = ''

        email = util.restore_text(params.get('email', ''))
        specs = sorter('date', kwd)
        sort_id = specs.sort_id
        order = specs.order
        arrow = specs.arrow
        _order = specs.exc_order

        q = sa.select((self.select_month(model.Job.table.c.create_time).label('date'),
                       sa.func.count(model.Job.table.c.id).label('total_jobs')),
                      whereclause=model.User.table.c.email == email,
                      from_obj=[sa.join(model.Job.table, model.User.table)],
                      group_by=self.group_by_month(model.Job.table.c.create_time),
                      order_by=[_order])

        all_jobs_per_user = sa.select((model.Job.table.c.create_time.label('date'),
                                       model.Job.table.c.id.label('job_id')),
                                      whereclause=sa.and_(model.User.table.c.email == email),
                                      from_obj=[sa.join(model.Job.table, model.User.table)])

        trends = dict()
        for job in all_jobs_per_user.execute():
            job_day = int(job.date.strftime("%-d")) - 1
            job_month = int(job.date.strftime("%-m"))
            job_month_name = job.date.strftime("%B")
            job_year = job.date.strftime("%Y")
            key = str(job_month_name + job_year)

            try:
                trends[key][job_day] += 1
            except KeyError:
                job_year = int(job_year)
                wday, day_range = calendar.monthrange(job_year, job_month)
                trends[key] = [0] * day_range
                trends[key][job_day] += 1

        jobs = []
        for row in q.execute():
            jobs.append((row.date.strftime("%Y-%m"),
                         row.total_jobs,
                         row.date.strftime("%B"),
                         row.date.strftime("%Y")))
        return trans.fill_template('/webapps/reports/jobs_user_per_month.mako',
                                   order=order,
                                   arrow=arrow,
                                   sort_id=sort_id,
                                   id=kwd.get('id'),
                                   trends=trends,
                                   email=util.sanitize_text(email),
                                   jobs=jobs, message=message)

    @web.expose
    def per_tool(self, trans, **kwd):
        message = ''
        PageSpec = namedtuple('PageSpec', ['entries', 'offset', 'page', 'pages_found'])

        params = util.Params(kwd)
        monitor_email = params.get('monitor_email', 'monitor@bx.psu.edu')
        specs = sorter('tool_id', kwd)
        sort_id = specs.sort_id
        order = specs.order
        arrow = specs.arrow
        _order = specs.exc_order
        time_period = kwd.get('spark_time')
        time_period, _time_period = get_spark_time(time_period)
        spark_limit = 30
        offset = 0
        limit = 10

        if "entries" in kwd:
            entries = int(kwd.get('entries'))
        else:
            entries = 10
        limit = entries * 4

        if "offset" in kwd:
            offset = int(kwd.get('offset'))
        else:
            offset = 0

        if "page" in kwd:
            page = int(kwd.get('page'))
        else:
            page = 1

        # In case we don't know which is the monitor user we will query for all jobs
        monitor_user_id = get_monitor_id(trans, monitor_email)

        jobs = []
        q = sa.select((model.Job.table.c.tool_id.label('tool_id'),
                       sa.func.count(model.Job.table.c.id).label('total_jobs')),
                      whereclause=model.Job.table.c.user_id != monitor_user_id,
                      from_obj=[model.Job.table],
                      group_by=['tool_id'],
                      order_by=[_order],
                      offset=offset,
                      limit=limit)

        all_jobs_per_tool = sa.select((model.Job.table.c.tool_id.label('tool_id'),
                                       model.Job.table.c.id.label('id'),
                                       self.select_day(model.Job.table.c.create_time).label('date')),
                                      whereclause=model.Job.table.c.user_id != monitor_user_id,
                                      from_obj=[model.Job.table])

        currday = date.today()
        trends = dict()
        for job in all_jobs_per_tool.execute():
            curr_tool = re.sub(r'\W+', '', str(job.tool_id))
            try:
                day = currday - job.date
            except TypeError:
                day = currday - datetime.date(job.date)

            day = day.days
            container = floor(day / _time_period)
            container = int(container)
            try:
                if container < spark_limit:
                    trends[curr_tool][container] += 1
            except KeyError:
                trends[curr_tool] = [0] * spark_limit
                if container < spark_limit:
                    trends[curr_tool][container] += 1

        for row in q.execute():
            jobs.append((row.tool_id,
                         row.total_jobs))

        pages_found = ceil(len(jobs) / float(entries))
        page_specs = PageSpec(entries, offset, page, pages_found)

        return trans.fill_template('/webapps/reports/jobs_per_tool.mako',
                                   order=order,
                                   arrow=arrow,
                                   sort_id=sort_id,
                                   spark_limit=spark_limit,
                                   time_period=time_period,
                                   trends=trends,
                                   jobs=jobs,
                                   message=message,
                                   is_user_jobs_only=monitor_user_id,
                                   page_specs=page_specs)

    @web.expose
    def errors_per_tool(self, trans, **kwd):
        """
        Queries the DB for user jobs in error. Filters out monitor jobs.
        """

        message = ''
        PageSpec = namedtuple('PageSpec', ['entries', 'offset', 'page', 'pages_found'])

        params = util.Params(kwd)
        monitor_email = params.get('monitor_email', 'monitor@bx.psu.edu')
        specs = sorter('tool_id', kwd)
        sort_id = specs.sort_id
        order = specs.order
        arrow = specs.arrow
        _order = specs.exc_order
        time_period = kwd.get('spark_time')
        time_period, _time_period = get_spark_time(time_period)
        spark_limit = 30
        offset = 0
        limit = 10

        if "entries" in kwd:
            entries = int(kwd.get('entries'))
        else:
            entries = 10
        limit = entries * 4

        if "offset" in kwd:
            offset = int(kwd.get('offset'))
        else:
            offset = 0

        if "page" in kwd:
            page = int(kwd.get('page'))
        else:
            page = 1

        # In case we don't know which is the monitor user we will query for all jobs
        monitor_user_id = get_monitor_id(trans, monitor_email)

        jobs_in_error_per_tool = sa.select((model.Job.table.c.tool_id.label('tool_id'),
                                            sa.func.count(model.Job.table.c.id).label('total_jobs')),
                                           whereclause=sa.and_(model.Job.table.c.state == 'error',
                                                               model.Job.table.c.user_id != monitor_user_id),
                                           from_obj=[model.Job.table],
                                           group_by=['tool_id'],
                                           order_by=[_order],
                                           offset=offset,
                                           limit=limit)

        all_jobs_per_tool_errors = sa.select((self.select_day(model.Job.table.c.create_time).label('date'),
                                              model.Job.table.c.id.label('id'),
                                              model.Job.table.c.tool_id.label('tool_id')),
                                             whereclause=sa.and_(model.Job.table.c.state == 'error',
                                                                 model.Job.table.c.user_id != monitor_user_id),
                                             from_obj=[model.Job.table])

        currday = date.today()
        trends = dict()
        for job in all_jobs_per_tool_errors.execute():
            curr_tool = re.sub(r'\W+', '', str(job.tool_id))
            try:
                day = currday - job.date
            except TypeError:
                day = currday - datetime.date(job.date)

            # convert day into days/weeks/months/years
            day = day.days
            container = floor(day / _time_period)
            container = int(container)
            try:
                if container < spark_limit:
                    trends[curr_tool][container] += 1
            except KeyError:
                trends[curr_tool] = [0] * spark_limit
                if day < spark_limit:
                    trends[curr_tool][container] += 1
        jobs = []
        for row in jobs_in_error_per_tool.execute():
            jobs.append((row.total_jobs, row.tool_id))

        pages_found = ceil(len(jobs) / float(entries))
        page_specs = PageSpec(entries, offset, page, pages_found)

        return trans.fill_template('/webapps/reports/jobs_errors_per_tool.mako',
                                   order=order,
                                   arrow=arrow,
                                   sort_id=sort_id,
                                   spark_limit=spark_limit,
                                   time_period=time_period,
                                   trends=trends,
                                   jobs=jobs,
                                   message=message,
                                   is_user_jobs_only=monitor_user_id,
                                   page_specs=page_specs)

    @web.expose
    def tool_per_month(self, trans, **kwd):
        message = ''

        params = util.Params(kwd)
        monitor_email = params.get('monitor_email', 'monitor@bx.psu.edu')
        specs = sorter('date', kwd)
        sort_id = specs.sort_id
        order = specs.order
        arrow = specs.arrow
        _order = specs.exc_order
        # In case we don't know which is the monitor user we will query for all jobs
        monitor_user_id = get_monitor_id(trans, monitor_email)

        tool_id = params.get('tool_id', 'Add a column1')
        specified_date = params.get('specified_date', datetime.utcnow().strftime("%Y-%m-%d"))
        q = sa.select((self.select_month(model.Job.table.c.create_time).label('date'),
                       sa.func.count(model.Job.table.c.id).label('total_jobs')),
                      whereclause=sa.and_(model.Job.table.c.tool_id == tool_id,
                                          model.Job.table.c.user_id != monitor_user_id),
                      from_obj=[model.Job.table],
                      group_by=self.group_by_month(model.Job.table.c.create_time),
                      order_by=[_order])

        # Use to make sparkline
        all_jobs_for_tool = sa.select((self.select_month(model.Job.table.c.create_time).label('month'),
                                       self.select_day(model.Job.table.c.create_time).label('day'),
                                       model.Job.table.c.id.label('id')),
                                      whereclause=sa.and_(model.Job.table.c.tool_id == tool_id,
                                                          model.Job.table.c.user_id != monitor_user_id),
                             from_obj=[model.Job.table])
        trends = dict()
        for job in all_jobs_for_tool.execute():
            job_day = int(job.day.strftime("%-d")) - 1
            job_month = int(job.month.strftime("%-m"))
            job_month_name = job.month.strftime("%B")
            job_year = job.month.strftime("%Y")
            key = str(job_month_name + job_year)

            try:
                trends[key][job_day] += 1
            except KeyError:
                job_year = int(job_year)
                wday, day_range = calendar.monthrange(job_year, job_month)
                trends[key] = [0] * day_range
                trends[key][job_day] += 1

        jobs = []
        for row in q.execute():
            jobs.append((row.date.strftime("%Y-%m"),
                         row.total_jobs,
                         row.date.strftime("%B"),
                         row.date.strftime("%Y")))
        return trans.fill_template('/webapps/reports/jobs_tool_per_month.mako',
                                   order=order,
                                   arrow=arrow,
                                   sort_id=sort_id,
                                   specified_date=specified_date,
                                   tool_id=tool_id,
                                   trends=trends,
                                   jobs=jobs,
                                   message=message,
                                   is_user_jobs_only=monitor_user_id)

    @web.expose
    def job_info(self, trans, **kwd):
        message = ''
        job = trans.sa_session.query(model.Job) \
                              .get(trans.security.decode_id(kwd.get('id', '')))
        return trans.fill_template('/webapps/reports/job_info.mako',
                                   job=job,
                                   message=message)

# ---- Utility methods -------------------------------------------------------


def get_job(trans, id):
    return trans.sa_session.query(trans.model.Job).get(trans.security.decode_id(id))


def get_monitor_id(trans, monitor_email):
    """
    A convenience method to obtain the monitor job id.
    """
    monitor_user_id = None
    monitor_row = trans.sa_session.query(trans.model.User.table.c.id) \
        .filter(trans.model.User.table.c.email == monitor_email) \
        .first()
    if monitor_row is not None:
        monitor_user_id = monitor_row[0]
    return monitor_user_id
