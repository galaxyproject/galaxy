import os
import shutil
from json import dumps, loads
from time import sleep

from .destination import submit_params

CACHE_WAIT_SECONDS = 3
MAX_RETRY_COUNT = 5
RETRY_SLEEP_TIME = 0.1


class parseJson(object):

    def __call__(self, func):
        def replacement(*args, **kwargs):
            response = func(*args, **kwargs)
            return loads(response)
        return replacement


class retry(object):

    def __call__(self, func):

        def replacement(*args, **kwargs):
            max_count = MAX_RETRY_COUNT
            count = 0
            while True:
                count += 1
                try:
                    return func(*args, **kwargs)
                except:
                    if count >= max_count:
                        raise
                    else:
                        sleep(RETRY_SLEEP_TIME)
                        continue

        return replacement


class OutputNotFoundException(Exception):

    def __init__(self, path):
        self.path = path

    def __str__(self):
        return "No remote output found for path %s" % self.path


class JobClient(object):
    """
    Objects of this client class perform low-level communication with a remote LWR server.

    **Parameters**

    destination_params : dict or str
        connection parameters, either url with dict containing url (and optionally `private_token`).
    job_id : str
        Galaxy job/task id.
    """

    def __init__(self, destination_params, job_id, job_manager_interface):
        self.job_manager_interface = job_manager_interface
        self.destination_params = destination_params
        self.job_id = job_id

        self.default_file_action = self.destination_params.get("default_file_action", "transfer")
        self.action_config_path = self.destination_params.get("file_action_config", None)

    def _raw_execute(self, command, args={}, data=None, input_path=None, output_path=None):
        return self.job_manager_interface.execute(command, args, data, input_path, output_path)

    @property
    def _submit_params(self):
        return submit_params(self.destination_params)

    @parseJson()
    def input_path(self, path, input_type, name=None):
        args = {"job_id": self.job_id, "name": name, "input_type": input_type}
        return self._raw_execute('input_path', args)

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
            self._copy(path, lwr_path)
            return {'path': lwr_path}

    @parseJson()
    def _upload_file(self, args, contents, input_path):
        return self._raw_execute(self._upload_file_action(args), args, contents, input_path)

    def _upload_file_action(self, args):
        ## Hack for backward compatibility, instead of using new upload_file
        ## path. Use old paths.
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

    # Deprecated
    def fetch_output_legacy(self, path, working_directory, action_type='transfer'):
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

    def fetch_output(self, path, name=None, check_exists_remotely=False, action_type='transfer'):
        """
        Download an output dataset from the remote server.

        **Parameters**

        path : str
            Local path of the dataset.
        working_directory : str
            Local working_directory for the job.
        """

        if not name:
            # Extra files will send in the path.
            name = os.path.basename(path)

        output_type = "direct"  # Task/from_work_dir outputs now handled with fetch_work_dir_output
        self.__populate_output_path(name, path, output_type, action_type)

    def __populate_output_path(self, name, output_path, output_type, action_type):
        self.__ensure_directory(output_path)
        if action_type == 'transfer':
            self.__raw_download_output(name, self.job_id, output_type, output_path)
        elif action_type == 'copy':
            lwr_path = self._output_path(name, self.job_id, output_type)['path']
            self._copy(lwr_path, output_path)

    def fetch_work_dir_output(self, name, working_directory, output_path, action_type='transfer'):
        """
        Download an output dataset specified with from_work_dir from the
        remote server.

        **Parameters**

        name : str
            Path in job's working_directory to find output in.
        working_directory : str
            Local working_directory for the job.
        output_path : str
            Full path to output dataset.
        """
        self.__ensure_directory(output_path)
        if action_type == 'transfer':
            self.__raw_download_output(name, self.job_id, "work_dir", output_path)
        else:  # Even if action is none - LWR has a different work_dir so this needs to be copied.
            lwr_path = self._output_path(name, self.job_id, 'work_dir')['path']
            self._copy(lwr_path, output_path)

    def __ensure_directory(self, output_path):
        output_path_directory = os.path.dirname(output_path)
        if not os.path.exists(output_path_directory):
            os.makedirs(output_path_directory)

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

    def launch(self, command_line, requirements=[]):
        """
        Run or queue up the execution of the supplied
        `command_line` on the remote server.

        **Parameters**

        command_line : str
            Command to execute.
        """
        launch_params = dict(command_line=command_line, job_id=self.job_id)
        submit_params = self._submit_params
        if submit_params:
            launch_params['params'] = dumps(submit_params)
        if requirements:
            launch_params['requirements'] = dumps([requirement.to_dict() for requirement in requirements])
        return self._raw_execute("launch", launch_params)

    def kill(self):
        """
        Cancel remote job, either removing from the queue or killing it.
        """
        return self._raw_execute("kill", {"job_id": self.job_id})

    def wait(self):
        """
        Wait for job to finish.
        """
        while True:
            complete_response = self.raw_check_complete()
            if complete_response["complete"] == "true":
                return complete_response
            sleep(1)

    @parseJson()
    def raw_check_complete(self):
        """
        Get check_complete response from the remote server.
        """
        check_complete_response = self._raw_execute("check_complete", {"job_id": self.job_id})
        return check_complete_response

    def check_complete(self, response=None):
        """
        Return boolean indicating whether the job is complete.
        """
        if response is None:
            response = self.raw_check_complete()
        return response["complete"] == "true"

    @retry()
    def get_status(self):
        check_complete_response = self.raw_check_complete()
        # Older LWR instances won't set status so use 'complete', at some
        # point drop backward compatibility.
        complete = self.check_complete(check_complete_response)
        old_status = "complete" if complete else "running"
        status = check_complete_response.get("status", old_status)
        # Bug in certains older LWR instances returned literal "status".
        if status not in ["complete", "running", "queued"]:
            status = old_status
        return status

    def clean(self):
        """
        Cleanup the remote job.
        """
        self._raw_execute("clean", {"job_id": self.job_id})

    @parseJson()
    def setup(self, tool_id=None, tool_version=None):
        """
        Setup remote LWR server to run this job.
        """
        setup_args = {"job_id": self.job_id}
        if tool_id:
            setup_args["tool_id"] = tool_id
        if tool_version:
            setup_args["tool_version"] = tool_version
        return self._raw_execute("setup", setup_args)

    def _copy(self, source, destination):
        source = os.path.abspath(source)
        destination = os.path.abspath(destination)
        if source != destination:
            shutil.copyfile(source, destination)


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


