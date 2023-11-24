""" API for asynchronous job running mechanisms can use to fetch or put files
related to running and queued jobs.
"""
import logging
import os
import shutil

from galaxy import (
    exceptions,
    model,
    util,
)
from galaxy.web import (
    expose_api_anonymous_and_sessionless,
    expose_api_raw_anonymous_and_sessionless,
)
from . import BaseGalaxyAPIController

log = logging.getLogger(__name__)


class JobFilesAPIController(BaseGalaxyAPIController):
    """This job files controller allows remote job running mechanisms to
    read and modify the current state of files for queued and running jobs.
    It is certainly not meant to represent part of Galaxy's stable, user
    facing API.

    Furthermore, even if a user key corresponds to the user running the job,
    it should not be accepted for authorization - this API allows access to
    low-level unfiltered files and such authorization would break Galaxy's
    security model for tool execution.
    """

    @expose_api_raw_anonymous_and_sessionless
    def index(self, trans, job_id, **kwargs):
        """
        GET /api/jobs/{job_id}/files

        Get a file required to staging a job (proper datasets, extra inputs,
        task-split inputs, working directory files).

        :type   job_id: str
        :param  job_id: encoded id string of the job
        :type   path: str
        :param  path: Path to file.
        :type   job_key: str
        :param  job_key: A key used to authenticate this request as acting on
                         behalf or a job runner for the specified job.

        ..note:
            This API method is intended only for consumption by job runners,
            not end users.

        :rtype:     binary
        :returns:   contents of file
        """
        self.__authorize_job_access(trans, job_id, **kwargs)
        path = kwargs.get("path", None)
        return open(path, "rb")

    @expose_api_anonymous_and_sessionless
    def create(self, trans, job_id, payload, **kwargs):
        """
        create( self, trans, job_id, payload, **kwargs )
        * POST /api/jobs/{job_id}/files
            Populate an output file (formal dataset, task split part, working
            directory file (such as those related to metadata)). This should be
            a multipart post with a 'file' parameter containing the contents of
            the actual file to create.

        :type   job_id: str
        :param  job_id: encoded id string of the job
        :type   payload:    dict
        :param  payload:    dictionary structure containing::
            'job_key'   = Key authenticating
            'path'      = Path to file to create.

        ..note:
            This API method is intended only for consumption by job runners,
            not end users.

        :rtype:     dict
        :returns:   an okay message
        """
        job = self.__authorize_job_access(trans, job_id, **payload)
        path = payload.get("path")
        self.__check_job_can_write_to_path(trans, job, path)

        # Is this writing an unneeded file? Should this just copy in Python?
        if "__file_path" in payload:
            file_path = payload.get("__file_path")
            upload_store = trans.app.config.nginx_upload_job_files_store
            assert upload_store, (
                "Request appears to have been processed by"
                " nginx_upload_module but Galaxy is not"
                " configured to recognize it"
            )
            assert file_path.startswith(
                upload_store
            ), f"Filename provided by nginx ({file_path}) is not in correct directory ({upload_store})"
            input_file = open(file_path)
        else:
            input_file = payload.get("file", payload.get("__file", None)).file
        target_dir = os.path.dirname(path)
        util.safe_makedirs(target_dir)
        try:
            shutil.move(input_file.name, path)
        finally:
            try:
                input_file.close()
            except OSError:
                # Fails to close file if not using nginx upload because the
                # tempfile has moved and Python wants to delete it.
                pass
        return {"message": "ok"}

    def __authorize_job_access(self, trans, encoded_job_id, **kwargs):
        for key in ["path", "job_key"]:
            if key not in kwargs:
                error_message = f"Job files action requires a valid '{key}'."
                raise exceptions.ObjectAttributeMissingException(error_message)

        job_id = trans.security.decode_id(encoded_job_id)
        job_key = trans.security.encode_id(job_id, kind="jobs_files")
        if not util.safe_str_cmp(str(kwargs["job_key"]), job_key):
            raise exceptions.ItemAccessibilityException("Invalid job_key supplied.")

        # Verify job is active. Don't update the contents of complete jobs.
        job = trans.sa_session.query(model.Job).get(job_id)
        if job.finished:
            error_message = "Attempting to read or modify the files of a job that has already completed."
            raise exceptions.ItemAccessibilityException(error_message)
        return job

    def __check_job_can_write_to_path(self, trans, job, path):
        """Verify an idealized job runner should actually be able to write to
        the specified path - it must be a dataset output, a dataset "extra
        file", or a some place in the working directory of this job.

        Would like similar checks for reading the unstructured nature of loc
        files make this very difficult. (See abandoned work here
        https://gist.github.com/jmchilton/9103619.)
        """
        in_work_dir = self.__in_working_directory(job, path, trans.app)
        if not in_work_dir and not self.__is_output_dataset_path(job, path):
            raise exceptions.ItemAccessibilityException("Job is not authorized to write to supplied path.")

    def __is_output_dataset_path(self, job, path):
        """Check if is an output path for this job or a file in the an
        output's extra files path.
        """
        da_lists = [job.output_datasets, job.output_library_datasets]
        for da_list in da_lists:
            for job_dataset_association in da_list:
                dataset = job_dataset_association.dataset
                if not dataset:
                    continue
                if os.path.abspath(dataset.file_name) == os.path.abspath(path):
                    return True
                elif util.in_directory(path, dataset.extra_files_path):
                    return True
        return False

    def __in_working_directory(self, job, path, app):
        working_directory = app.object_store.get_filename(
            job, base_dir="job_work", dir_only=True, extra_dir=str(job.id)
        )
        return util.in_directory(path, working_directory)
