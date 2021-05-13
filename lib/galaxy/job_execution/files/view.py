import os
import shutil

from galaxy import (
    exceptions,
    model,
    util
)


class JobFilesView(object):

    def __init__(self, app):
        self._app = app

    def get_file(self, job_id, **kwd):
        self.__authorize_job_access(job_id, **kwd)
        path = kwd.get("path", None)
        return open(path, 'rb')

    def post_file(self, job_id, **kwd):
        job = self.__authorize_job_access(job_id, **kwd)
        path = kwd.get("path")
        self.__check_job_can_write_to_path(job, path)

        # Is this writing an unneeded file? Should this just copy in Python?
        if '__file_path' in kwd:
            file_path = kwd.get('__file_path')
            upload_store = self._app.config.nginx_upload_job_files_store
            assert upload_store, ("Request appears to have been processed by"
                                  " nginx_upload_module but Galaxy is not"
                                  " configured to recognize it")
            assert file_path.startswith(upload_store), \
                ("Filename provided by nginx (%s) is not in correct"
                 " directory (%s)" % (file_path, upload_store))
            input_file = open(file_path)
        else:
            input_file = kwd.get("file", kwd.get("__file", None)).file
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

    def __authorize_job_access(self, encoded_job_id, **kwargs):
        for key in ["path", "job_key"]:
            if key not in kwargs:
                error_message = "Job files action requires a valid '%s'." % key
                raise exceptions.ObjectAttributeMissingException(error_message)

        job_id = self._security.decode_id(encoded_job_id)
        job_key = self._security.encode_id(job_id, kind="jobs_files")
        if not util.safe_str_cmp(kwargs["job_key"], job_key):
            raise exceptions.ItemAccessibilityException("Invalid job_key supplied.")

        # Verify job is active. Don't update the contents of complete jobs.
        sa_session = self._app.model.context.current
        job = sa_session.query(model.Job).get(job_id)
        if job.finished:
            error_message = "Attempting to read or modify the files of a job that has already completed."
            raise exceptions.ItemAccessibilityException(error_message)
        return job

    def __check_job_can_write_to_path(self, job, path):
        """ Verify an idealized job runner should actually be able to write to
        the specified path - it must be a dataset output, a dataset "extra
        file", or a some place in the working directory of this job.

        Would like similar checks for reading the unstructured nature of loc
        files make this very difficult. (See abandoned work here
        https://gist.github.com/jmchilton/9103619.)
        """
        in_work_dir = self.__in_working_directory(job, path)
        if not in_work_dir and not self.__is_output_dataset_path(job, path):
            raise exceptions.ItemAccessibilityException("Job is not authorized to write to supplied path.")

    def __is_output_dataset_path(self, job, path):
        """ Check if is an output path for this job or a file in the an
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

    def __in_working_directory(self, job, path):
        app = self._app
        working_directory = app.object_store.get_filename(job, base_dir='job_work', dir_only=True, extra_dir=str(job.id))
        return util.in_directory(path, working_directory)

    @property
    def _security(self):
        return self._app.security