class ObjectStoreClient(object):

    def __init__(self, lwr_interface):
        self.lwr_interface = lwr_interface

    @parseJson()
    def exists(self, **kwds):
        return self._raw_execute("object_store_exists", args=self.__data(**kwds))

    @parseJson()
    def file_ready(self, **kwds):
        return self._raw_execute("object_store_file_ready", args=self.__data(**kwds))

    @parseJson()
    def create(self, **kwds):
        return self._raw_execute("object_store_create", args=self.__data(**kwds))

    @parseJson()
    def empty(self, **kwds):
        return self._raw_execute("object_store_empty", args=self.__data(**kwds))

    @parseJson()
    def size(self, **kwds):
        return self._raw_execute("object_store_size", args=self.__data(**kwds))

    @parseJson()
    def delete(self, **kwds):
        return self._raw_execute("object_store_delete", args=self.__data(**kwds))

    @parseJson()
    def get_data(self, **kwds):
        return self._raw_execute("object_store_get_data", args=self.__data(**kwds))

    @parseJson()
    def get_filename(self, **kwds):
        return self._raw_execute("object_store_get_filename", args=self.__data(**kwds))

    @parseJson()
    def update_from_file(self, **kwds):
        return self._raw_execute("object_store_update_from_file", args=self.__data(**kwds))

    @parseJson()
    def get_store_usage_percent(self):
        return self._raw_execute("object_store_get_store_usage_percent", args={})

    def __data(self, **kwds):
        return kwds

    def _raw_execute(self, command, args={}):
        return self.lwr_interface.execute(command, args, data=None, input_path=None, output_path=None)
