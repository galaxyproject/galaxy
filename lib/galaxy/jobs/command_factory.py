import json
import typing
from logging import getLogger
from os import getcwd
from os.path import (
    abspath,
    join,
)
from typing import Optional

from galaxy import util
from galaxy.job_execution.output_collect import default_exit_code_file
from galaxy.jobs.runners.util.job_script import (
    INTEGRITY_INJECTION,
    ScriptIntegrityChecks,
    write_script,
)
from galaxy.tool_util.deps.container_classes import (
    Container,
    TRAP_KILL_CONTAINER,
)

if typing.TYPE_CHECKING:
    from galaxy.jobs import MinimalJobWrapper
    from galaxy.jobs.runners import BaseJobRunner

log = getLogger(__name__)

CAPTURE_RETURN_CODE = "return_code=$?"
YIELD_CAPTURED_CODE = 'sh -c "exit $return_code"'
SETUP_GALAXY_FOR_METADATA = """
[ "$GALAXY_VIRTUAL_ENV" = "None" ] && GALAXY_VIRTUAL_ENV="$_GALAXY_VIRTUAL_ENV"; _galaxy_setup_environment True"""
PREPARE_DIRS = """mkdir -p working outputs configs
if [ -d _working ]; then
    rm -rf working/ outputs/ configs/; cp -R _working working; cp -R _outputs outputs; cp -R _configs configs
else
    cp -R working _working; cp -R outputs _outputs; cp -R configs _configs
fi
cd working"""


def build_command(
    runner: "BaseJobRunner",
    job_wrapper: "MinimalJobWrapper",
    container: Optional[Container] = None,
    modify_command_for_container: bool = True,
    include_metadata: bool = False,
    include_work_dir_outputs: bool = True,
    create_tool_working_directory: bool = True,
    remote_command_params=None,
    remote_job_directory=None,
    stream_stdout_stderr: bool = False,
):
    """
    Compose the sequence of commands necessary to execute a job. This will
    currently include:

        - environment settings corresponding to any requirement tags
        - preparing input files
        - command line taken from job wrapper
        - commands to set metadata (if include_metadata is True)
    """
    remote_command_params = remote_command_params or {}
    shell = job_wrapper.shell
    base_command_line = job_wrapper.get_command_line()
    # job_id = job_wrapper.job_id
    # log.debug( 'Tool evaluation for job (%s) produced command-line: %s' % ( job_id, base_command_line ) )

    commands_builder = CommandsBuilder(base_command_line)

    # Dependency resolution and task splitting are prepended to the
    # command - so they need to appear in the following order to ensure that
    # the underlying application used by version command is available in the
    # environment after dependency resolution, but the task splitting command
    # is still executed in Galaxy's Python environment.

    # One could imagine also allowing dependencies inside of the container but
    # that is too sophisticated for a first crack at this - build your
    # containers ready to go!
    if not container or container.resolve_dependencies:
        __handle_dependency_resolution(commands_builder, job_wrapper, remote_command_params)

    __handle_task_splitting(commands_builder, job_wrapper)

    externalized = False
    for_pulsar = "pulsar_version" in remote_command_params
    if (container and modify_command_for_container) or job_wrapper.commands_in_new_shell:
        externalized = True
        if container and modify_command_for_container:
            # Many Docker containers do not have /bin/bash.
            external_command_shell = container.shell
        else:
            external_command_shell = shell
        externalized_commands = __externalize_commands(
            job_wrapper, external_command_shell, commands_builder, remote_command_params, container=container
        )
        if container and modify_command_for_container:
            # Stop now and build command before handling metadata and copying
            # working directory files back. These should always happen outside
            # of docker container - no security implications when generating
            # metadata and means no need for Galaxy to be available to container
            # and not copying workdir outputs back means on can be more restrictive
            # of where container can write to in some circumstances.
            run_in_container_command = container.containerize_command(externalized_commands)
            commands_builder = CommandsBuilder(run_in_container_command)
        else:
            commands_builder = CommandsBuilder(externalized_commands)

    wrap_stdio = externalized or not for_pulsar
    if wrap_stdio:
        # Galaxy writes I/O files to outputs, Pulsar uses metadata. metadata seems like
        # it should be preferred - at least if the directory exists.
        io_directory = "../metadata" if for_pulsar else "../outputs"
        commands_builder.capture_stdout_stderr(
            f"{io_directory}/tool_stdout", f"{io_directory}/tool_stderr", stream_stdout_stderr=stream_stdout_stderr
        )

    # Don't need to create a separate tool working directory for Pulsar
    # jobs - that is handled by Pulsar.
    if create_tool_working_directory:
        # usually working will already exist, but it will not for task
        # split jobs.

        # Copy working and outputs before job submission so that these can be restored on resubmission
        # xref https://github.com/galaxyproject/galaxy/issues/3289
        commands_builder.prepend_command(PREPARE_DIRS)

    __handle_remote_command_line_building(commands_builder, job_wrapper, for_pulsar=for_pulsar)

    container_monitor_command = job_wrapper.container_monitor_command(container)
    if container_monitor_command:
        commands_builder.prepend_command(container_monitor_command)

    working_directory = remote_job_directory or job_wrapper.working_directory
    commands_builder.capture_return_code(default_exit_code_file(working_directory, job_wrapper.job_id))

    if job_wrapper.is_cwl_job:
        # Minimal metadata needed by the relocate script
        cwl_metadata_params = {
            "job_metadata": join("working", job_wrapper.tool.provided_metadata_file),
            "job_id_tag": job_wrapper.get_id_tag(),
        }
        cwl_metadata_params_path = join(job_wrapper.working_directory, "cwl_params.json")
        with open(cwl_metadata_params_path, "w") as f:
            json.dump(cwl_metadata_params, f)

        relocate_script_file = join(job_wrapper.working_directory, "relocate_dynamic_outputs.py")
        relocate_contents = (
            "from galaxy_ext.cwl.handle_outputs import relocate_dynamic_outputs; relocate_dynamic_outputs()"
        )
        write_script(relocate_script_file, relocate_contents, ScriptIntegrityChecks(check_job_script_integrity=False))
        commands_builder.append_command(SETUP_GALAXY_FOR_METADATA)
        commands_builder.append_command(f"python '{relocate_script_file}'")

    if include_work_dir_outputs:
        __handle_work_dir_outputs(commands_builder, job_wrapper, runner, remote_command_params)

    if include_metadata and job_wrapper.requires_setting_metadata:
        commands_builder.append_command(f"cd '{working_directory}'")
        __handle_metadata(commands_builder, job_wrapper, runner, remote_command_params)

    return commands_builder.build()


