import os
import time
import urllib
import simplejson

from .transport import get_transport
from .destination import url_to_destination_params


class parseJson(object):

    def __init__(self):
        pass

    def __call__(self, func):
        def replacement(*args, **kwargs):
            response = func(*args, **kwargs)
            return simplejson.loads(response)
        return replacement


class OutputNotFoundException(Exception):

    def __init__(self, path):
        self.path = path

    def __str__(self):
        return "No remote output found for path %s" % self.path


class Client(object):
    """
    Objects of this client class perform low-level communication with a remote LWR server.

    **Parameters**

    destination_params : dict or str
        connection parameters, either url with dict containing url (and optionally `private_token`).
    job_id : str
        Galaxy job/task id.
    """

    def __init__(self, destination_params, job_id, transport_type=None):
        if isinstance(destination_params, str) or isinstance(destination_params, unicode):
            destination_params = url_to_destination_params(destination_params)
        self.remote_host = destination_params.get("url")
        assert self.remote_host != None, "Failed to determine url for LWR client."
        self.private_key = destination_params.get("private_token", None)
        self.job_id = job_id
        self.transport = get_transport(transport_type)

    def __build_url(self, command, args):
        if self.private_key:
            args["private_key"] = self.private_key
        data = urllib.urlencode(args)
        url = self.remote_host + command + "?" + data
        return url

    def __raw_execute(self, command, args={}, data=None, input_path=None, output_path=None):
        url = self.__build_url(command, args)
        response = self.transport.execute(url, data=data, input_path=input_path, output_path=output_path)
        return response

    @parseJson()
    def __upload_file(self, action, path, name=None, contents=None):
        if not name:
            name = os.path.basename(path)
        args = {"job_id": self.job_id, "name": name}
        input_path = path
        if contents:
            input_path = None
        return self.__raw_execute(action, args, contents, input_path)

    def upload_tool_file(self, path):
        """
        Upload a tool related file (e.g. wrapper) required to run job.

        **Parameters**

        path : str
            Local path tool.
        """
        return self.__upload_file("upload_tool_file", path)

    def upload_input(self, path):
        """
        Upload input dataset to remote server.

        **Parameters**

        path : str
            Local path of input dataset.
        """
        return self.__upload_file("upload_input", path)

    def upload_extra_input(self, path, relative_name):
        """
        Upload extra input file to remote server.

        **Parameters**

        path : str
            Extra files path of input dataset corresponding to this input.
        relative_name : str
            Relative path of extra file to upload relative to inputs extra files path.
        """
        return self.__upload_file("upload_extra_input", path, name=relative_name)

    def upload_config_file(self, path, contents):
        """
        Upload a job's config file to the remote server.

        **Parameters**

        path : str
            Local path to the original config file.
        contents : str
            Rewritten contents of the config file to upload.
        """
        return self.__upload_file("upload_config_file", path, contents=contents)

    def upload_working_directory_file(self, path):
        """
        Upload the supplied file (path) from a job's working directory
        to remote server.

        **Parameters**

        path : str
            Path to file to upload.
        """
        return self.__upload_file("upload_working_directory_file", path)

    @parseJson()
    def _get_output_type(self, name):
        return self.__raw_execute("get_output_type", {"name": name,
                                                      "job_id": self.job_id})

    def download_work_dir_output(self, source, working_directory, output_path):
        """
        Download an output dataset specified with from_work_dir from the
        remote server.

        **Parameters**

        source : str
            Path in job's working_directory to find output in.
        working_directory : str
            Local working_directory for the job.
        output_path : str
            Full path to output dataset.
        """
        output = open(output_path, "wb")
        name = os.path.basename(source)
        self.__raw_download_output(name, self.job_id, "work_dir", output)

    def download_output(self, path, working_directory):
        """
        Download an output dataset from the remote server.

        **Parameters**

        path : str
            Local path of the dataset.
        working_directory : str
            Local working_directory for the job.
        """
        name = os.path.basename(path)
        output_type = self._get_output_type(name)
        if output_type == "direct":
            output_path = path
        elif output_type == "task":
            output_path = os.path.join(working_directory, name)
        else:
            raise OutputNotFoundException(path)
        self.__raw_download_output(name, self.job_id, output_type, output_path)

    def __raw_download_output(self, name, job_id, output_type, output_path):
        self.__raw_execute("download_output",
                           {"name": name,
                            "job_id": self.job_id,
                            "output_type": output_type},
                           output_path=output_path)

    def launch(self, command_line):
        """
        Run or queue up the execution of the supplied
        `command_line` on the remote server.

        **Parameters**

        command_line : str
            Command to execute.
        """
        return self.__raw_execute("launch", {"command_line": command_line,
                                             "job_id": self.job_id})

    def kill(self):
        """
        Cancel remote job, either removing from the queue or killing it.
        """
        return self.__raw_execute("kill", {"job_id": self.job_id})

    def wait(self):
        """
        Wait for job to finish.
        """
        while True:
            complete_response = self.raw_check_complete()
            if complete_response["complete"] == "true":
                return complete_response
            time.sleep(1)

    @parseJson()
    def raw_check_complete(self):
        """
        Get check_complete response from the remote server.
        """
        check_complete_response = self.__raw_execute("check_complete", {"job_id": self.job_id})
        return check_complete_response

    def check_complete(self, response=None):
        """
        Return boolean indicating whether the job is complete.
        """
        if response == None:
            response = self.raw_check_complete()
        return response["complete"] == "true"

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
        self.__raw_execute("clean", {"job_id": self.job_id})

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
        return self.__raw_execute("setup", setup_args)
