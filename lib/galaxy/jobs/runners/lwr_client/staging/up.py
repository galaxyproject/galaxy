from os.path import abspath, basename, join, exists
from os.path import dirname
from os.path import relpath
from os import listdir, sep
from re import findall
from io import open

from ..staging import COMMAND_VERSION_FILENAME
from ..action_mapper import FileActionMapper
from ..action_mapper import path_type
from ..action_mapper import MessageAction
from ..util import PathHelper
from ..util import directory_files

from logging import getLogger
log = getLogger(__name__)


def submit_job(client, client_job_description, job_config=None):
    """
    """
    file_stager = FileStager(client, client_job_description, job_config)
    rebuilt_command_line = file_stager.get_command_line()
    job_id = file_stager.job_id
    launch_kwds = dict(
        command_line=rebuilt_command_line,
        dependencies_description=client_job_description.dependencies_description,
        env=client_job_description.env,
    )
    if file_stager.job_config:
        launch_kwds["job_config"] = file_stager.job_config
    remote_staging = {}
    remote_staging_actions = file_stager.transfer_tracker.remote_staging_actions
    if remote_staging_actions:
        remote_staging["setup"] = remote_staging_actions
    # Somehow make the following optional.
    remote_staging["action_mapper"] = file_stager.action_mapper.to_dict()
    remote_staging["client_outputs"] = client_job_description.client_outputs.to_dict()

    if remote_staging:
        launch_kwds["remote_staging"] = remote_staging

    client.launch(**launch_kwds)
    return job_id


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
        self.version_file = client_job_description.version_file
        self.arbitrary_files = client_job_description.arbitrary_files
        self.rewrite_paths = client_job_description.rewrite_paths

        # Setup job inputs, these will need to be rewritten before
        # shipping off to remote LWR server.
        self.job_inputs = JobInputs(self.command_line, self.config_files)

        self.action_mapper = FileActionMapper(client)

        self.__handle_setup(job_config)

        self.transfer_tracker = TransferTracker(client, self.path_helper, self.action_mapper, self.job_inputs, rewrite_paths=self.rewrite_paths)

        self.__initialize_referenced_tool_files()
        if self.rewrite_paths:
            self.__initialize_referenced_arbitrary_files()

        self.__upload_tool_files()
        self.__upload_input_files()
        self.__upload_working_directory_files()
        self.__upload_arbitrary_files()

        if self.rewrite_paths:
            self.__initialize_output_file_renames()
            self.__initialize_task_output_file_renames()
            self.__initialize_config_file_renames()
            self.__initialize_version_file_rename()

        self.__handle_rewrites()

        self.__upload_rewritten_config_files()

    def __handle_setup(self, job_config):
        if not job_config:
            job_config = self.client.setup(self.tool_id, self.tool_version)

        self.new_working_directory = job_config['working_directory']
        self.new_outputs_directory = job_config['outputs_directory']
        # Default configs_directory to match remote working_directory to mimic
        # behavior of older LWR servers.
        self.new_configs_directory = job_config.get('configs_directory', self.new_working_directory)
        self.remote_separator = self.__parse_remote_separator(job_config)
        self.path_helper = PathHelper(self.remote_separator)
        # If remote LWR server assigned job id, use that otherwise
        # just use local job_id assigned.
        galaxy_job_id = self.client.job_id
        self.job_id = job_config.get('job_id', galaxy_job_id)
        if self.job_id != galaxy_job_id:
            # Remote LWR server assigned an id different than the
            # Galaxy job id, update client to reflect this.
            self.client.job_id = self.job_id
        self.job_config = job_config

    def __parse_remote_separator(self, job_config):
        separator = job_config.get("system_properties", {}).get("separator", None)
        if not separator:  # Legacy LWR
            separator = job_config["path_separator"]  # Poorly named
        return separator

    def __initialize_referenced_tool_files(self):
        self.referenced_tool_files = self.job_inputs.find_referenced_subfiles(self.tool_dir)

    def __initialize_referenced_arbitrary_files(self):
        referenced_arbitrary_path_mappers = dict()
        for mapper in self.action_mapper.unstructured_mappers():
            mapper_pattern = mapper.to_pattern()
            # TODO: Make more sophisticated, allow parent directories,
            # grabbing sibbling files based on patterns, etc...
            paths = self.job_inputs.find_pattern_references(mapper_pattern)
            for path in paths:
                if path not in referenced_arbitrary_path_mappers:
                    referenced_arbitrary_path_mappers[path] = mapper
        for path, mapper in referenced_arbitrary_path_mappers.iteritems():
            action = self.action_mapper.action(path, path_type.UNSTRUCTURED, mapper)
            unstructured_map = action.unstructured_map(self.path_helper)
            self.arbitrary_files.update(unstructured_map)

    def __upload_tool_files(self):
        for referenced_tool_file in self.referenced_tool_files:
            self.transfer_tracker.handle_transfer(referenced_tool_file, path_type.TOOL)

    def __upload_arbitrary_files(self):
        for path, name in self.arbitrary_files.iteritems():
            self.transfer_tracker.handle_transfer(path, path_type.UNSTRUCTURED, name=name)

    def __upload_input_files(self):
        for input_file in self.input_files:
            self.__upload_input_file(input_file)
            self.__upload_input_extra_files(input_file)

    def __upload_input_file(self, input_file):
        if self.__stage_input(input_file):
            if exists(input_file):
                self.transfer_tracker.handle_transfer(input_file, path_type.INPUT)
            else:
                message = "LWR: __upload_input_file called on empty or missing dataset." + \
                          " So such file: [%s]" % input_file
                log.debug(message)

    def __upload_input_extra_files(self, input_file):
        files_path = "%s_files" % input_file[0:-len(".dat")]
        if exists(files_path) and self.__stage_input(files_path):
            for extra_file_name in directory_files(files_path):
                extra_file_path = join(files_path, extra_file_name)
                remote_name = self.path_helper.remote_name(relpath(extra_file_path, dirname(files_path)))
                self.transfer_tracker.handle_transfer(extra_file_path, path_type.INPUT, name=remote_name)

    def __upload_working_directory_files(self):
        # Task manager stages files into working directory, these need to be
        # uploaded if present.
        working_directory_files = listdir(self.working_directory) if exists(self.working_directory) else []
        for working_directory_file in working_directory_files:
            path = join(self.working_directory, working_directory_file)
            self.transfer_tracker.handle_transfer(path, path_type.WORKDIR)

    def __initialize_version_file_rename(self):
        version_file = self.version_file
        if version_file:
            remote_path = self.path_helper.remote_join(self.new_outputs_directory, COMMAND_VERSION_FILENAME)
            self.transfer_tracker.register_rewrite(version_file, remote_path, path_type.OUTPUT)

    def __initialize_output_file_renames(self):
        for output_file in self.output_files:
            remote_path = self.path_helper.remote_join(self.new_outputs_directory, basename(output_file))
            self.transfer_tracker.register_rewrite(output_file, remote_path, path_type.OUTPUT)

    def __initialize_task_output_file_renames(self):
        for output_file in self.output_files:
            name = basename(output_file)
            task_file = join(self.working_directory, name)
            remote_path = self.path_helper.remote_join(self.new_working_directory, name)
            self.transfer_tracker.register_rewrite(task_file, remote_path, path_type.OUTPUT_WORKDIR)

    def __initialize_config_file_renames(self):
        for config_file in self.config_files:
            remote_path = self.path_helper.remote_join(self.new_configs_directory, basename(config_file))
            self.transfer_tracker.register_rewrite(config_file, remote_path, path_type.CONFIG)

    def __handle_rewrites(self):
        """
        For each file that has been transferred and renamed, updated
        command_line and configfiles to reflect that rewrite.
        """
        self.transfer_tracker.rewrite_input_paths()

    def __upload_rewritten_config_files(self):
        for config_file, new_config_contents in self.job_inputs.config_files.items():
            self.transfer_tracker.handle_transfer(config_file, type=path_type.CONFIG, contents=new_config_contents)

    def get_command_line(self):
        """
        Returns the rewritten version of the command line to execute suitable
        for remote host.
        """
        return self.job_inputs.command_line

    def __stage_input(self, file_path):
        # If we have disabled path rewriting, just assume everything needs to be transferred,
        # else check to ensure the file is referenced before transferring it.
        return (not self.rewrite_paths) or self.job_inputs.path_referenced(file_path)


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
    >>> inputs.command_line == u'hello C:\\\\input'
    True
    >>> inputs.config_files[tf.name] == u'world C:\\\\input the rest'
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
        self.command_line = command_line
        self.config_files = {}
        for config_file in config_files or []:
            config_contents = _read(config_file)
            self.config_files[config_file] = config_contents

    def find_pattern_references(self, pattern):
        referenced_files = set()
        for input_contents in self.__items():
            referenced_files.update(findall(pattern, input_contents))
        return list(referenced_files)

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
        return self.find_pattern_references(pattern)

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
        self.command_line = self.command_line.replace(local_path, remote_path)

    def __rewrite_config_files(self, local_path, remote_path):
        for config_file, contents in self.config_files.items():
            self.config_files[config_file] = contents.replace(local_path, remote_path)

    def __items(self):
        items = [self.command_line]
        items.extend(self.config_files.values())
        return items


