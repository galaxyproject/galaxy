import io
import json
import os
import re
import shutil
import sys
import tarfile
import tempfile
import time
from collections import OrderedDict
from json import dumps
from logging import getLogger

from packaging.version import parse as parse_version, Version
try:
    from nose.tools import nottest
except ImportError:
    def nottest(x):
        return x
try:
    import requests
except ImportError:
    requests = None

from galaxy import util
from galaxy.tool_util.parser.interface import TestCollectionDef, TestCollectionOutputDef
from galaxy.util.bunch import Bunch
from . import verify
from .asserts import verify_assertions
from .wait import wait_on

log = getLogger(__name__)

# Off by default because it can pound the database pretty heavily
# and result in sqlite errors on larger tests or larger numbers of
# tests.
VERBOSE_ERRORS = util.asbool(os.environ.get("GALAXY_TEST_VERBOSE_ERRORS", False))
UPLOAD_ASYNC = util.asbool(os.environ.get("GALAXY_TEST_UPLOAD_ASYNC", True))
ERROR_MESSAGE_DATASET_SEP = "--------------------------------------"
DEFAULT_TOOL_TEST_WAIT = int(os.environ.get("GALAXY_TEST_DEFAULT_WAIT", 86400))

DEFAULT_FTYPE = 'auto'
# This following default dbkey was traditionally hg17 before Galaxy 18.05,
# restore this behavior by setting GALAXY_TEST_DEFAULT_DBKEY to hg17.
DEFAULT_DBKEY = os.environ.get("GALAXY_TEST_DEFAULT_DBKEY", "?")


class OutputsDict(OrderedDict):
    """Ordered dict that can also be accessed by index.

    >>> out = OutputsDict()
    >>> out['item1'] = 1
    >>> out['item2'] = 2
    >>> out[1] == 2 == out['item2']
    True
    """

    def __getitem__(self, item):
        if isinstance(item, int):
            return self[list(self.keys())[item]]
        else:
            # ideally we'd do `return super(OutputsDict, self)[item]`,
            # but this fails because OrderedDict has no `__getitem__`. (!?)
            item = self.get(item)
            if item is None:
                raise KeyError(item)
            return item


def stage_data_in_history(galaxy_interactor, tool_id, all_test_data, history=None, force_path_paste=False, maxseconds=DEFAULT_TOOL_TEST_WAIT):
    # Upload any needed files
    upload_waits = []

    assert tool_id

    if UPLOAD_ASYNC:
        for test_data in all_test_data:
            upload_waits.append(galaxy_interactor.stage_data_async(test_data,
                                                                   history,
                                                                   tool_id,
                                                                   force_path_paste=force_path_paste,
                                                                   maxseconds=maxseconds))
        for upload_wait in upload_waits:
            upload_wait()
    else:
        for test_data in all_test_data:
            upload_wait = galaxy_interactor.stage_data_async(test_data,
                                                             history,
                                                             tool_id,
                                                             force_path_paste=force_path_paste,
                                                             maxseconds=maxseconds)
            upload_wait()


