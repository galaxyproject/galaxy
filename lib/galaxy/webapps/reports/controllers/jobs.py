import operator, os
from datetime import datetime
from time import strftime
from galaxy.webapps.reports.base.controller import *
import galaxy.model
import pkg_resources
pkg_resources.require( "sqlalchemy>=0.3" )
#from sqlalchemy import eagerload, desc
import sqlalchemy
import logging
log = logging.getLogger( __name__ )

class Jobs( BaseController ):
    @web.expose
    def index( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = ''
            
        jobs = self.current_month( trans, **kwd )
        return trans.fill_template( 'jobs_current_month.mako', jobs=jobs, msg=msg )

    @web.expose
    def current_month( self, trans, **kwd ):
        month = datetime.utcnow().strftime( "%Y-%m" )
        engine = galaxy.model.mapping.metadata.engine
        jobs = []

        s = """
            SELECT
                wanted_year_month_day AS year_month_day,
                num_jobs AS num_jobs,
                num_jobs_to_subtract AS num_monitor_jobs,
                wanted_day_label AS day_label
            FROM
                (SELECT
                    year_month_day AS year_month_day,
                    day_of_month AS day_of_month,
                    num_jobs_to_subtract AS num_jobs_to_subtract,
                    to_char(a_timestamp, 'Day') AS day_label
                FROM
                    (SELECT
                        substr(job.create_time, 1, 10) AS year_month_day,
                        substr(job.create_time, 9, 2) AS day_of_month,
                        count(substr(job.create_time, 1, 10)) AS num_jobs_to_subtract,
                        to_timestamp(substr(job.create_time, 1, 10), 'YYYY-MM-DD+02') AS a_timestamp
                    FROM
                        job
                    LEFT OUTER JOIN history ON job.history_id = history.id
                    LEFT OUTER JOIN galaxy_user ON history.user_id = galaxy_user.id
                    WHERE
                        substr(job.create_time, 1, 7) = '%s'
                    AND
                        galaxy_user.email = 'monitor@bx.psu.edu'
                    GROUP BY
                        substr(job.create_time, 9, 2),
                        substr(job.create_time, 1, 10)) AS fubar
                ) AS total_fubar
            FULL JOIN
                (SELECT
                    year_month_day AS wanted_year_month_day,
                    day_of_month AS wanted_day_of_month,
                    num_jobs AS num_jobs,
                    to_char(a_timestamp, 'Day') AS wanted_day_label
                FROM
                    (SELECT
                        foo.create_time AS year_month_day,
                        foo.day_of_month AS day_of_month,
                        count(foo.create_time) AS num_jobs,
                        to_timestamp(foo.create_time, 'YYYY-MM-DD+02') AS a_timestamp
                    FROM
                        (SELECT
                            substr(job.create_time, 1, 10) AS create_time,
                            substr(job.create_time, 9, 2) AS day_of_month
                        FROM
                            job
                        WHERE
                            substr(job.create_time, 1, 7) = '%s'
                        GROUP BY 
                            day_of_month,
                            job.create_time) AS foo
                    GROUP BY
                        day_of_month,
                        create_time
                    ORDER BY
                        create_time DESC) AS bar
                ) AS foobar
            ON
                foobar.wanted_year_month_day = total_fubar.year_month_day
            ORDER BY
                year_month_day DESC
        """ % ( month, month )
        
        job_rows = engine.text( s ).execute().fetchall()
        for job in job_rows:
            try:
                num_user_jobs = job.num_jobs - job.num_monitor_jobs
            except:
                num_user_jobs = job.num_jobs
            jobs.append( ( job.day_label, job.year_month_day, num_user_jobs, job.num_monitor_jobs, job.num_jobs ) )
        return jobs

