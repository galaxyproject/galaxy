import json
import logging

from galaxy.exceptions import RequestParameterMissingException
from galaxy.tools.actions import upload_common
from galaxy.util import ExecutionTimer
from . import ToolAction

log = logging.getLogger(__name__)


class BaseUploadToolAction(ToolAction):

    def execute(self, tool, trans, incoming={}, history=None, **kwargs):
        dataset_upload_inputs = []
        for input_name, input in tool.inputs.items():
            if input.type == "upload_dataset":
                dataset_upload_inputs.append(input)
        assert dataset_upload_inputs, Exception("No dataset upload groups were found.")

        persisting_uploads_timer = ExecutionTimer()
        incoming = upload_common.persist_uploads(incoming, trans)
        log.debug("Persisted uploads %s" % persisting_uploads_timer)
        rval = self._setup_job(tool, trans, incoming, dataset_upload_inputs, history)
        return rval

    def _setup_job(self, tool, trans, incoming, dataset_upload_inputs, history):
        """Take persisted uploads and create a job for given tool."""

    def _create_job(self, *args, **kwds):
        """Wrapper around upload_common.create_job with a timer."""
        create_job_timer = ExecutionTimer()
        rval = upload_common.create_job(*args, **kwds)
        log.debug("Created upload job %s" % create_job_timer)
        return rval


class UploadToolAction(BaseUploadToolAction):

    def _setup_job(self, tool, trans, incoming, dataset_upload_inputs, history):
        check_timer = ExecutionTimer()
        uploaded_datasets = upload_common.get_uploaded_datasets(trans, '', incoming, dataset_upload_inputs, history=history)

        if not uploaded_datasets:
            return None, 'No data was entered in the upload form, please go back and choose data to upload.'

        json_file_path = upload_common.create_paramfile(trans, uploaded_datasets)
        data_list = [ud.data for ud in uploaded_datasets]
        log.debug("Checked uploads %s" % check_timer)
        return self._create_job(
            trans, incoming, tool, json_file_path, data_list, history=history
        )


class FetchUploadToolAction(BaseUploadToolAction):

    def _setup_job(self, tool, trans, incoming, dataset_upload_inputs, history):
        # Now replace references in requests with these.
        files = incoming.get("files", [])
        files_iter = iter(files)
        request = json.loads(incoming.get("request_json"))

        def replace_file_srcs(request_part):
            if isinstance(request_part, dict):
                if request_part.get("src", None) == "files":
                    path_def = next(files_iter)
                    if path_def is None or path_def["file_data"] is None:
                        raise RequestParameterMissingException("Failed to find uploaded file matching target with src='files'")
                    request_part["path"] = path_def["file_data"]["local_filename"]
                    if "name" not in request_part:
                        request_part["name"] = path_def["file_data"]["filename"]
                    request_part["src"] = "path"
                else:
                    for key, value in request_part.items():
                        replace_file_srcs(value)
            elif isinstance(request_part, list):
                for value in request_part:
                    replace_file_srcs(value)

        replace_file_srcs(request)

        incoming["request_json"] = json.dumps(request)
        return self._create_job(
            trans, incoming, tool, None, [], history=history
        )
