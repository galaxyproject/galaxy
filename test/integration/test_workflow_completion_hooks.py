"""Integration tests for workflow completion hooks.

These tests verify that workflow completion hooks execute correctly,
including the export_to_file_source hook that exports completed
workflow invocations to a configured file source.
"""

import os
import zipfile

from galaxy_test.base.api import UsesCeleryTasks
from galaxy_test.base.populators import (
    DatasetPopulator,
    wait_on,
    WorkflowPopulator,
)
from galaxy_test.base.workflow_fixtures import WORKFLOW_SIMPLE_CAT_TWICE
from galaxy_test.driver.integration_setup import PosixFileSourceSetup
from galaxy_test.driver.integration_util import IntegrationTestCase


class TestWorkflowCompletionExportHook(PosixFileSourceSetup, IntegrationTestCase, UsesCeleryTasks):
    """Integration tests for the export_to_file_source completion hook."""

    dataset_populator: DatasetPopulator
    workflow_populator: WorkflowPopulator
    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        UsesCeleryTasks.handle_galaxy_config_kwds(config)

    def setUp(self):
        super().setUp()
        self._write_file_fixtures()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.workflow_populator = WorkflowPopulator(self.galaxy_interactor)

    def test_export_to_file_source_on_completion(self):
        """Test that export_to_file_source hook exports invocation when workflow completes."""
        export_filename = "test_export.rocrate.zip"
        target_uri = f"gxfiles://posix_test/{export_filename}"

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
            self.workflow_populator.wait_for_invocation_and_completion(summary.invocation_id, timeout=60)

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
                datasets = [n for n in names if n.startswith("datasets/") and not n.endswith("/")]
                assert len(datasets) == 2, f"Expected 2 datasets, got {len(datasets)}: {datasets}"
                assert "ro-crate-metadata.json" in names, f"Missing ro-crate-metadata.json in {names}"