class GalaxyInteractorApi:

    def __init__(self, **kwds):
        self.api_url = "%s/api" % kwds["galaxy_url"].rstrip("/")
        self.master_api_key = kwds["master_api_key"]
        self.api_key = self.__get_user_key(kwds.get("api_key"), kwds.get("master_api_key"), test_user=kwds.get("test_user"))
        if kwds.get('user_api_key_is_admin_key', False):
            self.master_api_key = self.api_key
        self.keep_outputs_dir = kwds["keep_outputs_dir"]
        self.download_attempts = kwds.get("download_attempts", 1)
        self.download_sleep = kwds.get("download_sleep", 1)
        # Local test data directories.
        self.test_data_directories = kwds.get("test_data", [])

        self._target_galaxy_version = None

        self.uploads = {}

    @property
    def target_galaxy_version(self):
        if self._target_galaxy_version is None:
            self._target_galaxy_version = parse_version(self._get('version').json()['version_major'])
        return self._target_galaxy_version

    @property
    def supports_test_data_download(self):
        return self.target_galaxy_version >= Version("19.01")

    def __get_user_key(self, user_key, admin_key, test_user=None):
        if not test_user:
            test_user = "test@bx.psu.edu"
        if user_key:
            return user_key
        test_user = self.ensure_user_with_email(test_user)
        return self._post("users/%s/api_key" % test_user['id'], key=admin_key).json()

    # def get_tools(self):
    #    response = self._get("tools?in_panel=false")
    #    assert response.status_code == 200, "Non 200 response from tool index API. [%s]" % response.content
    #    return response.json()

    def get_tests_summary(self):
        response = self._get("tools/tests_summary")
        assert response.status_code == 200, "Non 200 response from tool tests available API. [%s]" % response.content
        return response.json()

    def get_tool_tests(self, tool_id, tool_version=None):
        url = "tools/%s/test_data" % tool_id
        if tool_version is not None:
            url += "?tool_version=%s" % tool_version
        response = self._get(url)
        assert response.status_code == 200, "Non 200 response from tool test API. [%s]" % response.content
        return response.json()

    def verify_output_collection(self, output_collection_def, output_collection_id, history, tool_id):
        data_collection = self._get("dataset_collections/%s" % output_collection_id, data={"instance_type": "history"}).json()

        def verify_dataset(element, element_attrib, element_outfile):
            hda = element["object"]
            self.verify_output_dataset(
                history,
                hda_id=hda["id"],
                outfile=element_outfile,
                attributes=element_attrib,
                tool_id=tool_id
            )

        verify_collection(output_collection_def, data_collection, verify_dataset)

    def verify_output(self, history_id, jobs, output_data, output_testdef, tool_id, maxseconds):
        outfile = output_testdef.outfile
        attributes = output_testdef.attributes
        name = output_testdef.name

        self.wait_for_jobs(history_id, jobs, maxseconds)
        hid = self.__output_id(output_data)
        # TODO: Twill version verifies dataset is 'ok' in here.
        try:
            self.verify_output_dataset(history_id=history_id, hda_id=hid, outfile=outfile, attributes=attributes, tool_id=tool_id)
        except AssertionError as e:
            raise AssertionError("Output {}: {}".format(name, str(e)))

        primary_datasets = attributes.get('primary_datasets', {})
        if primary_datasets:
            job_id = self._dataset_provenance(history_id, hid)["job_id"]
            outputs = self._get("jobs/%s/outputs" % (job_id)).json()

        for designation, (primary_outfile, primary_attributes) in primary_datasets.items():
            primary_output = None
            for output in outputs:
                if output["name"] == f'__new_primary_file_{name}|{designation}__':
                    primary_output = output
                    break

            if not primary_output:
                msg_template = "Failed to find primary dataset with designation [%s] for output with name [%s]"
                msg_args = (designation, name)
                raise Exception(msg_template % msg_args)

            primary_hda_id = primary_output["dataset"]["id"]
            try:
                self.verify_output_dataset(history_id, primary_hda_id, primary_outfile, primary_attributes, tool_id=tool_id)
            except AssertionError as e:
                raise AssertionError("Primary output {}: {}".format(name, str(e)))

    def wait_for_jobs(self, history_id, jobs, maxseconds):
        for job in jobs:
            self.wait_for_job(job['id'], history_id, maxseconds)

    def verify_output_dataset(self, history_id, hda_id, outfile, attributes, tool_id):
        fetcher = self.__dataset_fetcher(history_id)
        test_data_downloader = self.__test_data_downloader(tool_id)
        verify_hid(
            outfile,
            hda_id=hda_id,
            attributes=attributes,
            dataset_fetcher=fetcher,
            test_data_downloader=test_data_downloader,
            keep_outputs_dir=self.keep_outputs_dir
        )
        self._verify_metadata(history_id, hda_id, attributes)

    def _verify_metadata(self, history_id, hid, attributes):
        """Check dataset metadata.

        ftype on output maps to `file_ext` on the hda's API description, `name`, `info`,
        `dbkey` and `tags` all map to the API description directly. Other metadata attributes
        are assumed to be datatype-specific and mapped with a prefix of `metadata_`.
        """
        metadata = attributes.get('metadata', {}).copy()
        for key, value in metadata.copy().items():
            if key not in ['name', 'info', 'tags', 'created_from_basename']:
                new_key = "metadata_%s" % key
                metadata[new_key] = metadata[key]
                del metadata[key]
            elif key == "info":
                metadata["misc_info"] = metadata["info"]
                del metadata["info"]
        expected_file_type = attributes.get('ftype', None)
        if expected_file_type:
            metadata["file_ext"] = expected_file_type

        if metadata:
            time.sleep(5)
            dataset = self._get(f"histories/{history_id}/contents/{hid}").json()
            for key, value in metadata.items():
                try:
                    dataset_value = dataset.get(key, None)

                    def compare(val, expected):
                        if str(val) != str(expected):
                            msg = "Dataset metadata verification for [%s] failed, expected [%s] but found [%s]. Dataset API value was [%s]."
                            msg_params = (key, value, dataset_value, dataset)
                            msg = msg % msg_params
                            raise Exception(msg)

                    if isinstance(dataset_value, list):
                        value = str(value).split(",")
                        if len(value) != len(dataset_value):
                            msg = "Dataset metadata verification for [%s] failed, expected [%s] but found [%s], lists differ in length. Dataset API value was [%s]."
                            msg_params = (key, value, dataset_value, dataset)
                            msg = msg % msg_params
                            raise Exception(msg)
                        for val, expected in zip(dataset_value, value):
                            compare(val, expected)
                    else:
                        compare(dataset_value, value)
                except KeyError:
                    msg = "Failed to verify dataset metadata, metadata key [%s] was not found." % key
                    raise Exception(msg)

    def wait_for_job(self, job_id, history_id=None, maxseconds=DEFAULT_TOOL_TEST_WAIT):
        self.wait_for(lambda: self.__job_ready(job_id, history_id), maxseconds=maxseconds)

    def wait_for(self, func, what='tool test run', **kwd):
        walltime_exceeded = int(kwd.get("maxseconds", DEFAULT_TOOL_TEST_WAIT))
        wait_on(func, what, walltime_exceeded)

    def get_job_stdio(self, job_id):
        job_stdio = self.__get_job_stdio(job_id).json()
        return job_stdio

    def __get_job(self, job_id):
        return self._get('jobs/%s' % job_id)

    def __get_job_stdio(self, job_id):
        return self._get('jobs/%s?full=true' % job_id)

    def new_history(self, history_name='test_history', publish_history=False):
        create_response = self._post("histories", {"name": history_name})
        try:
            create_response.raise_for_status()
        except Exception as e:
            raise Exception(f"Error occured while creating history with name '{history_name}': {e}")
        history_id = create_response.json()['id']
        if publish_history:
            self.publish_history(history_id)
        return history_id

    def publish_history(self, history_id):
        response = self._put(f'histories/{history_id}', json.dumps({'published': True}))
        response.raise_for_status()

    @nottest
    def test_data_path(self, tool_id, filename):
        response = self._get(f"tools/{tool_id}/test_data_path?filename={filename}", admin=True)
        return response.json()

    @nottest
    def test_data_download(self, tool_id, filename, mode='file', is_output=True):
        result = None
        local_path = None

        if self.supports_test_data_download:
            response = self._get(f"tools/{tool_id}/test_data_download?filename={filename}", admin=True)
            if response.status_code == 200:
                if mode == 'file':
                    result = response.content
                elif mode == 'directory':
                    prefix = os.path.basename(filename)
                    path = tempfile.mkdtemp(prefix=prefix)
                    with tarfile.open(fileobj=io.BytesIO(response.content)) as tar_contents:
                        tar_contents.extractall(path=path)
                    result = path
        else:
            # We can only use local data
            local_path = self.test_data_path(tool_id, filename)

        if result is None and (local_path is None or not os.path.exists(local_path)):
            for test_data_directory in self.test_data_directories:
                local_path = os.path.join(test_data_directory, filename)
                if os.path.exists(local_path):
                    break

        if result is None and os.path.exists(local_path):
            if mode == 'file':
                result = open(local_path, mode='rb')
            elif mode == 'directory':
                # Make a copy, since we are going to clean up the returned path
                path = tempfile.mkdtemp()
                shutil.copytree(local_path, path)
                result = path

        if result is None:
            if is_output:
                raise AssertionError(f"Test output file ({filename}) is missing. If you are using planemo, try adding --update_test_data to generate it.")
            else:
                raise AssertionError(f"Test input file ({filename}) cannot be found.")

        return result

    def __output_id(self, output_data):
        # Allow data structure coming out of tools API - {id: <id>, output_name: <name>, etc...}
        # or simple id as comes out of workflow API.
        try:
            output_id = output_data.get('id')
        except AttributeError:
            output_id = output_data
        return output_id

    def stage_data_async(self, test_data, history_id, tool_id, force_path_paste=False, maxseconds=DEFAULT_TOOL_TEST_WAIT):
        fname = test_data['fname']
        tool_input = {
            "file_type": test_data['ftype'],
            "dbkey": test_data['dbkey'],
        }
        metadata = test_data.get("metadata", {})
        if not hasattr(metadata, "items"):
            raise Exception(f"Invalid metadata description found for input [{fname}] - [{metadata}]")
        for name, value in test_data.get('metadata', {}).items():
            tool_input["files_metadata|%s" % name] = value

        composite_data = test_data['composite_data']
        if composite_data:
            files = {}
            for i, file_name in enumerate(composite_data):
                if force_path_paste:
                    file_path = self.test_data_path(tool_id, file_name)
                    tool_input.update({
                        "files_%d|url_paste" % i: "file://" + file_path
                    })
                else:
                    file_content = self.test_data_download(tool_id, file_name, is_output=False)
                    files["files_%s|file_data" % i] = file_content
                tool_input.update({
                    "files_%d|type" % i: "upload_dataset",
                })
            name = test_data['name']
        else:
            name = os.path.basename(fname)
            tool_input.update({
                "files_0|NAME": name,
                "files_0|type": "upload_dataset",
            })
            files = {}
            if force_path_paste:
                file_name = self.test_data_path(tool_id, fname)
                tool_input.update({
                    "files_0|url_paste": "file://" + file_name
                })
            else:
                file_content = self.test_data_download(tool_id, fname, is_output=False)
                files = {
                    "files_0|file_data": file_content
                }
        submit_response_object = self.__submit_tool(history_id, "upload1", tool_input, extra_data={"type": "upload_dataset"}, files=files)
        submit_response = ensure_tool_run_response_okay(submit_response_object, "upload dataset %s" % name)
        assert "outputs" in submit_response, "Invalid response from server [%s], expecting outputs in response." % submit_response
        outputs = submit_response["outputs"]
        assert len(outputs) > 0, "Invalid response from server [%s], expecting an output dataset." % submit_response
        dataset = outputs[0]
        hid = dataset['id']
        self.uploads[os.path.basename(fname)] = self.uploads[fname] = self.uploads[name] = {"src": "hda", "id": hid}
        assert "jobs" in submit_response, "Invalid response from server [%s], expecting jobs in response." % submit_response
        jobs = submit_response["jobs"]
        assert len(jobs) > 0, "Invalid response from server [%s], expecting a job." % submit_response
        return lambda: self.wait_for_job(jobs[0]["id"], history_id, maxseconds=maxseconds)

    def run_tool(self, testdef, history_id, resource_parameters={}):
        # We need to handle the case where we've uploaded a valid compressed file since the upload
        # tool will have uncompressed it on the fly.

        inputs_tree = testdef.inputs.copy()
        for key, value in inputs_tree.items():
            values = [value] if not isinstance(value, list) else value
            new_values = []
            for value in values:
                if isinstance(value, TestCollectionDef):
                    hdca_id = self._create_collection(history_id, value)
                    new_values = [dict(src="hdca", id=hdca_id)]
                elif value in self.uploads:
                    new_values.append(self.uploads[value])
                else:
                    new_values.append(value)
            inputs_tree[key] = new_values

        if resource_parameters:
            inputs_tree["__job_resource|__job_resource__select"] = "yes"
            for key, value in resource_parameters.items():
                inputs_tree["__job_resource|%s" % key] = value

        # HACK: Flatten single-value lists. Required when using expand_grouping
        for key, value in inputs_tree.items():
            if isinstance(value, list) and len(value) == 1:
                inputs_tree[key] = value[0]

        submit_response = None
        for _ in range(30):
            submit_response = self.__submit_tool(history_id, tool_id=testdef.tool_id, tool_input=inputs_tree)
            if _are_tool_inputs_not_ready(submit_response):
                print("Tool inputs not ready yet")
                time.sleep(1)
                continue
            else:
                break

        submit_response_object = ensure_tool_run_response_okay(submit_response, "execute tool", inputs_tree)
        try:
            return Bunch(
                inputs=inputs_tree,
                outputs=self.__dictify_outputs(submit_response_object),
                output_collections=self.__dictify_output_collections(submit_response_object),
                jobs=submit_response_object['jobs'],
            )
        except KeyError:
            message = "Error creating a job for these tool inputs - %s" % submit_response_object['err_msg']
            raise RunToolException(message, inputs_tree)

    def _create_collection(self, history_id, collection_def):
        create_payload = dict(
            name=collection_def.name,
            element_identifiers=dumps(self._element_identifiers(collection_def)),
            collection_type=collection_def.collection_type,
            history_id=history_id,
        )
        return self._post("dataset_collections", data=create_payload).json()["id"]

    def _element_identifiers(self, collection_def):
        element_identifiers = []
        for element_dict in collection_def.elements:
            element_identifier = element_dict["element_identifier"]
            element_def = element_dict["element_definition"]
            if isinstance(element_def, TestCollectionDef):
                subelement_identifiers = self._element_identifiers(element_def)
                element = dict(
                    name=element_identifier,
                    src="new_collection",
                    collection_type=element_def.collection_type,
                    element_identifiers=subelement_identifiers
                )
            else:
                element = self.uploads[element_def["value"]].copy()
                element["name"] = element_identifier
                tags = element_def.get("attributes").get("tags")
                if tags:
                    element["tags"] = tags.split(",")
            element_identifiers.append(element)
        return element_identifiers

    def __dictify_output_collections(self, submit_response):
        output_collections_dict = OrderedDict()
        for output_collection in submit_response['output_collections']:
            output_collections_dict[output_collection.get("output_name")] = output_collection
        return output_collections_dict

    def __dictify_outputs(self, datasets_object):
        # Convert outputs list to a dictionary that can be accessed by
        # output_name so can be more flexible about ordering of outputs
        # but also allows fallback to legacy access as list mode.
        outputs_dict = OutputsDict()

        for output in datasets_object['outputs']:
            outputs_dict[output.get("output_name")] = output
        return outputs_dict

    def output_hid(self, output_data):
        return output_data['id']

    def delete_history(self, history):
        self._delete(f"histories/{history}")

    def __job_ready(self, job_id, history_id=None):
        if job_id is None:
            raise ValueError("__job_ready passed empty job_id")
        job_json = self._get("jobs/%s" % job_id).json()
        state = job_json['state']
        try:
            return self._state_ready(state, error_msg="Job in error state.")
        except Exception:
            if VERBOSE_ERRORS and history_id is not None:
                self._summarize_history(history_id)
            raise

    def _summarize_history(self, history_id):
        if history_id is None:
            raise ValueError("_summarize_history passed empty history_id")
        print("Problem in history with id %s - summary of history's datasets and jobs below." % history_id)
        try:
            history_contents = self.__contents(history_id)
        except Exception:
            print("*TEST FRAMEWORK FAILED TO FETCH HISTORY DETAILS*")
            return

        for history_content in history_contents:

            dataset = history_content

            print(ERROR_MESSAGE_DATASET_SEP)
            dataset_id = dataset.get('id', None)
            print("| %d - %s (HID - NAME) " % (int(dataset['hid']), dataset['name']))
            if history_content['history_content_type'] == 'dataset_collection':
                history_contents_json = self._get("histories/{}/contents/dataset_collections/{}".format(history_id, history_content["id"])).json()
                print("| Dataset Collection: %s" % history_contents_json)
                print("|")
                continue

            try:
                dataset_info = self._dataset_info(history_id, dataset_id)
                print("| Dataset State:")
                print(self.format_for_summary(dataset_info.get("state"), "Dataset state is unknown."))
                print("| Dataset Blurb:")
                print(self.format_for_summary(dataset_info.get("misc_blurb", ""), "Dataset blurb was empty."))
                print("| Dataset Info:")
                print(self.format_for_summary(dataset_info.get("misc_info", ""), "Dataset info is empty."))
                print("| Peek:")
                print(self.format_for_summary(dataset_info.get("peek", ""), "Peek unavilable."))
            except Exception:
                print("| *TEST FRAMEWORK ERROR FETCHING DATASET DETAILS*")
            try:
                provenance_info = self._dataset_provenance(history_id, dataset_id)
                print("| Dataset Job Standard Output:")
                print(self.format_for_summary(provenance_info.get("stdout", ""), "Standard output was empty."))
                print("| Dataset Job Standard Error:")
                print(self.format_for_summary(provenance_info.get("stderr", ""), "Standard error was empty."))
            except Exception:
                print("| *TEST FRAMEWORK ERROR FETCHING JOB DETAILS*")
            print("|")
        try:
            jobs_json = self._get("jobs?history_id=%s" % history_id).json()
            for job_json in jobs_json:
                print(ERROR_MESSAGE_DATASET_SEP)
                print("| Job %s" % job_json["id"])
                print("| State: ")
                print(self.format_for_summary(job_json.get("state", ""), "Job state is unknown."))
                print("| Update Time:")
                print(self.format_for_summary(job_json.get("update_time", ""), "Job update time is unknown."))
                print("| Create Time:")
                print(self.format_for_summary(job_json.get("create_time", ""), "Job create time is unknown."))
                print("|")
            print(ERROR_MESSAGE_DATASET_SEP)
        except Exception:
            print(ERROR_MESSAGE_DATASET_SEP)
            print("*TEST FRAMEWORK FAILED TO FETCH HISTORY JOBS*")
            print(ERROR_MESSAGE_DATASET_SEP)

    def format_for_summary(self, blob, empty_message, prefix="|  "):
        contents = "\n".join(f"{prefix}{line.strip()}" for line in io.StringIO(blob).readlines() if line.rstrip("\n\r"))
        return contents or f"{prefix}*{empty_message}*"

    def _dataset_provenance(self, history_id, id):
        provenance = self._get(f"histories/{history_id}/contents/{id}/provenance").json()
        return provenance

    def _dataset_info(self, history_id, id):
        dataset_json = self._get(f"histories/{history_id}/contents/{id}").json()
        return dataset_json

    def __contents(self, history_id):
        history_contents_response = self._get("histories/%s/contents" % history_id)
        history_contents_response.raise_for_status()
        return history_contents_response.json()

    def _state_ready(self, state_str, error_msg):
        if state_str == 'ok':
            return True
        elif state_str == 'error':
            raise Exception(error_msg)
        return None

    def __submit_tool(self, history_id, tool_id, tool_input, extra_data={}, files=None):
        data = dict(
            history_id=history_id,
            tool_id=tool_id,
            inputs=dumps(tool_input),
            **extra_data
        )
        return self._post("tools", files=files, data=data)

    def ensure_user_with_email(self, email, password=None):
        admin_key = self.master_api_key
        all_users_response = self._get('users', key=admin_key)
        try:
            all_users_response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise Exception(f"Failed to verify user with email [{email}] exists - perhaps you're targetting the wrong Galaxy server or using an incorrect admin API key. HTTP error: {e}")
        all_users = all_users_response.json()
        try:
            test_user = [user for user in all_users if user["email"] == email][0]
        except IndexError:
            username = re.sub(r"[^a-z-\d]", '--', email.lower())
            password = password or 'testpass'
            # If remote user middleware is enabled - this endpoint consumes
            # ``remote_user_email`` otherwise it requires ``email``, ``password``
            # and ``username``.
            data = dict(
                remote_user_email=email,
                email=email,
                password=password,
                username=username,
            )
            test_user = self._post('users', data, key=admin_key).json()
        return test_user

    def __test_data_downloader(self, tool_id):
        def test_data_download(filename, mode='file'):
            return self.test_data_download(tool_id, filename, mode=mode)
        return test_data_download

    def __dataset_fetcher(self, history_id):
        def fetcher(hda_id, base_name=None):
            url = f"histories/{history_id}/contents/{hda_id}/display?raw=true"
            if base_name:
                url += "&filename=%s" % base_name
            response = None
            for _ in range(self.download_attempts):
                response = self._get(url)
                if response.status_code == 500:
                    print(f"Retrying failed download with status code {response.status_code}")
                    time.sleep(self.download_sleep)
                    continue
                else:
                    break

            response.raise_for_status()
            return response.content

        return fetcher

    def api_key_header(self, key, admin, anon):
        header = {}
        if not anon:
            if not key:
                key = self.api_key if not admin else self.master_api_key
            header['x-api-key'] = key
        return header

    def _post(self, path, data=None, files=None, key=None, admin=False, anon=False, json=False):
        # If json=True, use post payload using request's json parameter instead of the data
        # parameter (i.e. assume the contents is a jsonified blob instead of form parameters
        # with individual parameters jsonified if needed).
        headers = self.api_key_header(key=key, admin=admin, anon=anon)
        url = f"{self.api_url}/{path}"
        return galaxy_requests_post(url, data=data, files=files, as_json=json, headers=headers)

    def _delete(self, path, data=None, key=None, admin=False, anon=False):
        headers = self.api_key_header(key=key, admin=admin, anon=anon)
        return requests.delete(f"{self.api_url}/{path}", params=data, headers=headers)

    def _patch(self, path, data=None, key=None, admin=False, anon=False):
        headers = self.api_key_header(key=key, admin=admin, anon=anon)
        return requests.patch(f"{self.api_url}/{path}", data=data, headers=headers)

    def _put(self, path, data=None, key=None, admin=False, anon=False):
        headers = self.api_key_header(key=key, admin=admin, anon=anon)
        return requests.put(f"{self.api_url}/{path}", data=data, headers=headers)

    def _get(self, path, data=None, key=None, admin=False, anon=False):
        headers = self.api_key_header(key=key, admin=admin, anon=anon)
        if path.startswith("/api"):
            path = path[len("/api"):]
        url = f"{self.api_url}/{path}"
        # no data for GET
        return requests.get(url, params=data, headers=headers)


