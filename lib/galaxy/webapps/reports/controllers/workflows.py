import calendar
import logging
import re
from collections import namedtuple
from datetime import (
    date,
    datetime,
    timedelta
)
from math import (
    ceil,
    floor
)

import sqlalchemy as sa
from markupsafe import escape
from sqlalchemy import and_

from galaxy import model, util
from galaxy.web.base.controller import BaseUIController, web
from galaxy.webapps.reports.controllers.jobs import (
    get_spark_time,
    sorter
)
from galaxy.webapps.reports.controllers.query import ReportQueryBuilder
from galaxy.webapps.reports.framework import grids

log = logging.getLogger(__name__)


class SpecifiedDateListGrid(grids.Grid):

    class WorkflowNameColumn(grids.TextColumn):

        def get_value(self, trans, grid, stored_workflow):
            return escape(stored_workflow.name)

    class CreateTimeColumn(grids.DateTimeColumn):

        def get_value(self, trans, grid, stored_workflow):
            return stored_workflow.create_time

    class UserColumn(grids.TextColumn):

        def get_value(self, trans, grid, stored_workflow):
            if stored_workflow.user:
                return escape(stored_workflow.user.email)
            return 'unknown'

    class EmailColumn(grids.GridColumn):

        def filter(self, trans, user, query, column_filter):
            if column_filter == 'All':
                return query
            return query.filter(and_(model.StoredWorkflow.table.c.user_id == model.User.table.c.id,
                                     model.User.table.c.email == column_filter))

    class SpecifiedDateColumn(grids.GridColumn):

        def filter(self, trans, user, query, column_filter):
            if column_filter == 'All':
                return query
            # We are either filtering on a date like YYYY-MM-DD or on a month like YYYY-MM,
            # so we need to figure out which type of date we have
            if column_filter.count('-') == 2:
                # We are filtering on a date like YYYY-MM-DD
                year, month, day = map(int, column_filter.split("-"))
                start_date = date(year, month, day)
                end_date = start_date + timedelta(days=1)
                return query.filter(and_(self.model_class.table.c.create_time >= start_date,
                                         self.model_class.table.c.create_time < end_date))
            if column_filter.count('-') == 1:
                # We are filtering on a month like YYYY-MM
                year, month = map(int, column_filter.split("-"))
                start_date = date(year, month, 1)
                end_date = start_date + timedelta(days=calendar.monthrange(year, month)[1])
                return query.filter(and_(self.model_class.table.c.create_time >= start_date,
                                         self.model_class.table.c.create_time < end_date))

    # Grid definition
    use_async = False
    model_class = model.StoredWorkflow
    title = "Workflows"
    default_sort_key = "name"
    columns = [
        WorkflowNameColumn("Name",
                           key="name",
                           attach_popup=False,
                           filterable="advanced"),
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
    ]
    columns.append(grids.MulticolFilterColumn("Search",
                                              cols_to_filter=[columns[0], columns[2]],
                                              key="free-text-search",
                                              visible=False,
                                              filterable="standard"))
    standard_filters = []
    default_filter = {'specified_date': 'All'}
    num_rows_per_page = 50
    use_paging = True

    def build_initial_query(self, trans, **kwd):
        return trans.sa_session.query(self.model_class) \
                               .join(model.User) \
                               .enable_eagerloads(False)