def __externalize_commands(
    job_wrapper: "MinimalJobWrapper",
    shell,
    commands_builder,
    remote_command_params,
    script_name="tool_script.sh",
    container: Optional[Container] = None,
):
    local_container_script = join(job_wrapper.working_directory, script_name)
    tool_commands = commands_builder.build()
    integrity_injection = ""
    # Setting shell to none in the job config disables creating a tool command script,
    # set -e doesn't work for composite commands but this is necessary for Windows jobs
    # for instance.
    if shell and shell.lower() == "none":
        return tool_commands
    if job_wrapper.job_io.check_job_script_integrity:
        integrity_injection = INTEGRITY_INJECTION
    set_e = ""
    if job_wrapper.strict_shell:
        set_e = "set -e\n"
    source_command = ""
    if container:
        source_command = container.source_environment
    script_contents = "#!{}\n{}{}{}{}".format(
        shell,
        integrity_injection,
        set_e,
        source_command,
        tool_commands,
    )
    write_script(
        local_container_script,
        script_contents,
        job_io=job_wrapper.job_io,
    )
    commands = f"{shell} {local_container_script}"
    # TODO: Cleanup for_pulsar hack.
    # - Integrate Pulsar sending tool_stdout/tool_stderr back
    #   https://github.com/galaxyproject/pulsar/pull/202
    # *and*
    # - Get Galaxy to write these files to an output directory so the container itself
    #   doesn't need to mount the job directory (rw) and then eliminate this hack
    #   (or restrict to older Pulsar versions).
    #   https://github.com/galaxyproject/galaxy/pull/8449
    for_pulsar = "pulsar_version" in remote_command_params
    if for_pulsar:
        commands = f"{shell} {join(remote_command_params['script_directory'], script_name)}"
    log.info(f"Built script [{local_container_script}] for tool command [{tool_commands}]")
    return commands


def __handle_remote_command_line_building(commands_builder, job_wrapper: "MinimalJobWrapper", for_pulsar=False):
    if job_wrapper.remote_command_line:
        sep = "" if for_pulsar else "&&"
        command = 'PYTHONPATH="$GALAXY_LIB:$PYTHONPATH" python "$GALAXY_LIB"/galaxy/tools/remote_tool_eval.py'
        if for_pulsar:
            # TODO: that's not how to do this, pulsar doesn't execute an externalized script by default.
            # This also breaks rewriting paths etc, so it doesn't really work if there are no shared paths
            command = f"{command} && bash ../tool_script.sh"
        commands_builder.prepend_command(command, sep=sep)


def __handle_task_splitting(commands_builder, job_wrapper: "MinimalJobWrapper"):
    # prepend getting input files (if defined)
    prepare_input_files_cmds = getattr(job_wrapper, "prepare_input_files_cmds", None)
    if prepare_input_files_cmds:
        commands_builder.prepend_commands(prepare_input_files_cmds)


def __handle_dependency_resolution(commands_builder, job_wrapper: "MinimalJobWrapper", remote_command_params):
    local_dependency_resolution = remote_command_params.get("dependency_resolution", "local") == "local"
    # Prepend dependency injection
    if local_dependency_resolution and job_wrapper.dependency_shell_commands:
        commands_builder.prepend_commands(job_wrapper.dependency_shell_commands)


