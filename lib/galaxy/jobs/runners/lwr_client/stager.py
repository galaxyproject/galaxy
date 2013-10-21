
import os
from re import findall


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
            referenced_files.update(findall(pattern, input_contents))
        return list(referenced_files)

    def path_referenced(self, path):
        pattern = r"%s" % path
        found = False
        for input_contents in self.__items():
            if findall(pattern, input_contents):
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

    def __init__(self, client, tool, command_line, config_files, input_files, output_files, working_directory):
        """
        """
        self.client = client
        self.command_line = command_line
        self.config_files = config_files
        self.input_files = input_files
        self.output_files = output_files
        self.tool_id = tool.id
        self.tool_version = tool.version
        self.tool_dir = os.path.abspath(tool.tool_dir)
        self.working_directory = working_directory

        # Setup job inputs, these will need to be rewritten before
        # shipping off to remote LWR server.
        self.job_inputs = JobInputs(self.command_line, self.config_files)

        self.file_renames = {}

        self.__handle_setup()
        self.__initialize_referenced_tool_files()
        self.__upload_tool_files()
        self.__upload_input_files()
        self.__upload_working_directory_files()
        self.__initialize_output_file_renames()
        self.__initialize_task_output_file_renames()
        self.__initialize_config_file_renames()
        self.__handle_rewrites()
        self.__upload_rewritten_config_files()

    def __handle_setup(self):
        job_config = self.client.setup(self.tool_id, self.tool_version)

        self.new_working_directory = job_config['working_directory']
        self.new_outputs_directory = job_config['outputs_directory']
        # Default configs_directory to match remote working_directory to mimic
        # behavior of older LWR servers.
        self.new_configs_drectory = job_config.get('configs_directory', self.new_working_directory)
        self.remote_path_separator = job_config['path_separator']
        # If remote LWR server assigned job id, use that otherwise
        # just use local job_id assigned.
        galaxy_job_id = self.client.job_id
        self.job_id = job_config.get('job_id', galaxy_job_id)
        if self.job_id != galaxy_job_id:
            # Remote LWR server assigned an id different than the
            # Galaxy job id, update client to reflect this.
            self.client.job_id = self.job_id

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
            self.file_renames[config_file] = r'%s%s%s' % (self.new_configs_drectory,
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
