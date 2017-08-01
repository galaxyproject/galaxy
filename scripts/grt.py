#!/usr/bin/env python
"""Script for parsing Galaxy job information in preparation for submission to the Galactic radio telescope.

See doc/source/admin/grt.rst for more detailed usage information.
"""
from __future__ import print_function

import argparse
import gzip
import tarfile
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
    # parser.add_argument("-m", "--max-batch", type=int, min=1, help="The maximum number of records to be exported in a single invocation of GRT.")

    args = parser.parse_args()
    logging.getLogger().setLevel(getattr(logging, args.loglevel.upper()))

    _times = []
    _start_time = time.time()
    def annotate(label, human_label=None):
        if human_label:
            logging.info(human_label)
        _times.append((label, time.time() - _start_time))

    annotate('init_start', 'Loading GRT ini...')
    try:
        with open(args.config) as handle:
            config = yaml.load(handle)
    except Exception:
        logging.info('Using default GRT Configuration')
        with open(sample_config) as handle:
            config = yaml.load(handle)
    annotate('init_end')

    REPORT_DIR = args.report_directory
    CHECK_POINT_FILE = os.path.join(REPORT_DIR, '.checkpoint')
    REPORT_IDENTIFIER = str(time.time())
    REPORT_BASE = os.path.join(REPORT_DIR, REPORT_IDENTIFIER)

    if os.path.exists(CHECK_POINT_FILE):
        with open(CHECK_POINT_FILE, 'r') as handle:
            last_job_sent = int(handle.read())
    else:
        last_job_sent = -1

    annotate('galaxy_init', 'Loading Galaxy...')
    model, object_store, engine, gxconfig, app = _init(config['galaxy_config'], need_app=config['grt']['share_toolbox'])
    sa_session = model.context.current
    annotate('galaxy_end')

    # Fetch jobs COMPLETED with status OK that have not yet been sent.

    # Set up our arrays
    active_users = defaultdict(int)
    grt_jobs_data = []

    annotate('san_init', 'Building Sanitizer')
    san = Sanitization(config['blacklist'], model, sa_session)
    annotate('san_end')

    if not os.path.exists(REPORT_DIR):
        os.makedirs(REPORT_DIR)


    # Pick an end point so our queries can return uniform data.
    annotate('endpoint_start', 'Identifying a safe endpoint for SQL queries')
    end_job_id = sa_session.query(model.Job.id) \
        .order_by(model.Job.id.desc()) \
        .first()[0]
    annotate('endpoint_end')

    annotate('export_jobs_start', 'Exporting Jobs')
    handle_job = open(REPORT_BASE + '.jobs.tsv', 'w')
    for job in sa_session.query(model.Job.id, model.Job.tool_id, model.Job.state) \
            .filter(model.Job.id > last_job_sent) \
            .filter(model.Job.id <= end_job_id) \
            .all():

        handle_job.write(str(job[0]))
        handle_job.write('\t')
        handle_job.write(job[1])
        handle_job.write('\n')
    handle_job.close()
    annotate('export_jobs_end')


    annotate('export_metric_num_start', 'Exporting Metrics (Numeric)')
    handle_metric_num = open(REPORT_BASE + '.metric_num.tsv', 'w')
    for metric in sa_session.query(model.JobMetricNumeric.job_id, model.JobMetricNumeric.plugin, model.JobMetricNumeric.metric_name, model.JobMetricNumeric.metric_value) \
            .filter(model.JobMetricNumeric.job_id > last_job_sent) \
            .filter(model.JobMetricNumeric.job_id <= end_job_id) \
            .all():

        handle_metric_num.write(str(metric[0]))
        handle_metric_num.write('\t')
        handle_metric_num.write(metric[1])
        handle_metric_num.write('\t')
        handle_metric_num.write(metric[2])
        handle_metric_num.write('\t')
        handle_metric_num.write(str(metric[3]))
        handle_metric_num.write('\n')
    handle_metric_num.close()
    annotate('export_metric_num_end')


    annotate('export_metric_txt_start', 'Exporting Metrics (Text)')
    handle_metric_txt = open(REPORT_BASE + '.metric_txt.tsv', 'w')
    for metric in sa_session.query(model.JobMetricText.job_id, model.JobMetricText.plugin, model.JobMetricText.metric_name, model.JobMetricText.metric_value) \
            .filter(model.JobMetricText.job_id > last_job_sent) \
            .filter(model.JobMetricText.job_id <= end_job_id) \
            .all():

        handle_metric_txt.write(str(metric[0]))
        handle_metric_txt.write('\t')
        handle_metric_txt.write(metric[1])
        handle_metric_txt.write('\t')
        handle_metric_txt.write(metric[2])
        handle_metric_txt.write('\t')
        handle_metric_txt.write(metric[3])
        handle_metric_txt.write('\n')
    handle_metric_txt.close()
    annotate('export_metric_txt_end')


    # job, metric_text, metric_num, params

    annotate('export_params_start', 'Export Job Parameters')
    handle_params = open(REPORT_BASE + '.params.tsv', 'w')
    for param in sa_session.query(model.JobParameter.job_id, model.JobParameter.name, model.JobParameter.value) \
            .filter(model.JobParameter.job_id > last_job_sent) \
            .filter(model.JobParameter.job_id <= end_job_id) \
            .all():

        handle_params.write(str(param[0]))
        handle_params.write('\t')
        handle_params.write(param[1])
        handle_params.write('\t')
        handle_params.write(param[2])
        handle_params.write('\n')
    handle_params.close()
    annotate('export_params_end')

    # Remember the last job sent.
    if len(grt_jobs_data) > 0:
        last_job_sent = job.id
    else:
        logging.info("No new jobs to report")

    # Now on to outputs.

    with tarfile.open(REPORT_BASE + '.tar.gz', 'w:gz') as handle:
        for name in ('jobs', 'metric_num', 'metric_txt', 'params'):
            handle.add(REPORT_BASE + '.' + name + '.tsv')

    _times.append(('job_finish', time.time() - _start_time))
    sha = subprocess.check_output(['sha256sum', REPORT_BASE + '.tar.gz'])
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
