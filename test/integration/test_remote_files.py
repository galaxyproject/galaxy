import operator
import os
import shutil
from tempfile import mkdtemp
from typing import ClassVar
from unittest import SkipTest
from urllib.parse import urlparse

from galaxy.exceptions import error_codes
from galaxy_test.base.api_asserts import (
    assert_error_code_is,
    assert_error_message_contains,
)
from galaxy_test.base.populators import (
    DatasetCollectionPopulator,
    DatasetPopulator,
)
from galaxy_test.driver import integration_util

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
FILE_SOURCES_JOB_CONF = os.path.join(SCRIPT_DIRECTORY, "file_sources_conf_remote_files.yml")
VCF_GZ_PATH = os.path.join(SCRIPT_DIRECTORY, os.path.pardir, os.path.pardir, "test-data", "test.vcf.gz")

USERNAME = "user--bx--psu--edu"
USER_EMAIL = "user@bx.psu.edu"


class ConfiguresRemoteFilesIntegrationTestCase(integration_util.IntegrationTestCase):
    dataset_populator: DatasetPopulator
    library_dir: ClassVar[str]
    user_library_dir: ClassVar[str]
    ftp_upload_dir: ClassVar[str]
    root: ClassVar[str]

    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        root = os.path.realpath(mkdtemp())
        cls._test_driver.temp_directories.append(root)
        cls.root = root
        cls.library_dir = os.path.join(root, "library")
        cls.user_library_dir = os.path.join(root, "user_library")
        cls.ftp_upload_dir = os.path.join(root, "ftp")
        config["library_import_dir"] = cls.library_dir
        config["user_library_import_dir"] = cls.user_library_dir
        config["ftp_upload_dir"] = cls.ftp_upload_dir
        config["ftp_upload_site"] = "ftp://cow.com"
        # driver_util sets this to False, though the Galaxy default is True.
        # Restore default for these tests.
        config["ftp_upload_purge"] = True
        config["metadata_strategy"] = "extended"
        config["tool_evaluation_strategy"] = "remote"
        config["file_sources_config_file"] = FILE_SOURCES_JOB_CONF

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.dataset_collection_populator = DatasetCollectionPopulator(self.galaxy_interactor)

        for d in [self.library_dir, self.user_library_dir, self.ftp_upload_dir]:
            if os.path.exists(d):
                shutil.rmtree(d)
            os.mkdir(d)

    @property
    def user_ftp_dir(self):
        ftp_dir = os.path.join(self.ftp_upload_dir, USER_EMAIL)
        if not os.path.exists(ftp_dir):
            os.mkdir(ftp_dir)
        return ftp_dir