def ensure_tool_run_response_okay(submit_response_object, request_desc, inputs=None):
    if submit_response_object.status_code != 200:
        message = None
        dynamic_param_error = False
        try:
            err_response = submit_response_object.json()
            if "param_errors" in err_response:
                param_errors = err_response["param_errors"]
                if "dbkey" in param_errors:
                    dbkey_err_obj = param_errors["dbkey"]
                    dbkey_val = dbkey_err_obj.get("parameter_value")
                    message = "Invalid dbkey specified [%s]" % dbkey_val
                for key, val in param_errors.items():
                    if isinstance(val, dict) and val.get("is_dynamic"):
                        dynamic_param_error = True
            if message is None:
                message = err_response.get("err_msg") or None
        except Exception:
            # invalid JSON content.
            pass
        if message is None:
            template = "Request to %s failed - invalid JSON content returned from Galaxy server [%s]"
            message = template % (request_desc, submit_response_object.text)
        raise RunToolException(message, inputs, dynamic_param_error=dynamic_param_error)
    submit_response = submit_response_object.json()
    return submit_response


def _are_tool_inputs_not_ready(submit_response):
    if submit_response.status_code != 400:
        return False
    try:
        submit_json = submit_response.json()
        return submit_json.get("err_code") == 400015
    except Exception:
        return False


