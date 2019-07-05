import logging
import os
import shutil
import tempfile

from galaxy import model
from galaxy.model import store
from galaxy.version import VERSION_MAJOR

log = logging.getLogger(__name__)

ATTRS_FILENAME_HISTORY = 'history_attrs.txt'


class JobImportHistoryArchiveWrapper:
    """
        Class provides support for performing jobs that import a history from
        an archive.
    """

    def __init__(self, app, job_id):
        self.app = app
        self.job_id = job_id
        self.sa_session = self.app.model.context

    def cleanup_after_job(self):
        """ Set history, datasets, collections and jobs' attributes
            and clean up archive directory.
        """

        #
        # Import history.
        #

        jiha = self.sa_session.query(model.JobImportHistoryArchive).filter_by(job_id=self.job_id).first()
        if not jiha:
            return None
        user = jiha.job.user

        new_history = None
        try:
            archive_dir = jiha.archive_dir
            model_store = store.get_import_model_store_for_directory(archive_dir, app=self.app, user=user)
            job = jiha.job
            with model_store.target_history(default_history=job.history) as new_history:

                jiha.history = new_history
                self.sa_session.flush()

                model_store.perform_import(new_history, job=job, new_history=True)

                # Cleanup.
                if os.path.exists(archive_dir):
                    shutil.rmtree(archive_dir)

        except Exception as e:
            jiha.job.tool_stderr += "Error cleaning up history import job: %s" % e
            self.sa_session.flush()
            raise

        return new_history


class JobExportHistoryArchiveWrapper:
    """
    Class provides support for performing jobs that export a history to an
    archive.
    """

    def __init__(self, app, job_id):
        self.app = app
        self.job_id = job_id
        self.sa_session = self.app.model.context

    def setup_job(self, jeha, include_hidden=False, include_deleted=False):
        """ Perform setup for job to export a history into an archive. Method generates
            attribute files for export, sets the corresponding attributes in the jeha
            object, and returns a command line for running the job. The command line
            includes the command, inputs, and options; it does not include the output
            file because it must be set at runtime. """

        app = self.app

        #
        # Create attributes/metadata files for export.
        #
        # Use abspath because mkdtemp() does not, contrary to the documentation,
        # always return an absolute path.
        temp_output_dir = os.path.abspath(tempfile.mkdtemp())

        history = jeha.history
        history_attrs_filename = os.path.join(temp_output_dir, ATTRS_FILENAME_HISTORY)
        jeha.history_attrs_filename = history_attrs_filename

        # symlink files on export, on worker files will tarred up in a dereferenced manner.
        with store.DirectoryModelExportStore(temp_output_dir, app=app, export_files="symlink") as export_store:
            export_store.export_history(history, include_hidden=include_hidden, include_deleted=include_deleted)

        #
        # Create and return command line for running tool.
        #
        options = "--galaxy-version '%s'" % VERSION_MAJOR
        if jeha.compressed:
            options += " -G"
        return "%s %s" % (options, temp_output_dir)

    def cleanup_after_job(self):
        """ Remove temporary directory and attribute files generated during setup for this job. """
        # Get jeha for job.
        jeha = self.sa_session.query(model.JobExportHistoryArchive).filter_by(job_id=self.job_id).first()
        if jeha:
            temp_dir = jeha.temp_directory
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                log.debug('Error deleting directory containing attribute files (%s): %s' % (temp_dir, e))
