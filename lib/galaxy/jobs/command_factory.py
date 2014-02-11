from os import getcwd
from os.path import abspath

CAPTURE_RETURN_CODE = "return_code=$?"
YIELD_CAPTURED_CODE = 'sh -c "exit $return_code"'


def build_command( runner, job_wrapper, include_metadata=False, include_work_dir_outputs=True, remote_command_params={} ):
    """
    Compose the sequence of commands necessary to execute a job. This will
    currently include:

        - environment settings corresponding to any requirement tags
        - preparing input files
        - command line taken from job wrapper
        - commands to set metadata (if include_metadata is True)
    """

    commands_builder = CommandsBuilder(job_wrapper.get_command_line())

    # All job runners currently handle this case which should never occur
    if not commands_builder.commands:
        return None

    __handle_version_command(commands_builder, job_wrapper)
    __handle_task_splitting(commands_builder, job_wrapper)
    __handle_dependency_resolution(commands_builder, job_wrapper, remote_command_params)

    if include_work_dir_outputs:
        __handle_work_dir_outputs(commands_builder, job_wrapper, runner, remote_command_params)

    if include_metadata and job_wrapper.requires_setting_metadata:
        __handle_metadata(commands_builder, job_wrapper, runner, remote_command_params)

    return commands_builder.build()


def __handle_version_command(commands_builder, job_wrapper):
    # Prepend version string
    write_version_cmd = job_wrapper.write_version_cmd
    if write_version_cmd:
        commands_builder.prepend_command(write_version_cmd)


def __handle_task_splitting(commands_builder, job_wrapper):
    # prepend getting input files (if defined)
    if getattr(job_wrapper, 'prepare_input_files_cmds', None):
        commands_builder.prepend_commands(job_wrapper.prepare_input_files_cmds)


def __handle_dependency_resolution(commands_builder, job_wrapper, remote_command_params):
    local_dependency_resolution = remote_command_params.get("dependency_resolution", "local") == "local"

    # Prepend dependency injection
    if job_wrapper.dependency_shell_commands and local_dependency_resolution:
        commands_builder.prepend_commands(job_wrapper.dependency_shell_commands)


def __handle_work_dir_outputs(commands_builder, job_wrapper, runner, remote_command_params):
    # Append commands to copy job outputs based on from_work_dir attribute.
    work_dir_outputs_kwds = {}
    if 'working_directory' in remote_command_params:
        work_dir_outputs_kwds['job_working_directory'] = remote_command_params['working_directory']
    work_dir_outputs = runner.get_work_dir_outputs( job_wrapper, **work_dir_outputs_kwds )
    if work_dir_outputs:
        commands_builder.capture_return_code()
        copy_commands = map(__copy_if_exists_command, work_dir_outputs)
        commands_builder.append_commands(copy_commands)


def __handle_metadata(commands_builder, job_wrapper, runner, remote_command_params):
    # Append metadata setting commands, we don't want to overwrite metadata
    # that was copied over in init_meta(), as per established behavior
    metadata_kwds = remote_command_params.get('metadata_kwds', {})
    exec_dir = metadata_kwds.get( 'exec_dir', abspath( getcwd() ) )
    tmp_dir = metadata_kwds.get( 'tmp_dir', job_wrapper.working_directory )
    dataset_files_path = metadata_kwds.get( 'dataset_files_path', runner.app.model.Dataset.file_path )
    output_fnames = metadata_kwds.get( 'output_fnames', job_wrapper.get_output_fnames() )
    config_root = metadata_kwds.get( 'config_root', None )
    config_file = metadata_kwds.get( 'config_file', None )
    datatypes_config = metadata_kwds.get( 'datatypes_config', None )
    metadata_command = job_wrapper.setup_external_metadata(
        exec_dir=exec_dir,
        tmp_dir=tmp_dir,
        dataset_files_path=dataset_files_path,
        output_fnames=output_fnames,
        set_extension=False,
        config_root=config_root,
        config_file=config_file,
        datatypes_config=datatypes_config,
        kwds={ 'overwrite' : False }
    ) or ''
    metadata_command = metadata_command.strip()
    if metadata_command:
        commands_builder.capture_return_code()
        commands_builder.append_command("cd %s; %s" % (exec_dir, metadata_command))


def __copy_if_exists_command(work_dir_output):
    source_file, destination = work_dir_output
    return "if [ -f %s ] ; then cp %s %s ; fi" % ( source_file, source_file, destination )


class CommandsBuilder(object):

    def __init__(self, initial_command):
        # Remove trailing semi-colon so we can start hacking up this command.
        # TODO: Refactor to compose a list and join with ';', would be more clean.
        commands = initial_command.rstrip("; ")
        self.commands = commands

        # Coping work dir outputs or setting metadata will mask return code of
        # tool command. If these are used capture the return code and ensure
        # the last thing that happens is an exit with return code.
        self.return_code_captured = False

    def prepend_command(self, command):
        self.commands = "%s; %s" % (command, self.commands)
        return self

    def prepend_commands(self, commands):
        return self.prepend_command("; ".join(commands))

    def append_command(self, command):
        self.commands = "%s; %s" % (self.commands, command)

    def append_commands(self, commands):
        self.append_command("; ".join(commands))

    def capture_return_code(self):
        if not self.return_code_captured:
            self.return_code_captured = True
            self.append_command(CAPTURE_RETURN_CODE)

    def build(self):
        if self.return_code_captured:
            self.append_command(YIELD_CAPTURED_CODE)
        return self.commands

__all__ = [build_command]
