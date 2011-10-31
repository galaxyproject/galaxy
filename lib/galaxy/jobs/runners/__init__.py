import os, os.path

class BaseJobRunner( object ):
    def build_command_line( self, job_wrapper, include_metadata=False ):
        """
        Compose the sequence of commands necessary to execute a job. This will
        currently include:
            - environment settings corresponding to any requirement tags
            - preparing input files
            - command line taken from job wrapper
            - commands to set metadata (if include_metadata is True)
        """
        commands = job_wrapper.get_command_line()
        # All job runners currently handle this case which should never
        # occur
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

        # Append metadata setting commands, we don't want to overwrite metadata
        # that was copied over in init_meta(), as per established behavior
        if include_metadata and self.app.config.set_metadata_externally:
            commands += "; cd %s; " % os.path.abspath( os.getcwd() )
            commands += job_wrapper.setup_external_metadata( 
                            exec_dir = os.path.abspath( os.getcwd() ),
                            tmp_dir = job_wrapper.working_directory,
                            dataset_files_path = self.app.model.Dataset.file_path,
                            output_fnames = job_wrapper.get_output_fnames(),
                            set_extension = False,
                            kwds = { 'overwrite' : False } ) 
        return commands
