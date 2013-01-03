"""
lwr_client
==========

This module contains logic for interfacing with an external LWR server.

"""
import mmap
import os
import re
import time
import urllib
import urllib2

import simplejson


class FileStager(object):
    """
    Objects of the FileStager class interact with an LWR client object to
    stage the files required to run jobs on a remote LWR server.

    **Parameters**

    client : Client
        LWR client object.
    command_line : str
        The local command line to execute, this will be rewritten for the remote server.
    config_files : list
        List of Galaxy 'configfile's produced for this job. These will be rewritten and sent to remote server.
    input_files :  list
        List of input files used by job. These will be transferred and references rewritten.
    output_files : list
        List of output_files produced by job.
    tool_dir : str
        Directory containing tool to execute (if a wrapper is used, it will be transferred to remote server).
    working_directory : str
        Local path created by Galaxy for running this job.

    """

    def __init__(self, client, command_line, config_files, input_files, output_files, tool_dir, working_directory):
        """
        """
        self.client = client
        self.command_line = command_line
        self.config_files = config_files
        self.input_files = input_files
        self.output_files = output_files
        self.tool_dir = os.path.abspath(tool_dir)
        self.working_directory = working_directory

        self.file_renames = {}

        job_config = client.setup()

        self.new_working_directory = job_config['working_directory']
        self.new_outputs_directory = job_config['outputs_directory']
        self.remote_path_separator = job_config['path_separator']

        self.__initialize_referenced_tool_files()
        self.__upload_tool_files()
        self.__upload_input_files()
        self.__upload_working_directory_files()
        self.__initialize_output_file_renames()
        self.__initialize_task_output_file_renames()
        self.__initialize_config_file_renames()
        self.__rewrite_and_upload_config_files()
        self.__rewrite_command_line()

    def __initialize_referenced_tool_files(self):
        pattern = r"(%s%s\S+)" % (self.tool_dir, os.sep)
        referenced_tool_files = []
        referenced_tool_files += re.findall(pattern, self.command_line)
        if self.config_files != None:
            for config_file in self.config_files:
                referenced_tool_files += re.findall(pattern, self.__read(config_file))
        self.referenced_tool_files = referenced_tool_files

    def __upload_tool_files(self):
        for referenced_tool_file in self.referenced_tool_files:
            tool_upload_response = self.client.upload_tool_file(referenced_tool_file)
            self.file_renames[referenced_tool_file] = tool_upload_response['path']

    def __upload_input_files(self):
        for input_file in self.input_files:
            input_upload_response = self.client.upload_input(input_file)
            self.file_renames[input_file] = input_upload_response['path']
            # TODO: Determine if this is object store safe and what needs to be
            # done if it is not.
            files_path = "%s_files" % input_file[0:-len(".dat")]
            if os.path.exists(files_path):
                for extra_file in os.listdir(files_path):
                    extra_file_path = os.path.join(files_path, extra_file)
                    relative_path = os.path.basename(files_path)
                    extra_file_relative_path = os.path.join(relative_path, extra_file)
                    response = self.client.upload_extra_input(extra_file_path, extra_file_relative_path)
                    self.file_renames[extra_file_path] = response['path']

    def __upload_working_directory_files(self):
        # Task manager stages files into working directory, these need to be
        # uploaded if present.
        for working_directory_file in os.listdir(self.working_directory):
            path = os.path.join(self.working_directory, working_directory_file)
            working_file_response = self.client.upload_working_directory_file(path)
            self.file_renames[path] = working_file_response['path']

    def __initialize_output_file_renames(self):
        for output_file in self.output_files:
            self.file_renames[output_file] = r'%s%s%s' % (self.new_outputs_directory,
                                                         self.remote_path_separator,
                                                         os.path.basename(output_file))

    def __initialize_task_output_file_renames(self):
        for output_file in self.output_files:
            name = os.path.basename(output_file)
            self.file_renames[os.path.join(self.working_directory, name)] = r'%s%s%s' % (self.new_working_directory,
                                                                                         self.remote_path_separator,
                                                                                         name)

    def __initialize_config_file_renames(self):
        for config_file in self.config_files:
            self.file_renames[config_file] = r'%s%s%s' % (self.new_working_directory,
                                                         self.remote_path_separator,
                                                         os.path.basename(config_file))

    def __rewrite_paths(self, contents):
        new_contents = contents
        for local_path, remote_path in self.file_renames.iteritems():
            new_contents = new_contents.replace(local_path, remote_path)
        return new_contents

    def __rewrite_and_upload_config_files(self):
        for config_file in self.config_files:
            config_contents = self.__read(config_file)
            new_config_contents = self.__rewrite_paths(config_contents)
            self.client.upload_config_file(config_file, new_config_contents)

    def __rewrite_command_line(self):
        self.rewritten_command_line = self.__rewrite_paths(self.command_line)

    def get_rewritten_command_line(self):
        """
        Returns the rewritten version of the command line to execute suitable
        for remote host.
        """
        return self.rewritten_command_line

    def __read(self, path):
        input = open(path, "r")
        try:
            return input.read()
        finally:
            input.close()


