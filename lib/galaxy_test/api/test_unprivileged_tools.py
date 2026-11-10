# Test tools API.
import base64
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from uuid import uuid4

from galaxy.tool_util_models import UserToolSource
from galaxy_test.base.api_mixins import TestsTools
from galaxy_test.base.populators import (
    DatasetCollectionPopulator,
    DatasetPopulator,
    TOOL_WITH_ELEMENT_IDENTIFIER,
    TOOL_WITH_SHELL_COMMAND,
)
from ._framework import ApiTestCase

TOOL_WITH_REFERENCE_DATA = {
    "class": "GalaxyUserTool",
    "id": "reference_data_tool",
    "version": "1.0.0",
    "name": "reference_data_tool",
    "container": "busybox",
    "shell_command": (
        "echo '$(inputs.reference.class) $(inputs.reference.path) "
        "$(inputs.reference.source.table) $(inputs.reference.source.value) $(inputs.reference.metadata.dbkey) "
        "$(inputs.reference.metadata.name)' > output.txt"
    ),
    "inputs": [{"name": "reference", "type": "reference_data", "table": "test_fasta_indexes"}],
    "outputs": [{"name": "output", "type": "data", "format": "txt", "from_work_dir": "output.txt"}],
}


BAM_INPUT_WITH_SECONDARY_FILES = {"type": "data", "name": "input", "format": "bam", "secondary_files": True}
TOOL_LINKING_BAM_INDEX = {
    **TOOL_WITH_SHELL_COMMAND,
    "shell_command": (
        "ln -s '$(inputs.input.path)' input.bam && "
        "ln -s '$(inputs.input.secondaryFiles[0].path)' 'input.bam$(inputs.input.secondaryFiles[0].nameext)' && "
        "od -An -v -tx1 input.bam.bai | tr -d ' \\n' > output.fastq"
    ),
    "inputs": [BAM_INPUT_WITH_SECONDARY_FILES],
}


