"""Mixin to help build advanced queries for reports interface."""

import sqlalchemy as sa


class ReportQueryBuilder:
    def group_by_month(self, column):
        if self.app.targets_mysql:
            return [sa.func.year(column), sa.func.month(sa.func.date(column))]
        else:
            return [sa.func.date_trunc("month", sa.func.date(column))]

    def select_month(self, column):
        if self.app.targets_mysql:
            return sa.func.date(column)
        else:
            return sa.func.date_trunc("month", sa.func.date(column))

    def group_by_day(self, column):
        if self.app.targets_mysql:
            return [sa.func.day(sa.func.date(column))]
        else:
            return [sa.func.date_trunc("day", sa.func.date(column))]

    def select_day(self, column):
        if self.app.targets_mysql:
            return sa.func.date(column)
        else:
            return sa.func.date_trunc("day", sa.func.date(column))