class Workflows(BaseUIController, ReportQueryBuilder):

    specified_date_list_grid = SpecifiedDateListGrid()

    @web.expose
    def specified_date_handler(self, trans, **kwd):
        # We add params to the keyword dict in this method in order to rename the param
        # with an "f-" prefix, simulating filtering by clicking a search link.  We have
        # to take this approach because the "-" character is illegal in HTTP requests.
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
            if operation == "workflow_per_month":
                # The received id is the stored_workflow id.
                return trans.response.send_redirect(web.url_for(controller='workflows',
                                                                action='workflow_per_month',
                                                                **kwd))
            elif operation == "user_per_month":
                stored_workflow_id = kwd.get('id', None)
                workflow = get_workflow(trans, stored_workflow_id)
                if workflow.user:
                    kwd['email'] = workflow.user.email
                else:
                    kwd['email'] = None  # For anonymous users ( shouldn't happen with workflows )
                return trans.response.send_redirect(web.url_for(controller='workflows',
                                                                action='user_per_month',
                                                                **kwd))
        return self.specified_date_list_grid(trans, **kwd)

    @web.expose
    def per_month_all(self, trans, **kwd):
        message = ''
        PageSpec = namedtuple('PageSpec', ['entries', 'offset', 'page', 'pages_found'])

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

        q = sa.select((self.select_month(model.StoredWorkflow.table.c.create_time).label('date'),
                       sa.func.count(model.StoredWorkflow.table.c.id).label('total_workflows')),
                      from_obj=[sa.outerjoin(model.StoredWorkflow.table, model.User.table)],
                      group_by=self.group_by_month(model.StoredWorkflow.table.c.create_time),
                      order_by=[_order],
                      offset=offset,
                      limit=limit)

        all_workflows = sa.select((self.select_day(model.StoredWorkflow.table.c.create_time).label('date'),
                     model.StoredWorkflow.table.c.id))

        trends = dict()
        for workflow in all_workflows.execute():
            workflow_day = int(workflow.date.strftime("%-d")) - 1
            workflow_month = int(workflow.date.strftime("%-m"))
            workflow_month_name = workflow.date.strftime("%B")
            workflow_year = workflow.date.strftime("%Y")
            key = str(workflow_month_name + workflow_year)

            try:
                trends[key][workflow_day] += 1
            except KeyError:
                workflow_year = int(workflow_year)
                wday, day_range = calendar.monthrange(workflow_year, workflow_month)
                trends[key] = [0] * day_range
                trends[key][workflow_day] += 1

        workflows = []
        for row in q.execute():
            month_name = row.date.strftime("%B")
            year = int(row.date.strftime("%Y"))

            workflows.append((row.date.strftime("%Y-%m"),
                              row.total_workflows,
                              month_name,
                              year))

        pages_found = ceil(len(workflows) / float(entries))
        page_specs = PageSpec(entries, offset, page, pages_found)

        return trans.fill_template('/webapps/reports/workflows_per_month_all.mako',
                                   order=order,
                                   arrow=arrow,
                                   sort_id=sort_id,
                                   trends=trends,
                                   workflows=workflows,
                                   message=message,
                                   page_specs=page_specs)

    @web.expose
    def per_user(self, trans, **kwd):
        message = ''
        PageSpec = namedtuple('PageSpec', ['entries', 'offset', 'page', 'pages_found'])

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

        workflows = []
        q = sa.select((model.User.table.c.email.label('user_email'),
                       sa.func.count(model.StoredWorkflow.table.c.id).label('total_workflows')),
                      from_obj=[sa.outerjoin(model.StoredWorkflow.table, model.User.table)],
                      group_by=['user_email'],
                      order_by=[_order],
                      offset=offset,
                      limit=limit)

        all_workflows_per_user = sa.select((model.User.table.c.email.label('user_email'),
                                            self.select_day(model.StoredWorkflow.table.c.create_time).label('date'),
                                            model.StoredWorkflow.table.c.id),
                                           from_obj=[sa.outerjoin(model.StoredWorkflow.table,
                                                                  model.User.table)])
        currday = datetime.today()
        trends = dict()
        for workflow in all_workflows_per_user.execute():
            curr_user = re.sub(r'\W+', '', workflow.user_email)
            try:
                day = currday - workflow.date
            except TypeError:
                day = datetime.date(currday) - datetime.date(workflow.date)

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

        for row in q.execute():
            workflows.append((row.user_email,
                              row.total_workflows))

        pages_found = ceil(len(workflows) / float(entries))
        page_specs = PageSpec(entries, offset, page, pages_found)

        return trans.fill_template('/webapps/reports/workflows_per_user.mako',
                                   order=order,
                                   arrow=arrow,
                                   sort_id=sort_id,
                                   spark_limit=spark_limit,
                                   trends=trends,
                                   time_period=time_period,
                                   workflows=workflows,
                                   message=message,
                                   page_specs=page_specs)

    @web.expose
    def user_per_month(self, trans, **kwd):
        params = util.Params(kwd)
        message = ''
        specs = sorter('date', kwd)
        sort_id = specs.sort_id
        order = specs.order
        arrow = specs.arrow
        _order = specs.exc_order
        email = util.restore_text(params.get('email', ''))
        user_id = trans.security.decode_id(params.get('id', ''))

        q = sa.select((self.select_month(model.StoredWorkflow.table.c.create_time).label('date'),
                       sa.func.count(model.StoredWorkflow.table.c.id).label('total_workflows')),
                      whereclause=model.StoredWorkflow.table.c.user_id == user_id,
                      from_obj=[model.StoredWorkflow.table],
                      group_by=self.group_by_month(model.StoredWorkflow.table.c.create_time),
                      order_by=[_order])

        all_workflows_user_month = sa.select((self.select_day(model.StoredWorkflow.table.c.create_time).label('date'),
                                              model.StoredWorkflow.table.c.id),
                                             whereclause=model.StoredWorkflow.table.c.user_id == user_id,
                                             from_obj=[model.StoredWorkflow.table])

        trends = dict()
        for workflow in all_workflows_user_month.execute():
            workflow_day = int(workflow.date.strftime("%-d")) - 1
            workflow_month = int(workflow.date.strftime("%-m"))
            workflow_month_name = workflow.date.strftime("%B")
            workflow_year = workflow.date.strftime("%Y")
            key = str(workflow_month_name + workflow_year)

            try:
                trends[key][workflow_day] += 1
            except KeyError:
                workflow_year = int(workflow_year)
                wday, day_range = calendar.monthrange(workflow_year, workflow_month)
                trends[key] = [0] * day_range
                trends[key][workflow_day] += 1

        workflows = []
        for row in q.execute():
            workflows.append((row.date.strftime("%Y-%m"),
                              row.total_workflows,
                              row.date.strftime("%B"),
                              row.date.strftime("%Y")))
        return trans.fill_template('/webapps/reports/workflows_user_per_month.mako',
                                   email=util.sanitize_text(email),
                                   order=order,
                                   arrow=arrow,
                                   sort_id=sort_id,
                                   trends=trends,
                                   workflows=workflows,
                                   message=message)

    @web.expose
    def per_workflow(self, trans, **kwd):
        message = ''
        PageSpec = namedtuple('PageSpec', ['entries', 'offset', 'page', 'pages_found'])

        specs = sorter('workflow_name', kwd)
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

        q = sa.select((model.Workflow.table.c.id.label('workflow_id'),
                       sa.func.min(model.Workflow.table.c.name).label('workflow_name'),
                       sa.func.count(model.WorkflowInvocation.table.c.id).label('total_runs')),
                      from_obj=[model.Workflow.table,
                                model.WorkflowInvocation.table],
                      whereclause=sa.and_(model.WorkflowInvocation.table.c.workflow_id == model.Workflow.table.c.id),
                      group_by=[model.Workflow.table.c.id],
                      order_by=[_order],
                      offset=offset,
                      limit=limit)

        all_runs_per_workflow = sa.select((model.Workflow.table.c.id.label('workflow_id'),
                                           model.Workflow.table.c.name.label('workflow_name'),
                                           self.select_day(model.WorkflowInvocation.table.c.create_time).label('date')),
                                          from_obj=[model.Workflow.table,
                                                    model.WorkflowInvocation.table],
                                          whereclause=sa.and_(model.WorkflowInvocation.table.c.workflow_id == model.Workflow.table.c.id))

        currday = date.today()
        trends = dict()
        for run in all_runs_per_workflow.execute():
            curr_tool = re.sub(r'\W+', '', str(run.workflow_id))
            try:
                day = currday - run.date
            except TypeError:
                day = currday - datetime.date(run.date)

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

        runs = []
        for row in q.execute():
            runs.append((row.workflow_name,
                         row.total_runs,
                         row.workflow_id))

        pages_found = ceil(len(runs) / float(entries))
        page_specs = PageSpec(entries, offset, page, pages_found)

        return trans.fill_template('/webapps/reports/workflows_per_workflow.mako',
                                   order=order,
                                   arrow=arrow,
                                   sort_id=sort_id,
                                   spark_limit=spark_limit,
                                   time_period=time_period,
                                   trends=trends,
                                   runs=runs,
                                   message=message,
                                   page_specs=page_specs)

# ---- Utility methods -------------------------------------------------------


def get_workflow(trans, id):
    return trans.sa_session.query(trans.model.Workflow).get(trans.security.decode_id(id))
