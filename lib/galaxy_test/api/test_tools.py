# Test tools API.
import contextlib
import json
import os
import zipfile
from io import BytesIO
from typing import (
    Any,
    Dict,
    List,
    Optional,
)
from uuid import uuid4

import pytest
from requests import (
    get,
    put,
)

from galaxy.tool_util.verify.interactor import ValidToolTestDict
from galaxy.util import galaxy_root_path
from galaxy.util.unittest_utils import skip_if_github_down
from galaxy_test.base import rules_test_data
from galaxy_test.base.api_asserts import (
    assert_has_keys,
    assert_status_code_is,
)
from galaxy_test.base.decorators import requires_new_history
from galaxy_test.base.populators import (
    BaseDatasetCollectionPopulator,
    DatasetCollectionPopulator,
    DatasetPopulator,
    skip_without_tool,
    stage_rules_example,
)
from ._framework import ApiTestCase

MINIMAL_TOOL = {
    "id": "minimal_tool",
    "name": "Minimal Tool",
    "class": "GalaxyTool",
    "version": "1.0.0",
    "command": "echo 'Hello World' > $output1",
    "inputs": [],
    "outputs": dict(
        output1=dict(format="txt"),
    ),
}
MINIMAL_TOOL_NO_ID = {
    "name": "Minimal Tool",
    "class": "GalaxyTool",
    "version": "1.0.0",
    "command": "echo 'Hello World 2' > $output1",
    "inputs": [],
    "outputs": dict(
        output1=dict(format="txt"),
    ),
}


class TestsTools:
    dataset_populator: DatasetPopulator
    dataset_collection_populator: BaseDatasetCollectionPopulator

    def _build_pair(self, history_id, contents):
        create_response = self.dataset_collection_populator.create_pair_in_history(
            history_id,
            contents=contents,
            direct_upload=True,
            wait=True,
        )
        hdca_id = create_response.json()["outputs"][0]["id"]
        return hdca_id

    def _run_cat(self, history_id, inputs, assert_ok=False, **kwargs):
        return self._run("cat", history_id, inputs, assert_ok=assert_ok, **kwargs)

    def _run(
        self,
        tool_id=None,
        history_id=None,
        inputs=None,
        tool_uuid=None,
        assert_ok=False,
        tool_version=None,
        use_cached_job=False,
        wait_for_job=False,
        input_format="legacy",
    ):
        if inputs is None:
            inputs = {}
        if tool_id is None:
            assert tool_uuid is not None
        payload = self.dataset_populator.run_tool_payload(
            tool_id=tool_id,
            inputs=inputs,
            history_id=history_id,
            input_format=input_format,
        )
        if tool_uuid:
            payload["tool_uuid"] = tool_uuid
        if tool_version is not None:
            payload["tool_version"] = tool_version
        if use_cached_job:
            payload["use_cached_job"] = True
        create_response = self.dataset_populator._post("tools", data=payload)
        if wait_for_job:
            self.dataset_populator.wait_for_job(job_id=create_response.json()["jobs"][0]["id"])
        if assert_ok:
            assert_status_code_is(create_response, 200)
            create = create_response.json()
            assert_has_keys(create, "outputs")
            return create
        else:
            return create_response