class RunToolException(Exception):

    def __init__(self, message, inputs=None, dynamic_param_error=False):
        super().__init__(message)
        self.inputs = inputs
        self.dynamic_param_error = dynamic_param_error


# Galaxy specific methods - rest of this can be used with arbitrary files and such.
def verify_hid(filename, hda_id, attributes, test_data_downloader, hid="", dataset_fetcher=None, keep_outputs_dir=False):
    assert dataset_fetcher is not None

    def verify_extra_files(extra_files):
        _verify_extra_files_content(extra_files, hda_id, dataset_fetcher=dataset_fetcher, test_data_downloader=test_data_downloader, keep_outputs_dir=keep_outputs_dir)

    data = dataset_fetcher(hda_id)
    item_label = ""
    verify(
        item_label,
        data,
        attributes=attributes,
        filename=filename,
        get_filecontent=test_data_downloader,
        keep_outputs_dir=keep_outputs_dir,
        verify_extra_files=verify_extra_files,
    )


def verify_collection(output_collection_def, data_collection, verify_dataset):
    name = output_collection_def.name

    expected_collection_type = output_collection_def.collection_type
    if expected_collection_type:
        collection_type = data_collection["collection_type"]
        if expected_collection_type != collection_type:
            template = "Expected output collection [%s] to be of type [%s], was of type [%s]."
            message = template % (name, expected_collection_type, collection_type)
            raise AssertionError(message)

    expected_element_count = output_collection_def.count
    if expected_element_count:
        actual_element_count = len(data_collection["elements"])
        if expected_element_count != actual_element_count:
            template = "Expected output collection [%s] to have %s elements, but it had %s."
            message = template % (name, expected_element_count, actual_element_count)
            raise AssertionError(message)

    def get_element(elements, id):
        for element in elements:
            if element["element_identifier"] == id:
                return element
        return False

    def verify_elements(element_objects, element_tests):
        # sorted_test_ids = [None] * len(element_tests)
        expected_sort_order = []

        eo_ids = [_["element_identifier"] for _ in element_objects]
        for element_identifier, element_test in element_tests.items():
            if isinstance(element_test, dict):
                element_outfile, element_attrib = None, element_test
            else:
                element_outfile, element_attrib = element_test
            if 'expected_sort_order' in element_attrib:
                expected_sort_order.append(element_identifier)

            element = get_element(element_objects, element_identifier)
            if not element:
                template = "Failed to find identifier '%s' in the tool generated collection elements %s"
                message = template % (element_identifier, eo_ids)
                raise AssertionError(message)

            element_type = element["element_type"]
            if element_type != "dataset_collection":
                verify_dataset(element, element_attrib, element_outfile)
            if element_type == "dataset_collection":
                elements = element["object"]["elements"]
                verify_elements(elements, element_attrib.get("elements", {}))

        if len(expected_sort_order) > 0:
            i = 0
            for element_identifier in expected_sort_order:
                element = None
                while i < len(element_objects):
                    if element_objects[i]["element_identifier"] == element_identifier:
                        element = element_objects[i]
                        i += 1
                        break
                    i += 1
                if element is None:
                    template = "Collection identifier '%s' found out of order, expected order of %s for the tool generated collection elements %s"
                    message = template % (element_identifier, expected_sort_order, eo_ids)
                    raise AssertionError(message)

    verify_elements(data_collection["elements"], output_collection_def.element_tests)


