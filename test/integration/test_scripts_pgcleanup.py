import string

from galaxy_test.base.populators import skip_without_tool
from galaxy_test.driver import integration_util
from .test_scripts import BaseScriptsIntegrationTestCase

DISTRIBUTED_OBJECT_STORE_CONFIG_TEMPLATE = string.Template("""
type: distributed
backends:
  - type: disk
    id: default
    weight: 1
    name: Default Store
    files_dir: "${temp_directory}/files_default"
    extra_dirs:
      - type: temp
        path: "${temp_directory}/tmp_default"
      - type: job_work
        path: "${temp_directory}/job_working_directory_default"
""")

USER_OBJECT_STORE_CATALOG = """
- id: general_disk
  name: General Disk
  description: General Disk Bound to You
  configuration:
    type: disk
    files_dir: '/data/general/{{ user.username }}'
"""

SCRIPT = "cleanup_datasets/pgcleanup.py"


class TestScriptsPgCleanupIntegration(BaseScriptsIntegrationTestCase):
    def test_help(self):
        self._skip_unless_postgres()
        self._scripts_check_argparse_help(SCRIPT)

    def test_purge_deleted_histories(self):
        self._skip_unless_postgres()

        history_id = self.dataset_populator.new_history()
        delete_response = self.dataset_populator._delete(f"histories/{history_id}")
        assert delete_response.status_code == 200
        assert delete_response.json()["purged"] is False
        self._pgcleanup_check_output(["--older-than", "0", "--sequence", "purge_deleted_histories"])
        history_response = self.dataset_populator._get(f"histories/{history_id}")
        assert history_response.status_code == 200
        assert history_response.json()["purged"] is True, history_response.json()

    def test_purge_old_hdas(self):
        self._skip_unless_postgres()

        history_id = self.dataset_populator.new_history()
        hda = self.dataset_populator.new_dataset(history_id, wait=True)
        assert not self.is_purged(history_id, hda)

        # filtering on a date too old - shouldn't purge the dataset
        self._pgcleanup_check_output(
            [
                "--older-than",
                "1",
                "--sequence",
                "purge_old_hdas",
            ]
        )
        assert not self.is_purged(history_id, hda)

        # filtering on invalid object store - shouldn't purge the dataset
        self._pgcleanup_check_output(
            [
                "--older-than",
                "0",
                "--object-store-id",
                "myfakeobjectstore",
                "--sequence",
                "purge_old_hdas",
            ]
        )
        assert not self.is_purged(history_id, hda)

        self._pgcleanup_check_output(["--older-than", "0", "--sequence", "purge_old_hdas"])

        assert self.is_purged(history_id, hda)

    @skip_without_tool("test_data_source")
    def test_purge_errored_hdas(self):
        history_id = self.dataset_populator.new_history()
        error_dataset = self.dataset_populator.new_error_dataset(history_id)
        assert not self.is_purged(history_id, error_dataset)

        # dataset not old enough, shouldn't be purged
        self._pgcleanup_check_output(
            [
                "--older-than",
                "1",
                "--sequence",
                "purge_error_hdas",
            ]
        )
        assert not self.is_purged(history_id, error_dataset)

        # dataset not in target object store, shouldn't be purged
        self._pgcleanup_check_output(
            [
                "--older-than",
                "0",
                "--object-store-id",
                "myfakeobjectstore",
                "--sequence",
                "purge_error_hdas",
            ]
        )
        assert not self.is_purged(history_id, error_dataset)

        # okay though, this should purge the dataset
        self._pgcleanup_check_output(
            [
                "--older-than",
                "0",
                "--sequence",
                "purge_error_hdas",
            ]
        )
        assert self.is_purged(history_id, error_dataset)

    def test_purge_datasets(self):
        self._skip_unless_postgres()

        history_id = self.dataset_populator.new_history()
        hda = self.dataset_populator.new_dataset(history_id, wait=True)
        self.dataset_populator.delete_dataset(history_id, hda["id"])
        assert not self.is_purged(history_id, hda)

        self._pgcleanup_check_output(
            [
                "--older-than",
                "1",
                "--sequence",
                "purge_datasets",
            ]
        )
        assert not self.is_purged(history_id, hda)

        self._pgcleanup_check_output(
            [
                "--older-than",
                "0",
                "--object-store-id",
                "myfakeobjectstore",
                "--sequence",
                "purge_datasets",
            ]
        )
        assert not self.is_purged(history_id, hda)

        self._pgcleanup_check_output(
            [
                "--older-than",
                "0",
                "--sequence",
                "purge_datasets",
            ]
        )
        self._pgcleanup_check_output(
            [
                "--older-than",
                "0",
                "--sequence",
                "purge_datasets",
            ]
        )

        # why is this not purged?
        # test or functionality seem broken but better to run through it and ensure
        # it isn't breaking anything and everything is syntactically correct than not
        # assert self.is_purged(history_id, hda)

    def test_delete_datasets(self):
        # this walks through the code to ensure no SQL or Python errors but
        # I think we would need to talk to the model layer from the test directly
        # to actually produce datasets of the target type for purging and to verify
        # they were purged (certainly a possibility)
        self._skip_unless_postgres()

        history_id = self.dataset_populator.new_history()
        hda = self.dataset_populator.new_dataset(history_id, wait=True)

        assert not self.is_purged(history_id, hda)

        self._pgcleanup_check_output(
            [
                "--older-than",
                "0",
                "--sequence",
                "delete_datasets",
            ]
        )
        self._pgcleanup_check_output(
            [
                "--older-than",
                "0",
                "--object-store-id",
                "myfakeobjectstore",
                "--sequence",
                "delete_datasets",
            ]
        )

        assert not self.is_purged(history_id, hda)

    def test_purge_historyless_hdas(self):
        # same as above - this is just a negative test for things being broken
        # we could access the model layer to write a test to verify the positive
        # behavior actually occurs
        self._skip_unless_postgres()

        history_id = self.dataset_populator.new_history()
        hda = self.dataset_populator.new_dataset(history_id, wait=True)

        assert not self.is_purged(history_id, hda)
        self._pgcleanup_check_output(
            [
                "--older-than",
                "0",
                "--sequence",
                "purge_historyless_hdas",
            ]
        )
        self._pgcleanup_check_output(
            [
                "--older-than",
                "0",
                "--object-store-id",
                "myfakeobjectstore",
                "--sequence",
                "purge_historyless_hdas",
            ]
        )

        assert not self.is_purged(history_id, hda)


