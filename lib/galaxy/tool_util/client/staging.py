"""Client for staging inputs for Galaxy Tools and Workflows.

Implement as a connector to serve a bridge between galactic_job_json
utility and a Galaxy API library.
"""
import abc
import json
import logging
import os

import six

from galaxy.tool_util.cwl.util import (
    DirectoryUploadTarget,
    FileLiteralTarget,
    FileUploadTarget,
    galactic_job_json,
    path_or_uri_to_uri,
)

log = logging.getLogger(__name__)

UPLOAD_TOOL_ID = "upload1"
LOAD_TOOLS_FROM_PATH = True


@six.add_metaclass(abc.ABCMeta)
class StagingInterace(object):
    """Client that parses a job input and populates files into the Galaxy API.

    Abstract class that must override _post (and optionally other things such
    _attach_file, _log, etc..) to adapt to bioblend (for Planemo) or using the
    tool test interactor infrastructure.
    """

    @abc.abstractmethod
    def _post(self, api_path, payload, files_attached=False):
        """Make a post to the Galaxy API along supplied path."""

    def _attach_file(self, path):
        return open(path, 'rb')

    def _tools_post(self, payload, files_attached=False):
        tool_response = self._post("tools", payload, files_attached=files_attached)
        for job in tool_response.get("jobs", []):
            self._handle_job(job)
        return tool_response

    def _handle_job(self, job_response):
        """Implementer can decide if to wait for job(s) individually or not here."""

    def stage(self, tool_or_workflow, history_id, job=None, job_path=None, use_path_paste=LOAD_TOOLS_FROM_PATH, default_job_dir=None):
        files_attached = [False]

        def upload_func(upload_target):

            def _attach_file(upload_payload, uri, index=0):
                uri = path_or_uri_to_uri(uri)
                is_path = uri.startswith("file://")
                if not is_path or use_path_paste:
                    upload_payload["inputs"]["files_%d|url_paste" % index] = uri
                else:
                    files_attached[0] = True
                    path = uri[len("file://"):]
                    upload_payload["files_%d|file_data" % index] = self._attach_file(path)

            if isinstance(upload_target, FileUploadTarget):
                file_path = upload_target.path
                upload_payload = _upload_payload(
                    history_id,
                    file_type=upload_target.properties.get('filetype', None) or "auto",
                )
                name = _file_path_to_name(file_path)
                upload_payload["inputs"]["files_0|auto_decompress"] = False
                upload_payload["inputs"]["auto_decompress"] = False
                if file_path is not None:
                    _attach_file(upload_payload, file_path)
                upload_payload["inputs"]["files_0|NAME"] = name
                if upload_target.secondary_files:
                    _attach_file(upload_payload, upload_target.secondary_files, index=1)
                    upload_payload["inputs"]["files_1|type"] = "upload_dataset"
                    upload_payload["inputs"]["files_1|auto_decompress"] = True
                    upload_payload["inputs"]["file_count"] = "2"
                    upload_payload["inputs"]["force_composite"] = "True"
                # galaxy.exceptions.RequestParameterInvalidException: Not input source type
                # defined for input '{'class': 'File', 'filetype': 'imzml', 'composite_data':
                # ['Example_Continuous.imzML', 'Example_Continuous.ibd']}'.\n"}]]

                if upload_target.composite_data:
                    for i, composite_data in enumerate(upload_target.composite_data):
                        upload_payload["inputs"]["files_%s|type" % i] = "upload_dataset"
                        _attach_file(upload_payload, composite_data, index=i)

                self._log("upload_payload is %s" % upload_payload)
                return self._tools_post(upload_payload, files_attached=files_attached[0])
            elif isinstance(upload_target, FileLiteralTarget):
                payload = _upload_payload(history_id, file_type="auto", auto_decompress=False)
                payload["inputs"]["files_0|url_paste"] = upload_target.contents
                return self._tools_post(payload)
            elif isinstance(upload_target, DirectoryUploadTarget):
                tar_path = upload_target.tar_path

                upload_payload = _upload_payload(
                    history_id,
                    file_type="tar",
                )
                upload_payload["inputs"]["files_0|auto_decompress"] = False
                _attach_file(upload_payload, tar_path)
                tar_upload_response = self._tools_post(upload_payload, files_attached=files_attached[0])
                convert_payload = dict(
                    tool_id="CONVERTER_tar_to_directory",
                    tool_inputs={"input1": {"src": "hda", "id": tar_upload_response["outputs"][0]["id"]}},
                    history_id=history_id,
                )
                convert_response = self._tools_post(convert_payload)
                assert "outputs" in convert_response, convert_response
                return convert_response
            else:
                content = json.dumps(upload_target.object)
                payload = _upload_payload(history_id, file_type="expression.json")
                payload["files_0|url_paste"] = content
                return self._tools_post(payload)

        def create_collection_func(element_identifiers, collection_type):
            payload = {
                "name": "dataset collection",
                "instance_type": "history",
                "history_id": history_id,
                "element_identifiers": element_identifiers,
                "collection_type": collection_type,
                "fields": None if collection_type != "record" else "auto",
            }
            return self._post("dataset_collections", payload)

        if job_path is not None:
            assert job is None
            with open(job_path, "r") as f:
                job = yaml.safe_load(f)
            job_dir = os.path.dirname(job_path)
        else:
            assert job is not None
            # Figure out what "." should be here instead.
            job_dir = default_job_dir or "."

        job_dict, datasets = galactic_job_json(
            job,
            job_dir,
            upload_func,
            create_collection_func,
            tool_or_workflow,
        )
        return job_dict, datasets

    # extension point for planemo to override logging
    def _log(self, message):
        log.debug(message)


class InteractorStaging(StagingInterace):

    def __init__(self, galaxy_interactor):
        self.galaxy_interactor = galaxy_interactor

    def _post(self, api_path, payload, files_attached=False):
        response = self.galaxy_interactor._post(api_path, payload, json=True)
        assert response.status_code == 200, response.text
        return response.json()

    def _handle_job(self, job_response):
        self.galaxy_interactor.wait_for_job(job_response["id"])

def _file_path_to_name(file_path):
    if file_path is not None:
        name = os.path.basename(file_path)
    else:
        name = "defaultname"
    return name


def _upload_payload(history_id, tool_id=UPLOAD_TOOL_ID, file_type="auto", dbkey="?", **kwd):
    """Adapted from bioblend tools client."""
    payload = {}
    payload["history_id"] = history_id
    payload["tool_id"] = tool_id
    tool_input = {}
    tool_input["file_type"] = file_type
    tool_input["dbkey"] = dbkey
    if not kwd.get('to_posix_lines', True):
        tool_input['files_0|to_posix_lines'] = False
    elif kwd.get('space_to_tab', False):
        tool_input['files_0|space_to_tab'] = 'Yes'
    if 'file_name' in kwd:
        tool_input["files_0|NAME"] = kwd['file_name']
    tool_input["files_0|type"] = "upload_dataset"
    payload["inputs"] = tool_input
    return payload