def _verify_composite_datatype_file_content(file_name, hda_id, base_name=None, attributes=None, dataset_fetcher=None, test_data_downloader=None, keep_outputs_dir=False, mode='file'):
    assert dataset_fetcher is not None

    data = dataset_fetcher(hda_id, base_name)
    item_label = "History item %s" % hda_id
    try:
        verify(
            item_label,
            data,
            attributes=attributes,
            filename=file_name,
            get_filecontent=test_data_downloader,
            keep_outputs_dir=keep_outputs_dir,
            mode=mode,
        )
    except AssertionError as err:
        errmsg = f'Composite file ({base_name}) of {item_label} different than expected, difference:\n'
        errmsg += util.unicodify(err)
        raise AssertionError(errmsg)


def _verify_extra_files_content(extra_files, hda_id, dataset_fetcher, test_data_downloader, keep_outputs_dir):
    files_list = []
    cleanup_directories = []
    for extra_file_dict in extra_files:
        extra_file_type = extra_file_dict["type"]
        extra_file_name = extra_file_dict["name"]
        extra_file_attributes = extra_file_dict["attributes"]
        extra_file_value = extra_file_dict["value"]

        if extra_file_type == 'file':
            files_list.append((extra_file_name, extra_file_value, extra_file_attributes, extra_file_type))
        elif extra_file_type == 'directory':
            extracted_path = test_data_downloader(extra_file_value, mode='directory')
            cleanup_directories.append(extracted_path)
            for root, directories, files in util.path.safe_walk(extracted_path):
                for filename in files:
                    filename = os.path.join(root, filename)
                    filename = os.path.relpath(filename, extracted_path)
                    files_list.append((filename, os.path.join(extracted_path, filename), extra_file_attributes, extra_file_type))
        else:
            raise ValueError('unknown extra_files type: %s' % extra_file_type)
    try:
        for filename, filepath, attributes, extra_file_type in files_list:
            _verify_composite_datatype_file_content(filepath, hda_id, base_name=filename, attributes=attributes, dataset_fetcher=dataset_fetcher, test_data_downloader=test_data_downloader, keep_outputs_dir=keep_outputs_dir, mode=extra_file_type)
    finally:
        for path in cleanup_directories:
            shutil.rmtree(path)


