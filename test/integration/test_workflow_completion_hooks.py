"""Integration tests for workflow completion hooks.

These tests verify that workflow completion hooks execute correctly,
including the export_to_file_source hook that exports completed
workflow invocations to a configured file source.
"""

import os
import time
import zipfile

from galaxy_test.base.api import UsesCeleryTasks
from galaxy_test.base.populators import (
    DatasetPopulator,
    wait_on,
    WorkflowPopulator,
)
from galaxy_test.base.workflow_fixtures import WORKFLOW_SIMPLE_CAT_TWICE
from galaxy_test.driver.integration_util import IntegrationTestCase


def get_simple_file_source_config(root_dir: str) -> str:
    """Generate a simple posix file source config without role/group restrictions."""
    return f"""
- type: posix
  id: completion_export_test
  label: Completion Export Test
  doc: File source for workflow completion export tests
  root: {root_dir}
  writable: true
"""


class TestWorkflowCompletionExportHook(IntegrationTestCase, UsesCeleryTasks):
    """Integration tests for the export_to_file_source completion hook."""

    dataset_populator: DatasetPopulator
    workflow_populator: WorkflowPopulator
    framework_tool_and_types = True
    root_dir: str

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        UsesCeleryTasks.handle_galaxy_config_kwds(config)

        # Set up temp directory for file source using test driver's mkdtemp
        temp_dir = os.path.realpath(cls._test_driver.mkdtemp())
        cls.root_dir = os.path.join(temp_dir, "root")
        os.makedirs(cls.root_dir, exist_ok=True)

        # Create file sources config
        file_sources_config = get_simple_file_source_config(cls.root_dir)
        file_sources_config_file = os.path.join(temp_dir, "file_sources_conf.yml")
        with open(file_sources_config_file, "w") as f:
            f.write(file_sources_config)
        config["file_sources_config_file"] = file_sources_config_file

        # Disable stock file source plugins
        config["ftp_upload_dir"] = None
        config["library_import_dir"] = None
        config["user_library_import_dir"] = None

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.workflow_populator = WorkflowPopulator(self.galaxy_interactor)

    def test_export_to_file_source_on_completion(self):
        """Test that export_to_file_source hook exports invocation when workflow completes."""
        export_filename = "test_export.rocrate.zip"
        target_uri = f"gxfiles://completion_export_test/{export_filename}"

        with self.dataset_populator.test_history() as history_id:
            summary = self.workflow_populator.run_workflow(
                WORKFLOW_SIMPLE_CAT_TWICE,
                test_data={"input1": "hello world"},
                history_id=history_id,
                wait=True,
                assert_ok=True,
                extra_invocation_kwds={
                    "on_complete": [
                        {
                            "export_to_file_source": {
                                "target_uri": target_uri,
                                "format": "rocrate.zip",
                                "include_files": True,
                            }
                        }
                    ],
                },
            )

            # Wait for invocation to reach completed state
            invocation = self.workflow_populator.wait_for_invocation_and_completion(summary.invocation_id, timeout=60)
            assert invocation["state"] == "completed"

            # Wait for the export file to appear (hook execution is async via Celery)
            export_path = os.path.join(self.root_dir, export_filename)

            def check_export_exists():
                return export_path if os.path.exists(export_path) else None

            wait_on(check_export_exists, "export file to be created", timeout=60)

            # Verify the export file exists and is a valid zip
            assert os.path.exists(export_path), f"Export file not found at {export_path}"
            assert zipfile.is_zipfile(export_path), f"Export file is not a valid zip: {export_path}"

            # Verify the zip contains expected rocrate metadata
            with zipfile.ZipFile(export_path, "r") as zf:
                names = zf.namelist()
                assert "ro-crate-metadata.json" in names, f"Missing ro-crate-metadata.json in {names}"

    def test_export_with_multiple_outputs(self):
        """Test export works correctly with multiple workflow outputs."""
        workflow = """
class: GalaxyWorkflow
name: Multi-Output Completion Export Test
inputs:
  input1: data
steps:
  cat1:
    tool_id: cat1
    in:
      input1: input1
  cat2:
    tool_id: cat1
    in:
      input1: input1
outputs:
  output1:
    outputSource: cat1/out_file1
  output2:
    outputSource: cat2/out_file1
"""
        export_filename = "multi_output_export.rocrate.zip"
        target_uri = f"gxfiles://completion_export_test/{export_filename}"

        with self.dataset_populator.test_history() as history_id:
            summary = self.workflow_populator.run_workflow(
                workflow,
                test_data={"input1": "test data content"},
                history_id=history_id,
                wait=True,
                assert_ok=True,
                extra_invocation_kwds={
                    "on_complete": [
                        {
                            "export_to_file_source": {
                                "target_uri": target_uri,
                                "format": "rocrate.zip",
                                "include_files": True,
                            }
                        }
                    ],
                },
            )

            # Wait for completion
            self.workflow_populator.wait_for_invocation_and_completion(summary.invocation_id, timeout=60)

            # Wait for export
            export_path = os.path.join(self.root_dir, export_filename)

            def check_export():
                return export_path if os.path.exists(export_path) else None

            wait_on(check_export, "export file", timeout=60)

            # Verify export contains dataset files
            with zipfile.ZipFile(export_path, "r") as zf:
                names = zf.namelist()
                dataset_files = [n for n in names if n.startswith("datasets/")]
                # Should have input + 2 outputs = 3 datasets
                assert (
                    len(dataset_files) >= 3
                ), f"Expected at least 3 dataset files, found {len(dataset_files)}: {dataset_files}"

    def test_no_export_without_on_complete(self):
        """Test that no export happens when on_complete is not specified."""
        export_filename = "should_not_exist.rocrate.zip"
        export_path = os.path.join(self.root_dir, export_filename)

        with self.dataset_populator.test_history() as history_id:
            summary = self.workflow_populator.run_workflow(
                WORKFLOW_SIMPLE_CAT_TWICE,
                test_data={"input1": "hello world"},
                history_id=history_id,
                wait=True,
                assert_ok=True,
            )

            # Wait for completion
            self.workflow_populator.wait_for_invocation_and_completion(summary.invocation_id, timeout=60)

            # Give a moment for any erroneous export to happen
            time.sleep(2)

            # Verify no export file was created
            assert not os.path.exists(export_path), f"Export file should not exist: {export_path}"
