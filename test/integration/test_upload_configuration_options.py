"""Integration tests various upload aspects.

This file checks upload options that require different non-default Galaxy
configuration options. More vanilla upload options and behaviors are tested
with the API test framework (located in test_tools_upload.py).

These options include:
 - The config options ``check_upload_content`` and ``allow_path_paste``.
 - The upload API parameter ``auto_decompress``.
 - Checking for malicious content in uploads of compressed files.
 - Restricting ``file://`` uploads to admins and allowing them only when
   ``allow_path_paste`` is set to ``True``.
 - Various FTP upload configuration options including:
    - ftp_upload_dir
    - ftp_upload_identifier
    - ftp_upload_dir_template
    - ftp_upload_purge (sort of - seems broken...)
 - Various upload API options tested for url_paste uploads in the API test
   framework but tested here for FTP uploads.
"""

import os
import re
import shutil
import tempfile
from typing import (
    Any,
    Dict,
)

from requests import Response

from galaxy.tool_util.verify.test_data import TestDataResolver
from galaxy.util.unittest import TestCase
from galaxy_test.base.api_util import TEST_USER
from galaxy_test.base.constants import (
    ONE_TO_SIX_ON_WINDOWS,
    ONE_TO_SIX_WITH_SPACES,
    ONE_TO_SIX_WITH_TABS,
)
from galaxy_test.base.populators import (
    DatasetPopulator,
    LibraryPopulator,
    skip_without_datatype,
)
from galaxy_test.driver import integration_util

SCRIPT_DIR = os.path.normpath(os.path.dirname(__file__))
TEST_DATA_DIRECTORY = os.path.join(SCRIPT_DIR, os.pardir, os.pardir, "test-data")


class BaseUploadContentConfigurationIntegrationInstance(integration_util.IntegrationInstance):
    dataset_populator: DatasetPopulator
    framework_tool_and_types = True

    def setUp(self) -> None:
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.library_populator = LibraryPopulator(self.galaxy_interactor)

    def fetch_target(
        self,
        target: Dict[str, Any],
        history_id: str,
        assert_ok: bool = False,
        attach_test_file: bool = False,
        wait: bool = False,
    ) -> Response:
        payload: Dict[str, Any] = {
            "history_id": history_id,
            "targets": [target],
        }
        if attach_test_file:
            payload["__files"] = {"files_0|file_data": open(self.test_data_resolver.get_filename("4.bed"))}

        response = self.dataset_populator.fetch(payload, assert_ok=assert_ok, wait=wait)
        return response


def _write_file(dir_path: str, content: str, filename: str = "test") -> str:
    """Helper for writing ftp/server dir files."""
    _ensure_directory(dir_path)
    path = os.path.join(dir_path, filename)
    with open(path, "w") as f:
        f.write(content)
    return path


def _ensure_directory(path: str) -> None:
    if not os.path.exists(path):
        os.makedirs(path)


class BaseUploadContentConfigurationTestCase(BaseUploadContentConfigurationIntegrationInstance, TestCase):
    pass


class TestInvalidFetchRequests(BaseUploadContentConfigurationTestCase):
    def test_in_place_not_allowed(self, history_id: str) -> None:
        elements = [{"src": "files", "in_place": False}]
        target = {
            "destination": {"type": "hdca"},
            "elements": elements,
            "collection_type": "list",
        }
        response = self.fetch_target(target, history_id, attach_test_file=True)
        self._assert_status_code_is(response, 400)
        assert "in_place" in response.json()["err_msg"]

    def test_files_not_attached(self, history_id: str) -> None:
        elements = [{"src": "files"}]
        target = {
            "destination": {"type": "hdca"},
            "elements": elements,
            "collection_type": "list",
        }
        response = self.fetch_target(target, history_id)
        self._assert_status_code_is(response, 400)
        assert "Failed to find uploaded file matching target" in response.json()["err_msg"]


