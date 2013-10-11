from os import getcwd
from os.path import abspath


def build_command( job, job_wrapper, include_metadata=False, include_work_dir_outputs=True ):
    """
    Compose the sequence of commands necessary to execute a job. This will
    currently include:

        - environment settings corresponding to any requirement tags
        - preparing input files
        - command line taken from job wrapper
        - commands to set metadata (if include_metadata is True)
    """

    commands = job_wrapper.get_command_line()

    # All job runners currently handle this case which should never occur
    if not commands:
        return None

    # Prepend version string
    if job_wrapper.version_string_cmd:
        commands = "%s &> %s; " % ( job_wrapper.version_string_cmd, job_wrapper.get_version_string_path() ) + commands

    # prepend getting input files (if defined)
    if hasattr(job_wrapper, 'prepare_input_files_cmds') and job_wrapper.prepare_input_files_cmds is not None:
        commands = "; ".join( job_wrapper.prepare_input_files_cmds + [ commands ] )

    # Prepend dependency injection
    if job_wrapper.dependency_shell_commands:
        commands = "; ".join( job_wrapper.dependency_shell_commands + [ commands ] )

    # Coping work dir outputs or setting metadata will mask return code of
    # tool command. If these are used capture the return code and ensure
    # the last thing that happens is an exit with return code.
    capture_return_code_command = "; return_code=$?"
    captured_return_code = False

    # Append commands to copy job outputs based on from_work_dir attribute.
    if include_work_dir_outputs:
        work_dir_outputs = job.get_work_dir_outputs( job_wrapper )
        if work_dir_outputs:
            if not captured_return_code:
                commands += capture_return_code_command
                captured_return_code = True

            commands += "; " + "; ".join( [ "if [ -f %s ] ; then cp %s %s ; fi" %
                ( source_file, source_file, destination ) for ( source_file, destination ) in work_dir_outputs ] )

    # Append metadata setting commands, we don't want to overwrite metadata
    # that was copied over in init_meta(), as per established behavior
    if include_metadata and job_wrapper.requires_setting_metadata:
        if not captured_return_code:
            commands += capture_return_code_command
            captured_return_code = True
        commands += "; cd %s; " % abspath( getcwd() )
        commands += job_wrapper.setup_external_metadata(
            exec_dir=abspath( getcwd() ),
            tmp_dir=job_wrapper.working_directory,
            dataset_files_path=job.app.model.Dataset.file_path,
            output_fnames=job_wrapper.get_output_fnames(),
            set_extension=False,
            kwds={ 'overwrite' : False }
        )

    if captured_return_code:
        commands += '; sh -c "exit $return_code"'

    return commands
