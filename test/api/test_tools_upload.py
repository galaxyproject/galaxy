import json

from base import api
from base.constants import (
    ONE_TO_SIX_ON_WINDOWS,
    ONE_TO_SIX_WITH_SPACES,
    ONE_TO_SIX_WITH_TABS,
)
from base.populators import (
    DatasetPopulator,
    skip_without_datatype,
    uses_test_history,
)

from galaxy.tools.verify.test_data import TestDataResolver


class ToolsUploadTestCase(api.ApiTestCase):

    def setUp(self):
        super(ToolsUploadTestCase, self).setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def test_upload1_paste(self):
        with self.dataset_populator.test_history() as history_id:
            payload = self.dataset_populator.upload_payload(history_id, 'Hello World')
            create_response = self._post("tools", data=payload)
            self._assert_has_keys(create_response.json(), 'outputs')

    def test_upload1_paste_bad_datatype(self):
        # Check that you get a nice message if you upload an incorrect datatype
        with self.dataset_populator.test_history() as history_id:
            file_type = "johnsawesomebutfakedatatype"
            payload = self.dataset_populator.upload_payload(history_id, 'Hello World', file_type=file_type)
            create = self._post("tools", data=payload).json()
            self._assert_has_keys(create, 'err_msg')
            assert file_type in create['err_msg']

    # upload1 rewrites content with posix lines by default but this can be disabled by setting
    # to_posix_lines=None in the request. Newer fetch API does not do this by default prefering
    # to keep content unaltered if possible but it can be enabled with a simple JSON boolean switch
    # of the same name (to_posix_lines).
    def test_upload_posix_newline_fixes_by_default(self):
        windows_content = ONE_TO_SIX_ON_WINDOWS
        result_content = self._upload_and_get_content(windows_content)
        self.assertEqual(result_content, ONE_TO_SIX_WITH_TABS)

    def test_fetch_posix_unaltered(self):
        windows_content = ONE_TO_SIX_ON_WINDOWS
        result_content = self._upload_and_get_content(windows_content, api="fetch")
        self.assertEqual(result_content, ONE_TO_SIX_ON_WINDOWS)

    def test_upload_disable_posix_fix(self):
        windows_content = ONE_TO_SIX_ON_WINDOWS
        result_content = self._upload_and_get_content(windows_content, to_posix_lines=None)
        self.assertEqual(result_content, windows_content)

    def test_fetch_post_lines_option(self):
        windows_content = ONE_TO_SIX_ON_WINDOWS
        result_content = self._upload_and_get_content(windows_content, api="fetch", to_posix_lines=True)
        self.assertEqual(result_content, ONE_TO_SIX_WITH_TABS)

    def test_upload_tab_to_space_off_by_default(self):
        table = ONE_TO_SIX_WITH_SPACES
        result_content = self._upload_and_get_content(table)
        self.assertEqual(result_content, table)

    def test_fetch_tab_to_space_off_by_default(self):
        table = ONE_TO_SIX_WITH_SPACES
        result_content = self._upload_and_get_content(table, api='fetch')
        self.assertEqual(result_content, table)

    def test_upload_tab_to_space(self):
        table = ONE_TO_SIX_WITH_SPACES
        result_content = self._upload_and_get_content(table, space_to_tab="Yes")
        self.assertEqual(result_content, ONE_TO_SIX_WITH_TABS)

    def test_fetch_tab_to_space(self):
        table = ONE_TO_SIX_WITH_SPACES
        result_content = self._upload_and_get_content(table, api="fetch", space_to_tab=True)
        self.assertEqual(result_content, ONE_TO_SIX_WITH_TABS)

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

    @uses_test_history(require_new=True)
    def test_fetch_compressed_auto_decompress_target(self, history_id):
        # TODO: this should definitely be fixed to allow auto decompression via that API.
        fastqgz_path = TestDataResolver().get_filename("1.fastqsanger.gz")
        with open(fastqgz_path, "rb") as fh:
            details = self._upload_and_get_details(fh,
                                                   api="fetch",
                                                   history_id=history_id,
                                                   assert_ok=False,
                                                   auto_decompress=True)
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

    @uses_test_history(require_new=True)
    def test_fetch_compressed_with_auto(self, history_id):
        # UNSTABLE_FLAG: This might default to a bed.gz datatype in the future.
        # TODO: this should definitely be fixed to allow auto decompression via that API.
        bedgz_path = TestDataResolver().get_filename("4.bed.gz")
        with open(bedgz_path, "rb") as fh:
            details = self._upload_and_get_details(fh,
                                                   api="fetch",
                                                   history_id=history_id,
                                                   auto_decompress=True,
                                                   assert_ok=False)
        assert details["state"] == "ok"
        assert details["file_ext"] == "bed"

    @skip_without_datatype("rdata")
    def test_rdata_not_decompressed(self):
        # Prevent regression of https://github.com/galaxyproject/galaxy/issues/753
        rdata_path = TestDataResolver().get_filename("1.RData")
        with open(rdata_path, "rb") as fh:
            rdata_metadata = self._upload_and_get_details(fh, file_type="auto")
        self.assertEqual(rdata_metadata["file_ext"], "rdata")

    @skip_without_datatype("csv")
    def test_csv_upload(self):
        csv_path = TestDataResolver().get_filename("1.csv")
        with open(csv_path, "rb") as fh:
            csv_metadata = self._upload_and_get_details(fh, file_type="csv")
        self.assertEqual(csv_metadata["file_ext"], "csv")

    @skip_without_datatype("csv")
    def test_csv_upload_auto(self):
        csv_path = TestDataResolver().get_filename("1.csv")
        with open(csv_path, "rb") as fh:
            csv_metadata = self._upload_and_get_details(fh, file_type="auto")
        self.assertEqual(csv_metadata["file_ext"], "csv")

    @skip_without_datatype("csv")
    def test_csv_fetch(self):
        csv_path = TestDataResolver().get_filename("1.csv")
        with open(csv_path, "rb") as fh:
            csv_metadata = self._upload_and_get_details(fh, api="fetch", ext="csv", to_posix_lines=True)
        self.assertEqual(csv_metadata["file_ext"], "csv")

    @skip_without_datatype("csv")
    def test_csv_sniff_fetch(self):
        csv_path = TestDataResolver().get_filename("1.csv")
        with open(csv_path, "rb") as fh:
            csv_metadata = self._upload_and_get_details(fh, api="fetch", ext="auto", to_posix_lines=True)
        self.assertEqual(csv_metadata["file_ext"], "csv")

    @skip_without_datatype("tiff")
    def test_image_upload_auto(self):
        tiff_path = TestDataResolver().get_filename("1.tiff")
        with open(tiff_path, "rb") as fh:
            tiff_metadata = self._upload_and_get_details(fh, file_type="auto")
        self.assertEqual(tiff_metadata["file_ext"], "tiff")

    @skip_without_datatype("velvet")
    def test_composite_datatype(self):
        with self.dataset_populator.test_history() as history_id:
            dataset = self._velvet_upload(history_id, extra_inputs={
                "files_1|url_paste": "roadmaps content",
                "files_1|type": "upload_dataset",
                "files_2|url_paste": "log content",
                "files_2|type": "upload_dataset",
            })

            roadmaps_content = self._get_roadmaps_content(history_id, dataset)
            assert roadmaps_content.strip() == "roadmaps content", roadmaps_content

    @skip_without_datatype("velvet")
    def test_composite_datatype_space_to_tab(self):
        # Like previous test but set one upload with space_to_tab to True to
        # verify that works.
        with self.dataset_populator.test_history() as history_id:
            dataset = self._velvet_upload(history_id, extra_inputs={
                "files_1|url_paste": "roadmaps content",
                "files_1|type": "upload_dataset",
                "files_1|space_to_tab": "Yes",
                "files_2|url_paste": "log content",
                "files_2|type": "upload_dataset",
            })

            roadmaps_content = self._get_roadmaps_content(history_id, dataset)
            assert roadmaps_content.strip() == "roadmaps\tcontent", roadmaps_content

    @skip_without_datatype("velvet")
    def test_composite_datatype_posix_lines(self):
        # Like previous test but set one upload with space_to_tab to True to
        # verify that works.
        with self.dataset_populator.test_history() as history_id:
            dataset = self._velvet_upload(history_id, extra_inputs={
                "files_1|url_paste": "roadmaps\rcontent",
                "files_1|type": "upload_dataset",
                "files_1|space_to_tab": "Yes",
                "files_2|url_paste": "log\rcontent",
                "files_2|type": "upload_dataset",
            })

            roadmaps_content = self._get_roadmaps_content(history_id, dataset)
            assert roadmaps_content.strip() == "roadmaps\ncontent", roadmaps_content

    @skip_without_datatype("isa-tab")
    def test_composite_datatype_isatab(self):
        isatab_zip_path = TestDataResolver().get_filename("MTBLS6.zip")
        details = self._upload_and_get_details(open(isatab_zip_path, "rb"), file_type="isa-tab")
        assert details["state"] == "ok"
        assert details["file_ext"] == "isa-tab", details
        assert details["file_size"] == 85, details

    def test_upload_dbkey(self):
        with self.dataset_populator.test_history() as history_id:
            payload = self.dataset_populator.upload_payload(history_id, "Test123", dbkey="hg19")
            run_response = self.dataset_populator.tools_post(payload)
            self.dataset_populator.wait_for_tool_run(history_id, run_response)
            datasets = run_response.json()["outputs"]
            assert datasets[0].get("genome_build") == "hg19", datasets[0]

    @uses_test_history(require_new=False)
    def test_fetch_bam_file(self, history_id):
        bam_path = TestDataResolver().get_filename("1.bam")
        with open(bam_path, "rb") as fh:
            details = self._upload_and_get_details(fh,
                                                   api="fetch",
                                                   history_id=history_id,
                                                   assert_ok=False)
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
        details = self._upload_and_get_details(table, api='fetch', dbkey="hg19", info="cool upload", tags=["name:data", "group:type:paired-end"])
        assert details.get("genome_build") == "hg19"
        assert details.get("misc_info") == "cool upload", details
        tags = details.get("tags")
        assert len(tags) == 2, details
        assert "group:type:paired-end" in tags
        assert "name:data" in tags

    def test_upload_multiple_files_1(self):
        with self.dataset_populator.test_history() as history_id:
            payload = self.dataset_populator.upload_payload(history_id, "Test123",
                dbkey="hg19",
                extra_inputs={
                    "files_1|url_paste": "SecondOutputContent",
                    "files_1|NAME": "SecondOutputName",
                    "files_1|file_type": "tabular",
                    "files_1|dbkey": "hg18",
                    "file_count": "2",
                }
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
            payload = self.dataset_populator.upload_payload(history_id, "Test123",
                file_type="tabular",
                dbkey="hg19",
                extra_inputs={
                    "files_1|url_paste": "SecondOutputContent",
                    "files_1|NAME": "SecondOutputName",
                    "files_1|file_type": "txt",
                    "files_1|dbkey": "hg18",
                    "file_count": "2",
                }
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
            payload = self.dataset_populator.upload_payload(history_id, "Test123",
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
                }
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
            payload = self.dataset_populator.upload_payload(history_id, "Test123",
                file_type="tabular",
                dbkey=None,
                extra_inputs={
                    "files_0|file_type": "txt",
                    "files_1|url_paste": "SecondOutputContent",
                    "files_1|NAME": "SecondOutputName",
                    "files_1|file_type": "txt",
                    "file_count": "2",
                }
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
            payload = self.dataset_populator.upload_payload(history_id,
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
                }
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
            payload = self.dataset_populator.upload_payload(history_id,
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
                }
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
            payload = self.dataset_populator.upload_payload(history_id, "Test123",
                extra_inputs={
                    "files_1|url_paste": "CompositeContent",
                    "files_1|NAME": "composite",
                    "file_count": "2",
                    "force_composite": "True",
                }
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
        history_id, new_dataset = self._upload('https://usegalaxy.org/bla123', assert_ok=False)
        dataset_details = self.dataset_populator.get_history_dataset_details(history_id, dataset_id=new_dataset["id"], assert_ok=False)
        assert dataset_details['state'] == 'error', "expected dataset state to be 'error', but got '%s'" % dataset_details['state']

    def test_upload_from_valid_url(self):
        history_id, new_dataset = self._upload('https://usegalaxy.org/api/version')
        self.dataset_populator.get_history_dataset_details(history_id, dataset_id=new_dataset["id"], assert_ok=True)

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
        roadmaps_content = self.dataset_populator.get_history_dataset_content(history_id, dataset=dataset, filename="Roadmaps")
        return roadmaps_content

    def _upload_and_get_content(self, content, **upload_kwds):
        history_id, new_dataset = self._upload(content, **upload_kwds)
        return self.dataset_populator.get_history_dataset_content(history_id, dataset=new_dataset)

    def _upload_and_get_details(self, content, **upload_kwds):
        history_id, new_dataset = self._upload(content, **upload_kwds)
        assert_ok = upload_kwds.get("assert_ok", True)
        return self.dataset_populator.get_history_dataset_details(history_id, dataset=new_dataset, assert_ok=assert_ok)

    def _upload(self, content, api="upload1", history_id=None, **upload_kwds):
        assert_ok = upload_kwds.get("assert_ok", True)
        history_id = history_id or self.dataset_populator.new_history()
        if api == "upload1":
            new_dataset = self.dataset_populator.new_dataset(history_id, content=content, **upload_kwds)
        else:
            assert api == "fetch"
            element = dict(src="files", **upload_kwds)
            target = {
                "destination": {"type": "hdas"},
                "elements": [element],
            }
            targets = json.dumps([target])
            payload = {
                "history_id": history_id,
                "targets": targets,
                "__files": {"files_0|file_data": content}
            }
            new_dataset = self.dataset_populator.fetch(payload, assert_ok=assert_ok).json()["outputs"][0]
        self.dataset_populator.wait_for_history(history_id, assert_ok=assert_ok)
        return history_id, new_dataset
