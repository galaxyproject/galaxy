import calendar
import logging
import operator
from datetime import (
    date,
    datetime,
    timedelta
)

import sqlalchemy as sa
from markupsafe import escape
from sqlalchemy import false

import galaxy.model
from galaxy import util
from galaxy.web.base.controller import BaseUIController, web
from galaxy.webapps.reports.controllers.jobs import sorter
from galaxy.webapps.reports.controllers.query import ReportQueryBuilder

log = logging.getLogger(__name__)


class Users(BaseUIController, ReportQueryBuilder):

    @web.expose
    def registered_users(self, trans, **kwd):
        message = escape(util.restore_text(kwd.get('message', '')))
        num_users = trans.sa_session.query(galaxy.model.User).count()
        return trans.fill_template('/webapps/reports/registered_users.mako', num_users=num_users, message=message)

    @web.expose
    def registered_users_per_month(self, trans, **kwd):
        message = escape(util.restore_text(kwd.get('message', '')))
        specs = sorter('date', kwd)
        sort_id = specs.sort_id
        order = specs.order
        arrow = specs.arrow
        _order = specs.exc_order

        q = sa.select((self.select_month(galaxy.model.User.table.c.create_time).label('date'),
                       sa.func.count(galaxy.model.User.table.c.id).label('num_users')),
                      from_obj=[galaxy.model.User.table],
                      group_by=self.group_by_month(galaxy.model.User.table.c.create_time),
                      order_by=[_order])
        users = []
        for row in q.execute():
            users.append((row.date.strftime("%Y-%m"),
                          row.num_users,
                          row.date.strftime("%B"),
                          row.date.strftime("%Y")))
        return trans.fill_template('/webapps/reports/registered_users_per_month.mako',
                                   order=order,
                                   arrow=arrow,
                                   sort_id=sort_id,
                                   users=users,
                                   message=message)

    @web.expose
    def specified_month(self, trans, **kwd):
        message = escape(util.restore_text(kwd.get('message', '')))
        # If specified_date is not received, we'll default to the current month
        specified_date = kwd.get('specified_date', datetime.utcnow().strftime("%Y-%m-%d"))
        specified_month = specified_date[:7]
        year, month = map(int, specified_month.split("-"))
        start_date = date(year, month, 1)
        end_date = start_date + timedelta(days=calendar.monthrange(year, month)[1])
        month_label = start_date.strftime("%B")
        year_label = start_date.strftime("%Y")
        q = sa.select((self.select_day(galaxy.model.User.table.c.create_time).label('date'),
                       sa.func.count(galaxy.model.User.table.c.id).label('num_users')),
                      whereclause=sa.and_(galaxy.model.User.table.c.create_time >= start_date,
                                          galaxy.model.User.table.c.create_time < end_date),
                      from_obj=[galaxy.model.User.table],
                      group_by=self.group_by_day(galaxy.model.User.table.c.create_time),
                      order_by=[sa.desc('date')])
        users = []
        for row in q.execute():
            users.append((row.date.strftime("%Y-%m-%d"),
                          row.date.strftime("%d"),
                          row.num_users,
                          row.date.strftime("%A")))
        return trans.fill_template('/webapps/reports/registered_users_specified_month.mako',
                                   month_label=month_label,
                                   year_label=year_label,
                                   month=month,
                                   users=users,
                                   message=message)

    @web.expose
    def specified_date(self, trans, **kwd):
        message = escape(util.restore_text(kwd.get('message', '')))
        # If specified_date is not received, we'll default to the current month
        specified_date = kwd.get('specified_date', datetime.utcnow().strftime("%Y-%m-%d"))
        year, month, day = map(int, specified_date.split("-"))
        start_date = date(year, month, day)
        end_date = start_date + timedelta(days=1)
        day_of_month = start_date.strftime("%d")
        day_label = start_date.strftime("%A")
        month_label = start_date.strftime("%B")
        year_label = start_date.strftime("%Y")
        q = sa.select((self.select_day(galaxy.model.User.table.c.create_time).label('date'),
                       galaxy.model.User.table.c.email),
                      whereclause=sa.and_(galaxy.model.User.table.c.create_time >= start_date,
                                          galaxy.model.User.table.c.create_time < end_date),
                      from_obj=[galaxy.model.User.table],
                      order_by=[galaxy.model.User.table.c.email])
        users = []
        for row in q.execute():
            users.append((row.email))
        return trans.fill_template('/webapps/reports/registered_users_specified_date.mako',
                                   specified_date=start_date,
                                   day_label=day_label,
                                   month_label=month_label,
                                   year_label=year_label,
                                   day_of_month=day_of_month,
                                   users=users,
                                   message=message)

    @web.expose
    def last_access_date(self, trans, **kwd):
        message = escape(util.restore_text(kwd.get('message', '')))
        specs = sorter('one', kwd)
        sort_id = specs.sort_id
        order = specs.order
        arrow = specs.arrow

        def name_to_num(name):
            num = None

            if name is not None and name.lower() == 'zero':
                num = 0
            else:
                num = 1

            return num

        if order == "desc":
            _order = True
        else:
            _order = False

        days_not_logged_in = kwd.get('days_not_logged_in', 90)
        if not days_not_logged_in:
            days_not_logged_in = 0
        cutoff_time = datetime.utcnow() - timedelta(days=int(days_not_logged_in))
        users = []
        for user in trans.sa_session.query(galaxy.model.User) \
                                    .filter(galaxy.model.User.table.c.deleted == false()) \
                                    .order_by(galaxy.model.User.table.c.email):
            if user.galaxy_sessions:
                last_galaxy_session = user.galaxy_sessions[0]
                if last_galaxy_session.update_time < cutoff_time:
                    users.append((user.email, last_galaxy_session.update_time.strftime("%Y-%m-%d")))
            else:
                # The user has never logged in
                users.append((user.email, "never logged in"))
        users = sorted(users, key=operator.itemgetter(name_to_num(sort_id)), reverse=_order)
        return trans.fill_template('/webapps/reports/users_last_access_date.mako',
                                   order=order,
                                   arrow=arrow,
                                   sort_id=sort_id,
                                   days_not_logged_in=days_not_logged_in,
                                   users=users,
                                   message=message)

    @web.expose
    def user_disk_usage(self, trans, **kwd):
        message = escape(util.restore_text(kwd.get('message', '')))
        specs = sorter('disk_usage', kwd)
        sort_id = specs.sort_id
        order = specs.order
        arrow = specs.arrow

        if order == "desc":
            _order = True
        else:
            _order = False

        user_cutoff = int(kwd.get('user_cutoff', 60))
        # disk_usage isn't indexed
        users = sorted(trans.sa_session.query(galaxy.model.User).all(), key=operator.attrgetter(str(sort_id)), reverse=_order)
        if user_cutoff:
            users = users[:user_cutoff]
        return trans.fill_template('/webapps/reports/users_user_disk_usage.mako',
                                   order=order,
                                   arrow=arrow,
                                   sort_id=sort_id,
                                   users=users,
                                   user_cutoff=user_cutoff,
                                   message=message)

    @web.expose
    def history_per_user(self, trans, **kwd):
        message = escape(util.restore_text(kwd.get('message', '')))
        user_cutoff = int(kwd.get('user_cutoff', 60))
        sorting = 0 if kwd.get('sorting', 'User') == 'User' else 1
        descending = 1 if kwd.get('descending', 'desc') == 'desc' else -1
        reverse = descending == 1
        sort_keys = (
            lambda v: v[0].lower(),
            lambda v: v[1]
        )

        req = sa.select(
            (sa.func.count(galaxy.model.History.table.c.id).label('history'),
             galaxy.model.User.table.c.username.label('username')),
            from_obj=[sa.outerjoin(galaxy.model.History.table, galaxy.model.User.table)],
            whereclause=galaxy.model.History.table.c.user_id == galaxy.model.User.table.c.id,
            group_by=['username'],
            order_by=[sa.desc('username'), 'history'])

        histories = [(_.username if _.username is not None else "Unknown", _.history) for _ in req.execute()]
        histories.sort(key=sort_keys[sorting], reverse=reverse)
        if user_cutoff != 0:
            histories = histories[:user_cutoff]

        return trans.fill_template('/webapps/reports/history_per_user.mako',
                                   histories=histories,
                                   user_cutoff=user_cutoff,
                                   sorting=sorting,
                                   descending=descending,
                                   message=message)
