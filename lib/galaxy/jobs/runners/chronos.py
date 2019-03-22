from __future__ import absolute_import

import functools
import logging

from galaxy import model
from galaxy.jobs.runners import AsynchronousJobRunner, AsynchronousJobState

CHRONOS_IMPORT_MSG = ('The Python \'chronos\' package is required to use '
                      'this feature, please install it or correct the '
                      'following error:\nImportError {msg!s}')

try:
    import chronos
    chronos_exceptions = (
        chronos.ChronosAPIError,
        chronos.UnauthorizedError,
        chronos.MissingFieldError,
        chronos.OneOfViolationError,
    )
except ImportError as e:
    chronos = None
    CHRONOS_IMPORT_MSG.format(msg=str(e))


__all__ = ('ChronosJobRunner',)
LOGGER = logging.getLogger(__name__)


class ChronosRunnerException(Exception):
    pass


def handle_exception_call(func):
    # Catch chronos exceptions. The latest version of chronos-python does
    # support a hierarchy over the exceptions.

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except chronos_exceptions as e:
            LOGGER.error(str(e))

    return wrapper


def to_dict(segments, v):
    if len(segments) == 0:
        return v
    return {segments[0]: to_dict(segments[1:], v)}


def _write_logfile(logfile, msg):
    with open(logfile, 'w') as fil:
        fil.write(msg)


