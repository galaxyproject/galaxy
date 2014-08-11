import os
from json import dumps

from .destination import submit_params
from .setup_handler import build as build_setup_handler
from .job_directory import RemoteJobDirectory
from .decorators import parseJson
from .decorators import retry
from .util import copy
from .util import ensure_directory
from .util import to_base64_json


import logging
log = logging.getLogger(__name__)

CACHE_WAIT_SECONDS = 3


class OutputNotFoundException(Exception):

    def __init__(self, path):
        self.path = path

    def __str__(self):
        return "No remote output found for path %s" % self.path


class BaseJobClient(object):

    def __init__(self, destination_params, job_id):
        self.destination_params = destination_params
        self.job_id = job_id
        if "jobs_directory" in (destination_params or {}):
            staging_directory = destination_params["jobs_directory"]
            sep = destination_params.get("remote_sep", os.sep)
            job_directory = RemoteJobDirectory(
                remote_staging_directory=staging_directory,
                remote_id=job_id,
                remote_sep=sep,
            )
        else:
            job_directory = None
        self.env = destination_params.get("env", [])
        self.files_endpoint = destination_params.get("files_endpoint", None)
        self.job_directory = job_directory

        self.default_file_action = self.destination_params.get("default_file_action", "transfer")
        self.action_config_path = self.destination_params.get("file_action_config", None)

        self.setup_handler = build_setup_handler(self, destination_params)

    def setup(self, tool_id=None, tool_version=None):
        """
        Setup remote LWR server to run this job.
        """
        setup_args = {"job_id": self.job_id}
        if tool_id:
            setup_args["tool_id"] = tool_id
        if tool_version:
            setup_args["tool_version"] = tool_version
        return self.setup_handler.setup(**setup_args)

    @property
    def prefer_local_staging(self):
        # If doing a job directory is defined, calculate paths here and stage
        # remotely.
        return self.job_directory is None


