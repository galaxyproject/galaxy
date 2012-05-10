"""
Support for running a tool in Galaxy via an internal job management system
"""

import os
import sys
import pwd
import time
import logging
import threading
import traceback
import subprocess

import galaxy
from galaxy import util, model
from galaxy.datatypes.tabular import *
from galaxy.datatypes.interval import *
# tabular/interval imports appear to be unused.  Clean up?
from galaxy.datatypes import metadata
from galaxy.util.json import from_json_string
from galaxy.util.expressions import ExpressionContext
from galaxy.jobs.actions.post import ActionBox
from galaxy.exceptions import ObjectInvalid

log = logging.getLogger( __name__ )

# This file, if created in the job's working directory, will be used for
# setting advanced metadata properties on the job and its associated outputs.
# This interface is currently experimental, is only used by the upload tool,
# and should eventually become API'd
TOOL_PROVIDED_JOB_METADATA_FILE = 'galaxy.json'

class Sleeper( object ):
    """
    Provides a 'sleep' method that sleeps for a number of seconds *unless*
    the notify method is called (from a different thread).
    """
    def __init__( self ):
        self.condition = threading.Condition()
    def sleep( self, seconds ):
        self.condition.acquire()
        self.condition.wait( seconds )
        self.condition.release()
    def wake( self ):
        self.condition.acquire()
        self.condition.notify()
        self.condition.release()

