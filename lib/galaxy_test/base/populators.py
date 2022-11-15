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
import random
import string
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
    Dict,
    List,
    NamedTuple,
    Optional,
    Set,
    Tuple,
    Union,
)

import cwltest.utils
import requests
import yaml
from bioblend.galaxy import GalaxyClient
from gxformat2 import (
    convert_and_import_workflow,
    ImporterGalaxyInterface,
)
from gxformat2._yaml import ordered_load
from requests.models import Response

from galaxy.tool_util.client.staging import InteractorStaging
from galaxy.tool_util.cwl.util import guess_artifact_type
from galaxy.tool_util.verify.test_data import TestDataResolver
from galaxy.tool_util.verify.wait import (
    timeout_type,
    TimeoutAssertionError,
)
from galaxy.tool_util.verify.wait import wait_on as tool_util_wait_on
from galaxy.util import (
    DEFAULT_SOCKET_TIMEOUT,
    galaxy_root_path,
)
from galaxy.util.resources import resource_string
from . import api_asserts
from .api import ApiTestInteractor

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


def flakey(method):
    @wraps(method)
    def wrapped_method(test_case, *args, **kwargs):
        try:
            method(test_case, *args, **kwargs)
        except unittest.SkipTest:
            raise
        except Exception:
            if SKIP_FLAKEY_TESTS_ON_ERROR:
                raise unittest.SkipTest("Error encountered during test marked as @flakey.")
            else:
                raise

    return wrapped_method


def skip_without_tool(tool_id):
    """Decorate an API test method as requiring a specific tool.

    Have test framework skip the test case if the tool is unavailable.
    """

    def method_wrapper(method):
        def get_tool_ids(api_test_case):
            index = api_test_case.galaxy_interactor.get("tools", data=dict(in_panel=False))
            tools = index.json()
            # In panels by default, so flatten out sections...
            tool_ids = [itemgetter("id")(_) for _ in tools]
            return tool_ids

        @wraps(method)
        def wrapped_method(api_test_case, *args, **kwargs):
            _raise_skip_if(tool_id not in get_tool_ids(api_test_case))
            return method(api_test_case, *args, **kwargs)

        return wrapped_method

    return method_wrapper


def skip_without_asgi(method):
    @wraps(method)
    def wrapped_method(api_test_case, *args, **kwd):
        config = api_test_case.galaxy_interactor.get("configuration").json()
        asgi_enabled = config.get("asgi_enabled", False)
        if not asgi_enabled:
            raise unittest.SkipTest("ASGI not enabled, skipping test")
        return method(api_test_case, *args, **kwd)

    return wrapped_method


def skip_without_datatype(extension):
    """Decorate an API test method as requiring a specific datatype.

    Have test framework skip the test case if the datatype is unavailable.
    """

    def has_datatype(api_test_case):
        index_response = api_test_case.galaxy_interactor.get("datatypes")
        assert index_response.status_code == 200, "Failed to fetch datatypes for target Galaxy."
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


def is_site_up(url):
    try:
        response = requests.get(url, timeout=10)
        return response.status_code == 200
    except Exception:
        return False


def skip_if_site_down(url):
    def method_wrapper(method):
        @wraps(method)
        def wrapped_method(api_test_case, *args, **kwargs):
            _raise_skip_if(not is_site_up(url), f"Test depends on [{url}] being up and it appears to be down.")
            method(api_test_case, *args, **kwargs)

        return wrapped_method

    return method_wrapper


skip_if_toolshed_down = skip_if_site_down("https://toolshed.g2.bx.psu.edu")
skip_if_github_down = skip_if_site_down("https://github.com/")


def summarize_instance_history_on_error(method):
    @wraps(method)
    def wrapped_method(api_test_case, *args, **kwds):
        try:
            method(api_test_case, *args, **kwds)
        except Exception:
            api_test_case.dataset_populator._summarize_history(api_test_case.history_id)
            raise

    return wrapped_method


def uses_test_history(**test_history_kwd):
    """Can override require_new and cancel_executions using kwds to decorator."""

    def method_wrapper(method):
        @wraps(method)
        def wrapped_method(api_test_case, *args, **kwds):
            with api_test_case.dataset_populator.test_history(**test_history_kwd) as history_id:
                method(api_test_case, history_id, *args, **kwds)

        return wrapped_method

    return method_wrapper