class TestRemoteFilesIntegration(ConfiguresRemoteFilesIntegrationTestCase):
    def test_index(self):
        index = self.galaxy_interactor.get("remote_files?target=importdir").json()
        self._assert_index_empty(index)

        _write_file_fixtures(self.root, self.library_dir)
        index = self.galaxy_interactor.get("remote_files?target=importdir").json()
        self._assert_index_matches_fixtures(index)

        # Get a 404 if the directory doesn't exist.
        index = self.galaxy_interactor.get("remote_files?target=userdir").json()
        assert_error_code_is(index, error_codes.error_codes_by_name["USER_OBJECT_NOT_FOUND"])

        users_dir = os.path.join(self.user_library_dir, USER_EMAIL)
        os.mkdir(users_dir)

        index = self.galaxy_interactor.get("remote_files?target=userdir").json()
        self._assert_index_empty(index)

        _write_file_fixtures(self.root, users_dir)

        index = self.galaxy_interactor.get("remote_files?target=userdir").json()
        self._assert_index_matches_fixtures(index)

        index = self.galaxy_interactor.get("remote_files?target=userdir&format=jstree").json()
        self._assert_index_matches_fixtures_jstree(index)

    def test_fetch_from_import(self):
        _write_file_fixtures(self.root, self.library_dir)
        with self.dataset_populator.test_history() as history_id:
            element = dict(src="url", url="gximport://a")
            target = {
                "destination": {"type": "hdas"},
                "elements": [element],
            }
            targets = [target]
            payload = {
                "history_id": history_id,
                "targets": targets,
            }
            new_dataset = self.dataset_populator.fetch(payload, assert_ok=True).json()["outputs"][0]
            content = self.dataset_populator.get_history_dataset_content(history_id, dataset=new_dataset)
            assert content == "a\n", content

        assert os.path.exists(os.path.join(self.library_dir, "a"))

    def test_fetch_from_drs(self):
        CONTENT = "a\n"
        history_id = self.dataset_populator.new_history()

        def create_drs_object():
            hda = self.dataset_populator.new_dataset(history_id, content=CONTENT, wait=True)
            # Force the md5 hash to be evaluated. Otherwise, the DRS endpoint will attempt to dispatch an md5
            # task and returns a 204 Try Later. This will cause a timeout in a test environment without multiple
            # celery workers, so we forcibly compute the hash.
            self.dataset_populator.compute_hash(hda["id"])
            drs_id = hda["drs_id"]
            components = urlparse(self.url)
            netloc = components.netloc
            if components.path != "/":
                raise SkipTest("Real DRS cannot be served on Galaxy not hosted at root.")
            drs_uri = f"drs://{netloc}/{drs_id}"
            return drs_uri

        # Upload a dataset to Galaxy, which will be available over DRS
        drs_url = create_drs_object()
        # Download the created DRS object to check drs url handling
        element = dict(src="url", url=drs_url)
        target = {
            "destination": {"type": "hdas"},
            "elements": [element],
        }
        targets = [target]
        payload = {
            "history_id": history_id,
            "targets": targets,
        }
        new_dataset = self.dataset_populator.fetch(payload, assert_ok=True).json()["outputs"][0]
        content = self.dataset_populator.get_history_dataset_content(history_id, dataset=new_dataset)
        assert content == CONTENT, content

    def test_fetch_from_ftp(self):
        ftp_dir = self.user_ftp_dir
        _write_file_fixtures(self.root, ftp_dir)
        with self.dataset_populator.test_history() as history_id:
            element = dict(src="url", url="gxftp://a")
            target = {
                "destination": {"type": "hdas"},
                "elements": [element],
            }
            targets = [target]
            payload = {
                "history_id": history_id,
                "targets": targets,
            }
            new_dataset = self.dataset_populator.fetch(payload, assert_ok=True).json()["outputs"][0]
            content = self.dataset_populator.get_history_dataset_content(history_id, dataset=new_dataset)
            assert content == "a\n", content

        assert not os.path.exists(os.path.join(ftp_dir, "a"))

    def test_write_to_files(self):
        dataset_populator = self.dataset_populator
        ftp_dir = self.user_ftp_dir
        _write_file_fixtures(self.root, ftp_dir)
        with dataset_populator.test_history() as history_id:
            inputs = {
                "d_uri": "gxftp://",
            }
            response = dataset_populator.run_tool("directory_uri", inputs, history_id)
            dataset_populator.wait_for_job(response["jobs"][0]["id"])
            assert "helloworld" in os.listdir(ftp_dir)
            with open(os.path.join(ftp_dir, "helloworld")) as f:
                assert "hello world!\n" == f.read()

    def test_export_remote_tool_default(self):
        dataset_populator = self.dataset_populator
        ftp_dir = self.user_ftp_dir
        _write_file_fixtures(self.root, ftp_dir)
        with dataset_populator.test_history() as history_id:
            dataset = dataset_populator.new_dataset(history_id, content="example content", wait=True, name="foo")
            infile = {"src": "hda", "id": dataset["id"]}
            inputs = {
                "d_uri": "gxftp://",
                "export_type|export_type_selector": "datasets_named",
                "export_type|datasets_0|infile": infile,
                "export_type|datasets_0|name": ".my_cool/utf8_name_😻.txt",
            }
            response = dataset_populator.run_tool("export_remote", inputs, history_id)
            dataset_populator.wait_for_job(response["jobs"][0]["id"], assert_ok=True)
            with open(os.path.join(ftp_dir, "my_cool", "utf8_name_😻.txt")) as f:
                assert "example content\n" == f.read()

    def test_export_remote_tool_with_space(self):
        dataset_populator = self.dataset_populator
        ftp_dir = self.user_ftp_dir
        _write_file_fixtures(self.root, ftp_dir)
        dir_with_space = os.path.join(ftp_dir, "space dir")
        os.makedirs(dir_with_space)
        with dataset_populator.test_history() as history_id:
            dataset = dataset_populator.new_dataset(history_id, content="example content", wait=True, name="foo")
            infile = {"src": "hda", "id": dataset["id"]}
            inputs = {
                "d_uri": "gxftp://space dir/",
                "export_type|export_type_selector": "datasets_named",
                "export_type|datasets_0|infile": infile,
                "export_type|datasets_0|name": ".my_cool/utf8_name_😻.txt",
            }
            response = dataset_populator.run_tool("export_remote", inputs, history_id)
            dataset_populator.wait_for_job(response["jobs"][0]["id"], assert_ok=True)
            with open(os.path.join(ftp_dir, "space dir", "my_cool", "utf8_name_😻.txt")) as f:
                assert "example content\n" == f.read()

    def test_export_remote_tool_with_space_encoded(self):
        dataset_populator = self.dataset_populator
        ftp_dir = self.user_ftp_dir
        _write_file_fixtures(self.root, ftp_dir)
        dir_with_space = os.path.join(ftp_dir, "space%20dir")
        os.makedirs(dir_with_space)
        with dataset_populator.test_history() as history_id:
            dataset = dataset_populator.new_dataset(history_id, content="example content", wait=True, name="foo")
            infile = {"src": "hda", "id": dataset["id"]}
            inputs = {
                "d_uri": "gxftp://space%20dir/",
                "export_type|export_type_selector": "datasets_named",
                "export_type|datasets_0|infile": infile,
                "export_type|datasets_0|name": ".my_cool/utf8_name_😻.txt",
            }
            response = dataset_populator.run_tool("export_remote", inputs, history_id)
            dataset_populator.wait_for_job(response["jobs"][0]["id"], assert_ok=True)
            with open(os.path.join(ftp_dir, "space%20dir", "my_cool", "utf8_name_😻.txt")) as f:
                assert "example content\n" == f.read()

    def test_export_remote_tool_default_duplicate_name_fails(self):
        dataset_populator = self.dataset_populator
        ftp_dir = self.user_ftp_dir
        _write_file_fixtures(self.root, ftp_dir)
        with dataset_populator.test_history() as history_id:
            dataset = dataset_populator.new_dataset(history_id, content="example content", wait=True, name="foo")
            infile = {"src": "hda", "id": dataset["id"]}
            inputs = {
                "d_uri": "gxftp://",
                "export_type|export_type_selector": "datasets_named",
                "export_type|datasets_0|infile": infile,
                "export_type|datasets_0|name": "name.txt",
                "export_type|datasets_1|infile": infile,
                "export_type|datasets_1|name": "name.txt",
            }
            response = dataset_populator.run_tool("export_remote", inputs, history_id)
            job_id = response["jobs"][0]["id"]
            dataset_populator.wait_for_job(job_id, assert_ok=False)
            job = self.dataset_populator.get_job_details(job_id, full=True).json()
            assert job["state"] == "error"
            assert "Duplicate export filenames given" in job["tool_stderr"]
            assert not os.path.exists(os.path.join(ftp_dir, "name.txt"))

    def test_export_remote_tool_with_metadata_file_auto_name(self):
        dataset_populator = self.dataset_populator
        ftp_dir = self.user_ftp_dir
        _write_file_fixtures(self.root, ftp_dir)
        with dataset_populator.test_history() as history_id:
            with open(VCF_GZ_PATH, "rb") as vcf_gz:
                dataset = dataset_populator.new_dataset(
                    history_id, content=vcf_gz, file_type="vcf_bgzip", wait=True, name="foo/1"
                )
            infile = {"src": "hda", "id": dataset["id"]}
            inputs = {
                "d_uri": "gxftp://",
                "export_type|export_type_selector": "datasets_auto",
                "export_type|infiles": [infile],
            }
            response = dataset_populator.run_tool("export_remote", inputs, history_id)
            dataset_populator.wait_for_job(response["jobs"][0]["id"], assert_ok=True)
            with open(os.path.join(ftp_dir, "foo_1.vcf.gz"), "rb") as export, open(VCF_GZ_PATH, "rb") as vcf_gz:
                assert export.read() == vcf_gz.read()
            assert os.path.exists(os.path.join(ftp_dir, "foo_1.vcf.gz.tbi"))

    def test_export_remote_tool_collection_structure(self):
        dataset_populator = self.dataset_populator
        ftp_dir = self.user_ftp_dir
        assert "test0" not in os.listdir(ftp_dir)
        _write_file_fixtures(self.root, ftp_dir)
        with dataset_populator.test_history() as history_id:
            hdca = self.dataset_collection_populator.create_list_of_list_in_history(history_id, wait=True).json()
            outer_elements = hdca["elements"][0]
            assert outer_elements["element_identifier"] == "test0"
            for i in range(2):
                assert outer_elements["object"]["elements"][i]["element_identifier"] == f"data{i}"
                assert outer_elements["object"]["elements"][i]["object"]["file_ext"] == "txt"
            incollection = {"src": "hdca", "id": hdca["id"]}
            inputs = {
                "d_uri": "gxftp://",
                "export_type|export_type_selector": "collection_auto",
                "export_type|infiles": [incollection],
            }
            response = dataset_populator.run_tool("export_remote", inputs, history_id)
            dataset_populator.wait_for_job(response["jobs"][0]["id"], assert_ok=True)
            assert "test0" in os.listdir(ftp_dir)
            subdir_content = os.listdir(os.path.join(ftp_dir, "test0"))
            assert sorted(subdir_content) == ["data0.txt", "data1.txt", "data2.txt"]

    def _assert_index_empty(self, index):
        assert len(index) == 0

    def _assert_index_matches_fixtures(self, index):
        paths = map(operator.itemgetter("path"), index)
        assert "a" in paths
        assert "subdir1/c" in paths

    def _assert_index_matches_fixtures_jstree(self, index):
        a_file = index[0]
        assert a_file["li_attr"]["full_path"] == "a"
        subdir1 = index[1]
        assert subdir1["type"] == "folder"
        assert subdir1["state"]["disabled"]
        assert subdir1["li_attr"]["full_path"] == "subdir1"
        subdir1_children = subdir1["children"]
        assert len(subdir1_children) == 2
        c = subdir1_children[0]
        assert c["li_attr"]["full_path"] == "subdir1/c"