class NullClientTestConfig:

    def get_test_config(self, job_data):
        return None


class DictClientTestConfig:

    def __init__(self, tools):
        self._tools = tools or {}

    def get_test_config(self, job_data):
        # TODO: allow short ids, allow versions below outer id instead of key concatenation.
        tool_id = job_data.get("tool_id")
        tool_version = job_data.get("tool_version")
        tool_test_config = None
        tool_version_test_config = None
        is_default = False
        if tool_id in self._tools:
            tool_test_config = self._tools[tool_id]
        if tool_test_config is None:
            tool_id = f"{tool_id}/{tool_version}"
            if tool_id in self._tools:
                tool_version_test_config = self._tools[tool_id]
        else:
            if tool_version in tool_test_config:
                tool_version_test_config = tool_test_config[tool_version]
            elif "default" in tool_test_config:
                tool_version_test_config = tool_test_config["default"]
                is_default = True

        if tool_version_test_config:
            test_index = job_data.get("test_index")
            if test_index in tool_version_test_config:
                return tool_version_test_config[test_index]
            elif str(test_index) in tool_version_test_config:
                return tool_version_test_config[str(test_index)]
            if 'default' in tool_version_test_config:
                return tool_version_test_config['default']
            elif is_default:
                return tool_version_test_config
        return None


def verify_tool(tool_id,
                galaxy_interactor,
                resource_parameters=None,
                register_job_data=None,
                test_index=0,
                tool_version=None,
                quiet=False,
                test_history=None,
                no_history_cleanup=False,
                publish_history=False,
                force_path_paste=False,
                maxseconds=DEFAULT_TOOL_TEST_WAIT,
                tool_test_dicts=None,
                client_test_config=None,
                skip_with_reference_data=False,
                skip_on_dynamic_param_errors=False):
    if resource_parameters is None:
        resource_parameters = {}
    if client_test_config is None:
        client_test_config = NullClientTestConfig()
    tool_test_dicts = tool_test_dicts or galaxy_interactor.get_tool_tests(tool_id, tool_version=tool_version)
    tool_test_dict = tool_test_dicts[test_index]
    if "test_index" not in tool_test_dict:
        tool_test_dict["test_index"] = test_index
    if "tool_id" not in tool_test_dict:
        tool_test_dict["tool_id"] = tool_id
    if tool_version is None and "tool_version" in tool_test_dict:
        tool_version = tool_test_dict.get("tool_version")

    job_data = {
        "tool_id": tool_id,
        "tool_version": tool_version,
        "test_index": test_index,
    }
    client_config = client_test_config.get_test_config(job_data)
    skip_message = None
    if client_config is not None:
        job_data.update(client_config)
        skip_message = job_data.get("skip")

    if not skip_message and skip_with_reference_data:
        required_data_tables = tool_test_dict.get("required_data_tables")
        required_loc_files = tool_test_dict.get("required_loc_files")
        # TODO: actually hit the API and see if these tables are available.
        if required_data_tables:
            skip_message = f"Skipping test because of required data tables ({required_data_tables})"
        if required_loc_files:
            skip_message = f"Skipping test because of required loc files ({required_loc_files})"

    if skip_message:
        job_data["status"] = "skip"
        register_job_data(job_data)
        return

    tool_test_dict.setdefault('maxseconds', maxseconds)
    testdef = ToolTestDescription(tool_test_dict)
    _handle_def_errors(testdef)

    created_history = False
    if test_history is None:
        created_history = True
        history_name = f"Tool Test History for {tool_id}/{tool_version}-{test_index}"
        test_history = galaxy_interactor.new_history(history_name=history_name, publish_history=publish_history)

    # Upload data to test_history, run the tool and check the outputs - record
    # API input, job info, tool run exception, as well as exceptions related to
    # job output checking and register they with the test plugin so it can
    # record structured information.
    tool_inputs = None
    job_stdio = None
    job_output_exceptions = None
    tool_execution_exception = None
    input_staging_exception = None
    expected_failure_occurred = False
    begin_time = time.time()
    try:
        try:
            stage_data_in_history(
                galaxy_interactor,
                tool_id,
                testdef.test_data(),
                history=test_history,
                force_path_paste=force_path_paste,
                maxseconds=maxseconds,
            )
        except Exception as e:
            input_staging_exception = e
            raise
        try:
            tool_response = galaxy_interactor.run_tool(testdef, test_history, resource_parameters=resource_parameters)
            data_list, jobs, tool_inputs = tool_response.outputs, tool_response.jobs, tool_response.inputs
            data_collection_list = tool_response.output_collections
        except RunToolException as e:
            tool_inputs = e.inputs
            tool_execution_exception = e
            if not testdef.expect_failure:
                raise e
            else:
                expected_failure_occurred = True
        except Exception as e:
            tool_execution_exception = e
            raise e

        if not expected_failure_occurred:
            assert data_list or data_collection_list

            try:
                job_stdio = _verify_outputs(testdef, test_history, jobs, tool_id, data_list, data_collection_list, galaxy_interactor, quiet=quiet)
            except JobOutputsError as e:
                job_stdio = e.job_stdio
                job_output_exceptions = e.output_exceptions
                raise e
            except Exception as e:
                job_output_exceptions = [e]
                raise e
    finally:
        if register_job_data is not None:
            end_time = time.time()
            job_data["time_seconds"] = end_time - begin_time
            if tool_inputs is not None:
                job_data["inputs"] = tool_inputs
            if job_stdio is not None:
                job_data["job"] = job_stdio
            status = "success"
            if job_output_exceptions:
                job_data["output_problems"] = [util.unicodify(_) for _ in job_output_exceptions]
                status = "failure"
            if tool_execution_exception:
                job_data["execution_problem"] = util.unicodify(tool_execution_exception)
                dynamic_param_error = getattr(tool_execution_exception, "dynamic_param_error", False)
                job_data["dynamic_param_error"] = dynamic_param_error
                status = "error" if not skip_on_dynamic_param_errors or not dynamic_param_error else "skip"
            if input_staging_exception:
                job_data["execution_problem"] = "Input staging problem: %s" % util.unicodify(input_staging_exception)
                status = "error"
            job_data["status"] = status
            register_job_data(job_data)

    if created_history and not no_history_cleanup:
        galaxy_interactor.delete_history(test_history)


