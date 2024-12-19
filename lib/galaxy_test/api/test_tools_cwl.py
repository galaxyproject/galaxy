"""Test CWL Tool Execution via the API."""

from typing import (
    Any,
    Dict,
    Optional,
)

from typing_extensions import Literal

from galaxy.tool_util.cwl.representation import USE_FIELD_TYPES
from galaxy_test.api._framework import ApiTestCase
from galaxy_test.base.populators import (
    CwlPopulator,
    CwlToolRun,
    DatasetPopulator,
    skip_without_tool,
    WorkflowPopulator,
)


class TestCwlTools(ApiTestCase):
    """Test CWL Tool Execution via the API."""

    dataset_populator: DatasetPopulator

    require_admin_user = True

    def setUp(self):
        """Setup dataset populator."""
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        workflow_populator = WorkflowPopulator(self.galaxy_interactor)
        self.cwl_populator = CwlPopulator(self.dataset_populator, workflow_populator)

    @skip_without_tool("cat1-tool.cwl")
    def test_cat1_number(self, history_id: str) -> None:
        """Test execution of cat1 using the "normal" Galaxy job API representation."""
        hda1 = _dataset_to_param(self.dataset_populator.new_dataset(history_id, content="1\n2\n3", name="test1"))
        if not USE_FIELD_TYPES:
            inputs = {
                "file1": hda1,
                "numbering|_cwl__type_": "boolean",
                "numbering|_cwl__value_": True,
            }
        else:
            inputs = {
                "file1": hda1,
                "numbering": {"src": "json", "value": True},
            }
        stdout = self._run_and_get_stdout("cat1-tool.cwl", history_id, inputs, assert_ok=True)
        assert stdout == "     1\t1\n     2\t2\n     3\t3\n"

    @skip_without_tool("cat1-tool.cwl")
    def test_cat1_number_cwl_json(self, history_id: str) -> None:
        """Test execution of cat1 using the "CWL" Galaxy job API representation."""
        hda1 = _dataset_to_param(self.dataset_populator.new_dataset(history_id, content="1\n2\n3"))
        inputs = {
            "file1": hda1,
            "numbering": True,
        }
        stdout = self._run_and_get_stdout(
            "cat1-tool.cwl", history_id, inputs, assert_ok=True, inputs_representation="cwl"
        )
        assert stdout == "     1\t1\n     2\t2\n     3\t3\n"

    @skip_without_tool("cat1-tool.cwl")
    def test_cat1_number_cwl_json_file(self) -> None:
        """Test execution of cat1 using the CWL job definition file."""
        run_object = self.cwl_populator.run_cwl_job(
            "cat1-tool.cwl", "test/functional/tools/cwl_tools/v1.0_custom/cat-job.json"
        )
        assert isinstance(run_object, CwlToolRun)
        stdout = self._get_job_stdout(run_object.job_id)
        assert stdout == "Hello world!\n"

    @skip_without_tool("cat1-tool.cwl")
    def test_cat1_number_cwl_n_json_file(self) -> None:
        run_object = self.cwl_populator.run_cwl_job(
            "cat1-tool.cwl", "test/functional/tools/cwl_tools/v1.0_custom/cat-n-job.json"
        )
        assert isinstance(run_object, CwlToolRun)
        stdout = self._get_job_stdout(run_object.job_id)
        assert stdout == "     1\tHello world!\n"

    @skip_without_tool("cat2-tool.cwl")
    def test_cat2(self) -> None:
        run_object = self.cwl_populator.run_cwl_job(
            "cat2-tool.cwl", "test/functional/tools/cwl_tools/v1.0_custom/cat-job.json"
        )
        assert isinstance(run_object, CwlToolRun)
        stdout = self._get_job_stdout(run_object.job_id)
        assert stdout == "Hello world!\n"

    @skip_without_tool("galactic_cat.cwl#galactic_cat")
    def test_galactic_cat_1(self, history_id: str) -> None:
        hda_id = self.dataset_populator.new_dataset(history_id, name="test_dataset.txt")["id"]
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        inputs = {"input1": {"src": "hda", "id": hda_id}}
        run_response = self._run("galactic_cat.cwl#galactic_cat", history_id, inputs, assert_ok=True)
        dataset = run_response["outputs"][0]
        content = self.dataset_populator.get_history_dataset_content(history_id, dataset=dataset)
        assert content.strip() == "TestData123", content

    @skip_without_tool("galactic_record_input.cwl#galactic_record_input")
    def test_galactic_record_input(self, history_id: str) -> None:
        hda1_id = self.dataset_populator.new_dataset(history_id, content="moo", name="test_dataset.txt")["id"]
        hda2_id = self.dataset_populator.new_dataset(history_id, content="cow dog foo", name="test_dataset.txt")["id"]
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        inputs = {
            "input1": {"src": "hda", "id": hda1_id},
            "input2": {"src": "hda", "id": hda2_id},
        }
        run_response = self._run("galactic_record_input.cwl#galactic_record_input", history_id, inputs, assert_ok=True)
        dataset = run_response["outputs"][0]
        content = self.dataset_populator.get_history_dataset_content(history_id, dataset=dataset)
        assert content.strip() == "moo", content

        dataset = run_response["outputs"][1]
        content = self.dataset_populator.get_history_dataset_content(history_id, dataset=dataset)
        assert content.strip() == "cow dog foo", content

    def _run_and_get_stdout(self, tool_id: str, history_id: str, inputs: Dict[str, Any], **kwds) -> str:
        response = self._run(tool_id, history_id, inputs, **kwds)
        assert "jobs" in response
        job = response["jobs"][0]
        job_id = job["id"]
        final_state = self.dataset_populator.wait_for_job(job_id)
        assert final_state == "ok"
        return self._get_job_stdout(job_id)

    def _get_job_stdout(self, job_id: str) -> str:
        job_details = self.dataset_populator.get_job_details(job_id, full=True)
        stdout = job_details.json()["tool_stdout"]
        return stdout

    @skip_without_tool("cat3-tool.cwl")
    def test_cat3(self, history_id: str) -> None:
        hda1 = _dataset_to_param(self.dataset_populator.new_dataset(history_id, content="1\t2\t3"))
        inputs = {
            "f1": hda1,
        }
        response = self._run("cat3-tool.cwl", history_id, inputs, assert_ok=True)
        output1 = response["outputs"][0]
        output1_details = self.dataset_populator.get_history_dataset_details(history_id, dataset=output1)
        assert "created_from_basename" in output1_details, output1_details.keys()
        assert output1_details["created_from_basename"] == "output.txt", output1_details["created_from_basename"]
        output1_content = self.dataset_populator.get_history_dataset_content(history_id, dataset=output1)
        assert output1_content == "1\t2\t3\n", output1_content

    @skip_without_tool("sorttool.cwl")
    def test_sorttool(self, history_id: str) -> None:
        hda1 = _dataset_to_param(self.dataset_populator.new_dataset(history_id, content="1\n2\n3"))
        inputs = {"reverse": False, "input": hda1}
        response = self._run("sorttool.cwl", history_id, inputs, assert_ok=True)
        output1 = response["outputs"][0]
        output1_content = self.dataset_populator.get_history_dataset_content(history_id, dataset=output1)
        assert output1_content == "1\n2\n3\n", output1_content

    @skip_without_tool("sorttool.cwl")
    def test_sorttool_reverse(self, history_id: str) -> None:
        hda1 = _dataset_to_param(self.dataset_populator.new_dataset(history_id, content="1\n2\n3"))
        inputs = {"reverse": True, "input": hda1}
        response = self._run("sorttool.cwl", history_id, inputs, assert_ok=True)
        output1 = response["outputs"][0]
        output1_content = self.dataset_populator.get_history_dataset_content(history_id, dataset=output1)
        assert output1_content == "3\n2\n1\n", output1_content

    @skip_without_tool("env-tool1.cwl")
    def test_env_tool1(self, history_id: str) -> None:
        inputs = {
            "in": "Hello World",
        }
        response = self._run("env-tool1.cwl", history_id, inputs, assert_ok=True)
        output1 = response["outputs"][0]
        output1_content = self.dataset_populator.get_history_dataset_content(history_id, dataset=output1)
        assert output1_content == "Hello World\n"

    @skip_without_tool("optional-output.cwl")
    def test_optional_output(self) -> None:
        run_object = self.cwl_populator.run_cwl_job(
            "optional-output.cwl", "test/functional/tools/cwl_tools/v1.0/v1.0/cat-job.json"
        )
        output_file_id = run_object._output_name_to_object("output_file").history_content_id
        optional_file_id = run_object._output_name_to_object("optional_file").history_content_id
        output_content = self.dataset_populator.get_history_dataset_content(
            run_object.history_id, dataset_id=output_file_id
        )
        optional_content = self.dataset_populator.get_history_dataset_content(
            run_object.history_id, dataset_id=optional_file_id
        )
        assert output_content == "Hello world!\n"
        assert optional_content == "null"

    @skip_without_tool("optional-output2.cwl")
    def test_optional_output2_on(self) -> None:
        run_object = self.cwl_populator.run_cwl_job(
            "optional-output2.cwl",
            job={
                "produce": "do_write",
            },
            test_data_directory="test/functional/tools/cwl_tools/v1.0_custom",
        )
        output_content = self.dataset_populator.get_history_dataset_content(run_object.history_id)
        assert output_content == "bees\n"

    @skip_without_tool("optional-output2.cwl")
    def test_optional_output2_off(self) -> None:
        run_object = self.cwl_populator.run_cwl_job(
            "optional-output2.cwl",
            job={
                "produce": "dont_write",
            },
            test_data_directory="test/functional/tools/cwl_tools/v1.0_custom",
        )
        output_content = self.dataset_populator.get_history_dataset_content(run_object.history_id)
        assert output_content == "null"

    @skip_without_tool("index1.cwl")
    @skip_without_tool("showindex1.cwl")
    def test_index1(self) -> None:
        run_object = self.cwl_populator.run_cwl_job(
            "index1.cwl",
            job={
                "file": {"class": "File", "path": "whale.txt"},
            },
            test_data_directory="test/functional/tools/cwl_tools/v1.0_custom",
        )
        output1 = self.dataset_populator.get_history_dataset_details(run_object.history_id)
        run_object = self.cwl_populator.run_cwl_job(
            "showindex1.cwl",
            job={
                "file": {
                    "src": "hda",
                    "id": output1["id"],
                },
            },
            test_data_directory="test/functional/tools/cwl_tools/v1.0_custom",
            history_id=run_object.history_id,
            skip_input_staging=True,
        )
        output1_content = self.dataset_populator.get_history_dataset_content(run_object.history_id)
        assert "call: 1\n" in output1_content, output1_content

    @skip_without_tool("any1.cwl")
    def test_any1_0(self) -> None:
        run_object = self.cwl_populator.run_cwl_job(
            "any1.cwl",
            job={"bar": 7},
            test_data_directory="test/functional/tools/cwl_tools/v1.0/v1.0/",
        )
        output1_content = self.dataset_populator.get_history_dataset_content(run_object.history_id)
        assert output1_content == "7", output1_content

    @skip_without_tool("any1.cwl")
    def test_any1_1(self) -> None:
        run_object = self.cwl_populator.run_cwl_job(
            "any1.cwl",
            job={"bar": "7"},
            test_data_directory="test/functional/tools/cwl_tools/v1.0/v1.0/",
        )
        output1_content = self.dataset_populator.get_history_dataset_content(run_object.history_id)
        assert output1_content == '"7"', output1_content

    @skip_without_tool("any1.cwl")
    def test_any1_file(self) -> None:
        run_object = self.cwl_populator.run_cwl_job(
            "any1.cwl",
            job={
                "bar": {
                    "class": "File",
                    "location": "whale.txt",
                }
            },
            test_data_directory="test/functional/tools/cwl_tools/v1.0/v1.0/",
        )
        output1_content = self.dataset_populator.get_history_dataset_content(run_object.history_id)
        self.dataset_populator._summarize_history(run_object.history_id)
        assert output1_content == '"File"'

    @skip_without_tool("any1.cwl")
    def test_any1_2(self) -> None:
        run_object = self.cwl_populator.run_cwl_job(
            "any1.cwl",
            job={"bar": {"Cow": ["Turkey"]}},
            test_data_directory="test/functional/tools/cwl_tools/v1.0/v1.0/",
        )
        output1_content = self.dataset_populator.get_history_dataset_content(run_object.history_id)
        assert output1_content == '{"Cow": ["Turkey"]}', output1_content

    @skip_without_tool("null-expression2-tool.cwl")
    def test_null_expression_any_bad_1(self) -> None:
        """Test explicitly passing null to Any type without a default value fails."""
        run_object = self.cwl_populator.run_cwl_job(
            "null-expression2-tool.cwl",
            "test/functional/tools/cwl_tools/v1.0/v1.0/null-expression1-job.json",
            assert_ok=False,
        )
        with self.assertRaises(AssertionError):
            run_object.wait()

    @skip_without_tool("null-expression2-tool.cwl")
    def test_null_expression_any_bad_2(self) -> None:
        """Test Any without defaults can be unspecified."""
        run_object = self.cwl_populator.run_cwl_job(
            "null-expression2-tool.cwl", "test/functional/tools/cwl_tools/v1.0/v1.0/empty.json", assert_ok=False
        )
        with self.assertRaises(AssertionError):
            run_object.wait()

    @skip_without_tool("default_path_custom_1.cwl")
    def test_default_path(self) -> None:
        # produces no output - just test the job runs okay.
        # later come back and verify standard output of the job.
        run_object = self.cwl_populator.run_cwl_job("default_path_custom_1.cwl", job={})
        assert isinstance(run_object, CwlToolRun)
        stdout = self._get_job_stdout(run_object.job_id)
        assert "this is the test file that will be used when calculating an md5sum" in stdout

    @skip_without_tool("parseInt-tool.cwl")
    def test_parse_int_tool(self) -> None:
        run_object = self.cwl_populator.run_cwl_job(
            "parseInt-tool.cwl", "test/functional/tools/cwl_tools/v1.0/v1.0/parseInt-job.json"
        )
        output1 = self.dataset_populator.get_history_dataset_details(run_object.history_id, hid=2)
        assert output1["state"] == "ok"
        output1_content = self.dataset_populator.get_history_dataset_content(run_object.history_id, hid=2)
        assert output1_content == "42"
        assert output1["extension"] == "expression.json"

    @skip_without_tool("record-output.cwl")
    def test_record_output(self) -> None:
        run_object = self.cwl_populator.run_cwl_job(
            "record-output.cwl", "test/functional/tools/cwl_tools/v1.0/v1.0/record-output-job.json"
        )
        assert isinstance(run_object, CwlToolRun)
        result_record = run_object.output_collection(0)
        assert result_record["collection_type"] == "record"
        record_elements = result_record["elements"]
        first_element = record_elements[0]
        assert first_element["element_identifier"] == "ofoo"
        first_hda = first_element["object"]
        output1_content = self.dataset_populator.get_history_dataset_content(
            run_object.history_id, hid=first_hda["hid"]
        )
        assert "Call me Ishmael." in output1_content, f"Expected contents of whale.txt, got [{output1_content}]"

    # def test_dynamic_tool_execution(self) -> None:
    #     workflow_tool_json = {
    #         "inputs": [{"inputBinding": {}, "type": "File", "id": "file:///home/john/workspace/galaxy/test/unit/tools/cwl_tools/v1.0/v1.0/count-lines2-wf.cwl#step1/wc/wc_file1"}],
    #         "stdout": "output.txt",
    #         "id": "file:///home/john/workspace/galaxy/test/unit/tools/cwl_tools/v1.0/v1.0/count-lines2-wf.cwl#step1/wc",
    #         "outputs": [{"outputBinding": {"glob": "output.txt"}, "type": "File", "id": "file:///home/john/workspace/galaxy/test/unit/tools/cwl_tools/v1.0/v1.0/count-lines2-wf.cwl#step1/wc/wc_output"}],
    #         "baseCommand": "wc",
    #         "class": "CommandLineTool",
    #     }

    #     create_payload = dict(
    #         representation=json.dumps(workflow_tool_json),
    #     )
    #     create_response = self._post("dynamic_tools", data=create_payload, admin=True)
    #     self._assert_status_code_is(create_response, 200)

    # TODO: Use mixin so this can be shared with tools test case.
    def _run(
        self,
        tool_id: str,
        history_id: str,
        inputs: Dict[str, Any],
        assert_ok: bool = False,
        tool_version: Optional[str] = None,
        inputs_representation: Optional[Literal["cwl", "galaxy"]] = None,
    ):
        payload = self.dataset_populator.run_tool_payload(
            tool_id=tool_id,
            inputs=inputs,
            history_id=history_id,
            inputs_representation=inputs_representation,
        )
        if tool_version is not None:
            payload["tool_version"] = tool_version
        create_response = self._post("tools", data=payload)
        if assert_ok:
            self._assert_status_code_is(create_response, 200)
            create = create_response.json()
            self._assert_has_keys(create, "outputs")
            return create
        else:
            return create_response


def whale_text() -> str:
    return open("test/functional/tools/cwl_tools/v1.0/v1.0/whale.txt").read()


def _dataset_to_param(dataset: Dict) -> Dict[str, str]:
    return dict(src="hda", id=dataset["id"])
