import logging

from galaxy import model
from galaxy.authnz.util import provider_name_to_backend
from galaxy.jobs.runners import (
    AsynchronousJobRunner,
    AsynchronousJobState,
)
from galaxy.jobs.runners.util.arc_util import (
    ARCJobBuilder,
    ensure_pyarc,
    get_client,
)

try:
    from pyarcrest.errors import (
        ARCHTTPError,
        NoValueInARCResult,
    )
except ImportError:
    ARCHTTPError = None
    NoValueInARCResult = None

from galaxy.job_execution.compute_environment import (
    ComputeEnvironment,
    dataset_path_to_extra_path,
)
from galaxy.util import unicodify

log = logging.getLogger(__name__)

__all__ = ("ArcRESTJobRunner",)


class Arc:
    """
    API parameters
    """

    def __init__(self):
        self.url = ""

        self.ARC_STATE_MAPPING = {
            "ACCEPTING": "Accepted",
            "Accepted": "Accepted",
            "ACCEPTED": "Accepted",
            "PREPARING": "Preparing",
            "PREPARED": "Preparing",
            "SUBMITTING": "Submitting",
            "QUEUING": "Queuing",
            "RUNNING": "Running",
            "HELD": "Hold",
            "EXITINGLRMS": "Running",
            "OTHER": "Other",
            "EXECUTED": "Running",
            "FINISHING": "Finishing",
            "FINISHED": "Finished",
            "FAILED": "Failed",
            "KILLING": "Killing",
            "KILLED": "Killed",
            "WIPED": "Deleted",
            "None": "Failed",
            "Job not found": "Failed",
        }


class ARCComputeEnvironment(ComputeEnvironment):
    """NB! This is just blunt copy-paste and simplification from pulsar runner.
    Many things are not used, and will not work properly.
    Currently just using input-path rewrite"""

    def __init__(self, job_wrapper):
        self.job_wrapper = job_wrapper

        self.local_path_config = job_wrapper.default_compute_environment()

        self.path_rewrites_input_extra = {}
        self._working_directory = "."
        self._config_directory = "."
        self._home_directory = ""
        self._tool_dir = ""
        self._tmp_directory = ""
        self._shared_home_dir = ""
        self._sep = ""
        self._version_path = ""

    def output_names(self):
        # Maybe this should use the path mapper, but the path mapper just uses basenames
        return self.job_wrapper.job_io.get_output_basenames()

    def input_path_rewrite(self, dataset):
        """
        ARC Jobs run in the ARC remote compute clusters workdir - not known to Galaxy at this point.
        But all input-files are all uploaded (by ARC) to this workdir, so a simple relative  path will work for all ARC jobs
        """
        return f"{str(self._working_directory)}/{str(dataset.get_display_name())}"

    def output_path_rewrite(self, dataset):
        """
        ARC Jobs run in the ARC remote compute clusters workdir - not known to Galaxy at this point.
        But all outputfiles are created in this workdir, so a simple relative  path will work for all ARC jobs
        """
        # return f'{str(self._working_directory)}/{str(dataset.get_file_name())}'
        return f"{str(dataset.get_file_name())}"

    def input_extra_files_rewrite(self, dataset):
        """TODO - find out what this is and if I need it"""
        input_path_rewrite = self.input_path_rewrite(dataset)
        remote_extra_files_path_rewrite = dataset_path_to_extra_path(input_path_rewrite)
        self.path_rewrites_input_extra[dataset.extra_files_path] = remote_extra_files_path_rewrite
        return remote_extra_files_path_rewrite

    def output_extra_files_rewrite(self, dataset):
        """TODO - find out what this is and if I need it"""
        output_path_rewrite = self.output_path_rewrite(dataset)
        remote_extra_files_path_rewrite = dataset_path_to_extra_path(output_path_rewrite)
        return remote_extra_files_path_rewrite

    def input_metadata_rewrite(self, dataset, metadata_val):
        """TODO - find out what this is and if I need it"""
        return None

    def unstructured_path_rewrite(self, parameter_value):
        """TODO - find out what this is and if I need it"""
        return self._working_directory

    def working_directory(self):
        return self._working_directory

    def env_config_directory(self):
        return self._config_directory

    def config_directory(self):
        return self._config_directory

    def new_file_path(self):
        return self._working_directory

    def sep(self):
        return self._sep

    def version_path(self):
        return self._version_path

    def tool_directory(self):
        return self._tool_dir

    def home_directory(self):
        return self._home_directory

    def tmp_directory(self):
        return self._tmp_directory

    def galaxy_url(self):
        return self.job_wrapper.get_destination_configuration("galaxy_infrastructure_url")

    def get_file_sources_dict(self):
        return self.job_wrapper.job_io.file_sources_dict


