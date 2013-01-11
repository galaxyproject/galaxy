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


class JobInputs(object):
    """
    Abstractions over dynamic inputs created for a given job (namely the command to
    execute and created configfiles).

    **Parameters**

    command_line : str
        Local command to execute for this job. (To be rewritten.)
    config_files : str
        Config files created for this job. (To be rewritten.)


    >>> import tempfile
    >>> tf = tempfile.NamedTemporaryFile()
    >>> def setup_inputs(tf):
    ...     open(tf.name, "w").write("world /path/to/input the rest")
    ...     inputs = JobInputs("hello /path/to/input", [tf.name])
    ...     return inputs
    >>> inputs = setup_inputs(tf)
    >>> inputs.rewrite_paths("/path/to/input", 'C:\\input')
    >>> inputs.rewritten_command_line
    'hello C:\\\\input'
    >>> inputs.rewritten_config_files[tf.name]
    'world C:\\\\input the rest'
    >>> tf.close()
    >>> tf = tempfile.NamedTemporaryFile()
    >>> inputs = setup_inputs(tf)
    >>> inputs.find_referenced_subfiles('/path/to')
    ['/path/to/input']
    >>> inputs.path_referenced('/path/to')
    True
    >>> inputs.path_referenced('/path/to/input')
    True
    >>> inputs.path_referenced('/path/to/notinput')
    False
    >>> tf.close()
    """

    def __init__(self, command_line, config_files):
        self.rewritten_command_line = command_line
        self.rewritten_config_files = {}
        for config_file in config_files or []:
            config_contents = _read(config_file)
            self.rewritten_config_files[config_file] = config_contents

    def find_referenced_subfiles(self, directory):
        """
        Return list of files below specified `directory` in job inputs. Could
        use more sophisticated logic (match quotes to handle spaces, handle
        subdirectories, etc...).

        **Parameters**

        directory : str
            Full path to directory to search.

        """
        pattern = r"(%s%s\S+)" % (directory, os.sep)
        referenced_files = set()
        for input_contents in self.__items():
            referenced_files.update(re.findall(pattern, input_contents))
        return list(referenced_files)

    def path_referenced(self, path):
        pattern = r"%s" % path
        found = False
        for input_contents in self.__items():
            if re.findall(pattern, input_contents):
                found = True
                break
        return found

    def rewrite_paths(self, local_path, remote_path):
        """
        Rewrite references to `local_path` with  `remote_path` in job inputs.
        """
        self.__rewrite_command_line(local_path, remote_path)
        self.__rewrite_config_files(local_path, remote_path)

    def __rewrite_command_line(self, local_path, remote_path):
        self.rewritten_command_line = self.rewritten_command_line.replace(local_path, remote_path)

    def __rewrite_config_files(self, local_path, remote_path):
        for config_file, rewritten_contents in self.rewritten_config_files.iteritems():
            self.rewritten_config_files[config_file] = rewritten_contents.replace(local_path, remote_path)

    def __items(self):
        items = [self.rewritten_command_line]
        items.extend(self.rewritten_config_files.values())
        return items


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

        # Setup job inputs, these will need to be rewritten before
        # shipping off to remote LWR server.
        self.job_inputs = JobInputs(self.command_line, self.config_files)

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
        self.__handle_rewrites()
        self.__upload_rewritten_config_files()

    def __initialize_referenced_tool_files(self):
        self.referenced_tool_files = self.job_inputs.find_referenced_subfiles(self.tool_dir)

    def __upload_tool_files(self):
        for referenced_tool_file in self.referenced_tool_files:
            tool_upload_response = self.client.upload_tool_file(referenced_tool_file)
            self.file_renames[referenced_tool_file] = tool_upload_response['path']

    def __upload_input_files(self):
        for input_file in self.input_files:
            self.__upload_input_file(input_file)
            self.__upload_input_extra_files(input_file)

    def __upload_input_file(self, input_file):
        if self.job_inputs.path_referenced(input_file):
            input_upload_response = self.client.upload_input(input_file)
            self.file_renames[input_file] = input_upload_response['path']

    def __upload_input_extra_files(self, input_file):
        # TODO: Determine if this is object store safe and what needs to be
        # done if it is not.
        files_path = "%s_files" % input_file[0:-len(".dat")]
        if os.path.exists(files_path) and self.job_inputs.path_referenced(files_path):
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

    def __handle_rewrites(self):
        for local_path, remote_path in self.file_renames.iteritems():
            self.job_inputs.rewrite_paths(local_path, remote_path)

    def __upload_rewritten_config_files(self):
        for config_file, new_config_contents in self.job_inputs.rewritten_config_files.iteritems():
            self.client.upload_config_file(config_file, new_config_contents)

    def get_rewritten_command_line(self):
        """
        Returns the rewritten version of the command line to execute suitable
        for remote host.
        """
        return self.job_inputs.rewritten_command_line


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
            output = open(path, "wb")
        elif output_type == "task":
            output = open(os.path.join(working_directory, name), "wb")
        else:
            raise Exception("No remote output found for dataset with path %s" % path)
        self.__raw_download_output(name, self.job_id, output_type, output)

    def __raw_download_output(self, name, job_id, output_type, output_file):
        response = self.__raw_execute("download_output", {"name": name,
                                                          "job_id": self.job_id,
                                                          "output_type": output_type})
        try:
            while True:
                buffer = response.read(1024)
                if buffer == "":
                    break
                output_file.write(buffer)
        finally:
            output_file.close()

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


def _read(path):
    """
    Utility method to quickly read small files (config files and tool
    wrappers) into memory as strings.
    """
    input = open(path, "r")
    try:
        return input.read()
    finally:
        input.close()
