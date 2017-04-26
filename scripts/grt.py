#!/usr/bin/env python
"""Script for uploading Galaxy statistics to the Galactic radio telescope.

See doc/source/admin/grt.rst for more detailed usage information.
"""
from __future__ import print_function

import os
import sys
import json
import urllib2
import argparse
import sqlalchemy as sa
import yaml
import re

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, 'lib')))

from galaxy.util.properties import load_app_properties
import galaxy.config
from galaxy.objectstore import build_object_store_from_config
from galaxy.model import mapping

sample_config = os.path.abspath(os.path.join(os.path.dirname(__file__), 'grt.yml.sample'))
default_config = os.path.abspath(os.path.join(os.path.dirname(__file__), 'grt.yml'))


def _init(config):
    if config.startswith('/'):
        config = os.path.abspath(config)
    else:
        config = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, config))

    properties = load_app_properties(ini_file=config)
    config = galaxy.config.Configuration(**properties)
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


def _sanitize_dict(unsanitized_dict):
    sanitized_dict = dict()

    for key in unsanitized_dict:
        if key == 'values' and type(unsanitized_dict[key]) is list:
            sanitized_dict[key] = None
        else:
            sanitized_dict[key] = _sanitize_value(unsanitized_dict[key])

        if sanitized_dict[key] is None:
            del sanitized_dict[key]

    if len(sanitized_dict) == 0:
        return None
    else:
        return sanitized_dict


def _sanitize_list(unsanitized_list):
    sanitized_list = list()

    for key in range(len(unsanitized_list)):
        sanitized_value = _sanitize_value(unsanitized_list[key])
        if not None:
            sanitized_list.append(sanitized_value)

    if len(sanitized_list) == 0:
        return None
    else:
        return sanitized_list


def _sanitize_value(unsanitized_value):
    sanitized_value = None

    fp_regex = re.compile('^(\/[^\/]+)+$')

    if type(unsanitized_value) is dict:
        sanitized_value = _sanitize_dict(unsanitized_value)
    elif type(unsanitized_value) is list:
        sanitized_value = _sanitize_list(unsanitized_value)
    else:
        if fp_regex.match(str(unsanitized_value)):
            sanitized_value = None
        else:
            sanitized_value = unsanitized_value

    return sanitized_value


def main(argv):
    """Entry point for GRT statistics collection."""
    parser = argparse.ArgumentParser()
    parser.add_argument('instance_id', help='Galactic Radio Telescope Instance ID')
    parser.add_argument('api_key', help='Galactic Radio Telescope API Key')

    parser.add_argument('-c', '--config', dest='config', help='Path to GRT config file (scripts/grt.ini)', default=default_config)
    parser.add_argument('--dry-run', dest='dryrun', help='Dry run (show data to be sent, but do not send)', action='store_true', default=False)
    parser.add_argument('--grt-url', dest='grt_url', help='GRT Server (You can run your own!)')
    args = parser.parse_args(argv[1:])

    print('Loading GRT ini...')
    try:
        with open(args.config) as f:
            config_dict = yaml.load(f)
    except Exception:
        with open(sample_config) as f:
            config_dict = yaml.load(f)

    # set to 0 by default
    if 'last_job_id_sent' not in config_dict:
        config_dict['last_job_id_sent'] = 0

    if args.instance_id:
        config_dict['instance_id'] = args.instance_id
    if args.api_key:
        config_dict['api_key'] = args.api_key
    if args.grt_url:
        config_dict['grt_url'] = args.grt_url

    print('Loading Galaxy...')
    model, object_store, engine = _init(config_dict['galaxy_config'])
    sa_session = model.context.current

    # Fetch jobs COMPLETED with status OK that have not yet been sent.
    jobs = sa_session.query(model.Job)\
        .filter(sa.and_(
            model.Job.table.c.state == "ok",
            model.Job.table.c.id > config_dict['last_job_id_sent']
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
        if job.tool_id in config_dict['tool_blacklist']:
            continue

        # Append an active user, we'll reduce at the end
        active_users.append(job.user_id)

        # Find the tool in our normalized tool table.
        if (job.tool_id, job.tool_version) not in grt_tool_data:
            grt_tool_idx = len(grt_tool_data)
            grt_tool_data.append((job.tool_id, job.tool_version))
        else:
            grt_tool_idx = grt_tool_data.index((job.tool_id, job.tool_version))

        metrics = kw_metrics(job)

        wanted_metrics = ('core_galaxy_slots', 'core_runtime_seconds')

        grt_metrics = {
            k: int(metrics.get(k, 0))
            for k in wanted_metrics
        }

        params = job.raw_param_dict()
        for key in params:
            params[key] = json.loads(params[key])

        job_data = {
            'tool': grt_tool_idx,
            'date': job.update_time.strftime('%s'),
            'metrics': grt_metrics,
            'params': _sanitize_dict(params)
        }
        grt_jobs_data.append(job_data)

    if len(jobs) > 0:
        config_dict['last_job_id_sent'] = jobs[-1].id

    grt_report_data = {
        'meta': {
            'version': 1,
            'instance_uuid': config_dict['instance_id'],
            'instance_api_key': config_dict['api_key'],
            # We do not record ANYTHING about your users other than count.
            'active_users': len(set(active_users)),
            'total_users': sa_session.query(model.User).count(),
            'recent_jobs': len(jobs),
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
        print(json.dumps(grt_report_data, indent=2))
    else:
        try:
            urllib2.urlopen(config_dict['grt_url'], data=json.dumps(grt_report_data))
        except urllib2.HTTPError as htpe:
            print(htpe.read())
            exit(1)

        # Update grt.ini with last id of job (prevent duplicates from being sent)
        with open(args.config, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False)


if __name__ == '__main__':
    main(sys.argv)
