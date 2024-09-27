import calendar
import logging
import re
from collections import namedtuple
from datetime import (
    date,
    datetime,
    timedelta,
    timezone,
)
from math import (
    ceil,
    floor,
)

import sqlalchemy as sa
from markupsafe import escape
from sqlalchemy import (
    and_,
    not_,
    or_,
)

from galaxy import (
    model,
    util,
)
from galaxy.model import Job
from galaxy.model.db.user import get_user_by_email
from galaxy.web.legacy_framework import grids
from galaxy.webapps.base.controller import (
    BaseUIController,
    web,
)
from galaxy.webapps.reports.controllers.query import ReportQueryBuilder

log = logging.getLogger(__name__)


class Timer:
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
            del self.stop_time
            del self.start_time
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
    SortSpec = namedtuple("SortSpec", ["sort_id", "order", "arrow", "exc_order"])

    sort_id = kwd.get("sort_id")
    order = kwd.get("order")

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


def get_curr_item(check_item, unique_items):
    """
    When rendering by item and destination_id,
    render the item uniquely.
    """
    if check_item in unique_items:
        return ("", unique_items)
    unique_items.add(check_item)
    return (check_item, unique_items)


class SpecifiedDateListGrid(grids.Grid):
    class JobIdColumn(grids.IntegerColumn):
        def get_value(self, trans, grid, job):
            return job.id

    class StateColumn(grids.TextColumn):
        def get_value(self, trans, grid, job):
            return f'<div class="count-box state-color-{job.state}">{job.state}</div>'

        def filter(self, trans, user, query, column_filter):
            if column_filter == "Unfinished":
                return query.filter(
                    not_(
                        or_(
                            model.Job.table.c.state == model.Job.states.OK,
                            model.Job.table.c.state == model.Job.states.ERROR,
                            model.Job.table.c.state == model.Job.states.DELETED,
                        )
                    )
                )
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
                return escape(job.get_user_email())
            return "anonymous"

    class EmailColumn(grids.GridColumn):
        def filter(self, trans, user, query, column_filter):
            if column_filter == "All":
                return query
            return query.filter(
                and_(model.Job.table.c.user_id == model.User.table.c.id, model.User.table.c.email == column_filter)
            )

    class DestinationIdColumn(grids.GridColumn):
        def filter(self, trans, user, query, column_filter):
            if column_filter == "All":
                return query
            return query.filter(model.Job.table.c.destination_id == column_filter)

    class SpecifiedDateColumn(grids.GridColumn):
        def filter(self, trans, user, query, column_filter):
            if column_filter == "All":
                return query
            # We are either filtering on a date like YYYY-MM-DD or on a month like YYYY-MM,
            # so we need to figure out which type of date we have
            if column_filter.count("-") == 2:  # We are filtering on a date like YYYY-MM-DD
                year, month, day = map(int, column_filter.split("-"))
                start_date = date(year, month, day)
                end_date = start_date + timedelta(days=1)
            if column_filter.count("-") == 1:  # We are filtering on a month like YYYY-MM
                year, month = map(int, column_filter.split("-"))
                start_date = date(year, month, 1)
                end_date = start_date + timedelta(days=calendar.monthrange(year, month)[1])

            return query.filter(
                and_(
                    self.model_class.table.c.create_time >= start_date, self.model_class.table.c.create_time < end_date
                )
            )

    # Grid definition
    use_async = False
    model_class = model.Job
    title = "Jobs"
    default_sort_key = "id"
    columns = [
        JobIdColumn(
            "Id",
            key="id",
            link=(lambda item: dict(operation="job_info", id=item.id, webapp="reports")),
            attach_popup=False,
            filterable="advanced",
        ),
        StateColumn("State", key="state", attach_popup=False),
        DestinationIdColumn("Destination Id", key="destination_id", attach_popup=False),
        ToolColumn(
            "Tool Id",
            key="tool_id",
            link=(lambda item: dict(operation="tool_per_month", id=item.id, webapp="reports")),
            attach_popup=False,
        ),
        CreateTimeColumn("Creation Time", key="create_time", attach_popup=False),
        UserColumn(
            "User",
            key="email",
            model_class=model.User,
            link=(lambda item: dict(operation="user_per_month", id=item.id, webapp="reports")),
            attach_popup=False,
        ),
        # Columns that are valid for filtering but are not visible.
        SpecifiedDateColumn("Specified Date", key="specified_date", visible=False),
        EmailColumn("Email", key="email", model_class=model.User, visible=False),
        grids.StateColumn("State", key="state", visible=False, filterable="advanced"),
    ]
    columns.append(
        grids.MulticolFilterColumn(
            "Search",
            cols_to_filter=[columns[1], columns[2]],
            key="free-text-search",
            visible=False,
            filterable="standard",
        )
    )
    default_filter = {"specified_date": "All"}
    num_rows_per_page = 50
    use_paging = True

    def build_initial_query(self, trans, **kwd):
        params = util.Params(kwd)
        monitor_email = params.get("monitor_email", "monitor@bx.psu.edu")
        monitor_user_id = get_monitor_id(trans, monitor_email)
        return (
            trans.sa_session.query(self.model_class)
            .join(model.User)
            .filter(model.Job.table.c.user_id != monitor_user_id)
            .enable_eagerloads(False)
        )


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
        kwd["sort_id"] = "default"
        kwd["order"] = "default"

        if "f-specified_date" in kwd and "specified_date" not in kwd:
            # The user clicked a State link in the Advanced Search box, so 'specified_date'
            # will have been eliminated.
            pass
        elif "specified_date" not in kwd:
            kwd["f-specified_date"] = "All"
        else:
            kwd["f-specified_date"] = kwd["specified_date"]
        if "operation" in kwd:
            operation = kwd["operation"].lower()
            if operation == "job_info":
                return trans.response.send_redirect(web.url_for(controller="jobs", action="job_info", **kwd))
            elif operation == "tool_for_month":
                kwd["f-tool_id"] = kwd["tool_id"]
            elif operation == "tool_per_month":
                # The received id is the job id, so we need to get the job's tool_id.
                job_id = kwd.get("id", None)
                job = get_job(trans, job_id)
                kwd["tool_id"] = job.tool_id
                return trans.response.send_redirect(web.url_for(controller="jobs", action="tool_per_month", **kwd))
            elif operation == "user_for_month":
                kwd["f-email"] = util.restore_text(kwd["email"])
            elif operation == "user_for_month_by_destination":
                kwd["f-email"] = util.restore_text(kwd["email"])
                kwd["f-destination_id"] = kwd["destination_id"]
            elif operation == "user_per_month":
                # The received id is the job id, so we need to get the id of the user
                # that submitted the job.
                job_id = kwd.get("id", None)
                job = get_job(trans, job_id)
                kwd["email"] = job.get_user_email()
                return trans.response.send_redirect(web.url_for(controller="jobs", action="user_per_month", **kwd))
            elif operation == "specified_date_in_error":
                kwd["f-state"] = "error"
            elif operation == "unfinished":
                kwd["f-state"] = "Unfinished"
            elif operation == "specified_tool_in_error":
                kwd["f-state"] = "error"
                kwd["f-tool_id"] = kwd["tool_id"]
        return self.specified_date_list_grid(trans, **kwd)

    def _calculate_trends_for_jobs(self, sa_session, jobs_query):
        trends = {}
        for job in sa_session.execute(jobs_query):
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

    def _calculate_job_table(self, sa_session, jobs_query, by_destination=False):
        jobs = []
        unique_month_year_strs = set()
        for row in sa_session.execute(jobs_query):
            month_name = row.date.strftime("%B")
            year = int(row.date.strftime("%Y"))

            if str(by_destination).lower() == "true":
                month_year_str = f"{month_name} {year}"
                curr_month_year_str, unique_month_year_strs = get_curr_item(month_year_str, unique_month_year_strs)
                if curr_month_year_str == "":
                    curr_month = ""
                    curr_year = ""
                else:
                    curr_month = row.date.strftime("%B")
                    curr_year = row.date.strftime("%Y")
                jobs.append(
                    (
                        row.date.strftime("%Y-%m"),
                        row.total_jobs,
                        curr_month,
                        curr_year,
                        row.user_email,
                        row.destination_id,
                        row.execute_time,
                    )
                )
            else:
                jobs.append((row.date.strftime("%Y-%m"), row.total_jobs, month_name, year))
        return jobs

    @web.expose
    def specified_month_all(self, trans, **kwd):
        """
        Queries the DB for all jobs in given month, defaults to current month.
        """
        message = ""
        PageSpec = namedtuple("PageSpec", ["entries", "offset", "page", "pages_found"])

        params = util.Params(kwd)
        monitor_email = params.get("monitor_email", "monitor@bx.psu.edu")
        specs = sorter("date", kwd)
        offset = 0
        limit = 10
        sort_id = specs.sort_id
        order = specs.order
        arrow = specs.arrow

        if "entries" in kwd:
            entries = int(kwd.get("entries"))
        else:
            entries = 10
        limit = entries * 4

        if "offset" in kwd:
            offset = int(kwd.get("offset"))
        else:
            offset = 0

        if "page" in kwd:
            page = int(kwd.get("page"))
        else:
            page = 1

        # In case we don't know which is the monitor user we will query for all jobs
        monitor_user_id = get_monitor_id(trans, monitor_email)

        # If specified_date is not received, we'll default to the current month
        specified_date = kwd.get("specified_date", datetime.now(tz=timezone.utc).strftime("%Y-%m-%d"))
        specified_month = specified_date[:7]

        year, month = map(int, specified_month.split("-"))
        start_date = date(year, month, 1)
        end_date = start_date + timedelta(days=calendar.monthrange(year, month)[1])
        month_label = start_date.strftime("%B")
        year_label = start_date.strftime("%Y")

        # Use to make the page table
        month_jobs = (
            sa.select(
                sa.func.date(model.Job.table.c.create_time).label("date"),
                sa.func.count(model.Job.table.c.id).label("total_jobs"),
            )
            .where(
                sa.and_(
                    model.Job.table.c.user_id != monitor_user_id,
                    model.Job.table.c.create_time >= start_date,
                    model.Job.table.c.create_time < end_date,
                )
            )
            .group_by("date")
            .order_by(specs.exc_order)
            .offset(offset)
            .limit(limit)
        )

        # Use to make trendline
        all_jobs = sa.select(model.Job.table.c.create_time.label("date"), model.Job.table.c.id.label("id")).where(
            sa.and_(
                model.Job.table.c.user_id != monitor_user_id,
                model.Job.table.c.create_time >= start_date,
                model.Job.table.c.create_time < end_date,
            )
        )

        trends = {}
        for job in trans.sa_session.execute(all_jobs):
            job_hour = int(job.date.strftime("%-H"))
            job_day = job.date.strftime("%d")

            try:
                trends[job_day][job_hour] += 1
            except KeyError:
                trends[job_day] = [0] * 24
                trends[job_day][job_hour] += 1

        jobs = []
        for row in trans.sa_session.execute(month_jobs):
            row_dayname = row.date.strftime("%A")
            row_day = row.date.strftime("%d")

            jobs.append((row_dayname, row_day, row.total_jobs, row.date))

        pages_found = ceil(len(jobs) / float(entries))
        page_specs = PageSpec(entries, offset, page, pages_found)

        return trans.fill_template(
            "/webapps/reports/jobs_specified_month_all.mako",
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
            message=message,
        )

    @web.expose
    def specified_month_in_error(self, trans, **kwd):
        """
        Queries the DB for the user jobs in error.
        """
        message = ""
        PageSpec = namedtuple("PageSpec", ["entries", "offset", "page", "pages_found"])

        params = util.Params(kwd)
        monitor_email = params.get("monitor_email", "monitor@bx.psu.edu")
        specs = sorter("date", kwd)
        sort_id = specs.sort_id
        order = specs.order
        arrow = specs.arrow
        offset = 0
        limit = 10

        if "entries" in kwd:
            entries = int(kwd.get("entries"))
        else:
            entries = 10
        limit = entries * 4

        if "offset" in kwd:
            offset = int(kwd.get("offset"))
        else:
            offset = 0

        if "page" in kwd:
            page = int(kwd.get("page"))
        else:
            page = 1

        # In case we don't know which is the monitor user we will query for all jobs instead
        monitor_user_id = get_monitor_id(trans, monitor_email)

        # If specified_date is not received, we'll default to the current month
        specified_date = kwd.get("specified_date", datetime.now(tz=timezone.utc).strftime("%Y-%m-%d"))
        specified_month = specified_date[:7]
        year, month = map(int, specified_month.split("-"))
        start_date = date(year, month, 1)
        end_date = start_date + timedelta(days=calendar.monthrange(year, month)[1])
        month_label = start_date.strftime("%B")
        year_label = start_date.strftime("%Y")

        month_jobs_in_error = (
            sa.select(
                sa.func.date(model.Job.table.c.create_time).label("date"),
                sa.func.count(model.Job.table.c.id).label("total_jobs"),
            )
            .where(
                sa.and_(
                    model.Job.table.c.user_id != monitor_user_id,
                    model.Job.table.c.state == "error",
                    model.Job.table.c.create_time >= start_date,
                    model.Job.table.c.create_time < end_date,
                )
            )
            .group_by("date")
            .order_by(specs.exc_order)
            .offset(offset)
            .limit(limit)
        )

        # Use to make trendline
        all_jobs_in_error = sa.select(
            model.Job.table.c.create_time.label("date"), model.Job.table.c.id.label("id")
        ).where(
            sa.and_(
                model.Job.table.c.user_id != monitor_user_id,
                model.Job.table.c.state == "error",
                model.Job.table.c.create_time >= start_date,
                model.Job.table.c.create_time < end_date,
            )
        )

        trends = {}
        for job in trans.sa_session.execute(all_jobs_in_error):
            job_hour = int(job.date.strftime("%-H"))
            job_day = job.date.strftime("%d")

            try:
                trends[job_day][job_hour] += 1
            except KeyError:
                trends[job_day] = [0] * 24
                trends[job_day][job_hour] += 1

        jobs = []
        for row in trans.sa_session.execute(month_jobs_in_error):
            row_dayname = row.date.strftime("%A")
            row_day = row.date.strftime("%d")

            jobs.append((row_dayname, row_day, row.total_jobs, row.date))

        pages_found = ceil(len(jobs) / float(entries))
        page_specs = PageSpec(entries, offset, page, pages_found)

        return trans.fill_template(
            "/webapps/reports/jobs_specified_month_in_error.mako",
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
            page_specs=page_specs,
        )

    @web.expose
    def per_month_all(self, trans, **kwd):
        """
        Queries the DB for all jobs. Avoids monitor jobs.  The
        by_destination param will group by User.email and
        Job.destination_id.
        """
        by_destination = str(kwd.get("by_destination", False)).lower()
        message = ""
        PageSpec = namedtuple("PageSpec", ["entries", "offset", "page", "pages_found"])

        params = util.Params(kwd)
        monitor_email = params.get("monitor_email", "monitor@bx.psu.edu")
        specs = sorter("date", kwd)
        sort_id = specs.sort_id
        order = specs.order
        arrow = specs.arrow
        _order = specs.exc_order
        offset = 0
        limit = 10

        if "entries" in kwd:
            entries = int(kwd.get("entries"))
        else:
            entries = 10
        limit = entries * 4

        if "offset" in kwd:
            offset = int(kwd.get("offset"))
        else:
            offset = 0

        if "page" in kwd:
            page = int(kwd.get("page"))
        else:
            page = 1

        # In case we don't know which is the monitor user we will query for all jobs
        monitor_user_id = get_monitor_id(trans, monitor_email)

        # Use to make the page table
        if by_destination == "true":
            jobs_by_month = (
                sa.select(
                    self.select_month(model.Job.table.c.create_time).label("date"),
                    model.Job.table.c.destination_id.label("destination_id"),
                    sa.func.sum(model.Job.table.c.update_time - model.Job.table.c.create_time).label("execute_time"),
                    sa.func.count(model.Job.table.c.id).label("total_jobs"),
                    model.User.table.c.email.label("user_email"),
                )
                .where(model.Job.table.c.user_id != monitor_user_id)
                .select_from(sa.join(model.Job.table, model.User.table))
                .group_by("user_email", "date", "destination_id")
                .order_by(_order)
                .offset(offset)
                .limit(limit)
            )
        else:
            jobs_by_month = (
                sa.select(
                    self.select_month(model.Job.table.c.create_time).label("date"),
                    sa.func.count(model.Job.table.c.id).label("total_jobs"),
                )
                .where(model.Job.table.c.user_id != monitor_user_id)
                .group_by(self.group_by_month(model.Job.table.c.create_time))
                .order_by(_order)
                .offset(offset)
                .limit(limit)
            )

        # Use to make sparkline
        all_jobs = sa.select(
            self.select_day(model.Job.table.c.create_time).label("date"), model.Job.table.c.id.label("id")
        )

        trends = self._calculate_trends_for_jobs(trans.sa_session, all_jobs)
        jobs = self._calculate_job_table(trans.sa_session, jobs_by_month, by_destination=by_destination)

        pages_found = ceil(len(jobs) / float(entries))
        page_specs = PageSpec(entries, offset, page, pages_found)

        if by_destination == "true":
            page = "/webapps/reports/jobs_per_month_by_user_and_destination.mako"
        else:
            page = "/webapps/reports/jobs_per_month_all.mako"
        return trans.fill_template(
            page,
            order=order,
            arrow=arrow,
            sort_id=sort_id,
            trends=trends,
            jobs=jobs,
            is_user_jobs_only=monitor_user_id,
            message=message,
            page_specs=page_specs,
        )

    @web.expose
    def per_month_in_error(self, trans, **kwd):
        """
        Queries the DB for user jobs in error. Filters out monitor jobs.
        """

        message = ""
        PageSpec = namedtuple("PageSpec", ["entries", "offset", "page", "pages_found"])

        params = util.Params(kwd)
        monitor_email = params.get("monitor_email", "monitor@bx.psu.edu")
        specs = sorter("date", kwd)
        sort_id = specs.sort_id
        order = specs.order
        arrow = specs.arrow
        _order = specs.exc_order
        offset = 0
        limit = 10

        if "entries" in kwd:
            entries = int(kwd.get("entries"))
        else:
            entries = 10
        limit = entries * 4

        if "offset" in kwd:
            offset = int(kwd.get("offset"))
        else:
            offset = 0

        if "page" in kwd:
            page = int(kwd.get("page"))
        else:
            page = 1

        # In case we don't know which is the monitor user we will query for all jobs
        monitor_user_id = get_monitor_id(trans, monitor_email)

        # Use to make the page table
        jobs_in_error_by_month = (
            sa.select(
                self.select_month(model.Job.table.c.create_time).label("date"),
                sa.func.count(model.Job.table.c.id).label("total_jobs"),
            )
            .where(sa.and_(model.Job.table.c.state == "error", model.Job.table.c.user_id != monitor_user_id))
            .group_by(self.group_by_month(model.Job.table.c.create_time))
            .order_by(_order)
            .offset(offset)
            .limit(limit)
        )

        # Use to make trendline
        all_jobs = sa.select(
            self.select_day(model.Job.table.c.create_time).label("date"), model.Job.table.c.id.label("id")
        ).where(sa.and_(model.Job.table.c.state == "error", model.Job.table.c.user_id != monitor_user_id))

        trends = self._calculate_trends_for_jobs(trans.sa_session, all_jobs)
        jobs = self._calculate_job_table(trans.sa_session, jobs_in_error_by_month)

        pages_found = ceil(len(jobs) / float(entries))
        page_specs = PageSpec(entries, offset, page, pages_found)

        return trans.fill_template(
            "/webapps/reports/jobs_per_month_in_error.mako",
            order=order,
            arrow=arrow,
            sort_id=sort_id,
            trends=trends,
            jobs=jobs,
            message=message,
            is_user_jobs_only=monitor_user_id,
            page_specs=page_specs,
            offset=offset,
            limit=limit,
        )

    @web.expose
    def per_user(self, trans, **kwd):
        """
        Queries the DB for jobs per user.  The by_destination
        param will group by Job.destination_id.
        """
        by_destination = str(kwd.get("by_destination", False)).lower()
        total_time = Timer()
        q_time = Timer()

        total_time.start()
        params = util.Params(kwd)
        message = ""
        PageSpec = namedtuple("PageSpec", ["entries", "offset", "page", "pages_found"])

        monitor_email = params.get("monitor_email", "monitor@bx.psu.edu")
        specs = sorter("user_email", kwd)
        sort_id = specs.sort_id
        order = specs.order
        arrow = specs.arrow
        _order = specs.exc_order
        time_period = kwd.get("spark_time")
        time_period, _time_period = get_spark_time(time_period)
        spark_limit = 30
        offset = 0
        limit = 10

        if "entries" in kwd:
            entries = int(kwd.get("entries"))
        else:
            entries = 10
        limit = entries * 4

        if "offset" in kwd:
            offset = int(kwd.get("offset"))
        else:
            offset = 0

        if "page" in kwd:
            page = int(kwd.get("page"))
        else:
            page = 1

        jobs = []
        if by_destination == "true":
            jobs_per_user = (
                sa.select(
                    model.User.table.c.email.label("user_email"),
                    sa.func.count(model.Job.table.c.id).label("total_jobs"),
                    model.Job.table.c.destination_id.label("destination_id"),
                )
                .select_from(sa.outerjoin(model.Job.table, model.User.table))
                .group_by("user_email", "destination_id")
                .order_by(_order)
                .offset(offset)
                .limit(limit)
            )

        else:
            jobs_per_user = (
                sa.select(
                    model.User.table.c.email.label("user_email"),
                    sa.func.count(model.Job.table.c.id).label("total_jobs"),
                )
                .select_from(sa.outerjoin(model.Job.table, model.User.table))
                .group_by("user_email")
                .order_by(_order)
                .offset(offset)
                .limit(limit)
            )

        q_time.start()
        unique_users = set()
        for row in trans.sa_session.execute(jobs_per_user):
            if row.user_email is None:
                curr_user, unique_users = get_curr_item("Anonymous", unique_users)
                if by_destination == "true":
                    jobs.append((curr_user, row.destination_id, row.total_jobs))
                else:
                    jobs.append((curr_user, row.total_jobs))
            elif row.user_email == monitor_email:
                continue
            else:
                curr_user, unique_users = get_curr_item(row.user_email, unique_users)
                if by_destination == "true":
                    jobs.append((curr_user, row.destination_id, row.total_jobs))
                else:
                    jobs.append((curr_user, row.total_jobs))
        q_time.stop()
        query1time = q_time.time_elapsed()

        users = sa.select(model.User.table.c.email).select_from(model.User.table)

        all_jobs_per_user = (
            sa.select(
                model.Job.table.c.id.label("id"),
                model.Job.table.c.create_time.label("date"),
                model.User.table.c.email.label("user_email"),
            )
            .select_from(sa.outerjoin(model.Job.table, model.User.table))
            .where(model.User.table.c.email.in_(users))
        )

        currday = datetime.today()
        trends = {}
        q_time.start()
        for job in trans.sa_session.execute(all_jobs_per_user):
            if job.user_email is None:
                curr_user = "Anonymous"
            else:
                curr_user = re.sub(r"\W+", "", job.user_email)

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
        if by_destination == "true":
            page = "/webapps/reports/jobs_per_user_by_destination.mako"
        else:
            page = "/webapps/reports/jobs_per_user.mako"
        return trans.fill_template(
            page,
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
            page_specs=page_specs,
        )

    @web.expose
    def user_per_month(self, trans, **kwd):
        """
        Queries the DB for jobs per user per month.  The
        by_destination param will group by Job.destination_id.
        """
        by_destination = str(kwd.get("by_destination", False)).lower()
        params = util.Params(kwd)
        message = ""

        email = util.restore_text(params.get("email", ""))
        specs = sorter("date", kwd)
        sort_id = specs.sort_id
        order = specs.order
        arrow = specs.arrow
        _order = specs.exc_order

        if by_destination == "true":
            q = (
                sa.select(
                    self.select_month(model.Job.table.c.create_time).label("date"),
                    model.Job.table.c.destination_id.label("destination_id"),
                    sa.func.sum(model.Job.table.c.update_time - model.Job.table.c.create_time).label("execute_time"),
                    sa.func.count(model.Job.table.c.id).label("total_jobs"),
                )
                .where(model.User.table.c.email == email)
                .select_from(sa.join(model.Job.table, model.User.table))
                .group_by("date", "destination_id")
                .order_by(_order)
            )
        else:
            q = (
                sa.select(
                    self.select_month(model.Job.table.c.create_time).label("date"),
                    sa.func.count(model.Job.table.c.id).label("total_jobs"),
                )
                .where(model.User.table.c.email == email)
                .select_from(sa.join(model.Job.table, model.User.table))
                .group_by(self.group_by_month(model.Job.table.c.create_time))
                .order_by(_order)
            )

        all_jobs_per_user = (
            sa.select(model.Job.table.c.create_time.label("date"), model.Job.table.c.id.label("job_id"))
            .where(sa.and_(model.User.table.c.email == email))
            .select_from(sa.join(model.Job.table, model.User.table))
        )

        trends = {}
        for job in trans.sa_session.execute(all_jobs_per_user):
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
        unique_month_year_strs = set()
        for row in trans.sa_session.execute(q):
            if by_destination == "true":
                month_year_str = f"{row.date.strftime('%B')} {row.date.strftime('%Y')}"
                curr_month_year_str, unique_month_year_strs = get_curr_item(month_year_str, unique_month_year_strs)
                if curr_month_year_str == "":
                    curr_month = ""
                    curr_year = ""
                else:
                    curr_month = row.date.strftime("%B")
                    curr_year = row.date.strftime("%Y")
                jobs.append(
                    (
                        row.date.strftime("%Y-%m"),
                        row.execute_time,
                        row.total_jobs,
                        curr_month,
                        curr_year,
                        row.destination_id,
                    )
                )
            else:
                jobs.append(
                    (row.date.strftime("%Y-%m"), row.total_jobs, row.date.strftime("%B"), row.date.strftime("%Y"))
                )
        if by_destination == "true":
            page = "/webapps/reports/jobs_user_per_month_by_destination.mako"
        else:
            page = "/webapps/reports/jobs_user_per_month.mako"
        return trans.fill_template(
            page,
            order=order,
            arrow=arrow,
            sort_id=sort_id,
            id=kwd.get("id"),
            trends=trends,
            email=util.sanitize_text(email),
            jobs=jobs,
            message=message,
        )

    @web.expose
    def per_tool(self, trans, **kwd):
        message = ""
        PageSpec = namedtuple("PageSpec", ["entries", "offset", "page", "pages_found"])

        params = util.Params(kwd)
        monitor_email = params.get("monitor_email", "monitor@bx.psu.edu")
        specs = sorter("tool_id", kwd)
        sort_id = specs.sort_id
        order = specs.order
        arrow = specs.arrow
        _order = specs.exc_order
        time_period = kwd.get("spark_time")
        time_period, _time_period = get_spark_time(time_period)
        spark_limit = 30
        offset = 0
        limit = 10

        if "entries" in kwd:
            entries = int(kwd.get("entries"))
        else:
            entries = 10
        limit = entries * 4

        if "offset" in kwd:
            offset = int(kwd.get("offset"))
        else:
            offset = 0

        if "page" in kwd:
            page = int(kwd.get("page"))
        else:
            page = 1

        # In case we don't know which is the monitor user we will query for all jobs
        monitor_user_id = get_monitor_id(trans, monitor_email)

        jobs = []
        q = (
            sa.select(
                model.Job.table.c.tool_id.label("tool_id"), sa.func.count(model.Job.table.c.id).label("total_jobs")
            )
            .where(model.Job.table.c.user_id != monitor_user_id)
            .group_by("tool_id")
            .order_by(_order)
            .offset(offset)
            .limit(limit)
        )

        all_jobs_per_tool = sa.select(
            model.Job.table.c.tool_id.label("tool_id"),
            model.Job.table.c.id.label("id"),
            self.select_day(model.Job.table.c.create_time).label("date"),
        ).where(model.Job.table.c.user_id != monitor_user_id)

        currday = date.today()
        trends = {}
        for job in trans.sa_session.execute(all_jobs_per_tool):
            curr_tool = re.sub(r"\W+", "", str(job.tool_id))
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

        for row in trans.sa_session.execute(q):
            jobs.append((row.tool_id, row.total_jobs))

        pages_found = ceil(len(jobs) / float(entries))
        page_specs = PageSpec(entries, offset, page, pages_found)

        return trans.fill_template(
            "/webapps/reports/jobs_per_tool.mako",
            order=order,
            arrow=arrow,
            sort_id=sort_id,
            spark_limit=spark_limit,
            time_period=time_period,
            trends=trends,
            jobs=jobs,
            message=message,
            is_user_jobs_only=monitor_user_id,
            page_specs=page_specs,
        )

    @web.expose
    def errors_per_tool(self, trans, **kwd):
        """
        Queries the DB for user jobs in error. Filters out monitor jobs.
        """

        message = ""
        PageSpec = namedtuple("PageSpec", ["entries", "offset", "page", "pages_found"])

        params = util.Params(kwd)
        monitor_email = params.get("monitor_email", "monitor@bx.psu.edu")
        specs = sorter("tool_id", kwd)
        sort_id = specs.sort_id
        order = specs.order
        arrow = specs.arrow
        _order = specs.exc_order
        time_period = kwd.get("spark_time")
        time_period, _time_period = get_spark_time(time_period)
        spark_limit = 30
        offset = 0
        limit = 10

        if "entries" in kwd:
            entries = int(kwd.get("entries"))
        else:
            entries = 10
        limit = entries * 4

        if "offset" in kwd:
            offset = int(kwd.get("offset"))
        else:
            offset = 0

        if "page" in kwd:
            page = int(kwd.get("page"))
        else:
            page = 1

        # In case we don't know which is the monitor user we will query for all jobs
        monitor_user_id = get_monitor_id(trans, monitor_email)

        jobs_in_error_per_tool = (
            sa.select(
                model.Job.table.c.tool_id.label("tool_id"), sa.func.count(model.Job.table.c.id).label("total_jobs")
            )
            .where(sa.and_(model.Job.table.c.state == "error", model.Job.table.c.user_id != monitor_user_id))
            .group_by("tool_id")
            .order_by(_order)
            .offset(offset)
            .limit(limit)
        )

        all_jobs_per_tool_errors = sa.select(
            self.select_day(model.Job.table.c.create_time).label("date"),
            model.Job.table.c.id.label("id"),
            model.Job.table.c.tool_id.label("tool_id"),
        ).where(sa.and_(model.Job.table.c.state == "error", model.Job.table.c.user_id != monitor_user_id))

        currday = date.today()
        trends = {}
        for job in trans.sa_session.execute(all_jobs_per_tool_errors):
            curr_tool = re.sub(r"\W+", "", str(job.tool_id))
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
        for row in trans.sa_session.execute(jobs_in_error_per_tool):
            jobs.append((row.total_jobs, row.tool_id))

        pages_found = ceil(len(jobs) / float(entries))
        page_specs = PageSpec(entries, offset, page, pages_found)

        return trans.fill_template(
            "/webapps/reports/jobs_errors_per_tool.mako",
            order=order,
            arrow=arrow,
            sort_id=sort_id,
            spark_limit=spark_limit,
            time_period=time_period,
            trends=trends,
            jobs=jobs,
            message=message,
            is_user_jobs_only=monitor_user_id,
            page_specs=page_specs,
        )

    @web.expose
    def tool_per_month(self, trans, **kwd):
        message = ""

        params = util.Params(kwd)
        monitor_email = params.get("monitor_email", "monitor@bx.psu.edu")
        specs = sorter("date", kwd)
        sort_id = specs.sort_id
        order = specs.order
        arrow = specs.arrow
        _order = specs.exc_order
        # In case we don't know which is the monitor user we will query for all jobs
        monitor_user_id = get_monitor_id(trans, monitor_email)

        tool_id = params.get("tool_id", "Add a column1")
        specified_date = params.get("specified_date", datetime.now(tz=timezone.utc).strftime("%Y-%m-%d"))
        q = (
            sa.select(
                self.select_month(model.Job.table.c.create_time).label("date"),
                sa.func.count(model.Job.table.c.id).label("total_jobs"),
            )
            .where(sa.and_(model.Job.table.c.tool_id == tool_id, model.Job.table.c.user_id != monitor_user_id))
            .group_by(self.group_by_month(model.Job.table.c.create_time))
            .order_by(_order)
        )

        # Use to make sparkline
        all_jobs_for_tool = sa.select(
            self.select_month(model.Job.table.c.create_time).label("month"),
            self.select_day(model.Job.table.c.create_time).label("day"),
            model.Job.table.c.id.label("id"),
        ).where(sa.and_(model.Job.table.c.tool_id == tool_id, model.Job.table.c.user_id != monitor_user_id))
        trends = {}
        for job in trans.sa_session.execute(all_jobs_for_tool):
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
        for row in trans.sa_session.execute(q):
            jobs.append((row.date.strftime("%Y-%m"), row.total_jobs, row.date.strftime("%B"), row.date.strftime("%Y")))
        return trans.fill_template(
            "/webapps/reports/jobs_tool_per_month.mako",
            order=order,
            arrow=arrow,
            sort_id=sort_id,
            specified_date=specified_date,
            tool_id=tool_id,
            trends=trends,
            jobs=jobs,
            message=message,
            is_user_jobs_only=monitor_user_id,
        )

    @web.expose
    def job_info(self, trans, **kwd):
        message = ""
        job = trans.sa_session.get(Job, trans.security.decode_id(kwd.get("id", "")))
        return trans.fill_template("/webapps/reports/job_info.mako", job=job, message=message)


# ---- Utility methods -------------------------------------------------------


def get_job(trans, id):
    return trans.sa_session.get(Job, trans.security.decode_id(id))


def get_monitor_id(trans, monitor_email):
    """
    A convenience method to obtain the monitor job id.
    """
    monitor_user_id = None
    if (monitor_row := get_user_by_email(trans.sa_session, monitor_email)) is not None:
        monitor_user_id = monitor_row[0]
    return monitor_user_id