def _raise_skip_if(check, *args):
    if check:
        raise unittest.SkipTest(*args)


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


class CwlToolRun(CwlRun):
    def __init__(self, dataset_populator, history_id, run_response):
        super().__init__(dataset_populator, history_id)
        self.run_response = run_response

    @property
    def job_id(self):
        return self.run_response.json()["jobs"][0]["id"]

    def wait(self):
        self.dataset_populator.wait_for_job(self.job_id, assert_ok=True)


class CwlWorkflowRun(CwlRun):
    def __init__(self, dataset_populator, workflow_populator, history_id, workflow_id, invocation_id):
        super().__init__(dataset_populator, history_id)
        self.workflow_populator = workflow_populator
        self.workflow_id = workflow_id
        self.invocation_id = invocation_id

    def wait(self):
        self.workflow_populator.wait_for_invocation_and_jobs(self.history_id, self.workflow_id, self.invocation_id)


class BasePopulator(metaclass=ABCMeta):

    galaxy_interactor: ApiTestInteractor

    @abstractmethod
    def _post(self, route, data=None, files=None, headers=None, admin=False, json: bool = False) -> Response:
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
    ) -> dict:
        """Create a new history dataset instance (HDA) and return its ID.

        :returns: the HDA id of the new object
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
    ) -> requests.Response:
        """Lower-level dataset creation that returns the upload tool response object."""
        if content is None and "ftp_files" not in kwds:
            content = "TestData123"
        if not fetch_data:
            payload = self.upload_payload(history_id, content=content, **kwds)
            run_response = self.tools_post(payload)
        else:
            payload = self.fetch_payload(history_id, content=content, **kwds)
            run_response = self.fetch(payload, wait=wait)
        if wait:
            self.wait_for_tool_run(history_id, run_response, assert_ok=kwds.get("assert_ok", True))
        return run_response

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

    def fetch_hda(self, history_id, item: Dict[str, Any], wait: bool = True) -> Dict[str, Any]:
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

    def tag_dataset(self, history_id, hda_id, tags):
        url = f"histories/{history_id}/contents/{hda_id}"
        response = self._put(url, {"tags": tags}, json=True)
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
        run_response: requests.Response,
        timeout: timeout_type = DEFAULT_TIMEOUT,
        assert_ok: bool = True,
    ):
        job = self.check_run(run_response)
        self.wait_for_job(job["id"], timeout=timeout)
        self.wait_for_history(history_id, assert_ok=assert_ok, timeout=timeout)
        return run_response

    def check_run(self, run_response: requests.Response) -> dict:
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
            self.wait_for_history(history_id, assert_ok=True, timeout=timeout)

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

    def cancel_history_jobs(self, history_id: str, wait=True) -> None:
        active_jobs = self.active_history_jobs(history_id)
        for active_job in active_jobs:
            self.cancel_job(active_job["id"])

    def history_jobs(self, history_id: str) -> List[Dict[str, Any]]:
        query_params = {"history_id": history_id, "order_by": "create_time"}
        jobs_response = self._get("jobs", query_params)
        assert jobs_response.status_code == 200
        return jobs_response.json()

    def active_history_jobs(self, history_id: str) -> list:
        all_history_jobs = self.history_jobs(history_id)
        active_jobs = [j for j in all_history_jobs if j["state"] in ["new", "upload", "waiting", "queued", "running"]]
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
        try:
            create_response = self._post("dynamic_tools", data=payload, admin=True)
        except TypeError:
            create_response = self._post("dynamic_tools", data=payload)
        assert create_response.status_code == 200, create_response.text
        return create_response.json()

    def list_dynamic_tools(self) -> list:
        list_response = self._get("dynamic_tools", admin=True)
        assert list_response.status_code == 200, list_response
        return list_response.json()

    def show_dynamic_tool(self, uuid) -> dict:
        show_response = self._get(f"dynamic_tools/{uuid}", admin=True)
        assert show_response.status_code == 200, show_response
        return show_response.json()

    def deactivate_dynamic_tool(self, uuid) -> dict:
        delete_response = self._delete(f"dynamic_tools/{uuid}", admin=True)
        return delete_response.json()

    def _summarize_history(self, history_id: str) -> None:
        """Abstract method for summarizing a target history - override to provide details."""

    @contextlib.contextmanager
    def test_history(self, cancel_executions: bool = True, require_new: bool = True, **kwds):
        cleanup = "GALAXY_TEST_NO_CLEANUP" not in os.environ
        history_id = None

        def wrap_up():
            if cleanup and cancel_executions and history_id:
                self.cancel_history_jobs(history_id)

        try:
            if not require_new:
                history_id = kwds.get("GALAXY_TEST_HISTORY_ID", None)

            history_id = history_id or self.new_history()
            yield history_id
            wrap_up()
        except Exception:
            if history_id:
                self._summarize_history(history_id)
            wrap_up()
            raise

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

    def get_history_dataset_content(self, history_id: str, wait=True, filename=None, type="text", raw=False, **kwds):
        dataset_id = self.__history_content_id(history_id, wait=wait, **kwds)
        data = {}
        if filename:
            data["filename"] = filename
        if raw:
            data["raw"] = True
        display_response = self._get_contents_request(history_id, f"/{dataset_id}/display", data=data)
        assert display_response.status_code == 200, display_response.text
        if type == "text":
            return display_response.text
        else:
            return display_response.content

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

    def get_history_dataset_details(self, history_id: str, **kwds) -> dict:
        dataset_id = self.__history_content_id(history_id, **kwds)
        details_response = self.get_history_dataset_details_raw(history_id, dataset_id)
        details_response.raise_for_status()
        return details_response.json()

    def get_history_dataset_details_raw(self, history_id: str, dataset_id: str) -> Response:
        details_response = self._get_contents_request(history_id, f"/datasets/{dataset_id}")
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

    def get_history_contents(self, history_id: str) -> List[Dict[str, Any]]:
        contents_response = self._get_contents_request(history_id)
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
        roles_response = self._get("roles", admin=True)
        assert roles_response.status_code == 200
        return roles_response.json()

    def get_configuration(self, admin=False) -> Dict[str, Any]:
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
        user_email = self.user_email()
        roles = self.get_roles()
        users_roles = [r for r in roles if r["name"] == user_email]
        assert len(users_roles) == 1, f"Did not find exactly one role for email {user_email} - {users_roles}"
        role = users_roles[0]
        assert "id" in role, role
        return role["id"]

    def create_role(self, user_ids: list, description: Optional[str] = None) -> dict:
        payload = {
            "name": self.get_random_name(prefix="testpop"),
            "description": description or "Test Role",
            "user_ids": user_ids,
        }
        role_response = self._post("roles", data=payload, admin=True, json=True)
        assert role_response.status_code == 200
        return role_response.json()

    def create_quota(self, quota_payload: dict) -> dict:
        quota_response = self._post("quotas", data=quota_payload, admin=True)
        quota_response.raise_for_status()
        return quota_response.json()

    def get_quotas(self) -> list:
        quota_response = self._get("quotas", admin=True)
        quota_response.raise_for_status()
        return quota_response.json()

    def make_private(self, history_id: str, dataset_id: str) -> dict:
        role_id = self.user_private_role_id()
        # Give manage permission to the user.
        payload = {
            "access": [role_id],
            "manage": [role_id],
        }
        url = f"histories/{history_id}/contents/{dataset_id}/permissions"
        update_response = self._put(url, payload, admin=True, json=True)
        assert update_response.status_code == 200, update_response.content
        return update_response.json()

    def make_public(self, history_id: str) -> dict:
        sharing_response = self._put(f"histories/{history_id}/publish")
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
            if validated_state == "unknown":
                return
            else:
                return validated_state

        return wait_on(validated, "dataset validation")

    def setup_history_for_export_testing(self, history_name):
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
        archive_file = import_data.pop("archive_file", None)
        if archive_file:
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

    def rename_history(self, history_id, new_name):
        update_url = f"histories/{history_id}"
        put_response = self._put(update_url, {"name": new_name}, json=True)
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

    def assert_download_request_ok(self, download_request_response: Response) -> str:
        """Assert response is valid and okay and extract storage request ID."""
        api_asserts.assert_status_code_is(download_request_response, 200)
        download_async = download_request_response.json()
        assert "storage_request_id" in download_async
        storage_request_id = download_async["storage_request_id"]
        return storage_request_id

    def wait_for_download_ready(self, storage_request_id: str):
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

    def wait_on_download_request(self, storage_request_id: str) -> Response:
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

    def get_random_name(self, prefix=None, suffix=None, len=10):
        # stolen from navigates_galaxy.py
        return "{}{}{}".format(
            prefix or "",
            "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(len)),
            suffix or "",
        )

    def wait_for_dataset(
        self, history_id: str, dataset_id: str, assert_ok: bool = False, timeout: timeout_type = DEFAULT_TIMEOUT
    ) -> str:
        return wait_on_state(
            lambda: self._get(f"histories/{history_id}/contents/{dataset_id}"),
            desc="dataset state",
            assert_ok=assert_ok,
            timeout=timeout,
        )

    def new_page(
        self, slug: str = "mypage", title: str = "MY PAGE", content_format: str = "html", content: Optional[str] = None
    ) -> Dict[str, Any]:
        page_response = self.new_page_raw(slug=slug, title=title, content_format=content_format, content=content)
        page_response.raise_for_status()
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


class GalaxyInteractorHttpMixin:
    galaxy_interactor: ApiTestInteractor

    @property
    def _api_key(self):
        return self.galaxy_interactor.api_key

    def _post(self, route, data=None, files=None, headers=None, admin=False, json: bool = False) -> Response:
        return self.galaxy_interactor.post(route, data, files=files, admin=admin, headers=headers, json=json)

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
    def __init__(self, galaxy_interactor):
        self.galaxy_interactor = galaxy_interactor

    def _summarize_history(self, history_id):
        self.galaxy_interactor._summarize_history(history_id)


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

    def upload_yaml_workflow(self, has_yaml, **kwds) -> str:
        round_trip_conversion = kwds.get("round_trip_format_conversion", False)
        client_convert = kwds.pop("client_convert", not round_trip_conversion)
        kwds["convert"] = client_convert
        workflow = convert_and_import_workflow(has_yaml, galaxy_interface=self, **kwds)
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
        self, workflow_id: str, invocation_id: str, timeout: timeout_type = DEFAULT_TIMEOUT, assert_ok: bool = True
    ) -> str:
        url = f"invocations/{invocation_id}"

        def workflow_state():
            return self._get(url)

        return wait_on_state(workflow_state, desc="workflow invocation state", timeout=timeout, assert_ok=assert_ok)

    def workflow_invocations(self, workflow_id: str) -> List[Dict[str, Any]]:
        response = self._get(f"workflows/{workflow_id}/invocations")
        api_asserts.assert_status_code_is(response, 200)
        return response.json()

    def history_invocations(self, history_id: str) -> List[Dict[str, Any]]:
        history_invocations_response = self._get("invocations", {"history_id": history_id})
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

            wait_on(invocation_count, f"{expected_invocation_count} history invocations")
        for invocation in self.history_invocations(history_id):
            workflow_id = invocation["workflow_id"]
            invocation_id = invocation["id"]
            self.wait_for_workflow(workflow_id, invocation_id, history_id, timeout=timeout, assert_ok=assert_ok)

    def wait_for_workflow(
        self,
        workflow_id: str,
        invocation_id: str,
        history_id: str,
        assert_ok: bool = True,
        timeout: timeout_type = DEFAULT_TIMEOUT,
    ) -> None:
        """Wait for a workflow invocation to completely schedule and then history
        to be complete."""
        self.wait_for_invocation(workflow_id, invocation_id, timeout=timeout, assert_ok=assert_ok)
        self.dataset_populator.wait_for_history_jobs(history_id, assert_ok=assert_ok, timeout=timeout)

    def get_invocation(self, invocation_id, step_details=False):
        r = self._get(f"invocations/{invocation_id}", data={"step_details": step_details})
        r.raise_for_status()
        return r.json()

    def download_invocation_to_store(self, invocation_id, extension="tgz"):
        url = f"invocations/{invocation_id}/prepare_store_download"
        download_response = self._post(url, dict(include_files=False, model_store_format=extension), json=True)
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

    def get_biocompute_object(self, invocation_id):
        bco_response = self._get(f"invocations/{invocation_id}/biocompute")
        bco_response.raise_for_status()
        return bco_response.json()

    def validate_biocompute_object(
        self, bco, expected_schema_version="https://w3id.org/ieee/ieee-2791-schema/2791object.json"
    ):
        # TODO: actually use jsonref and jsonschema to validate this someday
        api_asserts.assert_has_keys(
            bco,
            "object_id",
            "spec_version",
            "etag",
            "provenance_domain",
            "usability_domain",
            "description_domain",
            "execution_domain",
            "parametric_domain",
            "io_domain",
            "error_domain",
        )
        assert bco["spec_version"] == expected_schema_version
        api_asserts.assert_has_keys(bco["description_domain"], "keywords", "xref", "platform", "pipeline_steps")
        api_asserts.assert_has_keys(
            bco["execution_domain"],
            "script",
            "script_driver",
            "software_prerequisites",
            "external_data_endpoints",
            "environment_variables",
        )
        for p in bco["parametric_domain"]:
            api_asserts.assert_has_keys(p, "param", "value", "step")
        api_asserts.assert_has_keys(bco["io_domain"], "input_subdomain", "output_subdomain")

    def invoke_workflow_raw(self, workflow_id: str, request: dict, assert_ok: bool = False) -> Response:
        url = f"workflows/{workflow_id}/invocations"
        invocation_response = self._post(url, data=request)
        if assert_ok:
            invocation_response.raise_for_status()
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
        self.wait_for_workflow(workflow_id, invocation_id, history_id, assert_ok=True)
        return invoke_return

    def workflow_report_json(self, workflow_id: str, invocation_id: str) -> dict:
        response = self._get(f"workflows/{workflow_id}/invocations/{invocation_id}/report")
        api_asserts.assert_status_code_is(response, 200)
        return response.json()

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
        has_workflow,
        test_data=None,
        history_id=None,
        wait=True,
        source_type=None,
        jobs_descriptions=None,
        expected_response=200,
        assert_ok=True,
        client_convert=None,
        round_trip_format_conversion=False,
        invocations=1,
        raw_yaml=False,
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
                    jobs_descriptions = yaml.safe_load(has_workflow)

            test_data = jobs_descriptions.get("test_data", {})

        if not isinstance(test_data, dict):
            test_data = yaml.safe_load(test_data)

        parameters = test_data.pop("step_parameters", {})
        replacement_parameters = test_data.pop("replacement_parameters", {})
        if history_id is None:
            history_id = self.dataset_populator.new_history()
        inputs, label_map, has_uploads = load_data_dict(
            history_id, test_data, self.dataset_populator, self.dataset_collection_populator
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
        if has_uploads:
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
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
                jobs.extend(self.dataset_populator.history_jobs(history_id))
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
        workflow_show_resposne = self._get(f"workflows/{workflow_id}")
        api_asserts.assert_status_code_is_ok(workflow_show_resposne)
        workflow_inputs = workflow_show_resposne.json()["inputs"]
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
        hda1 = self.dataset_populator.new_dataset(history_id, content="1 2 3", wait=True)
        hda2 = self.dataset_populator.new_dataset(history_id, content="4 5 6", wait=True)
        workflow_request = dict(
            history=f"hist_id={history_id}",
        )
        label_map = {"WorkflowInput1": ds_entry(hda1), "WorkflowInput2": ds_entry(hda2)}
        if inputs_by == "step_id":
            ds_map = self.build_ds_map(workflow_id, label_map)
            workflow_request["ds_map"] = ds_map
        elif inputs_by == "step_index":
            index_map = {"0": ds_entry(hda1), "1": ds_entry(hda2)}
            workflow_request["inputs"] = json.dumps(index_map)
            workflow_request["inputs_by"] = "step_index"
        elif inputs_by == "name":
            workflow_request["inputs"] = json.dumps(label_map)
            workflow_request["inputs_by"] = "name"
        elif inputs_by in ["step_uuid", "uuid_implicitly"]:
            assert workflow, f"Must specify workflow for this inputs_by {inputs_by} parameter value"
            uuid_map = {
                workflow["steps"]["0"]["uuid"]: ds_entry(hda1),
                workflow["steps"]["1"]["uuid"]: ds_entry(hda2),
            }
            workflow_request["inputs"] = json.dumps(uuid_map)
            if inputs_by == "step_uuid":
                workflow_request["inputs_by"] = "step_uuid"

        return workflow_request, history_id, workflow_id

    def wait_for_invocation_and_jobs(
        self, history_id: str, workflow_id: str, invocation_id: str, assert_ok: bool = True
    ) -> None:
        state = self.wait_for_invocation(workflow_id, invocation_id)
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

    def _import_tool_response(self, tool) -> Response:
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
    ):
        galaxy_tool_id: Optional[str] = tool_id
        tool_uuid = None

        if os.path.exists(tool_id):
            raw_tool_id = os.path.basename(tool_id)
            index = self.dataset_populator._get("tools", data=dict(in_panel=False))
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
        assert_ok=True,
    ):
        """
        :param artifact: CWL tool id, or (absolute or relative) path to a CWL
          tool or workflow file
        """
        if history_id is None:
            history_id = self.dataset_populator.new_history()
        artifact_without_id = artifact.split("#", 1)[0]
        if not os.path.exists(artifact_without_id):
            # Assume it's a tool id
            tool_or_workflow = "tool"
        else:
            tool_or_workflow = guess_artifact_type(artifact)
        if job_path and not os.path.exists(job_path):
            raise ValueError(f"job_path [{job_path}] does not exist")
        if test_data_directory is None and job_path is not None:
            test_data_directory = os.path.dirname(job_path)
        if job_path is not None:
            assert job is None
            with open(job_path) as f:
                if job_path.endswith(".yml") or job_path.endswith(".yaml"):
                    job = yaml.safe_load(f)
                else:
                    job = json.load(f)
        elif job is None:
            job = {}
        _, datasets_uploaded = stage_inputs(
            self.dataset_populator.galaxy_interactor,
            history_id,
            job,
            use_fetch_api=False,
            tool_or_workflow=tool_or_workflow,
            job_dir=test_data_directory,
        )
        if datasets_uploaded:
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
        try:
            for key, value in expected_outputs.items():
                actual_output = run.get_output_as_object(key)
                cwltest.utils.compare(value, actual_output)
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
            "validate_hashes": True,
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
        if files is None:
            files = {}

        url_rel = f"libraries/{library_id}/contents"
        return self.galaxy_interactor.post(url_rel, payload, files=files)

    def show_ld(self, library_id, library_dataset_id):
        response = self.galaxy_interactor.get(f"libraries/{library_id}/contents/{library_dataset_id}")
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

    def nested_collection_identifiers(self, history_id, collection_type):
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

    def create_list_of_list_in_history(self, history_id, **kwds):
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

    def create_pair_in_history(self, history_id, wait=False, **kwds):
        payload = self.create_pair_payload(history_id, instance_type="history", **kwds)
        return self.__create(payload, wait=wait)

    def create_list_in_history(self, history_id, wait=False, **kwds):
        payload = self.create_list_payload(history_id, instance_type="history", **kwds)
        return self.__create(payload, wait=wait)

    def upload_collection(self, history_id, collection_type, elements, wait=False, **kwds):
        payload = self.__create_payload_fetch(history_id, collection_type, contents=elements, **kwds)
        return self.__create(payload, wait=wait)

    def create_list_payload(self, history_id, **kwds):
        return self.__create_payload(history_id, identifiers_func=self.list_identifiers, collection_type="list", **kwds)

    def create_pair_payload(self, history_id, **kwds):
        return self.__create_payload(
            history_id, identifiers_func=self.pair_identifiers, collection_type="paired", **kwds
        )

    def __create_payload(self, *args, **kwds):
        direct_upload = kwds.pop("direct_upload", True)
        if direct_upload:
            return self.__create_payload_fetch(*args, **kwds)
        else:
            return self.__create_payload_collection(*args, **kwds)

    def __create_payload_fetch(self, history_id, collection_type, **kwds):
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

                element = {"src": "pasted", "ext": "txt"}
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

    def __create_payload_collection(self, history_id, identifiers_func, collection_type, **kwds):
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

    def pair_identifiers(self, history_id, contents=None):
        hda1, hda2 = self.__datasets(history_id, count=2, contents=contents)

        element_identifiers = [
            dict(name="forward", src="hda", id=hda1["id"]),
            dict(name="reverse", src="hda", id=hda2["id"]),
        ]
        return element_identifiers

    def list_identifiers(self, history_id, contents=None):
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
        # Create a colleciton - either from existing datasets using collection creation API
        # or from direct uploads with the fetch API. Dispatch on "targets" keyword in payload
        # to decide which to use.
        if "targets" not in payload:
            return self._create_collection(payload)
        else:
            return self.dataset_populator.fetch(payload, wait=wait)

    def __datasets(self, history_id, count, contents=None):
        datasets = []
        for i in range(count):
            new_kwds = {}
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

    def open_test_data(test_dict, mode="rb"):
        test_data_resolver = TestDataResolver()
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
            for element_data in elements_data:
                # Adapt differences between test_data dict and fetch API description.
                if "name" not in element_data:
                    identifier = element_data.pop("identifier")
                    element_data["name"] = identifier
                input_type = element_data.pop("type", "raw")
                content = None
                if input_type == "File":
                    content = read_test_data(element_data)
                else:
                    content = element_data.pop("content")
                if content is not None:
                    element_data["src"] = "pasted"
                    element_data["paste_content"] = content
                elements.append(element_data)
            new_collection_kwds = {}
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
                content = open_test_data(value)
                new_dataset_kwds = {"content": content}
                if "name" in value:
                    new_dataset_kwds["name"] = value["name"]
                if "file_type" in value:
                    new_dataset_kwds["file_type"] = value["file_type"]
                hda = dataset_populator.new_dataset(history_id, wait=True, **new_dataset_kwds)
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
        else:
            raise ValueError(f"Invalid test_data def {test_data}")

    return inputs, label_map, has_uploads


def stage_inputs(
    galaxy_interactor,
    history_id,
    job,
    use_path_paste=True,
    use_fetch_api=True,
    to_posix_lines=True,
    tool_or_workflow="workflow",
    job_dir=None,
):
    """Alternative to load_data_dict that uses production-style workflow inputs."""
    kwds = dict(
        history_id=history_id,
        job=job,
        use_path_paste=use_path_paste,
        to_posix_lines=to_posix_lines,
    )
    if job_dir is not None:
        kwds["job_dir"] = job_dir
    inputs, datasets = InteractorStaging(galaxy_interactor, use_fetch_api=use_fetch_api).stage(tool_or_workflow, **kwds)
    return inputs, datasets


def stage_rules_example(galaxy_interactor, history_id, example):
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
        skip_states = ["running", "queued", "new", "ready", "stop", "stopped", "setting_metadata", "waiting"]
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


class GiHttpMixin:
    """Mixin for adapting Galaxy testing populators helpers to bioblend."""

    _gi: GalaxyClient

    @property
    def _api_key(self):
        return self._gi.key

    def _api_url(self):
        return self._gi.url

    def _get(self, route, data=None, headers=None, admin=False) -> Response:
        if data is None:
            data = {}
        return self._gi.make_get_request(self._url(route), data=data)

    def _post(self, route, data=None, files=None, headers=None, admin=False, json: bool = False) -> Response:
        if data is None:
            data = {}
        data = data.copy()
        data["key"] = self._gi.key
        return requests.post(self._url(route), data=data, headers=headers, timeout=DEFAULT_SOCKET_TIMEOUT)

    def _put(self, route, data=None, headers=None, admin=False, json: bool = False):
        if data is None:
            data = {}
        data = data.copy()
        data["key"] = self._gi.key
        return requests.put(self._url(route), data=data, headers=headers, timeout=DEFAULT_SOCKET_TIMEOUT)

    def _delete(self, route, data=None, headers=None, admin=False, json: bool = False):
        if data is None:
            data = {}
        data = data.copy()
        data["key"] = self._gi.key
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


def wait_on(function: Callable, desc: str, timeout: timeout_type = DEFAULT_TIMEOUT):
    return tool_util_wait_on(function, desc, timeout)
