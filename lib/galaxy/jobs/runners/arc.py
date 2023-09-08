import os, sys
import json
import logging
import time
from datetime import datetime
import shutil

import requests
from galaxy.authnz.util import provider_name_to_backend

from galaxy import model
from galaxy.jobs.runners import (
    AsynchronousJobRunner,
    AsynchronousJobState
)
from galaxy.jobs.runners.util.arc_util import (
    ARCHTTPError,
    ARCJob,
    ensure_pyarc,
    get_client,
)
from galaxy.util import unicodify

from xml.etree.ElementTree import Element, SubElement, tostring, fromstring

log = logging.getLogger(__name__)

__all__ = ('ArcRESTJobRunner', )

class Arc:
    """
    API parameters
    """

    def __init__(self):

        self.cluster = ""
        self.job_mapping = {}

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
            "Job not found": "Failed"
        }

        
    def set_job_cluster(self,cluster):
        self.cluster = cluster


class ArcRESTJobRunner(AsynchronousJobRunner):
    """
    Job runner backed by a finite pool of worker threads. FIFO scheduling
    """
    runner_name = "ArcRESTJobRunner"

    def __init__(self, app, nworkers, **kwargs):
        """ 1: Get runner_param_specs from job_conf.xml
            2: Initialise job runner parent object
            3: Start the worker and monitor threads
        """

        # Start the job runner parent object
        super(ArcRESTJobRunner,self).__init__(app, nworkers, **kwargs)
        ensure_pyarc()

        self.arc = Arc()
        self.arcjob = ARCJob()
        self.provider_backend = provider_name_to_backend("wlcg")
        #self.arc_url = None
                
        
        """ Following methods starts threads.
        These methods invoke threading.Thread(name,target)
        which in turn invokes methods monitor() and run_next().
        """
        self._init_monitor_thread()
        self._init_worker_threads()
                    
    def queue_job(self, job_wrapper):
        """ When a tool is submitted for execution in galaxy """
        """ This method 
        1. Fetches the configured ARC endpoint for this user
        2. Prepares an ARC job description based on the jobs destination parameters
        3. Submits the job to the remote ARC endpoint via pyarcrest
        4. Adds the job to the galaxy job queue
        """

        job_destination = job_wrapper.job_destination
        galaxy_jobid = job_wrapper.job_id
        
        """ Set the cluster to submit the job to - extracted from the job_destination parameters in job_conf.xml """
        user_preferences = job_wrapper.get_job().user.extra_preferences
        arc_url = user_preferences.get("distributed_arc_compute|remote_arc_resources", "None")
        self.arc.set_job_cluster(arc_url)
        
        """ Prepare and submit job to arc """
        self.prepare_job(job_wrapper, self.arcjob)
         
        token = job_wrapper.get_job().user.get_oidc_tokens(self.provider_backend)['access']
        # proxypath is ignored if you are using token
        self.arcrest = get_client(self.arc.cluster, token=token)
        
        # token parameter isn't necessary, unless there is a bug
        delegationID = self.arcrest.createDelegation()
        
        bulkdesc = "<ActivityDescriptions>"
        bulkdesc += self.arcjob.descstr
        bulkdesc += "</ActivityDescriptions>"
            
        results = self.arcrest.createJobs(bulkdesc, delegationID=delegationID)
        
        if isinstance(results[0], ARCHTTPError):
            # submission error
            log.error("Job creation failure.  No Response from ARC")
            job_wrapper.fail("Not submitted")
        else:
            # successful submission
            arc_jobid, status = results[0]
            log.debug(f'Successfully submitted job to remote ARC resource {self.arc.cluster} with ARC id: {arc_jobid}')
            # beware! this means 1 worker, no timeout and default upload buffer
            errors = self.arcrest.uploadJobFiles([arc_jobid], [self.arcjob.inputFiles])
            if errors[0]:  # input upload error
                log.error("Job creation failure. No Response from ARC")
                log.debug(f'Could not upload job files for job with galaxy-id: {galaxy_jobid} to ARC resource {self.arc.cluster}. Error was: {errors[0]}')
                job_wrapper.fail("Not submitted")
            else:
                # successful input upload
                log.debug(f'Successfully uploaded input-files to remote ARC resource {self.arc.cluster} for job with galaxy-id: {galaxy_jobid} and ARC id: {arc_jobid}')
                self.arc.job_mapping[galaxy_jobid]=arc_jobid
                # Create an object of AsynchronousJobState and add it to the monitor queue.
                ajs = AsynchronousJobState(files_dir=job_wrapper.working_directory, job_wrapper=job_wrapper, job_id=galaxy_jobid, job_destination=job_destination)
                self.monitor_queue.put(ajs)

    def place_output_files(self, job_state, job_status_arc):
        """ Create log files in galaxy, namely error_file, output_file, exit_code_file
            Return true, if all the file creations are successful
        """

        job_dir = job_state.job_wrapper.working_directory
        galaxy_workdir= job_dir + '/working'
        galaxy_outputs= job_dir + '/outputs'
        
        arc_jobid = self.arc.job_mapping[job_state.job_id]
        outputs_dir = job_state.job_wrapper.outputs_directory


        """ job_state.output_file and job_state.error_file is e.g. galaxy_5.e and galaxy_5.o where 5 is the galaxy job id """
        """ Hardcoded out and err files - this is ok. But TODO - need to handle if the tool itself has some stdout that should be kept"""

        """ Galaxy stderr and stdout files need to be poupulated from the arc.out and arc.err files """
        try:
            # Read from ARC output_file and write it into galaxy output_file.
            out_log = ''
            tool_stdout_path =  galaxy_outputs + '/tool_stdout'
            with open(galaxy_workdir+"/"+arc_jobid+"/arc.out","r") as f:
                out_log = f.read()
            with open(job_state.output_file,"a+") as log_file:
                log_file.write(out_log)
                log_file.write("Some hardcoded stdout - as a sample from the arc.py runner.")
            with open(tool_stdout_path, "a+") as tool_stdout:
                tool_stdout.write(out_log)

        
            # Read from ARC error_file and write it into galaxy error_file.
            err_log = ''
            tool_stderr_path =  galaxy_outputs + '/tool_stderr'
            with open(galaxy_workdir+"/"+arc_jobid+"/arc.err","r") as f:
                err_log = f.read()
            with open(job_state.error_file,"w+") as log_file:
                log_file.write(err_log)
                log_file.write("Some hardcoded stderr - as a sample from the arc.py runner.")
            with open(tool_stderr_path, "w+") as tool_stderr:
                tool_stderr.write(err_log)
            
        except OSError as e:
            log.error('Could not access task log file: %s', unicodify(e))
            log.debug("IO Error occurred when accessing the files.")
            return False
        return True

    
    def check_watched_item(self, job_state):

        """ Get the job current status from ARC
                    using job_id and update the status in galaxy.
            If the job execution is successful, call
                    mark_as_finished() and return 'None' to galaxy.
            else if the job failed, call mark_as_failed()
                    and return 'None' to galaxy.
            else if the job is running or in pending state, simply
                    return the 'AsynchronousJobState object' (job_state).
        """
        ''' This function is called by check_watched_items() where
                    param job_state is an object of AsynchronousJobState.
            Expected return type of this function is None or
                    AsynchronousJobState object with updated running status.
        '''

        galaxy_job_wrapper = job_state.job_wrapper
        galaxy_job = galaxy_job_wrapper.get_job()
        galaxy_workdir = galaxy_job_wrapper.working_directory
        mapped_state= ''

        """ Make sure to get a fresh token and client """
        token = self._get_token(galaxy_job_wrapper)
        self.arcrest = get_client(self.arc.cluster, token=token)
        
        """ Get task from ARC """
        arc_jobid = self.arc.job_mapping[job_state.job_id]
        arc_job_state = self.job_actions(arc_jobid, "status")
        if arc_job_state is None:
            return None

        
        if arc_job_state:
            mapped_state = self.arc.ARC_STATE_MAPPING[arc_job_state]
        else:
            log.debug(f'Could not map state of ARC job with id: {arc_jobid} and Galaxy job id: {job_state.job_id}')
            return None
        
        self.arcrest = get_client(self.arc.cluster, token=self._get_token(galaxy_job_wrapper))

        if mapped_state == "Finished":

            job_state.running = False
            galaxy_job_wrapper.change_state(model.Job.states.OK)

            galaxy_outputdir = galaxy_workdir + '/working'
            self.arcrest.downloadJobFiles(galaxy_outputdir,[arc_jobid])
            
            self.place_output_files(job_state,mapped_state)
            self.mark_as_finished(job_state)

            '''The function mark_as_finished() executes:
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
            '''
            return None

        elif mapped_state == "Running":
            job_state.running = True
            galaxy_job_wrapper.change_state(model.Job.states.RUNNING)
            return job_state
        elif mapped_state == "Accepted" or mapped_state == "Preparing" or mapped_state == "Submitting" or mapped_state == "Queuing" or mapped_state == "Hold" or mapped_state == "Other":
            """ Job is in transition status """
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
        '''This function is called by fail_job()
           where param job = self.sa_session.query( self.app.model.Job ).get( job_state.job_wrapper.job_id )
           No Return data expected
        '''
        job_id = job_wrapper.job_id
        arc_jobid = ''
        
        """ Make sure to get a fresh token and client """
        token = self._get_token(job_wrapper)
        self.arcrest = get_client(self.arc.cluster, token=token)


        # Get task status from ARC.
        try:
            arc_jobid = self.arc.job_mapping[job_id]
        except KeyError:
            log.debug(f'Could not find arc_jobid for stopping job {job_id}')
            return None
        
        arc_job_state = self.job_actions([arc_jobid],  "status")
        if arc_job_state is None:
            return None
        mapped_state = self.arc.ARC_STATE_MAPPING[arc_job_state]
        if not(mapped_state == "Killed" or mapped_state == "Deleted" or mapped_state == "Finished"):

            try:
                # Initiate a delete call,if the job is running in ARC.
                waskilled = self.job_actions([arc_jobid],"kill")
            except Exception as e:
                log.debug(f'Job with ARC id: {arc_jobid} and Galaxy id: {job_id} was attempted killed by external request (user or admin), but this did not succeed. Exception was: {e}')
            
        return None

    def recover(self, job, job_wrapper):
        """ Recovers jobs stuck in the queued/running state when Galaxy started """
        """ This method is called by galaxy at the time of startup.
            Jobs in Running & Queued status in galaxy are put in the monitor_queue by creating an AsynchronousJobState object
        """
        job_id = job_wrapper.job_id
        ajs = AsynchronousJobState(files_dir=job_wrapper.working_directory, job_wrapper=job_wrapper)
        ajs.job_id = str(job_id)
        ajs.job_destination = job_wrapper.job_destination
        job_wrapper.command_line = job.command_line
        ajs.job_wrapper = job_wrapper
        if job.state == model.Job.states.RUNNING:
            log.debug("({}/{}) is still in running state, adding to the god queue".format(job.id, job.get_job_runner_external_id()))
            ajs.old_state = 'R'
            ajs.running = True
            self.monitor_queue.put(ajs)

        elif job.state == model.Job.states.QUEUED:
            log.debug("({}/{}) is still in god queued state, adding to the god queue".format(job.id, job.get_job_runner_external_id()))
            ajs.old_state = 'Q'
            ajs.running = False
            self.monitor_queue.put(ajs)


    def _get_token(self, job_wrapper):
        return job_wrapper.get_job().user.get_oidc_tokens(self.provider_backend)['access']

        
    def prepare_job(self, job_wrapper, arcjob):

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

        """ The job_wrapper.job_destination has access to the parameters from the id=arc destination configured in the job_conf"""
        job_destination = job_wrapper.job_destination
        galaxy_job = job_wrapper.get_job()
        galaxy_workdir = job_wrapper.working_directory

        """ job_input_params are the input params fetched from the tool """
        job_input_params = {}
        """ Make a dictionary of the job inputs and use this for filling in the job description"""
        for param in galaxy_job.parameters:
            job_input_params[str(param.name)]=str(param.value.strip('"'))
        
        """ 
        Organize the galaxy jobs input-files into executables,  input- and output-files 
        
        This works currently in the following way
        - The tool (hello_arc.xml) has param with name tag arcjob_exe, arcjob_outputs (and could potentially have arcjob_inputs) 
        In the below I match the strings
        - exe in the tag_name to match  the input file uploaded via the arcjob_exe form field
        - output in the tag_name to match the input file uploaded via the arcjob_outputs form field
        - currently input is empty - TODO 
        TODO - discuss if the exe box is convenient to use - I think so - This can then be used as a generic tool to run any kind of script. But then... must consider what to do with dependencies... So probably this option would lead to lots of errors for users. 

        TODO - This needs to be reconsidered so that any tool can work on an ARC endpoint. Not the special arc-tool created here. 
        Need a way to reliably identify executables (if local) inputs and outputs independent on how the tool form is like 
        """
        job_files = {}

        job_files['inputs'] = []
        job_files['outputs'] = []
        for inputdata in galaxy_job.input_datasets:
            tag_name = inputdata.name
            file_name = (inputdata.__dict__["dataset"]).__dict__["name"]
            file_id = (inputdata.__dict__["dataset"]).__dict__["dataset_id"]
            isExe = 'exe' in tag_name
            data_dict = {'tag':tag_name,'name':file_name ,'dataset_id':file_id, 'isexe':isExe}
            
            if "input" in tag_name or "exe" in tag_name:
                job_files['inputs'].append(data_dict)
            elif "output" in tag_name:
                job_files['outputs'].append(data_dict)


        """ Fetch the other job description items from the ARC destination """
        arc_cpuhrs = str(job_input_params["arcjob_cpuhrs"])
        arc_mem = str(job_input_params["arcjob_memory"])
        

        """ 
        TODO- should probably not be Hard-coded 
        the user should him/herself enter what oout and err files 
        that the executable produces 
        """

        std_out = "arc.out"
        std_err = "arc.err"

        """ Construct the job description xml object """
        """ TODO - extend to support fuller ARC job description options """
        
        descr     = Element('ActivityDescription')
        descr.set("xmlns","http://www.eu-emi.eu/es/2010/12/adl")
        descr.set("xmlns:emiestypes","http://www.eu-emi.eu/es/2010/12/types")
        descr.set("xmlns:nordugrid-adl","http://www.nordugrid.org/es/2011/12/nordugrid-adl")

        actid     = SubElement(descr,"ActivityIdentification")
        app       = SubElement(descr,"Application")
        resources = SubElement(descr,"Resources")
        datastaging = SubElement(descr,"DataStaging")

        actid_name = SubElement(actid,"Name")
        actid_name.text = "galaxy_arc_hello_test"

        app_out = SubElement(app,"Output")
        app_out.text = std_out
        
        app_err = SubElement(app,"Error")
        app_err.text = std_err
        
        app_exe = SubElement(app,"Executable")


        """ These are the files that are uploaded by the user for this job - store the path in a dict for use later  
        key is dataset_id and value is the file path in the galaxy data folder """
        inputfile_paths = job_wrapper.job_io.get_input_paths()
        job_inputfiles_galaxy_paths = {}
        for idx, input_path in enumerate(inputfile_paths):
            job_inputfiles_galaxy_paths[input_path.dataset_id] = input_path.real_path

        
        """ Populate datastaging exec tag with all exec files - in addition populate the arcjob object  """
        for job_file in job_files['inputs']:

            dataset_name = job_file['name']
            dataset_id = job_file['dataset_id']
            dataset_path = job_inputfiles_galaxy_paths[dataset_id]
            isexe = job_file['isexe']
           
            """ Populate the arcjob object with the source - pyarcrest expects this"""
            arcjob.inputFiles[dataset_name] = 'file://' + dataset_path

            """ Datastaging tag """
            sub_el = SubElement(datastaging,"InputFile")
            subsub_el = SubElement(sub_el,"Name")
            subsub_el.text = dataset_name

            if isexe:
                """ Fill the appropriate job description fields expected for executables"""
                """ App tag """
                sub_el = SubElement(app_exe,"Path")
                sub_el.text = "./" + dataset_name


        """ Populate datastaging output tag with all output files - in addition to populate the arcjob object"""
        """ Potentially more than one file - but currently actually only one, so the for-loop here is currently not actually needed """
 
        """ Fill the appropriate job description fields """
        sub_el = SubElement(datastaging,"OutputFile")
        subsub_el = SubElement(sub_el,"Name")
        subsub_el.text = "/"
        

        """ This is hardcoded stdout and stderr files from the ARC job defined here in the runner - TODO - not hardcoded """
        sub_el = SubElement(datastaging,"OutputFile")
        subsub_el = SubElement(sub_el,"Name")
        subsub_el.text = std_out

        """ This is hardcoded stdout and stderr files from the ARC job defined here in the runner - TODO - not hardcoded """
        sub_el = SubElement(datastaging,"OutputFile")
        subsub_el = SubElement(sub_el,"Name")
        subsub_el.text = std_err

        """ TODO - just a sample, this will probably be set by the destination itself - to be discussed """
        cpuhrs = arc_cpuhrs
        sub_el = SubElement(resources,"IndividualCPUTime")
        sub_el.text = arc_cpuhrs

        """ TODO - just a sample, this will probably be set by the destination itself - to be discussed """
        mem = arc_mem
        sub_el = SubElement(resources,"IndividualPhysicalMemory")
        sub_el.text = arc_mem

        """ Populate the arcjob object with rest of necessary and useful fields including the full job description string"""
        """ All files that should be collected by ARC when the job is finished need to be appended to the downloadFiles list - 
        here it is just the folder / and all files in the folder will be downloaded. 
        The arc.py in pyarcrest loops over this list to fetch all outputfiles  """
        arcjob.downloadFiles.append("/")
        arcjob.StdOut = std_out
        arcjob.StdErr = std_err
        arcjob.RequestedTotalCPUTime = cpuhrs
        arcjob.descstr = tostring(descr, encoding='unicode',method='xml')


    def job_actions(self, arcid, action):


        """ Kill job in ARC.
            Pass job_id to http_delete_request method.
        """
        """ Really processing one job at a time, should I do this better? pyarcrest/arc.py takes a list of jobs"""

        if action == "status":
            results = self.arcrest.getJobsStatus([arcid])
            for state in results:
                try:
                    job_state = state
                    return  job_state
                except Exception:
                    log.error(f'Could not get status of job with id: {arcid}')
        elif action == "kill":
            results = self.arcrest.killJobs([arcid])
            for killed in results:
                if killed:
                    return True
                else:
                    return False
