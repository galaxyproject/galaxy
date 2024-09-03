import logging
import os
import time
import traceback
from datetime import timedelta

try:
    import pbs

    PBS_IMPORT_MESSAGE = None
except ImportError as exc:
    pbs = None
    PBS_IMPORT_MESSAGE = (
        "The Python pbs-python package is required to use "
        "this feature, please install it or correct the "
        f"following error:\nImportError {exc}"
    )

from galaxy import (
    model,
    util,
)
from galaxy.jobs import JobDestination
from galaxy.jobs.runners import (
    AsynchronousJobRunner,
    AsynchronousJobState,
)
from galaxy.util.bunch import Bunch

log = logging.getLogger(__name__)

__all__ = ("PBSJobRunner",)

CLUSTER_ERROR_MESSAGE = "Job cannot be completed due to a cluster error, please retry it later: %s"

# The last two lines execute the command and then retrieve the command's
# exit code ($?) and write it to a file.
pbs_symlink_template = """
for dataset in %s; do
    dir=`dirname $dataset`
    file=`basename $dataset`
    [ ! -d $dir ] && mkdir -p $dir
    [ ! -e $dataset ] && ln -s %s/$file $dataset
done
mkdir -p %s
"""

PBS_ARGMAP = {
    "destination": "-q",
    "Execution_Time": "-a",
    "Account_Name": "-A",
    "Checkpoint": "-c",
    "Error_Path": "-e",
    "Group_List": "-g",
    "Hold_Types": "-h",
    "Join_Paths": "-j",
    "Keep_Files": "-k",
    "Resource_List": "-l",
    "Mail_Points": "-m",
    "Mail_Users": "-M",
    "Job_Name": "-N",
    "Output_Path": "-o",
    "Priority": "-p",
    "Rerunable": "-r",
    "Shell_Path_List": "-S",
    "job_array_request": "-t",
    "User_List": "-u",
    "Variable_List": "-v",
}

# From pbs' pbs_job.h
JOB_EXIT_STATUS = {
    0: "job exec successful",
    -1: "job exec failed, before files, no retry",
    -2: "job exec failed, after files, no retry",
    -3: "job execution failed, do retry",
    -4: "job aborted on MOM initialization",
    -5: "job aborted on MOM init, chkpt, no migrate",
    -6: "job aborted on MOM init, chkpt, ok migrate",
    -7: "job restart failed",
    -8: "exec() of user command failed",
    -9: "could not create/open stdout stderr files",
    -10: "job exceeded a memory limit",
    -11: "job exceeded a walltime limit",
    -12: "job exceeded a cpu time limit",
}