class TestUnprivilegedToolsApi(ApiTestCase, TestsTools):
    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.dataset_collection_populator = DatasetCollectionPopulator(self.galaxy_interactor)

    def test_admin_cannot_create_public_galaxy_user_tool(self):
        # GalaxyUserTool would land as public=True and bypass role+ownership.
        payload = {"representation": TOOL_WITH_SHELL_COMMAND}
        response = self.dataset_populator._post("dynamic_tools", data=payload, admin=True, json=True)
        assert response.status_code == 400, response.text
        assert "GalaxyUserTool" in response.text

    def test_create_unprivileged_requires_execute_role(self):
        dynamic_tool = self.dataset_populator.create_unprivileged_tool(
            UserToolSource(**TOOL_WITH_SHELL_COMMAND), assert_ok=False
        )
        assert dynamic_tool["err_msg"] == "User is not allowed to run unprivileged tools"

    def test_create_unprivileged(self):
        # Create a new dynamic tool.
        with self.dataset_populator.user_tool_execute_permissions():
            dynamic_tool = self.dataset_populator.create_unprivileged_tool(UserToolSource(**TOOL_WITH_SHELL_COMMAND))
            assert dynamic_tool["uuid"], "Dynamic tool UUID not found in response"
            assert dynamic_tool["representation"]["name"] == TOOL_WITH_SHELL_COMMAND["name"]

    def test_create_unprivileged_with_group_inherited_role(self):
        # Regression: USER_TOOL_EXECUTE granted via group membership must also allow access,
        # not only direct UserRoleAssociation.
        with self.dataset_populator.user_tool_execute_permissions_via_group():
            dynamic_tool = self.dataset_populator.create_unprivileged_tool(UserToolSource(**TOOL_WITH_SHELL_COMMAND))
            assert dynamic_tool["uuid"], "Dynamic tool UUID not found in response"
            assert dynamic_tool["representation"]["name"] == TOOL_WITH_SHELL_COMMAND["name"]

    def test_list_unprivileged(self):
        with self.dataset_populator.user_tool_execute_permissions():
            dynamic_tool = self.dataset_populator.create_unprivileged_tool(UserToolSource(**TOOL_WITH_SHELL_COMMAND))
            dynamic_tools = self.dataset_populator.get_unprivileged_tools()
        assert any(
            dynamic_tool["uuid"] == t["uuid"] for t in dynamic_tools
        ), f"Newly created dynamic tool {dynamic_tool['uuid']} not in dynamic tools list {dynamic_tools}"

    def test_show(self):
        with self.dataset_populator.user_tool_execute_permissions():
            dynamic_tool = self.dataset_populator.create_unprivileged_tool(UserToolSource(**TOOL_WITH_SHELL_COMMAND))
            show_response = self.dataset_populator.show_unprivileged_tool(dynamic_tool["uuid"])
        assert show_response["representation"]["name"]

    def test_build(self):
        with (
            self.dataset_populator.test_history() as history_id,
            self.dataset_populator.user_tool_execute_permissions(),
        ):
            response = self.dataset_populator.build_unprivileged_tool(
                UserToolSource(**TOOL_WITH_SHELL_COMMAND), history_id=history_id
            )
        assert response

    def test_build_rejects_rst_help(self):
        representation = {**TOOL_WITH_SHELL_COMMAND, "help": {"format": "restructuredtext", "content": "**help**"}}
        payload = {"src": "representation", "representation": representation}
        with (
            self.dataset_populator.test_history() as history_id,
            self.dataset_populator.user_tool_execute_permissions(),
        ):
            response = self.dataset_populator._post(
                f"unprivileged_tools/build?history_id={history_id}", data=payload, json=True
            )
        assert response.status_code == 400, response.text
        assert "markdown" in response.text

    def test_build_runtime_model(self):
        with self.dataset_populator.user_tool_execute_permissions():
            response = self.dataset_populator.build_runtime_model_for_tool(UserToolSource(**TOOL_WITH_SHELL_COMMAND))
            assert response
            assert response["openapi"] == "3.1.0"
            assert response["components"]["schemas"]["inputs"]

    def test_build_requires_execute_role(self):
        with self.dataset_populator.test_history() as history_id:
            response = self.dataset_populator.build_unprivileged_tool(
                UserToolSource(**TOOL_WITH_SHELL_COMMAND), history_id=history_id, assert_ok=False
            )
        assert response["err_msg"] == "User is not allowed to run unprivileged tools"

    def test_build_requires_authenticated_user(self):
        with self.dataset_populator.test_history() as history_id, self._different_user(anon=True):
            response = self.dataset_populator.build_unprivileged_tool(
                UserToolSource(**TOOL_WITH_SHELL_COMMAND), history_id=history_id, assert_ok=False
            )
        assert response["err_msg"] == "Action requires user authentication."

    def test_build_runtime_model_requires_execute_role(self):
        response = self.dataset_populator.build_runtime_model_for_tool(
            UserToolSource(**TOOL_WITH_SHELL_COMMAND), assert_ok=False
        )
        assert response["err_msg"] == "User is not allowed to run unprivileged tools"

    def test_run(self):
        with (
            self.dataset_populator.test_history() as history_id,
            self.dataset_populator.user_tool_execute_permissions(),
        ):
            # Create a new dynamic tool.
            # This is a shell command tool that will echo the input dataset.
            dynamic_tool = self.dataset_populator.create_unprivileged_tool(UserToolSource(**TOOL_WITH_SHELL_COMMAND))
            # Run tool.
            dataset = self.dataset_populator.new_dataset(history_id=history_id, content="abc")
            self._run(
                history_id=history_id,
                tool_uuid=dynamic_tool["uuid"],
                inputs={"input": {"src": "hda", "id": dataset["id"]}},
            )

            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            output_content = self.dataset_populator.get_history_dataset_content(history_id)
            assert output_content == "abc\n"

    def test_run_with_reference_data(self):
        with (
            self.dataset_populator.test_history() as history_id,
            self.dataset_populator.user_tool_execute_permissions(),
        ):
            dynamic_tool = self.dataset_populator.create_unprivileged_tool(UserToolSource(**TOOL_WITH_REFERENCE_DATA))
            self._run(history_id=history_id, tool_uuid=dynamic_tool["uuid"], inputs={"reference": "hg19_value"})
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            output_content = self.dataset_populator.get_history_dataset_content(history_id)
            assert output_content == "ReferenceData hg19_path test_fasta_indexes hg19_value hg19 hg19_name\n"

    def test_reference_data_needs_a_table_admins_opened_to_user_tools(self):
        representation = {
            **TOOL_WITH_REFERENCE_DATA,
            "inputs": [{"name": "reference", "type": "reference_data", "table": "testalpha"}],
        }
        with (
            self.dataset_populator.test_history() as history_id,
            self.dataset_populator.user_tool_execute_permissions(),
        ):
            dynamic_tool = self.dataset_populator.create_unprivileged_tool(UserToolSource(**representation))
            response = self.dataset_populator.run_tool_raw(
                None, {"reference": "data1"}, history_id, tool_uuid=dynamic_tool["uuid"]
            )
            self._assert_status_code_is(response, 400)

    def test_queued_job_fails_when_execute_role_is_revoked(self):
        with self.dataset_populator.test_history() as history_id:
            dataset = self.dataset_populator.new_dataset(history_id=history_id, content="abc", wait=True)
            slow_run = self.dataset_populator.run_tool(
                "cat_data_and_sleep",
                {"input1": {"src": "hda", "id": dataset["id"]}, "sleep_time": 10},
                history_id,
            )
            with self.dataset_populator.user_tool_execute_permissions():
                dynamic_tool = self.dataset_populator.create_unprivileged_tool(
                    UserToolSource(**TOOL_WITH_SHELL_COMMAND)
                )
                # Waits on the slow job's output, so it is still queued when the role is revoked.
                queued_run = self._run(
                    history_id=history_id,
                    tool_uuid=dynamic_tool["uuid"],
                    inputs={"input": {"src": "hda", "id": slow_run["outputs"][0]["id"]}},
                    assert_ok=True,
                )
            self.dataset_populator.wait_for_job(slow_run["jobs"][0]["id"], assert_ok=True)
            queued_job_id = queued_run["jobs"][0]["id"]
            self.dataset_populator.wait_for_job(queued_job_id)
            job_details = self.dataset_populator.get_job_details(queued_job_id, full=True).json()
            assert job_details["state"] == "error", job_details
            output_details = self.dataset_populator.get_history_dataset_details(
                history_id=history_id, dataset_id=queued_run["outputs"][0]["id"], assert_ok=False
            )
            assert output_details["misc_info"] == "User is not allowed to run unprivileged tools", output_details

    def test_run_mapped_over_writes_element_identifier(self):
        contents = self._run_mapped_over_list(TOOL_WITH_ELEMENT_IDENTIFIER, [("sample_a", "a"), ("sample_b", "b")])
        assert contents == {"sample_a": "sample_a\n", "sample_b": "sample_b\n"}

    def test_tool_request_mapped_over_writes_element_identifier(self):
        contents = self._tool_request_mapped_over_list(
            TOOL_WITH_ELEMENT_IDENTIFIER, [("sample_a", "a"), ("sample_b", "b")]
        )
        assert contents == {"sample_a": "sample_a\n", "sample_b": "sample_b\n"}

    def test_run_mapped_over_converted_input_writes_element_identifier(self):
        tabular_input = [{**TOOL_WITH_ELEMENT_IDENTIFIER["inputs"][0], "format": "tabular"}]
        tool = {**TOOL_WITH_ELEMENT_IDENTIFIER, "inputs": tabular_input}
        contents = self._run_mapped_over_list(tool, [("sample_a", "a,1\n"), ("sample_b", "b,2\n")], ext="csv")
        assert contents == {"sample_a": "sample_a\n", "sample_b": "sample_b\n"}

    def test_tool_request_mapped_over_converted_input_writes_element_identifier(self):
        tabular_input = [{**TOOL_WITH_ELEMENT_IDENTIFIER["inputs"][0], "format": "tabular"}]
        tool = {**TOOL_WITH_ELEMENT_IDENTIFIER, "inputs": tabular_input}
        contents = self._tool_request_mapped_over_list(tool, [("sample_a", "a,1\n"), ("sample_b", "b,2\n")], ext="csv")
        assert contents == {"sample_a": "sample_a\n", "sample_b": "sample_b\n"}

    def test_run_plain_dataset_element_identifier_falls_back_to_name(self):
        with (
            self.dataset_populator.test_history() as history_id,
            self.dataset_populator.user_tool_execute_permissions(),
        ):
            dynamic_tool = self.dataset_populator.create_unprivileged_tool(
                UserToolSource(**TOOL_WITH_ELEMENT_IDENTIFIER)
            )
            dataset = self.dataset_populator.new_dataset(history_id=history_id, content="abc", name="reads.txt")
            self._run(
                history_id=history_id,
                tool_uuid=dynamic_tool["uuid"],
                inputs={"input": {"src": "hda", "id": dataset["id"]}},
                assert_ok=True,
            )
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            output_content = self.dataset_populator.get_history_dataset_content(history_id)
        assert output_content == "reads.txt\n"

    def test_run_paired_input_writes_element_identifiers(self):
        tool = {
            **TOOL_WITH_SHELL_COMMAND,
            "shell_command": "echo '$(inputs.input.forward.element_identifier) $(inputs.input.forward.basename) $(inputs.input.reverse.element_identifier) $(inputs.input.reverse.basename)' > output.fastq",
            "inputs": [{"type": "data_collection", "name": "input", "collection_type": "paired"}],
        }
        with (
            self.dataset_populator.test_history() as history_id,
            self.dataset_populator.user_tool_execute_permissions(),
        ):
            dynamic_tool = self.dataset_populator.create_unprivileged_tool(UserToolSource(**tool))
            r1 = self.dataset_populator.new_dataset(history_id=history_id, content="a", name="r1.fq")
            r2 = self.dataset_populator.new_dataset(history_id=history_id, content="b", name="r2.fq")
            hdca = self.dataset_collection_populator.create_pair_in_history(
                history_id,
                direct_upload=False,
                element_identifiers=[
                    {"name": "forward", "src": "hda", "id": r1["id"]},
                    {"name": "reverse", "src": "hda", "id": r2["id"]},
                ],
                wait=True,
            ).json()
            self._run(
                history_id=history_id,
                tool_uuid=dynamic_tool["uuid"],
                inputs={"input": {"src": "hdca", "id": hdca["id"]}},
                assert_ok=True,
            )
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            output_content = self.dataset_populator.get_history_dataset_content(history_id)
        assert output_content == "forward r1.fq reverse r2.fq\n"

    def test_run_mapped_over_deferred_list_with_deferred_input_writes_element_identifiers(self):
        tool = {
            **TOOL_WITH_SHELL_COMMAND,
            "shell_command": "echo '$(inputs.input.element_identifier) $(inputs.ref.element_identifier)' > output.fastq",
            "inputs": [
                {"type": "data", "name": "input", "format": "txt"},
                {"type": "data", "name": "ref", "format": "txt"},
            ],
        }

        def deferred(name: str, content: str) -> dict[str, Any]:
            url = f"base64://{base64.b64encode(content.encode()).decode()}"
            return {"src": "url", "url": url, "deferred": True, "ext": "txt", "name": name}

        with (
            self.dataset_populator.test_history() as history_id,
            self.dataset_populator.user_tool_execute_permissions(),
        ):
            dynamic_tool = self.dataset_populator.create_unprivileged_tool(UserToolSource(**tool))
            hdca = self.dataset_collection_populator.create_list_in_history(
                history_id, contents=[deferred("sample_a", "a"), deferred("sample_b", "b")], wait=True
            ).json()["outputs"][0]
            ref = self.dataset_populator.fetch_hda(history_id, deferred("ref.txt", "ref"))
            run = self._run(
                history_id=history_id,
                tool_uuid=dynamic_tool["uuid"],
                inputs={
                    "input": {"batch": True, "values": [{"src": "hdca", "id": hdca["id"]}]},
                    "ref": {"src": "hda", "id": ref["id"]},
                },
                assert_ok=True,
            )
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            contents = self.dataset_populator.get_collection_element_contents(
                history_id, run["implicit_collections"][0]["id"]
            )
        assert contents == {"sample_a": "sample_a ref.txt\n", "sample_b": "sample_b ref.txt\n"}

    def test_tool_request_plain_dataset_element_identifier_falls_back_to_name(self):
        with (
            self.dataset_populator.test_history() as history_id,
            self.dataset_populator.user_tool_execute_permissions(),
        ):
            dynamic_tool = self.dataset_populator.create_unprivileged_tool(
                UserToolSource(**TOOL_WITH_ELEMENT_IDENTIFIER)
            )
            dataset = self.dataset_populator.new_dataset(history_id=history_id, content="abc", name="reads.txt")
            response = self.dataset_populator.tool_request_raw(
                tool_id=None,
                inputs={"input": {"src": "hda", "id": dataset["id"]}},
                history_id=history_id,
                tool_uuid=dynamic_tool["uuid"],
            )
            self._assert_status_code_is(response, 200)
            assert self.dataset_populator.wait_on_tool_request(response.json()["tool_request_id"])
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            output_content = self.dataset_populator.get_history_dataset_content(history_id)
        assert output_content == "reads.txt\n"

    def test_run_links_secondary_file_next_to_input(self):
        self._assert_links_bam_index(via_tool_request=False)

    def test_tool_request_links_secondary_file_next_to_input(self):
        self._assert_links_bam_index(via_tool_request=True)

    def _assert_links_bam_index(self, via_tool_request: bool) -> None:
        with self._user_tool_history() as history_id:
            bam = self.dataset_populator.new_bam_dataset(history_id, self.test_data_resolver)
            output = self._run_user_tool(
                history_id, TOOL_LINKING_BAM_INDEX, {"input": {"src": "hda", "id": bam["id"]}}, via_tool_request
            )
            assert output.strip() == self._bam_index_hex(history_id, bam)

    def test_run_multiple_input_lists_secondary_files(self):
        tool = {
            **TOOL_LINKING_BAM_INDEX,
            "shell_command": "echo '$(inputs.input.map((f) => f.secondaryFiles[0].format).join(\",\"))' > output.fastq",
            "inputs": [{**BAM_INPUT_WITH_SECONDARY_FILES, "multiple": True}],
        }
        with self._user_tool_history() as history_id:
            bams = self._new_bams(history_id, 2)
            inputs = {"input": [{"src": "hda", "id": bam["id"]} for bam in bams]}
            assert self._run_user_tool(history_id, tool, inputs) == "bai,bai\n"

    def test_run_collection_input_lists_secondary_files(self):
        self._assert_collection_input_lists_secondary_files(via_tool_request=False)

    def test_tool_request_collection_input_lists_secondary_files(self):
        self._assert_collection_input_lists_secondary_files(via_tool_request=True)

    def _assert_collection_input_lists_secondary_files(self, via_tool_request: bool) -> None:
        # /api/tools and tool requests give a list different shapes, elements only appears in the latter.
        tool = {
            **TOOL_LINKING_BAM_INDEX,
            "shell_command": (
                "echo '$((inputs.input.elements || inputs.input).map((f) => f.secondaryFiles[0].format).join(\",\"))'"
                " > output.fastq"
            ),
            "inputs": [
                {"type": "data_collection", "name": "input", "collection_type": "list", "secondary_files": True}
            ],
        }
        with self._user_tool_history() as history_id:
            hdca = self._new_bam_list(history_id, 2)
            output = self._run_user_tool(
                history_id, tool, {"input": {"src": "hdca", "id": hdca["id"]}}, via_tool_request
            )
            assert output == "bai,bai\n"

    def test_run_mapped_over_list_lists_secondary_files(self):
        tool = {
            **TOOL_LINKING_BAM_INDEX,
            "shell_command": "echo '$(inputs.input.secondaryFiles[0].nameext)' > output.fastq",
        }
        with self._user_tool_history() as history_id:
            hdca = self._new_bam_list(history_id, 1)
            inputs = {"input": {"batch": True, "values": [{"src": "hdca", "id": hdca["id"]}]}}
            assert self._run_user_tool(history_id, tool, inputs) == ".bai\n"

    def test_run_secondary_files_empty_unless_asked_for_and_indexed(self):
        # Only a dataset in a format Galaxy indexes, on an input that sets secondary_files, gets an index.
        tool = {
            **TOOL_LINKING_BAM_INDEX,
            "shell_command": (
                "echo '$(inputs.not_asked.secondaryFiles.length) $(inputs.not_indexed.secondaryFiles.length)'"
                " > output.fastq"
            ),
            "inputs": [
                {"type": "data", "name": "not_asked", "format": "bam"},
                {"type": "data", "name": "not_indexed", "format": ["bam", "txt"], "secondary_files": True},
            ],
        }
        with self._user_tool_history() as history_id:
            bam = self.dataset_populator.new_bam_dataset(history_id, self.test_data_resolver)
            txt = self.dataset_populator.new_dataset(history_id=history_id, content="abc", wait=True)
            inputs = {"not_asked": {"src": "hda", "id": bam["id"]}, "not_indexed": {"src": "hda", "id": txt["id"]}}
            assert self._run_user_tool(history_id, tool, inputs) == "0 0\n"

    @contextmanager
    def _user_tool_history(self) -> Iterator[str]:
        with (
            self.dataset_populator.test_history() as history_id,
            self.dataset_populator.user_tool_execute_permissions(),
        ):
            yield history_id

    def _run_user_tool(
        self, history_id: str, tool: dict[str, Any], inputs: dict[str, Any], via_tool_request: bool = False
    ) -> str:
        """Create a UDT, run it via /api/tools or a tool request, and return the newest dataset's content."""
        tool_uuid = self.dataset_populator.create_unprivileged_tool(UserToolSource(**tool))["uuid"]
        if via_tool_request:
            response = self.dataset_populator.tool_request_raw(
                tool_id=None, inputs=inputs, history_id=history_id, tool_uuid=tool_uuid
            )
            self._assert_status_code_is(response, 200)
            assert self.dataset_populator.wait_on_tool_request(response.json()["tool_request_id"])
        else:
            self._run(history_id=history_id, tool_uuid=tool_uuid, inputs=inputs, assert_ok=True)
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        return self.dataset_populator.get_history_dataset_content(history_id)

    def _new_bams(self, history_id: str, count: int) -> list[dict[str, Any]]:
        return [self.dataset_populator.new_bam_dataset(history_id, self.test_data_resolver) for _ in range(count)]

    def _new_bam_list(self, history_id: str, count: int) -> dict[str, Any]:
        return self.dataset_collection_populator.create_list_in_history(
            history_id,
            direct_upload=False,
            element_identifiers=[
                {"name": f"sample_{i}", "src": "hda", "id": bam["id"]}
                for i, bam in enumerate(self._new_bams(history_id, count))
            ],
            wait=True,
        ).json()

    def _bam_index_hex(self, history_id: str, bam: dict[str, Any]) -> str:
        index = self.dataset_populator.get_history_dataset_metadata_file(history_id, bam["id"], "bam_index")
        return index.hex()

    def _run_mapped_over_list(
        self, tool: dict[str, Any], elements: list[tuple[str, str]], ext: str = "txt"
    ) -> dict[str, str]:
        """Run a UDT mapped over a new list via /api/tools; return output contents by element identifier."""
        with (
            self.dataset_populator.test_history() as history_id,
            self.dataset_populator.user_tool_execute_permissions(),
        ):
            dynamic_tool = self.dataset_populator.create_unprivileged_tool(UserToolSource(**tool))
            hdca = self.dataset_collection_populator.create_list_of_named_datasets(history_id, elements, ext=ext)
            run = self._run(
                history_id=history_id,
                tool_uuid=dynamic_tool["uuid"],
                inputs={"input": {"batch": True, "values": [{"src": "hdca", "id": hdca["id"]}]}},
                assert_ok=True,
            )
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            return self.dataset_populator.get_collection_element_contents(
                history_id, run["implicit_collections"][0]["id"]
            )

    def _tool_request_mapped_over_list(
        self, tool: dict[str, Any], elements: list[tuple[str, str]], ext: str = "txt"
    ) -> dict[str, str]:
        """Run a UDT mapped over a new list via /api/jobs; return output contents by element identifier."""
        with (
            self.dataset_populator.test_history() as history_id,
            self.dataset_populator.user_tool_execute_permissions(),
        ):
            dynamic_tool = self.dataset_populator.create_unprivileged_tool(UserToolSource(**tool))
            hdca = self.dataset_collection_populator.create_list_of_named_datasets(history_id, elements, ext=ext)
            response = self.dataset_populator.tool_request_raw(
                tool_id=None,
                inputs={"input": {"__class__": "Batch", "values": [{"src": "hdca", "id": hdca["id"]}]}},
                history_id=history_id,
                tool_uuid=dynamic_tool["uuid"],
            )
            self._assert_status_code_is(response, 200)
            tool_request_id = response.json()["tool_request_id"]
            assert self.dataset_populator.wait_on_tool_request(tool_request_id)
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            [implicit] = self.dataset_populator.get_tool_request(tool_request_id)["implicit_collections"]
            return self.dataset_populator.get_collection_element_contents(history_id, implicit["id"])

    def test_rerun_private_udt_denied_for_non_owner_with_execute_role(self):
        with (
            self.dataset_populator.test_history() as history_id,
            self.dataset_populator.user_tool_execute_permissions(),
        ):
            dynamic_tool = self.dataset_populator.create_unprivileged_tool(UserToolSource(**TOOL_WITH_SHELL_COMMAND))
            dataset = self.dataset_populator.new_dataset(history_id=history_id, content="abc")
            run_response = self._run(
                history_id=history_id,
                tool_uuid=dynamic_tool["uuid"],
                inputs={"input": {"src": "hda", "id": dataset["id"]}},
            )
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            job_id = run_response.json()["jobs"][0]["id"]
            tool_uuid = dynamic_tool["uuid"]
            self.dataset_populator.make_public(history_id)

            other_email = f"udt_non_owner_{uuid4()}@bx.psu.edu"
            with self._different_user(email=other_email):
                with self.dataset_populator.user_tool_execute_permissions():
                    # Import A's published history into B's account so B holds a
                    # legitimate copy of the data; rerun must still be denied.
                    copy_response = self.dataset_populator.copy_history(history_id)
                    copy_response.raise_for_status()

                    rerun_response = self.dataset_populator._get(f"jobs/{job_id}/build_for_rerun")
                    assert rerun_response.status_code == 403, rerun_response.text

                    tool_response = self.dataset_populator._get(f"tools/{tool_uuid}")
                    assert tool_response.status_code in (403, 404), tool_response.text

    def test_rerun_private_udt_denied_for_user_without_execute_role(self):
        with (
            self.dataset_populator.test_history() as history_id,
            self.dataset_populator.user_tool_execute_permissions(),
        ):
            dynamic_tool = self.dataset_populator.create_unprivileged_tool(UserToolSource(**TOOL_WITH_SHELL_COMMAND))
            dataset = self.dataset_populator.new_dataset(history_id=history_id, content="abc")
            run_response = self._run(
                history_id=history_id,
                tool_uuid=dynamic_tool["uuid"],
                inputs={"input": {"src": "hda", "id": dataset["id"]}},
            )
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            job_id = run_response.json()["jobs"][0]["id"]
            self.dataset_populator.make_public(history_id)

            other_email = f"udt_no_role_{uuid4()}@bx.psu.edu"
            with self._different_user(email=other_email):
                # Import A's published history into B's account so B holds a
                # legitimate copy of the data; rerun must still be denied.
                copy_response = self.dataset_populator.copy_history(history_id)
                copy_response.raise_for_status()

                rerun_response = self.dataset_populator._get(f"jobs/{job_id}/build_for_rerun")
                assert rerun_response.status_code == 403, rerun_response.text

    def test_deactivate(self):
        with self.dataset_populator.user_tool_execute_permissions():
            # Create a new dynamic tool.
            dynamic_tool = self.dataset_populator.create_unprivileged_tool(UserToolSource(**TOOL_WITH_SHELL_COMMAND))
            # Deactivate the tool.
            self.dataset_populator.deactivate_unprivileged_tool(dynamic_tool["uuid"])
            # Check that the tool is deactivated.
            dynamic_tools = self.dataset_populator.get_unprivileged_tools()
            assert not any(
                dynamic_tool["uuid"] == t["uuid"] for t in dynamic_tools
            ), f"Dynamic tool {dynamic_tool['uuid']} still in dynamic tools list {dynamic_tools}"

    def test_create_unprivileged_rejects_unparseable_shell_command(self):
        """A shell_command with an unbalanced '$(' is refused at create time.

        It can never be evaluated, so storing it only buys a job that fails with
        an internal expression-scanner error (#23147).
        """
        representation = dict(TOOL_WITH_SHELL_COMMAND)
        representation["shell_command"] = 'n="$(wc -l < "$INPUT)"\ncat out.txt > output.fastq\n'
        with self.dataset_populator.user_tool_execute_permissions():
            response = self.dataset_populator.create_unprivileged_tool(
                UserToolSource(**representation), assert_ok=False
            )
        assert response["err_code"] == 400008, response
        assert "Unterminated expression in tool shell_command at line 1, column 4" in response["err_msg"]
        # The message names the escape that makes a literal shell substitution work.
        assert "\\$(" in response["err_msg"]
        assert "uuid" not in response
