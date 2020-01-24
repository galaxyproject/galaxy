import json
import logging
import os

from galaxy.exceptions import RequestParameterMissingException
from galaxy.model.dataset_collections.structure import UninitializedTree
from galaxy.tools.actions import upload_common
from galaxy.util import ExecutionTimer
from galaxy.util.bunch import Bunch
from . import ToolAction

log = logging.getLogger(__name__)


class BaseUploadToolAction(ToolAction):
    produces_real_jobs = True

    def execute(self, tool, trans, incoming={}, history=None, **kwargs):
        trans.check_user_activation()
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
                    try:
                        path_def = next(files_iter)
                    except StopIteration:
                        path_def = None
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

        outputs = []
        for target in request.get("targets", []):
            destination = target.get("destination")
            destination_type = destination.get("type")
            # Start by just pre-creating HDAs.
            if destination_type == "hdas":
                if target.get("elements_from"):
                    # Dynamic collection required I think.
                    continue
                _precreate_fetched_hdas(trans, history, target, outputs)

            if destination_type == "hdca":
                _precreate_fetched_collection_instance(trans, history, target, outputs)

        incoming["request_json"] = json.dumps(request)
        return self._create_job(
            trans, incoming, tool, None, outputs, history=history
        )


def _precreate_fetched_hdas(trans, history, target, outputs):
    for item in target.get("elements", []):
        name = item.get("name", None)
        if name is None:
            src = item.get("src", None)
            if src == "url":
                url = item.get("url")
                if name is None:
                    name = url.split("/")[-1]
            elif src == "path":
                path = item["path"]
                if name is None:
                    name = os.path.basename(path)

        file_type = item.get("ext", "auto")
        dbkey = item.get("dbkey", "?")
        uploaded_dataset = Bunch(
            type='file', name=name, file_type=file_type, dbkey=dbkey
        )
        tag_list = item.get("tags", [])
        data = upload_common.new_upload(trans, '', uploaded_dataset, library_bunch=None, history=history, tag_list=tag_list)
        outputs.append(data)
        item["object_id"] = data.id


def _precreate_fetched_collection_instance(trans, history, target, outputs):
    collection_type = target.get("collection_type")
    if not collection_type:
        # Can't precreate collections of unknown type at this time.
        return

    name = target.get("name")
    if not name:
        return

    tags = target.get("tags", [])
    collections_service = trans.app.dataset_collections_service
    collection_type_description = collections_service.collection_type_descriptions.for_collection_type(collection_type)
    structure = UninitializedTree(collection_type_description)
    hdca = collections_service.precreate_dataset_collection_instance(
        trans, history, name, structure=structure, tags=tags
    )
    outputs.append(hdca)
    # Following flushed needed for an ID.
    trans.sa_session.flush()
    target["destination"]["object_id"] = hdca.id