class JobClient(BaseJobClient):
    """
    Objects of this client class perform low-level communication with a remote LWR server.

    **Parameters**

    destination_params : dict or str
        connection parameters, either url with dict containing url (and optionally `private_token`).
    job_id : str
        Galaxy job/task id.
    """

    def __init__(self, destination_params, job_id, job_manager_interface):
        super(JobClient, self).__init__(destination_params, job_id)
        self.job_manager_interface = job_manager_interface

    def launch(self, command_line, dependencies_description=None, env=[], remote_staging=[], job_config=None):
        """
        Queue up the execution of the supplied `command_line` on the remote
        server. Called launch for historical reasons, should be renamed to
        enqueue or something like that.

        **Parameters**

        command_line : str
            Command to execute.
        """
        launch_params = dict(command_line=command_line, job_id=self.job_id)
        submit_params_dict = submit_params(self.destination_params)
        if submit_params_dict:
            launch_params['params'] = dumps(submit_params_dict)
        if dependencies_description:
            launch_params['dependencies_description'] = dumps(dependencies_description.to_dict())
        if env:
            launch_params['env'] = dumps(env)
        if remote_staging:
            launch_params['remote_staging'] = dumps(remote_staging)
        if job_config and self.setup_handler.local:
            # Setup not yet called, job properties were inferred from
            # destination arguments. Hence, must have LWR setup job
            # before queueing.
            setup_params = _setup_params_from_job_config(job_config)
            launch_params["setup_params"] = dumps(setup_params)
        return self._raw_execute("launch", launch_params)

    def full_status(self):
        """ Return a dictionary summarizing final state of job.
        """
        return self.raw_check_complete()

    def kill(self):
        """
        Cancel remote job, either removing from the queue or killing it.
        """
        return self._raw_execute("kill", {"job_id": self.job_id})

    @retry()
    @parseJson()
    def raw_check_complete(self):
        """
        Get check_complete response from the remote server.
        """
        check_complete_response = self._raw_execute("check_complete", {"job_id": self.job_id})
        return check_complete_response

    def get_status(self):
        check_complete_response = self.raw_check_complete()
        # Older LWR instances won't set status so use 'complete', at some
        # point drop backward compatibility.
        status = check_complete_response.get("status", None)
        if status in ["status", None]:
            # LEGACY: Bug in certains older LWR instances returned literal
            # "status".
            complete = check_complete_response["complete"] == "true"
            old_status = "complete" if complete else "running"
            status = old_status
        return status

    def clean(self):
        """
        Cleanup the remote job.
        """
        self._raw_execute("clean", {"job_id": self.job_id})

    @parseJson()
    def remote_setup(self, **setup_args):
        """
        Setup remote LWR server to run this job.
        """
        return self._raw_execute("setup", setup_args)

    def put_file(self, path, input_type, name=None, contents=None, action_type='transfer'):
        if not name:
            name = os.path.basename(path)
        args = {"job_id": self.job_id, "name": name, "input_type": input_type}
        input_path = path
        if contents:
            input_path = None
        if action_type == 'transfer':
            return self._upload_file(args, contents, input_path)
        elif action_type == 'copy':
            lwr_path = self._raw_execute('input_path', args)
            copy(path, lwr_path)
            return {'path': lwr_path}

    def fetch_output(self, path, name, working_directory, action_type, output_type):
        """
        Fetch (transfer, copy, etc...) an output from the remote LWR server.

        **Parameters**

        path : str
            Local path of the dataset.
        name : str
            Remote name of file (i.e. path relative to remote staging output
            or working directory).
        working_directory : str
            Local working_directory for the job.
        action_type : str
            Where to find file on LWR (output_workdir or output). legacy is also
            an option in this case LWR is asked for location - this will only be
            used if targetting an older LWR server that didn't return statuses
            allowing this to be inferred.
        """
        if output_type == 'legacy':
            self._fetch_output_legacy(path, working_directory, action_type=action_type)
        elif output_type == 'output_workdir':
            self._fetch_work_dir_output(name, working_directory, path, action_type=action_type)
        elif output_type == 'output':
            self._fetch_output(path=path, name=name, action_type=action_type)
        else:
            raise Exception("Unknown output_type %s" % output_type)

    def _raw_execute(self, command, args={}, data=None, input_path=None, output_path=None):
        return self.job_manager_interface.execute(command, args, data, input_path, output_path)

    # Deprecated
    def _fetch_output_legacy(self, path, working_directory, action_type='transfer'):
        # Needs to determine if output is task/working directory or standard.
        name = os.path.basename(path)

        output_type = self._get_output_type(name)
        if output_type == "none":
            # Just make sure the file was created.
            if not os.path.exists(path):
                raise OutputNotFoundException(path)
            return
        elif output_type in ["task"]:
            path = os.path.join(working_directory, name)

        self.__populate_output_path(name, path, output_type, action_type)

    def _fetch_output(self, path, name=None, check_exists_remotely=False, action_type='transfer'):
        if not name:
            # Extra files will send in the path.
            name = os.path.basename(path)

        output_type = "direct"  # Task/from_work_dir outputs now handled with fetch_work_dir_output
        self.__populate_output_path(name, path, output_type, action_type)

    def _fetch_work_dir_output(self, name, working_directory, output_path, action_type='transfer'):
        ensure_directory(output_path)
        if action_type == 'transfer':
            self.__raw_download_output(name, self.job_id, "work_dir", output_path)
        else:  # Even if action is none - LWR has a different work_dir so this needs to be copied.
            lwr_path = self._output_path(name, self.job_id, 'work_dir')['path']
            copy(lwr_path, output_path)

    def __populate_output_path(self, name, output_path, output_type, action_type):
        ensure_directory(output_path)
        if action_type == 'transfer':
            self.__raw_download_output(name, self.job_id, output_type, output_path)
        elif action_type == 'copy':
            lwr_path = self._output_path(name, self.job_id, output_type)['path']
            copy(lwr_path, output_path)

    @parseJson()
    def _upload_file(self, args, contents, input_path):
        return self._raw_execute(self._upload_file_action(args), args, contents, input_path)

    def _upload_file_action(self, args):
        # Hack for backward compatibility, instead of using new upload_file
        # path. Use old paths.
        input_type = args['input_type']
        action = {
            # For backward compatibility just target upload_input_extra for all
            # inputs, it allows nested inputs. Want to do away with distinction
            # inputs and extra inputs.
            'input': 'upload_extra_input',
            'config': 'upload_config_file',
            'workdir': 'upload_working_directory_file',
            'tool': 'upload_tool_file',
            'unstructured': 'upload_unstructured_file',
        }[input_type]
        del args['input_type']
        return action

    @parseJson()
    def _get_output_type(self, name):
        return self._raw_execute("get_output_type", {"name": name,
                                                     "job_id": self.job_id})

    @parseJson()
    def _output_path(self, name, job_id, output_type):
        return self._raw_execute("output_path",
                                 {"name": name,
                                  "job_id": self.job_id,
                                  "output_type": output_type})

    @retry()
    def __raw_download_output(self, name, job_id, output_type, output_path):
        output_params = {
            "name": name,
            "job_id": self.job_id,
            "output_type": output_type
        }
        self._raw_execute("download_output", output_params, output_path=output_path)


