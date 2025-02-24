"""Abstractions used by the Galaxy testing frameworks for interacting with the Galaxy API.

These abstractions are geared toward testing use cases and populating fixtures.
For a more general framework for working with the Galaxy API checkout `bioblend
<https://github.com/galaxyproject/bioblend>`__.

The populators are broken into different categories of data one might want to populate
and work with (datasets, histories, libraries, and workflows). Within each populator
type abstract classes describe high-level functionality that depend on abstract
HTTP verbs executions (e.g. methods for executing GET, POST, DELETE). The abstract
classes are :class:`galaxy_test.base.populators.BaseDatasetPopulator`,
:class:`galaxy_test.base.populators.BaseWorkflowPopulator`, and
:class:`galaxy_test.base.populators.BaseDatasetCollectionPopulator`.

There are a few different concrete ways to supply these low-level verb executions.
For instance :class:`galaxy_test.base.populators.DatasetPopulator` implements the abstract
:class:`galaxy_test.base.populators.BaseDatasetPopulator` by leveraging a galaxy interactor
:class:`galaxy.tool_util.interactor.GalaxyInteractorApi`. It is non-intuitive
that the Galaxy testing framework uses the tool testing code inside Galaxy's code
base for a lot of heavy lifting. This is due to the API testing framework organically
growing from the tool testing framework that predated it and then the tool testing
framework being extracted for re-use in `Planemo <https://github.com/galaxyproject/planemo>`__, etc..

These other two concrete implementation of the populators are much more
direct and intuitive. :class:`galaxy_test.base.populators.GiDatasetPopulator`, et. al.
are populators built based on Bioblend ``gi`` objects to build URLs and describe
API keys. :class:`galaxy_test.selenium.framework.SeleniumSessionDatasetPopulator`,
et al. are populators built based on Selenium sessions to leverage Galaxy cookies
for auth for instance.

All three of these implementations are now effectively light wrappers around
`requests <https://requests.readthedocs.io/>`__. Not leveraging requests directly
is a bit ugly and this ugliness again stems from these organically growing from a
framework that originally didn't use requests at all.

API tests and Selenium tests routinely use requests directly and that is totally fine,
requests should just be filtered through the verb abstractions if that functionality
is then added to populators to be shared across tests or across testing frameworks.
"""

import base64
import contextlib
import json
import os
import tarfile
import tempfile
import time
import unittest
import urllib.parse
from abc import (
    ABCMeta,
    abstractmethod,
)
from functools import wraps
from io import StringIO
from operator import itemgetter
from typing import (
    Any,
    Callable,
    cast,
    Dict,
    Generator,
    List,
    NamedTuple,
    Optional,
    Set,
    Tuple,
    Union,
)
from uuid import UUID

import cwltest.compare
import requests
import yaml
from bioblend.galaxyclient import GalaxyClient
from gxformat2 import (
    convert_and_import_workflow,
    ImporterGalaxyInterface,
)
from gxformat2.yaml import ordered_load
from pydantic import UUID4
from requests import Response
from rocrate.rocrate import ROCrate
from typing_extensions import (
    Literal,
    Self,
    TypedDict,
)

from galaxy.schema.schema import (
    CreateToolLandingRequestPayload,
    CreateWorkflowLandingRequestPayload,
    ToolLandingRequest,
    WorkflowLandingRequest,
)
from galaxy.tool_util.client.staging import InteractorStaging
from galaxy.tool_util.cwl.util import (
    download_output,
    GalaxyOutput,
    guess_artifact_type,
    invocation_to_output,
    output_to_cwl_json,
    tool_response_to_output,
)
from galaxy.tool_util.verify.test_data import TestDataResolver
from galaxy.tool_util.verify.wait import (
    timeout_type,
    TimeoutAssertionError,
    wait_on as tool_util_wait_on,
)
from galaxy.util import (
    DEFAULT_SOCKET_TIMEOUT,
    galaxy_root_path,
    UNKNOWN,
)
from galaxy.util.path import StrPath
from galaxy.util.resources import resource_string
from galaxy.util.unittest_utils import skip_if_site_down
from galaxy_test.base.decorators import (
    has_requirement,
    using_requirement,
)
from galaxy_test.base.json_schema_utils import JsonSchemaValidator
from . import api_asserts
from .api import (
    AnonymousGalaxyInteractor,
    ApiTestInteractor,
    HasAnonymousGalaxyInteractor,
)
from .api_util import random_name
from .env import REQUIRE_ALL_NEEDED_TOOLS

FILE_URL = "https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/4.bed"
FILE_MD5 = "37b59762b59fff860460522d271bc111"

CWL_TOOL_DIRECTORY = os.path.join(galaxy_root_path, "test", "functional", "tools", "cwl_tools")

# Simple workflow that takes an input and call cat wrapper on it.
workflow_str = resource_string(__package__, "data/test_workflow_1.ga")
# Simple workflow that takes an input and filters with random lines twice in a
# row - first grabbing 8 lines at random and then 6.
workflow_random_x2_str = resource_string(__package__, "data/test_workflow_2.ga")

DEFAULT_TIMEOUT = 60  # Secs to wait for state to turn ok

SKIP_FLAKEY_TESTS_ON_ERROR = os.environ.get("GALAXY_TEST_SKIP_FLAKEY_TESTS_ON_ERROR", None)

PRIVATE_ROLE_TYPE = "private"


def flakey(method):
    @wraps(method)
    def wrapped_method(*args, **kwargs):
        try:
            method(*args, **kwargs)
        except unittest.SkipTest:
            raise
        except Exception:
            if SKIP_FLAKEY_TESTS_ON_ERROR:
                raise unittest.SkipTest("Error encountered during test marked as @flakey.")
            else:
                raise

    return wrapped_method


def get_tool_ids(interactor: AnonymousGalaxyInteractor):
    index = interactor.get("tools", data=dict(in_panel=False))
    api_asserts.assert_status_code_is_ok(index, "Failed to fetch toolbox for target Galaxy.")
    tools = index.json()
    # In panels by default, so flatten out sections...
    tool_ids = [itemgetter("id")(_) for _ in tools]
    return tool_ids


def skip_without_tool(tool_id: str):
    """Decorate an API test method as requiring a specific tool.

    Have test framework skip the test case if the tool is unavailable.
    """

    def method_wrapper(method):

        @wraps(method)
        def wrapped_method(api_test_case, *args, **kwargs):
            check_missing_tool(tool_id not in get_tool_ids(api_test_case.anonymous_galaxy_interactor))
            return method(api_test_case, *args, **kwargs)

        return wrapped_method

    return method_wrapper


def skip_without_asgi(method):
    @wraps(method)
    def wrapped_method(api_test_case: HasAnonymousGalaxyInteractor, *args, **kwd):
        interactor = api_test_case.anonymous_galaxy_interactor
        config_response = interactor.get("configuration")
        api_asserts.assert_status_code_is_ok(config_response, "Failed to fetch configuration for target Galaxy.")
        config = config_response.json()
        asgi_enabled = config.get("asgi_enabled", False)
        if not asgi_enabled:
            raise unittest.SkipTest("ASGI not enabled, skipping test")
        return method(api_test_case, *args, **kwd)

    return wrapped_method


def skip_without_datatype(extension: str):
    """Decorate an API test method as requiring a specific datatype.

    Have test framework skip the test case if the datatype is unavailable.
    """

    def has_datatype(api_test_case: HasAnonymousGalaxyInteractor):
        interactor = api_test_case.anonymous_galaxy_interactor
        index_response = interactor.get("datatypes", anon=True)
        api_asserts.assert_status_code_is_ok(index_response, "Failed to fetch datatypes for target Galaxy.")
        datatypes = index_response.json()
        assert isinstance(datatypes, list)
        return extension in datatypes

    def method_wrapper(method):
        @wraps(method)
        def wrapped_method(api_test_case, *args, **kwargs):
            _raise_skip_if(not has_datatype(api_test_case))
            method(api_test_case, *args, **kwargs)

        return wrapped_method

    return method_wrapper


def skip_without_visualization_plugin(plugin_name: str):
    def has_plugin(api_test_case: HasAnonymousGalaxyInteractor):
        interactor = api_test_case.anonymous_galaxy_interactor
        index_response = interactor.get("plugins", anon=True)
        api_asserts.assert_status_code_is_ok(index_response, "Failed to fetch visualizations for target Galaxy.")
        plugins = index_response.json()
        assert isinstance(plugins, list)
        return plugin_name in [p["name"] for p in plugins]

    def method_wrapper(method):
        @wraps(method)
        def wrapped_method(api_test_case, *args, **kwargs):
            _raise_skip_if(not has_plugin(api_test_case))
            method(api_test_case, *args, **kwargs)

        return wrapped_method

    return method_wrapper


skip_if_toolshed_down = skip_if_site_down("https://toolshed.g2.bx.psu.edu")


def summarize_instance_history_on_error(method):
    @wraps(method)
    def wrapped_method(api_test_case, *args, **kwds):
        try:
            method(api_test_case, *args, **kwds)
        except Exception:
            api_test_case.dataset_populator._summarize_history(api_test_case.history_id)
            raise

    return wrapped_method


def _raise_skip_if(check, *args):
    if check:
        raise unittest.SkipTest(*args)


def check_missing_tool(check):
    if check:
        if REQUIRE_ALL_NEEDED_TOOLS:
            raise AssertionError("Test requires a missing tool and GALAXY_TEST_REQUIRE_ALL_NEEDED_TOOLS is enabled")
        else:
            raise unittest.SkipTest(
                "Missing tool required to run test, skipping. If this is not intended, ensure GALAXY_TEST_TOOL_CONF if set contains the required tool_conf.xml target and the tool properly parses and loads in Galaxy's test configuration"
            )


def conformance_tests_gen(directory, filename="conformance_tests.yaml"):
    conformance_tests_path = os.path.join(directory, filename)
    with open(conformance_tests_path) as f:
        conformance_tests = yaml.safe_load(f)

    for conformance_test in conformance_tests:
        if "$import" in conformance_test:
            import_dir, import_filename = os.path.split(conformance_test["$import"])
            yield from conformance_tests_gen(os.path.join(directory, import_dir), import_filename)
        else:
            conformance_test["directory"] = directory
            yield conformance_test


class CwlRun:
    def __init__(self, dataset_populator, history_id):
        self.dataset_populator = dataset_populator
        self.history_id = history_id

    @abstractmethod
    def _output_name_to_object(self, output_name) -> GalaxyOutput:
        """
        Convert the name of a run output to a GalaxyOutput object.
        """

    def get_output_as_object(self, output_name, download_folder=None):
        galaxy_output = self._output_name_to_object(output_name)

        def get_metadata(history_content_type, content_id):
            if history_content_type == "raw_value":
                return {}
            elif history_content_type == "dataset":
                return self.dataset_populator.get_history_dataset_details(self.history_id, dataset_id=content_id)
            else:
                assert history_content_type == "dataset_collection"
                # Don't wait - we've already done that, history might be "new"
                return self.dataset_populator.get_history_collection_details(
                    self.history_id, content_id=content_id, wait=False
                )

        def get_dataset(dataset_details, filename=None):
            content = self.dataset_populator.get_history_dataset_content(
                self.history_id, dataset_id=dataset_details["id"], type="content", filename=filename
            )
            if filename is None:
                basename = dataset_details.get("created_from_basename")
                if not basename:
                    basename = dataset_details.get("name")
            else:
                basename = os.path.basename(filename)
            return {"content": content, "basename": basename}

        def get_extra_files(dataset_details):
            return self.dataset_populator.get_history_dataset_extra_files(
                self.history_id, dataset_id=dataset_details["id"]
            )

        output = output_to_cwl_json(
            galaxy_output,
            get_metadata,
            get_dataset,
            get_extra_files,
            pseudo_location=True,
        )
        if download_folder:
            if isinstance(output, dict) and "basename" in output:
                download_path = os.path.join(download_folder, output["basename"])
                download_output(galaxy_output, get_metadata, get_dataset, get_extra_files, download_path)
                output["path"] = download_path
                output["location"] = f"file://{download_path}"
        return output

    @abstractmethod
    def wait(self):
        """
        Wait for the completion of the job(s) generated by this run.
        """


class CwlToolRun(CwlRun):
    def __init__(self, dataset_populator, history_id, run_response):
        super().__init__(dataset_populator, history_id)
        self.run_response = run_response

    @property
    def job_id(self):
        return self.run_response.json()["jobs"][0]["id"]

    def _output_name_to_object(self, output_name):
        return tool_response_to_output(self.run_response.json(), self.history_id, output_name)

    def wait(self):
        self.dataset_populator.wait_for_job(self.job_id, assert_ok=True)


class CwlWorkflowRun(CwlRun):
    def __init__(self, dataset_populator, workflow_populator, history_id, workflow_id, invocation_id):
        super().__init__(dataset_populator, history_id)
        self.workflow_populator = workflow_populator
        self.workflow_id = workflow_id
        self.invocation_id = invocation_id

    def _output_name_to_object(self, output_name):
        invocation_response = self.dataset_populator._get(f"invocations/{self.invocation_id}")
        api_asserts.assert_status_code_is(invocation_response, 200)
        invocation = invocation_response.json()
        return invocation_to_output(invocation, self.history_id, output_name)

    def wait(self):
        self.workflow_populator.wait_for_invocation_and_jobs(self.history_id, self.workflow_id, self.invocation_id)


class BasePopulator(metaclass=ABCMeta):
    galaxy_interactor: ApiTestInteractor

    @abstractmethod
    def _post(
        self, route, data=None, files=None, headers=None, admin=False, json: bool = False, anon: bool = False
    ) -> Response:
        """POST data to target Galaxy instance on specified route."""

    @abstractmethod
    def _put(self, route, data=None, headers=None, admin=False, json: bool = False) -> Response:
        """PUT data to target Galaxy instance on specified route."""

    @abstractmethod
    def _get(self, route, data=None, headers=None, admin=False) -> Response:
        """GET data from target Galaxy instance on specified route."""

    @abstractmethod
    def _delete(self, route, data=None, headers=None, admin=False, json: bool = False) -> Response:
        """DELETE against target Galaxy instance on specified route."""

    def _get_to_tempfile(self, route, suffix=None, **kwd) -> str:
        """Perform a _get and store the result in a tempfile."""
        get_response = self._get(route, **kwd)
        get_response.raise_for_status()
        temp_file = tempfile.NamedTemporaryFile("wb", delete=False, suffix=suffix)
        temp_file.write(get_response.content)
        temp_file.flush()
        return temp_file.name


