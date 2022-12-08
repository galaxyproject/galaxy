import json
import os
import urllib.parse

import pytest
from tusclient import client

from galaxy.tool_util.verify.test_data import TestDataResolver
from galaxy.util.unittest_utils import (
    skip_if_github_down,
    skip_if_site_down,
)
from galaxy_test.base.constants import (
    ONE_TO_SIX_ON_WINDOWS,
    ONE_TO_SIX_WITH_SPACES,
    ONE_TO_SIX_WITH_SPACES_ON_WINDOWS,
    ONE_TO_SIX_WITH_TABS,
    ONE_TO_SIX_WITH_TABS_NO_TRAILING_NEWLINE,
)
from galaxy_test.base.populators import (
    DatasetPopulator,
    skip_without_datatype,
    stage_inputs,
)
from ._framework import ApiTestCase


class TestToolsUpload(ApiTestCase):
    dataset_populator: DatasetPopulator

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def test_upload1_paste(self):
        with self.dataset_populator.test_history() as history_id:
            payload = self.dataset_populator.upload_payload(history_id, "Hello World")
            create_response = self._post("tools", data=payload)
            self._assert_has_keys(create_response.json(), "outputs")

    def test_upload1_paste_bad_datatype(self):
        # Check that you get a nice message if you upload an incorrect datatype
        with self.dataset_populator.test_history() as history_id:
            file_type = "johnsawesomebutfakedatatype"
            payload = self.dataset_populator.upload_payload(history_id, "Hello World", file_type=file_type)
            create = self._post("tools", data=payload).json()
            self._assert_has_keys(create, "err_msg")
            assert file_type in create["err_msg"]

    # upload1 rewrites content with posix lines by default but this can be disabled by setting
    # to_posix_lines=None in the request. Newer fetch API does not do this by default prefering
    # to keep content unaltered if possible but it can be enabled with a simple JSON boolean switch
    # of the same name (to_posix_lines).
    def test_upload_posix_newline_fixes_by_default(self):
        windows_content = ONE_TO_SIX_ON_WINDOWS
        result_content = self._upload_and_get_content(windows_content)
        assert result_content == ONE_TO_SIX_WITH_TABS

    def test_fetch_posix_unaltered(self):
        windows_content = ONE_TO_SIX_ON_WINDOWS
        result_content = self._upload_and_get_content(windows_content, api="fetch")
        assert result_content == ONE_TO_SIX_ON_WINDOWS

    def test_upload_disable_posix_fix(self):
        windows_content = ONE_TO_SIX_ON_WINDOWS
        result_content = self._upload_and_get_content(windows_content, to_posix_lines=None)
        assert result_content == windows_content

    def test_fetch_post_lines_option(self):
        windows_content = ONE_TO_SIX_ON_WINDOWS
        result_content = self._upload_and_get_content(windows_content, api="fetch", to_posix_lines=True)
        assert result_content == ONE_TO_SIX_WITH_TABS

    # Test how trailing new lines are added
    # - upload1 adds by default because to_posix_lines is on by default
    # - fetch doesn't add by default because to_posix_lines is off by default
    # - fetch does add trailing newline if to_posix_lines is enabled
    def test_post_lines_trailing(self):
        input_content = ONE_TO_SIX_WITH_TABS_NO_TRAILING_NEWLINE
        result_content = self._upload_and_get_content(input_content)
        assert result_content == ONE_TO_SIX_WITH_TABS

    def test_post_lines_trailing_off(self):
        input_content = ONE_TO_SIX_WITH_TABS_NO_TRAILING_NEWLINE
        result_content = self._upload_and_get_content(input_content, to_posix_lines=False)
        assert result_content == ONE_TO_SIX_WITH_TABS_NO_TRAILING_NEWLINE

    def test_fetch_post_lines_trailing_off_by_default(self):
        input_content = ONE_TO_SIX_WITH_TABS_NO_TRAILING_NEWLINE
        result_content = self._upload_and_get_content(input_content, api="fetch")
        assert result_content == ONE_TO_SIX_WITH_TABS_NO_TRAILING_NEWLINE

    def test_fetch_post_lines_trailing_if_to_posix(self):
        input_content = ONE_TO_SIX_WITH_TABS_NO_TRAILING_NEWLINE
        result_content = self._upload_and_get_content(input_content, api="fetch", to_posix_lines=True)
        assert result_content == ONE_TO_SIX_WITH_TABS

    def test_upload_tab_to_space_off_by_default(self):
        table = ONE_TO_SIX_WITH_SPACES
        result_content = self._upload_and_get_content(table)
        assert result_content == table

    def test_fetch_tab_to_space_off_by_default(self):
        table = ONE_TO_SIX_WITH_SPACES
        result_content = self._upload_and_get_content(table, api="fetch")
        assert result_content == table

    def test_upload_tab_to_space(self):
        table = ONE_TO_SIX_WITH_SPACES
        result_content = self._upload_and_get_content(table, space_to_tab="Yes")
        assert result_content == ONE_TO_SIX_WITH_TABS

    def test_fetch_tab_to_space(self):
        table = ONE_TO_SIX_WITH_SPACES
        result_content = self._upload_and_get_content(table, api="fetch", space_to_tab=True)
        assert result_content == ONE_TO_SIX_WITH_TABS

    def test_fetch_tab_to_space_doesnt_swap_newlines(self):
        table = ONE_TO_SIX_WITH_SPACES_ON_WINDOWS
        result_content = self._upload_and_get_content(table, api="fetch", space_to_tab=True)
        assert result_content == ONE_TO_SIX_ON_WINDOWS

    def test_fetch_compressed_with_explicit_type(self):
        fastqgz_path = TestDataResolver().get_filename("1.fastqsanger.gz")
        with open(fastqgz_path, "rb") as fh:
            details = self._upload_and_get_details(fh, api="fetch", ext="fastqsanger.gz")
        assert details["state"] == "ok"
        assert details["file_ext"] == "fastqsanger.gz"

    def test_fetch_compressed_default(self):
        fastqgz_path = TestDataResolver().get_filename("1.fastqsanger.gz")
        with open(fastqgz_path, "rb") as fh:
            details = self._upload_and_get_details(fh, api="fetch", assert_ok=False)
        assert details["state"] == "ok"
        assert details["file_ext"] == "fastqsanger.gz", details

    @pytest.mark.require_new_history
    def test_fetch_compressed_auto_decompress_target(self, history_id):
        # TODO: this should definitely be fixed to allow auto decompression via that API.
        fastqgz_path = TestDataResolver().get_filename("1.fastqsanger.gz")
        with open(fastqgz_path, "rb") as fh:
            details = self._upload_and_get_details(
                fh, api="fetch", history_id=history_id, assert_ok=False, auto_decompress=True
            )
        assert details["state"] == "ok"
        assert details["file_ext"] == "fastqsanger.gz", details

    def test_upload_decompress_off_with_auto_by_default(self):
        # UNSTABLE_FLAG: This might default to a bed.gz datatype in the future.
        bedgz_path = TestDataResolver().get_filename("4.bed.gz")
        with open(bedgz_path, "rb") as fh:
            details = self._upload_and_get_details(fh, file_type="auto")
        assert details["state"] == "ok"
        assert details["file_ext"] == "bed", details

    def test_upload_decompresses_if_uncompressed_type_selected(self):
        fastqgz_path = TestDataResolver().get_filename("1.fastqsanger.gz")
        with open(fastqgz_path, "rb") as fh:
            details = self._upload_and_get_details(fh, file_type="fastqsanger")
        assert details["state"] == "ok"
        assert details["file_ext"] == "fastqsanger", details
        assert details["file_size"] == 178, details

    def test_upload_decompress_off_if_compressed_type_selected(self):
        fastqgz_path = TestDataResolver().get_filename("1.fastqsanger.gz")
        with open(fastqgz_path, "rb") as fh:
            details = self._upload_and_get_details(fh, file_type="fastqsanger.gz")
        assert details["state"] == "ok"
        assert details["file_ext"] == "fastqsanger.gz", details
        assert details["file_size"] == 161, details

    def test_upload_auto_decompress_off(self):
        # UNSTABLE_FLAG: This might default to a bed.gz datatype in the future.
        bedgz_path = TestDataResolver().get_filename("4.bed.gz")
        with open(bedgz_path, "rb") as fh:
            details = self._upload_and_get_details(fh, file_type="auto", assert_ok=False, auto_decompress=False)
        assert details["file_ext"] == "binary", details

    @pytest.mark.require_new_history
    def test_fetch_compressed_with_auto(self, history_id):
        # UNSTABLE_FLAG: This might default to a bed.gz datatype in the future.
        # TODO: this should definitely be fixed to allow auto decompression via that API.
        bedgz_path = TestDataResolver().get_filename("4.bed.gz")
        with open(bedgz_path, "rb") as fh:
            details = self._upload_and_get_details(
                fh, api="fetch", history_id=history_id, auto_decompress=True, assert_ok=False
            )
        assert details["state"] == "ok"
        assert details["file_ext"] == "bed"

    @skip_without_datatype("rdata")
    def test_rdata_not_decompressed(self):
        # Prevent regression of https://github.com/galaxyproject/galaxy/issues/753
        rdata_path = TestDataResolver().get_filename("1.RData")
        with open(rdata_path, "rb") as fh:
            rdata_metadata = self._upload_and_get_details(fh, file_type="auto")
        assert rdata_metadata["file_ext"] == "rdata"

    @skip_without_datatype("csv")
    def test_csv_upload(self):
        csv_path = TestDataResolver().get_filename("1.csv")
        with open(csv_path, "rb") as fh:
            csv_metadata = self._upload_and_get_details(fh, file_type="csv")
        assert csv_metadata["file_ext"] == "csv"

    @skip_without_datatype("csv")
    def test_csv_upload_auto(self):
        csv_path = TestDataResolver().get_filename("1.csv")
        with open(csv_path, "rb") as fh:
            csv_metadata = self._upload_and_get_details(fh, file_type="auto")
        assert csv_metadata["file_ext"] == "csv"

    @skip_without_datatype("csv")
    def test_csv_fetch(self):
        csv_path = TestDataResolver().get_filename("1.csv")
        with open(csv_path, "rb") as fh:
            csv_metadata = self._upload_and_get_details(fh, api="fetch", ext="csv", to_posix_lines=True)
        assert csv_metadata["file_ext"] == "csv"

    @skip_without_datatype("csv")
    def test_csv_sniff_fetch(self):
        csv_path = TestDataResolver().get_filename("1.csv")
        with open(csv_path, "rb") as fh:
            csv_metadata = self._upload_and_get_details(fh, api="fetch", ext="auto", to_posix_lines=True)
        assert csv_metadata["file_ext"] == "csv"

    @skip_without_datatype("tiff")
    def test_image_upload_auto(self):
        tiff_path = TestDataResolver().get_filename("1.tiff")
        with open(tiff_path, "rb") as fh:
            tiff_metadata = self._upload_and_get_details(fh, file_type="auto")
        assert tiff_metadata["file_ext"] == "tiff"

    def test_newlines_stage_fetch(self, history_id: str) -> None:
        job = {
            "input1": {
                "class": "File",
                "format": "txt",
                "path": "test-data/simple_line_no_newline.txt",
            }
        }
        inputs, datasets = stage_inputs(self.galaxy_interactor, history_id, job, use_path_paste=False)
        dataset = datasets[0]
        content = self.dataset_populator.get_history_dataset_content(history_id=history_id, dataset=dataset)
        # By default this appends the newline.
        assert content == "This is a line of text.\n"

    def test_stage_object(self, history_id: str) -> None:
        job = {"input1": "randomstr"}
        inputs, datasets = stage_inputs(
            self.galaxy_interactor, history_id, job, use_path_paste=False, use_fetch_api=False
        )
        dataset = datasets[0]
        content = self.dataset_populator.get_history_dataset_content(history_id=history_id, dataset=dataset)
        assert content.strip() == '"randomstr"'

    def test_stage_object_fetch(self, history_id: str) -> None:
        job = {"input1": "randomstr"}
        inputs, datasets = stage_inputs(self.galaxy_interactor, history_id, job, use_path_paste=False)
        dataset = datasets[0]
        content = self.dataset_populator.get_history_dataset_content(history_id=history_id, dataset=dataset)
        assert content == '"randomstr"'

    def test_newlines_stage_fetch_configured(self, history_id: str) -> None:
        job = {
            "input1": {
                "class": "File",
                "format": "txt",
                "path": "test-data/simple_line_no_newline.txt",
                "dbkey": "hg19",
            }
        }
        inputs, datasets = stage_inputs(
            self.galaxy_interactor, history_id, job, use_path_paste=False, to_posix_lines=False
        )
        dataset = datasets[0]
        content = self.dataset_populator.get_history_dataset_content(history_id=history_id, dataset=dataset)
        # By default this appends the newline, but we disabled with 'to_posix_lines=False' above.
        assert content == "This is a line of text."
        details = self.dataset_populator.get_history_dataset_details(history_id=history_id, dataset=dataset)
        assert details["genome_build"] == "hg19"

    @skip_if_github_down
    def test_upload_multiple_mixed_success(self, history_id):
        destination = {"type": "hdas"}
        targets = [
            {
                "destination": destination,
                "items": [
                    {"src": "url", "url": "https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/1.bed"},
                    {
                        "src": "url",
                        "url": "https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/12.bed",
                    },
                ],
            }
        ]
        payload = {
            "history_id": history_id,
            "targets": targets,
        }
        fetch_response = self.dataset_populator.fetch(payload)
        self._assert_status_code_is(fetch_response, 200)
        outputs = fetch_response.json()["outputs"]
        assert len(outputs) == 2
        output0 = outputs[0]
        output1 = outputs[1]
        output0 = self.dataset_populator.get_history_dataset_details(history_id, dataset=output0, assert_ok=False)
        output1 = self.dataset_populator.get_history_dataset_details(history_id, dataset=output1, assert_ok=False)
        assert output0["state"] == "ok"
        assert output1["state"] == "error"

    @skip_if_github_down
    def test_fetch_bam_file_from_url_with_extension_set(self, history_id):
        item = {
            "src": "url",
            "url": "https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/1.bam",
            "ext": "bam",
        }
        output = self.dataset_populator.fetch_hda(history_id, item)
        self.dataset_populator.get_history_dataset_details(history_id, dataset=output, assert_ok=True)

    @skip_if_github_down
    def test_fetch_html_from_url(self, history_id):
        destination = {"type": "hdas"}
        targets = [
            {
                "destination": destination,
                "items": [
                    {
                        "src": "url",
                        "url": "https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/html_file.txt",
                    },
                ],
            }
        ]
        payload = {
            "history_id": history_id,
            "targets": targets,
        }
        fetch_response = self.dataset_populator.fetch(payload)
        self._assert_status_code_is(fetch_response, 200)
        response = fetch_response.json()
        output = response["outputs"][0]
        job = response["jobs"][0]
        self.dataset_populator.wait_for_job(job["id"])
        dataset = self.dataset_populator.get_history_dataset_details(history_id, dataset=output, assert_ok=False)
        assert dataset["state"] == "error"
        assert dataset["name"] == "html_file.txt"

    def test_abort_fetch_job(self, history_id):
        # This should probably be an integration test that also verifies
        # that the celery chord is properly canceled.
        item = {
            "src": "url",
            "url": "https://httpstat.us/200?sleep=10000",
            "ext": "txt",
        }
        destination = {"type": "hdas"}
        targets = [
            {
                "destination": destination,
                "items": [item],
            }
        ]
        payload = {
            "history_id": history_id,
            "targets": targets,
        }
        fetch_response = self.dataset_populator.fetch(payload, wait=False)
        self._assert_status_code_is(fetch_response, 200)
        response = fetch_response.json()
        job_id = response["jobs"][0]["id"]
        # Wait until state is running
        self.dataset_populator.wait_for_job(job_id, ok_states=["running"])
        cancel_response = self.dataset_populator.cancel_job(job_id)
        self._assert_status_code_is(cancel_response, 200)
        dataset = self.dataset_populator.get_history_dataset_details(
            history_id, dataset_id=response["outputs"][0]["id"], assert_ok=False
        )
        assert dataset["file_size"] == 0
        assert dataset["state"] == "discarded"

    @skip_without_datatype("velvet")
    def test_composite_datatype(self):
        with self.dataset_populator.test_history() as history_id:
            dataset = self._velvet_upload(
                history_id,
                extra_inputs={
                    "files_1|url_paste": "roadmaps content",
                    "files_1|type": "upload_dataset",
                    "files_2|url_paste": "log content",
                    "files_2|type": "upload_dataset",
                },
            )

            roadmaps_content = self._get_roadmaps_content(history_id, dataset)
            assert roadmaps_content.strip() == "roadmaps content", roadmaps_content

    @skip_without_datatype("velvet")
    def test_composite_datatype_fetch(self, history_id):
        item = {
            "src": "composite",
            "ext": "velvet",
            "composite": {
                "items": [
                    {"src": "pasted", "paste_content": "sequences content"},
                    {"src": "pasted", "paste_content": "roadmaps content"},
                    {"src": "pasted", "paste_content": "log content"},
                ]
            },
        }
        output = self.dataset_populator.fetch_hda(history_id, item)
        roadmaps_content = self._get_roadmaps_content(history_id, output)
        assert roadmaps_content.strip() == "roadmaps content", roadmaps_content

    @skip_without_datatype("velvet")
    def test_composite_datatype_stage_fetch(self, history_id: str) -> None:
        job = {
            "input1": {
                "class": "File",
                "format": "velvet",
                "composite_data": [
                    "test-data/simple_line.txt",
                    "test-data/simple_line_alternative.txt",
                    "test-data/simple_line_x2.txt",
                ],
            }
        }
        stage_inputs(self.galaxy_interactor, history_id, job, use_path_paste=False)
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)

    @skip_without_datatype("velvet")
    def test_composite_datatype_pbed_stage_fetch(self, history_id: str) -> None:
        job = {
            "input1": {
                "class": "File",
                "format": "pbed",
                "composite_data": [
                    "test-data/rgenetics.bim",
                    "test-data/rgenetics.bed",
                    "test-data/rgenetics.fam",
                ],
            }
        }
        stage_inputs(self.galaxy_interactor, history_id, job, use_path_paste=False)
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)

    @skip_without_datatype("velvet")
    def test_composite_datatype_stage_upload1(self, history_id: str) -> None:
        job = {
            "input1": {
                "class": "File",
                "format": "velvet",
                "composite_data": [
                    "test-data/simple_line.txt",
                    "test-data/simple_line_alternative.txt",
                    "test-data/simple_line_x2.txt",
                ],
            }
        }
        stage_inputs(self.galaxy_interactor, history_id, job, use_path_paste=False, use_fetch_api=False)
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)

    @skip_without_datatype("velvet")
    def test_composite_datatype_space_to_tab(self, history_id):
        # Like previous test but set one upload with space_to_tab to True to
        # verify that works.
        dataset = self._velvet_upload(
            history_id,
            extra_inputs={
                "files_1|url_paste": "roadmaps content",
                "files_1|type": "upload_dataset",
                "files_1|space_to_tab": "Yes",
                "files_2|url_paste": "log content",
                "files_2|type": "upload_dataset",
            },
        )

        roadmaps_content = self._get_roadmaps_content(history_id, dataset)
        assert roadmaps_content.strip() == "roadmaps\tcontent", roadmaps_content

    @skip_without_datatype("velvet")
    def test_composite_datatype_posix_lines(self):
        # Like previous test but set one upload with space_to_tab to True to
        # verify that works.
        with self.dataset_populator.test_history() as history_id:
            dataset = self._velvet_upload(
                history_id,
                extra_inputs={
                    "files_1|url_paste": "roadmaps\rcontent",
                    "files_1|type": "upload_dataset",
                    "files_1|space_to_tab": "Yes",
                    "files_2|url_paste": "log\rcontent",
                    "files_2|type": "upload_dataset",
                },
            )

            roadmaps_content = self._get_roadmaps_content(history_id, dataset)
            assert roadmaps_content.strip() == "roadmaps\ncontent", roadmaps_content

    @skip_without_datatype("isa-tab")
    def test_composite_datatype_isatab(self):
        isatab_zip_path = TestDataResolver().get_filename("MTBLS6.zip")
        details = self._upload_and_get_details(open(isatab_zip_path, "rb"), file_type="isa-tab")
        assert details["state"] == "ok"
        assert details["file_ext"] == "isa-tab", details
        assert details["file_size"] == 85, details

    def test_upload_composite_as_tar(self, history_id):
        tar_path = self.test_data_resolver.get_filename("testdir.tar")
        with open(tar_path, "rb") as tar_f:
            payload = self.dataset_populator.upload_payload(
                history_id,
                "Test123",
                extra_inputs={
                    "files_1|file_data": tar_f,
                    "files_1|NAME": "composite",
                    "file_count": "2",
                    "force_composite": "True",
                },
            )
            run_response = self.dataset_populator.tools_post(payload)
            self.dataset_populator.wait_for_tool_run(history_id, run_response)
            dataset = run_response.json()["outputs"][0]
            self._check_testdir_composite(dataset, history_id)

    def test_upload_composite_as_tar_fetch(self, history_id):
        tar_path = self.test_data_resolver.get_filename("testdir.tar")
        with open(tar_path, "rb") as tar_f:
            destination = {"type": "hdas"}
            targets = [
                {
                    "destination": destination,
                    "items": [
                        {
                            "src": "pasted",
                            "paste_content": "Test123\n",
                            "ext": "txt",
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
            payload = {
                "history_id": history_id,
                "targets": targets,
            }
            payload["__files"] = {"files_0|file_data": tar_f}
            fetch_response = self.dataset_populator.fetch(payload)
            self._assert_status_code_is(fetch_response, 200)
            outputs = fetch_response.json()["outputs"]
            assert len(outputs) == 1
            output = outputs[0]
            self._check_testdir_composite(output, history_id)

    def _check_testdir_composite(self, dataset, history_id):
        content = self.dataset_populator.get_history_dataset_content(history_id, dataset=dataset)
        assert content.strip() == "Test123"
        extra_files = self.dataset_populator.get_history_dataset_extra_files(history_id, dataset_id=dataset["id"])
        assert len(extra_files) == 5, extra_files
        expected_contents = {
            "testdir": "Directory",
            "testdir/c": "Directory",
            "testdir/a": "File",
            "testdir/b": "File",
            "testdir/c/d": "File",
        }
        found_files = set()
        for extra_file in extra_files:
            path = extra_file["path"]
            assert path in expected_contents
            assert extra_file["class"] == expected_contents[path]
            found_files.add(path)

        assert len(found_files) == 5, found_files

    def test_upload_composite_from_bad_tar(self, history_id):
        tar_path = self.test_data_resolver.get_filename("unsafe.tar")
        with open(tar_path, "rb") as tar_f:
            payload = self.dataset_populator.upload_payload(
                history_id,
                "Test123",
                extra_inputs={
                    "files_1|file_data": tar_f,
                    "files_1|NAME": "composite",
                    "file_count": "2",
                    "force_composite": "True",
                },
            )
            run_response = self.dataset_populator.tools_post(payload)
            self.dataset_populator.wait_for_tool_run(history_id, run_response, assert_ok=False)
            dataset = run_response.json()["outputs"][0]
            details = self.dataset_populator.get_history_dataset_details(history_id, dataset=dataset, assert_ok=False)
            assert details["state"] == "error"

    def test_upload_dbkey(self):
        with self.dataset_populator.test_history() as history_id:
            payload = self.dataset_populator.upload_payload(history_id, "Test123", dbkey="hg19")
            run_response = self.dataset_populator.tools_post(payload)
            self.dataset_populator.wait_for_tool_run(history_id, run_response)
            datasets = run_response.json()["outputs"]
            assert datasets[0].get("genome_build") == "hg19", datasets[0]

    def test_fetch_bam_file(self, history_id):
        bam_path = TestDataResolver().get_filename("1.bam")
        with open(bam_path, "rb") as fh:
            details = self._upload_and_get_details(fh, api="fetch", history_id=history_id, assert_ok=False)
        assert details["state"] == "ok"
        assert details["file_ext"] == "bam", details

    def test_upload_bam_file(self):
        bam_path = TestDataResolver().get_filename("1.bam")
        with open(bam_path, "rb") as fh:
            details = self._upload_and_get_details(fh, file_type="auto")
        assert details["state"] == "ok"
        assert details["file_ext"] == "bam", details

    def test_fetch_metadata(self):
        table = ONE_TO_SIX_WITH_SPACES
        details = self._upload_and_get_details(
            table, api="fetch", dbkey="hg19", info="cool upload", tags=["name:data", "group:type:paired-end"]
        )
        assert details.get("genome_build") == "hg19"
        assert details.get("misc_info") == "cool upload", details
        tags = details.get("tags")
        assert len(tags) == 2, details
        assert "group:type:paired-end" in tags
        assert "name:data" in tags

    def test_upload_multiple_files_1(self):
        with self.dataset_populator.test_history() as history_id:
            payload = self.dataset_populator.upload_payload(
                history_id,
                "Test123",
                dbkey="hg19",
                extra_inputs={
                    "files_1|url_paste": "SecondOutputContent",
                    "files_1|NAME": "SecondOutputName",
                    "files_1|file_type": "tabular",
                    "files_1|dbkey": "hg18",
                    "file_count": "2",
                },
            )
            run_response = self.dataset_populator.tools_post(payload)
            self.dataset_populator.wait_for_tool_run(history_id, run_response)
            datasets = run_response.json()["outputs"]

            assert len(datasets) == 2, datasets
            content = self.dataset_populator.get_history_dataset_content(history_id, dataset=datasets[0])
            assert content.strip() == "Test123"
            assert datasets[0]["file_ext"] == "txt"
            assert datasets[0]["genome_build"] == "hg19", datasets

            content = self.dataset_populator.get_history_dataset_content(history_id, dataset=datasets[1])
            assert content.strip() == "SecondOutputContent"
            assert datasets[1]["file_ext"] == "tabular"
            assert datasets[1]["genome_build"] == "hg18", datasets

    def test_upload_multiple_files_2(self):
        with self.dataset_populator.test_history() as history_id:
            payload = self.dataset_populator.upload_payload(
                history_id,
                "Test123",
                file_type="tabular",
                dbkey="hg19",
                extra_inputs={
                    "files_1|url_paste": "SecondOutputContent",
                    "files_1|NAME": "SecondOutputName",
                    "files_1|file_type": "txt",
                    "files_1|dbkey": "hg18",
                    "file_count": "2",
                },
            )
            run_response = self.dataset_populator.tools_post(payload)
            self.dataset_populator.wait_for_tool_run(history_id, run_response)
            datasets = run_response.json()["outputs"]

            assert len(datasets) == 2, datasets
            content = self.dataset_populator.get_history_dataset_content(history_id, dataset=datasets[0])
            assert content.strip() == "Test123"
            assert datasets[0]["file_ext"] == "tabular", datasets
            assert datasets[0]["genome_build"] == "hg19", datasets

            content = self.dataset_populator.get_history_dataset_content(history_id, dataset=datasets[1])
            assert content.strip() == "SecondOutputContent"
            assert datasets[1]["file_ext"] == "txt"
            assert datasets[1]["genome_build"] == "hg18", datasets

    def test_upload_multiple_files_3(self):
        with self.dataset_populator.test_history() as history_id:
            payload = self.dataset_populator.upload_payload(
                history_id,
                "Test123",
                file_type="tabular",
                dbkey="hg19",
                extra_inputs={
                    "files_0|file_type": "txt",
                    "files_0|dbkey": "hg18",
                    "files_1|url_paste": "SecondOutputContent",
                    "files_1|NAME": "SecondOutputName",
                    "files_1|file_type": "txt",
                    "files_1|dbkey": "hg18",
                    "file_count": "2",
                },
            )
            run_response = self.dataset_populator.tools_post(payload)
            self.dataset_populator.wait_for_tool_run(history_id, run_response)
            datasets = run_response.json()["outputs"]

            assert len(datasets) == 2, datasets
            content = self.dataset_populator.get_history_dataset_content(history_id, dataset=datasets[0])
            assert content.strip() == "Test123"
            assert datasets[0]["file_ext"] == "txt", datasets
            assert datasets[0]["genome_build"] == "hg18", datasets

            content = self.dataset_populator.get_history_dataset_content(history_id, dataset=datasets[1])
            assert content.strip() == "SecondOutputContent"
            assert datasets[1]["file_ext"] == "txt"
            assert datasets[1]["genome_build"] == "hg18", datasets

    def test_upload_multiple_files_no_dbkey(self):
        with self.dataset_populator.test_history() as history_id:
            payload = self.dataset_populator.upload_payload(
                history_id,
                "Test123",
                file_type="tabular",
                dbkey=None,
                extra_inputs={
                    "files_0|file_type": "txt",
                    "files_1|url_paste": "SecondOutputContent",
                    "files_1|NAME": "SecondOutputName",
                    "files_1|file_type": "txt",
                    "file_count": "2",
                },
            )
            run_response = self.dataset_populator.tools_post(payload)
            self.dataset_populator.wait_for_tool_run(history_id, run_response)
            datasets = run_response.json()["outputs"]

            assert len(datasets) == 2, datasets
            content = self.dataset_populator.get_history_dataset_content(history_id, dataset=datasets[0])
            assert content.strip() == "Test123"
            assert datasets[0]["file_ext"] == "txt", datasets
            assert datasets[0]["genome_build"] == "?", datasets

            content = self.dataset_populator.get_history_dataset_content(history_id, dataset=datasets[1])
            assert content.strip() == "SecondOutputContent"
            assert datasets[1]["file_ext"] == "txt"
            assert datasets[1]["genome_build"] == "?", datasets

    def test_upload_multiple_files_space_to_tab(self):
        with self.dataset_populator.test_history() as history_id:
            payload = self.dataset_populator.upload_payload(
                history_id,
                content=ONE_TO_SIX_WITH_SPACES,
                file_type="tabular",
                dbkey="hg19",
                extra_inputs={
                    "files_0|file_type": "txt",
                    "files_0|space_to_tab": "Yes",
                    "files_1|url_paste": ONE_TO_SIX_WITH_SPACES,
                    "files_1|NAME": "SecondOutputName",
                    "files_1|file_type": "txt",
                    "files_2|url_paste": ONE_TO_SIX_WITH_SPACES,
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

    def test_multiple_files_posix_lines(self):
        with self.dataset_populator.test_history() as history_id:
            payload = self.dataset_populator.upload_payload(
                history_id,
                content=ONE_TO_SIX_ON_WINDOWS,
                file_type="tabular",
                dbkey="hg19",
                extra_inputs={
                    "files_0|file_type": "txt",
                    "files_0|to_posix_lines": "Yes",
                    "files_1|url_paste": ONE_TO_SIX_ON_WINDOWS,
                    "files_1|NAME": "SecondOutputName",
                    "files_1|file_type": "txt",
                    "files_1|to_posix_lines": None,
                    "files_2|url_paste": ONE_TO_SIX_ON_WINDOWS,
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

    def test_upload_force_composite(self):
        with self.dataset_populator.test_history() as history_id:
            payload = self.dataset_populator.upload_payload(
                history_id,
                "Test123",
                extra_inputs={
                    "files_1|url_paste": "CompositeContent",
                    "files_1|NAME": "composite",
                    "file_count": "2",
                    "force_composite": "True",
                },
            )
            run_response = self.dataset_populator.tools_post(payload)
            self.dataset_populator.wait_for_tool_run(history_id, run_response)
            dataset = run_response.json()["outputs"][0]
            content = self.dataset_populator.get_history_dataset_content(history_id, dataset=dataset)
            assert content.strip() == "Test123"
            extra_files = self.dataset_populator.get_history_dataset_extra_files(history_id, dataset_id=dataset["id"])
            assert len(extra_files) == 1, extra_files  # [{u'path': u'1', u'class': u'File'}]
            extra_file = extra_files[0]
            assert extra_file["path"] == "composite"
            assert extra_file["class"] == "File"

    def test_upload_from_invalid_url(self):
        with pytest.raises(AssertionError):
            self._upload("https://foo.invalid", assert_ok=False)

    @skip_if_site_down("https://usegalaxy.org")
    def test_upload_from_404_url(self):
        history_id, new_dataset = self._upload("https://usegalaxy.org/bla123", assert_ok=False)
        dataset_details = self.dataset_populator.get_history_dataset_details(
            history_id, dataset_id=new_dataset["id"], assert_ok=False
        )
        assert (
            dataset_details["state"] == "error"
        ), f"expected dataset state to be 'error', but got '{dataset_details['state']}'"

    @skip_if_site_down("https://usegalaxy.org")
    def test_upload_from_valid_url(self):
        history_id, new_dataset = self._upload("https://usegalaxy.org/api/version")
        self.dataset_populator.get_history_dataset_details(history_id, dataset_id=new_dataset["id"], assert_ok=True)

    @skip_if_site_down("https://usegalaxy.org")
    def test_upload_from_valid_url_spaces(self):
        history_id, new_dataset = self._upload("  https://usegalaxy.org/api/version  ")
        self.dataset_populator.get_history_dataset_details(history_id, dataset_id=new_dataset["id"], assert_ok=True)

    def test_upload_and_validate_invalid(self):
        path = TestDataResolver().get_filename("1.fastqsanger")
        with open(path, "rb") as fh:
            metadata = self._upload_and_get_details(fh, file_type="fastqcssanger")
        assert "validated_state" in metadata
        assert metadata["validated_state"] == "unknown"
        history_id = metadata["history_id"]
        dataset_id = metadata["id"]
        terminal_validated_state = self.dataset_populator.validate_dataset_and_wait(history_id, dataset_id)
        assert terminal_validated_state == "invalid", terminal_validated_state

    def test_upload_and_validate_valid(self):
        path = TestDataResolver().get_filename("1.fastqsanger")
        with open(path, "rb") as fh:
            metadata = self._upload_and_get_details(fh, file_type="fastqsanger")
        assert "validated_state" in metadata
        assert metadata["validated_state"] == "unknown"
        history_id = metadata["history_id"]
        dataset_id = metadata["id"]
        terminal_validated_state = self.dataset_populator.validate_dataset_and_wait(history_id, dataset_id)
        assert terminal_validated_state == "ok", terminal_validated_state

    def _velvet_upload(self, history_id, extra_inputs):
        payload = self.dataset_populator.upload_payload(
            history_id,
            "sequences content",
            file_type="velvet",
            extra_inputs=extra_inputs,
        )
        run_response = self.dataset_populator.tools_post(payload)
        self.dataset_populator.wait_for_tool_run(history_id, run_response)
        datasets = run_response.json()["outputs"]

        assert len(datasets) == 1
        dataset = datasets[0]

        return dataset

    def _get_roadmaps_content(self, history_id, dataset):
        roadmaps_content = self.dataset_populator.get_history_dataset_content(
            history_id, dataset=dataset, filename="Roadmaps"
        )
        return roadmaps_content

    def _upload_and_get_content(self, content, **upload_kwds):
        history_id, new_dataset = self._upload(content, **upload_kwds)
        return self.dataset_populator.get_history_dataset_content(history_id, dataset=new_dataset)

    def _upload_and_get_details(self, content, **upload_kwds):
        assert_ok = upload_kwds.pop("assert_ok", True)
        history_id, new_dataset = self._upload(content, **upload_kwds)
        return self.dataset_populator.get_history_dataset_details(history_id, dataset=new_dataset, assert_ok=assert_ok)

    def _upload(self, content, api="upload1", history_id=None, **upload_kwds):
        assert_ok = upload_kwds.get("assert_ok", True)
        history_id = history_id or self.dataset_populator.new_history()
        if api == "upload1":
            new_dataset = self.dataset_populator.new_dataset(
                history_id, content=content, fetch_data=False, **upload_kwds
            )
        else:
            assert api == "fetch"
            element = dict(src="files", **upload_kwds)
            target = {
                "destination": {"type": "hdas"},
                "elements": [element],
            }
            targets = [target]
            payload = {"history_id": history_id, "targets": targets, "__files": {"files_0|file_data": content}}
            new_dataset = self.dataset_populator.fetch(payload, assert_ok=assert_ok).json()["outputs"][0]
        self.dataset_populator.wait_for_history(history_id, assert_ok=assert_ok)
        return history_id, new_dataset

    def test_upload_dataset_resumable(self):
        def upload_file(url, path, api_key, history_id):
            filename = os.path.basename(path)
            metadata = {
                "filename": filename,
                "history_id": history_id,
            }
            my_client = client.TusClient(url, headers={"x-api-key": api_key})

            # Upload a file to a tus server.
            uploader = my_client.uploader(path, metadata=metadata)
            uploader.upload()
            return uploader.url.rsplit("/", 1)[1]

        with self.dataset_populator.test_history() as history_id:
            session_id = upload_file(
                url=urllib.parse.urljoin(self.url, "api/upload/resumable_upload"),
                path=TestDataResolver().get_filename("1.fastqsanger.gz"),
                api_key=self.galaxy_interactor.api_key,
                history_id=history_id,
            )
            hda = self._upload_and_get_details(
                content=json.dumps({"session_id": session_id}),
                api="fetch",
                ext="fastqsanger.gz",
                name="1.fastqsanger.gz",
            )
            assert hda["name"] == "1.fastqsanger.gz"
            assert hda["file_ext"] == "fastqsanger.gz"
            assert hda["state"] == "ok"

    def test_upload_deferred(self, history_id):
        details = self.dataset_populator.create_deferred_hda(
            history_id, "https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/1.bam", ext="bam"
        )
        assert details["state"] == "deferred"
        assert details["file_ext"] == "bam"
