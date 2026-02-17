"""Integration test for https://github.com/galaxyproject/galaxy/issues/21802

Tool output sharing should depend on history preferences, not on input dataset sharing status.
When a dataset is imported from a public library into a history configured with a private object
store, running a tool on that dataset should succeed — outputs should go to the private store
with private permissions, regardless of the input's origin.
"""

import string

from galaxy_test.base import api_asserts
from galaxy_test.base.populators import LibraryPopulator
from ._base import BaseObjectStoreIntegrationTestCase

DISTRIBUTED_OBJECT_STORE_WITH_PRIVATE_CONFIG_TEMPLATE = string.Template(
    """<?xml version="1.0"?>
<object_store type="distributed" id="primary" order="0">
    <backends>
        <backend id="default" allow_selection="true" type="disk" weight="1" name="Default Store">
            <files_dir path="${temp_directory}/files_default"/>
            <extra_dir type="temp" path="${temp_directory}/tmp_default"/>
            <extra_dir type="job_work" path="${temp_directory}/job_working_directory_default"/>
        </backend>
        <backend id="private" allow_selection="true" type="disk" weight="0" private="true" name="Private Store">
            <files_dir path="${temp_directory}/files_private"/>
            <extra_dir type="temp" path="${temp_directory}/tmp_private"/>
            <extra_dir type="job_work" path="${temp_directory}/job_working_directory_private"/>
        </backend>
    </backends>
</object_store>
"""
)


class TestToolOutputFromLibraryImportWithPrivateObjectStore(BaseObjectStoreIntegrationTestCase):
    """Test that tool outputs respect history's preferred (private) object store
    even when input datasets originate from a public library.

    Reproduces https://github.com/galaxyproject/galaxy/issues/21802
    """

    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        cls._configure_object_store(DISTRIBUTED_OBJECT_STORE_WITH_PRIVATE_CONFIG_TEMPLATE, config)
        config["object_store_store_by"] = "uuid"
        config["outputs_to_working_directory"] = True
        config["new_user_dataset_access_role_default_private"] = True

    def setUp(self):
        super().setUp()
        self.library_populator = LibraryPopulator(self.galaxy_interactor)

    def test_tool_output_uses_history_preferred_private_store_with_library_input(self):
        """Running a tool on a library-imported dataset should succeed when the
        history uses a private preferred object store."""
        with self.dataset_populator.test_history() as history_id:
            # Set history to use the private object store
            self.dataset_populator.update_history(history_id, {"preferred_object_store_id": "private"})

            # Upload a dataset directly — should work and land in the private store
            hda_direct = self.dataset_populator.new_dataset(history_id, content="1 2 3", wait=True)
            direct_storage = self.dataset_populator.dataset_storage_info(hda_direct["id"])
            assert (
                direct_storage["object_store_id"] == "private"
            ), f"Direct upload should go to private store, got {direct_storage['object_store_id']}"

            # Run a tool on the directly-uploaded dataset — should succeed
            run_response = self.dataset_populator.run_tool(
                "cat1",
                inputs={"input1": {"src": "hda", "id": hda_direct["id"]}},
                history_id=history_id,
            )
            self.dataset_populator.wait_for_history(history_id)
            job = run_response["jobs"][0]
            job_details = self.dataset_populator.get_job_details(job["id"], full=True).json()
            assert job_details["state"] == "ok", f"Direct input tool run failed: {job_details}"

            # Create a library dataset (goes to default/public store)
            library_dataset = self.library_populator.new_library_dataset("test_lib_for_private_history")

            # Copy the library dataset into the history with the private preferred store
            copy_payload = {"content": library_dataset["id"], "source": "library", "type": "dataset"}
            copy_response = self._post(f"histories/{history_id}/contents", data=copy_payload, json=True)
            copy_response.raise_for_status()
            copied_hda = copy_response.json()
            self.dataset_populator.wait_for_history(history_id)

            # Verify the copied dataset is from the default (public) store
            copied_storage = self.dataset_populator.dataset_storage_info(copied_hda["id"])
            assert (
                copied_storage["object_store_id"] == "default"
            ), f"Library import should retain default store, got {copied_storage['object_store_id']}"

            # Make the imported dataset public — simulating a dataset from a public
            # data library where datasets are accessible to all users. This is the
            # crux of the bug: the input's access permissions (public) propagate to
            # tool outputs, which then conflict with the private object store.
            response = self.dataset_populator.make_dataset_public_raw(history_id, copied_hda["id"])
            api_asserts.assert_status_code_is_ok(response)

            # Run a tool on the library-imported dataset — this is the scenario from the bug
            run_response = self.dataset_populator.run_tool(
                "cat1",
                inputs={"input1": {"src": "hda", "id": copied_hda["id"]}},
                history_id=history_id,
            )
            self.dataset_populator.wait_for_history(history_id)
            job = run_response["jobs"][0]
            job_details = self.dataset_populator.get_job_details(job["id"], full=True).json()
            # This is the core assertion — the job should succeed, not fail with
            # "Job attempted to create sharable output datasets in a storage location
            #  with sharing disabled"
            assert job_details["state"] == "ok", (
                f"Tool run on library-imported dataset failed with state '{job_details['state']}'. "
                f"Expected outputs to respect history's private store preference regardless of input origin."
            )

            # Verify the output landed in the private store
            output = job_details["outputs"]["out_file1"]
            output_storage = self.dataset_populator.dataset_storage_info(output["id"])
            assert (
                output_storage["object_store_id"] == "private"
            ), f"Tool output should be in the private store, got {output_storage['object_store_id']}"
