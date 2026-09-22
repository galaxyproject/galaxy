"""Exercise bundle finalization and consumption with real local jobs."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from galaxy.model import HistoryDatasetAssociation
from galaxy.tools.parameters.dynamic_options import DynamicOptions
from galaxy_test.base.populators import WorkflowPopulator
from .test_tool_data_delete import DataManagerIntegrationTestCase


class TestDataManagerBundleChaining(DataManagerIntegrationTestCase):
    temp_tool_data_dir: str

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        tool = Path(__file__).resolve().parents[1] / "functional/tools/data_manager_bundle_chain.xml"
        manager_config = Path(cls.temp_tool_data_dir) / "data_managers.xml"
        manager_config.write_text(f"""<data_managers>
  <data_manager id="data_manager_bundle_chain" tool_file="{tool}">
    <data_table name="testbeta">
      <output>
        <column name="value" />
        <column name="path" output_ref="out_file" />
      </output>
    </data_table>
  </data_manager>
</data_managers>""")
        config["data_manager_config_file"] = str(manager_config)
        config["outputs_to_working_directory"] = True
        config["object_store_store_by"] = "id"

    @pytest.mark.parametrize("shape", ["dict", "list"])
    def test_bundle_chaining(self, history_id, shape):
        populator = self.dataset_populator
        producer = populator.run_tool(
            "data_manager_bundle_chain",
            {"shape": shape, "source|kind": "new"},
            history_id,
            data_manager_mode="bundle",
        )
        dataset_id = producer["outputs"][0]["id"]
        populator.wait_for_history(history_id, assert_ok=True)
        producer_job = populator.get_job_details(producer["jobs"][0]["id"], full=True).json()
        recorded_path = producer_job["stdout"].strip()
        assert Path(recorded_path).is_absolute()
        primary = populator.get_history_dataset_content(history_id, dataset_id=dataset_id)
        index = populator.get_history_dataset_content(
            history_id, dataset_id=dataset_id, filename="_gx_data_bundle_index.json"
        )
        primary_rows = json.loads(primary)["data_tables"]["testbeta"]
        assert (primary_rows if shape == "dict" else primary_rows[0])["path"] == recorded_path
        data_tables = json.loads(index)["data_tables"]
        rows = data_tables["testbeta"]
        assert (rows if shape == "dict" else rows[0])["path"] == "db"
        details = populator.get_history_dataset_details(history_id, dataset_id=dataset_id)
        assert details["metadata_is_bundle"]
        assert details["metadata_data_tables"] == data_tables

        # Recompute through Galaxy's metadata job before downstream consumption.
        populator.validate_dataset(history_id, dataset_id)
        populator.wait_for_history(history_id, assert_ok=True)
        details = populator.get_history_dataset_details(history_id, dataset_id=dataset_id)
        assert details["metadata_data_tables"] == data_tables

        hda = self._app.model.context.get(HistoryDatasetAssociation, self._decode_id(dataset_id))
        assert hda is not None
        metadata = deepcopy(hda._metadata)
        key = "motus_3.1.0" if shape == "dict" else "motus"
        for _ in range(2):
            entry = DynamicOptions.hda_to_table_entries(hda, "testbeta")[key]
            assert entry["path"] == str(Path(hda.extra_files_path) / "db")
            assert entry["path"] != recorded_path
            assert hda._metadata == metadata

        workflows = WorkflowPopulator(self.galaxy_interactor)
        workflow_id = workflows.upload_yaml_workflow(
            {
                "class": "GalaxyWorkflow",
                "inputs": {"bundle": {"type": "data"}},
                "steps": {
                    "consume": {
                        "tool_id": "data_manager_bundle_chain",
                        "tool_state": {"shape": shape, "source": {"kind": "bundle"}, "__data_manager_mode": "bundle"},
                        "in": {"source|database": "bundle"},
                    },
                },
                "outputs": {"database": {"outputSource": "consume/out_file"}},
            }
        )
        invocation_id = workflows.invoke_workflow_and_assert_ok(
            workflow_id,
            history_id=history_id,
            inputs={"bundle": {"src": "hda", "id": dataset_id}},
            inputs_by="name",
        )
        invocation = workflows.wait_for_invocation_and_completion(invocation_id)
        populator.wait_for_history(history_id, assert_ok=True)
        version = populator.get_history_dataset_content(
            history_id, dataset_id=invocation["outputs"]["database"]["id"], filename="db/db_mOTU_versions"
        )
        assert version == "3.1.0"
