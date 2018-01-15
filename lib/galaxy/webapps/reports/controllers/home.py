import calendar
import logging
from datetime import datetime, timedelta

import sqlalchemy as sa

from galaxy import model
from galaxy.web.base.controller import BaseUIController, web
from galaxy.webapps.reports.controllers.query import ReportQueryBuilder

log = logging.getLogger(__name__)


class HomePage(BaseUIController, ReportQueryBuilder):
    @web.expose
    def run_stats(self, trans, **kwd):
        message = ''
        end_date = datetime.utcnow()
        end_date = datetime(end_date.year, end_date.month, end_date.day, end_date.hour)
        end_date_buffer = datetime(end_date.year, end_date.month, end_date.day, end_date.hour + 1)
        start_hours = end_date - timedelta(1)
        start_days = end_date - timedelta(30)

        jf_hr_data = [0] * 24
        jf_dy_data = [0] * 30
        jc_hr_data = [0] * 24
        jc_dy_data = [0] * 30
        et_hr_data = []
        et_dy_data = []

        recent_jobs = sa.select(
            (
                (model.Job.table.c.id),
                (model.Job.table.c.create_time).label('create_time'),
                (model.Job.table.c.update_time).label('update_time')
            )
        )

        for job in recent_jobs.execute():
            if(job.create_time >= start_days and
               job.create_time < end_date_buffer):
                if(job.create_time >= start_hours and
                   job.create_time < end_date_buffer):
                    # Get the creation time for the jobs in the past day
                    end_day = end_date.day
                    start_day = job.create_time.day
                    end_hour = end_date.hour
                    start_hour = job.create_time.hour

                    if(end_day != start_day):
                        hours = (end_hour + 24) - start_hour
                    else:
                        hours = end_hour - start_hour

                    if(hours < 24):
                        jc_hr_data[int(hours)] += 1
                    else:
                        jc_dy_data[23] += 1
                # Get the creation time for jobs in the past 30 days
                end_month = end_date.month
                start_month = job.create_time.month
                end_day = end_date.day
                start_day = job.create_time.day

                if(end_month != start_month):
                    month_weekday, month_range = calendar.monthrange(job.create_time.year, job.create_time.month)
                    day = (end_day + month_range) - start_day
                else:
                    day = end_day - start_day

                if(day < 30):
                    jc_dy_data[int(day)] += 1

            if(job.update_time >= start_days and
               job.update_time < end_date_buffer):
                if(job.update_time >= start_hours and
                   job.update_time < end_date_buffer):
                    # Get the time finishedfor the jobs in the past day
                    end_day = end_date.day
                    start_day = job.update_time.day
                    end_hour = end_date.hour
                    start_hour = job.update_time.hour

                    if(end_day != start_day):
                        hours = (end_hour + 23) - start_hour
                    else:
                        hours = end_hour - start_hour

                    if(hours < 24):
                        jf_hr_data[int(hours)] += 1

                        # Get the Elapsed Time for said job
                        time = (job.update_time - job.create_time)
                        seconds = time.seconds
                        minutes = seconds // 60
                        et_hr_data.append(minutes)
                # Get the time the job finished and run time in the 30 days
                end_month = end_date.month
                start_month = job.update_time.month
                end_day = end_date.day
                start_day = job.update_time.day

                if(end_month != start_month):
                    month_weekday, month_range = calendar.monthrange(job.update_time.year, job.update_time.month)
                    day = (end_day + (month_range - 1)) - start_day
                else:
                    day = end_day - start_day

                if(day < 30):
                    jf_dy_data[int(day)] += 1

                    # Get the Elapsed Time for said job
                    time = (job.update_time - job.create_time)
                    seconds = time.seconds
                    minutes = seconds // 60
                    et_dy_data.append(minutes)

        return trans.fill_template('/webapps/reports/run_stats.mako',
            jf_hr_data=jf_hr_data,
            jf_dy_data=jf_dy_data,
            jc_hr_data=jc_hr_data,
            jc_dy_data=jc_dy_data,
            et_hr_data=et_hr_data,
            et_dy_data=et_dy_data,
            message=message)
