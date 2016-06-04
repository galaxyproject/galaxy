#!/usr/bin/env python
import os
import sys
import json
import datetime
import urllib2
from ConfigParser import ConfigParser
import argparse
import sqlalchemy as sa

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, 'lib')))

import galaxy.config
from galaxy.objectstore import build_object_store_from_config
from galaxy.model import mapping

default_config = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, 'config/galaxy.ini'))


def init(config):
    config = os.path.abspath(config)

    config_parser = ConfigParser(dict(
        here=os.getcwd(),
        database_connection='sqlite:///database/universe.sqlite?isolation_level=IMMEDIATE'
    ))
    config_parser.read(config)
    config_dict = {}
    for key, value in config_parser.items("app:main"):
        config_dict[key] = value

    config = galaxy.config.Configuration(**config_dict)
    object_store = build_object_store_from_config(config)

    return (
        mapping.init(
            config.file_path,
            config.database_connection,
            create_tables=False,
            object_store=object_store
        ),
        object_store,
        config.database_connection.split(':')[0]
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('instance_id', help='Galactic Radio Telescope Instance ID')
    parser.add_argument('api_key', help='Galactic Radio Telescope API Key')

    parser.add_argument('-c', '--config', dest='config', help='Path to Galaxy config file (config/galaxy.ini)', default=default_config)
    parser.add_argument('--dry-run', dest='dryrun', help='Dry run (show data to be sent, but do not send)', action='store_true', default=False)
    parser.add_argument('--grt-url', dest='grt_url', help='GRT Server (You can run your own!)', default='https://radio-telescope.galaxyproject.org/api/v1/upload')
    parser.add_argument('--days', type=int, help="Number of days of data to submit", default=7)
    args = parser.parse_args()

    print 'Loading Galaxy...'
    model, object_store, engine = init(args.config)
    sa_session = model.context.current

    # Fetch jobs COMPLETED with status OK in the past week.
    since = datetime.datetime.now() - datetime.timedelta(days=args.days)
    jobs = sa_session.query(model.Job)\
        .filter(sa.and_(
            model.Job.table.c.state == "ok",
            model.Job.table.c.update_time > since
        ))\
        .all()

    # Set up our arrays
    active_users = []
    grt_tool_data = []
    grt_jobs_data = []

    def kw_metrics(job):
        return {
            '%s_%s' % (metric.plugin, metric.metric_name): metric.metric_value
            for metric in job.metrics
        }

    # For every job
    for job in jobs:
        # Append an active user, we'll reduce at the end
        active_users.append(job.user_id)

        # Find the tool in our normalized tool table.
        if (job.tool_id, job.tool_version) not in grt_tool_data:
            grt_tool_idx = len(grt_tool_data)
            grt_tool_data.append((job.tool_id, job.tool_version))
        else:
            grt_tool_idx = grt_tool_data.index((job.tool_id, job.tool_version))

        metrics = kw_metrics(job)

        wanted_metrics = ('cpuinfo_cores_allocated', 'core_runtime_seconds')

        grt_metrics = {
            k: int(metrics.get(k, 0))
            for k in wanted_metrics
        }

        job_data = {
            'tool': grt_tool_idx,
            'date': job.update_time.strftime('%s'),
            'metrics': grt_metrics,
        }
        grt_jobs_data.append(job_data)


    grt_report_data = {
        'meta': {
            'version': 1,
            'instance_uuid': args.instance_id,
            'instance_api_key': args.api_key,
            # We do not record ANYTHING about your users other than count.
            'active_users': len(set(active_users)),
            'total_users': sa_session.query(model.User).count(),
            'recent_jobs': len(jobs),
            'days': args.days,
        },
        'tools': [
            {
                'tool_id': a,
                'tool_version': b,
            }
            for (a, b) in grt_tool_data
        ],
        'jobs': grt_jobs_data,
    }

    if args.dryrun:
        print json.dumps(grt_report_data, indent=2)
    else:
        try:
            req = urllib2.urlopen(args.grt_url, data=json.dumps(grt_report_data))
        except urllib2.HTTPError, htpe:
            print htpe.reason
            print htpe.read()
