#!/usr/bin/env python
"""Script for parsing Galaxy job information in preparation for submission to the Galactic radio telescope.

See doc/source/admin/grt.rst for more detailed usage information.
"""
from __future__ import print_function

import argparse
import gzip
import json
import os
import sqlalchemy as sa
import sys
import time
import yaml
import logging

from collections import defaultdict

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, 'lib')))

from galaxy.util.properties import load_app_properties
import galaxy
import galaxy.config
from galaxy.objectstore import build_object_store_from_config
from galaxy.model import mapping

sample_config = os.path.abspath(os.path.join(os.path.dirname(__file__), 'grt.yml.sample'))
default_config = os.path.abspath(os.path.join(os.path.dirname(__file__), 'grt.yml'))


def dumper(obj):
    try:
        return obj.toJSON()
    except AttributeError:
        if obj.__class__.__name__ == 'Decimal':
            return str(obj)


def _init(config):
    if config.startswith('/'):
        config_file = os.path.abspath(config)
    else:
        config_file = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, config))

    properties = load_app_properties(ini_file=config_file)
    config = galaxy.config.Configuration(**properties)
    object_store = build_object_store_from_config(config)
    if not config.database_connection:
        logging.warning("The database connection is empty. If you are using the default value, please uncomment that in your galaxy.ini")

    return (
        mapping.init(
            config.file_path,
            config.database_connection,
            create_tables=False,
            object_store=object_store
        ),
        object_store,
        config.database_connection.split(':')[0],
        config,
        galaxy.app.UniverseApplication(global_conf={'__file__': config_file, 'here': os.getcwd()}),
    )


def kw_metrics(job):
    return {
        '%s_%s' % (metric.plugin, metric.metric_name): metric.metric_value
        for metric in job.metrics
    }


class Sanitization:

    def __init__(self, sanitization_config):
        self.sanitization_config = sanitization_config

        if 'tool_params' not in self.sanitization_config:
            self.sanitization_config['tool_params'] = {}

        if '__any__' not in self.sanitization_config['tool_params']:
            self.sanitization_config['tool_params']['__any__'] = []

    def blacklisted_tree(self, path):
        if path.lstrip('.') in self.sanitization_config['tool_params']['__any__']:
            return True
        elif self.tool_id in self.sanitization_config['tool_params']:
            if path.lstrip('.') in self.sanitization_config['tool_params'][self.tool_id]:
                return True
        return False

    def sanitize_data(self, tool_id, data):
        self.tool_id = tool_id
        return self._sanitize_value(data)

    def _sanitize_dict(self, unsanitized_dict, path=""):
        return {
            k: self._sanitize_value(v, path=path + '.' + k)
            for (k, v)
            in unsanitized_dict.items()
        }

    def _sanitize_list(self, unsanitized_list, path=""):
        return [
            self._sanitize_value(v, path=path + '.*')
            for v in unsanitized_list
        ]

    def _sanitize_value(self, unsanitized_value, path=""):
        logging.debug("%sSAN %s" % ('  ' * path.count('.'), unsanitized_value))
        if self.blacklisted_tree(path):
            logging.debug("%sSAN ***REDACTED***" % ('  ' * path.count('.')))
            return None

        if type(unsanitized_value) is dict:
            return self._sanitize_dict(unsanitized_value, path=path)
        elif type(unsanitized_value) is list:
            return self._sanitize_list(unsanitized_value, path=path)
        else:
            logging.debug("%s> Sanitizing %s = %s" % ('  ' * path.count('.'), path, unsanitized_value))
            return unsanitized_value