def __handle_work_dir_outputs(
    commands_builder, job_wrapper: "MinimalJobWrapper", runner: "BaseJobRunner", remote_command_params
):
    # Append commands to copy job outputs based on from_work_dir attribute.
    work_dir_outputs_kwds = {}
    if "working_directory" in remote_command_params:
        work_dir_outputs_kwds["job_working_directory"] = remote_command_params["working_directory"]
    work_dir_outputs = runner.get_work_dir_outputs(job_wrapper, **work_dir_outputs_kwds)
    if work_dir_outputs:
        copy_commands = map(__copy_if_exists_command, work_dir_outputs)
        commands_builder.append_commands(copy_commands)


def __handle_metadata(
    commands_builder, job_wrapper: "MinimalJobWrapper", runner: "BaseJobRunner", remote_command_params
):
    # Append metadata setting commands, we don't want to overwrite metadata
    # that was copied over in init_meta(), as per established behavior
    metadata_kwds = remote_command_params.get("metadata_kwds", {})
    exec_dir = metadata_kwds.get("exec_dir", abspath(getcwd()))
    tmp_dir = metadata_kwds.get("tmp_dir", job_wrapper.working_directory)
    dataset_files_path = metadata_kwds.get("dataset_files_path", runner.app.model.Dataset.file_path)
    output_fnames = metadata_kwds.get("output_fnames", job_wrapper.job_io.get_output_fnames())
    config_root = metadata_kwds.get("config_root", None)
    config_file = metadata_kwds.get("config_file", None)
    datatypes_config = metadata_kwds.get("datatypes_config", None)
    compute_tmp_dir = metadata_kwds.get("compute_tmp_dir", None)
    version_path = job_wrapper.job_io.version_path
    resolve_metadata_dependencies = job_wrapper.commands_in_new_shell
    metadata_command = (
        job_wrapper.setup_external_metadata(
            exec_dir=exec_dir,
            tmp_dir=tmp_dir,
            dataset_files_path=dataset_files_path,
            output_fnames=output_fnames,
            set_extension=False,
            config_root=config_root,
            config_file=config_file,
            datatypes_config=datatypes_config,
            compute_tmp_dir=compute_tmp_dir,
            compute_version_path=version_path,
            resolve_metadata_dependencies=resolve_metadata_dependencies,
            use_bin=job_wrapper.use_metadata_binary,
            kwds={"overwrite": False},
        )
        or ""
    )
    metadata_command = metadata_command.strip()
    if metadata_command:
        # Place Galaxy and its dependencies in environment for metadata regardless of tool.
        if not job_wrapper.is_cwl_job:
            commands_builder.append_command(SETUP_GALAXY_FOR_METADATA)
        commands_builder.append_command(metadata_command)


def __copy_if_exists_command(work_dir_output):
    source_file, destination = work_dir_output
    if "?" in source_file or "*" in source_file:
        source_file = source_file.replace("*", '"*"').replace("?", '"?"')
    return f'\nif [ -f "{source_file}" ] ; then cp "{source_file}" "{destination}" ; fi'


class CommandsBuilder:
    def __init__(self, initial_command=""):
        # Remove trailing semi-colon so we can start hacking up this command.
        # TODO: Refactor to compose a list and join with ';', would be more clean.
        self.raw_command = initial_command
        initial_command = util.unicodify(initial_command or "")
        commands = initial_command.rstrip("; ")
        self.commands = commands

        # Coping work dir outputs or setting metadata will mask return code of
        # tool command. If these are used capture the return code and ensure
        # the last thing that happens is an exit with return code.
        self.return_code_captured = False

    def prepend_command(self, command, sep=";"):
        if command:
            self.commands = f"{command}{sep} {self.commands}"
        return self

    def prepend_commands(self, commands):
        return self.prepend_command("; ".join(c for c in commands if c))

    def append_command(self, command, sep=";"):
        if command:
            self.commands = f"{self.commands}{sep} {command}"
        return self

    def append_commands(self, commands):
        self.append_command("; ".join(c for c in commands if c))

    def capture_stdout_stderr(self, stdout_file, stderr_file, stream_stdout_stderr=False):
        if not stream_stdout_stderr:
            self.append_command(f"> '{stdout_file}' 2> '{stderr_file}'", sep="")
            return
        trap_command = """trap 'rm -f "$__out" "$__err"' EXIT"""
        if TRAP_KILL_CONTAINER in self.commands:
            # We need to replace the container kill trap with one that removes the named pipes and kills the container
            self.commands = self.commands.replace(TRAP_KILL_CONTAINER, "")
            trap_command = """trap 'rm -f "$__out" "$__err"; _on_exit' EXIT"""
        self.prepend_command(
            f"""__out="${{TMPDIR:-.}}/out.$$" __err="${{TMPDIR:-.}}/err.$$"
mkfifo "$__out" "$__err"
{trap_command}
tee -a '{stdout_file}' < "$__out" &
tee -a '{stderr_file}' < "$__err" >&2 &""",
            sep="",
        )
        self.append_command('> "$__out" 2> "$__err"', sep="")

    def capture_return_code(self, exit_code_path):
        self.append_command(CAPTURE_RETURN_CODE)
        self.append_command(f"echo $return_code > {exit_code_path}")
        self.return_code_captured = True

    def build(self):
        if self.return_code_captured:
            self.append_command(YIELD_CAPTURED_CODE)
        return self.commands


__all__ = ("build_command",)
