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
import subprocess
import sys
import time
import yaml
import logging
# logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

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


def _init(config, need_app=False):
    if config.startswith('/'):
        config_file = os.path.abspath(config)
    else:
        config_file = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, config))

    properties = load_app_properties(ini_file=config_file)
    config = galaxy.config.Configuration(**properties)
    object_store = build_object_store_from_config(config)
    if not config.database_connection:
        logging.warning("The database connection is empty. If you are using the default value, please uncomment that in your galaxy.ini")

    if need_app:
        app = galaxy.app.UniverseApplication(global_conf={'__file__': config_file, 'here': os.getcwd()}),
    else:
        app = None

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
        app
    )


def kw_metrics(job):
    return {
        '%s_%s' % (metric.plugin, metric.metric_name): metric.metric_value
        for metric in job.metrics
    }


class Sanitization:

    def __init__(self, sanitization_config, model, sa_session):
        self.sanitization_config = sanitization_config
        # SA Stuff
        self.model = model
        self.sa_session = sa_session
        self.filesize_cache = {}

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

    def _file_dict(self, data):
        key = '{src}-{id}'.format(**data)
        if key in self.filesize_cache:
            return self.filesize_cache[data]
        if data['src'] == 'hda':
            try:
                dataset = self.sa_session.query(self.model.Dataset.id, self.model.Dataset.total_size) \
                        .filter_by(id=data['id']) \
                        .first()
                if dataset and dataset[1]:
                    data['size'] = int(dataset[1])
                else:
                    data['size'] = None
            except sa.orm.exc.NoResultFound:
                data['size'] = None

            # Push to cache for later.
            self.filesize_cache[data['id']] = data
            return data
        else:
            raise Exception("Cannot handle {src} yet".format(data))


    def _sanitize_dict(self, unsanitized_dict, path=""):
        # if it is a file dictionary, handle specially.
        if len(unsanitized_dict.keys()) == 2 and \
                'id' in unsanitized_dict and \
                'src' in unsanitized_dict and \
                unsanitized_dict['src'] in ('hda', 'ldda'):
            return self._file_dict(unsanitized_dict)

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
    logging.getLogger().setLevel(getattr(logging, args.loglevel.upper()))

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
    REPORT_IDENTIFIER = str(time.time())
    REPORT_BASE = os.path.join(ARCHIVE_DIR, REPORT_IDENTIFIER)

    if os.path.exists(CHECK_POINT_FILE):
        with open(CHECK_POINT_FILE, 'r') as handle:
            last_job_sent = int(handle.read())
    else:
        last_job_sent = -1

    logging.info('Loading Galaxy...')
    model, object_store, engine, gxconfig, app = _init(config['galaxy_config'], need_app=config['grt']['share_toolbox'])

    sa_session = model.context.current
    logging.info('Configuration Loaded')
    _times.append(('gx_conf_loaded', time.time() - _start_time))

    # Fetch jobs COMPLETED with status OK that have not yet been sent.

    # Set up our arrays
    active_users = defaultdict(int)
    grt_jobs_data = []

    logging.info('Building Sanitizer')
    _times.append(('san_init', time.time() - _start_time))
    san = Sanitization(config['blacklist'], model, sa_session)
    _times.append(('san_fin', time.time() - _start_time))

    logging.info('Loading Jobs')
    _times.append(('job_init', time.time() - _start_time))

    # Batch the database queries to improve the performance.
    # Get the maximum value.
    max_job_id = sa_session.query(model.Job.id) \
        .filter(model.Job.id > last_job_sent) \
        .order_by(model.Job.id.desc()) \
        .first()[0]

    for selection_start in range(last_job_sent, max_job_id + 1, 1000):
        logging.info("Processing %s - %s", selection_start, selection_start + 1000)
        _processing_times = []
        # For every job
        for job in sa_session.query(model.Job)\
                .filter(sa.and_(
                    model.Job.table.c.state == "ok",
                    model.Job.table.c.id > selection_start,
                    model.Job.table.c.id < selection_start + 1000
                ))\
                .order_by(model.Job.table.c.id.asc())\
                .all():
            if job.id % 100 == 0:
                logging.info(str(job.id))

            _job_start_time = time.time()
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
            _processing_times.append(time.time() - _job_start_time)
        logging.info('Min %s', min(_processing_times))
        logging.info('Max %s', max(_processing_times))
        logging.info('Avg %s', sum(t / len(_processing_times) for t in _processing_times))
    _times.append(('job_fin', time.time() - _start_time))

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

    with gzip.open(REPORT_BASE + '.tsv.gz', 'w') as handle:
        for job in grt_jobs_data:
            handle.write('\t'.join(job))
            handle.write('\n')
    _times.append(('job_finish', time.time() - _start_time))
    sha = subprocess.check_output(['sha256sum', REPORT_BASE + '.tsv.gz'])
    _times.append(('hash_finish', time.time() - _start_time))
    # Strip out to space
    sha = sha[0:sha.index(' ')]

    # Now serialize the individual report data.
    with open(REPORT_BASE + '.json', 'w') as handle:
        if config['grt']['share_toolbox']:
            toolbox = [
                (tool.id, tool.name, tool.version, tool.tool_shed, tool.repository_id, tool.repository_name)
                for tool_id, tool in app.toolbox._tools_by_id.items()
            ]
        else:
            toolbox = None

        json.dump({
            "version": 1,
            "galaxy_version": gxconfig.version_major,
            "generated": REPORT_IDENTIFIER,
            "report_hash": "sha256:" + sha,
            "metrics": {
                "_times": _times,
            },
            "users": {
                "active": len(set(active_users)),
                "total": sa_session.query(model.User.id).count(),
            },
            "jobs": {
                "ok": len(grt_jobs_data),
            },
            "tools": toolbox
        }, handle)

    # update our checkpoint
    with open(CHECK_POINT_FILE, 'w') as handle:
        handle.write(str(last_job_sent))


if __name__ == '__main__':
    main(sys.argv)
