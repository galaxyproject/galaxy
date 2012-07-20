import os, logging, os.path

log = logging.getLogger( __name__ )

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

        def in_directory( file, directory ):
            """
            Return true, if the common prefix of both is equal to directory
            e.g. /a/b/c/d.rst and directory is /a/b, the common prefix is /a/b
            """

            # Make both absolute.
            directory = os.path.abspath( directory )
            file = os.path.abspath( file )

            return os.path.commonprefix( [ file, directory ] ) == directory

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

        # Append commands to copy job outputs based on from_work_dir attribute.
        job = job_wrapper.get_job()
        job_tool = self.app.toolbox.tools_by_id.get( job.tool_id, None )
        for dataset_assoc in job.output_datasets + job.output_library_datasets:
            for dataset in dataset_assoc.dataset.dataset.history_associations + dataset_assoc.dataset.dataset.library_associations:
                if isinstance( dataset, self.app.model.HistoryDatasetAssociation ):
                    joda = self.sa_session.query( self.app.model.JobToOutputDatasetAssociation ).filter_by( job=job, dataset=dataset ).first()
                    if joda and job_tool:
                        hda_tool_output = job_tool.outputs.get( joda.name, None )
                        if hda_tool_output and hda_tool_output.from_work_dir:
                            # Copy from working dir to HDA.
                            # TODO: move instead of copy to save time?
                            source_file = os.path.join( os.path.abspath( job_wrapper.working_directory ), hda_tool_output.from_work_dir )
                            if in_directory( source_file, job_wrapper.working_directory ):
                                try:
                                    commands += "; cp %s %s" % ( source_file, dataset.file_name )
                                    log.debug( "Copying %s to %s as directed by from_work_dir" % ( source_file, dataset.file_name ) )
                                except ( IOError, OSError ):
                                    log.debug( "Could not copy %s to %s as directed by from_work_dir" % ( source_file, dataset.file_name ) )
                            else:
                                # Security violation.
                                log.exception( "from_work_dir specified a location not in the working directory: %s, %s" % ( source_file, job_wrapper.working_directory ) )



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
