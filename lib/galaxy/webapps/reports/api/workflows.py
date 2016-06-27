import logging
from collections import namedtuple
import sqlalchemy as sa

from galaxy import model, util
from math import floor
from galaxy.web.base.controller import BaseAPIController, web
import re
from math import ceil
from galaxy.webapps.reports.api.util import date_filter, state_filter, user_filter
from galaxy.webapps.reports.controllers.query import ReportQueryBuilder

log = logging.getLogger( __name__ )


class Workflows( BaseAPIController, ReportQueryBuilder ):

    @web.json
    @web.expose
    def by_date(self, trans, **kwd):
        """
        Queries the DB for all workflows
        /workflows/
        /workflows/:year/
        /workflows/:year/:month/

        Specifying ?show_names=True will show workflow names instead of counts
        """
        strftime, where_date, select, start_date, end_date = date_filter(self, kwd, model.StoredWorkflow.table.c.create_time)

        where_clauses = []
        if where_date:
            where_clauses += where_date

        workflows = sa.select(
            (
                select.label('date'),
                sa.func.count(model.StoredWorkflow.table.c.id).label('total_workflows'),
                model.StoredWorkflow.table.c.name.label('name'),
            ),
            whereclause=sa.and_(*where_clauses),
            from_obj=[model.StoredWorkflow.table],
            group_by=['date', 'name'],
            order_by=['date']
        )

        result = []
        for row in workflows.execute():
            if 'show_names' in kwd:
                result.append((
                    row.date.strftime(strftime),
                    row.name,
                ))
            else:
                result.append((
                    row.date.strftime(strftime),
                    row.total_workflows,
                ))

        return result

    @web.json
    @web.expose
    def by_user(self, trans, **kwd):
        """
        Queries the DB for all workflows run by a given user

        /workflows/user/:user/
        /workflows/user/:user/:year/
        /workflows/user/:user/:year/:month/
        """
        strftime, where_date, select, start_date, end_date = \
            date_filter(self, kwd, model.StoredWorkflow.table.c.create_time)
        where_clauses = user_filter(kwd, model.User.table.c.email)

        if where_date:
            where_clauses += where_date

        workflows = sa.select(
            (
                select.label('date'),
                sa.func.count(model.StoredWorkflow.table.c.id).label('total_workflows'),
                model.StoredWorkflow.table.c.name.label('name'),
            ),
            whereclause=sa.and_(*where_clauses),
            from_obj=[model.StoredWorkflow.table],
            group_by=['date', 'name'],
            order_by=['date']
        )

        # Todo, this data structure ain't great.
        result = []
        for row in workflows.execute():
            result.append((
                row.date.strftime(strftime),
                row.name,
            ))

        return result