def _handle_def_errors(testdef):
    # If the test generation had an error, raise
    if testdef.error:
        if testdef.exception:
            if isinstance(testdef.exception, Exception):
                raise testdef.exception
            else:
                raise Exception(testdef.exception)
        else:
            raise Exception("Test parse failure")


def _verify_outputs(testdef, history, jobs, tool_id, data_list, data_collection_list, galaxy_interactor, quiet=False):
    assert len(jobs) == 1, "Test framework logic error, somehow tool test resulted in more than one job."
    job = jobs[0]

    maxseconds = testdef.maxseconds
    if testdef.num_outputs is not None:
        expected = testdef.num_outputs
        actual = len(data_list) + len(data_collection_list)
        if expected != actual:
            message_template = "Incorrect number of outputs - expected %d, found %s."
            message = message_template % (expected, actual)
            raise Exception(message)
    found_exceptions = []

    def register_exception(e):
        if not found_exceptions and not quiet:
            # Only print this stuff out once.
            for stream in ['stdout', 'stderr']:
                if stream in job_stdio:
                    print(_format_stream(job_stdio[stream], stream=stream, format=True), file=sys.stderr)
        found_exceptions.append(e)

    if testdef.expect_failure:
        if testdef.outputs:
            raise Exception("Cannot specify outputs in a test expecting failure.")

    # Wait for the job to complete and register expections if the final
    # status was not what test was expecting.
    job_failed = False
    try:
        galaxy_interactor.wait_for_job(job['id'], history, maxseconds)
    except Exception as e:
        job_failed = True
        if not testdef.expect_failure:
            found_exceptions.append(e)

    job_stdio = galaxy_interactor.get_job_stdio(job['id'])

    if not job_failed and testdef.expect_failure:
        error = AssertionError("Expected job to fail but Galaxy indicated the job successfully completed.")
        register_exception(error)

    expect_exit_code = testdef.expect_exit_code
    if expect_exit_code is not None:
        exit_code = job_stdio["exit_code"]
        if str(expect_exit_code) != str(exit_code):
            error = AssertionError(f"Expected job to complete with exit code {expect_exit_code}, found {exit_code}")
            register_exception(error)

    for output_index, output_dict in enumerate(testdef.outputs):
        # Get the correct hid
        name = output_dict["name"]
        outfile = output_dict["value"]
        attributes = output_dict["attributes"]
        output_testdef = Bunch(name=name, outfile=outfile, attributes=attributes)
        try:
            output_data = data_list[name]
        except (TypeError, KeyError):
            # Legacy - fall back on ordered data list access if data_list is
            # just a list (case with twill variant or if output changes its
            # name).
            if hasattr(data_list, "values"):
                output_data = list(data_list.values())[output_index]
            else:
                output_data = data_list[len(data_list) - len(testdef.outputs) + output_index]
        assert output_data is not None
        try:
            galaxy_interactor.verify_output(history, jobs, output_data, output_testdef=output_testdef, tool_id=tool_id, maxseconds=maxseconds)
        except Exception as e:
            register_exception(e)

    other_checks = {
        "command_line": "Command produced by the job",
        "command_version": "Tool version indicated during job execution",
        "stdout": "Standard output of the job",
        "stderr": "Standard error of the job",
    }
    # TODO: Only hack the stdio like this for older profile, for newer tool profiles
    # add some syntax for asserting job messages maybe - or just drop this because exit
    # code and regex on stdio can be tested directly - so this is really testing Galaxy
    # core handling more than the tool.
    job_messages = job_stdio.get("job_messages") or []
    stdout_prefix = ""
    stderr_prefix = ""
    for job_message in job_messages:
        message_type = job_message.get("type")
        if message_type == "regex" and job_message.get("stream") == "stderr":
            stderr_prefix += (job_message.get("desc") or '') + "\n"
        elif message_type == "regex" and job_message.get("stream") == "stdout":
            stdout_prefix += (job_message.get("desc") or '') + "\n"
        elif message_type == "exit_code":
            stderr_prefix += (job_message.get("desc") or '') + "\n"
        else:
            raise Exception(f"Unknown job message type [{message_type}] in [{job_message}]")

    for what, description in other_checks.items():
        if getattr(testdef, what, None) is not None:
            try:
                raw_data = job_stdio[what]
                assertions = getattr(testdef, what)
                if what == "stdout":
                    data = stdout_prefix + raw_data
                elif what == "stderr":
                    data = stderr_prefix + raw_data
                else:
                    data = raw_data
                verify_assertions(data, assertions)
            except AssertionError as err:
                errmsg = '%s different than expected\n' % description
                errmsg += util.unicodify(err)
                register_exception(AssertionError(errmsg))

    for output_collection_def in testdef.output_collections:
        try:
            name = output_collection_def.name
            # TODO: data_collection_list is clearly a bad name for dictionary.
            if name not in data_collection_list:
                template = "Failed to find output [%s], tool outputs include [%s]"
                message = template % (name, ",".join(data_collection_list.keys()))
                raise AssertionError(message)

            # Data collection returned from submission, elements may have been populated after
            # the job completed so re-hit the API for more information.
            data_collection_id = data_collection_list[name]["id"]
            galaxy_interactor.verify_output_collection(output_collection_def, data_collection_id, history, tool_id)
        except Exception as e:
            register_exception(e)

    if found_exceptions:
        raise JobOutputsError(found_exceptions, job_stdio)
    else:
        return job_stdio