def main(argv):
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-r', '--report-directory', help='Directory to store reports in',
                        default=os.path.abspath(os.path.join('.', 'reports')))
    parser.add_argument('-c', '--config', help='Path to GRT config file',
                        default=default_config)
    parser.add_argument("-l", "--loglevel", choices=['debug', 'info', 'warning', 'error', 'critical'],
                        help="Set the logging level", default='warning')

    args = parser.parse_args()
    logging.basicConfig(level=getattr(logging, args.loglevel.upper()))

    _times = []
    _start_time = time.time()
    logging.info('Loading GRT ini...')
    try:
        with open(args.config) as handle:
            config = yaml.load(handle)
    except Exception:
        logging.info('Using default GRT Configuration')
        with open(sample_config) as handle:
            config = yaml.load(handle)
    _times.append(('conf_loaded', time.time() - _start_time))

    REPORT_DIR = args.report_directory
    CHECK_POINT_FILE = os.path.join(REPORT_DIR, '.checkpoint')
    ARCHIVE_DIR = os.path.join(REPORT_DIR, 'archives')
    METADATA_FILE = os.path.join(REPORT_DIR, 'meta.json')
    REPORT_IDENTIFIER = str(time.time())
    REPORT_BASE = os.path.join(ARCHIVE_DIR, REPORT_IDENTIFIER)

    if os.path.exists(CHECK_POINT_FILE):
        with open(CHECK_POINT_FILE, 'r') as handle:
            last_job_sent = int(handle.read())
    else:
        last_job_sent = -1

    logging.info('Loading Galaxy...')
    model, object_store, engine, gxconfig, app = _init(config['galaxy_config'])

    sa_session = model.context.current
    _times.append(('gx_conf_loaded', time.time() - _start_time))

    # Fetch jobs COMPLETED with status OK that have not yet been sent.

    # Set up our arrays
    active_users = defaultdict(int)
    grt_jobs_data = []

    san = Sanitization(config['blacklist'])

    # For every job
    for job in sa_session.query(model.Job)\
            .filter(sa.and_(
                model.Job.table.c.state == "ok",
                model.Job.table.c.id > last_job_sent
            ))\
            .order_by(model.Job.table.c.id.asc())\
            .all():
        if job.tool_id in config['blacklist'].get('tools', []):
            continue

        # If the user has run a job, they're active.
        active_users[job.user_id] += 1

        metrics = kw_metrics(job)

        params = job.raw_param_dict()
        for key in params:
            params[key] = json.loads(params[key])

        logging.debug("Sanitizing %s %s" % (job.tool_id, str(params)))
        job_data = (
            str(job.id),
            job.tool_id,
            job.tool_version,
            job.update_time.strftime('%s'),
            json.dumps(metrics, default=dumper),
            json.dumps(san.sanitize_data(job.tool_id, params))
        )
        grt_jobs_data.append(job_data)
    _times.append(('jobs_parsed', time.time() - _start_time))

    # Remember the last job sent.
    if len(grt_jobs_data) > 0:
        last_job_sent = job.id
    else:
        logging.info("No new jobs to report")

    # Now on to outputs.
    if not os.path.exists(REPORT_DIR):
        os.makedirs(REPORT_DIR)
        os.makedirs(ARCHIVE_DIR)

    if os.path.exists(REPORT_DIR) and not os.path.exists(ARCHIVE_DIR):
        os.makedirs(ARCHIVE_DIR)

    with open(METADATA_FILE, 'w') as handle:
        json.dump(config['grt']['metadata'], handle, indent=2)

    _times.append(('job_meta', time.time() - _start_time))
    with gzip.open(REPORT_BASE + '.tsv.gz', 'w') as handle:
        for job in grt_jobs_data:
            handle.write('\t'.join(job))
            handle.write('\n')
    _times.append(('job_finish', time.time() - _start_time))

    # Now serialize the individual report data.
    with open(REPORT_BASE + '.json', 'w') as handle:
        json.dump({
            "version": 1,
            "galaxy_version": gxconfig.version_major,
            "generated": REPORT_IDENTIFIER,
            "metrics": {
                "_times": _times,
            },
            "users": {
                "active": len(set(active_users)),
                "total": sa_session.query(model.User).count(),
            },
            "jobs": {
                "ok": len(grt_jobs_data),
            },
            "tools": [
                (tool.name, tool.version, tool.tool_shed, tool.repository_id, tool.repository_name)
                for tool_id, tool in app.toolbox._tools_by_id.items()
            ]
        }, handle)

    # update our checkpoint
    with open(CHECK_POINT_FILE, 'w') as handle:
        handle.write(str(last_job_sent))


if __name__ == '__main__':
    main(sys.argv)