class BaseDatasetPopulator(BasePopulator):
    """Abstract description of API operations optimized for testing
    Galaxy - implementations must implement _get, _post and _delete.
    """

    def new_dataset(
        self,
        history_id: str,
        content=None,
        wait: bool = False,
        fetch_data=True,
        to_posix_lines=True,
        auto_decompress=True,
        **kwds,
    ) -> Dict[str, Any]:
        """Create a new history dataset instance (HDA).

        :returns: a dictionary describing the new HDA
        """
        run_response = self.new_dataset_request(
            history_id,
            content=content,
            wait=wait,
            fetch_data=fetch_data,
            to_posix_lines=to_posix_lines,
            auto_decompress=auto_decompress,
            **kwds,
        )
        assert run_response.status_code == 200, f"Failed to create new dataset with response: {run_response.text}"
        if fetch_data and wait:
            return self.get_history_dataset_details_raw(
                history_id=history_id, dataset_id=run_response.json()["outputs"][0]["id"]
            ).json()
        return run_response.json()["outputs"][0]

    def new_dataset_request(
        self, history_id: str, content=None, wait: bool = False, fetch_data=True, **kwds
    ) -> Response:
        """Lower-level dataset creation that returns the upload tool response object."""
        if content is None and "ftp_files" not in kwds:
            content = "TestData123"
        if not fetch_data:
            payload = self.upload_payload(history_id, content=content, **kwds)
            run_response = self.tools_post(payload)
        else:
            payload = self.fetch_payload(history_id, content=content, **kwds)
            fetch_kwds = dict(wait=wait)
            if "assert_ok" in kwds:
                fetch_kwds["assert_ok"] = kwds["assert_ok"]
            run_response = self.fetch(payload, **fetch_kwds)
        if wait:
            self.wait_for_tool_run(history_id, run_response, assert_ok=kwds.get("assert_ok", True))
        return run_response

    def new_bam_dataset(self, history_id: str, test_data_resolver):
        return self.new_dataset(
            history_id, content=open(test_data_resolver.get_filename("1.bam"), "rb"), file_type="bam", wait=True
        )

    def new_directory_dataset(
        self, test_data_resolver: TestDataResolver, history_id: str, directory: str, format: str = "directory"
    ):
        directory_path = test_data_resolver.get_filename(directory)
        assert os.path.isdir(directory_path)

        tmp = tempfile.NamedTemporaryFile(delete=False)
        tf = tarfile.open(fileobj=tmp, mode="w:")
        tf.add(directory_path, ".")
        tf.close()

        with open(tmp.name, "rb") as tar_f:
            destination = {"type": "hdas"}
            targets = [
                {
                    "destination": destination,
                    "items": [
                        {
                            "src": "pasted",
                            "paste_content": "",
                            "ext": format,
                            "extra_files": {
                                "items_from": "archive",
                                "src": "files",
                                # Prevent Galaxy from checking for a single file in
                                # a directory and re-interpreting the archive
                                "fuzzy_root": False,
                            },
                        }
                    ],
                }
            ]
            payload = {"history_id": history_id, "targets": targets, "__files": {"files_0|file_data": tar_f}}
            fetch_response = self.fetch(payload)
        assert fetch_response.status_code == 200, fetch_response.content
        outputs = fetch_response.json()["outputs"]
        assert len(outputs) == 1
        return outputs[0]

    def fetch(
        self,
        payload: dict,
        assert_ok: bool = True,
        timeout: timeout_type = DEFAULT_TIMEOUT,
        wait: Optional[bool] = None,
    ):
        tool_response = self._post("tools/fetch", data=payload, json=True)
        if wait is None:
            wait = assert_ok
        if wait:
            job = self.check_run(tool_response)
            self.wait_for_job(job["id"], timeout=timeout)
            if assert_ok:
                job = tool_response.json()["jobs"][0]
                details = self.get_job_details(job["id"]).json()
                assert details["state"] == "ok", details

        return tool_response

    def fetch_hdas(self, history_id: str, items: List[Dict[str, Any]], wait: bool = True) -> List[Dict[str, Any]]:
        destination = {"type": "hdas"}
        targets = [
            {
                "destination": destination,
                "items": items,
            }
        ]
        payload = {
            "history_id": history_id,
            "targets": targets,
        }
        fetch_response = self.fetch(payload, wait=wait)
        api_asserts.assert_status_code_is(fetch_response, 200)
        outputs = fetch_response.json()["outputs"]
        return outputs

    def fetch_hda(self, history_id: str, item: Dict[str, Any], wait: bool = True) -> Dict[str, Any]:
        hdas = self.fetch_hdas(history_id, [item], wait=wait)
        assert len(hdas) == 1
        return hdas[0]

    def create_deferred_hda(self, history_id, uri: str, ext: Optional[str] = None) -> Dict[str, Any]:
        item = {
            "src": "url",
            "url": uri,
            "deferred": True,
        }
        if ext:
            item["ext"] = ext
        output = self.fetch_hda(history_id, item)
        details = self.get_history_dataset_details(history_id, dataset=output)
        return details

    def export_dataset_to_remote_file(self, history_id: str, content: str, name: str, target_uri: str):
        dataset = self.new_dataset(history_id, content=content, wait=True, name=name)
        infile = {"src": "hda", "id": dataset["id"]}
        inputs = {
            "d_uri": target_uri,
            "export_type|export_type_selector": "datasets_named",
            "export_type|datasets_0|infile": infile,
            "export_type|datasets_0|name": name,
        }
        response = self.run_tool("export_remote", inputs, history_id)
        self.wait_for_job(response["jobs"][0]["id"], assert_ok=True)
        return f"{target_uri}/{name}"

    def tag_dataset(self, history_id, hda_id, tags, raise_on_error=True):
        url = f"histories/{history_id}/contents/{hda_id}"
        response = self._put(url, {"tags": tags}, json=True)
        if raise_on_error:
            response.raise_for_status()
        return response.json()

    def create_from_store_raw(self, payload: Dict[str, Any]) -> Response:
        create_response = self._post("histories/from_store", payload, json=True)
        return create_response

    def create_from_store_raw_async(self, payload: Dict[str, Any]) -> Response:
        create_response = self._post("histories/from_store_async", payload, json=True)
        return create_response

    def create_from_store(
        self,
        store_dict: Optional[Dict[str, Any]] = None,
        store_path: Optional[str] = None,
        model_store_format: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload = _store_payload(store_dict=store_dict, store_path=store_path, model_store_format=model_store_format)
        create_response = self.create_from_store_raw(payload)
        api_asserts.assert_status_code_is_ok(create_response)
        return create_response.json()

    def create_from_store_async(
        self,
        store_dict: Optional[Dict[str, Any]] = None,
        store_path: Optional[str] = None,
        model_store_format: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload = _store_payload(store_dict=store_dict, store_path=store_path, model_store_format=model_store_format)
        create_response = self.create_from_store_raw_async(payload)
        create_response.raise_for_status()
        return create_response.json()

    def create_contents_from_store_raw(self, history_id: str, payload: Dict[str, Any]) -> Response:
        create_response = self._post(f"histories/{history_id}/contents_from_store", payload, json=True)
        return create_response

    def create_contents_from_store(
        self, history_id: str, store_dict: Optional[Dict[str, Any]] = None, store_path: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        if store_dict is not None:
            assert isinstance(store_dict, dict)
        if store_path is not None:
            assert isinstance(store_path, str)
        payload = _store_payload(store_dict=store_dict, store_path=store_path)
        create_response = self.create_contents_from_store_raw(history_id, payload)
        create_response.raise_for_status()
        return create_response.json()

    def download_contents_to_store(self, history_id: str, history_content: Dict[str, Any], extension=".tgz") -> str:
        url = f"histories/{history_id}/contents/{history_content['history_content_type']}s/{history_content['id']}/prepare_store_download"
        download_response = self._post(url, dict(include_files=False, model_store_format=extension), json=True)
        storage_request_id = self.assert_download_request_ok(download_response)
        self.wait_for_download_ready(storage_request_id)
        return self._get_to_tempfile(f"short_term_storage/{storage_request_id}")

    def reupload_contents(self, history_content: Dict[str, Any]):
        history_id = history_content["history_id"]
        temp_tar = self.download_contents_to_store(history_id, history_content, "tgz")
        with tarfile.open(name=temp_tar) as tf:
            assert "datasets_attrs.txt" in tf.getnames()
        new_history_id = self.new_history()
        as_list = self.create_contents_from_store(
            new_history_id,
            store_path=temp_tar,
        )
        return new_history_id, as_list

    def wait_for_tool_run(
        self,
        history_id: str,
        run_response: Response,
        timeout: timeout_type = DEFAULT_TIMEOUT,
        assert_ok: bool = True,
    ):
        job = self.check_run(run_response)
        self.wait_for_job(job["id"], timeout=timeout)
        self.wait_for_history(history_id, assert_ok=assert_ok, timeout=timeout)
        return run_response

    def check_run(self, run_response: Response) -> dict:
        run = None
        try:
            run = run_response.json()
            run_response.raise_for_status()
        except Exception:
            if run and run["err_msg"]:
                raise Exception(run["err_msg"])
            raise
        job = run["jobs"][0]
        return job

    def wait_for_history(
        self, history_id: str, assert_ok: bool = False, timeout: timeout_type = DEFAULT_TIMEOUT
    ) -> str:
        try:
            return wait_on_state(
                lambda: self._get(f"histories/{history_id}"), desc="history state", assert_ok=assert_ok, timeout=timeout
            )
        except AssertionError:
            self._summarize_history(history_id)
            raise

    def wait_for_history_jobs(self, history_id: str, assert_ok: bool = False, timeout: timeout_type = DEFAULT_TIMEOUT):
        def has_active_jobs():
            active_jobs = self.active_history_jobs(history_id)
            if len(active_jobs) == 0:
                return True
            else:
                return None

        try:
            wait_on(has_active_jobs, "active jobs", timeout=timeout)
        except TimeoutAssertionError as e:
            jobs = self.history_jobs(history_id)
            message = f"Failed waiting on active jobs to complete, current jobs are [{jobs}]. {e}"
            raise TimeoutAssertionError(message)

        if assert_ok:
            for job in self.history_jobs(history_id=history_id):
                assert job["state"] in ("ok", "skipped"), f"Job {job} not in expected state"

    def wait_for_jobs(
        self,
        jobs: Union[List[dict], List[str]],
        assert_ok: bool = False,
        timeout: timeout_type = DEFAULT_TIMEOUT,
        ok_states=None,
    ):
        for job in jobs:
            if isinstance(job, dict):
                job_id = job["id"]
            else:
                job_id = job
            self.wait_for_job(job_id, assert_ok=assert_ok, timeout=timeout, ok_states=ok_states)

    def wait_for_job(
        self, job_id: str, assert_ok: bool = False, timeout: timeout_type = DEFAULT_TIMEOUT, ok_states=None
    ):
        return wait_on_state(
            lambda: self.get_job_details(job_id, full=True),
            desc="job state",
            assert_ok=assert_ok,
            timeout=timeout,
            ok_states=ok_states,
        )

    def get_job_details(self, job_id: str, full: bool = False) -> Response:
        return self._get(f"jobs/{job_id}", {"full": full})

    def job_outputs(self, job_id: str) -> List[Dict[str, Any]]:
        outputs = self._get(f"jobs/{job_id}/outputs")
        outputs.raise_for_status()
        return outputs.json()

    def compute_hash(
        self,
        dataset_id: str,
        hash_function: Optional[str] = "MD5",
        extra_files_path: Optional[str] = None,
        wait: bool = True,
    ) -> Response:
        data: Dict[str, Any] = {}
        if hash_function:
            data["hash_function"] = hash_function
        if extra_files_path:
            data["extra_files_path"] = extra_files_path
        put_response = self._put(f"datasets/{dataset_id}/hash", data, json=True)
        api_asserts.assert_status_code_is_ok(put_response)
        if wait:
            self.wait_on_task(put_response)
        return put_response

    def cancel_history_jobs(self, history_id: str, wait=True) -> None:
        active_jobs = self.active_history_jobs(history_id)
        for active_job in active_jobs:
            self.cancel_job(active_job["id"])

    def history_jobs(self, history_id: str) -> List[Dict[str, Any]]:
        query_params = {"history_id": history_id, "order_by": "create_time"}
        jobs_response = self._get("jobs", query_params)
        assert jobs_response.status_code == 200
        return jobs_response.json()

    def history_jobs_for_tool(self, history_id: str, tool_id: str) -> List[Dict[str, Any]]:
        jobs = self.history_jobs(history_id)
        return [j for j in jobs if j["tool_id"] == tool_id]

    def invocation_jobs(self, invocation_id: str) -> List[Dict[str, Any]]:
        query_params = {"invocation_id": invocation_id, "order_by": "create_time"}
        jobs_response = self._get("jobs", query_params)
        assert jobs_response.status_code == 200
        return jobs_response.json()

    def active_history_jobs(self, history_id: str) -> list:
        all_history_jobs = self.history_jobs(history_id)
        active_jobs = [
            j for j in all_history_jobs if j["state"] in ["new", "upload", "waiting", "queued", "running", "deleting"]
        ]
        return active_jobs

    def cancel_job(self, job_id: str) -> Response:
        return self._delete(f"jobs/{job_id}")

    def delete_history(self, history_id: str) -> None:
        delete_response = self._delete(f"histories/{history_id}")
        delete_response.raise_for_status()

    def delete_dataset(
        self,
        history_id: str,
        content_id: str,
        purge: bool = False,
        stop_job: bool = False,
        wait_for_purge: bool = False,
        use_query_params: bool = False,
    ) -> Response:
        dataset_url = f"histories/{history_id}/contents/{content_id}"
        if use_query_params:
            delete_response = self._delete(f"{dataset_url}?purge={purge}&stop_job={stop_job}")
        else:
            delete_response = self._delete(dataset_url, {"purge": purge, "stop_job": stop_job}, json=True)
        delete_response.raise_for_status()
        if wait_for_purge and delete_response.status_code == 202:
            return self.wait_for_purge(history_id, content_id)
        return delete_response

    def wait_for_purge(self, history_id, content_id):
        dataset_url = f"histories/{history_id}/contents/{content_id}"

        def _wait_for_purge():
            dataset_response = self._get(dataset_url)
            dataset_response.raise_for_status()
            dataset = dataset_response.json()
            return dataset.get("purged") or None

        wait_on(_wait_for_purge, "dataset to become purged", timeout=2)
        return self._get(dataset_url)

    def create_tool_landing(self, payload: CreateToolLandingRequestPayload) -> ToolLandingRequest:
        create_url = "tool_landings"
        json = payload.model_dump(mode="json")
        create_response = self._post(create_url, json, json=True, anon=True)
        api_asserts.assert_status_code_is(create_response, 200)
        create_response.raise_for_status()
        return ToolLandingRequest.model_validate(create_response.json())

    def create_workflow_landing(self, payload: CreateWorkflowLandingRequestPayload) -> WorkflowLandingRequest:
        create_url = "workflow_landings"
        json = payload.model_dump(mode="json")
        create_response = self._post(create_url, json, json=True, anon=True)
        api_asserts.assert_status_code_is(create_response, 200)
        assert create_response.headers["access-control-allow-origin"]
        create_response.raise_for_status()
        return WorkflowLandingRequest.model_validate(create_response.json())

    def claim_tool_landing(self, uuid: UUID4) -> ToolLandingRequest:
        url = f"tool_landings/{uuid}/claim"
        claim_response = self._post(url, {"client_secret": "foobar"}, json=True)
        api_asserts.assert_status_code_is(claim_response, 200)
        return ToolLandingRequest.model_validate(claim_response.json())

    def claim_workflow_landing(self, uuid: UUID4) -> WorkflowLandingRequest:
        url = f"workflow_landings/{uuid}/claim"
        claim_response = self._post(url, {"client_secret": "foobar"}, json=True)
        api_asserts.assert_status_code_is(claim_response, 200)
        return WorkflowLandingRequest.model_validate(claim_response.json())

    def use_workflow_landing(self, uuid: UUID4) -> WorkflowLandingRequest:
        url = f"workflow_landings/{uuid}"
        landing_reponse = self._get(url, {"client_secret": "foobar"})
        api_asserts.assert_status_code_is(landing_reponse, 200)
        return WorkflowLandingRequest.model_validate(landing_reponse.json())

    def create_tool_from_path(self, tool_path: str) -> Dict[str, Any]:
        tool_directory = os.path.dirname(os.path.abspath(tool_path))
        payload = dict(
            src="from_path",
            path=tool_path,
            tool_directory=tool_directory,
        )
        return self._create_tool_raw(payload)

    def create_tool(self, representation, tool_directory: Optional[str] = None) -> Dict[str, Any]:
        if isinstance(representation, dict):
            representation = json.dumps(representation)
        payload = dict(
            representation=representation,
            tool_directory=tool_directory,
        )
        return self._create_tool_raw(payload)

    def _create_tool_raw(self, payload) -> Dict[str, Any]:
        using_requirement("admin")
        try:
            create_response = self._post("dynamic_tools", data=payload, admin=True)
        except TypeError:
            create_response = self._post("dynamic_tools", data=payload)
        assert create_response.status_code == 200, create_response.text
        return create_response.json()

    def list_dynamic_tools(self) -> list:
        using_requirement("admin")
        list_response = self._get("dynamic_tools", admin=True)
        assert list_response.status_code == 200, list_response
        return list_response.json()

    def show_dynamic_tool(self, uuid) -> dict:
        using_requirement("admin")
        show_response = self._get(f"dynamic_tools/{uuid}", admin=True)
        assert show_response.status_code == 200, show_response
        return show_response.json()

    def deactivate_dynamic_tool(self, uuid) -> dict:
        using_requirement("admin")
        delete_response = self._delete(f"dynamic_tools/{uuid}", admin=True)
        return delete_response.json()

    @abstractmethod
    def _summarize_history(self, history_id: str) -> None:
        """Abstract method for summarizing a target history - override to provide details."""

    def _cleanup_history(self, history_id: str) -> None:
        self.cancel_history_jobs(history_id)

    @contextlib.contextmanager
    def test_history_for(self, method) -> Generator[str, None, None]:
        require_new_history = has_requirement(method, "new_history")
        name = f"API Test History for {method.__name__}"
        with self.test_history(require_new=require_new_history, name=name) as history_id:
            yield history_id

    @contextlib.contextmanager
    def test_history(self, require_new: bool = True, name: Optional[str] = None) -> Generator[str, None, None]:
        with self._test_history(require_new=require_new, cleanup_callback=self._cleanup_history) as history_id:
            yield history_id

    @contextlib.contextmanager
    def _test_history(
        self,
        require_new: bool = True,
        cleanup_callback: Optional[Callable[[str], None]] = None,
        name: Optional[str] = None,
    ) -> Generator[str, None, None]:
        if name is not None:
            kwds = {"name": name}
        else:
            kwds = {}
        history_id = self.new_history(**kwds)
        try:
            yield history_id
        except Exception:
            cleanup_callback and cleanup_callback(history_id)

    def new_history(self, name="API Test History", **kwds) -> str:
        create_history_response = self._post("histories", data=dict(name=name))
        assert "id" in create_history_response.json(), create_history_response.text
        history_id = create_history_response.json()["id"]
        return history_id

    def copy_history(self, history_id, name="API Test Copied History", **kwds) -> Response:
        return self._post("histories", data={"name": name, "history_id": history_id, **kwds})

    def fetch_payload(
        self,
        history_id: str,
        content: str,
        auto_decompress: bool = False,
        file_type: str = "txt",
        dbkey: str = "?",
        name: str = "Test_Dataset",
        **kwds,
    ) -> dict:
        __files = {}
        element = {
            "ext": file_type,
            "dbkey": dbkey,
            "name": name,
            "auto_decompress": auto_decompress,
        }
        for arg in ["to_posix_lines", "space_to_tab"]:
            val = kwds.get(arg)
            if val:
                element[arg] = val
        target = {
            "destination": {"type": "hdas"},
            "elements": [element],
        }
        if "ftp_files" in kwds:
            element["src"] = "ftp_import"
            element["ftp_path"] = kwds["ftp_files"]
        elif hasattr(content, "read"):
            element["src"] = "files"
            __files["files_0|file_data"] = content
        elif content and "://" in content:
            element["src"] = "url"
            element["url"] = content
        else:
            element["src"] = "pasted"
            element["paste_content"] = content
        targets = [target]
        payload = {"history_id": history_id, "targets": targets, "__files": __files}
        return payload

    def upload_payload(self, history_id: str, content: Optional[str] = None, **kwds) -> dict:
        name = kwds.get("name", "Test_Dataset")
        dbkey = kwds.get("dbkey", "?")
        file_type = kwds.get("file_type", "txt")
        upload_params = {
            "files_0|NAME": name,
            "dbkey": dbkey,
            "file_type": file_type,
        }
        if dbkey is None:
            del upload_params["dbkey"]
        if content is None:
            upload_params["files_0|ftp_files"] = kwds.get("ftp_files")
        elif hasattr(content, "read"):
            upload_params["files_0|file_data"] = content
        else:
            upload_params["files_0|url_paste"] = content

        if "to_posix_lines" in kwds:
            upload_params["files_0|to_posix_lines"] = kwds["to_posix_lines"]
        if "space_to_tab" in kwds:
            upload_params["files_0|space_to_tab"] = kwds["space_to_tab"]
        if "auto_decompress" in kwds:
            upload_params["files_0|auto_decompress"] = kwds["auto_decompress"]
        upload_params.update(kwds.get("extra_inputs", {}))
        return self.run_tool_payload(
            tool_id="upload1", inputs=upload_params, history_id=history_id, upload_type="upload_dataset"
        )

    def get_remote_files(self, target: str = "ftp") -> dict:
        response = self._get("remote_files", data={"target": target})
        response.raise_for_status()
        return response.json()

    def run_tool_payload(self, tool_id: Optional[str], inputs: dict, history_id: str, **kwds) -> dict:
        # Remove files_%d|file_data parameters from inputs dict and attach
        # as __files dictionary.
        for key, value in list(inputs.items()):
            if key.startswith("files_") and key.endswith("|file_data"):
                if "__files" not in kwds:
                    kwds["__files"] = {}
                kwds["__files"][key] = value
                del inputs[key]

        return dict(tool_id=tool_id, inputs=json.dumps(inputs), history_id=history_id, **kwds)

    def build_tool_state(self, tool_id: str, history_id: str):
        response = self._post(f"tools/{tool_id}/build?history_id={history_id}")
        response.raise_for_status()
        return response.json()

    def run_tool_raw(self, tool_id: Optional[str], inputs: dict, history_id: str, **kwds) -> Response:
        payload = self.run_tool_payload(tool_id, inputs, history_id, **kwds)
        return self.tools_post(payload)

    def run_tool(self, tool_id: str, inputs: dict, history_id: str, **kwds):
        tool_response = self.run_tool_raw(tool_id, inputs, history_id, **kwds)
        api_asserts.assert_status_code_is(tool_response, 200)
        return tool_response.json()

    def tools_post(self, payload: dict, url="tools") -> Response:
        tool_response = self._post(url, data=payload)
        return tool_response

    def describe_tool_execution(self, tool_id: str) -> "DescribeToolExecution":
        return DescribeToolExecution(self, tool_id)

    def materialize_dataset_instance(self, history_id: str, id: str, source: str = "hda"):
        payload: Dict[str, Any]
        if source == "ldda":
            url = f"histories/{history_id}/materialize"
            payload = {
                "source": "ldda",
                "content": id,
            }
        else:
            url = f"histories/{history_id}/contents/datasets/{id}/materialize"
            payload = {}
        create_response = self._post(url, payload, json=True)
        api_asserts.assert_status_code_is_ok(create_response)
        create_response_json = create_response.json()
        assert "id" in create_response_json
        return create_response_json

    def get_history_dataset_content(
        self, history_id: str, wait=True, filename=None, type="text", to_ext=None, raw=False, **kwds
    ):
        dataset_id = self.__history_content_id(history_id, wait=wait, **kwds)
        data = {}
        if filename:
            data["filename"] = filename
        if raw:
            data["raw"] = True
        if to_ext is not None:
            data["to_ext"] = to_ext
        display_response = self._get_contents_request(history_id, f"/{dataset_id}/display", data=data)
        assert display_response.status_code == 200, display_response.text
        if type == "text":
            return display_response.text
        else:
            return display_response.content

    def display_chunk(self, dataset_id: str, offset: int = 0, ck_size: Optional[int] = None) -> Dict[str, Any]:
        # use the dataset display API endpoint with the offset parameter to enable chunking
        # of the target dataset for certain datatypes
        kwds = {
            "offset": offset,
        }
        if ck_size is not None:
            kwds["ck_size"] = ck_size
        display_response = self._get(f"datasets/{dataset_id}/display", kwds)
        api_asserts.assert_status_code_is(display_response, 200)
        print(display_response.content)
        return display_response.json()

    def get_history_dataset_source_transform_actions(self, history_id: str, **kwd) -> Set[str]:
        details = self.get_history_dataset_details(history_id, **kwd)
        if "sources" not in details:
            return set()
        sources = details["sources"]
        assert len(sources) <= 1  # We don't handle this use case yet.
        if len(sources) == 0:
            return set()

        source_0 = sources[0]
        assert "transform" in source_0
        transform = source_0["transform"]
        if transform is None:
            return set()
        assert isinstance(transform, list)
        return {t["action"] for t in transform}

    def get_history_dataset_details(self, history_id: str, keys: Optional[str] = None, **kwds) -> Dict[str, Any]:
        dataset_id = self.__history_content_id(history_id, **kwds)
        details_response = self.get_history_dataset_details_raw(history_id, dataset_id, keys=keys)
        details_response.raise_for_status()
        return details_response.json()

    def get_history_dataset_details_raw(self, history_id: str, dataset_id: str, keys: Optional[str] = None) -> Response:
        data = None
        if keys:
            data = {"keys": keys}
        details_response = self._get_contents_request(history_id, f"/datasets/{dataset_id}", data=data)
        return details_response

    def get_history_dataset_extra_files(self, history_id: str, **kwds) -> list:
        dataset_id = self.__history_content_id(history_id, **kwds)
        details_response = self._get_contents_request(history_id, f"/{dataset_id}/extra_files")
        assert details_response.status_code == 200, details_response.content
        return details_response.json()

    def get_history_collection_details(self, history_id: str, **kwds) -> dict:
        kwds["history_content_type"] = "dataset_collection"
        hdca_id = self.__history_content_id(history_id, **kwds)
        details_response = self._get_contents_request(history_id, f"/dataset_collections/{hdca_id}")
        assert details_response.status_code == 200, details_response.content
        return details_response.json()

    def run_collection_creates_list(self, history_id: str, hdca_id: str) -> Response:
        inputs = {
            "input1": {"src": "hdca", "id": hdca_id},
        }
        self.wait_for_history(history_id, assert_ok=True)
        return self.run_tool("collection_creates_list", inputs, history_id)

    def new_error_dataset(self, history_id: str) -> str:
        payload = self.run_tool_payload(
            tool_id="test_data_source",
            inputs={
                "URL": f"file://{os.path.join(os.getcwd(), 'README.rst')}",
                "URL_method": "get",
                "data_type": "bed",
            },
            history_id=history_id,
        )
        create_response = self._post("tools", data=payload)
        api_asserts.assert_status_code_is(create_response, 200)
        create_object = create_response.json()
        api_asserts.assert_has_keys(create_object, "outputs")
        assert len(create_object["outputs"]) == 1
        output = create_object["outputs"][0]
        self.wait_for_history(history_id, assert_ok=False)
        # wait=False to allow errors
        output_details = self.get_history_dataset_details(history_id, dataset=output, wait=False)
        assert output_details["state"] == "error", output_details
        return output_details["id"]

    def report_job_error_raw(
        self, job_id: str, dataset_id: str, message: str = "", email: Optional[str] = None
    ) -> Response:
        url = f"jobs/{job_id}/error"
        payload = dict(
            dataset_id=dataset_id,
            message=message,
        )
        if email is not None:
            payload["email"] = email
        report_response = self._post(url, data=payload, json=True)
        return report_response

    def report_job_error(
        self, job_id: str, dataset_id: str, message: str = "", email: Optional[str] = None
    ) -> Response:
        report_response = self.report_job_error_raw(job_id, dataset_id, message=message, email=email)
        api_asserts.assert_status_code_is_ok(report_response)
        return report_response.json()

    def run_detect_errors(self, history_id: str, exit_code: int, stdout: str = "", stderr: str = "") -> dict:
        inputs = {
            "stdoutmsg": stdout,
            "stderrmsg": stderr,
            "exit_code": exit_code,
        }
        response = self.run_tool("detect_errors", inputs, history_id)
        self.wait_for_history(history_id, assert_ok=False)
        return response

    def run_exit_code_from_file(self, history_id: str, hdca_id: str) -> dict:
        exit_code_inputs = {
            "input": {"batch": True, "values": [{"src": "hdca", "id": hdca_id}]},
        }
        response = self.run_tool("exit_code_from_file", exit_code_inputs, history_id)
        self.wait_for_history(history_id, assert_ok=False)
        return response

    def __history_content_id(self, history_id: str, wait=True, **kwds) -> str:
        if wait:
            assert_ok = kwds.get("assert_ok", True)
            self.wait_for_history(history_id, assert_ok=assert_ok)
        # kwds should contain a 'dataset' object response, a 'dataset_id' or
        # the last dataset in the history will be fetched.
        if "dataset_id" in kwds:
            history_content_id = kwds["dataset_id"]
        elif "content_id" in kwds:
            history_content_id = kwds["content_id"]
        elif "dataset" in kwds:
            history_content_id = kwds["dataset"]["id"]
        else:
            hid = kwds.get("hid", None)  # If not hid, just grab last dataset
            contents_request = self._get_contents_request(history_id)
            contents_request.raise_for_status()
            history_contents = contents_request.json()
            if hid:
                history_content_id = None
                for history_item in history_contents:
                    if history_item["hid"] == hid:
                        history_content_id = history_item["id"]
                if history_content_id is None:
                    raise Exception(f"Could not find content with HID [{hid}] in [{history_contents}]")
            else:
                # No hid specified - just grab most recent element of correct content type
                if kwds.get("history_content_type"):
                    history_contents = [
                        c for c in history_contents if c["history_content_type"] == kwds["history_content_type"]
                    ]
                history_content_id = history_contents[-1]["id"]
        return history_content_id

    def get_history_contents(self, history_id: str, data=None) -> List[Dict[str, Any]]:
        contents_response = self._get_contents_request(history_id, data=data)
        contents_response.raise_for_status()
        return contents_response.json()

    def _get_contents_request(self, history_id: str, suffix: str = "", data=None) -> Response:
        if data is None:
            data = {}
        url = f"histories/{history_id}/contents"
        if suffix:
            url = f"{url}{suffix}"
        return self._get(url, data=data)

    def ds_entry(self, history_content: dict) -> dict:
        src = "hda"
        if (
            "history_content_type" in history_content
            and history_content["history_content_type"] == "dataset_collection"
        ):
            src = "hdca"
        return dict(src=src, id=history_content["id"])

    def dataset_storage_info(self, dataset_id: str) -> Dict[str, Any]:
        response = self.dataset_storage_info_raw(dataset_id)
        response.raise_for_status()
        return response.json()

    def dataset_storage_info_raw(self, dataset_id: str) -> Response:
        storage_url = f"datasets/{dataset_id}/storage"
        get_storage_response = self._get(storage_url)
        return get_storage_response

    def get_roles(self) -> list:
        using_requirement("admin")
        roles_response = self._get("roles", admin=True)
        assert roles_response.status_code == 200
        return roles_response.json()

    def get_configuration(self, admin=False) -> Dict[str, Any]:
        if admin:
            using_requirement("admin")
        response = self._get("configuration", admin=admin)
        api_asserts.assert_status_code_is_ok(response)
        configuration = response.json()
        return configuration

    def user_email(self) -> str:
        users_response = self._get("users")
        users = users_response.json()
        assert len(users) == 1
        return users[0]["email"]

    def user_id(self) -> str:
        users_response = self._get("users")
        users = users_response.json()
        assert len(users) == 1
        return users[0]["id"]

    def user_private_role_id(self) -> str:
        userid = self.user_id()
        response = self._get(f"users/{userid}/roles", admin=True)
        assert response.status_code == 200
        roles = response.json()
        private_roles = [r for r in roles if r["type"] == PRIVATE_ROLE_TYPE]
        assert len(private_roles) == 1, f"Did not find exactly one private role for user {userid} - {private_roles}"
        role = private_roles[0]
        assert "id" in role, role
        return role["id"]

    def get_usage(self) -> List[Dict[str, Any]]:
        usage_response = self.galaxy_interactor.get("users/current/usage")
        usage_response.raise_for_status()
        return usage_response.json()

    def get_usage_for(self, label: Optional[str]) -> Dict[str, Any]:
        label_as_str = label if label is not None else "__null__"
        usage_response = self.galaxy_interactor.get(f"users/current/usage/{label_as_str}")
        usage_response.raise_for_status()
        return usage_response.json()

    def update_user(self, properties: Dict[str, Any]) -> Dict[str, Any]:
        update_response = self.update_user_raw(properties)
        api_asserts.assert_status_code_is_ok(update_response)
        return update_response.json()

    def set_user_preferred_object_store_id(self, store_id: Optional[str]) -> None:
        user_properties = self.update_user({"preferred_object_store_id": store_id})
        assert user_properties["preferred_object_store_id"] == store_id

    def update_user_raw(self, properties: Dict[str, Any]) -> Response:
        update_response = self.galaxy_interactor.put("users/current", properties, json=True)
        return update_response

    def total_disk_usage(self) -> float:
        response = self._get("users/current")
        response.raise_for_status()
        user_object = response.json()
        assert "total_disk_usage" in user_object
        return user_object["total_disk_usage"]

    def update_object_store_id(self, dataset_id: str, object_store_id: str):
        payload = {"object_store_id": object_store_id}
        url = f"datasets/{dataset_id}/object_store_id"
        update_response = self._put(url, payload, json=True)
        update_response.raise_for_status()
        return update_response

    def create_role(self, user_ids: list, description: Optional[str] = None) -> dict:
        using_requirement("admin")
        payload = {
            "name": self.get_random_name(prefix="testpop"),
            "description": description or "Test Role",
            "user_ids": user_ids,
        }
        role_response = self._post("roles", data=payload, admin=True, json=True)
        assert role_response.status_code == 200
        return role_response.json()

    def create_quota(self, quota_payload: dict) -> dict:
        using_requirement("admin")
        quota_response = self._post("quotas", data=quota_payload, admin=True, json=True)
        api_asserts.assert_status_code_is_ok(quota_response)
        return quota_response.json()

    def get_quotas(self) -> list:
        using_requirement("admin")
        quota_response = self._get("quotas", admin=True)
        api_asserts.assert_status_code_is_ok(quota_response)
        return quota_response.json()

    def make_private(self, history_id: str, dataset_id: str) -> dict:
        using_requirement("admin")
        role_id = self.user_private_role_id()
        # Give manage permission to the user.
        payload = {
            "access": [role_id],
            "manage": [role_id],
        }
        response = self.update_permissions_raw(history_id, dataset_id, payload)
        api_asserts.assert_status_code_is_ok(response)
        return response.json()

    def make_dataset_public_raw(self, history_id: str, dataset_id: str) -> Response:
        role_id = self.user_private_role_id()
        payload = {
            "access": [],
            "manage": [role_id],
        }
        response = self.update_permissions_raw(history_id, dataset_id, payload)
        return response

    def update_permissions_raw(self, history_id: str, dataset_id: str, payload: dict) -> Response:
        url = f"histories/{history_id}/contents/{dataset_id}/permissions"
        update_response = self._put(url, payload, admin=True, json=True)
        return update_response

    def make_public(self, history_id: str) -> dict:
        using_requirement("new_published_objects")
        sharing_response = self._put(f"histories/{history_id}/publish")
        api_asserts.assert_status_code_is_ok(sharing_response)
        assert sharing_response.status_code == 200
        return sharing_response.json()

    def validate_dataset(self, history_id: str, dataset_id: str) -> Dict[str, Any]:
        url = f"histories/{history_id}/contents/{dataset_id}/validate"
        update_response = self._put(url)
        assert update_response.status_code == 200, update_response.content
        return update_response.json()

    def validate_dataset_and_wait(self, history_id, dataset_id) -> Optional[str]:
        self.validate_dataset(history_id, dataset_id)

        def validated():
            metadata = self.get_history_dataset_details(history_id, dataset_id=dataset_id)
            validated_state = metadata["validated_state"]
            if validated_state == UNKNOWN:
                return
            else:
                return validated_state

        return wait_on(validated, "dataset validation")

    def setup_history_for_export_testing(self, history_name):
        using_requirement("new_history")
        history_id = self.new_history(name=history_name)
        hda = self.new_dataset(history_id, content="1 2 3", wait=True)
        tags = ["name:name"]
        response = self.tag_dataset(history_id, hda["id"], tags=tags)
        assert response["tags"] == tags
        deleted_hda = self.new_dataset(history_id, content="1 2 3", wait=True)
        self.delete_dataset(history_id, deleted_hda["id"])
        deleted_details = self.get_history_dataset_details(history_id, id=deleted_hda["id"])
        assert deleted_details["deleted"]
        return history_id

    def prepare_export(self, history_id, data):
        url = f"histories/{history_id}/exports"
        put_response = self._put(url, data, json=True)
        put_response.raise_for_status()

        if put_response.status_code == 202:

            def export_ready_response():
                put_response = self._put(url)
                if put_response.status_code == 202:
                    return None
                return put_response

            put_response = wait_on(export_ready_response, desc="export ready")
            api_asserts.assert_status_code_is(put_response, 200)
            return put_response
        else:
            job_desc = put_response.json()
            assert "job_id" in job_desc
            return self.wait_for_job(job_desc["job_id"])

    def export_url(self, history_id: str, data, check_download: bool = True) -> str:
        put_response = self.prepare_export(history_id, data)
        response = put_response.json()
        api_asserts.assert_has_keys(response, "download_url")
        download_url = urllib.parse.urljoin(self.galaxy_interactor.api_url, response["download_url"].strip("/"))

        if check_download:
            self.get_export_url(download_url)

        return download_url

    def get_export_url(self, export_url) -> Response:
        download_response = self._get(export_url)
        api_asserts.assert_status_code_is(download_response, 200)
        return download_response

    def import_history(self, import_data):
        files = {}
        if archive_file := import_data.pop("archive_file", None):
            files["archive_file"] = archive_file
        import_response = self._post("histories", data=import_data, files=files)
        api_asserts.assert_status_code_is(import_response, 200)
        return import_response.json()["id"]

    def wait_for_history_with_name(self, history_name: str, desc: str) -> Dict[str, Any]:
        def has_history_with_name():
            histories = self.history_names()
            return histories.get(history_name, None)

        target_history = wait_on(has_history_with_name, desc=desc)
        return target_history

    def import_history_and_wait_for_name(self, import_data, history_name):
        import_name = f"imported from archive: {history_name}"
        assert import_name not in self.history_names()

        job_id = self.import_history(import_data)
        self.wait_for_job(job_id, assert_ok=True)

        imported_history = self.wait_for_history_with_name(import_name, "import history")
        imported_history_id = imported_history["id"]
        self.wait_for_history(imported_history_id)
        return imported_history_id

    def history_names(self) -> Dict[str, Dict]:
        return {h["name"]: h for h in self.get_histories()}

    def rename_history(self, history_id: str, new_name: str):
        self.update_history(history_id, {"name": new_name})

    def update_history(self, history_id: str, payload: Dict[str, Any]) -> Response:
        update_url = f"histories/{history_id}"
        put_response = self._put(update_url, payload, json=True)
        return put_response

    def get_histories(self):
        history_index_response = self._get("histories")
        api_asserts.assert_status_code_is(history_index_response, 200)
        return history_index_response.json()

    def wait_on_history_length(self, history_id: str, wait_on_history_length: int):
        def history_has_length():
            history_length = self.history_length(history_id)
            return None if history_length != wait_on_history_length else True

        wait_on(history_has_length, desc="import history population")

    def wait_on_download(self, download_request_response: Response) -> Response:
        storage_request_id = self.assert_download_request_ok(download_request_response)
        return self.wait_on_download_request(storage_request_id)

    def assert_download_request_ok(self, download_request_response: Response) -> UUID:
        """Assert response is valid and okay and extract storage request ID."""
        api_asserts.assert_status_code_is(download_request_response, 200)
        download_async = download_request_response.json()
        assert "storage_request_id" in download_async
        storage_request_id = download_async["storage_request_id"]
        return storage_request_id

    def wait_for_download_ready(self, storage_request_id: UUID):
        def is_ready():
            is_ready_response = self._get(f"short_term_storage/{storage_request_id}/ready")
            is_ready_response.raise_for_status()
            is_ready_bool = is_ready_response.json()
            return True if is_ready_bool else None

        wait_on(is_ready, "waiting for download to become ready")
        assert is_ready()

    def wait_on_task(self, async_task_response: Response):
        task_id = async_task_response.json()["id"]
        return self.wait_on_task_id(task_id)

    def wait_on_task_id(self, task_id: str):
        def state():
            state_response = self._get(f"tasks/{task_id}/state")
            state_response.raise_for_status()
            return state_response.json()

        def is_ready():
            is_complete = state() in ["SUCCESS", "FAILURE"]
            return True if is_complete else None

        wait_on(is_ready, "waiting for task to complete")
        return state() == "SUCCESS"

    def wait_on_download_request(self, storage_request_id: UUID) -> Response:
        self.wait_for_download_ready(storage_request_id)
        download_contents_response = self._get(f"short_term_storage/{storage_request_id}")
        download_contents_response.raise_for_status()
        return download_contents_response

    def history_length(self, history_id):
        contents_response = self._get(f"histories/{history_id}/contents")
        api_asserts.assert_status_code_is(contents_response, 200)
        contents = contents_response.json()
        return len(contents)

    def reimport_history(self, history_id, history_name, wait_on_history_length, export_kwds, task_based=False):
        # Make history public so we can import by url
        self.make_public(history_id)
        if not task_based:
            # Export the history.
            full_download_url = self.export_url(history_id, export_kwds, check_download=True)
        else:
            # Give modern endpoint the legacy endpoint defaults for kwds...
            if "include_files" in export_kwds:
                export_kwds["include_files"] = True
            if "include_hidden" not in export_kwds:
                export_kwds["include_hidden"] = True
            if "include_deleted" not in export_kwds:
                export_kwds["include_hidden"] = False
            prepare_download_response = self._post(
                f"histories/{history_id}/prepare_store_download", export_kwds, json=True
            )
            storage_request_id = self.assert_download_request_ok(prepare_download_response)
            self.wait_for_download_ready(storage_request_id)
            api_key = self.galaxy_interactor.api_key
            full_download_url = urllib.parse.urljoin(
                self.galaxy_interactor.api_url, f"api/short_term_storage/{storage_request_id}?key={api_key}"
            )

        import_data = dict(archive_source=full_download_url, archive_type="url")

        imported_history_id = self.import_history_and_wait_for_name(import_data, history_name)

        if wait_on_history_length:
            self.wait_on_history_length(imported_history_id, wait_on_history_length)

        return imported_history_id

    def get_random_name(self, prefix: Optional[str] = None, suffix: Optional[str] = None, len: int = 10) -> str:
        return random_name(prefix=prefix, suffix=suffix, len=len)

    def wait_for_dataset(
        self, history_id: str, dataset_id: str, assert_ok: bool = False, timeout: timeout_type = DEFAULT_TIMEOUT
    ) -> str:
        return wait_on_state(
            lambda: self._get(f"histories/{history_id}/contents/{dataset_id}"),
            desc="dataset state",
            assert_ok=assert_ok,
            timeout=timeout,
        )

    def create_object_store_raw(self, payload: Dict[str, Any]) -> Response:
        response = self._post(
            "/api/object_store_instances",
            payload,
            json=True,
        )
        return response

    def create_object_store(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        response = self.create_object_store_raw(payload)
        api_asserts.assert_status_code_is_ok(response)
        return response.json()

    def upgrade_object_store_raw(self, id: str, payload: Dict[str, Any]) -> Response:
        response = self._put(
            f"/api/object_store_instances/{id}",
            payload,
            json=True,
        )
        return response

    def upgrade_object_store(self, id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        response = self.upgrade_object_store_raw(id, payload)
        api_asserts.assert_status_code_is_ok(response)
        return response.json()

    # same implementation client side, slightly different types...
    update_object_store_raw = upgrade_object_store_raw
    update_object_store = upgrade_object_store

    def selectable_object_stores(self) -> List[Dict[str, Any]]:
        selectable_object_stores_response = self._get("object_stores?selectable=true")
        selectable_object_stores_response.raise_for_status()
        selectable_object_stores = selectable_object_stores_response.json()
        return selectable_object_stores

    def selectable_object_store_ids(self) -> List[str]:
        selectable_object_stores = self.selectable_object_stores()
        selectable_object_store_ids = [s["object_store_id"] for s in selectable_object_stores]
        return selectable_object_store_ids

    def new_page(
        self, slug: str = "mypage", title: str = "MY PAGE", content_format: str = "html", content: Optional[str] = None
    ) -> Dict[str, Any]:
        page_response = self.new_page_raw(slug=slug, title=title, content_format=content_format, content=content)
        api_asserts.assert_status_code_is(page_response, 200)
        return page_response.json()

    def new_page_raw(
        self, slug: str = "mypage", title: str = "MY PAGE", content_format: str = "html", content: Optional[str] = None
    ) -> Response:
        page_request = self.new_page_payload(slug=slug, title=title, content_format=content_format, content=content)
        page_response = self._post("pages", page_request, json=True)
        return page_response

    def new_page_payload(
        self, slug: str = "mypage", title: str = "MY PAGE", content_format: str = "html", content: Optional[str] = None
    ) -> Dict[str, str]:
        if content is None:
            if content_format == "html":
                content = "<p>Page!</p>"
            else:
                content = "*Page*\n\n"
        request = dict(
            slug=slug,
            title=title,
            content=content,
            content_format=content_format,
        )
        return request

    def export_history_to_uri_async(
        self, history_id: str, target_uri: str, model_store_format: str = "tgz", include_files: bool = True
    ):
        url = f"histories/{history_id}/write_store"
        download_response = self._post(
            url,
            dict(target_uri=target_uri, include_files=include_files, model_store_format=model_store_format),
            json=True,
        )
        api_asserts.assert_status_code_is_ok(download_response)
        task_ok = self.wait_on_task(download_response)
        assert task_ok, f"Task: Writing history to {target_uri} task failed"

    def import_history_from_uri_async(self, target_uri: str, model_store_format: str):
        import_async_response = self.create_from_store_async(
            store_path=target_uri, model_store_format=model_store_format
        )
        task_id = import_async_response["id"]
        task_ok = self.wait_on_task_id(task_id)
        assert task_ok, f"Task: Import history from {target_uri} failed"

    def download_history_to_store(self, history_id: str, extension: str = "tgz", serve_file: bool = False):
        url = f"histories/{history_id}/prepare_store_download"
        download_response = self._post(url, dict(include_files=False, model_store_format=extension), json=True)
        storage_request_id = self.assert_download_request_ok(download_response)
        self.wait_for_download_ready(storage_request_id)
        if serve_file:
            return self._get_to_tempfile(f"short_term_storage/{storage_request_id}")
        else:
            return storage_request_id

    def get_history_export_tasks(self, history_id: str):
        headers = {"accept": "application/vnd.galaxy.task.export+json"}
        response = self._get(f"histories/{history_id}/exports", headers=headers)
        api_asserts.assert_status_code_is_ok(response)
        return response.json()

    def make_page_public(self, page_id: str) -> Dict[str, Any]:
        sharing_response = self._put(f"pages/{page_id}/publish")
        assert sharing_response.status_code == 200
        return sharing_response.json()

    def wait_for_export_task_on_record(self, export_record):
        if export_record["preparing"]:
            assert export_record["task_uuid"]
            self.wait_on_task_id(export_record["task_uuid"])

    def archive_history(
        self, history_id: str, export_record_id: Optional[str] = None, purge_history: Optional[bool] = False
    ) -> Response:
        payload = (
            {
                "archive_export_id": export_record_id,
                "purge_history": purge_history,
            }
            if export_record_id is not None or purge_history is not None
            else None
        )
        archive_response = self._post(f"histories/{history_id}/archive", data=payload, json=True)
        return archive_response

    def restore_archived_history(self, history_id: str, force: Optional[bool] = None) -> Response:
        restore_response = self._put(f"histories/{history_id}/archive/restore{f'?force={force}' if force else ''}")
        return restore_response

    def get_archived_histories(self, query: Optional[str] = None) -> List[Dict[str, Any]]:
        if query:
            query = f"?{query}"
        index_response = self._get(f"histories/archived{query if query else ''}")
        index_response.raise_for_status()
        return index_response.json()


class GalaxyInteractorHttpMixin:
    galaxy_interactor: ApiTestInteractor

    @property
    def _api_key(self):
        return self.galaxy_interactor.api_key

    def _post(
        self, route, data=None, files=None, headers=None, admin=False, json: bool = False, anon: bool = False
    ) -> Response:
        return self.galaxy_interactor.post(route, data, files=files, admin=admin, headers=headers, json=json, anon=anon)

    def _put(self, route, data=None, headers=None, admin=False, json: bool = False):
        return self.galaxy_interactor.put(route, data, headers=headers, admin=admin, json=json)

    def _get(self, route, data=None, headers=None, admin=False):
        if data is None:
            data = {}

        return self.galaxy_interactor.get(route, data=data, headers=headers, admin=admin)

    def _delete(self, route, data=None, headers=None, admin=False, json: bool = False):
        if data is None:
            data = {}

        return self.galaxy_interactor.delete(route, data=data, headers=headers, admin=admin, json=json)


class DatasetPopulator(GalaxyInteractorHttpMixin, BaseDatasetPopulator):
    def __init__(self, galaxy_interactor: ApiTestInteractor) -> None:
        self.galaxy_interactor = galaxy_interactor

    def _summarize_history(self, history_id):
        self.galaxy_interactor._summarize_history(history_id)

    @contextlib.contextmanager
    def _test_history(
        self,
        require_new: bool = True,
        cleanup_callback: Optional[Callable[[str], None]] = None,
        name: Optional[str] = None,
    ) -> Generator[str, None, None]:
        with self.galaxy_interactor.test_history(
            require_new=require_new, cleanup_callback=cleanup_callback
        ) as history_id:
            yield history_id


# Things gxformat2 knows how to upload as workflows
YamlContentT = Union[StrPath, dict]


class BaseWorkflowPopulator(BasePopulator):
    dataset_populator: BaseDatasetPopulator
    dataset_collection_populator: "BaseDatasetCollectionPopulator"

    def load_workflow(self, name: str, content: str = workflow_str, add_pja=False) -> dict:
        workflow = json.loads(content)
        workflow["name"] = name
        if add_pja:
            tool_step = workflow["steps"]["2"]
            tool_step["post_job_actions"]["RenameDatasetActionout_file1"] = dict(
                action_type="RenameDatasetAction",
                output_name="out_file1",
                action_arguments=dict(newname="foo ${replaceme}"),
            )
        return workflow

    def load_random_x2_workflow(self, name: str) -> dict:
        return self.load_workflow(name, content=workflow_random_x2_str)

    def load_workflow_from_resource(self, name: str, filename: Optional[str] = None) -> dict:
        if filename is None:
            filename = f"data/{name}.ga"
        content = resource_string(__package__, filename)
        return self.load_workflow(name, content=content)

    def simple_workflow(self, name: str, **create_kwds) -> str:
        workflow = self.load_workflow(name)
        return self.create_workflow(workflow, **create_kwds)

    def import_workflow_from_path_raw(self, from_path: str, object_id: Optional[str] = None) -> Response:
        data = dict(
            from_path=from_path,
            object_id=object_id,
        )
        import_response = self._post("workflows", data=data)
        return import_response

    def import_workflow_from_path(self, from_path: str, object_id: Optional[str] = None) -> str:
        import_response = self.import_workflow_from_path_raw(from_path, object_id)
        api_asserts.assert_status_code_is(import_response, 200)
        return import_response.json()["id"]

    def create_workflow(self, workflow: Dict[str, Any], **create_kwds) -> str:
        upload_response = self.create_workflow_response(workflow, **create_kwds)
        uploaded_workflow_id = upload_response.json()["id"]
        return uploaded_workflow_id

    def create_workflow_response(self, workflow: Dict[str, Any], **create_kwds) -> Response:
        data = dict(workflow=json.dumps(workflow), **create_kwds)
        upload_response = self._post("workflows/upload", data=data)
        return upload_response

    def upload_yaml_workflow(self, yaml_content: YamlContentT, **kwds) -> str:
        round_trip_conversion = kwds.get("round_trip_format_conversion", False)
        client_convert = kwds.pop("client_convert", not round_trip_conversion)
        kwds["convert"] = client_convert
        workflow = convert_and_import_workflow(yaml_content, galaxy_interface=self, **kwds)
        workflow_id = workflow["id"]
        if round_trip_conversion:
            workflow_yaml_wrapped = self.download_workflow(workflow_id, style="format2_wrapped_yaml")
            assert "yaml_content" in workflow_yaml_wrapped, workflow_yaml_wrapped
            round_trip_converted_content = workflow_yaml_wrapped["yaml_content"]
            workflow_id = self.upload_yaml_workflow(
                round_trip_converted_content, client_convert=False, round_trip_conversion=False
            )

        return workflow_id

    def wait_for_invocation(
        self,
        workflow_id: Optional[str],
        invocation_id: str,
        timeout: timeout_type = DEFAULT_TIMEOUT,
        assert_ok: bool = True,
    ) -> str:
        url = f"invocations/{invocation_id}"

        def workflow_state():
            return self._get(url)

        return wait_on_state(workflow_state, desc="workflow invocation state", timeout=timeout, assert_ok=assert_ok)

    def workflow_invocations(self, workflow_id: str, include_nested_invocations=True) -> List[Dict[str, Any]]:
        response = self._get(f"workflows/{workflow_id}/invocations")
        api_asserts.assert_status_code_is(response, 200)
        return response.json()

    def cancel_invocation(self, invocation_id: str):
        response = self._delete(f"invocations/{invocation_id}")
        api_asserts.assert_status_code_is(response, 200)
        return response.json()

    def history_invocations(self, history_id: str, include_nested_invocations: bool = True) -> List[Dict[str, Any]]:
        history_invocations_response = self._get(
            "invocations", {"history_id": history_id, "include_nested_invocations": include_nested_invocations}
        )
        api_asserts.assert_status_code_is(history_invocations_response, 200)
        return history_invocations_response.json()

    def wait_for_history_workflows(
        self,
        history_id: str,
        assert_ok: bool = True,
        timeout: timeout_type = DEFAULT_TIMEOUT,
        expected_invocation_count: Optional[int] = None,
    ) -> None:
        if expected_invocation_count is not None:

            def invocation_count():
                invocations = self.history_invocations(history_id)
                if len(invocations) == expected_invocation_count:
                    return True
                elif len(invocations) > expected_invocation_count:
                    raise AssertionError("More than the expect number of invocations found in workflow")

            wait_on(invocation_count, f"{expected_invocation_count} history invocations")
        for invocation in self.history_invocations(history_id):
            workflow_id = invocation["workflow_id"]
            invocation_id = invocation["id"]
            self.wait_for_workflow(workflow_id, invocation_id, history_id, timeout=timeout, assert_ok=assert_ok)

    def wait_for_workflow(
        self,
        workflow_id: Optional[str],
        invocation_id: str,
        history_id: str,
        assert_ok: bool = True,
        timeout: timeout_type = DEFAULT_TIMEOUT,
    ) -> None:
        """Wait for a workflow invocation to completely schedule and then history
        to be complete."""
        self.wait_for_invocation(workflow_id, invocation_id, timeout=timeout, assert_ok=assert_ok)
        for step in self.get_invocation(invocation_id)["steps"]:
            if step["subworkflow_invocation_id"]:
                self.wait_for_invocation(None, step["subworkflow_invocation_id"], timeout=timeout, assert_ok=assert_ok)
        self.dataset_populator.wait_for_history_jobs(history_id, assert_ok=assert_ok, timeout=timeout)

    def get_invocation(self, invocation_id, step_details=False):
        r = self._get(f"invocations/{invocation_id}", data={"step_details": step_details})
        r.raise_for_status()
        return r.json()

    def download_invocation_to_store(self, invocation_id, include_files=False, extension="tgz"):
        url = f"invocations/{invocation_id}/prepare_store_download"
        download_response = self._post(url, dict(include_files=include_files, model_store_format=extension), json=True)
        storage_request_id = self.dataset_populator.assert_download_request_ok(download_response)
        self.dataset_populator.wait_for_download_ready(storage_request_id)
        return self._get_to_tempfile(f"short_term_storage/{storage_request_id}")

    def download_invocation_to_uri(self, invocation_id, target_uri, extension="tgz"):
        url = f"invocations/{invocation_id}/write_store"
        download_response = self._post(
            url, dict(target_uri=target_uri, include_files=False, model_store_format=extension), json=True
        )
        api_asserts.assert_status_code_is_ok(download_response)
        task_ok = self.dataset_populator.wait_on_task(download_response)
        assert task_ok, f"waiting on task to write invocation to {target_uri} that failed"

    def create_invocation_from_store_raw(
        self,
        history_id: str,
        store_dict: Optional[Dict[str, Any]] = None,
        store_path: Optional[str] = None,
        model_store_format: Optional[str] = None,
    ) -> Response:
        url = "invocations/from_store"
        payload = _store_payload(store_dict=store_dict, store_path=store_path, model_store_format=model_store_format)
        payload["history_id"] = history_id
        create_response = self._post(url, payload, json=True)
        return create_response

    def create_invocation_from_store(
        self,
        history_id: str,
        store_dict: Optional[Dict[str, Any]] = None,
        store_path: Optional[str] = None,
        model_store_format: Optional[str] = None,
    ) -> Response:
        create_response = self.create_invocation_from_store_raw(
            history_id, store_dict=store_dict, store_path=store_path, model_store_format=model_store_format
        )
        api_asserts.assert_status_code_is_ok(create_response)
        return create_response.json()

    def validate_biocompute_object(
        self, bco, expected_schema_version="https://w3id.org/ieee/ieee-2791-schema/2791object.json"
    ):
        JsonSchemaValidator.validate_using_schema_url(bco, expected_schema_version)

    def get_ro_crate(self, invocation_id, include_files=False):
        crate_response = self.download_invocation_to_store(
            invocation_id=invocation_id, include_files=include_files, extension="rocrate.zip"
        )
        return ROCrate(crate_response)

    def validate_invocation_crate_directory(self, crate_directory):
        # TODO: where can a ro_crate be extracted
        metadata_json_path = crate_directory / "ro-crate-metadata.json"
        with metadata_json_path.open() as f:
            metadata_json = json.load(f)
            assert metadata_json["@context"] == "https://w3id.org/ro/crate/1.1/context"

    def invoke_workflow_raw(self, workflow_id: str, request: dict, assert_ok: bool = False) -> Response:
        url = f"workflows/{workflow_id}/invocations"
        invocation_response = self._post(url, data=request, json=True)
        if assert_ok:
            api_asserts.assert_status_code_is_ok(invocation_response)
        return invocation_response

    def invoke_workflow(
        self,
        workflow_id: str,
        history_id: Optional[str] = None,
        inputs: Optional[dict] = None,
        request: Optional[dict] = None,
        inputs_by: str = "step_index",
    ) -> Response:
        if inputs is None:
            inputs = {}

        if request is None:
            request = {}

        if history_id:
            request["history"] = f"hist_id={history_id}"
        # else history may be in request...

        if inputs:
            request["inputs"] = json.dumps(inputs)
            request["inputs_by"] = inputs_by
        invocation_response = self.invoke_workflow_raw(workflow_id, request)
        return invocation_response

    def invoke_workflow_and_assert_ok(
        self,
        workflow_id: str,
        history_id: Optional[str] = None,
        inputs: Optional[dict] = None,
        request: Optional[dict] = None,
        inputs_by: str = "step_index",
    ) -> str:
        invocation_response = self.invoke_workflow(
            workflow_id, history_id=history_id, inputs=inputs, request=request, inputs_by=inputs_by
        )
        api_asserts.assert_status_code_is(invocation_response, 200)
        invocation_id = invocation_response.json()["id"]
        return invocation_id

    def invoke_workflow_and_wait(
        self,
        workflow_id: str,
        history_id: Optional[str] = None,
        inputs: Optional[dict] = None,
        request: Optional[dict] = None,
        assert_ok: bool = True,
    ) -> Response:
        invoke_return = self.invoke_workflow(workflow_id, history_id=history_id, inputs=inputs, request=request)
        invoke_return.raise_for_status()
        invocation_id = invoke_return.json()["id"]

        if history_id is None and request:
            history_id = request.get("history_id")
        if history_id is None and request:
            history_id = request["history"]
            if history_id.startswith("hist_id="):
                history_id = history_id[len("hist_id=") :]
        assert history_id
        self.wait_for_workflow(workflow_id, invocation_id, history_id, assert_ok=assert_ok)
        return invoke_return

    def workflow_report_json(self, workflow_id: str, invocation_id: str) -> dict:
        response = self._get(f"workflows/{workflow_id}/invocations/{invocation_id}/report")
        api_asserts.assert_status_code_is(response, 200)
        return response.json()

    def workflow_report_pdf(self, workflow_id: str, invocation_id: str) -> Response:
        response = self._get(f"workflows/{workflow_id}/invocations/{invocation_id}/report.pdf")
        api_asserts.assert_status_code_is(response, 200)
        return response

    def download_workflow(
        self, workflow_id: str, style: Optional[str] = None, history_id: Optional[str] = None
    ) -> dict:
        params = {}
        if style is not None:
            params["style"] = style
        if history_id is not None:
            params["history_id"] = history_id
        response = self._get(f"workflows/{workflow_id}/download", data=params)
        api_asserts.assert_status_code_is(response, 200)
        if style != "format2":
            return response.json()
        else:
            return ordered_load(response.text)

    def invocation_to_request(self, invocation_id: str):
        request_response = self._get(f"invocations/{invocation_id}/request")
        api_asserts.assert_status_code_is_ok(request_response)
        return request_response.json()

    def set_tags(self, workflow_id: str, tags: List[str]) -> None:
        update_payload = {"tags": tags}
        response = self.update_workflow(workflow_id, update_payload)
        response.raise_for_status()

    def update_workflow(self, workflow_id: str, workflow_object: dict) -> Response:
        data = dict(workflow=workflow_object)
        raw_url = f"workflows/{workflow_id}"
        put_response = self._put(raw_url, data, json=True)
        return put_response

    def refactor_workflow(
        self, workflow_id: str, actions: list, dry_run: Optional[bool] = None, style: Optional[str] = None
    ) -> Response:
        data: Dict[str, Any] = dict(
            actions=actions,
        )
        if style is not None:
            data["style"] = style
        if dry_run is not None:
            data["dry_run"] = dry_run
        raw_url = f"workflows/{workflow_id}/refactor"
        put_response = self._put(raw_url, data, json=True)
        return put_response

    @contextlib.contextmanager
    def export_for_update(self, workflow_id):
        workflow_object = self.download_workflow(workflow_id)
        yield workflow_object
        put_respose = self.update_workflow(workflow_id, workflow_object)
        put_respose.raise_for_status()

    def run_workflow(
        self,
        has_workflow: YamlContentT,
        test_data: Optional[Union[str, dict]] = None,
        history_id: Optional[str] = None,
        wait: bool = True,
        source_type: Optional[str] = None,
        jobs_descriptions=None,
        expected_response: int = 200,
        assert_ok: bool = True,
        client_convert: Optional[bool] = None,
        extra_invocation_kwds: Optional[Dict[str, Any]] = None,
        round_trip_format_conversion: bool = False,
        invocations: int = 1,
        raw_yaml: bool = False,
    ):
        """High-level wrapper around workflow API, etc. to invoke format 2 workflows."""
        workflow_populator = self
        if client_convert is None:
            client_convert = not round_trip_format_conversion

        workflow_id = workflow_populator.upload_yaml_workflow(
            has_workflow,
            source_type=source_type,
            client_convert=client_convert,
            round_trip_format_conversion=round_trip_format_conversion,
            raw_yaml=raw_yaml,
        )

        if test_data is None:
            if jobs_descriptions is None:
                assert source_type != "path"
                if isinstance(has_workflow, dict):
                    jobs_descriptions = has_workflow
                else:
                    assert isinstance(has_workflow, str)
                    jobs_descriptions = yaml.safe_load(has_workflow)

            test_data_dict = jobs_descriptions.get("test_data", {})
        elif not isinstance(test_data, dict):
            test_data_dict = yaml.safe_load(test_data)
        else:
            test_data_dict = test_data

        parameters = test_data_dict.pop("step_parameters", {})
        replacement_parameters = test_data_dict.pop("replacement_parameters", {})
        if history_id is None:
            history_id = self.dataset_populator.new_history()
        inputs, label_map, has_uploads = load_data_dict(
            history_id, test_data_dict, self.dataset_populator, self.dataset_collection_populator
        )
        workflow_request: Dict[str, Any] = dict(
            history=f"hist_id={history_id}",
            workflow_id=workflow_id,
        )
        workflow_request["inputs"] = json.dumps(label_map)
        workflow_request["inputs_by"] = "name"
        if parameters:
            workflow_request["parameters"] = json.dumps(parameters)
            workflow_request["parameters_normalized"] = True
        if replacement_parameters:
            workflow_request["replacement_params"] = json.dumps(replacement_parameters)
        if extra_invocation_kwds is not None:
            workflow_request.update(extra_invocation_kwds)
        if has_uploads:
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)

        return self._request_to_summary(
            history_id,
            workflow_id,
            workflow_request,
            inputs=inputs,
            wait=wait,
            assert_ok=assert_ok,
            invocations=invocations,
            expected_response=expected_response,
        )

    def rerun(self, run_jobs_summary: "RunJobsSummary", wait: bool = True, assert_ok: bool = True) -> "RunJobsSummary":
        history_id = run_jobs_summary.history_id
        invocation_id = run_jobs_summary.invocation_id
        inputs = run_jobs_summary.inputs
        workflow_request = self.invocation_to_request(invocation_id)
        workflow_id = workflow_request["workflow_id"]
        assert workflow_request["history_id"] == history_id
        assert workflow_request["instance"] is True
        return self._request_to_summary(
            history_id,
            workflow_id,
            workflow_request,
            inputs=inputs,
            wait=wait,
            assert_ok=assert_ok,
            invocations=1,
            expected_response=200,
        )

    def _request_to_summary(
        self,
        history_id: str,
        workflow_id: str,
        workflow_request: Dict[str, Any],
        inputs,
        wait: bool,
        assert_ok: bool,
        invocations: int,
        expected_response: int,
    ):
        workflow_populator = self
        assert invocations > 0

        jobs = []
        for _ in range(invocations):
            invocation_response = workflow_populator.invoke_workflow_raw(workflow_id, workflow_request)
            api_asserts.assert_status_code_is(invocation_response, expected_response)
            invocation = invocation_response.json()
            if expected_response != 200:
                assert not assert_ok
                return invocation
            invocation_id = invocation.get("id")
            if invocation_id:
                # Wait for workflow to become fully scheduled and then for all jobs
                # complete.
                if wait:
                    workflow_populator.wait_for_workflow(workflow_id, invocation_id, history_id, assert_ok=assert_ok)
                jobs.extend(self.dataset_populator.invocation_jobs(invocation_id))

        return RunJobsSummary(
            history_id=history_id,
            workflow_id=workflow_id,
            invocation_id=invocation_id,
            inputs=inputs,
            jobs=jobs,
            invocation=invocation,
            workflow_request=workflow_request,
        )

    def dump_workflow(self, workflow_id, style=None):
        raw_workflow = self.download_workflow(workflow_id, style=style)
        if style == "format2_wrapped_yaml":
            print(raw_workflow["yaml_content"])
        else:
            print(json.dumps(raw_workflow, sort_keys=True, indent=2))

    def workflow_inputs(self, workflow_id: str) -> Dict[str, Dict[str, Any]]:
        workflow_show_response = self._get(f"workflows/{workflow_id}")
        api_asserts.assert_status_code_is_ok(workflow_show_response)
        workflow_inputs = workflow_show_response.json()["inputs"]
        return workflow_inputs

    def build_ds_map(self, workflow_id: str, label_map: Dict[str, Any]) -> str:
        workflow_inputs = self.workflow_inputs(workflow_id)
        ds_map = {}
        for key, value in workflow_inputs.items():
            label = value["label"]
            if label in label_map:
                ds_map[key] = label_map[label]
        return json.dumps(ds_map)

    def setup_workflow_run(
        self,
        workflow: Optional[Dict[str, Any]] = None,
        inputs_by: str = "step_id",
        history_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
    ) -> Tuple[Dict[str, Any], str, str]:
        ds_entry = self.dataset_populator.ds_entry
        if not workflow_id:
            assert workflow, "If workflow_id not specified, must specify a workflow dictionary to load"
            workflow_id = self.create_workflow(workflow)
        if not history_id:
            history_id = self.dataset_populator.new_history()
        hda1: Optional[Dict[str, Any]] = None
        hda2: Optional[Dict[str, Any]] = None
        label_map: Optional[Dict[str, Any]] = None
        if inputs_by != "url":
            hda1 = self.dataset_populator.new_dataset(history_id, content="1 2 3", wait=True)
            hda2 = self.dataset_populator.new_dataset(history_id, content="4 5 6", wait=True)
            label_map = {"WorkflowInput1": ds_entry(hda1), "WorkflowInput2": ds_entry(hda2)}
        workflow_request = dict(
            history=f"hist_id={history_id}",
        )
        if inputs_by == "step_id":
            assert label_map
            ds_map = self.build_ds_map(workflow_id, label_map)
            workflow_request["ds_map"] = ds_map
        elif inputs_by == "step_index":
            assert hda1
            assert hda2
            index_map = {"0": ds_entry(hda1), "1": ds_entry(hda2)}
            workflow_request["inputs"] = json.dumps(index_map)
            workflow_request["inputs_by"] = "step_index"
        elif inputs_by == "name":
            assert label_map
            workflow_request["inputs"] = json.dumps(label_map)
            workflow_request["inputs_by"] = "name"
        elif inputs_by in ["step_uuid", "uuid_implicitly"]:
            assert hda1
            assert hda2
            assert workflow, f"Must specify workflow for this inputs_by {inputs_by} parameter value"
            uuid_map = {
                workflow["steps"]["0"]["uuid"]: ds_entry(hda1),
                workflow["steps"]["1"]["uuid"]: ds_entry(hda2),
            }
            workflow_request["inputs"] = json.dumps(uuid_map)
            if inputs_by == "step_uuid":
                workflow_request["inputs_by"] = "step_uuid"
        elif inputs_by in ["url", "deferred_url"]:
            input_b64_1 = base64.b64encode(b"1 2 3").decode("utf-8")
            input_b64_2 = base64.b64encode(b"4 5 6").decode("utf-8")
            deferred = inputs_by == "deferred_url"
            inputs = {
                "WorkflowInput1": {"src": "url", "url": f"base64://{input_b64_1}", "ext": "txt", "deferred": deferred},
                "WorkflowInput2": {"src": "url", "url": f"base64://{input_b64_2}", "ext": "txt", "deferred": deferred},
            }
            workflow_request["inputs"] = json.dumps(inputs)
            workflow_request["inputs_by"] = "name"

        return workflow_request, history_id, workflow_id

    def get_invocation_jobs(self, invocation_id: str) -> List[Dict[str, Any]]:
        jobs_response = self._get("jobs", data={"invocation_id": invocation_id})
        api_asserts.assert_status_code_is(jobs_response, 200)
        jobs = jobs_response.json()
        assert isinstance(jobs, list)
        return jobs

    def wait_for_invocation_and_jobs(
        self, history_id: str, workflow_id: str, invocation_id: str, assert_ok: bool = True
    ) -> None:
        state = self.wait_for_invocation(workflow_id, invocation_id, assert_ok=assert_ok)
        if assert_ok:
            assert state == "scheduled", state
        time.sleep(0.5)
        self.dataset_populator.wait_for_history_jobs(history_id, assert_ok=assert_ok)
        time.sleep(0.5)

    def index(
        self,
        show_shared: Optional[bool] = None,
        show_published: Optional[bool] = None,
        sort_by: Optional[str] = None,
        sort_desc: Optional[bool] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        search: Optional[str] = None,
        skip_step_counts: Optional[bool] = None,
    ):
        endpoint = "workflows?"
        if show_shared is not None:
            endpoint += f"show_shared={show_shared}&"
        if show_published is not None:
            endpoint += f"show_published={show_published}&"
        if sort_by is not None:
            endpoint += f"sort_by={sort_by}&"
        if sort_desc is not None:
            endpoint += f"sort_desc={sort_desc}&"
        if limit is not None:
            endpoint += f"limit={limit}&"
        if offset is not None:
            endpoint += f"offset={offset}&"
        if search is not None:
            endpoint += f"search={search}&"
        if skip_step_counts is not None:
            endpoint += f"skip_step_counts={skip_step_counts}&"
        response = self._get(endpoint)
        api_asserts.assert_status_code_is_ok(response)
        return response.json()

    def index_ids(
        self,
        show_shared: Optional[bool] = None,
        show_published: Optional[bool] = None,
        sort_by: Optional[str] = None,
        sort_desc: Optional[bool] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        search: Optional[str] = None,
    ):
        workflows = self.index(
            show_shared=show_shared,
            show_published=show_published,
            sort_by=sort_by,
            sort_desc=sort_desc,
            limit=limit,
            offset=offset,
            search=search,
        )
        return [w["id"] for w in workflows]

    def share_with_user(self, workflow_id: str, user_id_or_email: str):
        data = {"user_ids": [user_id_or_email]}
        response = self._put(f"workflows/{workflow_id}/share_with_users", data, json=True)
        api_asserts.assert_status_code_is_ok(response)


class RunJobsSummary(NamedTuple):
    history_id: str
    workflow_id: str
    invocation_id: str
    inputs: dict
    jobs: list
    invocation: dict
    workflow_request: dict

    def jobs_for_tool(self, tool_id):
        return [j for j in self.jobs if j["tool_id"] == tool_id]


class WorkflowPopulator(GalaxyInteractorHttpMixin, BaseWorkflowPopulator, ImporterGalaxyInterface):
    def __init__(self, galaxy_interactor):
        self.galaxy_interactor = galaxy_interactor
        self.dataset_populator = DatasetPopulator(galaxy_interactor)
        self.dataset_collection_populator = DatasetCollectionPopulator(galaxy_interactor)

    # Required for ImporterGalaxyInterface interface - so we can recursively import
    # nested workflows.
    def import_workflow(self, workflow, **kwds) -> Dict[str, Any]:
        workflow_str = json.dumps(workflow, indent=4)
        data = {
            "workflow": workflow_str,
        }
        data.update(**kwds)
        upload_response = self._post("workflows", data=data)
        assert upload_response.status_code == 200, upload_response.content
        return upload_response.json()

    def import_tool(self, tool) -> Dict[str, Any]:
        """Import a workflow via POST /api/workflows or
        comparable interface into Galaxy.
        """
        upload_response = self._import_tool_response(tool)
        assert upload_response.status_code == 200, upload_response
        return upload_response.json()

    def build_module(self, step_type: str, content_id: Optional[str] = None, inputs: Optional[Dict[str, Any]] = None):
        payload = {"inputs": inputs or {}, "type": step_type, "content_id": content_id}
        response = self._post("workflows/build_module", data=payload, json=True)
        assert response.status_code == 200, response
        return response.json()

    def _import_tool_response(self, tool) -> Response:
        using_requirement("admin")
        tool_str = json.dumps(tool, indent=4)
        data = {"representation": tool_str}
        upload_response = self._post("dynamic_tools", data=data, admin=True)
        return upload_response

    def scaling_workflow_yaml(self, **kwd):
        workflow_dict = self._scale_workflow_dict(**kwd)
        has_workflow = yaml.dump(workflow_dict)
        return has_workflow

    def _scale_workflow_dict(self, workflow_type="simple", **kwd) -> Dict[str, Any]:
        if workflow_type == "two_outputs":
            return self._scale_workflow_dict_two_outputs(**kwd)
        elif workflow_type == "wave_simple":
            return self._scale_workflow_dict_wave(**kwd)
        else:
            return self._scale_workflow_dict_simple(**kwd)

    def _scale_workflow_dict_simple(self, **kwd) -> Dict[str, Any]:
        collection_size = kwd.get("collection_size", 2)
        workflow_depth = kwd.get("workflow_depth", 3)

        scale_workflow_steps = [
            {"tool_id": "create_input_collection", "state": {"collection_size": collection_size}, "label": "wf_input"},
            {"tool_id": "cat", "state": {"input1": self._link("wf_input", "output")}, "label": "cat_0"},
        ]

        for i in range(workflow_depth):
            link = f"cat_{str(i)}/out_file1"
            scale_workflow_steps.append(
                {"tool_id": "cat", "state": {"input1": self._link(link)}, "label": f"cat_{str(i + 1)}"}
            )

        workflow_dict = {
            "class": "GalaxyWorkflow",
            "inputs": {},
            "steps": scale_workflow_steps,
        }
        return workflow_dict

    def _scale_workflow_dict_two_outputs(self, **kwd) -> Dict[str, Any]:
        collection_size = kwd.get("collection_size", 10)
        workflow_depth = kwd.get("workflow_depth", 10)

        scale_workflow_steps = [
            {"tool_id": "create_input_collection", "state": {"collection_size": collection_size}, "label": "wf_input"},
            {
                "tool_id": "cat",
                "state": {"input1": self._link("wf_input"), "input2": self._link("wf_input")},
                "label": "cat_0",
            },
        ]

        for i in range(workflow_depth):
            link1 = f"cat_{str(i)}#out_file1"
            link2 = f"cat_{str(i)}#out_file2"
            scale_workflow_steps.append(
                {"tool_id": "cat", "state": {"input1": self._link(link1), "input2": self._link(link2)}}
            )
        workflow_dict = {
            "class": "GalaxyWorkflow",
            "inputs": {},
            "steps": scale_workflow_steps,
        }
        return workflow_dict

    def _scale_workflow_dict_wave(self, **kwd) -> Dict[str, Any]:
        collection_size = kwd.get("collection_size", 10)
        workflow_depth = kwd.get("workflow_depth", 10)

        scale_workflow_steps = [
            {"tool_id": "create_input_collection", "state": {"collection_size": collection_size}, "label": "wf_input"},
            {"tool_id": "cat_list", "state": {"input1": self._link("wf_input", "output")}, "label": "step_1"},
        ]

        for i in range(workflow_depth):
            step = i + 2
            if step % 2 == 1:
                step_dict = {"tool_id": "cat_list", "state": {"input1": self._link(f"step_{step - 1}", "output")}}
            else:
                step_dict = {"tool_id": "split", "state": {"input1": self._link(f"step_{step - 1}", "out_file1")}}
            step_dict["label"] = f"step_{step}"
            scale_workflow_steps.append(step_dict)

        workflow_dict = {
            "class": "GalaxyWorkflow",
            "inputs": {},
            "steps": scale_workflow_steps,
        }
        return workflow_dict

    @staticmethod
    def _link(link: str, output_name: Optional[str] = None) -> Dict[str, Any]:
        if output_name is not None:
            link = f"{str(link)}/{output_name}"
        return {"$link": link}

    def make_public(self, workflow_id: str) -> dict:
        using_requirement("new_published_objects")
        sharing_response = self._put(f"workflows/{workflow_id}/publish")
        api_asserts.assert_status_code_is_ok(sharing_response)
        assert sharing_response.status_code == 200
        return sharing_response.json()


class CwlPopulator:
    def __init__(self, dataset_populator: DatasetPopulator, workflow_populator: WorkflowPopulator):
        self.dataset_populator = dataset_populator
        self.workflow_populator = workflow_populator

    def get_conformance_test(self, version: str, doc: str):
        for test in conformance_tests_gen(os.path.join(CWL_TOOL_DIRECTORY, version)):
            if test.get("doc") == doc:
                return test
        raise Exception(f"doc [{doc}] not found")

    def _run_cwl_tool_job(
        self,
        tool_id: str,
        job: dict,
        history_id: str,
        assert_ok: bool = True,
    ) -> CwlToolRun:
        galaxy_tool_id: Optional[str] = tool_id
        tool_uuid = None

        if os.path.exists(tool_id):
            raw_tool_id = os.path.basename(tool_id)
            index = self.dataset_populator._get("tools", data=dict(in_panel=False))
            index.raise_for_status()
            tools = index.json()
            # In panels by default, so flatten out sections...
            tool_ids = [itemgetter("id")(_) for _ in tools]
            if raw_tool_id in tool_ids:
                galaxy_tool_id = raw_tool_id
            else:
                dynamic_tool = self.dataset_populator.create_tool_from_path(tool_id)
                galaxy_tool_id = None
                tool_uuid = dynamic_tool["uuid"]

        run_response = self.dataset_populator.run_tool_raw(galaxy_tool_id, job, history_id, tool_uuid=tool_uuid)
        if assert_ok:
            run_response.raise_for_status()
        return CwlToolRun(self.dataset_populator, history_id, run_response)

    def _run_cwl_workflow_job(
        self,
        workflow_path: str,
        job: dict,
        history_id: str,
        assert_ok: bool = True,
    ):
        workflow_path, object_id = urllib.parse.urldefrag(workflow_path)
        workflow_id = self.workflow_populator.import_workflow_from_path(workflow_path, object_id)

        request = {
            # TODO: rework tool state corrections so more of these are valid in Galaxy
            # workflows as well, and then make it the default. Or decide they are safe.
            "allow_tool_state_corrections": True,
        }
        invocation_id = self.workflow_populator.invoke_workflow_and_assert_ok(
            workflow_id, history_id=history_id, inputs=job, request=request, inputs_by="name"
        )
        return CwlWorkflowRun(self.dataset_populator, self.workflow_populator, history_id, workflow_id, invocation_id)

    def run_cwl_job(
        self,
        artifact: str,
        job_path: Optional[str] = None,
        job: Optional[Dict] = None,
        test_data_directory: Optional[str] = None,
        history_id: Optional[str] = None,
        assert_ok: bool = True,
    ) -> CwlRun:
        """
        :param artifact: CWL tool id, or (absolute or relative) path to a CWL
          tool or workflow file
        """
        if history_id is None:
            history_id = self.dataset_populator.new_history()
        artifact_without_id = artifact.split("#", 1)[0]
        if os.path.exists(artifact_without_id):
            tool_or_workflow: Literal["tool", "workflow"] = guess_artifact_type(artifact)
        else:
            # Assume it's a tool id
            tool_or_workflow = "tool"
        if job_path and not os.path.exists(job_path):
            raise ValueError(f"job_path [{job_path}] does not exist")
        if test_data_directory is None and job_path is not None:
            test_data_directory = os.path.dirname(job_path)
        if job_path is not None:
            assert job is None
            with open(job_path) as f:
                job = yaml.safe_load(f)
        elif job is None:
            job = {}
        _, datasets = stage_inputs(
            self.dataset_populator.galaxy_interactor,
            history_id,
            job,
            use_fetch_api=False,
            tool_or_workflow=tool_or_workflow,
            job_dir=test_data_directory,
        )
        if datasets:
            self.dataset_populator.wait_for_history(history_id=history_id, assert_ok=True)
        if tool_or_workflow == "tool":
            run_object = self._run_cwl_tool_job(
                artifact,
                job,
                history_id,
                assert_ok=assert_ok,
            )
        else:
            run_object = self._run_cwl_workflow_job(
                artifact,
                job,
                history_id,
                assert_ok=assert_ok,
            )
        if assert_ok:
            try:
                run_object.wait()
            except Exception:
                self.dataset_populator._summarize_history(history_id)
                raise
        return run_object

    def run_conformance_test(self, version: str, doc: str):
        test = self.get_conformance_test(version, doc)
        directory = test["directory"]
        artifact = os.path.join(directory, test["tool"])
        job_path = test.get("job")
        if job_path is not None:
            job_path = os.path.join(directory, job_path)
        should_fail = test.get("should_fail", False)
        try:
            run = self.run_cwl_job(artifact, job_path=job_path)
        except Exception:
            # Should fail so this is good!
            if should_fail:
                return True
            raise

        if should_fail:
            self.dataset_populator._summarize_history(run.history_id)
            raise Exception("Expected run to fail but it didn't.")

        expected_outputs = test["output"]
        for key, value in expected_outputs.items():
            try:
                actual_output = run.get_output_as_object(key)
                cwltest.compare.compare(value, actual_output)
            except Exception:
                self.dataset_populator._summarize_history(run.history_id)
                raise


class LibraryPopulator:
    def __init__(self, galaxy_interactor):
        self.galaxy_interactor = galaxy_interactor
        self.dataset_populator = DatasetPopulator(galaxy_interactor)

    def get_libraries(self):
        get_response = self.galaxy_interactor.get("libraries")
        return get_response.json()

    def new_private_library(self, name):
        library = self.new_library(name)
        library_id = library["id"]

        role_id = self.user_private_role_id()
        self.set_permissions(library_id, role_id)
        return library

    def create_from_store_raw(self, payload: Dict[str, Any]) -> Response:
        using_requirement("admin")
        using_requirement("new_library")
        create_response = self.galaxy_interactor.post("libraries/from_store", payload, json=True, admin=True)
        return create_response

    def create_from_store(
        self, store_dict: Optional[Dict[str, Any]] = None, store_path: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        payload = _store_payload(store_dict=store_dict, store_path=store_path)
        create_response = self.create_from_store_raw(payload)
        api_asserts.assert_status_code_is_ok(create_response)
        return create_response.json()

    def new_library(self, name):
        using_requirement("new_library")
        using_requirement("admin")
        data = dict(name=name)
        create_response = self.galaxy_interactor.post("libraries", data=data, admin=True, json=True)
        return create_response.json()

    def fetch_single_url_to_folder(self, file_type="auto", assert_ok=True):
        history_id, library, destination = self.setup_fetch_to_folder("single_url")
        items = [
            {
                "src": "url",
                "url": FILE_URL,
                "MD5": FILE_MD5,
                "ext": file_type,
            }
        ]
        targets = [
            {
                "destination": destination,
                "items": items,
            }
        ]
        payload = {
            "history_id": history_id,  # TODO: Shouldn't be needed :(
            "targets": targets,
        }
        return library, self.dataset_populator.fetch(payload, assert_ok=assert_ok)

    def get_permissions(
        self,
        library_id,
        scope: Optional[str] = "current",
        is_library_access: Optional[bool] = False,
        page: Optional[int] = 1,
        page_limit: Optional[int] = 1000,
        q: Optional[str] = None,
        admin: Optional[bool] = True,
    ):
        query = f"&q={q}" if q else ""
        response = self.galaxy_interactor.get(
            f"libraries/{library_id}/permissions?scope={scope}&is_library_access={is_library_access}&page={page}&page_limit={page_limit}{query}",
            admin=admin,
        )
        api_asserts.assert_status_code_is(response, 200)
        return response.json()

    def set_permissions(self, library_id, role_id=None):
        """Old legacy way of setting permissions."""
        perm_list = role_id or []
        permissions = {
            "LIBRARY_ACCESS_in": perm_list,
            "LIBRARY_MODIFY_in": perm_list,
            "LIBRARY_ADD_in": perm_list,
            "LIBRARY_MANAGE_in": perm_list,
        }
        self._set_permissions(library_id, permissions)

    def set_permissions_with_action(self, library_id, role_id=None, action=None):
        perm_list = role_id or []
        action = action or "set_permissions"
        permissions = {
            "action": action,
            "access_ids[]": perm_list,
            "add_ids[]": perm_list,
            "manage_ids[]": perm_list,
            "modify_ids[]": perm_list,
        }
        self._set_permissions(library_id, permissions)

    def set_access_permission(self, library_id, role_id, action=None):
        self._set_single_permission(library_id, role_id, permission="access_ids[]", action=action)

    def set_add_permission(self, library_id, role_id, action=None):
        self._set_single_permission(library_id, role_id, permission="add_ids[]", action=action)

    def set_manage_permission(self, library_id, role_id, action=None):
        self._set_single_permission(library_id, role_id, permission="manage_ids[]", action=action)

    def set_modify_permission(self, library_id, role_id, action=None):
        self._set_single_permission(library_id, role_id, permission="modify_ids[]", action=action)

    def _set_single_permission(self, library_id, role_id, permission, action=None):
        action = action or "set_permissions"
        permissions = {
            "action": action,
            permission: role_id or [],
        }
        self._set_permissions(library_id, permissions)

    def _set_permissions(self, library_id, permissions):
        using_requirement("admin")
        response = self.galaxy_interactor.post(
            f"libraries/{library_id}/permissions", data=permissions, admin=True, json=True
        )
        api_asserts.assert_status_code_is(response, 200)

    def user_email(self):
        # deprecated - use DatasetPopulator
        return self.dataset_populator.user_email()

    def user_private_role_id(self):
        # deprecated - use DatasetPopulator
        return self.dataset_populator.user_private_role_id()

    def create_dataset_request(self, library, **kwds):
        upload_option = kwds.get("upload_option", "upload_file")
        create_data = {
            "folder_id": kwds.get("folder_id", library["root_folder_id"]),
            "create_type": "file",
            "files_0|NAME": kwds.get("name", "NewFile"),
            "upload_option": upload_option,
            "file_type": kwds.get("file_type", "auto"),
            "db_key": kwds.get("db_key", "?"),
            "tags": kwds.get("tags", []),
        }
        if kwds.get("link_data"):
            create_data["link_data_only"] = "link_to_files"

        if upload_option == "upload_file":
            files = {
                "files_0|file_data": kwds.get("file", StringIO(kwds.get("contents", "TestData"))),
            }
        elif upload_option == "upload_paths":
            create_data["filesystem_paths"] = kwds["paths"]
            files = {}
        elif upload_option == "upload_directory":
            create_data["server_dir"] = kwds["server_dir"]
            files = {}

        return create_data, files

    def new_library_dataset(self, name, **create_dataset_kwds):
        library = self.new_private_library(name)
        payload, files = self.create_dataset_request(library, **create_dataset_kwds)
        dataset = self.raw_library_contents_create(library["id"], payload, files=files).json()[0]
        return self.wait_on_library_dataset(library["id"], dataset["id"])

    def wait_on_library_dataset(self, library_id, dataset_id):
        def show():
            return self.galaxy_interactor.get(f"libraries/{library_id}/contents/{dataset_id}")

        wait_on_state(show, assert_ok=True)
        return show().json()

    def raw_library_contents_create(self, library_id, payload, files=None):
        url_rel = f"libraries/{library_id}/contents"
        if not files:
            return self.galaxy_interactor.post(url_rel, payload, json=True)
        return self.galaxy_interactor.post(url_rel, payload, files=files)

    def show_ld_raw(self, library_id: str, library_dataset_id: str) -> Response:
        response = self.galaxy_interactor.get(f"libraries/{library_id}/contents/{library_dataset_id}")
        return response

    def show_ld(self, library_id: str, library_dataset_id: str) -> Dict[str, Any]:
        response = self.show_ld_raw(library_id, library_dataset_id)
        response.raise_for_status()
        return response.json()

    def show_ldda(self, ldda_id):
        response = self.galaxy_interactor.get(f"datasets/{ldda_id}?hda_ldda=ldda")
        response.raise_for_status()
        return response.json()

    def new_library_dataset_in_private_library(self, library_name="private_dataset", wait=True):
        library = self.new_private_library(library_name)
        payload, files = self.create_dataset_request(library, file_type="txt", contents="create_test")
        create_response = self.galaxy_interactor.post(f"libraries/{library['id']}/contents", payload, files=files)
        api_asserts.assert_status_code_is(create_response, 200)
        library_datasets = create_response.json()
        assert len(library_datasets) == 1
        library_dataset = library_datasets[0]
        if wait:
            library_dataset = self.wait_on_library_dataset(library["id"], library_dataset["id"])

        return library, library_dataset

    def get_library_contents(self, library_id: str) -> List[Dict[str, Any]]:
        all_contents_response = self.galaxy_interactor.get(f"libraries/{library_id}/contents")
        api_asserts.assert_status_code_is(all_contents_response, 200)
        all_contents = all_contents_response.json()
        return all_contents

    def get_library_contents_with_path(self, library_id: str, path: str) -> Dict[str, Any]:
        all_contents = self.get_library_contents(library_id)
        matching = [c for c in all_contents if c["name"] == path]
        if len(matching) == 0:
            raise Exception(f"Failed to find library contents with path [{path}], contents are {all_contents}")
        get_response = self.galaxy_interactor.get(matching[0]["url"])
        api_asserts.assert_status_code_is(get_response, 200)
        return get_response.json()

    def setup_fetch_to_folder(self, test_name):
        history_id = self.dataset_populator.new_history()
        library = self.new_private_library(test_name)
        folder_id = library["root_folder_id"][1:]
        destination = {"type": "library_folder", "library_folder_id": folder_id}
        return history_id, library, destination


class BaseDatasetCollectionPopulator:
    dataset_populator: BaseDatasetPopulator

    def create_list_from_pairs(self, history_id, pairs, name="Dataset Collection from pairs"):
        return self.create_nested_collection(
            history_id=history_id, collection=pairs, collection_type="list:paired", name=name
        )

    def nested_collection_identifiers(self, history_id: str, collection_type):
        rank_types = list(reversed(collection_type.split(":")))
        assert len(rank_types) > 0
        rank_type_0 = rank_types[0]
        if rank_type_0 == "list":
            identifiers = self.list_identifiers(history_id)
        else:
            identifiers = self.pair_identifiers(history_id)
        nested_collection_type = rank_type_0

        for i, rank_type in enumerate(reversed(rank_types[1:])):
            name = f"test_level_{i + 1}" if rank_type == "list" else "paired"
            identifiers = [
                dict(
                    src="new_collection",
                    name=name,
                    collection_type=nested_collection_type,
                    element_identifiers=identifiers,
                )
            ]
            nested_collection_type = f"{rank_type}:{nested_collection_type}"
        return identifiers

    def create_nested_collection(
        self, history_id, collection_type, name=None, collection=None, element_identifiers=None
    ):
        """Create a nested collection either from collection or using collection_type)."""
        assert collection_type is not None
        name = name or f"Test {collection_type}"
        if collection is not None:
            assert element_identifiers is None
            element_identifiers = []
            for i, pair in enumerate(collection):
                element_identifiers.append(dict(name=f"test{i}", src="hdca", id=pair))
        if element_identifiers is None:
            element_identifiers = self.nested_collection_identifiers(history_id, collection_type)

        payload = dict(
            instance_type="history",
            history_id=history_id,
            element_identifiers=element_identifiers,
            collection_type=collection_type,
            name=name,
        )
        return self.__create(payload)

    def example_list_of_pairs(self, history_id: str) -> str:
        response = self.upload_collection(
            history_id,
            "list:paired",
            elements=[
                {
                    "name": "test0",
                    "elements": [
                        {"src": "pasted", "paste_content": "123\n", "name": "forward", "ext": "txt"},
                        {"src": "pasted", "paste_content": "456\n", "name": "reverse", "ext": "txt"},
                    ],
                },
                {
                    "name": "test1",
                    "elements": [
                        {"src": "pasted", "paste_content": "789\n", "name": "forward", "ext": "txt"},
                        {"src": "pasted", "paste_content": "0ab\n", "name": "reverse", "ext": "txt"},
                    ],
                },
            ],
            wait=True,
        )
        api_asserts.assert_status_code_is_ok(response)
        hdca_id = response.json()["outputs"][0]["id"]
        return hdca_id

    def create_list_of_pairs_in_history(self, history_id, **kwds):
        return self.upload_collection(
            history_id,
            "list:paired",
            elements=[
                {
                    "name": "test0",
                    "elements": [
                        {"src": "pasted", "paste_content": "TestData123", "name": "forward"},
                        {"src": "pasted", "paste_content": "TestData123", "name": "reverse"},
                    ],
                }
            ],
        )

    def create_list_of_list_in_history(self, history_id: str, **kwds):
        # create_nested_collection will generate nested collection from just datasets,
        # this function uses recursive generation of history hdcas.
        collection_type = kwds.pop("collection_type", "list:list")
        collection_types = collection_type.split(":")
        list = self.create_list_in_history(history_id, **kwds).json()["output_collections"][0]
        current_collection_type = "list"
        for collection_type in collection_types[1:]:
            current_collection_type = f"{current_collection_type}:{collection_type}"
            response = self.create_nested_collection(
                history_id=history_id,
                collection_type=current_collection_type,
                name=current_collection_type,
                collection=[list["id"]],
            )
            list = response.json()
        return response

    def create_pair_in_history(self, history_id: str, wait: bool = False, **kwds):
        payload = self.create_pair_payload(history_id, instance_type="history", **kwds)
        return self.__create(payload, wait=wait)

    def create_list_in_history(self, history_id: str, wait: bool = False, **kwds):
        payload = self.create_list_payload(history_id, instance_type="history", **kwds)
        return self.__create(payload, wait=wait)

    def upload_collection(self, history_id: str, collection_type, elements, wait: bool = False, **kwds):
        payload = self.__create_payload_fetch(history_id, collection_type, contents=elements, **kwds)
        return self.__create(payload, wait=wait)

    def create_list_payload(self, history_id: str, **kwds):
        return self.__create_payload(history_id, identifiers_func=self.list_identifiers, collection_type="list", **kwds)

    def create_pair_payload(self, history_id: str, **kwds):
        return self.__create_payload(
            history_id, identifiers_func=self.pair_identifiers, collection_type="paired", **kwds
        )

    def __create_payload(self, history_id: str, *args, **kwds):
        direct_upload = kwds.pop("direct_upload", True)
        if direct_upload:
            return self.__create_payload_fetch(history_id, *args, **kwds)
        else:
            return self.__create_payload_collection(history_id, *args, **kwds)

    def __create_payload_fetch(self, history_id: str, collection_type, ext="txt", **kwds):
        contents = None
        if "contents" in kwds:
            contents = kwds["contents"]
            del kwds["contents"]

        elements = []
        if contents is None:
            if collection_type == "paired":
                contents = [("forward", "TestData123"), ("reverse", "TestData123")]
            elif collection_type == "list":
                contents = ["TestData123", "TestData123", "TestData123"]
            else:
                raise Exception(f"Unknown collection_type {collection_type}")

        if isinstance(contents, list):
            for i, contents_level in enumerate(contents):
                # If given a full collection definition pass as is.
                if isinstance(contents_level, dict):
                    elements.append(contents_level)
                    continue

                element = {"src": "pasted", "ext": ext}
                # Else older style list of contents or element ID and contents,
                # convert to fetch API.
                if isinstance(contents_level, tuple):
                    # (element_identifier, contents)
                    element_identifier = contents_level[0]
                    dataset_contents = contents_level[1]
                else:
                    dataset_contents = contents_level
                    if collection_type == "list":
                        element_identifier = f"data{i}"
                    elif collection_type == "paired" and i == 0:
                        element_identifier = "forward"
                    else:
                        element_identifier = "reverse"
                element["name"] = element_identifier
                element["paste_content"] = dataset_contents
                element["to_posix_lines"] = kwds.get("to_posix_lines", True)
                elements.append(element)

        name = kwds.get("name", "Test Dataset Collection")

        targets = [
            {
                "destination": {"type": "hdca"},
                "elements": elements,
                "collection_type": collection_type,
                "name": name,
            }
        ]
        payload = dict(
            history_id=history_id,
            targets=targets,
        )
        if "__files" in kwds:
            payload["__files"] = kwds.pop("__files")
        return payload

    def wait_for_fetched_collection(self, fetch_response: Union[Dict[str, Any], Response]):
        fetch_response_dict: Dict[str, Any]
        if isinstance(fetch_response, Response):
            fetch_response_dict = fetch_response.json()
        else:
            fetch_response_dict = fetch_response
        self.dataset_populator.wait_for_job(fetch_response_dict["jobs"][0]["id"], assert_ok=True)
        initial_dataset_collection = fetch_response_dict["output_collections"][0]
        dataset_collection = self.dataset_populator.get_history_collection_details(
            initial_dataset_collection["history_id"], hid=initial_dataset_collection["hid"]
        )
        return dataset_collection

    def __create_payload_collection(self, history_id: str, identifiers_func, collection_type, **kwds):
        contents = None
        if "contents" in kwds:
            contents = kwds["contents"]
            del kwds["contents"]

        if "element_identifiers" not in kwds:
            kwds["element_identifiers"] = identifiers_func(history_id, contents=contents)

        if "name" not in kwds:
            kwds["name"] = "Test Dataset Collection"

        payload = dict(history_id=history_id, collection_type=collection_type, **kwds)
        return payload

    def pair_identifiers(self, history_id: str, contents=None, wait: bool = False):
        hda1, hda2 = self.__datasets(history_id, count=2, contents=contents, wait=wait)

        element_identifiers = [
            dict(name="forward", src="hda", id=hda1["id"]),
            dict(name="reverse", src="hda", id=hda2["id"]),
        ]
        return element_identifiers

    def list_identifiers(self, history_id: str, contents=None):
        count = 3 if contents is None else len(contents)
        # Contents can be a list of strings (with name auto-assigned here) or a list of
        # 2-tuples of form (name, dataset_content).
        if contents and isinstance(contents[0], tuple):
            hdas = self.__datasets(history_id, count=count, contents=[c[1] for c in contents])

            def hda_to_identifier(i, hda):
                return dict(name=contents[i][0], src="hda", id=hda["id"])

        else:
            hdas = self.__datasets(history_id, count=count, contents=contents)

            def hda_to_identifier(i, hda):
                return dict(name=f"data{i + 1}", src="hda", id=hda["id"])

        element_identifiers = [hda_to_identifier(i, hda) for (i, hda) in enumerate(hdas)]
        return element_identifiers

    def __create(self, payload, wait=False):
        # Create a collection - either from existing datasets using collection creation API
        # or from direct uploads with the fetch API. Dispatch on "targets" keyword in payload
        # to decide which to use.
        if "targets" not in payload:
            return self._create_collection(payload)
        else:
            return self.dataset_populator.fetch(payload, wait=wait)

    def __datasets(self, history_id: str, count: int, contents=None, wait: bool = False):
        datasets = []
        for i in range(count):
            new_kwds = {
                "wait": wait,
            }
            if contents:
                new_kwds["content"] = contents[i]
            datasets.append(self.dataset_populator.new_dataset(history_id, **new_kwds))
        return datasets

    def wait_for_dataset_collection(
        self, create_payload: dict, assert_ok: bool = False, timeout: timeout_type = DEFAULT_TIMEOUT
    ) -> None:
        for element in create_payload["elements"]:
            if element["element_type"] == "hda":
                self.dataset_populator.wait_for_dataset(
                    history_id=element["object"]["history_id"],
                    dataset_id=element["object"]["id"],
                    assert_ok=assert_ok,
                    timeout=timeout,
                )
            elif element["element_type"] == "dataset_collection":
                self.wait_for_dataset_collection(element["object"], assert_ok=assert_ok, timeout=timeout)

    @abstractmethod
    def _create_collection(self, payload: dict) -> Response:
        """Create collection from specified payload."""


class DatasetCollectionPopulator(BaseDatasetCollectionPopulator):
    def __init__(self, galaxy_interactor: ApiTestInteractor):
        self.galaxy_interactor = galaxy_interactor
        self.dataset_populator = DatasetPopulator(galaxy_interactor)

    def _create_collection(self, payload: dict) -> Response:
        create_response = self.galaxy_interactor.post("dataset_collections", data=payload, json=True)
        return create_response


LoadDataDictResponseT = Tuple[Dict[str, Any], Dict[str, Any], bool]


def load_data_dict(
    history_id: str,
    test_data: Dict[str, Any],
    dataset_populator: BaseDatasetPopulator,
    dataset_collection_populator: BaseDatasetCollectionPopulator,
) -> LoadDataDictResponseT:
    """Load a dictionary as inputs to a workflow (test data focused)."""

    test_data_resolver = TestDataResolver()

    def open_test_data(test_dict, mode="rb"):
        filename = test_data_resolver.get_filename(test_dict.pop("value"))
        return open(filename, mode)

    def read_test_data(test_dict):
        return open_test_data(test_dict, mode="r").read()

    inputs = {}
    label_map = {}
    has_uploads = False

    for key, value in test_data.items():
        is_dict = isinstance(value, dict)
        if is_dict and ("elements" in value or value.get("collection_type")):
            elements_data = value.get("elements", [])
            elements = []
            new_collection_kwds: Dict[str, Any] = {}
            for i, element_data in enumerate(elements_data):
                # Adapt differences between test_data dict and fetch API description.
                if "name" not in element_data:
                    identifier = element_data.pop("identifier")
                    element_data["name"] = identifier
                input_type = element_data.pop("type", "raw")
                content = None
                if input_type == "File":
                    content = open_test_data(element_data)
                    element_data["src"] = "files"
                    if "__files" not in new_collection_kwds:
                        new_collection_kwds["__files"] = {}
                    new_collection_kwds["__files"][f"file_{i}|file_data"] = content
                else:
                    content = element_data.pop("content")
                    if content is not None:
                        element_data["src"] = "pasted"
                        element_data["paste_content"] = content
                elements.append(element_data)
            if "name" in value:
                new_collection_kwds["name"] = value["name"]
            collection_type = value.get("collection_type", "")
            if collection_type == "list:paired":
                fetch_response = dataset_collection_populator.create_list_of_pairs_in_history(
                    history_id, contents=elements, wait=True, **new_collection_kwds
                ).json()
            elif collection_type and ":" in collection_type:
                fetch_response = {
                    "outputs": [
                        dataset_collection_populator.create_nested_collection(
                            history_id, collection_type=collection_type, **new_collection_kwds
                        ).json()
                    ]
                }
            elif collection_type == "list":
                fetch_response = dataset_collection_populator.create_list_in_history(
                    history_id, contents=elements, direct_upload=True, wait=True, **new_collection_kwds
                ).json()
            else:
                fetch_response = dataset_collection_populator.create_pair_in_history(
                    history_id, contents=elements or None, direct_upload=True, wait=True, **new_collection_kwds
                ).json()
            hdca_output = fetch_response["outputs"][0]
            hdca = dataset_populator.ds_entry(hdca_output)
            hdca["hid"] = hdca_output["hid"]
            label_map[key] = hdca
            inputs[key] = hdca
            has_uploads = True
        elif is_dict and "type" in value:
            input_type = value.pop("type")
            if input_type == "File":
                if "value" in value:
                    content = open_test_data(value)
                elif "content" in value:
                    content = value["content"]
                else:
                    raise ValueError(f"Invalid test_data def {test_data}")
                new_dataset_kwds = {"content": content}
                if "name" in value:
                    new_dataset_kwds["name"] = value["name"]
                if "file_type" in value:
                    new_dataset_kwds["file_type"] = value["file_type"]
                hda = dataset_populator.new_dataset(history_id, wait=True, **new_dataset_kwds)
                label_map[key] = dataset_populator.ds_entry(hda)
                has_uploads = True
            elif input_type == "Directory":
                hda = dataset_populator.new_directory_dataset(
                    test_data_resolver, history_id, directory=value["value"], format=value.get("file_type", "directory")
                )
                label_map[key] = dataset_populator.ds_entry(hda)
                has_uploads = True
            elif input_type == "raw":
                label_map[key] = value["value"]
                inputs[key] = value["value"]
        elif not is_dict:
            has_uploads = True
            hda = dataset_populator.new_dataset(history_id, content=value)
            label_map[key] = dataset_populator.ds_entry(hda)
            inputs[key] = hda

    return inputs, label_map, has_uploads


def stage_inputs(
    galaxy_interactor: ApiTestInteractor,
    history_id: str,
    job: Dict[str, Any],
    use_path_paste: bool = True,
    use_fetch_api: bool = True,
    to_posix_lines: bool = True,
    tool_or_workflow: Literal["tool", "workflow"] = "workflow",
    job_dir: Optional[str] = None,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Alternative to load_data_dict that uses production-style workflow inputs."""
    kwds = {}
    if job_dir is not None:
        kwds["job_dir"] = job_dir
    return InteractorStaging(galaxy_interactor, use_fetch_api=use_fetch_api).stage(
        tool_or_workflow,
        history_id=history_id,
        job=job,
        use_path_paste=use_path_paste,
        to_posix_lines=to_posix_lines,
        **kwds,
    )


def stage_rules_example(
    galaxy_interactor: ApiTestInteractor, history_id: str, example: Dict[str, Any]
) -> Dict[str, Any]:
    """Wrapper around stage_inputs for staging collections defined by rules spec DSL."""
    input_dict = example["test_data"].copy()
    input_dict["collection_type"] = input_dict.pop("type")
    input_dict["class"] = "Collection"
    inputs, _ = stage_inputs(galaxy_interactor, history_id=history_id, job={"input": input_dict})
    return inputs


def wait_on_state(
    state_func: Callable,
    desc: str = "state",
    skip_states=None,
    ok_states=None,
    assert_ok: bool = False,
    timeout: timeout_type = DEFAULT_TIMEOUT,
) -> str:
    def get_state():
        response = state_func()
        assert response.status_code == 200, f"Failed to fetch state update while waiting. [{response.content}]"
        state_response = response.json()
        state = state_response["state"]
        if state in skip_states:
            return None
        else:
            if assert_ok:
                assert state in ok_states, f"Final state - {state} - not okay. Full response: {state_response}"
            return state

    if skip_states is None:
        skip_states = [
            "running",
            "queued",
            "new",
            "ready",
            "requires_materialization",
            "stop",
            "stopped",
            "setting_metadata",
            "waiting",
            "cancelling",
            "deleting",
        ]
    if ok_states is None:
        ok_states = ["ok", "scheduled", "deferred"]
    # Remove ok_states from skip_states, so we can wait for a state to becoming running
    skip_states = [s for s in skip_states if s not in ok_states]
    try:
        return wait_on(get_state, desc=desc, timeout=timeout)
    except TimeoutAssertionError as e:
        response = state_func()
        raise TimeoutAssertionError(f"{e} Current response containing state [{response.json()}].")


def _store_payload(
    store_dict: Optional[Dict[str, Any]] = None,
    store_path: Optional[str] = None,
    model_store_format: Optional[str] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
    # Ensure only one store method set.
    assert store_dict is not None or store_path is not None
    assert store_dict is None or store_path is None
    if store_dict is not None:
        payload["store_dict"] = store_dict
    if store_path is not None and "://" not in store_path:
        payload["store_content_uri"] = "base64://" + base64.b64encode(open(store_path, "rb").read()).decode("utf-8")
    else:
        payload["store_content_uri"] = store_path
    if model_store_format is not None:
        payload["model_store_format"] = model_store_format
    return payload


class DescribeToolExecutionOutput:

    def __init__(self, dataset_populator: BaseDatasetPopulator, history_id: str, hda_id: str):
        self._dataset_populator = dataset_populator
        self._history_id = history_id
        self._hda_id = hda_id

    @property
    def details(self) -> Dict[str, Any]:
        dataset_details = self._dataset_populator.get_history_dataset_details(self._history_id, dataset_id=self._hda_id)
        return dataset_details

    @property
    def contents(self) -> str:
        return self._dataset_populator.get_history_dataset_content(history_id=self._history_id, dataset_id=self._hda_id)

    def with_contents(self, expected_contents: str) -> Self:
        contents = self.contents
        if contents != expected_contents:
            raise AssertionError(f"Output dataset had contents {contents} but expected {expected_contents}")
        return self

    def with_contents_stripped(self, expected_contents: str) -> Self:
        contents = self.contents
        if contents.strip() != expected_contents:
            raise AssertionError(f"Output dataset had contents {contents} but expected {expected_contents}")
        return self

    def containing(self, expected_contents: str) -> Self:
        contents = self.contents
        if expected_contents not in contents:
            raise AssertionError(
                f"Output dataset had contents {contents} which does not contain the expected text {expected_contents}"
            )
        return self

    def with_file_ext(self, expected_ext: str) -> Self:
        ext = self.details["file_ext"]
        if ext != expected_ext:
            raise AssertionError(f"Output dataset had file extension {ext}, not the expected extension {expected_ext}")
        return self

    @property
    def json(self) -> Any:
        contents = self.contents
        return json.loads(contents)

    def with_json(self, expected_json: Any) -> Self:
        json = self.json
        if json != expected_json:
            raise AssertionError(f"Output dataset contianed JSON {json}, not {expected_json} as expected")
        return self

    # aliases that might help make tests more like English in particular cases. Declaring them explicitly
    # instead quick little aliases because of https://github.com/python/mypy/issues/6700
    def assert_contains(self, expected_contents: str) -> Self:
        return self.containing(expected_contents)

    def assert_has_contents(self, expected_contents: str) -> Self:
        return self.with_contents(expected_contents)


class DescribeToolExecutionOutputCollection:

    def __init__(self, dataset_populator: BaseDatasetPopulator, history_id: str, hdca_id: str):
        self._dataset_populator = dataset_populator
        self._history_id = history_id
        self._hdca_id = hdca_id

    @property
    def details(self) -> Dict[str, Any]:
        collection_details = self._dataset_populator.get_history_collection_details(
            self._history_id, content_id=self._hdca_id
        )
        return collection_details

    @property
    def elements(self) -> List[Dict[str, Any]]:
        return self.details["elements"]

    def with_n_elements(self, n: int) -> Self:
        count = len(self.elements)
        if count != n:
            raise AssertionError("Collection contained {count} elements and not the expected {n} elements")
        return self

    def with_element_dict(self, index: Union[str, int]) -> Dict[str, Any]:
        elements = self.elements
        if isinstance(index, int):
            element_dict = elements[index]
        else:
            element_dict = [e for e in elements if e["element_identifier"] == index][0]
        return element_dict

    def with_dataset_element(self, index: Union[str, int]) -> "DescribeToolExecutionOutput":
        element_dict = self.with_element_dict(index)
        element_object = element_dict["object"]
        return DescribeToolExecutionOutput(self._dataset_populator, self._history_id, element_object["id"])

    def named(self, expected_name: str) -> Self:
        name = self.details["name"]
        if name != expected_name:
            raise AssertionError(f"Dataset collection named {name} did not have expected name {expected_name}.")
        return self

    # aliases that might help make tests more like English in particular cases.
    def assert_has_dataset_element(self, index: Union[str, int]) -> "DescribeToolExecutionOutput":
        return self.with_dataset_element(index)


class DescribeJob:

    def __init__(self, dataset_populator: BaseDatasetPopulator, history_id: str, job_id: str):
        self._dataset_populator = dataset_populator
        self._history_id = history_id
        self._job_id = job_id
        self._final_details: Optional[Dict[str, Any]] = None

    def _wait_for(self):
        if self._final_details is None:
            self._dataset_populator.wait_for_job(self._job_id, assert_ok=False)
            self._final_details = self._dataset_populator.get_job_details(self._job_id).json()

    @property
    def final_details(self) -> Dict[str, Any]:
        self._wait_for()
        final_details = self._final_details
        assert final_details
        return final_details

    @property
    def final_state(self) -> str:
        final_state = self.final_details["state"]
        assert final_state
        return final_state

    def with_final_state(self, expected_state: str) -> Self:
        final_state = self.final_state
        if final_state != expected_state:
            raise AssertionError(
                f"Expected job {self._job_id} to end with state {expected_state} but it ended with state {final_state}"
            )
        return self

    @property
    def with_single_output(self) -> DescribeToolExecutionOutput:
        return self.with_output(0)

    def with_output(self, output: Union[str, int]) -> DescribeToolExecutionOutput:
        self.with_final_state("ok")
        outputs = self._dataset_populator.job_outputs(self._job_id)
        by_name = isinstance(output, str)
        dataset_id: Optional[str] = None
        if by_name:
            for output_assoc in outputs:
                if output_assoc["name"] == output:
                    dataset_id = output_assoc["dataset"]["id"]
        else:
            assert isinstance(output, int)
            dataset_id = outputs[output]["dataset"]["id"]
        if dataset_id is None:
            raise AssertionError(f"Could not find job output identified by {output}")
        return DescribeToolExecutionOutput(self._dataset_populator, self._history_id, dataset_id)

    # aliases that might help make tests more like English in particular cases.
    def assert_has_output(self, output: Union[str, int]) -> DescribeToolExecutionOutput:
        return self.with_output(output)

    @property
    def assert_has_single_output(self) -> DescribeToolExecutionOutput:
        return self.with_single_output


class DescribeFailure:
    def __init__(self, response: Response):
        self._response = response

    def __call__(self) -> Self:
        return self

    def with_status_code(self, code: int) -> Self:
        api_asserts.assert_status_code_is(self._response, code)
        return self

    def with_error_containing(self, message: str) -> Self:
        assert message in self._response.text
        return self


class RequiredTool:

    def __init__(self, dataset_populator: BaseDatasetPopulator, tool_id: str, default_history_id: Optional[str]):
        self._dataset_populator = dataset_populator
        self._tool_id = tool_id
        self._default_history_id = default_history_id

    @property
    def execute(self) -> "DescribeToolExecution":
        execution = DescribeToolExecution(self._dataset_populator, self._tool_id)
        if self._default_history_id:
            execution.in_history(self._default_history_id)
        return execution


class DescribeToolInputs:
    _input_format: str = "legacy"
    _inputs: Optional[Dict[str, Any]]

    def __init__(self, input_format: str):
        self._input_format = input_format
        self._inputs = None

    def any(self, inputs: Dict[str, Any]) -> Self:
        self._inputs = inputs
        return self

    def flat(self, inputs: Dict[str, Any]) -> Self:
        if self._input_format == "legacy":
            self._inputs = inputs
        return self

    def nested(self, inputs: Dict[str, Any]) -> Self:
        if self._input_format == "21.01":
            self._inputs = inputs
        return self

    # aliases for self to create silly little English sentense... inputs.when.flat().when.legacy()
    @property
    def when(self) -> Self:
        return self


class DescribeToolExecution:
    _history_id: Optional[str] = None
    _execute_response: Optional[Response] = None
    _input_format: Optional[str] = None
    _inputs: Dict[str, Any]

    def __init__(self, dataset_populator: BaseDatasetPopulator, tool_id: str):
        self._dataset_populator = dataset_populator
        self._tool_id = tool_id
        self._inputs = {}

    def in_history(self, has_history_id: Union[str, "TargetHistory"]) -> Self:
        if isinstance(has_history_id, str):
            self._history_id = has_history_id
        else:
            self._history_id = has_history_id._history_id
        return self

    def with_inputs(self, inputs: Union[DescribeToolInputs, Dict[str, Any]]) -> Self:
        if isinstance(inputs, DescribeToolInputs):
            self._inputs = inputs._inputs or {}
            self._input_format = inputs._input_format
        else:
            self._inputs = inputs
            self._input_format = "legacy"
        return self

    def with_nested_inputs(self, inputs: Dict[str, Any]) -> Self:
        self._inputs = inputs
        self._input_format = "21.01"
        return self

    def _execute(self):
        kwds = {}
        if self._input_format is not None:
            kwds["input_format"] = self._input_format
        history_id = self._ensure_history_id
        self._execute_response = self._dataset_populator.run_tool_raw(
            self._tool_id, self._inputs, history_id, assert_ok=False, **kwds
        )

    @property
    def _ensure_history_id(self) -> str:
        history_id = self._history_id
        if history_id is None:
            raise AssertionError("Problem building test execution - no history ID has been specified.")
        return history_id

    def _ensure_executed(self) -> None:
        if self._execute_response is None:
            self._execute()

    def _assert_executed_ok(self) -> Dict[str, Any]:
        self._ensure_executed()
        execute_response = self._execute_response
        assert execute_response is not None
        api_asserts.assert_status_code_is_ok(execute_response)
        return execute_response.json()

    def assert_has_n_jobs(self, n: int) -> Self:
        response = self._assert_executed_ok()
        jobs = response["jobs"]
        if len(jobs) != n:
            raise AssertionError(f"Expected tool execution to produce {n} jobs but it produced {len(jobs)}")
        return self

    def assert_creates_n_implicit_collections(self, n: int) -> Self:
        response = self._assert_executed_ok()
        collections = response["implicit_collections"]
        if len(collections) != n:
            raise AssertionError(f"Expected tool execution to produce {n} implicit but it produced {len(collections)}")
        return self

    def assert_creates_implicit_collection(self, index: Union[str, int]) -> "DescribeToolExecutionOutputCollection":
        response = self._assert_executed_ok()
        collections = response["implicit_collections"]
        assert isinstance(index, int)  # TODO: implement and then prefer str.
        history_id = self._ensure_history_id
        return DescribeToolExecutionOutputCollection(self._dataset_populator, history_id, collections[index]["id"])

    @property
    def assert_has_single_job(self) -> DescribeJob:
        return self.assert_has_n_jobs(1).assert_has_job(0)

    def assert_has_job(self, job_index: int = 0) -> DescribeJob:
        response = self._assert_executed_ok()
        job = response["jobs"][job_index]
        history_id = self._ensure_history_id
        return DescribeJob(self._dataset_populator, history_id, job["id"])

    @property
    def that_fails(self) -> DescribeFailure:
        self._ensure_executed()
        execute_response = self._execute_response
        assert execute_response is not None
        if execute_response.status_code != 200:
            return DescribeFailure(execute_response)
        else:
            response = self._assert_executed_ok()
            jobs = response["jobs"]
            for job in jobs:
                final_state = self._dataset_populator.wait_for_job(job["id"])
                assert final_state == "error"
            return DescribeFailure(execute_response)

    # alternative assert_ syntax for cases where it reads better.
    @property
    def assert_fails(self) -> DescribeFailure:
        return self.that_fails


class GiHttpMixin:
    """Mixin for adapting Galaxy testing populators helpers to bioblend."""

    _gi: GalaxyClient

    @property
    def _api_key(self):
        return self._gi.key

    def _api_url(self):
        return self._gi.url

    def _get(self, route, data=None, headers=None, admin=False) -> Response:
        return self._gi.make_get_request(self._url(route), params=data)

    def _post(
        self, route, data=None, files=None, headers=None, admin=False, json: bool = False, anon: bool = False
    ) -> Response:
        if headers is None:
            headers = {}
        headers = headers.copy()
        if not anon:
            headers["x-api-key"] = self._gi.key
        return requests.post(self._url(route), data=data, headers=headers, timeout=DEFAULT_SOCKET_TIMEOUT)

    def _put(self, route, data=None, headers=None, admin=False, json: bool = False):
        if headers is None:
            headers = {}
        headers = headers.copy()
        headers["x-api-key"] = self._gi.key
        return requests.put(self._url(route), data=data, headers=headers, timeout=DEFAULT_SOCKET_TIMEOUT)

    def _delete(self, route, data=None, headers=None, admin=False, json: bool = False):
        if headers is None:
            headers = {}
        headers = headers.copy()
        headers["x-api-key"] = self._gi.key
        return requests.delete(self._url(route), data=data, headers=headers, timeout=DEFAULT_SOCKET_TIMEOUT)

    def _url(self, route):
        if route.startswith("/api/"):
            route = route[len("/api/") :]

        return f"{self._api_url()}/{route}"


class GiDatasetPopulator(GiHttpMixin, BaseDatasetPopulator):
    """Implementation of BaseDatasetPopulator backed by bioblend."""

    def __init__(self, gi):
        """Construct a dataset populator from a bioblend GalaxyInstance."""
        self._gi = gi

    def _summarize_history(self, history_id: str) -> None:
        pass


class GiDatasetCollectionPopulator(GiHttpMixin, BaseDatasetCollectionPopulator):
    """Implementation of BaseDatasetCollectionPopulator backed by bioblend."""

    def __init__(self, gi):
        """Construct a dataset collection populator from a bioblend GalaxyInstance."""
        self._gi = gi
        self.dataset_populator = GiDatasetPopulator(gi)
        self.dataset_collection_populator = GiDatasetCollectionPopulator(gi)

    def _create_collection(self, payload):
        create_response = self._post("dataset_collections", data=payload, json=True)
        return create_response


class GiWorkflowPopulator(GiHttpMixin, BaseWorkflowPopulator):
    """Implementation of BaseWorkflowPopulator backed by bioblend."""

    def __init__(self, gi):
        """Construct a workflow populator from a bioblend GalaxyInstance."""
        self._gi = gi
        self.dataset_populator = GiDatasetPopulator(gi)


ListContentsDescription = Union[List[str], List[Tuple[str, str]]]


class TargetHistory:

    def __init__(
        self,
        dataset_populator: DatasetPopulator,
        dataset_collection_populator: DatasetCollectionPopulator,
        history_id: str,
    ):
        self._dataset_populator = dataset_populator
        self._dataset_collection_populator = dataset_collection_populator
        self._history_id = history_id

    @property
    def id(self) -> str:
        return self._history_id

    def with_dataset(
        self,
        content: str,
        named: Optional[str] = None,
    ) -> "HasSrcDict":
        kwd = {}
        if named is not None:
            kwd["name"] = named
        new_dataset = self._dataset_populator.new_dataset(
            history_id=self._history_id,
            content=content,
            assert_ok=True,
            wait=True,
            **kwd,
        )
        return HasSrcDict("hda", new_dataset)

    def with_pair(self, contents: Optional[List[str]] = None) -> "HasSrcDict":
        return self._fetch_response(
            self._dataset_collection_populator.create_pair_in_history(
                self._history_id, contents=contents, direct_upload=True, wait=True
            )
        )

    def with_list(self, contents: Optional[ListContentsDescription] = None) -> "HasSrcDict":
        return self._fetch_response(
            self._dataset_collection_populator.create_list_in_history(
                self._history_id, contents=contents, direct_upload=True, wait=True
            )
        )

    def with_example_list_of_pairs(self) -> "HasSrcDict":
        return HasSrcDict("hdca", self._dataset_collection_populator.example_list_of_pairs(self._history_id))

    @classmethod
    def _fetch_response(clz, response: Response) -> "HasSrcDict":
        api_asserts.assert_status_code_is_ok(response)
        hdca = response.json()["output_collections"][0]
        return HasSrcDict("hdca", hdca)

    def execute(self, tool_id: str) -> "DescribeToolExecution":
        return self._dataset_populator.describe_tool_execution(tool_id).in_history(self)


class SrcDict(TypedDict):
    src: str
    id: str


class HasSrcDict:
    api_object: Union[str, Dict[str, Any]]

    def __init__(self, src_type: str, api_object: Union[str, Dict[str, Any]]):
        self.src_type = src_type
        self.api_object = api_object

    @property
    def id(self) -> str:
        has_id = self.api_object
        return has_id if isinstance(has_id, str) else cast(str, has_id["id"])

    @property
    def src_dict(self) -> SrcDict:
        return SrcDict({"src": self.src_type, "id": self.id})

    @property
    def to_dict(self):
        return self.api_object


def wait_on(function: Callable, desc: str, timeout: timeout_type = DEFAULT_TIMEOUT):
    return tool_util_wait_on(function, desc, timeout)


def wait_on_assertion(function: Callable, desc: str, timeout: timeout_type = DEFAULT_TIMEOUT):
    def inner_func():
        try:
            function()
            return True
        except AssertionError:
            return False

    wait_on(inner_func, desc, timeout)