class TestNonAdminsCannotPasteFilePath(BaseUploadContentConfigurationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        super().handle_galaxy_config_kwds(config)
        config["allow_path_paste"] = True

    def test_disallowed_for_primary_file(self, history_id: str) -> None:
        payload = self.dataset_populator.upload_payload(
            history_id, f"file://{TEST_DATA_DIRECTORY}/1.RData", file_type="binary"
        )
        create_response = self.dataset_populator.tools_post(payload)
        # Ideally this would be 403 but the tool API endpoint isn't using
        # the newer API decorator that handles those details.
        assert create_response.status_code >= 400

    @skip_without_datatype("velvet")
    def test_disallowed_for_composite_file(self, history_id: str) -> None:
        path = os.path.join(TEST_DATA_DIRECTORY, "1.txt")
        assert os.path.exists(path)
        payload = self.dataset_populator.upload_payload(
            history_id,
            "sequences content",
            file_type="velvet",
            extra_inputs={
                "files_1|url_paste": "roadmaps content",
                "files_1|type": "upload_dataset",
                "files_2|url_paste": f"file://{path}",
                "files_2|type": "upload_dataset",
            },
        )
        create_response = self.dataset_populator.tools_post(payload)
        # Ideally this would be 403 but the tool API endpoint isn't using
        # the newer API decorator that handles those details.
        assert create_response.status_code >= 400
        assert os.path.exists(path)

    def test_disallowed_for_libraries(self) -> None:
        path = os.path.join(TEST_DATA_DIRECTORY, "1.txt")
        assert os.path.exists(path)
        library = self.library_populator.new_private_library("pathpastedisallowedlibraries")
        payload, files = self.library_populator.create_dataset_request(
            library, upload_option="upload_paths", paths=path
        )
        response = self.library_populator.raw_library_contents_create(library["id"], payload, files=files)
        assert response.status_code == 403, response.json()
        assert os.path.exists(path)

    def test_disallowed_for_fetch(self, history_id: str) -> None:
        path = os.path.join(TEST_DATA_DIRECTORY, "1.txt")
        assert os.path.exists(path)
        elements = [{"src": "path", "path": path}]
        target = {
            "destination": {"type": "hdca"},
            "elements": elements,
            "collection_type": "list",
        }
        response = self.fetch_target(target, history_id)
        self._assert_status_code_is(response, 403)
        assert os.path.exists(path)

    def test_disallowed_for_fetch_urls(self, history_id: str) -> None:
        path = os.path.join(TEST_DATA_DIRECTORY, "1.txt")
        assert os.path.exists(path)
        elements = [{"src": "url", "url": f"file://{path}"}]
        target = {
            "destination": {"type": "hdca"},
            "elements": elements,
            "collection_type": "list",
        }
        response = self.fetch_target(target, history_id)
        self._assert_status_code_is(response, 403)
        assert os.path.exists(path)


def fetch_link_data_only(
    library_populator: LibraryPopulator, dataset_populator: DatasetPopulator, test_data_resolver: TestDataResolver
):
    history_id, library, destination = library_populator.setup_fetch_to_folder("fetch_and_link")
    bed_test_data_path = test_data_resolver.get_filename("4.bed")
    assert os.path.exists(bed_test_data_path)
    items = [{"src": "path", "path": bed_test_data_path, "info": "my cool bed", "link_data_only": True}]
    targets = [{"destination": destination, "items": items}]
    payload = {
        "history_id": history_id,  # TODO: Shouldn't be needed :(
        "targets": targets,
    }
    dataset_populator.fetch(payload)
    dataset = library_populator.get_library_contents_with_path(library["id"], "/4.bed")
    assert dataset["file_size"] == 61, dataset
    assert dataset["file_name"] == bed_test_data_path, dataset
    assert os.path.exists(bed_test_data_path)


def link_data_only(server_dir: str, library_populator: LibraryPopulator) -> None:
    content = "hello world\n"
    dir_path = os.path.join(server_dir, "lib1")
    file_path = _write_file(dir_path, content)
    library = library_populator.new_private_library("serverdirupload")
    # upload $GALAXY_ROOT/test-data/library
    payload, files = library_populator.create_dataset_request(
        library, upload_option="upload_directory", server_dir="lib1", link_data=True
    )
    response = library_populator.raw_library_contents_create(library["id"], payload, files=files)
    assert response.status_code == 200, response.json()
    dataset = response.json()[0]
    ok_dataset = library_populator.wait_on_library_dataset(library["id"], dataset["id"])
    assert ok_dataset["file_size"] == 12, ok_dataset
    assert ok_dataset["file_name"] == file_path, ok_dataset


class TestAdminsCanPasteFilePaths(BaseUploadContentConfigurationTestCase):
    require_admin_user = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        super().handle_galaxy_config_kwds(config)
        config["allow_path_paste"] = True

    def test_admin_path_paste(self, history_id: str) -> None:
        payload = self.dataset_populator.upload_payload(
            history_id,
            f"file://{TEST_DATA_DIRECTORY}/random-file",
        )
        create_response = self.dataset_populator.tools_post(payload)
        # Is admin - so this should work fine!
        assert create_response.status_code == 200

    def test_admin_path_paste_libraries(self) -> None:
        library = self.library_populator.new_private_library("pathpasteallowedlibraries")
        path = f"{TEST_DATA_DIRECTORY}/1.txt"
        assert os.path.exists(path)
        payload, files = self.library_populator.create_dataset_request(
            library, upload_option="upload_paths", paths=path
        )
        response = self.library_populator.raw_library_contents_create(library["id"], payload, files=files)
        # Was 403 for non-admin above.
        assert response.status_code == 200
        # Test regression where this was getting deleted in this mode.
        assert os.path.exists(path)

    def test_admin_path_paste_libraries_link(self) -> None:
        library = self.library_populator.new_private_library("pathpasteallowedlibraries")
        path = f"{TEST_DATA_DIRECTORY}/1.txt"
        assert os.path.exists(path)
        payload, files = self.library_populator.create_dataset_request(
            library, upload_option="upload_paths", paths=path, link_data=True
        )
        response = self.library_populator.raw_library_contents_create(library["id"], payload, files=files)
        assert response.status_code == 200
        dataset = response.json()[0]
        self.library_populator.wait_on_library_dataset(library["id"], dataset["id"])
        # We should probably verify the linking, but this was enough for now to exhibit
        # https://github.com/galaxyproject/galaxy/issues/8756

    def test_admin_fetch(self, history_id: str) -> None:
        path = os.path.join(TEST_DATA_DIRECTORY, "1.txt")
        elements = [{"src": "path", "path": path}]
        target = {
            "destination": {"type": "hdca"},
            "elements": elements,
            "collection_type": "list",
        }
        response = self.fetch_target(target, history_id)
        self._assert_status_code_is(response, 200)
        assert os.path.exists(path)

    def test_admin_fetch_file_url(self, history_id: str) -> None:
        path = os.path.join(TEST_DATA_DIRECTORY, "1.txt")
        elements = [{"src": "url", "url": f"file://{path}"}]
        target = {
            "destination": {"type": "hdca"},
            "elements": elements,
            "collection_type": "list",
        }
        response = self.fetch_target(target, history_id)
        self._assert_status_code_is(response, 200)
        assert os.path.exists(path)


class TestDefaultBinaryContentFilters(BaseUploadContentConfigurationTestCase):
    require_admin_user = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        super().handle_galaxy_config_kwds(config)
        config["allow_path_paste"] = True

    def test_random_binary_allowed(self, history_id: str) -> None:
        dataset = self.dataset_populator.new_dataset(
            history_id, f"file://{TEST_DATA_DIRECTORY}/random-file", file_type="auto", wait=True
        )
        dataset = self.dataset_populator.get_history_dataset_details(history_id, dataset=dataset)
        assert dataset["file_ext"] == "binary", dataset

    def test_gzipped_html_content_blocked_by_default(self, history_id: str) -> None:
        dataset = self.dataset_populator.new_dataset(
            history_id, f"file://{TEST_DATA_DIRECTORY}/bad.html.gz", file_type="auto", wait=True, assert_ok=False
        )
        dataset = self.dataset_populator.get_history_dataset_details(history_id, dataset=dataset, assert_ok=False)
        assert dataset["file_size"] == 0


class TestDisableContentChecking(BaseUploadContentConfigurationTestCase):
    require_admin_user = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        super().handle_galaxy_config_kwds(config)
        config["allow_path_paste"] = True
        config["check_upload_content"] = False

    def test_gzipped_html_content_now_allowed(self, history_id: str) -> None:
        dataset = self.dataset_populator.new_dataset(
            history_id, f"file://{TEST_DATA_DIRECTORY}/bad.html.gz", file_type="auto", wait=True
        )
        dataset = self.dataset_populator.get_history_dataset_details(history_id, dataset=dataset)
        # Same file was empty above!
        assert dataset["file_size"] != 0


class TestAutoDecompress(BaseUploadContentConfigurationTestCase):
    require_admin_user = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        super().handle_galaxy_config_kwds(config)
        config["allow_path_paste"] = True

    def test_auto_decompress_off(self, history_id: str) -> None:
        dataset = self.dataset_populator.new_dataset(
            history_id,
            f"file://{TEST_DATA_DIRECTORY}/1.sam.gz",
            file_type="auto",
            auto_decompress=False,
            wait=True,
        )
        dataset = self.dataset_populator.get_history_dataset_details(history_id, dataset=dataset)
        assert dataset["file_ext"] == "binary", dataset

    def test_auto_decompress_on(self, history_id: str) -> None:
        dataset = self.dataset_populator.new_dataset(
            history_id, f"file://{TEST_DATA_DIRECTORY}/1.sam.gz", file_type="auto", wait=True
        )
        dataset = self.dataset_populator.get_history_dataset_details(history_id, dataset=dataset)
        assert dataset["file_ext"] == "sam", dataset


class TestLocalAddressWhitelisting(BaseUploadContentConfigurationTestCase):
    def test_blocked_url_for_primary_file(self, history_id: str) -> None:
        payload = self.dataset_populator.upload_payload(history_id, "http://localhost/", file_type="txt")
        create_response = self.dataset_populator.tools_post(payload)
        # Ideally this would be 403 but the tool API endpoint isn't using
        # the newer API decorator that handles those details.
        assert create_response.status_code >= 400

    @skip_without_datatype("velvet")
    def test_blocked_url_for_composite_file(self, history_id: str) -> None:
        payload = self.dataset_populator.upload_payload(
            history_id,
            "sequences content",
            file_type="velvet",
            extra_inputs={
                "files_1|url_paste": "roadmaps content",
                "files_1|type": "upload_dataset",
                "files_2|url_paste": "http://localhost/",
                "files_2|type": "upload_dataset",
            },
        )
        create_response = self.dataset_populator.tools_post(payload)
        # Ideally this would be 403 but the tool API endpoint isn't using
        # the newer API decorator that handles those details.
        assert create_response.status_code >= 400

    def test_blocked_url_for_fetch(self, history_id: str) -> None:
        elements = [{"src": "url", "url": "http://localhost"}]
        target = {
            "destination": {"type": "hdca"},
            "elements": elements,
            "collection_type": "list",
        }
        response = self.fetch_target(target, history_id)
        self._assert_status_code_is(response, 403)


class BaseFtpUploadConfigurationTestCase(BaseUploadContentConfigurationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        super().handle_galaxy_config_kwds(config)
        ftp_dir = cls.ftp_dir()
        os.makedirs(ftp_dir)
        config["ftp_upload_dir"] = ftp_dir
        cls.handle_extra_ftp_config(config)

    @classmethod
    def handle_extra_ftp_config(cls, config: Dict[str, Any]) -> None:
        """Overrride to specify additional FTP configuration options."""

    @classmethod
    def ftp_dir(cls) -> str:
        return cls.temp_config_dir("ftp")

    def _check_content(self, dataset: Dict[str, Any], content: str, history_id: str, ext: str = "txt") -> None:
        dataset = self.dataset_populator.get_history_dataset_details(history_id, dataset=dataset)
        assert dataset["file_ext"] == ext, dataset
        content = self.dataset_populator.get_history_dataset_content(history_id, dataset=dataset)
        assert content == content, content

    def _get_user_ftp_path(self) -> str:
        return os.path.join(self.ftp_dir(), TEST_USER)

    def _write_ftp_file(self, content: str, filename: str = "test") -> str:
        dir_path = self._get_user_ftp_path()
        self._ensure_directory(dir_path)
        path = os.path.join(dir_path, filename)
        with open(path, "w") as f:
            f.write(content)
        return path

    def _ensure_directory(self, path: str) -> None:
        if not os.path.exists(path):
            os.makedirs(path)

    def _run_purgable_upload(self, history_id: str) -> str:
        # Purge setting is actually used with a fairly specific set of parameters - see:
        # https://github.com/galaxyproject/galaxy/issues/5361
        content = "hello world\n"
        ftp_path = self._write_ftp_file(content)
        ftp_files = self.dataset_populator.get_remote_files()
        assert len(ftp_files) == 1
        assert ftp_files[0]["path"] == "test"
        assert os.path.exists(ftp_path)
        # gotta set to_posix_lines to None currently to force purging of non-binary data.
        dataset = self.dataset_populator.new_dataset(
            history_id, ftp_files="test", file_type="txt", to_posix_lines=None, wait=True
        )
        self._check_content(dataset, content, history_id)
        return ftp_path


class TestSimpleFtpUploadConfiguration(BaseFtpUploadConfigurationTestCase):
    def test_ftp_upload(self, history_id: str) -> None:
        content = "hello world\n"
        ftp_path = self._write_ftp_file(content)
        ftp_files = self.dataset_populator.get_remote_files()
        assert len(ftp_files) == 1, ftp_files
        assert ftp_files[0]["path"] == "test"
        assert os.path.exists(ftp_path)
        # set to_posix_lines to False to exercise purging - by default this file type wouldn't
        # be purged.
        dataset = self.dataset_populator.new_dataset(
            history_id, ftp_files="test", file_type="txt", to_posix_lines=False, wait=True
        )
        self._check_content(dataset, content, history_id)

    def test_ftp_fetch(self, history_id: str) -> None:
        content = "hello world\n"
        ftp_path = self._write_ftp_file(content)
        ftp_files = self.dataset_populator.get_remote_files()
        assert len(ftp_files) == 1, ftp_files
        assert ftp_files[0]["path"] == "test"
        assert os.path.exists(ftp_path)
        elements = [{"src": "ftp_import", "ftp_path": ftp_files[0]["path"]}]
        target = {
            "destination": {"type": "hdca"},
            "elements": elements,
            "collection_type": "list",
            "name": "cool collection",
        }
        response = self.fetch_target(target, history_id, assert_ok=True, wait=True)
        response_object = response.json()
        assert "output_collections" in response_object
        output_collections = response_object["output_collections"]
        assert len(output_collections) == 1, response_object
        dataset = self.dataset_populator.get_history_dataset_details(history_id, hid=2)
        self._check_content(dataset, content, history_id)


class TestExplicitEmailAsIdentifierFtpUploadConfiguration(TestSimpleFtpUploadConfiguration):
    @classmethod
    def handle_extra_ftp_config(cls, config) -> None:
        config["ftp_upload_dir_identifier"] = "email"


class TestPerUsernameFtpUploadConfiguration(TestSimpleFtpUploadConfiguration):
    @classmethod
    def handle_extra_ftp_config(cls, config) -> None:
        config["ftp_upload_dir_identifier"] = "username"

    def _get_user_ftp_path(self) -> str:
        username = re.sub("[^a-z-]", "--", TEST_USER.lower())
        return os.path.join(self.ftp_dir(), username)


class TestTemplatedFtpDirectoryUploadConfiguration(TestSimpleFtpUploadConfiguration):
    @classmethod
    def handle_extra_ftp_config(cls, config) -> None:
        config["ftp_upload_dir_template"] = "${ftp_upload_dir}/moo_${ftp_upload_dir_identifier}_cow"

    def _get_user_ftp_path(self) -> str:
        return os.path.join(self.ftp_dir(), f"moo_{TEST_USER}_cow")


class TestDisableFtpPurgeUploadConfiguration(BaseFtpUploadConfigurationTestCase):
    @classmethod
    def handle_extra_ftp_config(cls, config) -> None:
        config["ftp_upload_purge"] = "False"

    def test_ftp_uploads_not_purged(self, history_id: str) -> None:
        ftp_path = self._run_purgable_upload(history_id)
        # Purge is disabled, this better still be here.
        assert os.path.exists(ftp_path)


class TestEnableFtpPurgeUploadConfiguration(BaseFtpUploadConfigurationTestCase):
    @classmethod
    def handle_extra_ftp_config(cls, config) -> None:
        config["ftp_upload_purge"] = "True"

    def test_ftp_uploads_not_purged(self, history_id: str) -> None:
        ftp_path = self._run_purgable_upload(history_id)
        assert not os.path.exists(ftp_path)


class TestAdvancedFtpUploadFetch(BaseFtpUploadConfigurationTestCase):
    def test_fetch_ftp_directory(self, history_id: str) -> None:
        dir_path = self._get_user_ftp_path()
        _write_file(os.path.join(dir_path, "subdir"), "content 1", filename="1")
        _write_file(os.path.join(dir_path, "subdir"), "content 22", filename="2")
        _write_file(os.path.join(dir_path, "subdir"), "content 333", filename="3")
        target = {
            "destination": {"type": "hdca"},
            "elements_from": "directory",
            "src": "ftp_import",
            "ftp_path": "subdir",
            "collection_type": "list",
        }
        self.fetch_target(target, history_id, assert_ok=True, wait=True)
        hdca = self.dataset_populator.get_history_collection_details(history_id, hid=1)
        assert len(hdca["elements"]) == 3, hdca
        element0 = hdca["elements"][0]
        assert element0["element_identifier"] == "1", hdca
        assert element0["object"]["file_size"] == 9, element0

    def test_fetch_nested_elements_from(self, history_id: str) -> None:
        dir_path = self._get_user_ftp_path()
        _write_file(os.path.join(dir_path, "subdir1"), "content 1", filename="1")
        _write_file(os.path.join(dir_path, "subdir1"), "content 22", filename="2")
        _write_file(os.path.join(dir_path, "subdir2"), "content 333", filename="3")
        elements = [
            {
                "name": "subdirel1",
                "src": "ftp_import",
                "ftp_path": "subdir1",
                "elements_from": "directory",
                "collection_type": "list",
            },
            {
                "name": "subdirel2",
                "src": "ftp_import",
                "ftp_path": "subdir2",
                "elements_from": "directory",
                "collection_type": "list",
            },
        ]
        target = {
            "destination": {"type": "hdca"},
            "elements": elements,
            "collection_type": "list:list",
        }
        self.fetch_target(target, history_id, assert_ok=True, wait=True)
        hdca = self.dataset_populator.get_history_collection_details(
            history_id, history_content_type="dataset_collection"
        )
        assert len(hdca["elements"]) == 2, hdca
        element0 = hdca["elements"][0]
        assert element0["element_identifier"] == "subdirel1"


class TestUploadOptionsFtpUploadConfiguration(BaseFtpUploadConfigurationTestCase):
    def test_upload_api_option_space_to_tab(self, history_id: str) -> None:
        self._write_user_ftp_file("0.txt", ONE_TO_SIX_WITH_SPACES)
        self._write_user_ftp_file("1.txt", ONE_TO_SIX_WITH_SPACES)
        self._write_user_ftp_file("2.txt", ONE_TO_SIX_WITH_SPACES)

        payload = self.dataset_populator.upload_payload(
            history_id,
            ftp_files="0.txt",
            file_type="tabular",
            dbkey="hg19",
            extra_inputs={
                "files_0|file_type": "txt",
                "files_0|space_to_tab": "Yes",
                "files_1|ftp_files": "1.txt",
                "files_1|NAME": "SecondOutputName",
                "files_1|file_type": "txt",
                "files_2|ftp_files": "2.txt",
                "files_2|NAME": "ThirdOutputName",
                "files_2|file_type": "txt",
                "files_2|space_to_tab": "Yes",
                "file_count": "3",
            },
        )
        run_response = self.dataset_populator.tools_post(payload)
        self.dataset_populator.wait_for_tool_run(history_id, run_response)
        datasets = run_response.json()["outputs"]

        assert len(datasets) == 3, datasets
        content = self.dataset_populator.get_history_dataset_content(history_id, dataset=datasets[0])
        assert content == ONE_TO_SIX_WITH_TABS

        content = self.dataset_populator.get_history_dataset_content(history_id, dataset=datasets[1])
        assert content == ONE_TO_SIX_WITH_SPACES

        content = self.dataset_populator.get_history_dataset_content(history_id, dataset=datasets[2])
        assert content == ONE_TO_SIX_WITH_TABS

    def test_upload_api_option_to_posix_lines(self, history_id: str) -> None:
        self._write_user_ftp_file("0.txt", ONE_TO_SIX_ON_WINDOWS)
        self._write_user_ftp_file("1.txt", ONE_TO_SIX_ON_WINDOWS)
        self._write_user_ftp_file("2.txt", ONE_TO_SIX_ON_WINDOWS)

        payload = self.dataset_populator.upload_payload(
            history_id,
            ftp_files="0.txt",
            file_type="tabular",
            dbkey="hg19",
            extra_inputs={
                "files_0|file_type": "txt",
                "files_0|to_posix_lines": "Yes",
                "files_1|ftp_files": "1.txt",
                "files_1|NAME": "SecondOutputName",
                "files_1|file_type": "txt",
                "files_1|to_posix_lines": None,
                "files_2|ftp_files": "2.txt",
                "files_2|NAME": "ThirdOutputName",
                "files_2|file_type": "txt",
                "file_count": "3",
            },
        )
        run_response = self.dataset_populator.tools_post(payload)
        self.dataset_populator.wait_for_tool_run(history_id, run_response)
        datasets = run_response.json()["outputs"]

        assert len(datasets) == 3, datasets
        content = self.dataset_populator.get_history_dataset_content(history_id, dataset=datasets[0])
        assert content == ONE_TO_SIX_WITH_TABS

        content = self.dataset_populator.get_history_dataset_content(history_id, dataset=datasets[1])
        assert content == ONE_TO_SIX_ON_WINDOWS

        content = self.dataset_populator.get_history_dataset_content(history_id, dataset=datasets[2])
        assert content == ONE_TO_SIX_WITH_TABS

    def test_upload_option_auto_decompress_default(self, history_id: str) -> None:
        self._copy_to_user_ftp_file("1.sam.gz")
        payload = self.dataset_populator.upload_payload(
            history_id,
            ftp_files="1.sam.gz",
            file_type="auto",
        )
        run_response = self.dataset_populator.tools_post(payload)
        self.dataset_populator.wait_for_tool_run(history_id, run_response)
        datasets = run_response.json()["outputs"]
        dataset = self.dataset_populator.get_history_dataset_details(history_id, dataset=datasets[0])
        assert dataset["file_ext"] == "sam", dataset

    def test_upload_option_auto_decompress_off(self, history_id: str) -> None:
        self._copy_to_user_ftp_file("1.sam.gz")
        payload = self.dataset_populator.upload_payload(
            history_id,
            ftp_files="1.sam.gz",
            file_type="auto",
            auto_decompress=False,
        )
        run_response = self.dataset_populator.tools_post(payload)
        self.dataset_populator.wait_for_tool_run(history_id, run_response)
        datasets = run_response.json()["outputs"]
        dataset = self.dataset_populator.get_history_dataset_details(history_id, dataset=datasets[0])
        assert dataset["file_ext"] != "sam", dataset

    def _copy_to_user_ftp_file(self, test_data_path: str) -> None:
        input_path = os.path.join(TEST_DATA_DIRECTORY, test_data_path)
        target_dir = os.path.join(self.ftp_dir(), TEST_USER)
        self._ensure_directory(target_dir)
        shutil.copyfile(input_path, os.path.join(target_dir, test_data_path))

    def _write_user_ftp_file(self, path: str, content: str) -> str:
        return _write_file(os.path.join(self.ftp_dir(), TEST_USER), content, filename=path)


class TestServerDirectoryOffByDefault(BaseUploadContentConfigurationTestCase):
    require_admin_user = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        super().handle_galaxy_config_kwds(config)
        config["library_import_dir"] = None

    def test_server_dir_uploads_403_if_dir_not_set(self) -> None:
        library = self.library_populator.new_private_library("serverdiroffbydefault")
        payload, files = self.library_populator.create_dataset_request(
            library, upload_option="upload_directory", server_dir="foobar"
        )
        response = self.library_populator.raw_library_contents_create(library["id"], payload, files=files)
        assert response.status_code == 403, response.json()
        assert '"library_import_dir" is not set' in response.json()["err_msg"]


class TestServerDirectoryValidUsage(BaseUploadContentConfigurationTestCase):
    # This tests the library contents API - I think equivalent functionality is available via library datasets API
    # and should also be tested.

    require_admin_user = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        super().handle_galaxy_config_kwds(config)
        server_dir = cls.server_dir()
        os.makedirs(server_dir)
        config["library_import_dir"] = server_dir

    def test_valid_server_dir_uploads_okay(self) -> None:
        dir_to_import = "library"
        full_dir_path = os.path.join(self.server_dir(), dir_to_import)
        os.makedirs(full_dir_path)
        file_content = "hello world\n"
        with tempfile.NamedTemporaryFile(mode="w", dir=full_dir_path, delete=False) as fh:
            fh.write(file_content)
            file_to_import = fh.name

        library_dataset = self.library_populator.new_library_dataset(
            "serverdirupload", upload_option="upload_directory", server_dir=dir_to_import
        )
        # Check the file is still there and was not modified
        with open(file_to_import) as fh:
            read_content = fh.read()
        assert read_content == file_content

        assert library_dataset["file_size"] == 12, library_dataset

    def test_link_data_only(self) -> None:
        link_data_only(self.server_dir(), self.library_populator)

    @classmethod
    def server_dir(cls) -> str:
        return cls.temp_config_dir("server")


class TestUserServerDirectoryOffByDefault(BaseUploadContentConfigurationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        super().handle_galaxy_config_kwds(config)
        config["user_library_import_dir"] = None

    def test_library_import_dir_not_available_to_non_admins(self) -> None:
        # same test case above works for admins
        library = self.library_populator.new_private_library("serverdirupload")
        payload, files = self.library_populator.create_dataset_request(
            library, upload_option="upload_directory", server_dir="library"
        )
        response = self.library_populator.raw_library_contents_create(library["id"], payload, files=files)
        assert response.status_code == 403, response.json()


class TestUserServerDirectoryValidUsage(BaseUploadContentConfigurationTestCase):
    @classmethod
    def user_server_dir(cls) -> str:
        return cls.temp_config_dir("user_library_import_dir")

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        super().handle_galaxy_config_kwds(config)
        user_server_dir = cls.user_server_dir()
        os.makedirs(user_server_dir)
        config["user_library_import_dir"] = os.path.join(user_server_dir)

    def test_valid_user_server_dir_uploads_okay(self) -> None:
        dir_to_import = "library"
        full_dir_path = os.path.join(self.user_server_dir(), TEST_USER, dir_to_import)
        os.makedirs(full_dir_path)
        file_content = "hello world\n"
        with tempfile.NamedTemporaryFile(mode="w", dir=full_dir_path, delete=False) as fh:
            fh.write(file_content)
            file_to_import = fh.name

        library_dataset = self.library_populator.new_library_dataset(
            "serverdirupload", upload_option="upload_directory", server_dir=dir_to_import
        )
        # Check the file is still there and was not modified
        with open(file_to_import) as fh:
            read_content = fh.read()
        assert read_content == file_content

        assert library_dataset["file_size"] == 12, library_dataset


class TestFetchByPath(BaseUploadContentConfigurationTestCase):
    require_admin_user = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        super().handle_galaxy_config_kwds(config)
        config["allow_path_paste"] = True

    def test_fetch_path_to_folder(self) -> None:
        history_id, library, destination = self.library_populator.setup_fetch_to_folder("simple_fetch")
        bed_test_data_path = self.test_data_resolver.get_filename("4.bed")
        assert os.path.exists(bed_test_data_path)
        items = [{"src": "path", "path": bed_test_data_path, "info": "my cool bed"}]
        targets = [{"destination": destination, "items": items}]
        payload = {
            "history_id": history_id,  # TODO: Shouldn't be needed :(
            "targets": targets,
        }
        self.dataset_populator.fetch(payload)
        dataset = self.library_populator.get_library_contents_with_path(library["id"], "/4.bed")
        assert dataset["file_size"] == 61, dataset
        assert os.path.exists(bed_test_data_path)

    def test_fetch_link_data_only(self) -> None:
        fetch_link_data_only(self.library_populator, self.dataset_populator, self.test_data_resolver)

    def test_fetch_recursive_archive(self) -> None:
        history_id, library, destination = self.library_populator.setup_fetch_to_folder("recursive_archive")
        archive_test_data_path = self.test_data_resolver.get_filename("testdir1.zip")
        targets = [
            {
                "destination": destination,
                "items_from": "archive",
                "src": "path",
                "path": archive_test_data_path,
            }
        ]
        payload = {
            "history_id": history_id,  # TODO: Shouldn't be needed :(
            "targets": targets,
        }
        self.dataset_populator.fetch(payload)
        dataset = self.library_populator.get_library_contents_with_path(library["id"], "/file1")
        assert dataset["file_size"] == 6, dataset

        dataset = self.library_populator.get_library_contents_with_path(library["id"], "/file2")
        assert dataset["file_size"] == 6, dataset

        dataset = self.library_populator.get_library_contents_with_path(library["id"], "/dir1/file3")
        assert dataset["file_size"] == 11, dataset

    def test_fetch_history_compressed_type(self, history_id: str) -> None:
        destination = {"type": "hdas"}
        archive = self.test_data_resolver.get_filename("1.fastqsanger.gz")
        targets = [
            {
                "destination": destination,
                "items": [{"src": "path", "path": archive, "ext": "fastqsanger.gz"}],
            }
        ]
        payload = {
            "history_id": history_id,  # TODO: Shouldn't be needed :(
            "targets": targets,
        }
        fetch_response = self.dataset_populator.fetch(payload)
        self._assert_status_code_is(fetch_response, 200)
        outputs = fetch_response.json()["outputs"]
        assert len(outputs) == 1
        output = outputs[0]
        assert output["name"] == "1.fastqsanger.gz"
        contents_response = self.dataset_populator._get_contents_request(history_id)
        assert contents_response.status_code == 200
        contents = contents_response.json()
        assert len(contents) == 1, contents
        assert contents[0]["extension"] == "fastqsanger.gz", contents[0]
        assert contents[0]["name"] == "1.fastqsanger.gz", contents[0]
        assert contents[0]["hid"] == 1, contents[0]

    def test_fetch_recursive_archive_history(self, history_id: str) -> None:
        destination = {"type": "hdas"}
        archive = self.test_data_resolver.get_filename("testdir1.zip")
        targets = [
            {
                "destination": destination,
                "items_from": "archive",
                "src": "path",
                "path": archive,
            }
        ]
        payload = {
            "history_id": history_id,  # TODO: Shouldn't be needed :(
            "targets": targets,
        }
        self.dataset_populator.fetch(payload)
        contents_response = self.dataset_populator._get_contents_request(history_id)
        assert contents_response.status_code == 200
        contents = contents_response.json()
        assert len(contents) == 3

    def test_fetch_recursive_archive_to_library(self, history_id: str) -> None:
        bed_test_data_path = self.test_data_resolver.get_filename("testdir1.zip")
        targets = [
            {
                "destination": {"type": "library", "name": "My Cool Library"},
                "items_from": "archive",
                "src": "path",
                "path": bed_test_data_path,
            }
        ]
        payload = {
            "history_id": history_id,  # TODO: Shouldn't be needed :(
            "targets": targets,
        }
        self.dataset_populator.fetch(payload)
        libraries = self.library_populator.get_libraries()
        matching = [library for library in libraries if library["name"] == "My Cool Library"]
        assert len(matching) == 1
        library = matching[0]
        dataset = self.library_populator.get_library_contents_with_path(library["id"], "/file1")
        assert dataset["file_size"] == 6, dataset


class TestDirectoryAndCompressedTypes(BaseUploadContentConfigurationTestCase):
    require_admin_user = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        super().handle_galaxy_config_kwds(config)
        config["allow_path_paste"] = True

    def test_tar_to_directory(self, history_id: str) -> None:
        dataset = self.dataset_populator.new_dataset(
            history_id,
            f"file://{TEST_DATA_DIRECTORY}/testdir.tar",
            file_type="tar",
            auto_decompress=False,
            wait=True,
        )
        dataset = self.dataset_populator.get_history_dataset_details(history_id, dataset=dataset)
        assert dataset["file_ext"] == "tar", dataset
        response = self.dataset_populator.run_tool(
            tool_id="CONVERTER_tar_to_directory",
            inputs={"input1": {"src": "hda", "id": dataset["id"]}},
            history_id=history_id,
        )
        self.dataset_populator.wait_for_job(response["jobs"][0]["id"])


class TestLinkDataUploadExtendedMetadata(BaseUploadContentConfigurationTestCase):
    require_admin_user = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        super().handle_galaxy_config_kwds(config)
        config["allow_path_paste"] = True
        config["metadata_strategy"] = "extended"
        server_dir = cls.server_dir()
        os.makedirs(server_dir)
        config["library_import_dir"] = server_dir

    @classmethod
    def server_dir(cls) -> str:
        return cls.temp_config_dir("server")

    def test_fetch_link_data_only(self) -> None:
        fetch_link_data_only(self.library_populator, self.dataset_populator, self.test_data_resolver)

    def test_link_data_only(self) -> None:
        link_data_only(self.server_dir(), self.library_populator)
