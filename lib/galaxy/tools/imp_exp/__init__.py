import getpass
import logging
import os
import shutil
from typing import Optional

from sqlalchemy import select

from galaxy import model
from galaxy.model import store
from galaxy.model.base import transaction
from galaxy.schema.tasks import SetupHistoryExportJob
from galaxy.util.path import external_chown

log = logging.getLogger(__name__)


class JobImportHistoryArchiveWrapper:
    """
    Class provides support for performing jobs that import a history from
    an archive.
    """

    def __init__(self, app, job_id):
        self.app = app
        self.job_id = job_id
        self.sa_session = self.app.model.context

    def setup_job(self, jiha, archive_source, archive_type):
        if self.app.config.external_chown_script:
            if archive_type != "url":
                external_chown(
                    archive_source,
                    jiha.job.user.system_user_pwent(self.app.config.real_system_username),
                    self.app.config.external_chown_script,
                    "history import archive",
                )
            external_chown(
                jiha.archive_dir,
                jiha.job.user.system_user_pwent(self.app.config.real_system_username),
                self.app.config.external_chown_script,
                "history import archive directory",
            )

    def cleanup_after_job(self):
        """Set history, datasets, collections and jobs' attributes
        and clean up archive directory.
        """

        #
        # Import history.
        #

        stmt = select(model.JobImportHistoryArchive).filter_by(job_id=self.job_id).limit(1)
        jiha = self.sa_session.scalars(stmt).first()
        if not jiha:
            return None
        user = jiha.job.user

        new_history = None
        try:
            archive_dir = jiha.archive_dir
            if self.app.config.external_chown_script:
                external_chown(
                    archive_dir,
                    jiha.job.user.system_user_pwent(getpass.getuser()),
                    self.app.config.external_chown_script,
                    "history import archive directory",
                )
            model_store = store.get_import_model_store_for_directory(
                archive_dir,
                app=self.app,
                user=user,
                tag_handler=self.app.tag_handler.create_tag_handler_session(jiha.job.galaxy_session),
            )
            job = jiha.job
            with model_store.target_history(default_history=job.history) as new_history:
                jiha.history = new_history
                with transaction(self.sa_session):
                    self.sa_session.commit()
                model_store.perform_import(new_history, job=job, new_history=True)
                # Cleanup.
                if os.path.exists(archive_dir):
                    shutil.rmtree(archive_dir)

        except Exception as e:
            jiha.job.tool_stderr += f"Error cleaning up history import job: {e}"
            with transaction(self.sa_session):
                self.sa_session.commit()
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

    def setup_job(
        self,
        history,
        store_directory,
        include_hidden=False,
        include_deleted=False,
        compressed=True,
        user: Optional[model.User] = None,
    ):
        """
        Perform setup for job to export a history into an archive.
        """
        # TODO: prevent circular import here...
        from galaxy.celery.tasks import export_history

        app = self.app
        # TODO: parameterize API on include_files here...
        request = SetupHistoryExportJob(
            history_id=history.id,
            job_id=self.job_id,
            store_directory=store_directory,
            include_files=True,
            include_hidden=include_hidden,
            include_deleted=include_deleted,
        )
        if app.config.enable_celery_tasks:
            # symlink files on export, on worker files will tarred up in a dereferenced manner.
            export_history.delay(request=request, task_user_id=getattr(user, "id", None))
        else:
            export_history(request=request)