class JobWrapper( object ):
    """
    Wraps a 'model.Job' with convenience methods for running processes and
    state management.
    """
    def __init__( self, job, queue ):
        self.job_id = job.id
        self.session_id = job.session_id
        self.user_id = job.user_id
        self.tool = queue.app.toolbox.tools_by_id.get( job.tool_id, None )
        self.queue = queue
        self.app = queue.app
        self.sa_session = self.app.model.context
        self.extra_filenames = []
        self.command_line = None
        # Tool versioning variables
        self.version_string_cmd = None
        self.version_string = ""
        self.galaxy_lib_dir = None
        # With job outputs in the working directory, we need the working
        # directory to be set before prepare is run, or else premature deletion
        # and job recovery fail.
        # Create the working dir if necessary
        try:
            self.app.object_store.create(job, base_dir='job_work', dir_only=True, extra_dir=str(self.job_id))
            self.working_directory = self.app.object_store.get_filename(job, base_dir='job_work', dir_only=True, extra_dir=str(self.job_id))
            log.debug('(%s) Working directory for job is: %s' % (self.job_id, self.working_directory))
        except ObjectInvalid:
            raise Exception('Unable to create job working directory, job failure')
        self.output_paths = None
        self.output_hdas_and_paths = None
        self.tool_provided_job_metadata = None
        # Wrapper holding the info required to restore and clean up from files used for setting metadata externally
        self.external_output_metadata = metadata.JobExternalOutputMetadataWrapper( job )
        self.params = None
        if job.params:
            self.params = from_json_string( job.params )

        self.__user_system_pwent = None
        self.__galaxy_system_pwent = None

    def get_job_runner( self ):
        return self.tool.get_job_runner( self.params )

    def get_job( self ):
        return self.sa_session.query( model.Job ).get( self.job_id )

    def get_id_tag(self):
        # For compatability with drmaa, which uses job_id right now, and TaskWrapper
        return str(self.job_id)

    def get_param_dict( self ):
        """
        Restore the dictionary of parameters from the database.
        """
        job = self.get_job()
        param_dict = dict( [ ( p.name, p.value ) for p in job.parameters ] )
        param_dict = self.tool.params_from_strings( param_dict, self.app )
        return param_dict

    def get_version_string_path( self ):
        return os.path.abspath(os.path.join(self.app.config.new_file_path, "GALAXY_VERSION_STRING_%s" % self.job_id))

    def prepare( self ):
        """
        Prepare the job to run by creating the working directory and the
        config files.
        """
        self.sa_session.expunge_all() #this prevents the metadata reverting that has been seen in conjunction with the PBS job runner

        if not os.path.exists( self.working_directory ):
            os.mkdir( self.working_directory )

        # Restore parameters from the database
        job = self.get_job()
        if job.user is None and job.galaxy_session is None:
            raise Exception( 'Job %s has no user and no session.' % job.id )

        incoming = dict( [ ( p.name, p.value ) for p in job.parameters ] )
        incoming = self.tool.params_from_strings( incoming, self.app )
        # Do any validation that could not be done at job creation
        self.tool.handle_unvalidated_param_values( incoming, self.app )
        # Restore input / output data lists
        inp_data = dict( [ ( da.name, da.dataset ) for da in job.input_datasets ] )
        out_data = dict( [ ( da.name, da.dataset ) for da in job.output_datasets ] )
        inp_data.update( [ ( da.name, da.dataset ) for da in job.input_library_datasets ] )
        out_data.update( [ ( da.name, da.dataset ) for da in job.output_library_datasets ] )

        # Set up output dataset association for export history jobs. Because job
        # uses a Dataset rather than an HDA or LDA, it's necessary to set up a
        # fake dataset association that provides the needed attributes for
        # preparing a job.
        class FakeDatasetAssociation ( object ):
            def __init__( self, dataset=None ):
                self.dataset = dataset
                self.file_name = dataset.file_name
                self.metadata = dict()
                self.children = []
        special = self.sa_session.query( model.JobExportHistoryArchive ).filter_by( job=job ).first()
        if not special:
            special = self.sa_session.query( model.GenomeIndexToolData ).filter_by( job=job ).first()
        if special:
            out_data[ "output_file" ] = FakeDatasetAssociation( dataset=special.dataset )
            
        # These can be passed on the command line if wanted as $userId $userEmail
        if job.history and job.history.user: # check for anonymous user!
            userId = '%d' % job.history.user.id
            userEmail = str(job.history.user.email)
        else:
            userId = 'Anonymous'
            userEmail = 'Anonymous'
        incoming['__user_id__'] = incoming['userId'] = userId
        incoming['__user_email__'] = incoming['userEmail'] = userEmail
        # Build params, done before hook so hook can use
        param_dict = self.tool.build_param_dict( incoming, inp_data, out_data, self.get_output_fnames(), self.working_directory )
        # Certain tools require tasks to be completed prior to job execution
        # ( this used to be performed in the "exec_before_job" hook, but hooks are deprecated ).
        self.tool.exec_before_job( self.queue.app, inp_data, out_data, param_dict )
        # Run the before queue ("exec_before_job") hook
        self.tool.call_hook( 'exec_before_job', self.queue.app, inp_data=inp_data,
                             out_data=out_data, tool=self.tool, param_dict=incoming)
        self.sa_session.flush()
        # Build any required config files
        config_filenames = self.tool.build_config_files( param_dict, self.working_directory )
        # FIXME: Build the param file (might return None, DEPRECATED)
        param_filename = self.tool.build_param_file( param_dict, self.working_directory )
        # Build the job's command line
        self.command_line = self.tool.build_command_line( param_dict )
        # FIXME: for now, tools get Galaxy's lib dir in their path
        if self.command_line and self.command_line.startswith( 'python' ):
            self.galaxy_lib_dir = os.path.abspath( "lib" ) # cwd = galaxy root
        # Shell fragment to inject dependencies
        if self.app.config.use_tool_dependencies:
            self.dependency_shell_commands = self.tool.build_dependency_shell_commands()
        else:
            self.dependency_shell_commands = None
        # We need command_line persisted to the db in order for Galaxy to re-queue the job
        # if the server was stopped and restarted before the job finished
        job.command_line = self.command_line
        self.sa_session.add( job )
        self.sa_session.flush()
        # Return list of all extra files
        extra_filenames = config_filenames
        if param_filename is not None:
            extra_filenames.append( param_filename )
        self.param_dict = param_dict
        self.extra_filenames = extra_filenames
        self.version_string_cmd = self.tool.version_string_cmd
        return extra_filenames

    def fail( self, message, exception=False ):
        """
        Indicate job failure by setting state and message on all output
        datasets.
        """
        job = self.get_job()
        self.sa_session.refresh( job )
        # if the job was deleted, don't fail it
        if not job.state == job.states.DELETED:
            # Check if the failure is due to an exception
            if exception:
                # Save the traceback immediately in case we generate another
                # below
                job.traceback = traceback.format_exc()
                # Get the exception and let the tool attempt to generate
                # a better message
                etype, evalue, tb =  sys.exc_info()
                m = self.tool.handle_job_failure_exception( evalue )
                if m:
                    message = m
            if self.app.config.outputs_to_working_directory:
                for dataset_path in self.get_output_fnames():
                    try:
                        shutil.move( dataset_path.false_path, dataset_path.real_path )
                        log.debug( "fail(): Moved %s to %s" % ( dataset_path.false_path, dataset_path.real_path ) )
                    except ( IOError, OSError ), e:
                        log.error( "fail(): Missing output file in working directory: %s" % e )
            for dataset_assoc in job.output_datasets + job.output_library_datasets:
                dataset = dataset_assoc.dataset
                self.sa_session.refresh( dataset )
                dataset.state = dataset.states.ERROR
                dataset.blurb = 'tool error'
                dataset.info = message
                dataset.set_size()
                dataset.dataset.set_total_size()
                if dataset.ext == 'auto':
                    dataset.extension = 'data'
                # Update (non-library) job output datasets through the object store
                if dataset not in job.output_library_datasets:
                    self.app.object_store.update_from_file(dataset.dataset, create=True)
                self.sa_session.add( dataset )
                self.sa_session.flush()
            job.state = job.states.ERROR
            job.command_line = self.command_line
            job.info = message
            self.sa_session.add( job )
            self.sa_session.flush()
        #Perform email action even on failure.
        for pja in [pjaa.post_job_action for pjaa in job.post_job_actions if pjaa.post_job_action.action_type == "EmailAction"]:
            ActionBox.execute(self.app, self.sa_session, pja, job)
        # If the job was deleted, call tool specific fail actions (used for e.g. external metadata) and clean up
        if self.tool:
            self.tool.job_failed( self, message, exception )
        if self.app.config.cleanup_job == 'always' or (self.app.config.cleanup_job == 'onsuccess' and job.state == job.states.DELETED):
            self.cleanup()

    def change_state( self, state, info = False ):
        job = self.get_job()
        self.sa_session.refresh( job )
        for dataset_assoc in job.output_datasets + job.output_library_datasets:
            dataset = dataset_assoc.dataset
            self.sa_session.refresh( dataset )
            dataset.state = state
            if info:
                dataset.info = info
            self.sa_session.add( dataset )
            self.sa_session.flush()
        if info:
            job.info = info
        job.state = state
        self.sa_session.add( job )
        self.sa_session.flush()

    def get_state( self ):
        job = self.get_job()
        self.sa_session.refresh( job )
        return job.state

    def set_runner( self, runner_url, external_id ):
        job = self.get_job()
        self.sa_session.refresh( job )
        job.job_runner_name = runner_url
        job.job_runner_external_id = external_id
        self.sa_session.add( job )
        self.sa_session.flush()

    def finish( self, stdout, stderr ):
        """
        Called to indicate that the associated command has been run. Updates
        the output datasets based on stderr and stdout from the command, and
        the contents of the output files.
        """
        # default post job setup
        self.sa_session.expunge_all()
        job = self.get_job()

        try:
            self.reclaim_ownership()
        except:
            self.fail( job.info )
            log.exception( '(%s) Failed to change ownership of %s, failing' % ( job.id, self.working_directory ) )

        # if the job was deleted, don't finish it
        if job.state == job.states.DELETED or job.state == job.states.ERROR:
            #ERROR at this point means the job was deleted by an administrator.
            return self.fail( job.info )
        if stderr:
            job.state = job.states.ERROR
        else:
            job.state = job.states.OK
        if self.version_string_cmd:
            version_filename = self.get_version_string_path()
            if os.path.exists(version_filename):
                self.version_string = open(version_filename).read()
                os.unlink(version_filename)

        if self.app.config.outputs_to_working_directory and not self.__link_file_check():
            for dataset_path in self.get_output_fnames():
                try:
                    shutil.move( dataset_path.false_path, dataset_path.real_path )
                    log.debug( "finish(): Moved %s to %s" % ( dataset_path.false_path, dataset_path.real_path ) )
                except ( IOError, OSError ):
                    # this can happen if Galaxy is restarted during the job's
                    # finish method - the false_path file has already moved,
                    # and when the job is recovered, it won't be found.
                    if os.path.exists( dataset_path.real_path ) and os.stat( dataset_path.real_path ).st_size > 0:
                        log.warning( "finish(): %s not found, but %s is not empty, so it will be used instead" % ( dataset_path.false_path, dataset_path.real_path ) )
                    else:
                        return self.fail( "Job %s's output dataset(s) could not be read" % job.id )
        job_context = ExpressionContext( dict( stdout = stdout, stderr = stderr ) )
        job_tool = self.app.toolbox.tools_by_id.get( job.tool_id, None )
        def in_directory( file, directory ):
            # Make both absolute.
            directory = os.path.abspath( directory )
            file = os.path.abspath( file )

            #Return true, if the common prefix of both is equal to directory
            #e.g. /a/b/c/d.rst and directory is /a/b, the common prefix is /a/b
            return os.path.commonprefix( [ file, directory ] ) == directory
        for dataset_assoc in job.output_datasets + job.output_library_datasets:
            context = self.get_dataset_finish_context( job_context, dataset_assoc.dataset.dataset )
            #should this also be checking library associations? - can a library item be added from a history before the job has ended? - lets not allow this to occur
            for dataset in dataset_assoc.dataset.dataset.history_associations + dataset_assoc.dataset.dataset.library_associations: #need to update all associated output hdas, i.e. history was shared with job running
                #
                # If HDA is to be copied from the working directory, do it now so that other attributes are correctly set.
                #
                if isinstance( dataset, model.HistoryDatasetAssociation ):
                    joda = self.sa_session.query( model.JobToOutputDatasetAssociation ).filter_by( job=job, dataset=dataset ).first()
                    if joda and job_tool:
                        hda_tool_output = job_tool.outputs.get( joda.name, None )
                        if hda_tool_output and hda_tool_output.from_work_dir:
                            # Copy from working dir to HDA.
                            source_file = os.path.join( os.path.abspath( self.working_directory ), hda_tool_output.from_work_dir )
                            if in_directory( source_file, self.working_directory ):
                                try:
                                    shutil.move( source_file, dataset.file_name )
                                    log.debug( "finish(): Moved %s to %s as directed by from_work_dir" % ( source_file, dataset.file_name ) )
                                except ( IOError, OSError ):
                                    log.debug( "finish(): Could not move %s to %s as directed by from_work_dir" % ( source_file, dataset.file_name ) )
                            else:
                                # Security violation.
                                log.exception( "from_work_dir specified a location not in the working directory: %s, %s" % ( source_file, self.working_directory ) )

                dataset.blurb = 'done'
                dataset.peek  = 'no peek'
                dataset.info = ( dataset.info  or '' ) + context['stdout'] + context['stderr']
                dataset.tool_version = self.version_string
                dataset.set_size()
                # Update (non-library) job output datasets through the object store
                if dataset not in job.output_library_datasets:
                    self.app.object_store.update_from_file(dataset.dataset, create=True)
                if context['stderr']:
                    dataset.blurb = "error"
                elif dataset.has_data():
                    # If the tool was expected to set the extension, attempt to retrieve it
                    if dataset.ext == 'auto':
                        dataset.extension = context.get( 'ext', 'data' )
                        dataset.init_meta( copy_from=dataset )
                    #if a dataset was copied, it won't appear in our dictionary:
                    #either use the metadata from originating output dataset, or call set_meta on the copies
                    #it would be quicker to just copy the metadata from the originating output dataset,
                    #but somewhat trickier (need to recurse up the copied_from tree), for now we'll call set_meta()
                    if not self.app.config.set_metadata_externally or \
                     ( not self.external_output_metadata.external_metadata_set_successfully( dataset, self.sa_session ) \
                       and self.app.config.retry_metadata_internally ):
                        dataset.set_meta( overwrite = False )
                    elif not self.external_output_metadata.external_metadata_set_successfully( dataset, self.sa_session ) and not context['stderr']:
                        dataset._state = model.Dataset.states.FAILED_METADATA
                    else:
                        #load metadata from file
                        #we need to no longer allow metadata to be edited while the job is still running,
                        #since if it is edited, the metadata changed on the running output will no longer match
                        #the metadata that was stored to disk for use via the external process,
                        #and the changes made by the user will be lost, without warning or notice
                        dataset.metadata.from_JSON_dict( self.external_output_metadata.get_output_filenames_by_dataset( dataset, self.sa_session ).filename_out )
                    try:
                        assert context.get( 'line_count', None ) is not None
                        if ( not dataset.datatype.composite_type and dataset.dataset.is_multi_byte() ) or self.tool.is_multi_byte:
                            dataset.set_peek( line_count=context['line_count'], is_multi_byte=True )
                        else:
                            dataset.set_peek( line_count=context['line_count'] )
                    except:
                        if ( not dataset.datatype.composite_type and dataset.dataset.is_multi_byte() ) or self.tool.is_multi_byte:
                            dataset.set_peek( is_multi_byte=True )
                        else:
                            dataset.set_peek()
                    try:
                        # set the name if provided by the tool
                        dataset.name = context['name']
                    except:
                        pass
                else:
                    dataset.blurb = "empty"
                    if dataset.ext == 'auto':
                        dataset.extension = 'txt'
                self.sa_session.add( dataset )
            if context['stderr']:
                dataset_assoc.dataset.dataset.state = model.Dataset.states.ERROR
            else:
                dataset_assoc.dataset.dataset.state = model.Dataset.states.OK
            # If any of the rest of the finish method below raises an
            # exception, the fail method will run and set the datasets to
            # ERROR.  The user will never see that the datasets are in error if
            # they were flushed as OK here, since upon doing so, the history
            # panel stops checking for updates.  So allow the
            # self.sa_session.flush() at the bottom of this method set
            # the state instead.

        for pja in job.post_job_actions:
            ActionBox.execute(self.app, self.sa_session, pja.post_job_action, job)
        # Flush all the dataset and job changes above.  Dataset state changes
        # will now be seen by the user.
        self.sa_session.flush()
        # Save stdout and stderr
        if len( stdout ) > 32768:
            log.error( "stdout for job %d is greater than 32K, only first part will be logged to database" % job.id )
        job.stdout = stdout[:32768]
        if len( stderr ) > 32768:
            log.error( "stderr for job %d is greater than 32K, only first part will be logged to database" % job.id )
        job.stderr = stderr[:32768]
        # custom post process setup
        inp_data = dict( [ ( da.name, da.dataset ) for da in job.input_datasets ] )
        out_data = dict( [ ( da.name, da.dataset ) for da in job.output_datasets ] )
        inp_data.update( [ ( da.name, da.dataset ) for da in job.input_library_datasets ] )
        out_data.update( [ ( da.name, da.dataset ) for da in job.output_library_datasets ] )
        param_dict = dict( [ ( p.name, p.value ) for p in job.parameters ] ) # why not re-use self.param_dict here? ##dunno...probably should, this causes tools.parameters.basic.UnvalidatedValue to be used in following methods instead of validated and transformed values during i.e. running workflows
        param_dict = self.tool.params_from_strings( param_dict, self.app )
        # Check for and move associated_files
        self.tool.collect_associated_files(out_data, self.working_directory)
        gitd = self.sa_session.query( model.GenomeIndexToolData ).filter_by( job=job ).first()
        if gitd:
            self.tool.collect_associated_files({'' : gitd}, self.working_directory)
        # Create generated output children and primary datasets and add to param_dict
        collected_datasets = {'children':self.tool.collect_child_datasets(out_data, self.working_directory),'primary':self.tool.collect_primary_datasets(out_data, self.working_directory)}
        param_dict.update({'__collected_datasets__':collected_datasets})
        # Certain tools require tasks to be completed after job execution
        # ( this used to be performed in the "exec_after_process" hook, but hooks are deprecated ).
        self.tool.exec_after_process( self.queue.app, inp_data, out_data, param_dict, job = job )
        # Call 'exec_after_process' hook
        self.tool.call_hook( 'exec_after_process', self.queue.app, inp_data=inp_data,
                             out_data=out_data, param_dict=param_dict,
                             tool=self.tool, stdout=stdout, stderr=stderr )
        job.command_line = self.command_line

        bytes = 0
        # Once datasets are collected, set the total dataset size (includes extra files)
        for dataset_assoc in job.output_datasets:
            dataset_assoc.dataset.dataset.set_total_size()
            bytes += dataset_assoc.dataset.dataset.get_total_size()

        if job.user:
            job.user.total_disk_usage += bytes

        # fix permissions
        for path in [ dp.real_path for dp in self.get_output_fnames() ]:
            util.umask_fix_perms( path, self.app.config.umask, 0666, self.app.config.gid )
        self.sa_session.flush()
        log.debug( 'job %d ended' % self.job_id )
        if self.app.config.cleanup_job == 'always' or ( not stderr and self.app.config.cleanup_job == 'onsuccess' ):
            self.cleanup()

    def cleanup( self ):
        # remove temporary files
        try:
            for fname in self.extra_filenames:
                os.remove( fname )
            if self.app.config.set_metadata_externally:
                self.external_output_metadata.cleanup_external_metadata( self.sa_session )
            galaxy.tools.imp_exp.JobExportHistoryArchiveWrapper( self.job_id ).cleanup_after_job( self.sa_session )
            galaxy.tools.imp_exp.JobImportHistoryArchiveWrapper( self.job_id ).cleanup_after_job( self.sa_session )
            galaxy.tools.genome_index.GenomeIndexToolWrapper( self.job_id ).postprocessing( self.sa_session, self.app )
            self.app.object_store.delete(self.get_job(), base_dir='job_work', entire_dir=True, dir_only=True, extra_dir=str(self.job_id))
        except:
            log.exception( "Unable to cleanup job %d" % self.job_id )

    def get_command_line( self ):
        return self.command_line

    def get_session_id( self ):
        return self.session_id

    def get_env_setup_clause( self ):
        if self.app.config.environment_setup_file is None:
            return ''
        return '[ -f "%s" ] && . %s' % ( self.app.config.environment_setup_file, self.app.config.environment_setup_file )

    def get_input_dataset_fnames( self,  ds ):
        filenames = []
        filenames = [ ds.file_name ]
        #we will need to stage in metadata file names also
        #TODO: would be better to only stage in metadata files that are actually needed (found in command line, referenced in config files, etc.)
        for key, value in ds.metadata.items():
            if isinstance( value, model.MetadataFile ):
                filenames.append( value.file_name )
        return filenames

    def get_input_fnames( self ):
        job = self.get_job()
        filenames = []
        for da in job.input_datasets + job.input_library_datasets: #da is JobToInputDatasetAssociation object
            if da.dataset:
                filenames.extend(self.get_input_dataset_fnames(da.dataset))
        return filenames

    def get_output_fnames( self ):
        if self.output_paths is None:
            self.compute_outputs()
        return self.output_paths

    def get_output_hdas_and_fnames( self ):
        if self.output_hdas_and_paths is None:
            self.compute_outputs()
        return self.output_hdas_and_paths

    def compute_outputs( self ) :
        class DatasetPath( object ):
            def __init__( self, dataset_id, real_path, false_path = None ):
                self.dataset_id = dataset_id
                self.real_path = real_path
                self.false_path = false_path
            def __str__( self ):
                if self.false_path is None:
                    return self.real_path
                else:
                    return self.false_path
        job = self.get_job()
        # Job output datasets are combination of history, library, jeha and gitd datasets.
        special = self.sa_session.query( model.JobExportHistoryArchive ).filter_by( job=job ).first()
        if not special:
            special = self.sa_session.query( model.GenomeIndexToolData ).filter_by( job=job ).first()
        false_path = None
        if self.app.config.outputs_to_working_directory:
            self.output_paths = []
            self.output_hdas_and_paths = {}
            for name, hda in [ ( da.name, da.dataset ) for da in job.output_datasets + job.output_library_datasets ]:
                false_path = os.path.abspath( os.path.join( self.working_directory, "galaxy_dataset_%d.dat" % hda.dataset.id ) )
                dsp = DatasetPath( hda.dataset.id, hda.dataset.file_name, false_path )
                self.output_paths.append( dsp )
                self.output_hdas_and_paths[name] = hda, dsp
            if special:
                false_path = os.path.abspath( os.path.join( self.working_directory, "galaxy_dataset_%d.dat" % special.dataset.id ) )
        else:
            results = [ ( da.name, da.dataset, DatasetPath( da.dataset.dataset.id, da.dataset.file_name ) ) for da in job.output_datasets + job.output_library_datasets ]
            self.output_paths = [t[2] for t in results]
            self.output_hdas_and_paths = dict([(t[0],  t[1:]) for t in results])
        if special:
            dsp = DatasetPath( special.dataset.id, special.dataset.file_name, false_path )
            self.output_paths.append( dsp )
        return self.output_paths

    def get_output_file_id( self, file ):
        if self.output_paths is None:
            self.get_output_fnames()
        for dp in self.output_paths:
            if self.app.config.outputs_to_working_directory and os.path.basename( dp.false_path ) == file:
                return dp.dataset_id
            elif os.path.basename( dp.real_path ) == file:
                return dp.dataset_id
        return None

    def get_tool_provided_job_metadata( self ):
        if self.tool_provided_job_metadata is not None:
            return self.tool_provided_job_metadata

        # Look for JSONified job metadata
        self.tool_provided_job_metadata = []
        meta_file = os.path.join( self.working_directory, TOOL_PROVIDED_JOB_METADATA_FILE )
        if os.path.exists( meta_file ):
            for line in open( meta_file, 'r' ):
                try:
                    line = from_json_string( line )
                    assert 'type' in line
                except:
                    log.exception( '(%s) Got JSON data from tool, but data is improperly formatted or no "type" key in data' % self.job_id )
                    log.debug( 'Offending data was: %s' % line )
                    continue
                # Set the dataset id if it's a dataset entry and isn't set.
                # This isn't insecure.  We loop the job's output datasets in
                # the finish method, so if a tool writes out metadata for a
                # dataset id that it doesn't own, it'll just be ignored.
                if line['type'] == 'dataset' and 'dataset_id' not in line:
                    try:
                        line['dataset_id'] = self.get_output_file_id( line['dataset'] )
                    except KeyError:
                        log.warning( '(%s) Tool provided job dataset-specific metadata without specifying a dataset' % self.job_id )
                        continue
                self.tool_provided_job_metadata.append( line )
        return self.tool_provided_job_metadata

    def get_dataset_finish_context( self, job_context, dataset ):
        for meta in self.get_tool_provided_job_metadata():
            if meta['type'] == 'dataset' and meta['dataset_id'] == dataset.id:
                return ExpressionContext( meta, job_context )
        return job_context

    def check_output_sizes( self ):
        sizes = []
        output_paths = self.get_output_fnames()
        for outfile in [ str( o ) for o in output_paths ]:
            if os.path.exists( outfile ):
                sizes.append( ( outfile, os.stat( outfile ).st_size ) )
            else:
                sizes.append( ( outfile, 0 ) )
        return sizes

    def setup_external_metadata( self, exec_dir=None, tmp_dir=None, dataset_files_path=None, config_root=None, config_file=None, datatypes_config=None, set_extension=True, **kwds ):
        # extension could still be 'auto' if this is the upload tool.
        job = self.get_job()
        if set_extension:
            for output_dataset_assoc in job.output_datasets:
                if output_dataset_assoc.dataset.ext == 'auto':
                    context = self.get_dataset_finish_context( dict(), output_dataset_assoc.dataset.dataset )
                    output_dataset_assoc.dataset.extension = context.get( 'ext', 'data' )
            self.sa_session.flush()
        if tmp_dir is None:
            #this dir should should relative to the exec_dir
            tmp_dir = self.app.config.new_file_path
        if dataset_files_path is None:
            dataset_files_path = self.app.model.Dataset.file_path
        if config_root is None:
            config_root = self.app.config.root
        if config_file is None:
            config_file = self.app.config.config_file
        if datatypes_config is None:
            datatypes_config = self.app.datatypes_registry.integrated_datatypes_configs
        return self.external_output_metadata.setup_external_metadata( [ output_dataset_assoc.dataset for output_dataset_assoc in job.output_datasets ],
                                                                      self.sa_session,
                                                                      exec_dir = exec_dir,
                                                                      tmp_dir = tmp_dir,
                                                                      dataset_files_path = dataset_files_path,
                                                                      config_root = config_root,
                                                                      config_file = config_file,
                                                                      datatypes_config = datatypes_config,
                                                                      job_metadata = os.path.join( self.working_directory, TOOL_PROVIDED_JOB_METADATA_FILE ),
                                                                      **kwds )

    @property
    def user( self ):
        job = self.get_job()
        if job.user is not None:
            return job.user.email
        elif job.galaxy_session is not None and job.galaxy_session.user is not None:
            return job.galaxy_session.user.email
        elif job.history is not None and job.history.user is not None:
            return job.history.user.email
        elif job.galaxy_session is not None:
            return 'anonymous@' + job.galaxy_session.remote_addr.split()[-1]
        else:
            return 'anonymous@unknown'

    def __link_file_check( self ):
        """ outputs_to_working_directory breaks library uploads where data is
        linked.  This method is a hack that solves that problem, but is
        specific to the upload tool and relies on an injected job param.  This
        method should be removed ASAP and replaced with some properly generic
        and stateful way of determining link-only datasets. -nate
        """
        job = self.get_job()
        param_dict = job.get_param_values( self.app )
        return self.tool.id == 'upload1' and param_dict.get( 'link_data_only', None ) == 'link_to_files'

    def _change_ownership( self, username, gid ):
        job = self.get_job()
        # FIXME: hardcoded path
        cmd = [ '/usr/bin/sudo', '-E', self.app.config.external_chown_script, self.working_directory, username, str( gid ) ]
        log.debug( '(%s) Changing ownership of working directory with: %s' % ( job.id, ' '.join( cmd ) ) )
        p = subprocess.Popen( cmd, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE )
        # TODO: log stdout/stderr
        stdout, stderr = p.communicate()
        assert p.returncode == 0

    def change_ownership_for_run( self ):
        job = self.get_job()
        if self.app.config.external_chown_script and job.user is not None:
            try:
                self._change_ownership( self.user_system_pwent[0], str( self.user_system_pwent[3] ) )
            except:
                log.exception( '(%s) Failed to change ownership of %s, making world-writable instead' % ( job.id, self.working_directory ) )
                os.chmod( self.working_directory, 0777 )

    def reclaim_ownership( self ):
        job = self.get_job()
        if self.app.config.external_chown_script and job.user is not None:
            self._change_ownership( self.galaxy_system_pwent[0], str( self.galaxy_system_pwent[3] ) )

    @property
    def user_system_pwent( self ):
        if self.__user_system_pwent is None:
            job = self.get_job()
            try:
                self.__user_system_pwent = pwd.getpwnam( job.user.email.split('@')[0] )
            except:
                pass
        return self.__user_system_pwent

    @property
    def galaxy_system_pwent( self ):
        if self.__galaxy_system_pwent is None:
            self.__galaxy_system_pwent = pwd.getpwuid(os.getuid())
        return self.__galaxy_system_pwent

