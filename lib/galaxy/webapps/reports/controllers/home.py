import calendar
from collections import namedtuple
from datetime import datetime, date, timedelta
from galaxy.web.base.controller import BaseUIController, web
from galaxy import model, util
from galaxy.model.orm import and_, not_, or_
import pkg_resources
pkg_resources.require( "SQLAlchemy >= 0.4" )
import sqlalchemy as sa
from galaxy.webapps.reports.controllers.query import ReportQueryBuilder

import logging
log = logging.getLogger( __name__ )

class HomePage( BaseUIController, ReportQueryBuilder ):
	@web.expose
	def run_stats( self, trans, **kwd ):
		message = ''
		end_date = datetime.utcnow()
		end_date = datetime(end_date.year, end_date.month, end_date.day, end_date.hour)
		start_hours = end_date - timedelta(1)
		start_days_eta = end_date - timedelta(3)
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
				(model.Job.table.c.create_time).label( 'create_time' ),
				(model.Job.table.c.update_time).label( 'update_time' ) 
			)
		)

		for job in recent_jobs.execute():
			if( job.create_time >= start_days and
				job.create_time < end_date ):
				if( job.create_time >= start_hours and
					job.create_time < end_date ):
					# Get the creation time for the jobs in the past day
					time = end_date - job.create_time
					hours = time.total_seconds() // 3600
					jc_hr_data[int(hours)] += 1
				# Get the creation time for jobs in the past 30 days
				day = (end_date - job.create_time).days
				jc_dy_data[int(day)] += 1

			if( job.update_time >= start_days and
				job.update_time < end_date ):
				if( job.update_time >= start_hours and
					job.update_time < end_date ):
					# Get the time finishedfor the jobs in the past day
					hour = (end_date - job.update_time).total_seconds() // 3600
					jf_hr_data[int(hour)] += 1

					# Get the Elapsed Time for said job
					time = (job.update_time - job.create_time)
					sec = time.seconds
					hours, remainder = divmod(sec, 3600)
					minutes, seconds = divmod(remainder, 60)
					hours += (time.days * 24)
					minutes += (hours * 60)
					time =  minutes
					et_hr_data.append(time)
				# Get the elapsed time for the jobs in the past 3 days
				if( job.update_time >= start_days_eta and
					job.update_time < end_date ):
					time = (job.update_time - job.create_time)
					sec = time.seconds
					hours, remainder = divmod(sec, 3600)
					minutes, seconds = divmod(remainder, 60)
					hours += (time.days * 24)
					minutes += (hours * 60)
					time =  minutes
					if time <= 7200:
						et_dy_data.append(time)

				#Get the time the job finished in the 30 days
				day = (end_date - job.update_time).days
				jf_dy_data[int(day)] += 1

		return trans.fill_template( '/webapps/reports/run_stats.mako', 
			jf_hr_data=jf_hr_data,
			jf_dy_data=jf_dy_data,
			jc_hr_data=jc_hr_data,
			jc_dy_data=jc_dy_data,
			et_hr_data=et_hr_data,
			et_dy_data=et_dy_data,
			message=message )