class TestRemoteFilesNotConfiguredIntegration(integration_util.IntegrationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["library_import_dir"] = None
        config["user_library_import_dir"] = None
        config["ftp_upload_dir"] = None

    def test_configuration_statuses(self):
        importfiles = self.galaxy_interactor.get("remote_files?target=importdir")
        assert_error_code_is(importfiles, error_codes.error_codes_by_name["CONFIG_DOES_NOT_ALLOW"])
        assert_error_message_contains(importfiles, "import directory")

        importfiles = self.galaxy_interactor.get("remote_files?target=ftpdir")
        assert_error_code_is(importfiles, error_codes.error_codes_by_name["CONFIG_DOES_NOT_ALLOW"])
        assert_error_message_contains(importfiles, "FTP directories")

        importfiles = self.galaxy_interactor.get("remote_files?target=userdir")
        assert_error_code_is(importfiles, error_codes.error_codes_by_name["CONFIG_DOES_NOT_ALLOW"])
        assert_error_message_contains(importfiles, "user directories")

        # invalid request parameter waitwhat...
        importfiles = self.galaxy_interactor.get("remote_files?target=waitwhat")
        assert_error_code_is(importfiles, error_codes.error_codes_by_name["USER_REQUEST_INVALID_PARAMETER"])


def _write_file_fixtures(tmp, root):
    if not os.path.exists(root):
        os.mkdir(root)
    os.symlink(os.path.join(tmp, "b"), os.path.join(root, "unsafe"))
    with open(os.path.join(root, "a"), "w") as f:
        f.write("a\n")
    with open(os.path.join(tmp, "b"), "w") as f:
        f.write("b\n")

    subdir1 = os.path.join(root, "subdir1")
    os.mkdir(subdir1)
    with open(os.path.join(subdir1, "c"), "w") as f:
        f.write("c\n")

    subdir2 = os.path.join(subdir1, "subdir2")
    os.mkdir(subdir2)
    with open(os.path.join(subdir2, "d"), "w") as f:
        f.write("d\n")

    return tmp, root
