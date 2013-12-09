from os.path import abspath, basename, join, exists
from os import listdir, sep
from re import findall
from re import compile
from io import open

from .action_mapper import FileActionMapper

from logging import getLogger
log = getLogger(__name__)

# All output files marked with from_work_dir attributes will copied or downloaded
# this pattern picks up attiditional files to copy back - such as those
# associated with multiple outputs and metadata configuration. Set to .* to just
# copy everything
COPY_FROM_WORKING_DIRECTORY_PATTERN = compile(r"primary_.*|galaxy.json|metadata_.*")


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
    ...     open(tf.name, "w").write(u"world /path/to/input the rest")
    ...     inputs = JobInputs(u"hello /path/to/input", [tf.name])
    ...     return inputs
    >>> inputs = setup_inputs(tf)
    >>> inputs.rewrite_paths(u"/path/to/input", u'C:\\input')
    >>> inputs.rewritten_command_line == u'hello C:\\\\input'
    True
    >>> inputs.rewritten_config_files[tf.name] == u'world C:\\\\input the rest'
    True
    >>> tf.close()
    >>> tf = tempfile.NamedTemporaryFile()
    >>> inputs = setup_inputs(tf)
    >>> inputs.find_referenced_subfiles('/path/to') == [u'/path/to/input']
    True
    >>> inputs.path_referenced('/path/to')
    True
    >>> inputs.path_referenced(u'/path/to')
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
        pattern = r"(%s%s\S+)" % (directory, sep)
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
        for config_file, rewritten_contents in self.rewritten_config_files.items():
            self.rewritten_config_files[config_file] = rewritten_contents.replace(local_path, remote_path)

    def __items(self):
        items = [self.rewritten_command_line]
        items.extend(self.rewritten_config_files.values())
        return items


class TransferTracker(object):

    def __init__(self, client, job_inputs):
        self.client = client
        self.action_mapper = FileActionMapper(client)
        self.job_inputs = job_inputs
        self.file_renames = {}

    def handle_transfer(self, path, type, name=None, contents=None):
        if contents:
            # If contents loaded in memory, no need to write out file and copy,
            # just transfer.
            action = ('transfer', )
        else:
            if not exists(path):
                message = "handle_tranfer called on non-existent file - [%s]" % path
                log.warn(message)
                raise Exception(message)
            action = self.__action(path, type)

        if action[0] in ['transfer', 'copy']:
            response = self.client.put_file(path, type, name=name, contents=contents)
            self.register_rewrite(path, response['path'], type, force=True)
        elif action[0] == 'none':
            # No action for this file.
            pass
        else:
            raise Exception("Unknown action type (%s) encountered for path (%s)" % (action[0], path))

    def register_rewrite(self, local_path, remote_path, type, force=False):
        action = self.__action(local_path, type)
        if action[0] in ['transfer', 'copy'] or force:
            self.file_renames[local_path] = remote_path

    def rewrite_input_paths(self):
        """
        For each file that has been transferred and renamed, updated
        command_line and configfiles to reflect that rewrite.
        """
        for local_path, remote_path in self.file_renames.items():
            self.job_inputs.rewrite_paths(local_path, remote_path)

    def __action(self, path, type):
        return self.action_mapper.action(path, type)