class TaskWrapper(JobWrapper):
    """
    Extension of JobWrapper intended for running tasks.
    Should be refactored into a generalized executable unit wrapper parent, then jobs and tasks.
    """
    # Abstract this to be more useful for running tasks that *don't* necessarily compose a job.

    def __init__(self, task, queue):
        super(TaskWrapper, self).__init__(task.job, queue)
        self.task_id = task.id
        self.working_directory = task.working_directory
        if task.prepare_input_files_cmd is not None:
            self.prepare_input_files_cmds = [ task.prepare_input_files_cmd ]
        else:
            self.prepare_input_files_cmds = None
        self.status = task.states.NEW

    def get_job( self ):
        if self.job_id:
            return self.sa_session.query( model.Job ).get( self.job_id )
        else:
            return None

    def get_task( self ):
        return self.sa_session.query(model.Task).get(self.task_id)

    def get_id_tag(self):
        # For compatibility with drmaa job runner and TaskWrapper, instead of using job_id directly
        return "%s_%s" % (self.job_id, self.task_id)

    def get_param_dict( self ):
        """
        Restore the dictionary of parameters from the database.
        """
        job = self.sa_session.query( model.Job ).get( self.job_id )
        param_dict = dict( [ ( p.name, p.value ) for p in job.parameters ] )
        param_dict = self.tool.params_from_strings( param_dict, self.app )
        return param_dict

    def prepare( self ):
        """
        Prepare the job to run by creating the working directory and the
        config files.
        """
        # Restore parameters from the database
        job = self.get_job()
        task = self.get_task()
        if job.user is None and job.galaxy_session is None:
            raise Exception( 'Job %s has no user and no session.' % job.id )
        incoming = dict( [ ( p.name, p.value ) for p in job.parameters ] )
        incoming = self.tool.params_from_strings( incoming, self.app )
        # Do any validation that could not be done at job creation
        self.tool.handle_unvalidated_param_values( incoming, self.app )
        # Restore input / output data lists
        inp_data = dict( [ ( da.name, da.dataset ) for da in job.input_datasets ] )
        out_data = dict( [ ( da.name, da.dataset ) for da in job.output_datasets ] )
        inp_data.update( [ ( da.name, da.dataset ) for da in job.input_library_datasets ] )
        out_data.update( [ ( da.name, da.dataset ) for da in job.output_library_datasets ] )
        # DBTODO New method for generating command line for a task?
        # These can be passed on the command line if wanted as $userId $userEmail
        if job.history and job.history.user: # check for anonymous user!
            userId = '%d' % job.history.user.id
            userEmail = str(job.history.user.email)
        else:
            userId = 'Anonymous'
            userEmail = 'Anonymous'
        incoming['userId'] = userId
        incoming['userEmail'] = userEmail
        # Build params, done before hook so hook can use
        param_dict = self.tool.build_param_dict( incoming, inp_data, out_data, self.get_output_fnames(), self.working_directory )
        fnames = {}
        for v in self.get_input_fnames():
            fnames[v] = os.path.join(self.working_directory, os.path.basename(v))
        for dp in [x.real_path for x in self.get_output_fnames()]:
            fnames[dp] = os.path.join(self.working_directory, os.path.basename(dp))
        # Certain tools require tasks to be completed prior to job execution
        # ( this used to be performed in the "exec_before_job" hook, but hooks are deprecated ).
        self.tool.exec_before_job( self.queue.app, inp_data, out_data, param_dict )
        # Run the before queue ("exec_before_job") hook
        self.tool.call_hook( 'exec_before_job', self.queue.app, inp_data=inp_data,
                             out_data=out_data, tool=self.tool, param_dict=incoming)
        self.sa_session.flush()
        # Build any required config files
        config_filenames = self.tool.build_config_files( param_dict, self.working_directory )
        # FIXME: Build the param file (might return None, DEPRECATED)
        param_filename = self.tool.build_param_file( param_dict, self.working_directory )
        # Build the job's command line
        self.command_line = self.tool.build_command_line( param_dict )
        # HACK, Fix this when refactored.
        for k, v in fnames.iteritems():
            self.command_line = self.command_line.replace(k, v)
        # FIXME: for now, tools get Galaxy's lib dir in their path
        if self.command_line and self.command_line.startswith( 'python' ):
            self.galaxy_lib_dir = os.path.abspath( "lib" ) # cwd = galaxy root
        # Shell fragment to inject dependencies
        if self.app.config.use_tool_dependencies:
            self.dependency_shell_commands = self.tool.build_dependency_shell_commands()
        else:
            self.dependency_shell_commands = None
        # We need command_line persisted to the db in order for Galaxy to re-queue the job
        # if the server was stopped and restarted before the job finished
        task.command_line = self.command_line
        self.sa_session.add( task )
        self.sa_session.flush()
        # # Return list of all extra files
        extra_filenames = config_filenames
        if param_filename is not None:
            extra_filenames.append( param_filename )
        self.param_dict = param_dict
        self.extra_filenames = extra_filenames
        self.status = 'prepared'
        return extra_filenames

    def fail( self, message, exception=False ):
        log.error("TaskWrapper Failure %s" % message)
        self.status = 'error'
        # How do we want to handle task failure?  Fail the job and let it clean up?

    def change_state( self, state, info = False ):
        task = self.get_task()
        self.sa_session.refresh( task )
        if info:
            task.info = info
        task.state = state
        self.sa_session.add( task )
        self.sa_session.flush()

    def get_state( self ):
        task = self.get_task()
        self.sa_session.refresh( task )
        return task.state

    def set_runner( self, runner_url, external_id ):
        task = self.get_task()
        self.sa_session.refresh( task )
        task.task_runner_name = runner_url
        task.task_runner_external_id = external_id
        # DBTODO Check task job_runner_stuff
        self.sa_session.add( task )
        self.sa_session.flush()

    def finish( self, stdout, stderr ):
        # DBTODO integrate previous finish logic.
        # Simple finish for tasks.  Just set the flag OK.
        log.debug( 'task %s for job %d ended' % (self.task_id, self.job_id) )
        """
        Called to indicate that the associated command has been run. Updates
        the output datasets based on stderr and stdout from the command, and
        the contents of the output files.
        """
        # default post job setup_external_metadata
        self.sa_session.expunge_all()
        task = self.get_task()
        # if the job was deleted, don't finish it
        if task.state == task.states.DELETED:
            if self.app.config.cleanup_job in ( 'always', 'onsuccess' ):
                self.cleanup()
            return
        elif task.state == task.states.ERROR:
            # Job was deleted by an administrator
            self.fail( task.info )
            return
        if stderr:
            task.state = task.states.ERROR
        else:
            task.state = task.states.OK
        # Save stdout and stderr
        if len( stdout ) > 32768:
            log.error( "stdout for task %d is greater than 32K, only first part will be logged to database" % task.id )
        task.stdout = stdout[:32768]
        if len( stderr ) > 32768:
            log.error( "stderr for job %d is greater than 32K, only first part will be logged to database" % task.id )
        task.stderr = stderr[:32768]
        task.command_line = self.command_line
        self.sa_session.flush()
        log.debug( 'task %d ended' % self.task_id )

    def cleanup( self ):
        # There is no task cleanup.  The job cleans up for all tasks.
        pass

    def get_command_line( self ):
        return self.command_line

    def get_session_id( self ):
        return self.session_id

    def get_output_file_id( self, file ):
        # There is no permanent output file for tasks.
        return None

    def get_tool_provided_job_metadata( self ):
        # DBTODO Handle this as applicable for tasks.
        return None

    def get_dataset_finish_context( self, job_context, dataset ):
        # Handled at the parent job level.  Do nothing here.
        pass

    def check_output_sizes( self ):
        sizes = []
        output_paths = self.get_output_fnames()
        for outfile in [ str( o ) for o in output_paths ]:
            if os.path.exists( outfile ):
                sizes.append( ( outfile, os.stat( outfile ).st_size ) )
            else:
                sizes.append( ( outfile, 0 ) )
        return sizes

    def setup_external_metadata( self, exec_dir=None, tmp_dir=None, dataset_files_path=None, config_root=None, config_file=None, datatypes_config=None, set_extension=True, **kwds ):
        # There is no metadata setting for tasks.  This is handled after the merge, at the job level.
        return ""

class NoopQueue( object ):
    """
    Implements the JobQueue / JobStopQueue interface but does nothing
    """
    def put( self, *args ):
        return
    def put_stop( self, *args ):
        return
    def shutdown( self ):
        return