class TestToolsApi(ApiTestCase, TestsTools):
    dataset_populator: DatasetPopulator

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.dataset_collection_populator = DatasetCollectionPopulator(self.galaxy_interactor)

    def test_index(self):
        tool_ids = self.__tool_ids()
        assert "upload1" in tool_ids

    @skip_without_tool("cat1")
    def test_search_cat(self):
        url = self._api_url("tools")
        payload = dict(q="concat")
        get_response = get(url, payload).json()
        assert "cat1" in get_response

    @skip_without_tool("trimmer")
    def test_search_trimmer(self):
        url = self._api_url("tools")
        payload = dict(q="leading or trailing characters")
        get_response = get(url, payload).json()
        assert "trimmer" in get_response

    @skip_without_tool("Grep1")
    def test_search_grep(self):
        url = self._api_url("tools")
        payload = dict(q="Select lines that match an expression")
        get_response = get(url, payload).json()
        assert "Grep1" in get_response

    def test_no_panel_index(self):
        index = self._get("tools", data=dict(in_panel=False))
        tools_index = index.json()
        # No need to flatten out sections, with in_panel=False, only tools are
        # returned.
        tool_ids = [_["id"] for _ in tools_index]
        assert "upload1" in tool_ids

    @skip_without_tool("test_sam_to_bam_conversions")
    def test_requirements(self):
        requirements_response = self._get("tools/test_sam_to_bam_conversions/requirements", admin=True)
        self._assert_status_code_is_ok(requirements_response)
        requirements = requirements_response.json()
        assert len(requirements) == 1, requirements
        requirement = requirements[0]
        assert requirement["name"] == "samtools", requirement

    @skip_without_tool("cat1")
    def test_show_repeat(self):
        tool_info = self._show_valid_tool("cat1")
        parameters = tool_info["inputs"]
        assert len(parameters) == 2, f"Expected two inputs - got [{parameters}]"
        assert parameters[0]["name"] == "input1"
        assert parameters[1]["name"] == "queries"

        repeat_info = parameters[1]
        self._assert_has_keys(repeat_info, "min", "max", "title", "help")
        repeat_params = repeat_info["inputs"]
        assert len(repeat_params) == 1
        assert repeat_params[0]["name"] == "input2"

    @skip_without_tool("random_lines1")
    def test_show_conditional(self):
        tool_info = self._show_valid_tool("random_lines1")

        cond_info = tool_info["inputs"][2]
        self._assert_has_keys(cond_info, "cases", "test_param")
        self._assert_has_keys(cond_info["test_param"], "name", "type", "label", "help")

        cases = cond_info["cases"]
        assert len(cases) == 2
        case1 = cases[0]
        self._assert_has_keys(case1, "value", "inputs")
        assert case1["value"] == "no_seed"
        assert len(case1["inputs"]) == 0

        case2 = cases[1]
        self._assert_has_keys(case2, "value", "inputs")
        case2_inputs = case2["inputs"]
        assert len(case2_inputs) == 1
        self._assert_has_keys(case2_inputs[0], "name", "type", "label", "help", "argument")
        assert case2_inputs[0]["name"] == "seed"

    @skip_without_tool("gx_conditional_select")
    def test_invalid_conditional_payload_handled(self):
        with self.dataset_populator.test_history() as history_id:
            # Invalid request, should be `{"conditional_parameter": {"test_parameter": "A"}}`
            response = self._run(
                tool_id="gx_conditional_select", history_id=history_id, inputs={"conditional_parameter": "A"}
            )
            assert response.status_code == 400
            assert (
                response.json()["err_msg"]
                == "Invalid value 'A' submitted for conditional parameter 'conditional_parameter'."
            )

    @skip_without_tool("multi_data_param")
    def test_show_multi_data(self):
        tool_info = self._show_valid_tool("multi_data_param")

        f1_info, f2_info = tool_info["inputs"][0], tool_info["inputs"][1]
        self._assert_has_keys(f1_info, "min", "max")
        assert f1_info["min"] == 1
        assert f1_info["max"] == 1235

        self._assert_has_keys(f2_info, "min", "max")
        assert f2_info["min"] is None
        assert f2_info["max"] is None

    @skip_without_tool("collection_creates_list")
    def test_show_output_collection(self):
        tool_info = self._show_valid_tool("collection_creates_list")

        outputs = tool_info["outputs"]
        assert len(outputs) == 1
        output = outputs[0]
        assert output["label"] == "Duplicate List"
        assert output["inherit_format"] is True

    @skip_without_tool("test_data_source")
    def test_data_source_build_request(self):
        with self.dataset_populator.test_history() as history_id:
            build = self.dataset_populator.build_tool_state("test_data_source", history_id)
            galaxy_url_param = build["inputs"][0]
            assert galaxy_url_param["name"] == "GALAXY_URL"
            galaxy_url = galaxy_url_param["value"]
            assert galaxy_url.startswith("http")
            assert galaxy_url.endswith("tool_runner?tool_id=ratmine")

    @skip_without_tool("cheetah_problem_unbound_var_input")
    def test_legacy_biotools_xref_injection(self):
        url = self._api_url("tools/cheetah_problem_unbound_var_input")
        get_response = get(url)
        get_response.raise_for_status()
        get_json = get_response.json()
        assert "xrefs" in get_json
        assert len(get_json["xrefs"]) == 1
        xref = get_json["xrefs"][0]
        assert xref["reftype"] == "bio.tools"
        assert xref["value"] == "bwa"

    @skip_without_tool("test_data_source")
    @skip_if_github_down
    def test_data_source_ok_request(self):
        with self.dataset_populator.test_history() as history_id:
            payload = self.dataset_populator.run_tool_payload(
                tool_id="test_data_source",
                inputs={
                    "URL": "https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/1.bed",
                    "URL_method": "get",
                    "data_type": "bed",
                },
                history_id=history_id,
            )
            create_response = self._post("tools", data=payload)
            self._assert_status_code_is(create_response, 200)
            create_object = create_response.json()
            self._assert_has_keys(create_object, "outputs")
            assert len(create_object["outputs"]) == 1
            output = create_object["outputs"][0]
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            output_content = self.dataset_populator.get_history_dataset_content(history_id, dataset=output)
            assert output_content.startswith("chr1\t147962192\t147962580")

            output_details = self.dataset_populator.get_history_dataset_details(history_id, dataset=output)
            assert output_details["file_ext"] == "bed"

    @skip_without_tool("test_data_source")
    def test_data_source_sniff_fastqsanger(self):
        with self.dataset_populator.test_history() as history_id:
            payload = self.dataset_populator.run_tool_payload(
                tool_id="test_data_source",
                inputs={
                    "URL": "https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/1.fastqsanger.gz",
                    "URL_method": "get",
                },
                history_id=history_id,
            )
            create_response = self._post("tools", data=payload)
            self._assert_status_code_is(create_response, 200)
            create_object = create_response.json()
            self._assert_has_keys(create_object, "outputs")
            assert len(create_object["outputs"]) == 1
            output = create_object["outputs"][0]
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            output_details = self.dataset_populator.get_history_dataset_details(history_id, dataset=output)
            assert output_details["file_ext"] == "fastqsanger.gz", output_details

    @skip_without_tool("test_data_source")
    def test_data_sources_block_file_parameters(self):
        with self.dataset_populator.test_history() as history_id:
            payload = self.dataset_populator.run_tool_payload(
                tool_id="test_data_source",
                inputs={
                    "URL": f"file://{os.path.join(os.getcwd(), 'README.rst')}",
                    "URL_method": "get",
                    "data_type": "bed",
                },
                history_id=history_id,
            )
            create_response = self._post("tools", data=payload)
            self._assert_status_code_is(create_response, 200)
            create_object = create_response.json()
            self._assert_has_keys(create_object, "outputs")
            assert len(create_object["outputs"]) == 1
            output = create_object["outputs"][0]
            self.dataset_populator.wait_for_history(history_id, assert_ok=False)

            output_details = self.dataset_populator.get_history_dataset_details(history_id, dataset=output, wait=False)
            assert output_details["state"] == "error", output_details
            assert "has not sent back a URL parameter" in output_details["misc_info"], output_details

    def _show_valid_tool(self, tool_id, tool_version=None):
        data = dict(io_details=True)
        if tool_version:
            data["tool_version"] = tool_version
        tool_show_response = self._get(f"tools/{tool_id}", data=data)
        self._assert_status_code_is(tool_show_response, 200)
        tool_info = tool_show_response.json()
        self._assert_has_keys(tool_info, "inputs", "outputs", "panel_section_id")
        return tool_info

    @skip_without_tool("model_attributes")
    def test_model_attributes_sanitization(self):
        with self.dataset_populator.test_history(require_new=False) as history_id:
            cool_name_with_quote = 'cool name with a quo"te'
            cool_name_without_quote = "cool name with a quo__dq__te"

            current_user = self._get("users/current").json()
            user_info_url = self._api_url(f"users/{current_user['id']}/information/inputs", use_key=True)
            put_response = put(user_info_url, data=json.dumps({"address_0|desc": cool_name_with_quote}))
            put_response.raise_for_status()

            response = get(user_info_url).json()
            assert len(response["addresses"]) == 1
            assert response["addresses"][0]["desc"] == cool_name_with_quote

            hda1 = self.dataset_populator.new_dataset(history_id, content="1\t2\t3", name=cool_name_with_quote)
            assert hda1["name"] == cool_name_with_quote

            rval = self._run(
                tool_id="model_attributes",
                inputs={"input1": dataset_to_param(hda1)},
                history_id=history_id,
                assert_ok=True,
                wait_for_job=True,
            )
            sanitized_dataset_name = self.dataset_populator.get_history_dataset_content(
                history_id, dataset=rval["outputs"][0]
            )
            assert sanitized_dataset_name.strip() == cool_name_without_quote

            sanitized_email = self.dataset_populator.get_history_dataset_content(history_id, dataset=rval["outputs"][1])
            assert '"' not in sanitized_email

            sanitized_address = self.dataset_populator.get_history_dataset_content(
                history_id, dataset=rval["outputs"][2]
            )
            assert sanitized_address.strip() == cool_name_without_quote

    @skip_without_tool("composite_output")
    def test_test_data_filepath_security(self):
        test_data_response = self._get("tools/composite_output/test_data_path?filename=../CONTRIBUTORS.md", admin=True)
        assert test_data_response.status_code == 404, test_data_response.text

    @skip_without_tool("composite_output")
    def test_test_data_admin_security(self):
        test_data_response = self._get("tools/composite_output/test_data_path?filename=../CONTRIBUTORS.md")
        assert test_data_response.status_code == 403, test_data_response.text

    @skip_without_tool("dbkey_filter_multi_input")
    def test_data_table_requirement_annotated(self):
        test_data_response = self._get("tools/dbkey_filter_multi_input/test_data")
        assert test_data_response.status_code == 200
        test_case = test_data_response.json()[0]
        assert test_case["required_data_tables"][0] == "test_fasta_indexes"
        assert len(test_case["required_loc_files"]) == 0

    @skip_without_tool("composite_output")
    def test_test_data_composite_output(self):
        test_data_response = self._get("tools/composite_output/test_data")
        assert test_data_response.status_code == 200
        test_data = test_data_response.json()
        assert len(test_data) == 1
        test_case = test_data[0]
        self._assert_has_keys(test_case, "inputs", "outputs", "output_collections", "required_files")
        assert len(test_case["inputs"]) == 1, test_case
        # input0 = next(iter(test_case["inputs"].values()))

    @skip_without_tool("collection_two_paired")
    def test_test_data_collection_two_paired(self):
        test_data_response = self._get("tools/collection_two_paired/test_data")
        assert test_data_response.status_code == 200
        test_data = test_data_response.json()
        assert len(test_data) == 2
        test_case = test_data[0]
        assert len(test_case["required_data_tables"]) == 0
        assert len(test_case["required_loc_files"]) == 0
        self._assert_has_keys(test_case, "inputs", "outputs", "output_collections", "required_files")
        assert len(test_case["inputs"]) == 3, test_case

    @skip_without_tool("collection_nested_test")
    def test_test_data_collection_nested(self):
        test_data_response = self._get("tools/collection_nested_test/test_data")
        assert test_data_response.status_code == 200
        test_data = test_data_response.json()
        assert len(test_data) == 2
        test_case = test_data[0]
        self._assert_has_keys(test_case, "inputs", "outputs", "output_collections", "required_files")
        assert len(test_case["inputs"]) == 1, test_case

    @skip_without_tool("expression_null_handling_boolean")
    def test_test_data_null_boolean_inputs(self):
        test_data_response = self._get("tools/expression_null_handling_boolean/test_data")
        assert test_data_response.status_code == 200
        test_data = test_data_response.json()
        assert len(test_data) == 3
        test_case = test_data[2]
        self._assert_has_keys(test_case, "inputs", "outputs", "output_collections", "required_files")
        inputs = test_case["inputs"]
        assert len(inputs) == 1, test_case
        assert "bool_input" in inputs, inputs
        assert inputs["bool_input"] is None, inputs

    @skip_without_tool("simple_constructs_y")
    def test_test_data_yaml_tools(self):
        test_data_response = self._get("tools/simple_constructs_y/test_data")
        assert test_data_response.status_code == 200
        test_data = test_data_response.json()
        assert len(test_data) == 3

    @skip_without_tool("cat1")
    def test_test_data_download(self):
        test_data_response = self._get("tools/cat1/test_data_download?filename=1.bed")
        assert test_data_response.status_code == 200, test_data_response.text.startswith("chr")

    @skip_without_tool("composite_output")
    def test_test_data_downloads_security(self):
        test_data_response = self._get("tools/composite_output/test_data_download?filename=../CONTRIBUTORS.md")
        assert test_data_response.status_code == 404, test_data_response.text

    @skip_without_tool("composite_output")
    def test_test_data_download_composite(self):
        test_data_response = self._get("tools/composite_output/test_data_download?filename=velveth_test1")
        assert test_data_response.status_code == 200
        with zipfile.ZipFile(BytesIO(test_data_response.content)) as contents:
            namelist = contents.namelist()
        assert len(namelist) == 6
        expected_names = {
            "velveth_test1/Roadmaps",
            "velveth_test1/output.html",
            "velveth_test1/Sequences",
            "velveth_test1/Log",
            "velveth_test1/output/",
            "velveth_test1/output/1",
        }
        assert set(namelist) == expected_names

    def test_convert_dataset_explicit_history(self):
        with self.dataset_populator.test_history(require_new=False) as history_id:
            fasta1_contents = open(self.get_filename("1.fasta")).read()
            hda1 = self.dataset_populator.new_dataset(history_id, content=fasta1_contents)

            payload = {
                "src": "hda",
                "id": hda1["id"],
                "source_type": "fasta",
                "target_type": "tabular",
                "history_id": history_id,
            }
            create_response = self._post("tools/CONVERTER_fasta_to_tabular/convert", data=payload)
            self.dataset_populator.wait_for_job(create_response.json()["jobs"][0]["id"], assert_ok=True)
            create_response.raise_for_status()
            assert len(create_response.json()["implicit_collections"]) == 0
            for output in create_response.json()["outputs"]:
                assert output["file_ext"] == "tabular"

    def test_convert_dataset_implicit_history(self):
        with self.dataset_populator.test_history(require_new=False) as history_id:
            fasta1_contents = open(self.get_filename("1.fasta")).read()
            hda1 = self.dataset_populator.new_dataset(history_id, content=fasta1_contents)

            payload = {"src": "hda", "id": hda1["id"], "source_type": "fasta", "target_type": "tabular"}
            create_response = self._post("tools/CONVERTER_fasta_to_tabular/convert", data=payload)
            self.dataset_populator.wait_for_job(create_response.json()["jobs"][0]["id"], assert_ok=True)
            create_response.raise_for_status()
            assert len(create_response.json()["implicit_collections"]) == 0
            for output in create_response.json()["outputs"]:
                assert output["file_ext"] == "tabular"

    def test_convert_hdca(self):
        with self.dataset_populator.test_history(require_new=False) as history_id:
            data = [
                {
                    "name": "test0",
                    "elements": [
                        {"src": "pasted", "paste_content": "123\n", "name": "forward", "ext": "fasta"},
                        {"src": "pasted", "paste_content": "456\n", "name": "reverse", "ext": "fasta"},
                    ],
                },
                {
                    "name": "test1",
                    "elements": [
                        {"src": "pasted", "paste_content": "789\n", "name": "forward", "ext": "fasta"},
                        {"src": "pasted", "paste_content": "0ab\n", "name": "reverse", "ext": "fasta"},
                    ],
                },
            ]
            hdca1 = self.dataset_collection_populator.upload_collection(
                history_id, "list:paired", elements=data, wait=True
            )
            self._assert_status_code_is(hdca1, 200)

            payload = {
                "src": "hdca",
                "id": hdca1.json()["outputs"][0]["id"],
                "source_type": "fasta",
                "target_type": "tabular",
                "history_id": history_id,
            }
            create_response = self._post("tools/CONVERTER_fasta_to_tabular/convert", payload)
            create_response.raise_for_status()
            assert create_response.json()["implicit_collections"] != []
            hid = create_response.json()["implicit_collections"][0]["hid"]
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            collection_details = self.dataset_populator.get_history_collection_details(history_id, hid=hid)
            for element in collection_details["elements"][0]["object"]["elements"]:
                assert element["object"]["file_ext"] == "tabular"

    def test_unzip_collection(self):
        with self.dataset_populator.test_history(require_new=False) as history_id:
            hdca_id = self._build_pair(history_id, ["123", "456"])
            inputs = {
                "input": {"src": "hdca", "id": hdca_id},
            }
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            response = self._run("__UNZIP_COLLECTION__", history_id, inputs, assert_ok=True)
            outputs = response["outputs"]
            assert len(outputs) == 2
            output_forward = outputs[0]
            output_reverse = outputs[1]
            output_forward_content = self.dataset_populator.get_history_dataset_content(
                history_id, dataset=output_forward
            )
            output_reverse_content = self.dataset_populator.get_history_dataset_content(
                history_id, dataset=output_reverse
            )
            assert output_forward_content.strip() == "123"
            assert output_reverse_content.strip() == "456"

            output_forward = self.dataset_populator.get_history_dataset_details(history_id, dataset=output_forward)
            output_reverse = self.dataset_populator.get_history_dataset_details(history_id, dataset=output_reverse)

            assert output_forward["history_id"] == history_id
            assert output_reverse["history_id"] == history_id

    def test_unzip_nested(self):
        with self.dataset_populator.test_history(require_new=False) as history_id:
            response = self.dataset_collection_populator.upload_collection(
                history_id,
                "list:paired",
                elements=[
                    {
                        "name": "test0",
                        "elements": [
                            {
                                "src": "pasted",
                                "paste_content": "123\n",
                                "name": "forward",
                                "ext": "txt",
                                "tags": ["#foo"],
                            },
                            {
                                "src": "pasted",
                                "paste_content": "456\n",
                                "name": "reverse",
                                "ext": "txt",
                                "tags": ["#bar"],
                            },
                        ],
                    }
                ],
                wait=True,
            )
            self._assert_status_code_is(response, 200)
            hdca_id = response.json()["outputs"][0]["id"]
            inputs = {
                "input": {
                    "batch": True,
                    "values": [{"src": "hdca", "map_over_type": "paired", "id": hdca_id}],
                }
            }
            response = self._run("__UNZIP_COLLECTION__", history_id, inputs, assert_ok=True)
            implicit_collections = response["implicit_collections"]
            assert len(implicit_collections) == 2
            unzipped_hdca = self.dataset_populator.get_history_collection_details(
                history_id, hid=implicit_collections[0]["hid"]
            )
            assert unzipped_hdca["elements"][0]["element_type"] == "hda", unzipped_hdca

    def test_zip_inputs(self):
        with self.dataset_populator.test_history(require_new=False) as history_id:
            hda1 = dataset_to_param(self.dataset_populator.new_dataset(history_id, content="1\t2\t3"))
            hda2 = dataset_to_param(self.dataset_populator.new_dataset(history_id, content="4\t5\t6"))
            inputs = {
                "input_forward": hda1,
                "input_reverse": hda2,
            }
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            response = self._run("__ZIP_COLLECTION__", history_id, inputs, assert_ok=True)
            output_collections = response["output_collections"]
            assert len(output_collections) == 1
            self.dataset_populator.wait_for_job(response["jobs"][0]["id"], assert_ok=True)
            zipped_hdca = self.dataset_populator.get_history_collection_details(
                history_id, hid=output_collections[0]["hid"]
            )
            assert zipped_hdca["collection_type"] == "paired"

    @skip_without_tool("__ZIP_COLLECTION__")
    def test_collection_operation_dataset_input_permissions(self):
        with self.dataset_populator.test_history(require_new=False) as history_id:
            hda1 = dataset_to_param(self.dataset_populator.new_dataset(history_id, content="1\t2\t3"))
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            self.dataset_populator.make_private(history_id, hda1["id"])
            inputs = {
                "input_forward": hda1,
                "input_reverse": hda1,
            }
            with self._different_user_and_history() as other_history_id:
                response = self._run("__ZIP_COLLECTION__", other_history_id, inputs, assert_ok=False)
                self._assert_dataset_permission_denied_response(response)

    @skip_without_tool("__UNZIP_COLLECTION__")
    def test_collection_operation_collection_input_permissions(self):
        with self.dataset_populator.test_history(require_new=False) as history_id:
            create_response = self.dataset_collection_populator.create_pair_in_history(
                history_id, direct_upload=True, wait=True
            )
            self._assert_status_code_is(create_response, 200)
            collection = create_response.json()["outputs"][0]
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            collection = self.dataset_populator.get_history_collection_details(history_id, hid=collection["hid"])
            element_id = collection["elements"][0]["object"]["id"]
            self.dataset_populator.make_private(history_id, element_id)
            inputs = {
                "input": {"src": "hdca", "id": collection["id"]},
            }
            with self._different_user_and_history() as other_history_id:
                response = self._run("__UNZIP_COLLECTION__", other_history_id, inputs, assert_ok=False)
                self._assert_dataset_permission_denied_response(response)

    def test_zip_list_inputs(self):
        with self.dataset_populator.test_history(require_new=False) as history_id:
            hdca1_id = self.dataset_collection_populator.create_list_in_history(
                history_id, contents=["a\nb\nc\nd", "e\nf\ng\nh"], wait=True
            ).json()["outputs"][0]["id"]

            hdca2_id = self.dataset_collection_populator.create_list_in_history(
                history_id, contents=["1\n2\n3\n4", "5\n6\n7\n8"], wait=True
            ).json()["outputs"][0]["id"]
            inputs = {
                "input_forward": {"batch": True, "values": [{"src": "hdca", "id": hdca1_id}]},
                "input_reverse": {"batch": True, "values": [{"src": "hdca", "id": hdca2_id}]},
            }
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            response = self._run("__ZIP_COLLECTION__", history_id, inputs, assert_ok=True)
            implicit_collections = response["implicit_collections"]
            assert len(implicit_collections) == 1
            self.dataset_populator.wait_for_job(response["jobs"][0]["id"], assert_ok=True)
            zipped_hdca = self.dataset_populator.get_history_collection_details(
                history_id, hid=implicit_collections[0]["hid"]
            )
            assert zipped_hdca["collection_type"] == "list:paired"

    @skip_without_tool("__EXTRACT_DATASET__")
    @skip_without_tool("cat_data_and_sleep")
    def test_database_operation_tool_with_pending_inputs(self):
        with self.dataset_populator.test_history(require_new=False) as history_id:
            hdca1_id = self.dataset_collection_populator.create_list_in_history(
                history_id, contents=["a\nb\nc\nd", "e\nf\ng\nh"], wait=True
            ).json()["outputs"][0]["id"]
            run_response = self.dataset_populator.run_tool(
                tool_id="cat_data_and_sleep",
                inputs={
                    "sleep_time": 15,
                    "input1": {"batch": True, "values": [{"src": "hdca", "id": hdca1_id}]},
                },
                history_id=history_id,
            )
            output_hdca_id = run_response["implicit_collections"][0]["id"]
            run_response = self.dataset_populator.run_tool(
                tool_id="__EXTRACT_DATASET__",
                inputs={
                    "data_collection": {"src": "hdca", "id": output_hdca_id},
                },
                history_id=history_id,
            )
            assert run_response["outputs"][0]["state"] != "ok"

    @skip_without_tool("__EXTRACT_DATASET__")
    def test_extract_dataset_invalid_element_identifier(self):
        with self.dataset_populator.test_history(require_new=False) as history_id:
            hdca1_id = self.dataset_collection_populator.create_list_in_history(
                history_id, contents=["a\nb\nc\nd", "e\nf\ng\nh"], wait=True
            ).json()["outputs"][0]["id"]
            run_response = self.dataset_populator.run_tool_raw(
                tool_id="__EXTRACT_DATASET__",
                inputs={
                    "data_collection": {"src": "hdca", "id": hdca1_id},
                    "which": {"which_dataset": "by_index", "index": 100},
                },
                history_id=history_id,
                input_format="21.01",
            )
            assert run_response.status_code == 400
            assert run_response.json()["err_msg"] == "Dataset collection has no element_index with key 100."

    @skip_without_tool("__FILTER_FAILED_DATASETS__")
    def test_filter_failed_list(self):
        with self.dataset_populator.test_history(require_new=False) as history_id:
            ok_hdca_id = self.dataset_collection_populator.create_list_in_history(
                history_id, contents=["0", "1", "0", "1"], wait=True
            ).json()["outputs"][0]["id"]
            response = self.dataset_populator.run_exit_code_from_file(history_id, ok_hdca_id)

            mixed_implicit_collections = response["implicit_collections"]
            assert len(mixed_implicit_collections) == 1
            mixed_hdca_hid = mixed_implicit_collections[0]["hid"]
            mixed_hdca = self.dataset_populator.get_history_collection_details(
                history_id, hid=mixed_hdca_hid, wait=False
            )

            def get_state(dce):
                return dce["object"]["state"]

            mixed_states = [get_state(_) for _ in mixed_hdca["elements"]]
            assert mixed_states == ["ok", "error", "ok", "error"], mixed_states

            filtered_hdca = self._run_filter(history_id=history_id, failed_hdca_id=mixed_hdca["id"])
            filtered_states = [get_state(_) for _ in filtered_hdca["elements"]]
            assert filtered_states == ["ok", "ok"], filtered_states

    @skip_without_tool("__FILTER_FAILED_DATASETS__")
    def test_filter_failed_list_paired(self):
        with self.dataset_populator.test_history(require_new=False) as history_id:
            pair1 = self.dataset_collection_populator.create_pair_in_history(
                history_id, contents=["0", "0"], wait=True
            ).json()["outputs"][0]["id"]
            pair2 = self.dataset_collection_populator.create_pair_in_history(
                history_id, contents=["0", "1"], wait=True
            ).json()["outputs"][0]["id"]
            ok_hdca_id = self.dataset_collection_populator.create_list_from_pairs(history_id, [pair1, pair2]).json()[
                "id"
            ]
            response = self.dataset_populator.run_exit_code_from_file(history_id, ok_hdca_id)

            mixed_implicit_collections = response["implicit_collections"]
            assert len(mixed_implicit_collections) == 1
            mixed_hdca_hid = mixed_implicit_collections[0]["hid"]
            mixed_hdca = self.dataset_populator.get_history_collection_details(
                history_id, hid=mixed_hdca_hid, wait=False
            )

            def get_state(dce):
                return dce["object"]["state"]

            mixed_states = [get_state(element) for _ in mixed_hdca["elements"] for element in _["object"]["elements"]]
            assert mixed_states == ["ok", "ok", "ok", "error"], mixed_states

            filtered_hdca = self._run_filter(history_id=history_id, failed_hdca_id=mixed_hdca["id"])
            filtered_states = [
                get_state(element) for _ in filtered_hdca["elements"] for element in _["object"]["elements"]
            ]
            assert filtered_states == ["ok", "ok"], filtered_states

            # Also try list:list:paired
            llp = self.dataset_collection_populator.create_nested_collection(
                history_id=history_id, collection_type="list:list:paired", collection=[mixed_hdca["id"]]
            ).json()

            filtered_nested_hdca = self._run_filter(history_id=history_id, failed_hdca_id=llp["id"], batch=True)
            filtered_states = [
                get_state(element)
                for _ in filtered_nested_hdca["elements"]
                for parent_element in _["object"]["elements"]
                for element in parent_element["object"]["elements"]
            ]
            assert filtered_states == ["ok", "ok"], filtered_states

    def _run_filter(self, history_id, failed_hdca_id, batch=False):
        if batch:
            inputs = {
                "input": {
                    "batch": batch,
                    "values": [{"map_over_type": "list:paired", "src": "hdca", "id": failed_hdca_id}],
                },
            }
        else:
            inputs = {
                "input": {"batch": batch, "src": "hdca", "id": failed_hdca_id},
            }
        response = self._run("__FILTER_FAILED_DATASETS__", history_id, inputs, assert_ok=False).json()
        self.dataset_populator.wait_for_history(history_id, assert_ok=False)
        filter_output_collections = response["output_collections"]
        if batch:
            return response["implicit_collections"][0]
        assert len(filter_output_collections) == 1
        filtered_hid = filter_output_collections[0]["hid"]
        filtered_hdca = self.dataset_populator.get_history_collection_details(history_id, hid=filtered_hid, wait=False)
        return filtered_hdca

    def _apply_rules_and_check(self, example: Dict[str, Any]) -> None:
        with self.dataset_populator.test_history(require_new=False) as history_id:
            inputs = stage_rules_example(self.galaxy_interactor, history_id, example)
            hdca = inputs["input"]
            inputs = {"input": {"src": "hdca", "id": hdca["id"]}, "rules": example["rules"]}
            self.dataset_populator.wait_for_history(history_id)
            response = self._run("__APPLY_RULES__", history_id, inputs, assert_ok=True)
            output_collections = response["output_collections"]
            assert len(output_collections) == 1
            output_hid = output_collections[0]["hid"]
            output_hdca = self.dataset_populator.get_history_collection_details(history_id, hid=output_hid, wait=False)
            example["check"](output_hdca, self.dataset_populator)

    def test_apply_rules_1(self):
        self._apply_rules_and_check(rules_test_data.EXAMPLE_1)

    def test_apply_rules_2(self):
        self._apply_rules_and_check(rules_test_data.EXAMPLE_2)

    def test_apply_rules_3(self):
        self._apply_rules_and_check(rules_test_data.EXAMPLE_3)

    def test_apply_rules_4(self):
        self._apply_rules_and_check(rules_test_data.EXAMPLE_4)

    def test_apply_rules_5(self):
        self._apply_rules_and_check(rules_test_data.EXAMPLE_5)

    def test_apply_rules_6(self):
        self._apply_rules_and_check(rules_test_data.EXAMPLE_6)

    @skip_without_tool("galaxy_json_sleep")
    def test_dataset_hidden_after_job_finish(self):
        with self.dataset_populator.test_history() as history_id:
            inputs = {
                "sleep_time": 5,
            }
            response = self._run("galaxy_json_sleep", history_id, inputs, assert_ok=True)
            output = response["outputs"][0]
            response = self._put(
                f"histories/{history_id}/contents/datasets/{output['id']}", data={"visible": False}, json=True
            )
            response.raise_for_status()
            output_details = self.dataset_populator.get_history_dataset_details(history_id, dataset=output, wait=False)
            assert not output_details["visible"]
            output_details = self.dataset_populator.get_history_dataset_details(history_id, dataset=output, wait=True)
            assert not output_details["visible"]

    @skip_without_tool("gx_drill_down_exact")
    @skip_without_tool("gx_drill_down_exact_multiple")
    @skip_without_tool("gx_drill_down_recurse")
    @skip_without_tool("gx_drill_down_recurse_multiple")
    def test_drill_down_first_by_default(self):
        # we have a tool test for this but I wanted to verify it wasn't just the
        # tool test framework filling in a default. Creating a raw request here
        # verifies that currently select parameters don't require a selection.
        with self.dataset_populator.test_history(require_new=False) as history_id:
            inputs: Dict[str, Any] = {}
            response = self._run("gx_drill_down_exact", history_id, inputs, assert_ok=False)
            self._assert_status_code_is(response, 400)
            assert "an invalid option" in response.text

            response = self._run("gx_drill_down_exact_multiple", history_id, inputs, assert_ok=False)
            self._assert_status_code_is(response, 400)
            assert "an invalid option" in response.text

            response = self._run("gx_drill_down_recurse", history_id, inputs, assert_ok=False)
            self._assert_status_code_is(response, 400)
            assert "an invalid option" in response.text

            response = self._run("gx_drill_down_recurse_multiple", history_id, inputs, assert_ok=False)
            self._assert_status_code_is(response, 400)
            assert "an invalid option" in response.text

            # having an initially selected value - is useful for the UI but doesn't serve
            # as a default and doesn't make the drill down optional in a someway.
            response = self._run("gx_drill_down_exact_with_selection", history_id, inputs, assert_ok=True)
            output = response["outputs"][0]
            output1_content = self.dataset_populator.get_history_dataset_content(history_id, dataset=output)
            assert output1_content.strip() == "parameter: aba"

    def test_data_column_defaults(self):
        for input_format in ["legacy", "21.01"]:
            tabular_contents = "1\t2\t3\t\n4\t5\t6\n"
            with self.dataset_populator.test_history(require_new=True) as history_id:
                hda = dataset_to_param(
                    self.dataset_populator.new_dataset(history_id, content=tabular_contents, file_type="tabular")
                )
                details = self.dataset_populator.get_history_dataset_details(history_id, dataset=hda, assert_ok=True)
                inputs = {"ref_parameter": hda}
                response = self._run(
                    "gx_data_column", history_id, inputs, assert_ok=False, input_format=input_format
                ).json()
                output = response["outputs"]
                details = self.dataset_populator.get_history_dataset_details(
                    history_id, dataset=output[0], assert_ok=False
                )
                assert details["state"] == "ok"

                bed1_contents = open(self.get_filename("1.bed")).read()
                hda = dataset_to_param(
                    self.dataset_populator.new_dataset(history_id, content=bed1_contents, file_type="bed")
                )
                details = self.dataset_populator.get_history_dataset_details(history_id, dataset=hda, assert_ok=True)
                inputs = {"ref_parameter": hda}
                response = self._run(
                    "gx_data_column", history_id, inputs, assert_ok=False, input_format=input_format
                ).json()
                output = response["outputs"]
                details = self.dataset_populator.get_history_dataset_details(
                    history_id, dataset=output[0], assert_ok=False
                )
                assert details["state"] == "ok"

            with self.dataset_populator.test_history(require_new=False) as history_id:
                response = self._run("gx_data_column_multiple", history_id, inputs, assert_ok=False).json()
                assert "err_msg" in response, str(response)
                assert "Parameter 'parameter': an invalid option" in response["err_msg"]

            with self.dataset_populator.test_history(require_new=True) as history_id:
                response = self._run("gx_data_column_optional", history_id, inputs, assert_ok=True)
                output = response["outputs"]
                content = self.dataset_populator.get_history_dataset_content(history_id, dataset=output[0])
                assert "parameter: None" in content

                response = self._run("gx_data_column_with_default", history_id, inputs, assert_ok=True)
                output = response["outputs"]
                content = self.dataset_populator.get_history_dataset_content(history_id, dataset=output[0])
                assert "parameter: 2" in content

                response = self._run("gx_data_column_with_default_legacy", history_id, inputs, assert_ok=True)
                output = response["outputs"]
                content = self.dataset_populator.get_history_dataset_content(history_id, dataset=output[0])
                assert "parameter: 3" in content

                response = self._run("gx_data_column_accept_default", history_id, inputs, assert_ok=True)
                output = response["outputs"]
                content = self.dataset_populator.get_history_dataset_content(history_id, dataset=output[0])
                assert "parameter: 1" in content

                response = self._run("gx_data_column_multiple_with_default", history_id, inputs, assert_ok=True)
                output = response["outputs"]
                content = self.dataset_populator.get_history_dataset_content(history_id, dataset=output[0])
                assert "parameter: 1,2" in content

    @skip_without_tool("cat1")
    def test_run_cat1(self):
        with self.dataset_populator.test_history(require_new=False) as history_id:
            # Run simple non-upload tool with an input data parameter.
            new_dataset = self.dataset_populator.new_dataset(history_id, content="Cat1Test")
            inputs = dict(
                input1=dataset_to_param(new_dataset),
            )
            outputs = self._cat1_outputs(history_id, inputs=inputs)
            assert len(outputs) == 1
            output1 = outputs[0]
            output1_content = self.dataset_populator.get_history_dataset_content(history_id, dataset=output1)
            assert output1_content.strip() == "Cat1Test"

    def _get_cat1_inputs(self, history_id):
        new_dataset = self.dataset_populator.new_dataset(history_id, content="Cat1Test")
        inputs = dict(
            input1=dataset_to_param(new_dataset),
        )
        return inputs

    @skip_without_tool("cat1")
    @requires_new_history
    def test_run_cat1_use_cached_job(self):
        with self.dataset_populator.test_history_for(self.test_run_cat1_use_cached_job) as history_id:
            # Run simple non-upload tool with an input data parameter.
            inputs = self._get_cat1_inputs(history_id)
            outputs_one = self._run_cat1(history_id, inputs=inputs, assert_ok=True, wait_for_job=True)
            outputs_two = self._run_cat1(
                history_id, inputs=inputs, use_cached_job=False, assert_ok=True, wait_for_job=True
            )
            outputs_three = self._run_cat1(
                history_id, inputs=inputs, use_cached_job=True, assert_ok=True, wait_for_job=True
            )
            dataset_details = []
            for output in [outputs_one, outputs_two, outputs_three]:
                output_id = output["outputs"][0]["id"]
                dataset_details.append(self._get(f"datasets/{output_id}").json())
            filenames = [dd["file_name"] for dd in dataset_details]
            assert len(filenames) == 3, filenames
            assert len(set(filenames)) <= 2, filenames

    @skip_without_tool("cat1")
    @requires_new_history
    def test_run_cat1_use_cached_job_from_public_history(self):
        with self.dataset_populator.test_history_for(self.test_run_cat1_use_cached_job) as history_id:
            # Run simple non-upload tool with an input data parameter.
            inputs = self._get_cat1_inputs(history_id)
            original_output = self._run_cat1(history_id, inputs=inputs, assert_ok=True, wait_for_job=True)
            original_job = self.dataset_populator.get_job_details(original_output["jobs"][0]["id"], full=True).json()

            def run_again(user_email):
                with self._different_user_and_history(user_email=user_email) as different_history_id:
                    cached_output = self._run_cat1(
                        different_history_id, inputs=inputs, use_cached_job=True, assert_ok=True, wait_for_job=True
                    )
                    return self.dataset_populator.get_job_details(cached_output["jobs"][0]["id"], full=True).json()

            job = run_again(f"{uuid4()}@test.com")
            assert job["user_id"] != original_job["user_id"]
            assert not job["copied_from_job_id"]
            # publish history, now we can use cached job
            self.dataset_populator.make_public(history_id=history_id)
            cached_job = run_again(f"{uuid4()}@test.com")
            assert cached_job["user_id"] != original_job["user_id"]
            assert cached_job["copied_from_job_id"] == original_output["jobs"][0]["id"]

    @skip_without_tool("cat1")
    @requires_new_history
    def test_run_cat1_use_cached_job_renamed_input(self):
        with self.dataset_populator.test_history_for(self.test_run_cat1_use_cached_job_renamed_input) as history_id:
            # Run simple non-upload tool with an input data parameter.
            inputs = self._get_cat1_inputs(history_id)
            outputs_one = self._run_cat1(history_id, inputs=inputs, assert_ok=True, wait_for_job=True)
            # Rename inputs. Job should still be cached since cat1 doesn't look at name attribute
            self.dataset_populator.rename_dataset(inputs["input1"]["id"])
            outputs_two = self._run_cat1(
                history_id, inputs=inputs, use_cached_job=True, assert_ok=True, wait_for_job=True
            )
            copied_job_id = outputs_two["jobs"][0]["id"]
            job_details = self.dataset_populator.get_job_details(copied_job_id, full=True).json()
            assert job_details["copied_from_job_id"] == outputs_one["jobs"][0]["id"]

    @skip_without_tool("collection_creates_list")
    @requires_new_history
    def test_run_collection_creates_list_use_cached_job(self):
        with self.dataset_populator.test_history_for(
            self.test_run_collection_creates_list_use_cached_job
        ) as history_id:
            # Run tool that consumes and produces hdca
            create_response = self.dataset_collection_populator.create_list_in_history(
                history_id, contents=["123", "456"], wait=True
            ).json()
            hdca = create_response["output_collections"][0]
            outputs_one = self._run(
                "collection_creates_list",
                history_id,
                inputs={"input1": {"src": "hdca", "id": hdca["id"]}},
                assert_ok=True,
                wait_for_job=True,
            )
            outputs_two = self._run(
                "collection_creates_list",
                history_id,
                inputs={"input1": {"src": "hdca", "id": hdca["id"]}},
                assert_ok=True,
                wait_for_job=True,
                use_cached_job=True,
            )
            copied_job_id = outputs_two["jobs"][0]["id"]
            job_details = self.dataset_populator.get_job_details(copied_job_id, full=True).json()
            assert job_details["copied_from_job_id"] == outputs_one["jobs"][0]["id"]

    @skip_without_tool("collection_creates_list")
    @requires_new_history
    def test_run_collection_creates_list_use_cached_job_renamed_input(self):
        with self.dataset_populator.test_history_for(
            self.test_run_collection_creates_list_use_cached_job
        ) as history_id:
            # Run tool that consumes and produces hdca
            create_response = self.dataset_collection_populator.create_list_in_history(
                history_id, contents=["123", "456"], wait=True
            ).json()
            hdca = create_response["output_collections"][0]
            outputs_one = self._run(
                "collection_creates_list",
                history_id,
                inputs={"input1": {"src": "hdca", "id": hdca["id"]}},
                assert_ok=True,
                wait_for_job=True,
            )
            self.dataset_populator.rename_collection(history_id, hdca["id"])
            outputs_two = self._run(
                "collection_creates_list",
                history_id,
                inputs={"input1": {"src": "hdca", "id": hdca["id"]}},
                assert_ok=True,
                wait_for_job=True,
                use_cached_job=True,
            )
            copied_job_id = outputs_two["jobs"][0]["id"]
            job_details = self.dataset_populator.get_job_details(copied_job_id, full=True).json()
            assert job_details["copied_from_job_id"] == outputs_one["jobs"][0]["id"]

    @skip_without_tool("identifier_single")
    @requires_new_history
    def test_run_identifier_single_map_over_nested_collection_use_cached_job(self):
        with self.dataset_populator.test_history_for(
            self.test_run_identifier_single_use_cached_job_renamed_input
        ) as history_id:
            # Run tool that acccesses input.name (via input.element_identifier).
            hdca = self.dataset_collection_populator.create_list_of_list_in_history(history_id, wait=True).json()
            inputs = {"input1": {"batch": True, "values": [{"src": "hdca", "id": hdca["id"]}]}}
            outputs_one = self._run("identifier_single", history_id, inputs=inputs, assert_ok=True, wait_for_job=True)
            outputs_two = self._run(
                "identifier_single", history_id, inputs=inputs, use_cached_job=True, assert_ok=True, wait_for_job=True
            )
            copied_job_id = outputs_two["jobs"][0]["id"]
            job_details = self.dataset_populator.get_job_details(copied_job_id, full=True).json()
            assert job_details["copied_from_job_id"] == outputs_one["jobs"][0]["id"]

    @skip_without_tool("identifier_single")
    @requires_new_history
    def test_run_identifier_single_use_cached_job_renamed_input(self):
        with self.dataset_populator.test_history_for(
            self.test_run_identifier_single_use_cached_job_renamed_input
        ) as history_id:
            # Run tool that acccesses input.name (via input.element_identifier).
            inputs = self._get_cat1_inputs(history_id)
            self._run("identifier_single", history_id, inputs=inputs, assert_ok=True, wait_for_job=True)
            # Rename inputs. Job should not be cached since tool looks at name attribute
            self.dataset_populator.rename_dataset(inputs["input1"]["id"])
            outputs_two = self._run(
                "identifier_single", history_id, inputs=inputs, use_cached_job=True, assert_ok=True, wait_for_job=True
            )
            copied_job_id = outputs_two["jobs"][0]["id"]
            job_details = self.dataset_populator.get_job_details(copied_job_id, full=True).json()
            assert job_details["copied_from_job_id"] is None

    @skip_without_tool("collection_creates_dynamic_list_of_pairs")
    @requires_new_history
    def test_run_collection_creates_dynamic_list_of_pairs_use_cached_job(self):
        with self.dataset_populator.test_history_for(
            self.test_run_collection_creates_dynamic_list_of_pairs_use_cached_job
        ) as history_id:
            dataset = self.dataset_populator.new_dataset(history_id, content="123")
            outputs_one = self._run(
                "collection_creates_dynamic_list_of_pairs",
                history_id,
                inputs={"file": {"src": "hda", "id": dataset["id"]}, "foo": "abc"},
                assert_ok=True,
                wait_for_job=True,
                use_cached_job=False,
            )
            self.dataset_populator.rename_dataset(dataset["id"])
            outputs_two = self._run(
                "collection_creates_dynamic_list_of_pairs",
                history_id,
                inputs={"file": {"src": "hda", "id": dataset["id"]}, "foo": "abc"},
                assert_ok=True,
                wait_for_job=True,
                use_cached_job=True,
            )
            copied_job_id = outputs_two["jobs"][0]["id"]
            job_details = self.dataset_populator.get_job_details(copied_job_id, full=True).json()
            assert job_details["copied_from_job_id"] == outputs_one["jobs"][0]["id"]
            contents = self.dataset_populator.get_history_contents(history_id)
            # Make sure we add the correct number of output to the history
            # 1 input dataset
            # 2 output collections
            # with 6 HDAs each
            assert len(contents) == 15
            hdca_details = self.dataset_populator.get_history_collection_details(
                history_id=history_id, content_id=outputs_two["output_collections"][0]["id"]
            )
            assert hdca_details["collection_type"] == "list:paired"
            assert hdca_details["element_count"] == 3
            assert hdca_details["populated"]
            assert hdca_details["populated_state"] == "ok"
            assert hdca_details["elements_datatypes"] == ["fastqsanger"]

    @skip_without_tool("multi_output_assign_primary_ext_dbkey")
    @requires_new_history
    def test_run_multi_output_assign_primary_ext_dbkey_use_cached_job(self):
        with self.dataset_populator.test_history_for(
            self.test_run_multi_output_assign_primary_ext_dbkey_use_cached_job
        ) as history_id:
            dataset = self.dataset_populator.new_dataset(history_id, content="123")
            outputs_one = self._run(
                "multi_output_assign_primary_ext_dbkey",
                history_id,
                inputs={"input": {"src": "hda", "id": dataset["id"]}, "num_param": 1},
                assert_ok=True,
                wait_for_job=True,
                use_cached_job=False,
            )
            self.dataset_populator.rename_dataset(dataset["id"])
            outputs_two = self._run(
                "multi_output_assign_primary_ext_dbkey",
                history_id,
                inputs={"input": {"src": "hda", "id": dataset["id"]}, "num_param": 1},
                assert_ok=True,
                wait_for_job=True,
                use_cached_job=True,
            )
            copied_job_id = outputs_two["jobs"][0]["id"]
            job_details = self.dataset_populator.get_job_details(copied_job_id, full=True).json()
            assert job_details["copied_from_job_id"] == outputs_one["jobs"][0]["id"]
            contents = self.dataset_populator.get_history_contents(history_id)
            # Make sure we add the correct number of output to the history
            # 1 input dataset
            # 2 output datasets each
            assert len(contents) == 5

    @skip_without_tool("cat1")
    def test_run_cat1_listified_param(self):
        with self.dataset_populator.test_history_for(self.test_run_cat1_listified_param) as history_id:
            # Run simple non-upload tool with an input data parameter.
            new_dataset = self.dataset_populator.new_dataset(history_id, content="Cat1Testlistified")
            inputs = dict(
                input1=[dataset_to_param(new_dataset)],
            )
            outputs = self._cat1_outputs(history_id, inputs=inputs)
            assert len(outputs) == 1
            output1 = outputs[0]
            output1_content = self.dataset_populator.get_history_dataset_content(history_id, dataset=output1)
            assert output1_content.strip() == "Cat1Testlistified"

    @skip_without_tool("multiple_versions")
    def test_run_by_versions(self):
        with self.dataset_populator.test_history_for(self.test_run_by_versions) as history_id:
            for version in ["0.1", "0.2"]:
                # Run simple non-upload tool with an input data parameter.
                outputs = self._run_and_get_outputs(
                    tool_id="multiple_versions", history_id=history_id, tool_version=version
                )
                assert len(outputs) == 1
                output1 = outputs[0]
                output1_content = self.dataset_populator.get_history_dataset_content(history_id, dataset=output1)
                assert output1_content.strip() == f"Version {version}"

    @skip_without_tool("multiple_versions")
    def test_test_by_versions(self):
        test_data_response = self._get("tools/multiple_versions/test_data")
        test_data_response.raise_for_status()
        test_data_dicts = test_data_response.json()
        assert len(test_data_dicts) == 1
        assert test_data_dicts[0]["tool_version"] == "0.2"

        test_data_response = self._get("tools/multiple_versions/test_data?tool_version=*")
        test_data_response.raise_for_status()
        test_data_dicts = test_data_response.json()
        # this found a bug - tools that appear in the toolbox twice should not cause
        # multiple copies of test data to be returned. This assertion broke when
        # we placed multiple_versions in the test tool panel in multiple places. We need
        # to fix this but it isn't as important as the existing bug.
        # assert len(test_data_dicts) == 3

    @skip_without_tool("multiple_versions")
    def test_show_with_wrong_tool_version_in_tool_id(self):
        tool_info = self._show_valid_tool("multiple_versions", tool_version="0.01")
        # Return last version
        assert tool_info["version"] == "0.2"

    @skip_without_tool("cat1")
    def test_run_cat1_single_meta_wrapper(self):
        with self.dataset_populator.test_history_for(self.test_run_cat1_single_meta_wrapper) as history_id:
            # Wrap input in a no-op meta parameter wrapper like Sam is planning to
            # use for all UI API submissions.
            new_dataset = self.dataset_populator.new_dataset(history_id, content="123")
            inputs = dict(
                input1={"batch": False, "values": [dataset_to_param(new_dataset)]},
            )
            outputs = self._cat1_outputs(history_id, inputs=inputs)
            assert len(outputs) == 1
            output1 = outputs[0]
            output1_content = self.dataset_populator.get_history_dataset_content(history_id, dataset=output1)
            assert output1_content.strip() == "123"

    @skip_without_tool("cat1")
    @requires_new_history
    def test_guess_derived_permissions(self):
        with self.dataset_populator.test_history_for(self.test_run_cat1_single_meta_wrapper) as history_id:

            def assert_inputs(inputs, can_be_used=True):
                # Until we make the dataset private, _different_user() can use it:
                with self._different_user_and_history() as other_history_id:
                    response = self._run("cat1", other_history_id, inputs)
                    if can_be_used:
                        assert response.status_code == 200
                    else:
                        self._assert_dataset_permission_denied_response(response)

            new_dataset = self.dataset_populator.new_dataset(history_id, content="Cat1Test")
            inputs = dict(
                input1=dataset_to_param(new_dataset),
            )
            # Until we make the dataset private, _different_user() can use it:
            assert_inputs(inputs, can_be_used=True)
            self.dataset_populator.make_private(history_id, new_dataset["id"])
            # _different_user can no longer use the input dataset.
            assert_inputs(inputs, can_be_used=False)

            outputs = self._cat1_outputs(history_id, inputs=inputs)
            assert len(outputs) == 1
            output1 = outputs[0]

            inputs_2 = dict(
                input1=dataset_to_param(output1),
            )
            # _different_user cannot use datasets derived from the private input.
            assert_inputs(inputs_2, can_be_used=False)

    @skip_without_tool("collection_creates_list")
    def test_guess_derived_permissions_collections(self, history_id):
        def first_element_dataset_id(hdca):
            # Fetch full and updated details for HDCA
            print(hdca)
            full_hdca = self.dataset_populator.get_history_collection_details(history_id, hid=hdca["hid"])
            elements = full_hdca["elements"]
            element0 = elements[0]["object"]
            return element0["id"]

        response = self.dataset_collection_populator.create_list_in_history(
            history_id, contents=["a\nb\nc\nd", "e\nf\ng\nh"], direct_upload=True, wait=True
        )
        self._assert_status_code_is(response, 200)
        hdca = response.json()["output_collections"][0]
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        inputs = {
            "input1": {"src": "hdca", "id": hdca["id"]},
        }
        public_output_response = self._run("collection_creates_list", history_id, inputs)
        self._assert_status_code_is(public_output_response, 200)
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)

        input_element_id = first_element_dataset_id(hdca)
        self.dataset_populator.make_private(history_id, input_element_id)

        private_output_response = self._run("collection_creates_list", history_id, inputs)
        self._assert_status_code_is(private_output_response, 200)
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)

        public_element_id = first_element_dataset_id(public_output_response.json()["output_collections"][0])
        private_element_id = first_element_dataset_id(private_output_response.json()["output_collections"][0])

        def _dataset_accessible(dataset_id):
            contents_response = self._get(f"histories/{history_id}/contents/{dataset_id}").json()
            return "name" in contents_response

        with self._different_user():
            assert _dataset_accessible(public_element_id)
            assert not _dataset_accessible(private_element_id)

    @skip_without_tool("validation_default")
    def test_validation(self, history_id):
        inputs = {
            "select_param": '" ; echo "moo',
        }
        response = self._run("validation_default", history_id, inputs)
        self._assert_status_code_is(response, 400)

    @skip_without_tool("validation_empty_dataset")
    def test_validation_empty_dataset(self, history_id):
        outputs = self._run_and_get_outputs("empty_output", history_id)
        empty_dataset = outputs[0]
        inputs = {
            "input1": dataset_to_param(empty_dataset),
        }
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        response = self._run("validation_empty_dataset", history_id, inputs)
        self._assert_status_code_is(response, 400)

    @skip_without_tool("validation_repeat")
    def test_validation_in_repeat(self, history_id):
        inputs = {
            "r1_0|text": "123",
            "r2_0|text": "",
        }
        response = self._run("validation_repeat", history_id, inputs)
        self._assert_status_code_is(response, 400)

    @skip_without_tool("multi_select")
    def test_select_legal_values(self, history_id):
        inputs = {
            "select_ex": "not_option",
        }
        response = self._run("multi_select", history_id, inputs)
        self._assert_status_code_is(response, 400)

    @skip_without_tool("column_param")
    def test_column_legal_values(self, history_id):
        new_dataset1 = self.dataset_populator.new_dataset(history_id, content="#col1\tcol2")
        inputs = {
            "input1": {"src": "hda", "id": new_dataset1["id"]},
            "col": "' ; echo 'moo",
        }
        response = self._run("column_param", history_id, inputs)
        # This needs to either fail at submit time or at job prepare time, but we have
        # to make sure the job doesn't run.
        if response.status_code == 200:
            job = response.json()["jobs"][0]
            final_job_state = self.dataset_populator.wait_for_job(job["id"])
            assert final_job_state == "error"

    @requires_new_history
    @skip_without_tool("collection_paired_test")
    def test_collection_parameter(self, history_id):
        hdca_id = self._build_pair(history_id, ["123\n", "456\n"])
        inputs = {
            "f1": {"src": "hdca", "id": hdca_id},
        }
        output = self._run("collection_paired_test", history_id, inputs, assert_ok=True)
        assert len(output["jobs"]) == 1
        assert len(output["implicit_collections"]) == 0
        assert len(output["outputs"]) == 1
        contents = self.dataset_populator.get_history_dataset_content(history_id, hid=4)
        assert contents.strip() == "123\n456", contents

    @skip_without_tool("collection_creates_pair")
    def test_paired_collection_output(self, history_id):
        new_dataset1 = self.dataset_populator.new_dataset(history_id, content="123\n456\n789\n0ab")
        inputs = {
            "input1": {"src": "hda", "id": new_dataset1["id"]},
        }
        # TODO: shouldn't need this wait
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        create = self._run("collection_creates_pair", history_id, inputs, assert_ok=True)
        output_collection = self._assert_one_job_one_collection_run(create)
        element0, element1 = self._assert_elements_are(output_collection, "forward", "reverse")
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        self._verify_element(history_id, element0, contents="123\n789\n", file_ext="txt", visible=False)
        self._verify_element(history_id, element1, contents="456\n0ab\n", file_ext="txt", visible=False)

    @skip_without_tool("collection_creates_list")
    def test_list_collection_output(self, history_id):
        create_response = self.dataset_collection_populator.create_list_in_history(
            history_id, contents=["a\nb\nc\nd", "e\nf\ng\nh"], wait=True
        )
        hdca_id = create_response.json()["outputs"][0]["id"]
        create = self.dataset_populator.run_collection_creates_list(history_id, hdca_id)
        output_collection = self._assert_one_job_one_collection_run(create)
        element0, element1 = self._assert_elements_are(output_collection, "data0", "data1")
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        self._verify_element(history_id, element0, contents="identifier is data0\n", file_ext="txt")
        self._verify_element(history_id, element1, contents="identifier is data1\n", file_ext="txt")

    @skip_without_tool("collection_creates_list_2")
    def test_list_collection_output_format_source(self, history_id):
        # test using format_source with a tool
        new_dataset1 = self.dataset_populator.new_dataset(history_id, content="#col1\tcol2")
        create_response = self.dataset_collection_populator.create_list_in_history(
            history_id, contents=["a\tb\nc\td", "e\tf\ng\th"], wait=True
        )
        hdca_id = create_response.json()["outputs"][0]["id"]
        inputs = {
            "header": {"src": "hda", "id": new_dataset1["id"]},
            "input_collect": {"src": "hdca", "id": hdca_id},
        }
        # TODO: real problem here - shouldn't have to have this wait.
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        create = self._run("collection_creates_list_2", history_id, inputs, assert_ok=True)
        output_collection = self._assert_one_job_one_collection_run(create)
        element0, element1 = self._assert_elements_are(output_collection, "data0", "data1")
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        self._verify_element(history_id, element0, contents="#col1\tcol2\na\tb\nc\td\n", file_ext="txt")
        self._verify_element(history_id, element1, contents="#col1\tcol2\ne\tf\ng\th\n", file_ext="txt")

    @skip_without_tool("collection_split_on_column")
    def test_dynamic_list_output(self, history_id):
        new_dataset1 = self.dataset_populator.new_dataset(
            history_id, content="samp1\t1\nsamp1\t3\nsamp2\t2\nsamp2\t4\n"
        )
        inputs = {
            "input1": dataset_to_param(new_dataset1),
        }
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        create = self._run("collection_split_on_column", history_id, inputs, assert_ok=True)

        output_collection = self._assert_one_job_one_collection_run(create)
        self._assert_has_keys(output_collection, "id", "name", "elements", "populated")
        assert not output_collection["populated"]
        assert len(output_collection["elements"]) == 0
        assert output_collection["name"] == "Table split on first column"
        self.dataset_populator.wait_for_job(create["jobs"][0]["id"], assert_ok=True)

        get_collection_response = self._get(
            f"dataset_collections/{output_collection['id']}", data={"instance_type": "history"}
        )
        self._assert_status_code_is(get_collection_response, 200)

        output_collection = get_collection_response.json()
        self._assert_has_keys(output_collection, "id", "name", "elements", "populated")
        assert output_collection["populated"]
        assert output_collection["name"] == "Table split on first column"

        assert len(output_collection["elements"]) == 2
        output_element_0 = output_collection["elements"][0]
        assert output_element_0["element_index"] == 0
        assert output_element_0["element_identifier"] == "samp1"
        output_element_hda_0 = output_element_0["object"]
        assert output_element_hda_0["metadata_column_types"] is not None

    @skip_without_tool("collection_creates_dynamic_nested")
    def test_dynamic_list_output_datasets_in_failed_state(self, history_id):
        inputs = {"fail_bool": True}
        create = self._run("collection_creates_dynamic_nested", history_id, inputs, assert_ok=False, wait_for_job=True)
        self._assert_status_code_is(create, 200)
        collection = self._get(
            f"dataset_collections/{create.json()['output_collections'][0]['id']}", data={"instance_type": "history"}
        ).json()
        assert collection["element_count"] == 3
        for nested_collection in collection["elements"]:
            nested_collection = nested_collection["object"]
            assert nested_collection["element_count"] == 2
            for element in nested_collection["elements"]:
                assert element["object"]["state"] == "error"

    def test_nonadmin_users_cannot_create_tools(self):
        payload = dict(
            representation=json.dumps(MINIMAL_TOOL),
        )
        create_response = self._post("dynamic_tools", data=payload, admin=False)
        self._assert_status_code_is(create_response, 403)

    def test_dynamic_tool_1(self):
        # Create tool.
        self.dataset_populator.create_tool(MINIMAL_TOOL)

        # Run tool.
        history_id = self.dataset_populator.new_history()
        self._run("minimal_tool", history_id)

        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        output_content = self.dataset_populator.get_history_dataset_content(history_id)
        assert output_content == "Hello World\n"

    def test_dynamic_tool_from_path(self):
        # Create tool.
        dynamic_tool_path = os.path.join(
            galaxy_root_path, "lib", "galaxy_test", "base", "data", "minimal_tool_no_id.json"
        )
        tool_response = self.dataset_populator.create_tool_from_path(dynamic_tool_path)
        self._assert_has_keys(tool_response, "uuid")

        # Run tool.
        history_id = self.dataset_populator.new_history()
        self._run(history_id=history_id, tool_uuid=tool_response["uuid"])

        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        output_content = self.dataset_populator.get_history_dataset_content(history_id)
        assert output_content == "Hello World 2\n"

    def test_dynamic_tool_no_id(self):
        # Create tool.
        tool_response = self.dataset_populator.create_tool(MINIMAL_TOOL_NO_ID)
        self._assert_has_keys(tool_response, "uuid")

        # Run tool.
        history_id = self.dataset_populator.new_history()
        self._run(history_id=history_id, tool_uuid=tool_response["uuid"])

        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        output_content = self.dataset_populator.get_history_dataset_content(history_id)
        assert output_content == "Hello World 2\n"

    def test_show_dynamic_tools(self):
        # Create tool.
        original_list = self.dataset_populator.list_dynamic_tools()
        created_dynamic_tool_dict = self.dataset_populator.create_tool(MINIMAL_TOOL_NO_ID)
        self._assert_has_keys(created_dynamic_tool_dict, "id", "uuid", "active")
        created_id = created_dynamic_tool_dict["id"]
        created_uuid = created_dynamic_tool_dict["uuid"]
        new_list = self.dataset_populator.list_dynamic_tools()

        for dynamic_tool_dict in original_list:
            self._assert_has_keys(dynamic_tool_dict, "id", "uuid", "active")
            assert dynamic_tool_dict["id"] != created_id
            assert dynamic_tool_dict["uuid"] != created_uuid

        found_id = False
        found_uuid = False
        for dynamic_tool_dict in new_list:
            self._assert_has_keys(dynamic_tool_dict, "id", "uuid", "active")
            found_id = found_id or dynamic_tool_dict["id"] == created_id
            found_uuid = found_uuid or dynamic_tool_dict["uuid"] == created_uuid

        assert found_id
        assert found_uuid

    def test_show_tool_source_admin(self):
        response = self._get("tools/cat1/raw_tool_source", admin=True)
        response.raise_for_status()
        assert "Concatenate datasets" in response.text
        assert response.headers["language"] == "xml"

    def test_show_tool_source_denied(self):
        with self._different_user(anon=True):
            response = self._get("tools/cat1/raw_tool_source")
            assert response.status_code == 403

    def test_tool_deactivate(self):
        # Create tool.
        tool_response = self.dataset_populator.create_tool(MINIMAL_TOOL_NO_ID)
        self._assert_has_keys(tool_response, "id", "uuid", "active")
        assert tool_response["active"]
        deactivate_response = self.dataset_populator.deactivate_dynamic_tool(tool_response["uuid"])
        assert not deactivate_response["active"]

        # Run tool.
        history_id = self.dataset_populator.new_history()
        response = self._run(history_id=history_id, tool_uuid=tool_response["uuid"], assert_ok=False)
        # Get a 404 when trying to run a deactivated tool.
        self._assert_status_code_is(response, 404)

    @skip_without_tool("cat1")
    def test_run_cat1_with_two_inputs(self, history_id):
        # Run tool with an multiple data parameter and grouping (repeat)
        new_dataset1 = self.dataset_populator.new_dataset(history_id, content="Cat1Test")
        new_dataset2 = self.dataset_populator.new_dataset(history_id, content="Cat2Test")
        inputs = {"input1": dataset_to_param(new_dataset1), "queries_0|input2": dataset_to_param(new_dataset2)}
        outputs = self._cat1_outputs(history_id, inputs=inputs)
        assert len(outputs) == 1
        output1 = outputs[0]
        output1_content = self.dataset_populator.get_history_dataset_content(history_id, dataset=output1)
        assert output1_content.strip() == "Cat1Test\nCat2Test"

    @skip_without_tool("mapper_two")
    def test_bam_state_regression(self, history_id):
        # Test regression of https://github.com/galaxyproject/galaxy/issues/6856. With changes
        # to metadata file flushing to optimize creating bam outputs and copying bam datasets
        # we observed very subtle problems with HDA state changes on other files being flushed at
        # the same time. This tests txt datasets finalized before and after the bam outputs as
        # well as other bam files all flush properly during job completion.
        new_dataset1 = self.dataset_populator.new_dataset(history_id, content="123\n456\n789")
        inputs = {
            "input1": dataset_to_param(new_dataset1),
            "reference": dataset_to_param(new_dataset1),
        }
        outputs = self._run_and_get_outputs("mapper_two", history_id, inputs)
        assert len(outputs) == 4
        for output in outputs:
            details = self.dataset_populator.get_history_dataset_details(history_id, dataset=output)
            assert details["state"] == "ok"

    @skip_without_tool("qc_stdout")
    def test_qc_messages(self, history_id):
        new_dataset1 = self.dataset_populator.new_dataset(history_id, content="123\n456\n789")
        inputs = {
            "input1": dataset_to_param(new_dataset1),
            "quality": 3,
        }
        create = self._run("qc_stdout", history_id, inputs, wait_for_job=True, assert_ok=True)
        assert "jobs" in create, create
        job_id = create["jobs"][0]["id"]
        details = self.dataset_populator.get_job_details(job_id, full=True).json()
        assert "job_messages" in details, details
        # test autogenerated message (if regex defines no description attribute)
        qc_message = details["job_messages"][0]
        # assert qc_message["code_desc"] == "QC Metrics for Tool", qc_message
        assert qc_message["desc"] == "QC: Matched on Quality of sample is 30%."
        assert qc_message["match"] == "Quality of sample is 30%."
        assert qc_message["error_level"] == 1.1
        # test message generated from the description containing a reference to group defined in the regex
        qc_message = details["job_messages"][1]
        assert qc_message["desc"] == "QC: Sample quality 30"
        assert qc_message["match"] == "Quality of sample is 30%."
        assert qc_message["error_level"] == 1.1

    @skip_without_tool("cat1")
    def test_multirun_cat1(self, history_id):
        new_dataset1 = self.dataset_populator.new_dataset(history_id, content="123")
        new_dataset2 = self.dataset_populator.new_dataset(history_id, content="456")
        datasets = [dataset_to_param(new_dataset1), dataset_to_param(new_dataset2)]
        inputs = {
            "input1": {
                "batch": True,
                "values": datasets,
            },
        }
        self._check_cat1_multirun(history_id, inputs)

    def _check_cat1_multirun(self, history_id, inputs):
        outputs = self._cat1_outputs(history_id, inputs=inputs)
        assert len(outputs) == 2
        output1 = outputs[0]
        output2 = outputs[1]
        output1_content = self.dataset_populator.get_history_dataset_content(history_id, dataset=output1)
        output2_content = self.dataset_populator.get_history_dataset_content(history_id, dataset=output2)
        assert output1_content.strip() == "123"
        assert output2_content.strip() == "456"

    @skip_without_tool("random_lines1")
    def test_multirun_non_data_parameter(self, history_id):
        new_dataset1 = self.dataset_populator.new_dataset(history_id, content="123\n456\n789")
        inputs = {"input": dataset_to_param(new_dataset1), "num_lines": {"batch": True, "values": [1, 2, 3]}}
        outputs = self._run_and_get_outputs("random_lines1", history_id, inputs)
        # Assert we have three outputs with 1, 2, and 3 lines respectively.
        assert len(outputs) == 3
        outputs_contents = [
            self.dataset_populator.get_history_dataset_content(history_id, dataset=o).strip() for o in outputs
        ]
        assert sorted(len(c.split("\n")) for c in outputs_contents) == [1, 2, 3]

    @skip_without_tool("dbkey_output_action")
    def test_dynamic_parameter_error_handling(self):
        # Run test with valid index once, then supply invalid dbkey and invalid table
        # entry to ensure dynamic param errors are register.
        job_data_list = []

        def register_job_data(job_data):
            job_data_list.append(job_data)

        def tool_test_case_list(inputs, required_files) -> List[ValidToolTestDict]:
            return [
                {
                    "inputs": inputs,
                    "outputs": [],
                    "required_files": required_files,
                    "output_collections": [],
                    "test_index": 0,
                    "tool_version": "0.1.0",
                    "tool_id": "dbkey_output_action",
                    "error": False,
                }
            ]

        tool_test_dicts = tool_test_case_list(
            {
                "input": ["simple_line.txt"],
                "index": ["hg18_value"],
            },
            [["simple_line.txt", {"value": "simple_line.txt", "dbkey": "hg18"}]],
        )
        dynamic_param_error = None
        test_driver = self.driver_or_skip_test_if_remote()
        try:
            test_driver.run_tool_test("dbkey_output_action", _tool_test_dicts=tool_test_dicts)
        except Exception as e:
            dynamic_param_error = getattr(e, "dynamic_param_error", False)
        assert dynamic_param_error is None

        tool_test_dicts = tool_test_case_list(
            {
                "input": ["simple_line.txt"],
                "index": ["hg18_value"],
            },
            [["simple_line.txt", {"value": "simple_line.txt", "dbkey": "hgnot18"}]],
        )
        dynamic_param_error = None
        try:
            test_driver.run_tool_test("dbkey_output_action", _tool_test_dicts=tool_test_dicts)
        except Exception as e:
            dynamic_param_error = getattr(e, "dynamic_param_error", False)
        assert dynamic_param_error

        tool_test_dicts = tool_test_case_list(
            {
                "input": ["simple_line.txt"],
                "index": ["hgnot18"],
            },
            [["simple_line.txt", {"value": "simple_line.txt", "dbkey": "hg18"}]],
        )
        dynamic_param_error = None
        try:
            test_driver.run_tool_test(
                "dbkey_output_action", _tool_test_dicts=tool_test_dicts, register_job_data=register_job_data
            )
        except Exception as e:
            dynamic_param_error = getattr(e, "dynamic_param_error", False)
        assert dynamic_param_error
        assert len(job_data_list) == 1
        job_data = job_data_list[0]
        assert job_data["status"] == "error"
        job_data_list.clear()

        dynamic_param_error = None
        try:
            test_driver.run_tool_test(
                "dbkey_output_action",
                _tool_test_dicts=tool_test_dicts,
                skip_on_dynamic_param_errors=True,
                register_job_data=register_job_data,
            )
        except Exception as e:
            dynamic_param_error = getattr(e, "dynamic_param_error", False)
        assert dynamic_param_error
        assert len(job_data_list) == 1
        job_data = job_data_list[0]
        assert job_data["status"] == "skip"

    def _assert_one_job_one_collection_run(self, create):
        jobs = create["jobs"]
        implicit_collections = create["implicit_collections"]
        collections = create["output_collections"]

        assert len(jobs) == 1
        assert len(implicit_collections) == 0
        assert len(collections) == 1

        output_collection = collections[0]
        return output_collection

    def _assert_elements_are(self, collection, *args):
        elements = collection["elements"]
        assert len(elements) == len(args)
        for index, element in enumerate(elements):
            arg = args[index]
            assert arg == element["element_identifier"]
        return elements

    def _verify_element(self, history_id, element, **props):
        object_id = element["object"]["id"]

        if "contents" in props:
            expected_contents = props["contents"]

            contents = self.dataset_populator.get_history_dataset_content(history_id, dataset_id=object_id)
            assert contents == expected_contents

            del props["contents"]

        if props:
            details = self.dataset_populator.get_history_dataset_details(history_id, dataset_id=object_id)
            for key, value in props.items():
                assert details[key] == value

    @skip_without_tool("output_filter_with_input")
    def test_map_over_with_output_filter_no_filtering(self, history_id):
        hdca_id = self.dataset_collection_populator.create_list_in_history(history_id, wait=True).json()["outputs"][0][
            "id"
        ]
        inputs = {
            "input_1": {"batch": True, "values": [{"src": "hdca", "id": hdca_id}]},
            "produce_out_1": "true",
            "filter_text_1": "foo",
        }
        create = self._run("output_filter_with_input", history_id, inputs).json()
        jobs = create["jobs"]
        implicit_collections = create["implicit_collections"]
        assert len(jobs) == 3
        assert len(implicit_collections) == 3
        self._check_implicit_collection_populated(create)

    @skip_without_tool("output_filter_with_input_optional")
    def test_map_over_with_output_filter_on_optional_input(self, history_id):
        hdca_id = self.dataset_collection_populator.create_list_in_history(
            history_id, contents=["myinputs"], wait=True
        ).json()["outputs"][0]["id"]
        inputs = {
            "input_1": {"batch": True, "values": [{"src": "hdca", "id": hdca_id}]},
        }
        create = self._run("output_filter_with_input_optional", history_id, inputs).json()
        jobs = create["jobs"]
        implicit_collections = create["implicit_collections"]
        assert len(jobs) == 1
        self.dataset_populator.wait_for_job(jobs[0]["id"], assert_ok=True)
        assert len(implicit_collections) == 1
        self._check_implicit_collection_populated(create)

    @skip_without_tool("output_filter_with_input")
    def test_map_over_with_output_filter_one_filtered(self, history_id):
        hdca_id = self.dataset_collection_populator.create_list_in_history(history_id, wait=True).json()["outputs"][0][
            "id"
        ]
        inputs = {
            "input_1": {"batch": True, "values": [{"src": "hdca", "id": hdca_id}]},
            "produce_out_1": "true",
            "filter_text_1": "bar",
        }
        create = self._run("output_filter_with_input", history_id, inputs).json()
        jobs = create["jobs"]
        implicit_collections = create["implicit_collections"]
        assert len(jobs) == 3
        assert len(implicit_collections) == 2
        self._check_implicit_collection_populated(create)

    @skip_without_tool("Cut1")
    def test_map_over_with_complex_output_actions(self, history_id):
        hdca_id = self._bed_list(history_id)
        inputs = {
            "columnList": "c1,c2,c3,c4,c5",
            "delimiter": "T",
            "input": {"batch": True, "values": [{"src": "hdca", "id": hdca_id}]},
        }
        create = self._run("Cut1", history_id, inputs).json()
        outputs = create["outputs"]
        jobs = create["jobs"]
        implicit_collections = create["implicit_collections"]
        assert len(jobs) == 2
        assert len(outputs) == 2
        assert len(implicit_collections) == 1
        output1 = outputs[0]
        output2 = outputs[1]
        output1_content = self.dataset_populator.get_history_dataset_content(history_id, dataset=output1)
        output2_content = self.dataset_populator.get_history_dataset_content(history_id, dataset=output2)
        assert output1_content.startswith("chr1")
        assert output2_content.startswith("chr1")

    @skip_without_tool("collection_creates_dynamic_list_of_pairs")
    def test_map_over_with_discovered_output_collection_elements(self, history_id):
        hdca_id = self.dataset_collection_populator.create_list_in_history(history_id, wait=True).json()["outputs"][0][
            "id"
        ]
        inputs = {"input": {"batch": True, "values": [{"src": "hdca", "id": hdca_id}]}}
        create = self._run("collection_creates_dynamic_list_of_pairs", history_id, inputs).json()
        implicit_collections = create["implicit_collections"]
        assert len(implicit_collections) == 1
        assert implicit_collections[0]["collection_type"] == "list:list:paired"
        assert implicit_collections[0]["elements"][0]["object"]["element_count"] is None
        self.dataset_populator.wait_for_job(create["jobs"][0]["id"], assert_ok=True)
        hdca = self._get(f"histories/{history_id}/contents/dataset_collections/{implicit_collections[0]['id']}").json()
        assert hdca["elements"][0]["object"]["elements"][0]["object"]["elements"][0]["element_identifier"] == "forward"

    def _bed_list(self, history_id):
        bed1_contents = open(self.get_filename("1.bed")).read()
        bed2_contents = open(self.get_filename("2.bed")).read()
        contents = [bed1_contents, bed2_contents]
        hdca = self.dataset_collection_populator.create_list_in_history(history_id, contents=contents, wait=True).json()
        return hdca["outputs"][0]["id"]

    @skip_without_tool("identifier_single")
    def test_identifier_in_map(self, history_id):
        hdca_id = self._build_pair(history_id, ["123", "456"])
        inputs = {
            "input1": {"batch": True, "values": [{"src": "hdca", "id": hdca_id}]},
        }
        create_response = self._run("identifier_single", history_id, inputs)
        self._assert_status_code_is(create_response, 200)
        create = create_response.json()
        outputs = create["outputs"]
        jobs = create["jobs"]
        implicit_collections = create["implicit_collections"]
        assert len(jobs) == 2
        assert len(outputs) == 2
        assert len(implicit_collections) == 1
        output1 = outputs[0]
        output2 = outputs[1]
        output1_content = self.dataset_populator.get_history_dataset_content(history_id, dataset=output1)
        output2_content = self.dataset_populator.get_history_dataset_content(history_id, dataset=output2)
        assert output1_content.strip() == "forward"
        assert output2_content.strip() == "reverse"

    @skip_without_tool("identifier_single")
    def test_identifier_outside_map(self, history_id):
        new_dataset1 = self.dataset_populator.new_dataset(history_id, content="123", name="Plain HDA")
        inputs = {
            "input1": {"src": "hda", "id": new_dataset1["id"]},
        }
        create_response = self._run("identifier_single", history_id, inputs)
        self._assert_status_code_is(create_response, 200)
        create = create_response.json()
        outputs = create["outputs"]
        jobs = create["jobs"]
        implicit_collections = create["implicit_collections"]
        assert len(jobs) == 1
        assert len(outputs) == 1
        assert len(implicit_collections) == 0
        output1 = outputs[0]
        output1_content = self.dataset_populator.get_history_dataset_content(history_id, dataset=output1)
        assert output1_content.strip() == "Plain HDA"

    @skip_without_tool("identifier_multiple")
    def test_list_selectable_in_multidata_input(self, history_id):
        self.dataset_collection_populator.create_list_in_history(history_id, contents=["123", "456"], wait=True)
        build = self.dataset_populator.build_tool_state("identifier_multiple", history_id)
        assert len(build["inputs"][0]["options"]["hdca"]) == 1

    @skip_without_tool("identifier_in_conditional")
    def test_identifier_map_over_input_in_conditional(self, history_id):
        # Run cat tool, so HDA names are different from element identifiers
        hdca_id = self._build_pair(history_id, ["123", "456"], run_cat=True)
        inputs = {
            "outer_cond|input1": {"batch": True, "values": [{"src": "hdca", "id": hdca_id}]},
            "outer_cond|multi_input": False,
        }
        execute = (
            self.dataset_populator.describe_tool_execution("identifier_in_conditional")
            .in_history(history_id)
            .with_inputs(inputs)
        )
        collection = execute.assert_has_n_jobs(2).assert_creates_implicit_collection(0)
        collection.assert_has_dataset_element("forward").with_contents_stripped("forward")
        collection.assert_has_dataset_element("reverse").with_contents_stripped("reverse")

    @skip_without_tool("identifier_multiple_in_conditional")
    def test_identifier_multiple_reduce_in_conditional(self, history_id):
        hdca_id = self._build_pair(history_id, ["123", "456"])
        inputs = {
            "outer_cond|inner_cond|input1": {"src": "hdca", "id": hdca_id},
        }
        create_response = self._run("identifier_multiple_in_conditional", history_id, inputs)
        self._assert_status_code_is(create_response, 200)
        create = create_response.json()
        outputs = create["outputs"]
        jobs = create["jobs"]
        implicit_collections = create["implicit_collections"]
        assert len(jobs) == 1
        assert len(outputs) == 1
        assert len(implicit_collections) == 0
        output1 = outputs[0]
        output1_content = self.dataset_populator.get_history_dataset_content(history_id, dataset=output1)
        assert output1_content.strip() == "forward\nreverse"

    @skip_without_tool("cat1")
    def test_map_over_nested_collections(self, history_id):
        hdca_id = self.__build_nested_list(history_id)
        inputs = {
            "input1": {"batch": True, "values": [dict(src="hdca", id=hdca_id)]},
        }
        self._check_simple_cat1_over_nested_collections(history_id, inputs)

    @skip_without_tool("collection_paired_structured_like")
    def test_paired_input_map_over_nested_collections(self, history_id):
        hdca_id = self.__build_nested_list(history_id)
        inputs = {
            "input1": {"batch": True, "values": [dict(map_over_type="paired", src="hdca", id=hdca_id)]},
        }
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        create = self._run("collection_paired_structured_like", history_id, inputs, assert_ok=True)
        jobs = create["jobs"]
        implicit_collections = create["implicit_collections"]
        assert len(jobs) == 2
        assert len(implicit_collections) == 1
        implicit_collection = implicit_collections[0]
        assert implicit_collection["collection_type"] == "list:paired", implicit_collection["collection_type"]
        outer_elements = implicit_collection["elements"]
        assert len(outer_elements) == 2

    @skip_without_tool("collection_paired_conditional_structured_like")
    def test_paired_input_conditional_map_over_nested_collections(self, history_id):
        hdca_id = self.__build_nested_list(history_id)
        inputs = {
            "cond|cond_param": "paired",
            "cond|input1": {"batch": True, "values": [dict(map_over_type="paired", src="hdca", id=hdca_id)]},
        }
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        create = self._run("collection_paired_conditional_structured_like", history_id, inputs, assert_ok=True)
        jobs = create["jobs"]
        implicit_collections = create["implicit_collections"]
        assert len(jobs) == 2
        assert len(implicit_collections) == 1
        implicit_collection = implicit_collections[0]
        assert implicit_collection["collection_type"] == "list:paired", implicit_collection["collection_type"]
        outer_elements = implicit_collection["elements"]
        assert len(outer_elements) == 2

    def _check_simple_cat1_over_nested_collections(self, history_id, inputs):
        create = self._run_cat1(history_id, inputs=inputs, assert_ok=True)
        outputs = create["outputs"]
        jobs = create["jobs"]
        implicit_collections = create["implicit_collections"]
        assert len(jobs) == 4
        assert len(outputs) == 4
        assert len(implicit_collections) == 1
        implicit_collection = implicit_collections[0]
        self._assert_has_keys(implicit_collection, "collection_type", "elements")
        assert implicit_collection["collection_type"] == "list:paired"
        assert len(implicit_collection["elements"]) == 2
        first_element, second_element = implicit_collection["elements"]
        assert first_element["element_identifier"] == "test0", first_element
        assert second_element["element_identifier"] == "test1", second_element

        first_object = first_element["object"]
        assert first_object["collection_type"] == "paired"
        assert len(first_object["elements"]) == 2
        first_object_forward_element = first_object["elements"][0]
        assert outputs[0]["id"] == first_object_forward_element["object"]["id"]

    @skip_without_tool("cat1")
    def test_map_over_two_collections(self, history_id):
        hdca1_id = self._build_pair(history_id, ["123\n", "456\n"])
        hdca2_id = self._build_pair(history_id, ["789\n", "0ab\n"])
        inputs = {
            "input1": {"batch": True, "values": [{"src": "hdca", "id": hdca1_id}]},
            "queries_0|input2": {"batch": True, "values": [{"src": "hdca", "id": hdca2_id}]},
        }
        self._check_map_cat1_over_two_collections(history_id, inputs)

    def _check_map_cat1_over_two_collections(self, history_id, inputs):
        response = self._run_cat1(history_id, inputs)
        self._assert_status_code_is(response, 200)
        response_object = response.json()
        outputs = response_object["outputs"]
        assert len(outputs) == 2
        output1 = outputs[0]
        output2 = outputs[1]
        self.dataset_populator.wait_for_history(history_id)
        output1_content = self.dataset_populator.get_history_dataset_content(history_id, dataset=output1)
        output2_content = self.dataset_populator.get_history_dataset_content(history_id, dataset=output2)
        assert output1_content.strip() == "123\n789"
        assert output2_content.strip() == "456\n0ab"

        assert len(response_object["jobs"]) == 2
        assert len(response_object["implicit_collections"]) == 1

    @skip_without_tool("cat1")
    def test_map_over_two_collections_unlinked(self, history_id):
        hdca1_id = self._build_pair(history_id, ["123\n", "456\n"])
        hdca2_id = self._build_pair(history_id, ["789\n", "0ab\n"])
        inputs = {
            "input1": {"batch": True, "linked": False, "values": [{"src": "hdca", "id": hdca1_id}]},
            "queries_0|input2": {"batch": True, "linked": False, "values": [{"src": "hdca", "id": hdca2_id}]},
        }
        response = self._run_cat1(history_id, inputs)
        self._assert_status_code_is(response, 200)
        response_object = response.json()
        outputs = response_object["outputs"]
        assert len(outputs) == 4

        assert len(response_object["jobs"]) == 4
        implicit_collections = response_object["implicit_collections"]
        assert len(implicit_collections) == 1
        implicit_collection = implicit_collections[0]
        assert implicit_collection["collection_type"] == "paired:paired"

        outer_elements = implicit_collection["elements"]
        assert len(outer_elements) == 2
        element0, element1 = outer_elements
        assert element0["element_identifier"] == "forward"
        assert element1["element_identifier"] == "reverse"

        elements0 = element0["object"]["elements"]
        elements1 = element1["object"]["elements"]

        assert len(elements0) == 2
        assert len(elements1) == 2

        element00, element01 = elements0
        assert element00["element_identifier"] == "forward"
        assert element01["element_identifier"] == "reverse"

        element10, element11 = elements1
        assert element10["element_identifier"] == "forward"
        assert element11["element_identifier"] == "reverse"

        expected_contents_list = [
            (element00, "123\n789\n"),
            (element01, "123\n0ab\n"),
            (element10, "456\n789\n"),
            (element11, "456\n0ab\n"),
        ]
        for element, expected_contents in expected_contents_list:
            dataset_id = element["object"]["id"]
            contents = self.dataset_populator.get_history_dataset_content(history_id, dataset_id=dataset_id)
            assert expected_contents == contents

    @skip_without_tool("cat1")
    def test_map_over_collected_and_individual_datasets(self, history_id):
        hdca1_id = self._build_pair(history_id, ["123\n", "456\n"])
        new_dataset1 = self.dataset_populator.new_dataset(history_id, content="789")
        new_dataset2 = self.dataset_populator.new_dataset(history_id, content="0ab")

        inputs = {
            "input1": {"batch": True, "values": [{"src": "hdca", "id": hdca1_id}]},
            "queries_0|input2": {
                "batch": True,
                "values": [dataset_to_param(new_dataset1), dataset_to_param(new_dataset2)],
            },
        }
        response = self._run_cat1(history_id, inputs)
        self._assert_status_code_is(response, 200)
        response_object = response.json()
        outputs = response_object["outputs"]
        assert len(outputs) == 2

        assert len(response_object["jobs"]) == 2
        assert len(response_object["implicit_collections"]) == 1

    @skip_without_tool("identifier_source")
    def test_default_identifier_source_map_over(self):
        with self.dataset_populator.test_history() as history_id:
            input_a_hdca_id = self.dataset_collection_populator.create_list_in_history(
                history_id, contents=[("A", "A content")], wait=True
            ).json()["outputs"][0]["id"]
            input_b_hdca_id = self.dataset_collection_populator.create_list_in_history(
                history_id, contents=[("B", "B content")], wait=True
            ).json()["outputs"][0]["id"]
            inputs = {
                "inputA": {"batch": True, "values": [dict(src="hdca", id=input_a_hdca_id)]},
                "inputB": {"batch": True, "values": [dict(src="hdca", id=input_b_hdca_id)]},
            }
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            create = self._run("identifier_source", history_id, inputs, assert_ok=True)
            for implicit_collection in create["implicit_collections"]:
                if implicit_collection["output_name"] == "outputA":
                    assert implicit_collection["elements"][0]["element_identifier"] == "A"
                else:
                    assert implicit_collection["elements"][0]["element_identifier"] == "B"

    @skip_without_tool("collection_creates_pair")
    def test_map_over_collection_output(self):
        with self.dataset_populator.test_history() as history_id:
            create_response = self.dataset_collection_populator.create_list_in_history(
                history_id, contents=["a\nb\nc\nd", "e\nf\ng\nh"], wait=True
            )
            hdca_id = create_response.json()["outputs"][0]["id"]
            inputs = {
                "input1": {"batch": True, "values": [dict(src="hdca", id=hdca_id)]},
            }
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            create = self._run("collection_creates_pair", history_id, inputs, assert_ok=True)
            jobs = create["jobs"]
            implicit_collections = create["implicit_collections"]
            assert len(jobs) == 2
            assert len(implicit_collections) == 1
            implicit_collection = implicit_collections[0]
            assert implicit_collection["collection_type"] == "list:paired", implicit_collection
            outer_elements = implicit_collection["elements"]
            assert len(outer_elements) == 2
            element0, element1 = outer_elements
            assert element0["element_identifier"] == "data0"
            assert element1["element_identifier"] == "data1"

            pair0, pair1 = element0["object"], element1["object"]
            pair00, pair01 = pair0["elements"]
            pair10, pair11 = pair1["elements"]

            for pair in pair0, pair1:
                assert "collection_type" in pair, pair
                assert pair["collection_type"] == "paired", pair

            pair_ids = []
            for pair_element in pair00, pair01, pair10, pair11:
                assert "object" in pair_element
                pair_ids.append(pair_element["object"]["id"])

            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            expected_contents = [
                "a\nc\n",
                "b\nd\n",
                "e\ng\n",
                "f\nh\n",
            ]
            for i in range(4):
                contents = self.dataset_populator.get_history_dataset_content(history_id, dataset_id=pair_ids[i])
                assert expected_contents[i] == contents

    @skip_without_tool("cat1")
    def test_cannot_map_over_incompatible_collections(self):
        with self.dataset_populator.test_history() as history_id:
            hdca1_id = self._build_pair(history_id, ["123\n", "456\n"])
            hdca2_id = self.dataset_collection_populator.create_list_in_history(history_id).json()["outputs"][0]["id"]
            inputs = {
                "input1": {
                    "batch": True,
                    "values": [{"src": "hdca", "id": hdca1_id}],
                },
                "queries_0|input2": {
                    "batch": True,
                    "values": [{"src": "hdca", "id": hdca2_id}],
                },
            }
            run_response = self._run_cat1(history_id, inputs)
            # TODO: Fix this error checking once switch over to new API decorator
            # on server.
            assert run_response.status_code >= 400

    @skip_without_tool("__FILTER_FROM_FILE__")
    def test_map_over_collection_structured_like(self):
        with self.dataset_populator.test_history() as history_id:
            hdca_id = self.dataset_collection_populator.create_list_in_history(
                history_id, contents=[("A", "A"), ("B", "B")], wait=True
            ).json()["outputs"][0]["id"]
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            inputs = {
                "input": {"values": [dict(src="hdca", id=hdca_id)]},
                "how|filter_source": {"batch": True, "values": [dict(src="hdca", id=hdca_id)]},
            }
            implicit_collections = self._run("__FILTER_FROM_FILE__", history_id, inputs, assert_ok=True)[
                "implicit_collections"
            ]
            discarded_collection, filtered_collection = implicit_collections
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            history_contents = self.dataset_populator._get_contents_request(history_id).json()
            # We should have a final collection count of 3 (2 nested collections, plus the input collection)
            new_collections = (
                len([c for c in history_contents if c["history_content_type"] == "dataset_collection"]) - 1
            )
            assert (
                new_collections == 2
            ), f"Expected to generate 4 new, filtered collections, but got {new_collections} collections"
            assert (
                filtered_collection["collection_type"] == discarded_collection["collection_type"] == "list:list"
            ), filtered_collection
            collection_details = self.dataset_populator.get_history_collection_details(
                history_id, hid=filtered_collection["hid"]
            )
            assert collection_details["element_count"] == 2
            first_collection_level = collection_details["elements"][0]
            assert first_collection_level["element_type"] == "dataset_collection"
            second_collection_level = first_collection_level["object"]
            assert second_collection_level["collection_type"] == "list"
            assert second_collection_level["elements"][0]["element_type"] == "hda"

    @skip_without_tool("collection_type_source")
    def test_map_over_collection_type_source(self):
        with self.dataset_populator.test_history() as history_id:
            hdca_id = self.dataset_collection_populator.create_list_in_history(
                history_id, contents=[("A", "A"), ("B", "B")], wait=True
            ).json()["outputs"][0]["id"]
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            inputs = {
                "input_collect": {"values": [dict(src="hdca", id=hdca_id)]},
                "header": {"batch": True, "values": [dict(src="hdca", id=hdca_id)]},
            }
            self._run("collection_type_source", history_id, inputs, assert_ok=True, wait_for_job=True)
            collection_details = self.dataset_populator.get_history_collection_details(history_id, hid=4)
            assert collection_details["elements"][0]["object"]["elements"][0]["element_type"] == "hda"

    @skip_without_tool("multi_data_param")
    def test_reduce_collections_legacy(self):
        with self.dataset_populator.test_history() as history_id:
            hdca1_id = self._build_pair(history_id, ["123\n", "456\n"])
            hdca2_id = self.dataset_collection_populator.create_list_in_history(history_id, wait=True).json()[
                "outputs"
            ][0]["id"]
            inputs = {
                "f1": f"__collection_reduce__|{hdca1_id}",
                "f2": f"__collection_reduce__|{hdca2_id}",
            }
            self._check_simple_reduce_job(history_id, inputs)

    @skip_without_tool("multi_data_param")
    def test_reduce_collections(self):
        with self.dataset_populator.test_history() as history_id:
            hdca1_id = self._build_pair(history_id, ["123\n", "456\n"])
            hdca2_id = self.dataset_collection_populator.create_list_in_history(history_id, wait=True).json()[
                "outputs"
            ][0]["id"]
            inputs = {
                "f1": {"src": "hdca", "id": hdca1_id},
                "f2": {"src": "hdca", "id": hdca2_id},
            }
            self._check_simple_reduce_job(history_id, inputs)

    @skip_without_tool("multi_data_param")
    def test_implicit_reduce_with_mapping(self):
        with self.dataset_populator.test_history() as history_id:
            hdca1_id = self._build_pair(history_id, ["123\n", "456\n"])
            hdca2_id = self.dataset_collection_populator.create_list_of_list_in_history(history_id, wait=True).json()[
                "id"
            ]
            inputs = {
                "f1": {"src": "hdca", "id": hdca1_id},
                "f2": {
                    "batch": True,
                    "values": [{"src": "hdca", "map_over_type": "list", "id": hdca2_id}],
                },
            }
            create = self._run("multi_data_param", history_id, inputs, assert_ok=True)
            jobs = create["jobs"]
            implicit_collections = create["implicit_collections"]
            assert len(jobs) == 1
            assert len(implicit_collections) == 2
            output_hdca = self.dataset_populator.get_history_collection_details(
                history_id, hid=implicit_collections[0]["hid"]
            )
            assert output_hdca["collection_type"] == "list"

    @skip_without_tool("column_multi_param")
    def test_multi_param_column_nested_list(self):
        with self.dataset_populator.test_history() as history_id:
            hdca = self.dataset_collection_populator.create_list_of_list_in_history(
                history_id, ext="tabular", wait=True
            ).json()
            inputs = {
                "input1": {"src": "hdca", "id": hdca["id"]},
                # FIXME: integers don't work here
                "col": "1",
            }
            response = self._run("column_multi_param", history_id, inputs, assert_ok=True)
            self.dataset_populator.wait_for_job(job_id=response["jobs"][0]["id"], assert_ok=True)

    @skip_without_tool("column_multi_param")
    def test_multi_param_column_nested_list_fails_on_invalid_column(self):
        with self.dataset_populator.test_history() as history_id:
            hdca = self.dataset_collection_populator.create_list_of_list_in_history(
                history_id, ext="tabular", wait=True
            ).json()
            inputs = {
                "input1": {"src": "hdca", "id": hdca["id"]},
                "col": "10",
            }
            try:
                self._run("column_multi_param", history_id, inputs, assert_ok=True)
            except AssertionError as e:
                exception_raised = e
            assert exception_raised, "Expected invalid column selection to fail job"

    @skip_without_tool("implicit_conversion_format_input")
    def test_implicit_conversion_input_dataset_tracking(self):
        with self.dataset_populator.test_history() as history_id:
            compressed_path = self.test_data_resolver.get_filename("1.fastqsanger.gz")
            with open(compressed_path, "rb") as fh:
                dataset = self.dataset_populator.new_dataset(
                    history_id, content=fh, file_type="fastqsanger.gz", wait=True
                )
            outputs = self._run(
                "Grep1", history_id=history_id, inputs={"data": {"src": "hda", "id": dataset["id"]}}, assert_ok=True
            )
            job_details = self.dataset_populator.get_job_details(outputs["jobs"][0]["id"], full=True).json()
            assert job_details["inputs"]["input"]["id"] != dataset["id"]
            converted_input = self.dataset_populator.get_history_dataset_details(
                history_id=history_id, content_id=job_details["inputs"]["input"]["id"]
            )
            assert converted_input["extension"] == "fastqsanger"

    @skip_without_tool("column_multi_param")
    def test_implicit_conversion_and_reduce(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_implicit_collection_and_reduce(history_id=history_id, param="1")

    @skip_without_tool("column_multi_param")
    def test_implicit_conversion_and_reduce_invalid_param(self):
        with self.dataset_populator.test_history() as history_id:
            with pytest.raises(AssertionError):
                self._run_implicit_collection_and_reduce(history_id=history_id, param="X")
        details = self.dataset_populator.get_history_dataset_details(history_id=history_id, hid=3, assert_ok=False)
        assert details["state"] == "error"
        assert "Parameter 'col': an invalid option" in details["misc_info"]

    def _run_implicit_collection_and_reduce(self, history_id, param):
        fasta_path = self.test_data_resolver.get_filename("1.fasta")
        with open(fasta_path) as fasta_fh:
            fasta_content = fasta_fh.read()
            response = self.dataset_collection_populator.upload_collection(
                history_id,
                "list",
                elements=[
                    {
                        "name": "test0",
                        "src": "pasted",
                        "paste_content": fasta_content,
                        "ext": "fasta",
                    }
                ],
                wait=True,
            )
            details = self.dataset_populator.get_history_dataset_details(history_id, hid=2)
            assert details["extension"] == "fasta"
            self._assert_status_code_is(response, 200)
            hdca_id = response.json()["outputs"][0]["id"]
            inputs = {
                "input1": {"src": "hdca", "id": hdca_id},
                "col": param,
            }
            create = self._run("column_multi_param", history_id, inputs, assert_ok=True)
            jobs = create["jobs"]
            assert len(jobs) == 1
            content = self.dataset_populator.get_history_dataset_content(history_id, hid=3)
            assert content.strip() == "hg17", content

    @skip_without_tool("multi_data_repeat")
    def test_reduce_collections_in_repeat(self):
        with self.dataset_populator.test_history() as history_id:
            hdca1_id = self._build_pair(history_id, ["123\n", "456\n"])
            inputs = {
                "outer_repeat_0|f1": {"src": "hdca", "id": hdca1_id},
            }
            create = self._run("multi_data_repeat", history_id, inputs, assert_ok=True)
            outputs = create["outputs"]
            jobs = create["jobs"]
            assert len(jobs) == 1
            assert len(outputs) == 1
            output1 = outputs[0]
            output1_content = self.dataset_populator.get_history_dataset_content(history_id, dataset=output1)
            assert output1_content.strip() == "123\n456", output1_content

    @skip_without_tool("multi_data_repeat")
    def test_reduce_collections_in_repeat_legacy(self):
        with self.dataset_populator.test_history() as history_id:
            hdca1_id = self._build_pair(history_id, ["123\n", "456\n"])
            inputs = {
                "outer_repeat_0|f1": f"__collection_reduce__|{hdca1_id}",
            }
            create = self._run("multi_data_repeat", history_id, inputs, assert_ok=True)
            outputs = create["outputs"]
            jobs = create["jobs"]
            assert len(jobs) == 1
            assert len(outputs) == 1
            output1 = outputs[0]
            output1_content = self.dataset_populator.get_history_dataset_content(history_id, dataset=output1)
            assert output1_content.strip() == "123\n456", output1_content

    @skip_without_tool("multi_data_param")
    def test_reduce_multiple_lists_on_multi_data(self):
        with self.dataset_populator.test_history() as history_id:
            hdca1_id = self._build_pair(history_id, ["123\n", "456\n"])
            hdca2_id = self.dataset_collection_populator.create_list_in_history(history_id, wait=True).json()[
                "outputs"
            ][0]["id"]
            inputs = {
                "f1": [{"src": "hdca", "id": hdca1_id}, {"src": "hdca", "id": hdca2_id}],
                "f2": [{"src": "hdca", "id": hdca1_id}],
            }
            create = self._run("multi_data_param", history_id, inputs, assert_ok=True)
            outputs = create["outputs"]
            jobs = create["jobs"]
            assert len(jobs) == 1
            assert len(outputs) == 2
            output1, output2 = outputs
            output1_content = self.dataset_populator.get_history_dataset_content(history_id, dataset=output1)
            output2_content = self.dataset_populator.get_history_dataset_content(history_id, dataset=output2)
            assert output1_content.strip() == "123\n456\nTestData123\nTestData123\nTestData123"
            assert output2_content.strip() == "123\n456"

    def _check_simple_reduce_job(self, history_id, inputs):
        create = self._run("multi_data_param", history_id, inputs, assert_ok=True)
        outputs = create["outputs"]
        jobs = create["jobs"]
        assert len(jobs) == 1
        assert len(outputs) == 2
        output1, output2 = outputs
        output1_content = self.dataset_populator.get_history_dataset_content(history_id, dataset=output1)
        output2_content = self.dataset_populator.get_history_dataset_content(history_id, dataset=output2)
        assert output1_content.strip() == "123\n456", output1_content
        assert len(output2_content.strip().split("\n")) == 3, output2_content

    @skip_without_tool("collection_paired_test")
    def test_subcollection_mapping(self):
        with self.dataset_populator.test_history() as history_id:
            hdca_list_id = self.__build_nested_list(history_id)
            inputs = {
                "f1": {
                    "batch": True,
                    "values": [{"src": "hdca", "map_over_type": "paired", "id": hdca_list_id}],
                }
            }
            self._check_simple_subcollection_mapping(history_id, inputs)

    def _check_simple_subcollection_mapping(self, history_id, inputs):
        # Following wait not really needed - just getting so many database
        # locked errors with sqlite.
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        outputs = self._run_and_get_outputs("collection_paired_test", history_id, inputs)
        assert len(outputs), 2
        output1 = outputs[0]
        output2 = outputs[1]
        output1_content = self.dataset_populator.get_history_dataset_content(history_id, dataset=output1)
        output2_content = self.dataset_populator.get_history_dataset_content(history_id, dataset=output2)
        assert output1_content.strip() == "123\n456", output1_content
        assert output2_content.strip() == "789\n0ab", output2_content

    @skip_without_tool("collection_mixed_param")
    def test_combined_mapping_and_subcollection_mapping(self):
        with self.dataset_populator.test_history() as history_id:
            nested_list_id = self.__build_nested_list(history_id)
            create_response = self.dataset_collection_populator.create_list_in_history(
                history_id, contents=["xxx\n", "yyy\n"], wait=True
            )
            list_id = create_response.json()["outputs"][0]["id"]
            inputs = {
                "f1": {
                    "batch": True,
                    "values": [{"src": "hdca", "map_over_type": "paired", "id": nested_list_id}],
                },
                "f2": {
                    "batch": True,
                    "values": [{"src": "hdca", "id": list_id}],
                },
            }
            self._check_combined_mapping_and_subcollection_mapping(history_id, inputs)

    def _check_combined_mapping_and_subcollection_mapping(self, history_id, inputs):
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        outputs = self._run_and_get_outputs("collection_mixed_param", history_id, inputs)
        assert len(outputs), 2
        output1 = outputs[0]
        output2 = outputs[1]
        output1_content = self.dataset_populator.get_history_dataset_content(history_id, dataset=output1)
        output2_content = self.dataset_populator.get_history_dataset_content(history_id, dataset=output2)
        assert output1_content.strip() == "123\n456\nxxx", output1_content
        assert output2_content.strip() == "789\n0ab\nyyy", output2_content

    def _check_implicit_collection_populated(self, run_response):
        implicit_collections = run_response["implicit_collections"]
        assert implicit_collections
        for implicit_collection in implicit_collections:
            assert implicit_collection["populated_state"] == "ok"

    def _cat1_outputs(self, history_id, inputs):
        return self._run_outputs(self._run_cat1(history_id, inputs))

    def _run_and_get_outputs(self, tool_id, history_id, inputs=None, tool_version=None):
        if inputs is None:
            inputs = {}
        return self._run_outputs(self._run(tool_id, history_id, inputs, tool_version=tool_version))

    def _run_outputs(self, create_response):
        self._assert_status_code_is(create_response, 200)
        return create_response.json()["outputs"]

    def _run_cat1(self, history_id, inputs, assert_ok=False, **kwargs):
        return self._run("cat1", history_id, inputs, assert_ok=assert_ok, **kwargs)

    def __tool_ids(self):
        index = self._get("tool_panels/default")
        tools_index = index.json()
        # In panels by default, so flatten out sections...
        tool_ids = []
        for id, tool_or_section in tools_index.items():
            if "tools" in tool_or_section:
                tool_ids.extend([t for t in tool_or_section["tools"] if isinstance(t, str)])
            else:
                tool_ids.append(id)

        return tool_ids

    @skip_without_tool("collection_cat_group_tag_multiple")
    def test_group_tag_selection(self, history_id):
        input_hdca_id = self.__build_group_list(history_id)
        inputs = {
            "input1": {"src": "hdca", "id": input_hdca_id},
            "group": "condition:treated",
        }
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        response = self._run("collection_cat_group_tag", history_id, inputs, assert_ok=True)
        outputs = response["outputs"]
        assert len(outputs) == 1
        output = outputs[0]
        output_content = self.dataset_populator.get_history_dataset_content(history_id, dataset=output)
        assert output_content.strip() == "123\n456"

    @skip_without_tool("collection_cat_group_tag_multiple")
    def test_group_tag_selection_multiple(self, history_id):
        input_hdca_id = self.__build_group_list(history_id)
        inputs = {
            "input1": {"src": "hdca", "id": input_hdca_id},
            "groups": "condition:treated,type:single",
        }
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        response = self._run("collection_cat_group_tag_multiple", history_id, inputs, assert_ok=True)
        outputs = response["outputs"]
        assert len(outputs) == 1
        output = outputs[0]
        output_content = self.dataset_populator.get_history_dataset_content(history_id, dataset=output)
        assert output_content.strip() == "123\n456\n456\n0ab"

    @skip_without_tool("cat1")
    def test_run_deferred_dataset(self, history_id):
        details = self.dataset_populator.create_deferred_hda(
            history_id, "https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/1.bed", ext="bed"
        )
        inputs = {
            "input1": dataset_to_param(details),
        }
        outputs = self._cat1_outputs(history_id, inputs=inputs)
        output = outputs[0]
        details = self.dataset_populator.get_history_dataset_details(
            history_id, dataset=output, wait=True, assert_ok=True
        )
        assert details["state"] == "ok"
        output_content = self.dataset_populator.get_history_dataset_content(history_id, dataset=output)
        assert output_content.startswith("chr1	147962192	147962580	CCDS989.1_cds_0_0_chr1_147962193_r	0	-")

    @skip_without_tool("metadata_bam")
    def test_run_deferred_dataset_with_metadata_options_filter(self, history_id):
        details = self.dataset_populator.create_deferred_hda(
            history_id, "https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/1.bam", ext="bam"
        )
        inputs = {"input_bam": dataset_to_param(details), "ref_names": "chrM"}
        run_response = self.dataset_populator.run_tool(tool_id="metadata_bam", inputs=inputs, history_id=history_id)
        output = run_response["outputs"][0]
        output_details = self.dataset_populator.get_history_dataset_details(
            history_id, dataset=output, wait=True, assert_ok=True
        )
        assert output_details["state"] == "ok"
        output_content = self.dataset_populator.get_history_dataset_content(history_id, dataset=output)
        assert output_content.startswith("chrM")

    @skip_without_tool("pileup")
    def test_metadata_validator_on_deferred_input(self, history_id):
        deferred_bam_details = self.dataset_populator.create_deferred_hda(
            history_id, "https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/1.bam", ext="bam"
        )
        fasta1_contents = open(self.get_filename("1.fasta")).read()
        fasta = self.dataset_populator.new_dataset(history_id, content=fasta1_contents)
        inputs = {"input1": dataset_to_param(deferred_bam_details), "reference": dataset_to_param(fasta)}
        run_response = self.dataset_populator.run_tool(tool_id="pileup", inputs=inputs, history_id=history_id)
        self.dataset_populator.wait_for_job(run_response["jobs"][0]["id"], assert_ok=True)

    @pytest.mark.xfail
    @skip_without_tool("pileup")
    def test_metadata_validator_can_fail_on_deferred_input(self, history_id):
        # This test fails because we just skip the validator
        # Fixing this is a TODO
        deferred_bam_details = self.dataset_populator.create_deferred_hda(
            history_id,
            "https://github.com/galaxyproject/galaxy/blob/dev/test-data/3unsorted.bam?raw=true",
            ext="unsorted.bam",
        )
        fasta1_contents = open(self.get_filename("1.fasta")).read()
        fasta = self.dataset_populator.new_dataset(history_id, content=fasta1_contents)
        inputs = {"input1": dataset_to_param(deferred_bam_details), "reference": dataset_to_param(fasta)}
        run_response = self.dataset_populator.run_tool(tool_id="pileup", inputs=inputs, history_id=history_id)
        self.dataset_populator.wait_for_job(run_response["jobs"][0]["id"], assert_ok=False)
        job_id = run_response["jobs"][0]["id"]
        job_details = self.dataset_populator.get_job_details(job_id=job_id).json()
        assert job_details["state"] == "failed"

    @skip_without_tool("gx_allow_uri_if_protocol")
    def test_allow_uri_if_protocol_on_deferred_input(self, history_id):
        source_uri = "https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/simple_line.txt"
        deferred_hda = self.dataset_populator.create_deferred_hda(history_id, source_uri, ext="txt")

        inputs = {"input1": dataset_to_param(deferred_hda)}
        # The tool just returns the URI (or file path if it was materialized) as the output content
        run_response = self.dataset_populator.run_tool(
            tool_id="gx_allow_uri_if_protocol", inputs=inputs, history_id=history_id
        )
        output = run_response["outputs"][0]
        output_details = self.dataset_populator.get_history_dataset_details(
            history_id, dataset=output, wait=True, assert_ok=True
        )
        assert output_details["state"] == "ok"
        output_content = self.dataset_populator.get_history_dataset_content(history_id, dataset=output)
        assert output_content.strip() == source_uri.strip()

    @skip_without_tool("gx_allow_uri_if_protocol")
    def test_allow_uri_if_protocol_on_collection_with_deferred(self, history_id):
        source_uris = [
            "https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/simple_line.txt",
            "https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/simple_line_alternative.txt",
        ]
        elements = [
            {
                "src": "url",
                "url": source_uri,
                "deferred": True,
                "ext": "txt",
            }
            for source_uri in source_uris
        ]
        targets = [
            {
                "destination": {"type": "hdca"},
                "elements": elements,
                "collection_type": "list",
                "name": "deferred list",
            }
        ]
        payload = {
            "history_id": history_id,
            "targets": json.dumps(targets),
        }
        fetch_response = self.dataset_populator.fetch(payload, wait=True)
        dataset_collection = self.dataset_collection_populator.wait_for_fetched_collection(fetch_response)
        hdca_id = dataset_collection["id"]
        inputs = {
            "input1": {"batch": True, "values": [{"src": "hdca", "id": hdca_id}]},
        }
        run_response = self.dataset_populator.run_tool(
            tool_id="gx_allow_uri_if_protocol", inputs=inputs, history_id=history_id
        )
        hdca_id = run_response["implicit_collections"][0]["id"]
        dataset_collection = self.dataset_populator.get_history_collection_details(history_id, id=hdca_id)
        elements = dataset_collection["elements"]
        assert len(elements) == 2
        for element in elements:
            object = element["object"]
            assert isinstance(object, dict)
            assert object["state"] == "ok"
            output_content = self.dataset_populator.get_history_dataset_content(history_id, dataset=object)
            assert output_content.strip() in source_uris

    @skip_without_tool("cat1")
    def test_run_deferred_mapping(self, history_id: str):
        elements = [
            {
                "src": "url",
                "url": "https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/4.bed",
                "info": "my cool bed",
                "deferred": True,
                "ext": "bed",
            }
        ]
        targets = [
            {
                "destination": {"type": "hdca"},
                "elements": elements,
                "collection_type": "list",
                "name": "here is a name",
            }
        ]
        payload = {
            "history_id": history_id,
            "targets": json.dumps(targets),
        }
        fetch_response = self.dataset_populator.fetch(payload, wait=True)
        dataset_collection = self.dataset_collection_populator.wait_for_fetched_collection(fetch_response)
        hdca_id = dataset_collection["id"]
        inputs = {
            "input1": {"batch": True, "values": [{"src": "hdca", "id": hdca_id}]},
        }
        run_response = self._run_cat1(history_id, inputs).json()
        hdca_id = run_response["implicit_collections"][0]["id"]
        dataset_collection = self.dataset_populator.get_history_collection_details(history_id, id=hdca_id)
        elements = dataset_collection["elements"]
        assert len(elements) == 1
        object_0 = elements[0]["object"]
        assert isinstance(object_0, dict)
        assert object_0["state"] == "ok"
        output_content = self.dataset_populator.get_history_dataset_content(history_id, dataset=object_0)
        assert output_content.startswith("chr22	30128507	31828507	uc003bnx.1_cds_2_0_chr22_29227_f	0	+")

    @skip_without_tool("cat_list")
    def test_run_deferred_list_multi_data_reduction(self, history_id: str):
        elements = [
            {
                "src": "url",
                "url": "https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/4.bed",
                "info": "my cool bed",
                "deferred": True,
                "ext": "bed",
            }
        ]
        targets = [
            {
                "destination": {"type": "hdca"},
                "elements": elements,
                "collection_type": "list",
                "name": "here is a name",
            }
        ]
        payload = {
            "history_id": history_id,
            "targets": json.dumps(targets),
        }
        fetch_response = self.dataset_populator.fetch(payload, wait=True)
        dataset_collection = self.dataset_collection_populator.wait_for_fetched_collection(fetch_response)
        hdca_id = dataset_collection["id"]
        inputs = {
            "input1": {"src": "hdca", "id": hdca_id},
        }
        run_response = self._run("cat_list", history_id, inputs, assert_ok=True)
        output_dataset = run_response["outputs"][0]
        output_content = self.dataset_populator.get_history_dataset_content(history_id, dataset=output_dataset)
        assert output_content.startswith("chr22	30128507	31828507	uc003bnx.1_cds_2_0_chr22_29227_f	0	+")

    @skip_without_tool("cat_list")
    def test_run_deferred_nested_list_input(self, history_id: str):
        elements = [
            {
                "name": "outer",
                "elements": [
                    {
                        "src": "url",
                        "name": "forward",
                        "url": "https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/4.bed",
                        "info": "my cool bed 4",
                        "deferred": True,
                        "ext": "bed",
                    },
                    {
                        "src": "url",
                        "name": "reverse",
                        "url": "https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/1.bed",
                        "info": "my cool bed 1",
                        "deferred": True,
                        "ext": "bed",
                    },
                ],
            },
        ]
        targets = [
            {
                "destination": {"type": "hdca"},
                "elements": elements,
                "collection_type": "list:paired",
                "name": "here is a name",
            }
        ]
        payload = {
            "history_id": history_id,
            "targets": json.dumps(targets),
        }
        fetch_response = self.dataset_populator.fetch(payload, wait=True)
        dataset_collection = self.dataset_collection_populator.wait_for_fetched_collection(fetch_response)
        assert dataset_collection["collection_type"] == "list:paired"
        result_elements = dataset_collection["elements"]
        assert len(result_elements) == 1
        outer_element = result_elements[0]
        assert isinstance(outer_element, dict)
        inner_dataset_coll = outer_element["object"]
        assert isinstance(inner_dataset_coll, dict)
        inner_elements = inner_dataset_coll["elements"]
        assert isinstance(inner_elements, list)
        assert len(inner_elements) == 2
        hdca_id = dataset_collection["id"]
        inputs = {
            "input1": {"src": "hdca", "id": hdca_id},
        }
        run_response = self._run("collection_nested_test", history_id, inputs, assert_ok=True, wait_for_job=True)
        output_dataset = run_response["outputs"][1]
        output_content = self.dataset_populator.get_history_dataset_content(history_id, dataset=output_dataset)
        assert output_content.startswith("chr22	30128507	31828507	uc003bnx.1_cds_2_0_chr22_29227_f	0	+")

    @skip_without_tool("collection_paired_structured_like")
    def test_deferred_map_over_nested_collections(self, history_id):
        elements = [
            {
                "name": "outer1",
                "elements": [
                    {
                        "src": "url",
                        "name": "forward",
                        "url": "https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/4.bed",
                        "info": "my cool bed 4",
                        "deferred": True,
                        "ext": "bed",
                    },
                    {
                        "src": "url",
                        "name": "reverse",
                        "url": "https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/1.bed",
                        "info": "my cool bed 1",
                        "deferred": True,
                        "ext": "bed",
                    },
                ],
            },
            {
                "name": "outer2",
                "elements": [
                    {
                        "src": "url",
                        "name": "forward",
                        "url": "https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/4.bed",
                        "info": "my cool bed 4",
                        "deferred": True,
                        "ext": "bed",
                    },
                    {
                        "src": "url",
                        "name": "reverse",
                        "url": "https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/1.bed",
                        "info": "my cool bed 1",
                        "deferred": True,
                        "ext": "bed",
                    },
                ],
            },
        ]
        targets = [
            {
                "destination": {"type": "hdca"},
                "elements": elements,
                "collection_type": "list:paired",
                "name": "here is a name",
            }
        ]
        payload = {
            "history_id": history_id,
            "targets": json.dumps(targets),
        }
        fetch_response = self.dataset_populator.fetch(payload, wait=True)
        dataset_collection = self.dataset_collection_populator.wait_for_fetched_collection(fetch_response)
        hdca_id = dataset_collection["id"]
        inputs = {
            "input1": {"batch": True, "values": [dict(map_over_type="paired", src="hdca", id=hdca_id)]},
        }
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        create = self._run("collection_paired_structured_like", history_id, inputs, assert_ok=True)
        jobs = create["jobs"]
        implicit_collections = create["implicit_collections"]
        assert len(jobs) == 2
        self.dataset_populator.wait_for_jobs(jobs, assert_ok=True)
        assert len(implicit_collections) == 1
        implicit_collection = implicit_collections[0]
        assert implicit_collection["collection_type"] == "list:paired", implicit_collection["collection_type"]
        outer_elements = implicit_collection["elements"]
        assert len(outer_elements) == 2
        element0 = outer_elements[0]
        pair1 = element0["object"]
        hda = pair1["elements"][0]["object"]
        output1_content = self.dataset_populator.get_history_dataset_content(history_id, dataset=hda, wait=False)
        assert output1_content.startswith("chr22\t30128507\t31828507\tuc003bnx.1_cds_2_0_chr22_29227_f\t0\t+")

    def __build_group_list(self, history_id):
        response = self.dataset_collection_populator.upload_collection(
            history_id,
            "list",
            elements=[
                {
                    "name": "test0",
                    "src": "pasted",
                    "paste_content": "123\n",
                    "ext": "txt",
                    "tags": ["group:type:paired-end", "group:condition:treated"],
                },
                {
                    "name": "test1",
                    "src": "pasted",
                    "paste_content": "456\n",
                    "ext": "txt",
                    "tags": ["group:type:single", "group:condition:treated"],
                },
                {
                    "name": "test2",
                    "src": "pasted",
                    "paste_content": "789\n",
                    "ext": "txt",
                    "tags": ["group:type:paired-end", "group:condition:untreated"],
                },
                {
                    "name": "test3",
                    "src": "pasted",
                    "paste_content": "0ab\n",
                    "ext": "txt",
                    "tags": ["group:type:single", "group:condition:untreated"],
                },
            ],
            wait=True,
        )
        self._assert_status_code_is(response, 200)
        hdca_list_id = response.json()["outputs"][0]["id"]
        return hdca_list_id

    def __build_nested_list(self, history_id: str) -> str:
        return self.dataset_collection_populator.example_list_of_pairs(history_id)

    def _build_pair(self, history_id, contents, run_cat=False):
        create_response = self.dataset_collection_populator.create_pair_in_history(
            history_id, contents=contents, direct_upload=True, wait=True
        )
        hdca_id = create_response.json()["output_collections"][0]["id"]
        inputs = {
            "input1": {"batch": True, "values": [dict(src="hdca", id=hdca_id)]},
        }
        if run_cat:
            outputs = self._run_cat(history_id, inputs=inputs, assert_ok=True)
            hdca_id = outputs["implicit_collections"][0]["id"]
        return hdca_id

    def _assert_dataset_permission_denied_response(self, response):
        # TODO: This should be 403, should just need to throw more specific exception in the
        # Galaxy code.
        assert response.status_code != 200
        # err_message = response.json()["err_msg"]
        # assert "User does not have permission to use a dataset" in err_message, err_message

    @contextlib.contextmanager
    def _different_user_and_history(self, user_email: Optional[str] = None):
        with self._different_user(email=user_email):
            with self.dataset_populator.test_history() as other_history_id:
                yield other_history_id


def dataset_to_param(dataset):
    return dict(src="hda", id=dataset["id"])