def _format_stream(output, stream, format):
    output = output or ''
    if format:
        msg = "---------------------- >> begin tool %s << -----------------------\n" % stream
        msg += output + "\n"
        msg += "----------------------- >> end tool %s << ------------------------\n" % stream
    else:
        msg = output
    return msg


class JobOutputsError(AssertionError):

    def __init__(self, output_exceptions, job_stdio):
        big_message = "\n".join(map(util.unicodify, output_exceptions))
        super().__init__(big_message)
        self.job_stdio = job_stdio
        self.output_exceptions = output_exceptions


class ToolTestDescription:
    """
    Encapsulates information about a tool test, and allows creation of a
    dynamic TestCase class (the unittest framework is very class oriented,
    doing dynamic tests in this way allows better integration)
    """

    def __init__(self, processed_test_dict):
        assert "test_index" in processed_test_dict, "Invalid processed test description, must have a 'test_index' for naming, etc.."
        test_index = processed_test_dict["test_index"]
        name = processed_test_dict.get('name', 'Test-%d' % (test_index + 1))
        maxseconds = processed_test_dict.get('maxseconds', DEFAULT_TOOL_TEST_WAIT)
        if maxseconds is not None:
            maxseconds = int(maxseconds)

        self.test_index = test_index
        assert "tool_id" in processed_test_dict, "Invalid processed test description, must have a 'tool_id' for naming, etc.."
        self.tool_id = processed_test_dict["tool_id"]
        self.tool_version = processed_test_dict.get("tool_version")
        self.name = name
        self.maxseconds = maxseconds
        self.required_files = processed_test_dict.get("required_files", [])
        self.required_data_tables = processed_test_dict.get("required_data_tables", [])
        self.required_loc_files = processed_test_dict.get("required_loc_files", [])

        inputs = processed_test_dict.get("inputs", {})
        loaded_inputs = {}
        for key, value in inputs.items():
            if isinstance(value, dict) and value.get("model_class"):
                loaded_inputs[key] = TestCollectionDef.from_dict(value)
            else:
                loaded_inputs[key] = value

        self.inputs = loaded_inputs
        self.outputs = processed_test_dict.get("outputs", [])
        self.num_outputs = processed_test_dict.get("num_outputs", None)

        self.error = processed_test_dict.get("error", False)
        self.exception = processed_test_dict.get("exception", None)

        self.output_collections = map(TestCollectionOutputDef.from_dict, processed_test_dict.get("output_collections", []))
        self.command_line = processed_test_dict.get("command_line", None)
        self.command_version = processed_test_dict.get("command_version", None)
        self.stdout = processed_test_dict.get("stdout", None)
        self.stderr = processed_test_dict.get("stderr", None)
        self.expect_exit_code = processed_test_dict.get("expect_exit_code", None)
        self.expect_failure = processed_test_dict.get("expect_failure", False)

    def test_data(self):
        """
        Iterator over metadata representing the required files for upload.
        """
        return test_data_iter(self.required_files)

    def to_dict(self):
        inputs_dict = {}
        for key, value in self.inputs.items():
            if hasattr(value, "to_dict"):
                inputs_dict[key] = value.to_dict()
            else:
                inputs_dict[key] = value

        return {
            "inputs": inputs_dict,
            "outputs": self.outputs,
            "output_collections": [_.to_dict() for _ in self.output_collections],
            "num_outputs": self.num_outputs,
            "command_line": self.command_line,
            "command_version": self.command_version,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "expect_exit_code": self.expect_exit_code,
            "expect_failure": self.expect_failure,
            "name": self.name,
            "test_index": self.test_index,
            "tool_id": self.tool_id,
            "tool_version": self.tool_version,
            "required_files": self.required_files,
            "required_data_tables": self.required_data_tables,
            "required_loc_files": self.required_loc_files,
            "error": self.error,
            "exception": self.exception,
        }


@nottest
def test_data_iter(required_files):
    for fname, extra in required_files:
        data_dict = dict(
            fname=fname,
            metadata=extra.get('metadata', {}),
            composite_data=extra.get('composite_data', []),
            ftype=extra.get('ftype', DEFAULT_FTYPE),
            dbkey=extra.get('dbkey', DEFAULT_DBKEY),
        )
        edit_attributes = extra.get('edit_attributes', [])

        # currently only renaming is supported
        for edit_att in edit_attributes:
            if edit_att.get('type', None) == 'name':
                new_name = edit_att.get('value', None)
                assert new_name, 'You must supply the new dataset name as the value tag of the edit_attributes tag'
                data_dict['name'] = new_name
            else:
                raise Exception('edit_attributes type (%s) is unimplemented' % edit_att.get('type', None))

        yield data_dict


def galaxy_requests_post(url, data=None, files=None, as_json=False, params=None, headers=None):
    """Handle some Galaxy conventions and work around requests issues.

    This is admittedly kind of hacky, so the interface may change frequently - be
    careful on reuse.

    If ``as_json`` is True, use post payload using request's json parameter instead
    of the data parameter (i.e. assume the contents is a json-ified blob instead of
    form parameters with individual parameters json-ified if needed). requests doesn't
    allow files to be specified with the json parameter - so rewrite the parameters
    to handle that if as_json is True with specified files.
    """
    params = params or {}
    data = data or {}

    # handle encoded files
    if files is None:
        # if not explicitly passed, check __files... convention used in tool testing
        # and API testing code
        files = data.get("__files", None)
        if files is not None:
            del data["__files"]

    # files doesn't really work with json, so dump the parameters
    # and do a normal POST with request's data parameter.
    if bool(files) and as_json:
        as_json = False
        new_items = {}
        for key, val in data.items():
            if isinstance(val, dict) or isinstance(val, list):
                new_items[key] = dumps(val)
        data.update(new_items)

    kwd = {
        'files': files,
    }
    if headers:
        kwd['headers'] = headers
    if as_json:
        kwd['json'] = data
        kwd['params'] = params
    else:
        data.update(params)
        kwd['data'] = data

    return requests.post(url, **kwd)
