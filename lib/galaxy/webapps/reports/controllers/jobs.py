import operator, os, socket
from datetime import datetime
from time import mktime, strftime, localtime
from calendar import day_name, month_name
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
    def today_all( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = ''
        year = int( datetime.utcnow().strftime( "%Y" ) )
        month = int( datetime.utcnow().strftime( "%m" ) )
        day = int( datetime.utcnow().strftime( "%d" ) )
        year_month_day = datetime.utcnow().strftime( "%Y-%m-%d" )
        today = params.get( 'today', year_month_day )
        engine = galaxy.model.mapping.metadata.engine
        jobs = []
        monitor_email = params.get( 'monitor_email', 'monitor@bx.psu.edu' )
        # Return weekday (0-6 ~ Mon-Sun) for year (1970-...), month (1-12), day (1-31)
        def weekday( year, month, day ):
            secs = mktime( ( year, month, day, 0, 0, 0, 0, 0, 0 ) )
            tuple = localtime( secs )
            return tuple[6]
        day_of_week = weekday( year, month, day )
        day_label = params.get( 'day_label', day_name[ day_of_week ] )
        month_label = params.get( 'month_label', month_name[ int( datetime.utcnow().strftime( "%m" ) ) ] )
        year_label = params.get( 'year_label', datetime.utcnow().strftime( "%Y" ) )
        day_of_month = datetime.utcnow().strftime( "%d" )
        s = """
        SELECT
            wanted_year_month_day AS year_month_day,
            wanted_day_of_month AS day_of_month,
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
                    substr(job.create_time, 1, 10) = '%s'
                AND
                    galaxy_user.email = '%s'
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
                        substr(job.create_time, 1, 10) = '%s'
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
        """ % ( today, monitor_email, today )
        job_rows = engine.text( s ).execute().fetchall()
        for job in job_rows:
            try:
                num_user_jobs = job.num_jobs - job.num_monitor_jobs
            except:
                num_user_jobs = job.num_jobs
            jobs.append( ( job.day_label, job.year_month_day, num_user_jobs, job.num_monitor_jobs, job.num_jobs, job.day_of_month ) )
        return trans.fill_template( 'jobs_today_all.mako', day_label=day_label, month_label=month_label, year_label=year_label, day_of_month=day_of_month, month=month, jobs=jobs, msg=msg )
    @web.expose
    def specified_month_all( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = ''
        year_month = datetime.utcnow().strftime( "%Y-%m" )
        month = params.get( 'month', year_month )
        engine = galaxy.model.mapping.metadata.engine
        jobs = []
        monitor_email = params.get( 'monitor_email', 'monitor@bx.psu.edu' )
        month_label = params.get( 'month_label', month_name[ int( datetime.utcnow().strftime( "%m" ) ) ] )
        year_label = params.get( 'year_label', datetime.utcnow().strftime( "%Y" ) )
        s = """
        SELECT
            wanted_year_month_day AS year_month_day,
            wanted_day_of_month AS day_of_month,
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
                    galaxy_user.email = '%s'
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
        """ % ( month, monitor_email, month )
        job_rows = engine.text( s ).execute().fetchall()
        for job in job_rows:
            try:
                num_user_jobs = job.num_jobs - job.num_monitor_jobs
            except:
                num_user_jobs = job.num_jobs
            jobs.append( ( job.day_label, job.year_month_day, num_user_jobs, job.num_monitor_jobs, job.num_jobs, job.day_of_month ) )
        return trans.fill_template( 'jobs_specified_month_all.mako', month_label=month_label, year_label=year_label, month=month, jobs=jobs, msg=msg )
    @web.expose
    def specified_month_in_error( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = ''
        year_month = datetime.utcnow().strftime( "%Y-%m" )
        month = params.get( 'month', year_month )
        engine = galaxy.model.mapping.metadata.engine
        jobs = []
        month_label = params.get( 'month_label', month_name[ int( datetime.utcnow().strftime( "%m" ) ) ] )
        year_label = params.get( 'year_label', datetime.utcnow().strftime( "%Y" ) )
        s = """
        SELECT
            year_month_day AS year_month_day,
            day_of_month AS day_of_month,
            num_jobs AS num_jobs,
            to_char(a_timestamp, 'Day') AS day_label
        FROM
            (SELECT
                foo.create_time AS year_month_day,
                foo.day_of_month AS day_of_month,
                count(foo.create_time) AS num_jobs,
                to_timestamp(foo.create_time, 'YYYY-MM-DD') AS a_timestamp
            FROM
                (SELECT
                    substr(create_time, 1, 10) AS create_time,
                    substr(create_time, 9, 2) AS day_of_month
                FROM
                    job
                WHERE
                    state = 'error'
                AND
                    substr(create_time, 1, 7) = '%s'
                GROUP BY
                    day_of_month,
                    create_time) AS foo
            GROUP BY
                day_of_month,
                create_time
            ORDER BY
                create_time DESC) AS bar
        """ % ( month )
        job_rows = engine.text( s ).execute().fetchall()
        for job in job_rows:
            jobs.append( ( job.day_label, job.year_month_day, job.num_jobs, job.day_of_month ) )
        return trans.fill_template( 'jobs_specified_month_in_error.mako', month_label=month_label, year_label=year_label, month=month, jobs=jobs, msg=msg )
    @web.expose
    def specified_date_in_error( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = ''
        engine = galaxy.model.mapping.metadata.engine
        jobs = []
        today = datetime.utcnow().strftime( "%Y-%m-%d" )
        specified_date = params.get( 'specified_date', today )
        day_label = params.get( 'day_label', datetime.utcnow().strftime( "%d" ) )
        month_label = params.get( 'month_label', month_name[ int( datetime.utcnow().strftime( "%m" ) ) ] )
        year_label = params.get( 'year_label', datetime.utcnow().strftime( "%Y" ) )
        day_of_month = params.get( 'day_of_month', datetime.utcnow().strftime( "%d" ) )
        s = """
        SELECT
            job.id AS id,
            job.state AS state,
            substr(job.create_time, 1, 19) AS create_time,
            substr(job.update_time, 1, 19) AS update_time,
            job.tool_id AS tool_id,
            job.command_line AS command_line,
            job.stderr AS stderr,
            job.session_id AS session_id,
            job.traceback as stack_trace,
            job.info as info,
            galaxy_user.email AS user_email,
            galaxy_session.remote_addr AS remote_address
        FROM
            job
        LEFT OUTER JOIN history ON job.history_id = history.id
        LEFT OUTER JOIN galaxy_user ON history.user_id = galaxy_user.id
        LEFT OUTER JOIN galaxy_session ON job.session_id = galaxy_session.id
        WHERE
            state = 'error'
        AND
            substr(job.create_time, 1, 10) = '%s'
        ORDER BY
            job.id DESC
        """ % specified_date
        job_rows = engine.text( s ).execute().fetchall()
        for job in job_rows:
            remote_host = job.remote_address
            if job.remote_address:
                try:
                    remote_host = socket.gethostbyaddr( job.remote_address )[0]
                except:
                    pass
            jobs.append( ( job.state, job.id, job.create_time, job.update_time, job.session_id, job.tool_id, job.user_email, remote_host, job.command_line, job.stderr, job.stack_trace, job.info ) )
        return trans.fill_template( 'jobs_specified_date_in_error.mako', specified_date=specified_date, day_label=day_label, month_label=month_label, year_label=year_label, day_of_month=day_of_month, jobs=jobs, msg=msg )
    @web.expose
    def specified_date_all( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = ''
        engine = galaxy.model.mapping.metadata.engine
        jobs = []
        today = datetime.utcnow().strftime( "%Y-%m-%d" )
        specified_date = params.get( 'specified_date', today )
        monitor_email = params.get( 'monitor_email', 'monitor@bx.psu.edu' )
        day_label = params.get( 'day_label', datetime.utcnow().strftime( "%d" ) )
        month_label = params.get( 'month_label', month_name[ int( datetime.utcnow().strftime( "%m" ) ) ] )
        year_label = params.get( 'year_label', datetime.utcnow().strftime( "%Y" ) )
        day_of_month = params.get( 'day_of_month', datetime.utcnow().strftime( "%d" ) )
        s = """
        SELECT
            job.id AS id,
            job.state AS state,
            substr(job.create_time, 1, 19) AS create_time,
            substr(job.update_time, 1, 19) AS update_time,
            job.tool_id AS tool_id,
            job.command_line AS command_line,
            job.stderr AS stderr,
            job.session_id AS session_id,
            job.traceback as stack_trace,
            job.info as info,
            galaxy_user.email AS user_email,
            galaxy_session.remote_addr AS remote_address
        FROM
            job
        LEFT OUTER JOIN history ON job.history_id = history.id
        LEFT OUTER JOIN galaxy_user ON history.user_id = galaxy_user.id
        LEFT OUTER JOIN galaxy_session ON job.session_id = galaxy_session.id
        WHERE
            substr(job.create_time, 1, 10) = '%s'
        AND
            galaxy_user.email != '%s'
        ORDER BY
            job.id DESC
        """ % ( specified_date, monitor_email )
        job_rows = engine.text( s ).execute().fetchall()
        for job in job_rows:
            remote_host = job.remote_address
            if job.remote_address:
                try:
                    remote_host = socket.gethostbyaddr( job.remote_address )[0]
                except:
                    pass
            jobs.append( ( job.state, job.id, job.create_time, job.update_time, job.session_id, job.tool_id, job.user_email, remote_host, job.command_line, job.stderr, job.stack_trace, job.info ) )
        return trans.fill_template( 'jobs_specified_date_all.mako', specified_date=specified_date, day_label=day_label, month_label=month_label, year_label=year_label, day_of_month=day_of_month, jobs=jobs, msg=msg )
    @web.expose
    def all_unfinished( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = ''
        engine = galaxy.model.mapping.metadata.engine
        jobs = []
        s = """
        SELECT
            job.id AS id,
            job.state AS state,
            substr(job.create_time, 1, 19) AS create_time,
            substr(job.update_time, 1, 19) AS update_time,
            job.tool_id AS tool_id,
            job.command_line AS command_line,
            job.stderr AS stderr,
            job.session_id AS session_id,
            job.traceback as stack_trace,
            job.info as info,
            galaxy_user.email AS user_email,
            galaxy_session.remote_addr AS remote_address
        FROM
            job
        LEFT OUTER JOIN history ON job.history_id = history.id
        LEFT OUTER JOIN galaxy_user ON history.user_id = galaxy_user.id
        LEFT OUTER JOIN galaxy_session ON job.session_id = galaxy_session.id
        WHERE
            job.state = 'running'
        OR
            job.state = 'queued'
        OR
            job.state = 'new'
        ORDER BY
            job.update_time DESC
        """
        job_rows = engine.text( s ).execute().fetchall()
        for job in job_rows:
            remote_host = job.remote_address
            if job.remote_address:
                try:
                    remote_host = socket.gethostbyaddr( job.remote_address )[0]
                except:
                    pass
            jobs.append( ( job.state, job.id, job.create_time, job.update_time, job.session_id, job.tool_id, job.user_email, remote_host, job.command_line, job.stderr, job.stack_trace, job.info ) )
        return trans.fill_template( 'jobs_all_unfinished.mako', jobs=jobs, msg=msg )
    @web.expose
    def per_month_all( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = ''
        engine = galaxy.model.mapping.metadata.engine
        jobs = []
        monitor_email = params.get( 'monitor_email', 'monitor@bx.psu.edu' )
        s = """
        SELECT
            wanted_year_month AS year_month,
            num_jobs AS num_jobs,
            num_monitor_jobs AS num_monitor_jobs,
            wanted_month_label AS month_label,
            wanted_year_label AS year_label
        FROM
            (SELECT
                year_month AS year_month,
                num_monitor_jobs AS num_monitor_jobs,
                to_timestamp(year_month, 'YYYY-MM-DD+02') AS a_timestamp
            FROM
                (SELECT
                    substr(job.create_time, 1, 7) AS year_month,
                    count(substr(job.create_time, 1, 10)) AS num_monitor_jobs
                FROM
                    job
                LEFT OUTER JOIN history ON job.history_id = history.id
                LEFT OUTER JOIN galaxy_user ON history.user_id = galaxy_user.id
                WHERE
                    galaxy_user.email = '%s'
                GROUP BY
                    substr(job.create_time, 1, 7)
                ) AS fubar
            ) AS total_fubar
        FULL JOIN
            (SELECT
                num_jobs AS num_jobs,
                wanted_year_month AS wanted_year_month,
                to_char(a_timestamp, 'Month') AS wanted_month_label,
                to_char(a_timestamp, 'YYYY') AS wanted_year_label
            FROM
                (SELECT
                    num_jobs AS num_jobs,
                    wanted_year_month AS wanted_year_month,
                    to_timestamp(wanted_year_month, 'YYYY-MM-DD+02' ) AS a_timestamp
                FROM
                    (SELECT
                        count(id) AS num_jobs,
                        substr(create_time, 1, 7) AS wanted_year_month
                    FROM
                        job
                    GROUP BY
                        substr(create_time, 1, 7)
                    ORDER BY
                        substr(create_time, 1, 7) DESC) AS foo
                ) AS bar
            ) AS foobar
        ON
            foobar.wanted_year_month = total_fubar.year_month
        ORDER BY
            year_month DESC
        """ % monitor_email
        job_rows = engine.text( s ).execute().fetchall()
        for job in job_rows:
            if job.num_jobs is None:
                job.num_jobs = 0
            if job.num_monitor_jobs is None:
                job.num_monitor_jobs = 0 
            num_user_jobs = job.num_jobs - job.num_monitor_jobs
            jobs.append( ( job.year_month, num_user_jobs, job.num_monitor_jobs, job.num_jobs, job.month_label, job.year_label ) )
        return trans.fill_template( 'jobs_per_month_all.mako', jobs=jobs, msg=msg )
    @web.expose
    def per_month_in_error( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = ''
        engine = galaxy.model.mapping.metadata.engine
        jobs = []
        s = """
        SELECT
            num_jobs AS num_jobs,
            year_month AS year_month,
            to_char(a_timestamp, 'Month') AS month_label,
            to_char(a_timestamp, 'YYYY') AS year_label
        FROM
            (SELECT
                num_jobs AS num_jobs,
                year_month AS year_month,
                to_timestamp(year_month, 'YYYY-MM-DD') AS a_timestamp
            FROM
                (SELECT
                    count(id) AS num_jobs,
                    substr(create_time, 1, 7) AS year_month
                FROM
                    job
                WHERE
                    state = 'error'
                GROUP BY
                    year_month
                ORDER BY
                    year_month DESC) AS foo) AS bar
        """
        job_rows = engine.text( s ).execute().fetchall()
        for job in job_rows:
            jobs.append( ( job.year_month, job.num_jobs, job.month_label, job.year_label ) )
        return trans.fill_template( 'jobs_per_month_in_error.mako', jobs=jobs, msg=msg )
    @web.expose
    def per_user( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = ''
        engine = galaxy.model.mapping.metadata.engine
        jobs = []
        s = """
        SELECT
            galaxy_user.email AS user_email,
            count(job.id) AS num_jobs
        FROM
            job
        LEFT OUTER JOIN galaxy_session ON galaxy_session.id = job.session_id
        LEFT OUTER JOIN galaxy_user ON galaxy_session.user_id = galaxy_user.id
        GROUP BY
            user_email
        ORDER BY
            num_jobs DESC,
            user_email
        """
        job_rows = engine.text( s ).execute().fetchall()
        for job in job_rows:
            jobs.append( ( job.user_email, job.num_jobs ) )
        return trans.fill_template( 'jobs_per_user.mako', jobs=jobs, msg=msg )
    @web.expose
    def user_per_month( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = ''
        engine = galaxy.model.mapping.metadata.engine
        jobs = []
        email = params.get( 'email', 'monitor@bx.psu.edu' )
        # The @ char has been converted to an 'X'
        email = email.replace( 'X', '@' )
        s = """
        SELECT
            num_jobs AS num_jobs,
            year_month AS year_month,
            to_char(a_timestamp, 'Month') AS month_label,
            to_char(a_timestamp, 'YYYY') AS year_label
        FROM
            (SELECT
                num_jobs AS num_jobs,
                year_month AS year_month,
                to_timestamp(year_month, 'YYYY-MM-DD') AS a_timestamp
            FROM
                (SELECT
                    count(job.id) AS num_jobs,
                    substr(job.create_time, 1, 7) AS year_month
                FROM
                    job
                LEFT OUTER JOIN galaxy_session ON galaxy_session.id = job.session_id
                LEFT OUTER JOIN galaxy_user ON galaxy_session.user_id = galaxy_user.id
                WHERE
                    galaxy_user.email = '%s'
                GROUP BY
                    year_month
                ORDER BY
                    year_month DESC) AS foo) AS bar
        """ % email
        job_rows = engine.text( s ).execute().fetchall()
        for job in job_rows:
            jobs.append( ( job.year_month, job.num_jobs, job.month_label, job.year_label ) )
        return trans.fill_template( 'jobs_user_per_month.mako', email=email, jobs=jobs, msg=msg )
    @web.expose
    def user_for_month( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = ''
        engine = galaxy.model.mapping.metadata.engine
        jobs = []
        email = params.get( 'email', 'monitor@bx.psu.edu' )
        # The @ char has been converted to an 'X'
        email = email.replace( 'X', '@' )
        year_month = datetime.utcnow().strftime( "%Y-%m" )
        month = params.get( 'month', year_month )
        month_label = params.get( 'month_label', month_name[ int( datetime.utcnow().strftime( "%m" ) ) ] )
        year_label = params.get( 'year_label', datetime.utcnow().strftime( "%Y" ) )
        s = """
        SELECT
            job.id AS id,
            job.state AS state,
            substr(job.create_time, 1, 19) AS create_time,
            substr(job.update_time, 1, 19) AS update_time,
            job.tool_id AS tool_id,
            job.command_line AS command_line,
            job.stderr AS stderr,
            job.session_id AS session_id,
            job.traceback as stack_trace,
            job.info as info,
            galaxy_user.email AS user_email,
            galaxy_session.remote_addr AS remote_address
        FROM
            job
        LEFT OUTER JOIN history ON job.history_id = history.id
        LEFT OUTER JOIN galaxy_user ON history.user_id = galaxy_user.id
        LEFT OUTER JOIN galaxy_session ON job.session_id = galaxy_session.id
        WHERE
            galaxy_user.email = '%s'
        AND
            substr(job.create_time, 1, 7) = '%s'
        ORDER BY
            job.id DESC
        """ % ( email, month )
        job_rows = engine.text( s ).execute().fetchall()
        for job in job_rows:
            remote_host = job.remote_address
            if job.remote_address:
                try:
                    remote_host = socket.gethostbyaddr( job.remote_address )[0]
                except:
                    pass
            jobs.append( ( job.state, job.id, job.create_time, job.update_time, job.session_id, job.tool_id, job.user_email, remote_host, job.command_line, job.stderr, job.stack_trace, job.info ) )
        return trans.fill_template( 'jobs_user_for_month.mako', email=email, month=month, month_label=month_label, year_label=year_label, jobs=jobs, msg=msg )
    @web.expose
    def per_tool( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = ''
        engine = galaxy.model.mapping.metadata.engine
        jobs = []
        s = """
        SELECT
            tool_id AS tool_id,
            count(tool_id) AS times_run
        FROM
            job
        GROUP BY tool_id
        ORDER BY tool_id
        """
        job_rows = engine.text( s ).execute().fetchall()
        for job in job_rows:
            jobs.append( ( job.tool_id, job.times_run ) )
        return trans.fill_template( 'jobs_per_tool.mako', jobs=jobs, msg=msg )
    @web.expose
    def tool_per_month( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = ''
        engine = galaxy.model.mapping.metadata.engine
        jobs = []
        tool_id = params.get( 'tool_id', 'Add a column1' )
        s = """            
        SELECT
            num_jobs AS num_jobs,
            year_month AS year_month,
            to_char(a_timestamp, 'Month') AS month_label,
            to_char(a_timestamp, 'YYYY') AS year_label
        FROM
            (SELECT
                num_jobs AS num_jobs,
                year_month AS year_month,
                to_timestamp(year_month, 'YYYY-MM-DD') AS a_timestamp
            FROM
                (SELECT
                    count(id) AS num_jobs,
                    substr(create_time, 1, 7) AS year_month
                FROM
                    job
                WHERE
                    tool_id = '%s'
                GROUP BY
                    year_month
                ORDER BY
                    year_month DESC) AS foo) AS bar 
        """ % tool_id
        job_rows = engine.text( s ).execute().fetchall()
        for job in job_rows:
            jobs.append( ( job.year_month, job.num_jobs, job.month_label, job.year_label ) )
        return trans.fill_template( 'jobs_tool_per_month.mako', tool_id=tool_id, jobs=jobs, msg=msg )
    @web.expose
    def tool_for_month( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = ''
        engine = galaxy.model.mapping.metadata.engine
        jobs = []
        tool_id = params.get( 'tool_id', 'Add a column1' )
        year_month = datetime.utcnow().strftime( "%Y-%m" )
        month = params.get( 'month', year_month )
        month_label = params.get( 'month_label', month_name[ int( datetime.utcnow().strftime( "%m" ) ) ] )
        year_label = params.get( 'year_label', datetime.utcnow().strftime( "%Y" ) )
        s = """
        SELECT
            job.id AS id,
            job.state AS state,
            substr(job.create_time, 1, 19) AS create_time,
            substr(job.update_time, 1, 19) AS update_time,
            job.tool_id AS tool_id,
            job.command_line AS command_line,
            job.stderr AS stderr,
            job.session_id AS session_id,
            job.traceback as stack_trace,
            job.info as info,
            galaxy_user.email AS user_email,
            galaxy_session.remote_addr AS remote_address
        FROM
            job
        LEFT OUTER JOIN history ON job.history_id = history.id
        LEFT OUTER JOIN galaxy_user ON history.user_id = galaxy_user.id
        LEFT OUTER JOIN galaxy_session ON job.session_id = galaxy_session.id
        WHERE
            tool_id = '%s'
        AND
            substr(job.create_time, 1, 7) = '%s'
        ORDER BY
            job.id DESC
        """ % ( tool_id, month )
        job_rows = engine.text( s ).execute().fetchall()
        for job in job_rows:
            remote_host = job.remote_address
            if job.remote_address:
                try:
                    remote_host = socket.gethostbyaddr( job.remote_address )[0]
                except:
                    pass
            jobs.append( ( job.state, job.id, job.create_time, job.update_time, job.session_id, job.tool_id, job.user_email, remote_host, job.command_line, job.stderr, job.stack_trace, job.info ) )
        return trans.fill_template( 'jobs_tool_for_month.mako', tool_id=tool_id, month=month, month_label=month_label, year_label=year_label, jobs=jobs, msg=msg )
    @web.expose
    def per_domain( self, trans, **kwd ):
        params = util.Params( kwd )
        msg = ''
        engine = galaxy.model.mapping.metadata.engine
        jobs = []
        s = """
        SELECT
            substr(bar.first_pass_domain, bar.dot_position, 4) AS domain,
            count(job_id) AS num_jobs
        FROM
            (SELECT
                user_email AS user_email,
                first_pass_domain,
                position('.' in first_pass_domain) AS dot_position,
                job_id AS job_id
            FROM
                (SELECT
                    email AS user_email,
                    substr(email, char_length(email)-3, char_length(email)) AS first_pass_domain,
                    job.id AS job_id
                FROM
                    job
                LEFT OUTER JOIN galaxy_session ON galaxy_session.id = job.session_id
                LEFT OUTER JOIN galaxy_user ON galaxy_session.user_id = galaxy_user.id
                WHERE
                    job.session_id = galaxy_session.id
                AND
                    galaxy_session.user_id = galaxy_user.id
                ) AS foo
            ) AS bar
        GROUP BY
            domain
        ORDER BY
            num_jobs DESC
        """
        job_rows = engine.text( s ).execute().fetchall()
        for job in job_rows:
            jobs.append( ( job.domain, job.num_jobs ) )
        return trans.fill_template( 'jobs_per_domain.mako', jobs=jobs, msg=msg )