class BaseMessageJobClient(BaseJobClient):

    def __init__(self, destination_params, job_id, client_manager):
        super(BaseMessageJobClient, self).__init__(destination_params, job_id)
        if not self.job_directory:
            error_message = "Message-queue based LWR client requires destination define a remote job_directory to stage files into."
            raise Exception(error_message)
        self.client_manager = client_manager

    def clean(self):
        del self.client_manager.status_cache[self.job_id]

    def full_status(self):
        full_status = self.client_manager.status_cache.get(self.job_id, None)
        if full_status is None:
            raise Exception("full_status() called before a final status was properly cached with cilent manager.")
        return full_status

    def _build_setup_message(self, command_line, dependencies_description, env, remote_staging, job_config):
        """
        """
        launch_params = dict(command_line=command_line, job_id=self.job_id)
        submit_params_dict = submit_params(self.destination_params)
        if submit_params_dict:
            launch_params['submit_params'] = submit_params_dict
        if dependencies_description:
            launch_params['dependencies_description'] = dependencies_description.to_dict()
        if env:
            launch_params['env'] = env
        if remote_staging:
            launch_params['remote_staging'] = remote_staging
        if job_config and self.setup_handler.local:
            # Setup not yet called, job properties were inferred from
            # destination arguments. Hence, must have LWR setup job
            # before queueing.
            setup_params = _setup_params_from_job_config(job_config)
            launch_params["setup_params"] = setup_params
        return launch_params


class MessageJobClient(BaseMessageJobClient):

    def launch(self, command_line, dependencies_description=None, env=[], remote_staging=[], job_config=None):
        """
        """
        launch_params = self._build_setup_message(
            command_line,
            dependencies_description=dependencies_description,
            env=env,
            remote_staging=remote_staging,
            job_config=job_config
        )
        response = self.client_manager.exchange.publish("setup", launch_params)
        log.info("Job published to setup message queue.")
        return response

    def kill(self):
        self.client_manager.exchange.publish("kill", dict(job_id=self.job_id))


class MessageCLIJobClient(BaseMessageJobClient):

    def __init__(self, destination_params, job_id, client_manager, shell):
        super(MessageCLIJobClient, self).__init__(destination_params, job_id, client_manager)
        self.remote_lwr_path = destination_params["remote_lwr_path"]
        self.shell = shell

    def launch(self, command_line, dependencies_description=None, env=[], remote_staging=[], job_config=None):
        """
        """
        launch_params = self._build_setup_message(
            command_line,
            dependencies_description=dependencies_description,
            env=env,
            remote_staging=remote_staging,
            job_config=job_config
        )
        base64_message = to_base64_json(launch_params)
        submit_command = os.path.join(self.remote_lwr_path, "scripts", "submit.bash")
        # TODO: Allow configuration of manager, app, and ini path...
        self.shell.execute("nohup %s --base64 %s &" % (submit_command, base64_message))

    def kill(self):
        # TODO
        pass


class InputCachingJobClient(JobClient):
    """
    Beta client that cache's staged files to prevent duplication.
    """

    def __init__(self, destination_params, job_id, job_manager_interface, client_cacher):
        super(InputCachingJobClient, self).__init__(destination_params, job_id, job_manager_interface)
        self.client_cacher = client_cacher

    @parseJson()
    def _upload_file(self, args, contents, input_path):
        action = self._upload_file_action(args)
        if contents:
            input_path = None
            return self._raw_execute(action, args, contents, input_path)
        else:
            event_holder = self.client_cacher.acquire_event(input_path)
            cache_required = self.cache_required(input_path)
            if cache_required:
                self.client_cacher.queue_transfer(self, input_path)
            while not event_holder.failed:
                available = self.file_available(input_path)
                if available['ready']:
                    token = available['token']
                    args["cache_token"] = token
                    return self._raw_execute(action, args)
                event_holder.event.wait(30)
            if event_holder.failed:
                raise Exception("Failed to transfer file %s" % input_path)

    @parseJson()
    def cache_required(self, path):
        return self._raw_execute("cache_required", {"path": path})

    @parseJson()
    def cache_insert(self, path):
        return self._raw_execute("cache_insert", {"path": path}, None, path)

    @parseJson()
    def file_available(self, path):
        return self._raw_execute("file_available", {"path": path})


def _setup_params_from_job_config(job_config):
    job_id = job_config.get("job_id", None)
    tool_id = job_config.get("tool_id", None)
    tool_version = job_config.get("tool_version", None)
    return dict(
        job_id=job_id,
        tool_id=tool_id,
        tool_version=tool_version
    )