class TransferTracker(object):

    def __init__(self, client, path_helper, action_mapper, job_inputs, rewrite_paths):
        self.client = client
        self.path_helper = path_helper
        self.action_mapper = action_mapper

        self.job_inputs = job_inputs
        self.rewrite_paths = rewrite_paths
        self.file_renames = {}
        self.remote_staging_actions = []

    def handle_transfer(self, path, type, name=None, contents=None):
        action = self.__action_for_transfer(path, type, contents)

        if action.staging_needed:
            local_action = action.staging_action_local
            if local_action:
                response = self.client.put_file(path, type, name=name, contents=contents)
                get_path = lambda: response['path']
            else:
                job_directory = self.client.job_directory
                assert job_directory, "job directory required for action %s" % action
                if not name:
                    name = basename(path)
                self.__add_remote_staging_input(action, name, type)
                get_path = lambda: job_directory.calculate_path(name, type)
            register = self.rewrite_paths or type == 'tool'  # Even if inputs not rewritten, tool must be.
            if register:
                self.register_rewrite(path, get_path(), type, force=True)
        elif self.rewrite_paths:
            path_rewrite = action.path_rewrite(self.path_helper)
            if path_rewrite:
                self.register_rewrite(path, path_rewrite, type, force=True)

        # else: # No action for this file

    def __add_remote_staging_input(self, action, name, type):
        input_dict = dict(
            name=name,
            type=type,
            action=action.to_dict(),
        )
        self.remote_staging_actions.append(input_dict)

    def __action_for_transfer(self, path, type, contents):
        if contents:
            # If contents loaded in memory, no need to write out file and copy,
            # just transfer.
            action = MessageAction(contents=contents, client=self.client)
        else:
            if not exists(path):
                message = "handle_tranfer called on non-existent file - [%s]" % path
                log.warn(message)
                raise Exception(message)
            action = self.__action(path, type)
        return action

    def register_rewrite(self, local_path, remote_path, type, force=False):
        action = self.__action(local_path, type)
        if action.staging_needed or force:
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


__all__ = [submit_job]