class ChronosJobRunner(AsynchronousJobRunner):
    runner_name = 'ChronosRunner'
    RUNNER_PARAM_SPEC_KEY = 'runner_param_specs'
    JOB_NAME_PREFIX = 'galaxy-chronos-'

    RUNNER_PARAM_SPEC = {
        'chronos': {
            'map': str,
        },
        'insecure': {
            'map': lambda x: x in ['true', 'True', 'TRUE'],
            'default': True,
        },
        'username': {
            'map': str,
        },
        'password': {
            'map': str,
        },
        'owner': {
            'map': str
        },
    }

    DESTINATION_PARAMS_SPEC = {
        'docker_cpu': {
            'default': 0.1,
            'map_name': 'cpus',
            'map': float,
        },
        'docker_memory': {
            'default': 128,
            'map_name': 'mem',
            'map': int,
        },
        'docker_disk': {
            'default': 256,
            'map_name': 'disk',
            'map': int,
        },
        'volumes': {
            'default': None,
            'map_name': 'container/volumes',
            'map': (
                lambda x: [{'containerPath': x, 'hostPath': x, 'mode': 'RW'}]
                if x is not None else [])
        },
        'max_retries': {
            'default': 2,
            'map_name': 'retries',
            'map': int,
        },
    }

    def __init__(self, app, nworkers, **kwargs):
        """Initialize this job runner and start the monitor thread"""
        assert chronos, CHRONOS_IMPORT_MSG
        if self.RUNNER_PARAM_SPEC_KEY not in kwargs:
            kwargs[self.RUNNER_PARAM_SPEC_KEY] = {}
        kwargs[self.RUNNER_PARAM_SPEC_KEY].update(self.RUNNER_PARAM_SPEC)
        super(ChronosJobRunner, self).__init__(app, nworkers, **kwargs)
        protocol = 'http' if self.runner_params.get('insecure', True) else 'https'
        self._chronos_client = chronos.connect(
            self.runner_params['chronos'],
            username=self.runner_params.get('username'),
            password=self.runner_params.get('password'),
            proto=protocol)
        self._init_monitor_thread()
        self._init_worker_threads()

    @handle_exception_call
    def queue_job(self, job_wrapper):
        LOGGER.debug("Starting queue_job for job " + job_wrapper.get_id_tag())
        if not self.prepare_job(job_wrapper, include_metadata=False,
                                modify_command_for_container=False):
            LOGGER.debug("Not ready " + job_wrapper.get_id_tag())
            return
        job_destination = job_wrapper.job_destination
        chronos_job_spec = self._get_job_spec(job_wrapper)
        job_name = chronos_job_spec['name']
        self._chronos_client.add(chronos_job_spec)
        ajs = AsynchronousJobState(files_dir=job_wrapper.working_directory,
                                   job_wrapper=job_wrapper,
                                   job_id=job_name,
                                   job_destination=job_destination)
        self.monitor_queue.put(ajs)

    @handle_exception_call
    def stop_job(self, job_wrapper):
        job_id = job_wrapper.get_id_tag()
        job_name = self.JOB_NAME_PREFIX + job_id
        job = self._retrieve_job(job_name)
        if job:
            msg = 'Job {name!r} is terminated'
            self._chronos_client.delete(job_name)
            LOGGER.debug(msg.format(name=job_name))
        else:
            msg = 'Job {name!r} not found. It cannot be terminated.'
            LOGGER.error(msg.format(name=job_name))

    def recover(self, job, job_wrapper):
        msg = ('(name!r/runner!r) is still in {state!s} state, adding to'
               ' the runner monitor queue')
        job_id = job.get_job_runner_external_id()
        ajs = AsynchronousJobState(files_dir=job_wrapper.working_directory,
                                   job_wrapper=job_wrapper)
        ajs.job_id = self.JOB_NAME_PREFIX + str(job_id)
        ajs.command_line = job.command_line
        ajs.job_wrapper = job_wrapper
        ajs.job_destination = job_wrapper.job_destination
        if job.state == model.Job.states.RUNNING:
            LOGGER.debug(msg.format(
                name=job.id, runner=job.job_runner_external_id,
                state='running'))
            ajs.old_state = model.Job.states.RUNNING
            ajs.running = True
            self.monitor_queue.put(ajs)
        elif job.state == model.Job.states.QUEUED:
            LOGGER.debug(msg.format(
                name=job.id, runner=job.job_runner_external_id,
                state='queued'))
            ajs.old_state = model.Job.states.QUEUED
            ajs.running = False
            self.monitor_queue.put(ajs)

    @handle_exception_call
    def check_watched_item(self, job_state):
        job_name = job_state.job_id
        job = self._retrieve_job(job_name)
        if job:
            succeeded = job['successCount']
            errors = job['errorCount']
            if succeeded > 0:
                return self._mark_as_successful(job_state)
            elif not succeeded and not errors:
                return self._mark_as_active(job_state)
            elif errors:
                max_retries = job['retries']
                msg = 'Job {name!r} failed more than {retries!s} times'
                reason = msg.format(name=job_name, retries=str(max_retries))
                return self._mark_as_failed(job_state, reason)
        reason = 'Job {name!r} not found'.format(name=job_name)
        return self._mark_as_failed(job_state, reason)

    def _mark_as_successful(self, job_state):
        msg = 'Job {name!r} finished successfully'
        _write_logfile(job_state.output_file,
                       msg.format(name=job_state.job_id))
        _write_logfile(job_state.error_file, '')
        job_state.running = False
        job_state.job_wrapper.change_state(model.Job.states.OK)
        self.mark_as_finished(job_state)
        return None

    def _mark_as_active(self, job_state):
        job_state.running = True
        job_state.job_wrapper.change_state(model.Job.states.RUNNING)
        return job_state

    def _mark_as_failed(self, job_state, reason):
        _write_logfile(job_state.error_file, reason)
        job_state.running = False
        job_state.stop_job = True
        job_state.job_wrapper.change_state(model.Job.states.ERROR)
        job_state.fail_message = reason
        self.mark_as_failed(job_state)
        return None

    @handle_exception_call
    def finish_job(self, job_state):
        super(ChronosJobRunner, self).finish_job(job_state)
        self._chronos_client.delete(job_state.job_id)

    def parse_destination_params(self, params):
        parsed_params = {}
        for k, spec in self.DESTINATION_PARAMS_SPEC.items():
            value = params.get(k, spec.get('default'))
            map_to = spec.get('map_name')
            mapper = spec.get('map')
            segments = map_to.split('/')
            parsed_params.update(to_dict(segments, mapper(value)))
        return parsed_params

    def _get_job_spec(self, job_wrapper):
        job_name = self.JOB_NAME_PREFIX + job_wrapper.get_id_tag()
        job_destination = job_wrapper.job_destination
        template = {
            'async': False,
            'command': job_wrapper.runner_command_line,
            'owner': self.runner_params['owner'],
            'disabled': False,
            'schedule': 'R1//PT1S',
            'name': job_name,
        }
        if not job_destination.params.get('docker_enabled'):
            raise ChronosRunnerException(
                'ChronosJobRunner needs \'docker_enabled\' to be set as True')
        destination_params = self.parse_destination_params(
            job_destination.params)
        template.update(destination_params)
        template['container']['type'] = 'DOCKER'
        template['container']['image'] = self._find_container(
            job_wrapper).container_id
        return template

    def _retrieve_job(self, job_id):
        jobs = self._chronos_client.list()
        job = [x for x in jobs if x['name'] == job_id]
        if len(job) > 1:
            msg = 'Multiple jobs found with name {name!r}'.format(name=job_id)
            LOGGER.error(msg)
            raise ChronosRunnerException(msg)
        return job[0] if job else None