class ArcRESTJobRunner(AsynchronousJobRunner):
    """
    Job runner backed by a finite pool of worker threads. FIFO scheduling
    """

    runner_name = "ArcRESTJobRunner"

    def __init__(self, app, nworkers, **kwargs):
        """1: Get runner_param_specs from job_conf.xml
        2: Initialise job runner parent object
        3: Start the worker and monitor threads
        """

        # Start the job runner parent object
        super().__init__(app, nworkers, **kwargs)
        ensure_pyarc()

        self.arc = None
        self.arcjob = None
        self.provider_backend = provider_name_to_backend("wlcg")

    def queue_job(self, job_wrapper):
        """When a tool is submitted for execution in galaxy"""
        """ This method
        1. Fetches the configured ARC endpoint for this user
        2. Prepares an ARC job description based on the jobs destination parameters
        3. Submits the job to the remote ARC endpoint via pyarcrest
        4. Adds the job to the galaxy job queue
        """

        job_destination = job_wrapper.job_destination
        job_id = job_wrapper.job_id

        """ Build the command line - needs a rewrite of input-paths as ARC is a remote cluster """
        if not self.prepare_job(
            job_wrapper,
            include_metadata=False,
            include_work_dir_outputs=False,
            modify_command_for_container=False,
            stream_stdout_stderr=False,
        ):
            return
        """ prepare_job() calls prepare() but not allowing to pass a compute_environment object
        As I need to define my own compute_environment for the remote compute I must call it here passing the compute_environment
        TODO - not a good solution"""
        compute_environment = ARCComputeEnvironment(job_wrapper)
        try:
            job_wrapper.prepare(compute_environment)
            job_wrapper.runner_command_line = self.build_command_line(
                job_wrapper,
                include_metadata=False,
                include_work_dir_outputs=False,
                modify_command_for_container=False,
                stream_stdout_stderr=False,
            )
        except Exception as e:
            log.exception("(%s) Failure preparing job", job_id)
            job_wrapper.fail(unicodify(e), exception=True)
            return

        if not job_wrapper.runner_command_line:
            job_wrapper.finish("", "")
            return

        """ Set the ARC endpoint url to submit the job to - extracted from the job_destination parameters in job_conf.xml """
        user_preferences = job_wrapper.get_job().user.extra_preferences
        self.arc = Arc()
        self.arc.url = user_preferences.get("distributed_arc_compute|remote_arc_resources", "None")

        """ Prepare and submit job to arc """
        arc_job = self.prepare_job_arc(job_wrapper)

        token = job_wrapper.get_job().user.get_oidc_tokens(self.provider_backend)["access"]
        self.arcrest = get_client(self.arc.url, token=token)

        delegationID = self.arcrest.createDelegation()

        bulkdesc = "<ActivityDescriptions>"
        bulkdesc += arc_job.descrstr
        bulkdesc += "</ActivityDescriptions>"

        results = self.arcrest.createJobs(bulkdesc, delegationID=delegationID)
        arc_job_id = None

        if isinstance(results[0], ARCHTTPError):
            # submission error
            log.error("Job creation failure.  No Response from ARC")
            job_wrapper.fail("Not submitted")
        else:
            # successful submission
            arc_job_id, status = results[0]
            job_wrapper.set_external_id(arc_job_id)
            log.debug(
                f"Successfully submitted job to remote ARC resource {self.arc.url} with ARC id: {arc_job_id} and Galaxy id: {job_id}"
            )
            # beware! this means 1 worker, no timeout and default upload buffer
            errors = self.arcrest.uploadJobFiles([arc_job_id], [arc_job.inputs])
            if errors[0]:  # input upload error
                log.error("Job creation failure. No Response from ARC")
                log.debug(
                    f"Could not upload job files for job with galaxy-id: {job_id} to ARC resource {self.arc.url}. Error was: {errors[0]}"
                )
                job_wrapper.fail("Not submitted")
            else:
                # successful input upload
                log.debug(
                    f"Successfully uploaded input-files {arc_job.inputs.keys()} to remote ARC resource {self.arc.url} for job with galaxy-id: {job_id} and ARC id: {arc_job_id}"
                )
                # Create an object of AsynchronousJobState and add it to the monitor queue.
                ajs = AsynchronousJobState(
                    files_dir=job_wrapper.working_directory,
                    job_wrapper=job_wrapper,
                    job_id=arc_job_id,
                    job_destination=job_destination,
                )
                self.monitor_queue.put(ajs)

    def place_output_files(self, job_state, job_status_arc):
        """Create log files in galaxy, namely error_file, output_file, exit_code_file
        Return true, if all the file creations are successful
        """

        job_dir = job_state.job_wrapper.working_directory
        galaxy_workdir = job_dir + "/working"
        galaxy_outputs = job_dir + "/outputs"

        arc_job_id = job_state.job_id

        """ job_state.output_file and job_state.error_file is e.g. galaxy_5.e and galaxy_5.o where 5 is the galaxy job id """
        """ Hardcoded out and err files - this is ok. But TODO - need to handle if the tool itself has some stdout that should be kept"""

        """ Galaxy stderr and stdout files need to be poupulated from the arc.out and arc.err files """
        try:
            # Read from ARC output_file and write it into galaxy output_file.
            out_log = ""
            tool_stdout_path = galaxy_outputs + "/tool_stdout"
            with open(galaxy_workdir + "/" + arc_job_id + "/arc.out") as f:
                out_log = f.read()
            with open(job_state.output_file, "a+") as log_file:
                log_file.write(out_log)
                log_file.write("Some hardcoded stdout - as a sample from the arc.py runner.")
            with open(tool_stdout_path, "a+") as tool_stdout:
                tool_stdout.write(out_log)

            # Read from ARC error_file and write it into galaxy error_file.
            err_log = ""
            tool_stderr_path = galaxy_outputs + "/tool_stderr"
            with open(galaxy_workdir + "/" + arc_job_id + "/arc.err") as f:
                err_log = f.read()
            with open(job_state.error_file, "w+") as log_file:
                log_file.write(err_log)
                log_file.write("Some hardcoded stderr - as a sample from the arc.py runner.")
            with open(tool_stderr_path, "w+") as tool_stderr:
                tool_stderr.write(err_log)

        except OSError as e:
            log.error("Could not access task log file: %s", unicodify(e))
            log.debug("IO Error occurred when accessing the files.")
            return False
        return True

    def check_watched_item(self, job_state):
        """Get the job current status from ARC
                using job_id and update the status in galaxy.
        If the job execution is successful, call
                mark_as_finished() and return 'None' to galaxy.
        else if the job failed, call mark_as_failed()
                and return 'None' to galaxy.
        else if the job is running or in pending state, simply
                return the 'AsynchronousJobState object' (job_state).
        """
        """ This function is called by check_watched_items() where
                    param job_state is an object of AsynchronousJobState.
            Expected return type of this function is None or
                    AsynchronousJobState object with updated running status.
        """

        galaxy_job_wrapper = job_state.job_wrapper
        galaxy_workdir = galaxy_job_wrapper.working_directory
        mapped_state = ""

        """ Set the ARC endpoint url to submit the job to - extracted from the job_destination parameters in job_conf.xml """
        user_preferences = galaxy_job_wrapper.get_job().user.extra_preferences
        self.arc = Arc()
        self.arc.url = user_preferences.get("distributed_arc_compute|remote_arc_resources", "None")

        """ Make sure to get a fresh token and client """
        token = self._get_token(galaxy_job_wrapper)
        self.arcrest = get_client(self.arc.url, token=token)

        """ Get task from ARC """
        arc_job_id = job_state.job_id
        arc_job_state = self.arcrest.getJobsStatus([arc_job_id])[0]

        if isinstance(arc_job_state, ARCHTTPError) or isinstance(arc_job_state, NoValueInARCResult):
            return None

        if arc_job_state:
            mapped_state = self.arc.ARC_STATE_MAPPING[arc_job_state]
        else:
            log.debug(f"Could not map state of ARC job with id: {arc_job_id} and Galaxy job id: {job_state.job_id}")
            return None

        self.arcrest = get_client(self.arc.url, token=self._get_token(galaxy_job_wrapper))

        if mapped_state == "Finished":
            job_state.running = False
            galaxy_job_wrapper.change_state(model.Job.states.OK)

            galaxy_outputdir = galaxy_workdir + "/working"
            # self.arcrest.downloadJobFiles(galaxy_outputdir, [arc_job_id])
            self.arcrest.downloadJobFiles(
                galaxy_outputdir, [arc_job_id], outputFilters={f"{arc_job_id}": "(?!user.proxy$)"}
            )

            self.place_output_files(job_state, mapped_state)
            self.mark_as_finished(job_state)

            """The function mark_as_finished() executes:
            self.work_queue.put((self.finish_job, job_state))
            *self.finish_job ->
            job_state.job_wrapper.finish( stdout, stderr, exit_code )
            job_state.job_wrapper.reclaim_ownership()
            job_state.cleanup()
            *self.work_queue.put( method , arg ) ->
            The run_next() method starts execution on starting worker threads.
            This run_next() method executes method(arg)
            by using self.work_queue.get()
            *Possible outcomes of finish_job(job_state) ->
            job_state.job_wrapper.finish( stdout, stderr, exit_code )
            job_state.job_wrapper.fail( "Unable to finish job", exception=True)
            *Similar workflow is done for mark_as_failed() method.
            """
            return None

        elif mapped_state == "Running":
            job_state.running = True
            galaxy_job_wrapper.change_state(model.Job.states.RUNNING)
            return job_state
        elif (
            mapped_state == "Accepted"
            or mapped_state == "Preparing"
            or mapped_state == "Submitting"
            or mapped_state == "Queuing"
            or mapped_state == "Hold"
            or mapped_state == "Other"
        ):
            """Job is in transition status"""
            return job_state
        elif mapped_state == "Killing" or mapped_state == "Killed":
            job_state.running = False
            galaxy_job_wrapper.change_state(model.Job.states.DELETING)
            return job_state
        elif mapped_state == "Failed":
            job_state.running = False
            galaxy_job_wrapper.change_state(model.Job.states.ERROR)
            self.mark_as_failed(job_state)
            return None
        else:
            job_state.running = False
            self.mark_as_failed(job_state)
            return None

    def stop_job(self, job_wrapper):
        """
        TODO: I am not sure this method is working as intended. Is it supposed to be triggered if the user e.g.
        deletes an active job from history?
        I can not see that this method is called then. It seems to only get called once the external job state is
        fetched and rendered as "Finished".

        """
        """ Attempts to delete a dispatched executing Job in ARC """
        """This function is called by fail_job()
           where param job = self.sa_session.query( self.app.model.Job ).get( job_state.job_wrapper.job_id )
           No Return data expected
        """
        job_id = job_wrapper.job_id
        arc_job_id = job_wrapper.get_job().job_runner_external_id

        """ Set the ARC endpoint url to submit the job to - extracted from the job_destination parameters in job_conf.xml """
        user_preferences = job_wrapper.get_job().user.extra_preferences
        self.arc = Arc()
        self.arc.url = user_preferences.get("distributed_arc_compute|remote_arc_resources", "None")

        """ Make sure to get a fresh token and client """
        token = self._get_token(job_wrapper)
        self.arcrest = get_client(self.arc.url, token=token)

        """ Get the current ARC job status from the remote ARC endpoint """
        arc_job_state = self.arcrest.getJobsStatus([arc_job_id])[0]
        if arc_job_state is None:
            return None
        mapped_state = self.arc.ARC_STATE_MAPPING[arc_job_state]
        if not (mapped_state == "Killed" or mapped_state == "Deleted" or mapped_state == "Finished"):
            try:
                # Initiate a delete call,if the job is running in ARC.
                waskilled = self.arcrest.killJobs([arc_job_id])
                f"Job with ARC id: {arc_job_id} and Galaxy id: {job_id} was killed by external request (user or admin). Status waskilld: {waskilled}"
            except Exception as e:
                log.debug(
                    f"Job with ARC id: {arc_job_id} and Galaxy id: {job_id} was attempted killed by external request (user or admin), but this did not succeed. Exception was: {e}"
                )

        return None

    def recover(self, job, job_wrapper):
        """Recovers jobs stuck in the queued/running state when Galaxy started"""
        """ This method is called by galaxy at the time of startup.
            Jobs in Running & Queued status in galaxy are put in the monitor_queue by creating an AsynchronousJobState object
        """
        job_id = job.job_runner_external_id
        ajs = AsynchronousJobState(files_dir=job_wrapper.working_directory, job_wrapper=job_wrapper)
        ajs.job_id = str(job_id)
        ajs.job_destination = job_wrapper.job_destination
        job_wrapper.command_line = job.command_line
        ajs.job_wrapper = job_wrapper
        if job.state == model.Job.states.RUNNING:
            log.debug("({}/{}) is still in running state, adding to the god queue".format(job.id, ajs.job_id))
            ajs.old_state = "R"
            ajs.running = True
            self.monitor_queue.put(ajs)

        elif job.state == model.Job.states.QUEUED:
            log.debug("({}/{}) is still in god queued state, adding to the god queue".format(job.id, ajs.job_id))
            ajs.old_state = "Q"
            ajs.running = False
            self.monitor_queue.put(ajs)

    def _get_token(self, job_wrapper):
        return job_wrapper.get_job().user.get_oidc_tokens(self.provider_backend)["access"]

    def prepare_job_arc(self, job_wrapper):
        """
         job_wrapper is wrapper around python model galaxy.model.Job
         input_datasets
         output_datasets
         input_dataset_collections...
         parameters

         https://docs.galaxyproject.org/en/release_21.05/lib/galaxy.model.html?highlight=galaxy%20model#galaxy.model.Job

         Example of simple ARC job-description:

        <?xml version="1.0" ?>
        <ActivityDescriptions>
             <ActivityDescription xmlns="http://www.eu-emi.eu/es/2010/12/adl" xmlns:emiestypes="http://www.eu-emi.eu/es/2010/12/types" xmlns:nordugrid-adl="http://www.nordugrid.org/es/2011/12/nordugrid-adl">
                 <ActivityIdentification>
                         <Name>arc_hello_test</Name>
                 </ActivityIdentification>
                 <Application>
                         <Output>arc.out</Output>
                         <Error>arc.err</Error>
                         <Executable>
                                 <Path>./runhello.sh</Path>
                         </Executable>
                 </Application>
                 <Resources>
                         <QueueName>main</QueueName>
                         <IndividualCPUTime>1</IndividualCPUTime>
                         <IndividualPhysicalMemory>100</IndividualPhysicalMemory>
                 </Resources>
                 <DataStaging>
                         <InputFile>
                                 <Name>runhello.sh</Name>
                         </InputFile>
                         <OutputFile>
                                 <Name>arcout1.txt</Name>
                                 <Target>
                                         <URI>file:///storage/galaxy/jobs_directory/007/7595/outputs/arcout1.txt</URI>
                                 </Target>
                         </OutputFile>
                         <OutputFile>
                                 <Name>arcout2.txt</Name>
                                 <Target>
                                         <URI>file:///storage/galaxy/jobs_directory/007/7595/outputs/arcout2.txt</URI>
                                 </Target>
                         </OutputFile>
                         <OutputFile>
                                 <Name>arc.out</Name>
                         </OutputFile>
                         <OutputFile>
                                 <Name>arc.err</Name>
                         </OutputFile>
                 </DataStaging>
             </ActivityDescription>
         </ActivityDescriptions>

        """

        """ The job_wrapper.job_destination has access to the parameters from the id=arc destination configured in the job_conf """
        galaxy_job = job_wrapper.get_job()

        """
        Organize the galaxy jobs input-files into executables,  input- and output-files
        The ARC job description expects a different format for executables compared to other input files.
        TODO: Use the command-builder to extract the executable command instead of using an executable file uploaded to Galaxy.
        TODO: Extend to support fuller ARC job description options - such as ARC runtimeenvironment that inform the ARC client about what capabilities the endpoint has.
               e.g. what software is installed.
        """

        arc_job = ARCJobBuilder()

        """
        These are the files that are uploaded by the user for this job
        file_source: is the file path in the galaxy data folder,
        file_realname: the filename the uploaded file had
        tool_input_tag: - the tools form input name
        """
        input_datasets = galaxy_job.get_input_datasets()

        for input_data in input_datasets:
            file_source = input_data.dataset.get_file_name()
            tool_input_tag = input_data.name
            file_realname = input_data.dataset.get_display_name()

            if "arcjob_remote_filelist" in tool_input_tag:
                """Demo gymnastics just to show how ARC can handle fetching remote files - this needs to be discussed how to achieve in Galaxy - relies on the hello_arc.xml tool"""
                with open(file_source) as f:
                    files = f.readlines()
                    for idx, file_url in enumerate(files):
                        file_n_xrls = f"remote_file_{idx}"
                        arc_job.inputs[file_n_xrls] = file_url.strip()
            else:
                """Example of file local to the Galaxy server"""
                arc_job.inputs[file_realname] = "file://" + file_source

        """ Need also to upload the Executable produced by Galaxy - the tool_script.sh """
        file_realname = "tool_script.sh"
        file_source = "file://" + job_wrapper.working_directory + "/" + file_realname
        arc_job.inputs[file_realname] = file_source

        """ Use the tool_script.sh created by Galaxy as the executable to run """
        arc_job.exe_path = "./" + file_realname

        """ Potentially more than one file - but currently actually only one, so the for-loop here is currently not actually needed """
        """ TODO - Handling of complex dynamic output file list - there wlll be a post-job script tarring the output files - and this one tar-file will be pushed to galaxy """
        output_datasets = galaxy_job.get_output_datasets()
        arc_job.outputs.append("/")
        for output_data in output_datasets:
            file_name = output_data.name
            arc_job.outputs.append(file_name)

        """ Fetch the other job description items from the ARC destination """
        arc_cpuhrs = str(job_wrapper.job_destination.params["arc_cpuhrs"])
        arc_mem = str(job_wrapper.job_destination.params["arc_mem"])

        """
        TODO- should probably not be Hard-coded
        the user should him/herself enter what oout and err files
        that the executable produces
        """
        std_out = "arc.out"
        std_err = "arc.err"

        """ This is hardcoded stdout and stderr files from the ARC job defined here in the runner - TODO - not hardcoded """
        arc_job.stdout = std_out
        arc_job.stderr = std_err

        """ Construct the job description xml object """
        arc_job.name = "galaxy_arc_hello_test"

        """ TODO - just a sample, this will probably be set by the destination itself - to be discussed """
        arc_job.cpu_time = arc_cpuhrs

        """ TODO - just a sample, this will probably be set by the destination itself - to be discussed """
        arc_job.memory = arc_mem

        """ Populate the arcjob object with rest of necessary and useful fields including the full job description string"""
        """ All files that should be collected by ARC when the job is finished need to be appended to the downloadFiles list -
        here it is just the folder / and all files in the folder will be downloaded.
        The arc.py in pyarcrest loops over this list to fetch all outputfiles  """
        arc_job.descrstr = arc_job.to_xml_str()
        log.debug(f"{arc_job.descrstr}")

        return arc_job
