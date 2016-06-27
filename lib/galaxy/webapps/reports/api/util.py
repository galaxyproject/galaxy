import time
from datetime import datetime, date, timedelta
import calendar


def to_epoch(datetime_obj):
    return int(time.mktime(datetime_obj.timetuple()))

def date_filter(self, kwd, date_field):
    strftime = "%Y"
    where = None
    select = self.select_year(date_field)
    start_date = None
    end_date = None

    # If a year, refine by year
    if 'year' in kwd:
        year = int(kwd['year'])

        start_date = date(year, 1, 1)
        end_date = start_date + timedelta(days=365)
        select = self.select_month(date_field)
        strftime = "%Y-%m"

        # If we further refine by month, update the queries
        if 'month' in kwd:
            month = int(kwd['month'])
            start_date = date(year, month, 1)
            end_date = start_date + timedelta(days=calendar.monthrange(year, month)[1])
            select = self.select_day(date_field)
            strftime = "%Y-%m-%d"

        where = [
            date_field >= start_date,
            date_field < end_date,
        ]

    return strftime, where, select, start_date, end_date

def state_filter(kwd, state_col):
    if 'state' in kwd:
        if kwd['state'] == 'error':
            return [state_col == 'error']
        elif kwd['state'] == 'ok':
            return [state_col == 'ok']
    return None