class PBSJobRunner(AsynchronousJobRunner):
    """
    Job runner backed by a finite pool of worker threads. FIFO scheduling
    """

    runner_name = "PBSRunner"

    def __init__(self, app, nworkers):
        """Start the job runner"""
        # Check if PBS was importable, fail if not
        assert pbs is not None, PBS_IMPORT_MESSAGE
        if app.config.pbs_application_server and app.config.outputs_to_working_directory:
            raise Exception(
                "pbs_application_server (file staging) and outputs_to_working_directory options are mutually exclusive"
            )

        # Set the default server during startup
        self.__default_pbs_server = None
        self.default_pbs_server  # noqa: B018 this is a method with a property decorator, so this causes the default server to be set

        # Proceed with general initialization
        super().__init__(app, nworkers)

    @property
    def default_pbs_server(self):
        if self.__default_pbs_server is None:
            self.__default_pbs_server = pbs.pbs_default()
            log.debug(f"Set default PBS server to {self.default_pbs_server}")
        return self.__default_pbs_server

    def url_to_destination(self, url):
        """Convert a legacy URL to a job destination"""

        if not url:
            return

        # Determine the PBS server
        url_split = url.split("/")
        server = url_split[2]
        if server == "":
            server = self.default_pbs_server
        if server is None:
            raise Exception("Could not find TORQUE server")

        # Determine the queue, set the PBS destination (not the same thing as a Galaxy job destination)
        pbs_destination = f"@{server}"
        if (pbs_queue := url_split[3] or None) is not None:
            pbs_destination = f"{pbs_queue}{pbs_destination}"

        params = dict(destination=pbs_destination)

        # Determine the args (long-format args were never supported in URLs so they are not supported here)
        try:
            opts = url.split("/")[4].strip().lstrip("-").split(" -")
            assert opts != [""]
            # stripping the - comes later (in parse_destination_params)
            for i, opt in enumerate(opts):
                opts[i] = f"-{opt}"
        except Exception:
            opts = []
        for opt in opts:
            param, value = opt.split(None, 1)
            params[param] = value

        log.debug(f"Converted URL '{url}' to destination runner=pbs, params={params}")

        # Create a dynamic JobDestination
        return JobDestination(runner="pbs", params=params)

    def parse_destination_params(self, params):
        """A wrapper method around __args_to_attrs() that allow administrators to define PBS
        params as either command-line options (as in ``qsub(1B)``) or more human-readable "long"
        args (as in ``pbs_submit(3B)``).

        :returns: list of dicts -- The dicts map directly to pbs attropl structs (see ``pbs_submit(3B)``)
        """
        args = {}
        for arg, value in params.items():
            try:
                if not arg.startswith("-"):
                    arg = PBS_ARGMAP[arg]
                arg = arg.lstrip("-")
                args[arg] = value
            except Exception:
                log.warning(f"Unrecognized long argument in destination params: {arg}")
        return self.__args_to_attrs(args)

    # Internal stuff
    def __args_to_attrs(self, args):
        """Convert a list of PBS command-line args (as in ``qsub(1B)``) to PBS' internal attribute representations.

        :returns: list of dicts -- The dicts map directly to pbs attropl structs (see ``pbs_submit(3B)``)
        """
        rval = []
        for arg, value in args.items():
            if arg == "l":
                resource_attrs = value.split(",")
                for res, val in [a.split("=", 1) for a in resource_attrs]:
                    rval.append(dict(name=pbs.ATTR_l, value=val, resource=res))
            else:
                try:
                    rval.append(dict(name=getattr(pbs, f"ATTR_{arg}"), value=value))
                except AttributeError as e:
                    raise Exception(f"Invalid parameter '{arg}': {e}")
        return rval

    def __get_pbs_server(self, job_destination_params):
        if job_destination_params is None:
            return None
        return job_destination_params["destination"].split("@")[-1]

    def queue_job(self, job_wrapper):
        """Create PBS script for a job and submit it to the PBS queue"""
        # prepare the job
        if not self.prepare_job(job_wrapper, include_metadata=not (self.app.config.pbs_stage_path)):
            return

        job_destination = job_wrapper.job_destination

        # Determine the job's PBS destination (server/queue) and options from the job destination definition
        pbs_queue_name = None
        pbs_server_name = self.default_pbs_server
        pbs_options = []
        if "-q" in job_destination.params and "destination" not in job_destination.params:
            job_destination.params["destination"] = job_destination.params.pop("-q")
        if "destination" in job_destination.params:
            if "@" in job_destination.params["destination"]:
                # Destination includes a server
                pbs_queue_name, pbs_server_name = job_destination.params["destination"].split("@")
                if pbs_queue_name == "":
                    # e.g. `qsub -q @server`
                    pbs_queue_name = None
            else:
                # Destination is just a queue
                pbs_queue_name = job_destination.params["destination"]
            job_destination.params.pop("destination")

        # Parse PBS params
        pbs_options = self.parse_destination_params(job_destination.params)

        # Explicitly set the determined PBS destination in the persisted job destination for recovery
        job_destination.params["destination"] = f"{pbs_queue_name or ''}@{pbs_server_name}"

        c = pbs.pbs_connect(util.smart_str(pbs_server_name))
        if c <= 0:
            errno, text = pbs.error()
            job_wrapper.fail("Unable to queue job for execution.  Resubmitting the job may succeed.")
            log.error(f"Connection to PBS server for submit failed: {errno}: {text}")
            return

        # define job attributes
        ofile = f"{job_wrapper.working_directory}/{job_wrapper.job_id}.o"
        efile = f"{job_wrapper.working_directory}/{job_wrapper.job_id}.e"
        ecfile = f"{job_wrapper.working_directory}/{job_wrapper.job_id}.ec"

        output_fnames = job_wrapper.job_io.get_output_fnames()

        # If an application server is set, we're staging
        if self.app.config.pbs_application_server:
            pbs_ofile = f"{self.app.config.pbs_application_server}:{ofile}"
            pbs_efile = f"{self.app.config.pbs_application_server}:{efile}"
            output_files = [str(o) for o in output_fnames]
            output_files.append(ecfile)
            stagein = self.get_stage_in_out(job_wrapper.job_io.get_input_fnames() + output_files, symlink=True)
            stageout = self.get_stage_in_out(output_files)
            attrs = [
                dict(name=pbs.ATTR_o, value=pbs_ofile),
                dict(name=pbs.ATTR_e, value=pbs_efile),
                dict(name=pbs.ATTR_stagein, value=stagein),
                dict(name=pbs.ATTR_stageout, value=stageout),
            ]
        # If not, we're using NFS
        else:
            attrs = [
                dict(name=pbs.ATTR_o, value=ofile),
                dict(name=pbs.ATTR_e, value=efile),
            ]

        # define PBS job options
        attrs.append(dict(name=pbs.ATTR_N, value=str(f"{job_wrapper.job_id}_{job_wrapper.tool.id}_{job_wrapper.user}")))
        job_attrs = pbs.new_attropl(len(attrs) + len(pbs_options))
        for i, attr in enumerate(attrs + pbs_options):
            job_attrs[i].name = attr["name"]
            job_attrs[i].value = attr["value"]
            if "resource" in attr:
                job_attrs[i].resource = attr["resource"]
        exec_dir = os.path.abspath(job_wrapper.working_directory)

        # write the job script
        if self.app.config.pbs_stage_path != "":
            # touch the ecfile so that it gets staged
            with open(ecfile, "a"):
                os.utime(ecfile, None)

            stage_commands = pbs_symlink_template % (
                " ".join(job_wrapper.job_io.get_input_fnames() + output_files),
                self.app.config.pbs_stage_path,
                exec_dir,
            )
        else:
            stage_commands = ""

        env_setup_commands = [stage_commands]
        script = self.get_job_file(
            job_wrapper, exit_code_path=ecfile, env_setup_commands=env_setup_commands, shell=job_wrapper.shell
        )
        job_file = f"{job_wrapper.working_directory}/{job_wrapper.job_id}.sh"
        self.write_executable_script(job_file, script, job_io=job_wrapper.job_io)
        # job was deleted while we were preparing it
        if job_wrapper.get_state() in (model.Job.states.DELETED, model.Job.states.STOPPED):
            log.debug(f"Job {job_wrapper.job_id} deleted/stopped by user before it entered the PBS queue")
            pbs.pbs_disconnect(c)
            if job_wrapper.cleanup_job in ("always", "onsuccess"):
                self.cleanup((ofile, efile, ecfile, job_file))
                job_wrapper.cleanup()
            return

        # submit
        # The job tag includes the job and the task identifier
        # (if a TaskWrapper was passed in):
        galaxy_job_id = job_wrapper.get_id_tag()
        log.debug(f"({galaxy_job_id}) submitting file {job_file}")

        tries = 0
        while tries < 5:
            job_id = pbs.pbs_submit(c, job_attrs, job_file, pbs_queue_name, None)
            tries += 1
            if job_id:
                pbs.pbs_disconnect(c)
                break
            errno, text = pbs.error()
            log.warning("(%s) pbs_submit failed (try %d/5), PBS error %d: %s" % (galaxy_job_id, tries, errno, text))
            time.sleep(2)
        else:
            log.error(f"({galaxy_job_id}) All attempts to submit job failed")
            job_wrapper.fail("Unable to run this job due to a cluster error, please retry it later")
            return

        if pbs_queue_name is None:
            log.debug(f"({galaxy_job_id}) queued in default queue as {job_id}")
        else:
            log.debug(f"({galaxy_job_id}) queued in {pbs_queue_name} queue as {job_id}")

        # persist destination
        job_wrapper.set_job_destination(job_destination, job_id)

        # Store PBS related state information for job
        job_state = AsynchronousJobState(
            job_wrapper=job_wrapper,
            job_id=job_id,
            exit_code_file=ecfile,
            job_destination=job_destination,
            job_file=job_file,
            output_file=ofile,
            error_file=efile,
        )
        job_state.old_state = "N"
        job_state.running = False

        # Add to our 'queue' of jobs to monitor
        self.monitor_queue.put(job_state)

    def check_watched_items(self):
        """
        Called by the monitor thread to look at each watched job and deal
        with state changes.
        """
        new_watched = []
        # reduce pbs load by batching status queries
        (failures, statuses) = self.check_all_jobs()
        for pbs_job_state in self.watched:
            job_id = pbs_job_state.job_id
            galaxy_job_id = pbs_job_state.job_wrapper.get_id_tag()
            old_state = pbs_job_state.old_state
            pbs_server_name = self.__get_pbs_server(pbs_job_state.job_destination.params)
            if pbs_server_name in failures:
                log.debug(f"({galaxy_job_id}/{job_id}) Skipping state check because PBS server connection failed")
                new_watched.append(pbs_job_state)
                continue
            try:
                status = statuses[job_id]
            except KeyError:
                if pbs_job_state.job_wrapper.get_state() == model.Job.states.DELETED:
                    continue
                try:
                    # Recheck to make sure it wasn't a communication problem
                    self.check_single_job(pbs_server_name, job_id)
                    log.warning(
                        f"({galaxy_job_id}/{job_id}) PBS job was not in state check list, but was found with individual state check"
                    )
                    new_watched.append(pbs_job_state)
                except Exception:
                    errno, text = pbs.error()
                    if errno == 15001:
                        # 15001 == job not in queue
                        log.debug(f"({galaxy_job_id}/{job_id}) PBS job has left queue")
                        self.work_queue.put((self.finish_job, pbs_job_state))
                    else:
                        # Unhandled error, continue to monitor
                        log.info(
                            "(%s/%s) PBS state check resulted in error (%d): %s" % (galaxy_job_id, job_id, errno, text)
                        )
                        new_watched.append(pbs_job_state)
                continue
            if status.job_state != old_state:
                log.debug(f"({galaxy_job_id}/{job_id}) PBS job state changed from {old_state} to {status.job_state}")
            if status.job_state == "R" and not pbs_job_state.running:
                pbs_job_state.running = True
                pbs_job_state.job_wrapper.change_state(model.Job.states.RUNNING)
            if status.job_state == "R" and status.get("resources_used", False):
                # resources_used may not be in the status for new jobs
                h, m, s = (int(i) for i in status.resources_used.walltime.split(":"))
                runtime = timedelta(0, s, 0, 0, m, h)
                if pbs_job_state.check_limits(runtime=runtime):
                    self.work_queue.put((self.fail_job, pbs_job_state))
                    continue
            elif status.job_state == "C":
                # "keep_completed" is enabled in PBS, so try to check exit status
                try:
                    assert (
                        int(status.exit_status) == 0
                        or pbs_job_state.job_wrapper.get_state() == model.Job.states.STOPPED
                    )
                    log.debug(f"({galaxy_job_id}/{job_id}) PBS job has completed successfully")
                except AssertionError:
                    exit_status = int(status.exit_status)
                    error_message = JOB_EXIT_STATUS.get(exit_status, f"Unknown error: {status.exit_status}")
                    pbs_job_state.fail_message = CLUSTER_ERROR_MESSAGE % error_message
                    log.error(f"({galaxy_job_id}/{job_id}) PBS job failed: {error_message}")
                    pbs_job_state.stop_job = False
                    self.work_queue.put((self.fail_job, pbs_job_state))
                    continue
                except AttributeError:
                    # No exit_status, can't verify proper completion so we just have to assume success.
                    log.debug(f"({galaxy_job_id}/{job_id}) PBS job has completed")
                self.work_queue.put((self.finish_job, pbs_job_state))
                continue
            pbs_job_state.old_state = status.job_state
            new_watched.append(pbs_job_state)
        # Replace the watch list with the updated version
        self.watched = new_watched

    def check_all_jobs(self):
        """
        Returns a list of servers that failed to be contacted and a dict
        of "job_id : status" pairs (where status is a bunchified version
        of the API's structure.
        """
        servers = []
        failures = []
        statuses = {}
        for pbs_job_state in self.watched:
            pbs_server_name = self.__get_pbs_server(pbs_job_state.job_destination.params)
            if pbs_server_name not in servers:
                servers.append(pbs_server_name)
            pbs_job_state.check_count += 1
        for pbs_server_name in servers:
            c = pbs.pbs_connect(util.smart_str(pbs_server_name))
            if c <= 0:
                log.debug(f"connection to PBS server {pbs_server_name} for state check failed")
                failures.append(pbs_server_name)
                continue
            stat_attrl = pbs.new_attrl(3)
            stat_attrl[0].name = pbs.ATTR_state
            stat_attrl[1].name = pbs.ATTR_used
            stat_attrl[2].name = pbs.ATTR_exitstat
            jobs = pbs.pbs_statjob(c, None, stat_attrl, None)
            pbs.pbs_disconnect(c)
            statuses.update(self.convert_statjob_to_bunches(jobs))
        return (failures, statuses)

    def convert_statjob_to_bunches(self, statjob_out):
        statuses = {}
        for job in statjob_out:
            status = {}
            for attrib in job.attribs:
                if attrib.resource is None:
                    status[attrib.name] = attrib.value
                else:
                    if attrib.name not in status:
                        status[attrib.name] = Bunch()
                    status[attrib.name][attrib.resource] = attrib.value
            statuses[job.name] = Bunch(**status)
        return statuses

    def check_single_job(self, pbs_server_name, job_id):
        """
        Returns the state of a single job, used to make sure a job is
        really dead.
        """
        c = pbs.pbs_connect(util.smart_str(pbs_server_name))
        if c <= 0:
            log.debug(f"connection to PBS server {pbs_server_name} for state check failed")
            return None
        stat_attrl = pbs.new_attrl(1)
        stat_attrl[0].name = pbs.ATTR_state
        jobs = pbs.pbs_statjob(c, job_id, stat_attrl, None)
        pbs.pbs_disconnect(c)
        return jobs[0].attribs[0].value

    def get_stage_in_out(self, fnames, symlink=False):
        """Convenience function to create a stagein/stageout list"""
        stage = ""
        for fname in fnames:
            if os.access(fname, os.R_OK):
                if stage:
                    stage += ","
                # pathnames are now absolute
                if symlink and self.app.config.pbs_stage_path:
                    stage_name = os.path.join(self.app.config.pbs_stage_path, os.path.split(fname)[1])
                else:
                    stage_name = fname
                stage += f"{stage_name}@{self.app.config.pbs_dataset_server}:{fname}"
        return stage

    def stop_job(self, job_wrapper):
        """Attempts to delete a job from the PBS queue"""
        job = job_wrapper.get_job()
        job_id = job.get_job_runner_external_id().encode("utf-8")
        job_tag = f"({job.get_id_tag()}/{job_id})"
        log.debug(f"{job_tag} Stopping PBS job")

        # Declare the connection handle c so that it can be cleaned up:
        c = None

        try:
            pbs_server_name = self.__get_pbs_server(job.destination_params)
            if pbs_server_name is None:
                log.debug("(%s) Job queued but no destination stored in job params, cannot delete", job_tag)
                return
            c = pbs.pbs_connect(util.smart_str(pbs_server_name))
            if c <= 0:
                log.debug(f"({job_tag}) Connection to PBS server for job delete failed")
                return
            pbs.pbs_deljob(c, job_id, "")
            log.debug(f"{job_tag} Removed from PBS queue before job completion")
        except Exception:
            e = traceback.format_exc()
            log.debug(f"{job_tag} Unable to stop job: {e}")
        finally:
            # Cleanup: disconnect from the server.
            if None is not c:
                pbs.pbs_disconnect(c)

    def recover(self, job, job_wrapper):
        """Recovers jobs stuck in the queued/running state when Galaxy started"""
        job_id = job.get_job_runner_external_id()
        pbs_job_state = AsynchronousJobState(
            job_wrapper=job_wrapper,
            job_id=job_id,
            job_file=f"{job_wrapper.working_directory}/{job.id}.sh",
            output_file=f"{job_wrapper.working_directory}/{job.id}.o",
            error_file=f"{job_wrapper.working_directory}/{job.id}.e",
            exit_code_file=f"{job_wrapper.working_directory}/{job.id}.ec",
            job_destination=job_wrapper.job_destination,
        )
        pbs_job_state.runner_url = job_wrapper.get_job_runner_url()
        job_wrapper.command_line = job.command_line
        if job.state in (model.Job.states.RUNNING, model.Job.states.STOPPED):
            log.debug(
                f"({job.id}/{job.get_job_runner_external_id()}) is still in {job.state} state, adding to the PBS queue"
            )
            pbs_job_state.old_state = "R"
            pbs_job_state.running = True
            self.monitor_queue.put(pbs_job_state)
        elif job.state == model.Job.states.QUEUED:
            log.debug(
                f"({job.id}/{job.get_job_runner_external_id()}) is still in PBS queued state, adding to the PBS queue"
            )
            pbs_job_state.old_state = "Q"
            pbs_job_state.running = False
            self.monitor_queue.put(pbs_job_state)