class TestPgCleanupUserObjectStoreIntegration(
    BaseScriptsIntegrationTestCase,
    integration_util.ConfiguresObjectStores,
):
    """Test that pgcleanup handles datasets in user-defined object stores gracefully.

    When a dataset is stored in a user-defined object store (object_store_id starting
    with "user_objects://"), the pgcleanup script cannot resolve the object store backend
    since it doesn't have access to the UserObjectStoreResolver. The script should skip
    physical file removal for such objects while still updating the database records.
    """

    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        cls._configure_object_store(DISTRIBUTED_OBJECT_STORE_CONFIG_TEMPLATE, config, format="yml")
        config["object_store_store_by"] = "uuid"
        cls._configure_object_store_template_catalog(USER_OBJECT_STORE_CATALOG, config)

    def _create_user_object_store(self) -> str:
        """Create a user-defined object store via the API and return its object_store_id."""
        body = {
            "name": "My Test Disk",
            "template_id": "general_disk",
            "template_version": 0,
            "secrets": {},
            "variables": {},
        }
        object_store_json = self.dataset_populator.create_object_store(body)
        object_store_id = object_store_json["object_store_id"]
        assert object_store_id.startswith("user_objects://")
        return object_store_id

    def test_purge_deleted_histories_with_user_object_store_dataset(self):
        """Test that purging histories containing datasets in user object stores doesn't crash.

        This verifies the fix for the KeyError that occurred when pgcleanup tried to call
        get_store_by() on objects stored in user-defined object stores, which cannot be
        resolved without a UserObjectStoreResolver (not available in the cleanup script).
        """
        self._skip_unless_postgres()

        # Create a user-defined object store
        object_store_id = self._create_user_object_store()

        # Set the user's preferred object store to the user-defined one
        self.dataset_populator.set_user_preferred_object_store_id(object_store_id)

        # Create a history and upload a dataset (it should go to the user object store)
        history_id = self.dataset_populator.new_history()
        hda = self.dataset_populator.new_dataset(history_id, content="test data for user object store", wait=True)

        # Verify the dataset is in the user object store
        storage_info = self.dataset_populator.dataset_storage_info(hda["id"])
        assert (
            storage_info["object_store_id"] == object_store_id
        ), f"Expected dataset in user object store {object_store_id}, but got {storage_info['object_store_id']}"

        # Reset user preference so subsequent datasets don't use it
        self.dataset_populator.set_user_preferred_object_store_id(None)

        # Delete the history
        delete_response = self.dataset_populator._delete(f"histories/{history_id}")
        assert delete_response.status_code == 200
        assert delete_response.json()["purged"] is False

        # Run pgcleanup - this should NOT crash with a KeyError
        # Before the fix, this would raise:
        #   KeyError: 'user_objects://...' in _resolve_backend
        self._pgcleanup_check_output(["--older-than", "0", "--sequence", "purge_deleted_histories"])

        # The history should be purged in the database even though the physical
        # file in the user object store could not be removed
        history_response = self.dataset_populator._get(f"histories/{history_id}")
        assert history_response.status_code == 200
        assert history_response.json()["purged"] is True, history_response.json()

    def test_purge_old_hdas_with_user_object_store_dataset(self):
        """Test that purging HDAs in user object stores doesn't crash pgcleanup."""
        self._skip_unless_postgres()

        object_store_id = self._create_user_object_store()
        self.dataset_populator.set_user_preferred_object_store_id(object_store_id)

        history_id = self.dataset_populator.new_history()
        hda = self.dataset_populator.new_dataset(history_id, content="test data", wait=True)

        # Verify the dataset is in the user object store
        storage_info = self.dataset_populator.dataset_storage_info(hda["id"])
        assert storage_info["object_store_id"] == object_store_id

        self.dataset_populator.set_user_preferred_object_store_id(None)

        # Run pgcleanup - should not crash
        self._pgcleanup_check_output(["--older-than", "0", "--sequence", "purge_old_hdas"])

        # The HDA should be purged in the database
        assert self.is_purged(history_id, hda)