class FileStager(object):
    """
    Objects of the FileStager class interact with an LWR client object to
    stage the files required to run jobs on a remote LWR server.

    **Parameters**

    client : JobClient
        LWR client object.
    client_job_description : client_job_description
        Description of client view of job to stage and execute remotely.
    """

    def __init__(self, client, client_job_description, job_config):
        """
        """
        self.client = client
        self.command_line = client_job_description.command_line
        self.config_files = client_job_description.config_files
        self.input_files = client_job_description.input_files
        self.output_files = client_job_description.output_files
        self.tool_id = client_job_description.tool.id
        self.tool_version = client_job_description.tool.version
        self.tool_dir = abspath(client_job_description.tool.tool_dir)
        self.working_directory = client_job_description.working_directory

        # Setup job inputs, these will need to be rewritten before
        # shipping off to remote LWR server.
        self.job_inputs = JobInputs(self.command_line, self.config_files)

        self.transfer_tracker = TransferTracker(client, self.job_inputs)

        self.__handle_setup(job_config)
        self.__initialize_referenced_tool_files()
        self.__upload_tool_files()
        self.__upload_input_files()
        self.__upload_working_directory_files()
        self.__initialize_output_file_renames()
        self.__initialize_task_output_file_renames()
        self.__initialize_config_file_renames()
        self.__handle_rewrites()
        self.__upload_rewritten_config_files()

    def __handle_setup(self, job_config):
        if not job_config:
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
            self.transfer_tracker.handle_transfer(referenced_tool_file, 'tool')

    def __upload_input_files(self):
        for input_file in self.input_files:
            self.__upload_input_file(input_file)
            self.__upload_input_extra_files(input_file)

    def __upload_input_file(self, input_file):
        if self.job_inputs.path_referenced(input_file):
            if exists(input_file):
                self.transfer_tracker.handle_transfer(input_file, 'input')
            else:
                message = "LWR: __upload_input_file called on empty or missing dataset." + \
                          " So such file: [%s]" % input_file
                log.debug(message)

    def __upload_input_extra_files(self, input_file):
        # TODO: Determine if this is object store safe and what needs to be
        # done if it is not.
        files_path = "%s_files" % input_file[0:-len(".dat")]
        if exists(files_path) and self.job_inputs.path_referenced(files_path):
            for extra_file in listdir(files_path):
                extra_file_path = join(files_path, extra_file)
                relative_path = basename(files_path)
                extra_file_relative_path = join(relative_path, extra_file)
                self.transfer_tracker.handle_transfer(extra_file_path, 'input_extra', name=extra_file_relative_path)

    def __upload_working_directory_files(self):
        # Task manager stages files into working directory, these need to be
        # uploaded if present.
        for working_directory_file in listdir(self.working_directory):
            path = join(self.working_directory, working_directory_file)
            self.transfer_tracker.handle_transfer(path, 'work_dir')

    def __initialize_output_file_renames(self):
        for output_file in self.output_files:
            remote_path = r'%s%s%s' % (self.new_outputs_directory, self.remote_path_separator, basename(output_file))
            self.transfer_tracker.register_rewrite(output_file, remote_path, 'output')

    def __initialize_task_output_file_renames(self):
        for output_file in self.output_files:
            name = basename(output_file)
            task_file = join(self.working_directory, name)
            remote_path = r'%s%s%s' % (self.new_working_directory, self.remote_path_separator, name)
            self.transfer_tracker.register_rewrite(task_file, remote_path, 'output_task')

    def __initialize_config_file_renames(self):
        for config_file in self.config_files:
            remote_path = r'%s%s%s' % (self.new_configs_drectory, self.remote_path_separator, basename(config_file))
            self.transfer_tracker.register_rewrite(config_file, remote_path, 'config')

    def __handle_rewrites(self):
        """
        For each file that has been transferred and renamed, updated
        command_line and configfiles to reflect that rewrite.
        """
        self.transfer_tracker.rewrite_input_paths()

    def __upload_rewritten_config_files(self):
        for config_file, new_config_contents in self.job_inputs.rewritten_config_files.items():
            self.client.put_file(config_file, input_type='config', contents=new_config_contents)

    def get_rewritten_command_line(self):
        """
        Returns the rewritten version of the command line to execute suitable
        for remote host.
        """
        return self.job_inputs.rewritten_command_line


def finish_job(client, cleanup_job, job_completed_normally, working_directory, work_dir_outputs, output_files, working_directory_contents=[]):
    """
    """
    action_mapper = FileActionMapper(client)
    download_failure_exceptions = []
    downloaded_working_directory_files = []
    if job_completed_normally:
        # Fetch explicit working directory outputs.
        for source_file, output_file in work_dir_outputs:
            name = basename(source_file)
            try:
                action = action_mapper.action(output_file, 'output')
                client.fetch_work_dir_output(name, working_directory, output_file, action[0])
                downloaded_working_directory_files.append(name)
            except Exception as e:
                download_failure_exceptions.append(e)
            # Remove from full output_files list so don't try to download directly.
            output_files.remove(output_file)

        # Fetch output files.
        for output_file in output_files:
            try:
                action = action_mapper.action(output_file, 'output')
                client.fetch_output(output_file, working_directory=working_directory, action=action[0])
            except Exception as e:
                download_failure_exceptions.append(e)

        # Fetch remaining working directory outputs of interest.
        for name in working_directory_contents:
            if name in downloaded_working_directory_files:
                continue
            if COPY_FROM_WORKING_DIRECTORY_PATTERN.match(name):
                output_file = join(working_directory, name)
                action = action_mapper.action(output_file, 'output')
                client.fetch_work_dir_output(name, working_directory, output_file, action=action[0])
                downloaded_working_directory_files.append(name)

    return __clean(download_failure_exceptions, cleanup_job, client)


def __clean(download_failure_exceptions, cleanup_job, client):
    failed = (len(download_failure_exceptions) > 0)
    if (not failed and cleanup_job != "never") or cleanup_job == "always":
        try:
            client.clean()
        except:
            log.warn("Failed to cleanup remote LWR job")
    return failed


def submit_job(client, client_job_description, job_config=None):
    """
    """
    file_stager = FileStager(client, client_job_description, job_config)
    rebuilt_command_line = file_stager.get_rewritten_command_line()
    job_id = file_stager.job_id
    client.launch(rebuilt_command_line)
    return job_id


def _read(path):
    """
    Utility method to quickly read small files (config files and tool
    wrappers) into memory as bytes.
    """
    input = open(path, "r", encoding="utf-8")
    try:
        return input.read()
    finally:
        input.close()


class ClientJobDescription(object):
    """ A description of how client views job - command_line, inputs, etc..

    **Parameters**

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

    def __init__(self, tool, command_line, config_files, input_files, output_files, working_directory):
        self.tool = tool
        self.command_line = command_line
        self.config_files = config_files
        self.input_files = input_files
        self.output_files = output_files
        self.working_directory = working_directory


__all__ = [submit_job, ClientJobDescription, finish_job]