class Client(object):
    """
    Objects of this client class perform low-level communication with a remote LWR server.

    **Parameters**

    remote_host : str
        Remote URL of the LWR server.
    job_id : str
        Galaxy job/task id.
    private_key : str (optional)
        Secret key the remote LWR server is configured with.
    """

    def __init__(self, remote_host, job_id, private_key=None):
        if not remote_host.endswith("/"):
            remote_host = remote_host + "/"
        ## If we don't have an explicit private_key defined, check for
        ## one embedded in the URL. A URL of the form
        ## https://moo@cow:8913 will try to contact https://cow:8913
        ## with a private key of moo
        private_key_format = "https?://(.*)@.*/?"
        private_key_match = re.match(private_key_format, remote_host)
        if not private_key and private_key_match:
            private_key = private_key_match.group(1)
            remote_host = remote_host.replace("%s@" % private_key, '', 1)
        self.remote_host = remote_host
        self.job_id = job_id
        self.private_key = private_key

    def _url_open(self, request, data):
        return urllib2.urlopen(request, data)

    def __build_url(self, command, args):
        if self.private_key:
            args["private_key"] = self.private_key
        data = urllib.urlencode(args)
        url = self.remote_host + command + "?" + data
        return url

    def __raw_execute(self, command, args={}, data=None):
        url = self.__build_url(command, args)
        request = urllib2.Request(url=url, data=data)
        response = self._url_open(request, data)
        return response

    def __raw_execute_and_parse(self, command, args={}, data=None):
        response = self.__raw_execute(command, args, data)
        return simplejson.loads(response.read())

    def __upload_file(self, action, path, name=None, contents=None):
        input = open(path, 'rb')
        try:
            mmapped_input = mmap.mmap(input.fileno(), 0, access=mmap.ACCESS_READ)
            return self.__upload_contents(action, path, mmapped_input, name)
        finally:
            input.close()

    def __upload_contents(self, action, path, contents, name=None):
        if not name:
            name = os.path.basename(path)
        args = {"job_id": self.job_id, "name": name}
        return self.__raw_execute_and_parse(action, args, contents)

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
        return self.__upload_contents("upload_config_file", path, contents)

    def upload_working_directory_file(self, path):
        """
        Upload the supplied file (path) from a job's working directory
        to remote server.

        **Parameters**

        path : str
            Path to file to upload.
        """
        return self.__upload_file("upload_working_directory_file", path)

    def _get_output_type(self, name):
        return self.__raw_execute_and_parse("get_output_type", {"name": name,
                                                                "job_id": self.job_id})

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
        response = self.__raw_execute("download_output", {"name": name,
                                                          "job_id": self.job_id,
                                                          "output_type": output_type})
        if output_type == "direct":
            output = open(path, "wb")
        elif output_type == "task":
            output = open(os.path.join(working_directory, name), "wb")
        else:
            raise Exception("No remote output found for dataset with path %s" % path)
        try:
            while True:
                buffer = response.read(1024)
                if buffer == "":
                    break
                output.write(buffer)
        finally:
            output.close()

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

    def raw_check_complete(self):
        """
        Get check_complete response from the remote server.
        """
        check_complete_response = self.__raw_execute_and_parse("check_complete", {"job_id": self.job_id})
        return check_complete_response

    def check_complete(self):
        """
        Return boolean indicating whether the job is complete.
        """
        return self.raw_check_complete()["complete"] == "true"

    def clean(self):
        """
        Cleanup the remote job.
        """
        self.__raw_execute("clean", {"job_id": self.job_id})

    def setup(self):
        """
        Setup remote LWR server to run this job.
        """
        return self.__raw_execute_and_parse("setup", {"job_id": self.job_id})
