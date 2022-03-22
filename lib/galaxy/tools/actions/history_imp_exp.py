import datetime
import logging
import os
import tempfile

from galaxy.job_execution.setup import create_working_directory_for_job
from galaxy.tools.actions import ToolAction
from galaxy.tools.imp_exp import (
    JobExportHistoryArchiveWrapper,
    JobImportHistoryArchiveWrapper,
)
from galaxy.util import ready_name_for_url

log = logging.getLogger(__name__)


class ImportHistoryToolAction(ToolAction):
    """Tool action used for importing a history to an archive."""

    produces_real_jobs = True

    def execute(self, tool, trans, incoming=None, set_output_hid=False, overwrite=True, history=None, **kwargs):
        #
        # Create job.
        #
        incoming = incoming or {}
        trans.check_user_activation()
        job = trans.app.model.Job()
        job.galaxy_version = trans.app.config.version_major
        session = trans.get_galaxy_session()
        job.session_id = session and session.id
        if history:
            history_id = history.id
        elif trans.history:
            history_id = trans.history.id
        else:
            history_id = None
        job.history_id = history_id
        job.tool_id = tool.id
        job.user_id = trans.user.id
        start_job_state = job.state  # should be job.states.NEW
        job.state = (
            job.states.WAITING
        )  # we need to set job state to something other than NEW, or else when tracking jobs in db it will be picked up before we have added input / output parameters
        trans.sa_session.add(job)
        trans.sa_session.flush()  # ensure job.id are available

        #
        # Setup job and job wrapper.
        #

        # Add association for keeping track of job, history relationship.

        # Use abspath because mkdtemp() does not, contrary to the documentation,
        # always return an absolute path.
        archive_dir = os.path.abspath(tempfile.mkdtemp())
        jiha = trans.app.model.JobImportHistoryArchive(job=job, archive_dir=archive_dir)
        trans.sa_session.add(jiha)

        job_wrapper = JobImportHistoryArchiveWrapper(trans.app, job)
        job_wrapper.setup_job(jiha, incoming["__ARCHIVE_SOURCE__"], incoming["__ARCHIVE_TYPE__"])

        #
        # Add parameters to job_parameter table.
        #

        # Set additional parameters.
        incoming["__DEST_DIR__"] = jiha.archive_dir
        for name, value in tool.params_to_strings(incoming, trans.app).items():
            job.add_parameter(name, value)

        job.state = start_job_state  # job inputs have been configured, restore initial job state
        return job, {}


class ExportHistoryToolAction(ToolAction):
    """Tool action used for exporting a history to an archive."""

    produces_real_jobs = True

    def execute(self, tool, trans, incoming=None, set_output_hid=False, overwrite=True, history=None, **kwargs):
        trans.check_user_activation()
        #
        # Get history to export.
        #
        incoming = incoming or {}
        history = None
        for name, value in incoming.items():
            if isinstance(value, trans.app.model.History):
                history_param_name = name
                history = value
                del incoming[history_param_name]
                break

        if not history:
            raise Exception("There is no history to export.")

        #
        # Create the job and output dataset objects
        #
        job = trans.app.model.Job()
        job.galaxy_version = trans.app.config.version_major
        session = trans.get_galaxy_session()
        job.session_id = session and session.id
        history_id = history.id
        job.history_id = history_id
        job.tool_id = tool.id
        if trans.user:
            # If this is an actual user, run the job as that individual.  Otherwise we're running as guest.
            job.user_id = trans.user.id
        job.state = (
            job.states.WAITING
        )  # we need to set job state to something other than NEW, or else when tracking jobs in db it will be picked up before we have added input / output parameters
        trans.sa_session.add(job)

        compressed = incoming["compress"]
        exporting_to_uri = "directory_uri" in incoming
        if not exporting_to_uri:
            # see comment below about how this should be transitioned to occuring in a
            # job handler or detached MQ-driven thread
            jeha = trans.app.model.JobExportHistoryArchive.create_for_history(
                history, job, trans.sa_session, trans.app.object_store, compressed
            )
            store_directory = jeha.temp_directory
        else:
            # creating a job directory in the web thread is bad (it is slow, bypasses
            # dynamic objectstore assignment, etc..) but it is arguably less bad than
            # creating a dataset (like above for dataset export case).
            # ensure job.id is available
            trans.sa_session.flush()
            job_directory = create_working_directory_for_job(trans.app.object_store, job)
            store_directory = os.path.join(job_directory, "working", "_object_export")
            os.makedirs(store_directory)

        #
        # Setup job and job wrapper.
        #
        cmd_line = f"--galaxy-version '{job.galaxy_version}'"
        if compressed:
            cmd_line += " -G"
        cmd_line = f"{cmd_line} {store_directory}"

        #
        # Add parameters to job_parameter table.
        #

        # Set additional parameters.
        incoming["__HISTORY_TO_EXPORT__"] = history.id
        incoming["__EXPORT_HISTORY_COMMAND_INPUTS_OPTIONS__"] = cmd_line
        if exporting_to_uri:
            directory_uri = incoming["directory_uri"]
            file_name = incoming.get("file_name")
            if file_name is None:
                hname = ready_name_for_url(history.name)
                human_timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                if compressed:
                    extension = ".tar.gz"
                else:
                    extension = ".tar"
                file_name = f"Galaxy-History-{hname}-{human_timestamp}.{extension}"

            file_name = os.path.basename(os.path.abspath(file_name))
            sep = "" if directory_uri.endswith("/") else "/"
            incoming["__EXPORT_TO_URI__"] = f"{directory_uri}{sep}{file_name}"

        for name, value in tool.params_to_strings(incoming, trans.app).items():
            job.add_parameter(name, value)
        trans.sa_session.flush()

        job_wrapper = JobExportHistoryArchiveWrapper(trans.app, job.id)
        job_wrapper.setup_job(
            history,
            store_directory,
            include_hidden=incoming["include_hidden"],
            include_deleted=incoming["include_deleted"],
            compressed=compressed,
        )

        return job, {}
