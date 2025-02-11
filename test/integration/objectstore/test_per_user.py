from typing import (
    Any,
    Dict,
    Tuple,
)

from galaxy.objectstore.templates.examples import get_example
from galaxy_test.base import api_asserts
from galaxy_test.driver import integration_util
from ._base import BaseObjectStoreIntegrationTestCase
from .test_selection_with_resource_parameters import DISTRIBUTED_OBJECT_STORE_CONFIG_TEMPLATE

LIBRARY_2 = """
- id: general_disk
  name: General Disk
  description: General Disk Bound to You
  configuration:
    type: disk
    files_dir: '/data/general/{{ user.username }}'
    badges:
    - type: more_secure
    - type: faster
- id: secure_disk
  name: Secure Disk
  description: Secure Disk Bound to You
  configuration:
    type: disk
    files_dir: '/data/secure/{{ user.username }}'
    badges:
    - type: more_secure
    - type: slower
"""


LIBRARY_WITH_SECRET = """
- id: secure_disk
  name: Secure Disk
  description: Secure Disk Bound to You
  secrets:
    sec1:
      help: This is my test secret.
  configuration:
    type: disk
    files_dir: '/data/secure/{{ user.username }}/{{ secrets.sec1 }}/aftersec'
    badges:
    - type: more_secure
    - type: slower
"""


# These should not be things that affect the path... it is more for like
# enabling new connection features, etc...
MULTI_VERSION_LIBRARY = """
- id: general_disk
  version: 0
  name: General Disk (ver 0)
  description: General Disk Bound to You
  variables:
    var_1:
      type: string
      help: Variable 1.
  configuration:
    type: disk
    files_dir: '/data/version1/{{ variables.var_1 }}'
- id: general_disk
  version: 1
  name: General Disk (ver 1)
  description: General Disk Bound to You
  variables:
    var_1:
      type: string
      help: Variable 1.
    var_2:
      type: string
      help: Variable 2.
  configuration:
    type: disk
    files_dir: '/data/version1/{{ variables.var_1 }}_{{ variables.var_2 }}'
"""


MULTI_VERSION_WITH_SECRETS_LIBRARY = get_example("testing_multi_version_with_secrets.yml")


class BaseUserObjectStoreIntegration(BaseObjectStoreIntegrationTestCase):
    def _create_simple_payload(self) -> Dict[str, Any]:
        body = {
            "name": "My Cool Disk",
            "template_id": "general_disk",
            "template_version": 0,
            "secrets": {},
            "variables": {},
        }
        return body

    def _create_simple_object_store(self) -> str:
        before_selectable_object_store_count = len(self.dataset_populator.selectable_object_stores())

        body = self._create_simple_payload()
        object_store_json = self.dataset_populator.create_object_store(body)
        assert "name" in object_store_json
        assert object_store_json["name"] == "My Cool Disk"
        object_store_id = object_store_json["object_store_id"]
        assert object_store_id.startswith("user_objects://")

        object_stores = self.dataset_populator.selectable_object_stores()
        after_selectable_object_store_count = len(object_stores)
        assert after_selectable_object_store_count == before_selectable_object_store_count + 1
        return object_store_id

    def _create_hda_get_storage_info(self, history_id: str):
        hda1 = self.dataset_populator.new_dataset(history_id, content="1 2 3")
        self.dataset_populator.wait_for_history(history_id)
        return self.dataset_populator.dataset_storage_info(hda1["id"]), hda1

    def _run_tool_with_object_store_id_and_then_revert(self, history_id: str, object_store_id: str):
        storage_info, hda1 = self._create_hda_get_storage_info(history_id)
        assert storage_info["object_store_id"] == "default"

        self.dataset_populator.set_user_preferred_object_store_id(object_store_id)

        def _run_tool(tool_id, inputs, preferred_object_store_id=None):
            response = self.dataset_populator.run_tool(
                tool_id,
                inputs,
                history_id,
                preferred_object_store_id=preferred_object_store_id,
            )
            self.dataset_populator.wait_for_history(history_id)
            return response

        hda1_input = {"src": "hda", "id": hda1["id"]}
        response = _run_tool("multi_data_param", {"f1": hda1_input, "f2": hda1_input})
        storage_info, output = self._storage_info_for_job_output(response)
        self.dataset_populator.set_user_preferred_object_store_id(None)
        return storage_info, output

    def _storage_info_for_job_output(self, job_dict) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        outputs = job_dict["outputs"]  # could be a list or dictionary depending on source
        try:
            output = outputs[0]
        except KeyError:
            output = list(outputs.values())[0]
        storage_info = self.dataset_populator.dataset_storage_info(output["id"])
        return storage_info, output

    @classmethod
    def _write_template_and_object_store_config(cls, config, catalog: str):
        cls._configure_object_store(DISTRIBUTED_OBJECT_STORE_CONFIG_TEMPLATE, config)
        cls._configure_object_store_template_catalog(catalog, config)

    def _get_dataset_filename(self, history_id: str, output: Dict[str, Any]) -> str:
        details = self.dataset_populator.get_history_dataset_details(history_id, dataset_id=output["id"])
        assert "file_name" in details
        file_name = details["file_name"]
        assert file_name
        return file_name


class TestPerUserObjectStoreIntegration(BaseUserObjectStoreIntegration):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        cls._write_template_and_object_store_config(config, LIBRARY_2)

    def test_create_and_update(self):
        body = self._create_simple_payload()
        object_store_json = self.dataset_populator.create_object_store(body)
        assert object_store_json["template_version"] == 0
        badges = object_store_json["badges"]
        badge_types = {b["type"] for b in badges}
        assert "user_defined" in badge_types
        assert "restricted" in badge_types
        assert "cloud" not in badge_types
        assert "faster" in badge_types
        assert "more_secure" in badge_types
        assert "no_quota" in badge_types
        persisted_object_store_id = object_store_json["uuid"]

        payload = {
            "name": "my new name",
            "description": "my new description",
        }
        response = self.dataset_populator.update_object_store(persisted_object_store_id, payload)
        assert response["name"] == "my new name"
        assert response["description"] == "my new description"
        assert response["template_version"] == 0

    def test_create_and_use_simple(self):
        object_store_id = self._create_simple_object_store()
        with self.dataset_populator.test_history() as history_id:
            storage_info, hda1 = self._create_hda_get_storage_info(history_id)
            assert storage_info["object_store_id"] == "default"
            self.dataset_populator.set_user_preferred_object_store_id(object_store_id)

            def _run_tool(tool_id, inputs, preferred_object_store_id=None):
                response = self.dataset_populator.run_tool(
                    tool_id,
                    inputs,
                    history_id,
                    preferred_object_store_id=preferred_object_store_id,
                )
                self.dataset_populator.wait_for_history(history_id)
                return response

            hda1_input = {"src": "hda", "id": hda1["id"]}
            response = _run_tool("multi_data_param", {"f1": hda1_input, "f2": hda1_input})
            storage_info, output = self._storage_info_for_job_output(response)
            assert storage_info["object_store_id"] == object_store_id
            contents = self.dataset_populator.get_history_dataset_content(history_id, dataset=output)
            assert contents.startswith("1 2 3")
            self.dataset_populator.set_user_preferred_object_store_id(None)

    def test_create_unknown_id(self):
        body = {
            "template_id": "general_disk_2",
            "template_version": 0,
            "name": "My Unknown Disk",
            "secrets": {},
            "variables": {},
        }
        response = self.dataset_populator.create_object_store_raw(body)
        api_asserts.assert_status_code_is(response, 404)

    def test_create_invalid_version(self):
        body = {
            "template_id": "general_disk",
            "template_version": "0.0.0",
            "name": "My Unknown Disk",
            "secrets": {},
            "variables": {},
        }
        response = self.dataset_populator.create_object_store_raw(body)
        api_asserts.assert_status_code_is(response, 400)


class TestPerUserObjectStoreWithSecretsIntegration(
    BaseUserObjectStoreIntegration, integration_util.ConfiguresDatabaseVault
):
    # so we can see paths in the API...
    require_admin_user = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        cls._configure_database_vault(config)
        cls._write_template_and_object_store_config(config, LIBRARY_WITH_SECRET)

    def test_creation_with_secrets(self):
        body = {
            "name": "My Cool Disk",
            "template_id": "secure_disk",
            "template_version": 0,
            "secrets": {
                "sec1": "foobar",
            },
            "variables": {},
        }
        object_store_json = self.dataset_populator.create_object_store(body)
        object_store_id = object_store_json["object_store_id"]
        persisted_object_store_id = object_store_json["uuid"]

        with self.dataset_populator.test_history() as history_id:
            _, output = self._run_tool_with_object_store_id_and_then_revert(history_id, object_store_id)
            file_name = self._get_dataset_filename(history_id, output)
            assert "foobar" in file_name

            update_payload = {
                "secret_name": "sec1",
                "secret_value": "newbar",
            }
            self.dataset_populator.update_object_store(persisted_object_store_id, update_payload)

            _, output = self._run_tool_with_object_store_id_and_then_revert(history_id, object_store_id)
            file_name = self._get_dataset_filename(history_id, output)
            assert "foobar" not in file_name
            assert "newbar" in file_name


class TestPerUserObjectStoreWithExtendedMetadataIntegration(BaseUserObjectStoreIntegration):
    """This requires serializing the object store...

    ...so there is a lot of complexity behind the scenes tested here."""

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        cls._write_template_and_object_store_config(config, LIBRARY_2)
        config["metadata_strategy"] = "extended"
        # config["tool_evaluation_strategy"] = "remote"
        config["retry_metadata_internally"] = False

    def test_create_and_use(self):
        object_store_id = self._create_simple_object_store()
        with self.dataset_populator.test_history() as history_id:
            storage_info, output = self._run_tool_with_object_store_id_and_then_revert(history_id, object_store_id)
            assert storage_info["object_store_id"] == object_store_id
            contents = self.dataset_populator.get_history_dataset_content(history_id, dataset=output)
            assert contents.startswith("1 2 3")
            self.dataset_populator.set_user_preferred_object_store_id(None)


class TestPerUserObjectStoreUpgradesIntegration(BaseUserObjectStoreIntegration):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        cls._write_template_and_object_store_config(config, MULTI_VERSION_LIBRARY)

    def test_create_and_upgrade(self):
        body = {
            "name": "My Upgradable Disk",
            "template_id": "general_disk",
            "template_version": 0,
            "secrets": {},
            "variables": {
                "var_1": "moo_cow",
            },
        }
        object_store_json = self.dataset_populator.create_object_store(body)
        assert "name" in object_store_json
        assert object_store_json["name"] == "My Upgradable Disk"
        assert object_store_json["template_version"] == 0

        id = object_store_json["uuid"]
        object_store_id = object_store_json["object_store_id"]
        assert object_store_id.startswith("user_objects://")

        object_stores = self.dataset_populator.selectable_object_stores()
        assert len(object_stores) == 1
        user_object_store = object_stores[0]
        assert user_object_store["name"] == "My Upgradable Disk"

        body = {
            "template_version": 1,
            "secrets": {},
            "variables": {
                "var_1": "moo",
                "var_2": "cow",
            },
        }
        object_store_json = self.dataset_populator.upgrade_object_store(id, body)
        assert "name" in object_store_json
        assert object_store_json["name"] == "My Upgradable Disk"
        new_object_store_id = object_store_json["object_store_id"]
        assert new_object_store_id == object_store_id
        assert object_store_json["uuid"] == id
        assert object_store_json["template_version"] == 1


class TestPerUserObjectStoreUpgradesWithSecretsIntegration(
    BaseUserObjectStoreIntegration, integration_util.ConfiguresDatabaseVault
):
    require_admin_user = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        cls._configure_database_vault(config)
        cls._write_template_and_object_store_config(config, MULTI_VERSION_WITH_SECRETS_LIBRARY)

    def test_create_and_upgrade(self):
        body = {
            "name": "My Upgradable Disk",
            "template_id": "secure_disk",
            "template_version": 0,
            "secrets": {
                "sec1": "moocow",
            },
            "variables": {},
        }
        object_store_json = self.dataset_populator.create_object_store(body)
        assert "name" in object_store_json
        assert object_store_json["name"] == "My Upgradable Disk"
        assert object_store_json["template_version"] == 0
        id = object_store_json["uuid"]
        object_store_id = object_store_json["object_store_id"]

        secrets = object_store_json["secrets"]
        assert "sec1" in secrets
        assert "sec2" not in secrets

        with self.dataset_populator.test_history() as history_id:
            _, output = self._run_tool_with_object_store_id_and_then_revert(history_id, object_store_id)
            file_name = self._get_dataset_filename(history_id, output)
            assert "moocow/aftersec" in file_name
            assert "moocow/aftersec2" not in file_name

            body = {
                "template_version": 1,
                "secrets": {
                    "sec1": "moocow",
                    "sec2": "aftersec2",
                },
                "variables": {},
            }
            object_store_json = self.dataset_populator.upgrade_object_store(id, body)
            secrets = object_store_json["secrets"]
            assert object_store_json["template_version"] == 1
            assert "sec1" in secrets
            assert "sec2" in secrets

            _, output = self._run_tool_with_object_store_id_and_then_revert(history_id, object_store_id)
            file_name = self._get_dataset_filename(history_id, output)

            assert "moocow/aftersec2" in file_name

            body = {
                "template_version": 2,
                "secrets": {},
                "variables": {},
            }
            object_store_json = self.dataset_populator.upgrade_object_store(id, body)
            secrets = object_store_json["secrets"]
            assert object_store_json["template_version"] == 2
            assert "sec1" not in secrets
            assert "sec2" in secrets


class TestPerUserObjectStoreQuotaIntegration(BaseUserObjectStoreIntegration):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        cls._write_template_and_object_store_config(config, LIBRARY_2)
        config["enable_quotas"] = True

    def test_user_object_store_does_not_pause_jobs_over_quota(self):
        object_store_id = self._create_simple_object_store()
        with self.dataset_populator.test_history() as history_id:

            def _run_tool(tool_id, inputs, preferred_object_store_id=None):
                response = self.dataset_populator.run_tool(
                    tool_id,
                    inputs,
                    history_id,
                    preferred_object_store_id=preferred_object_store_id,
                )
                self.dataset_populator.wait_for_history(history_id)
                return response

            # Create one dataset in the default object store
            hda1 = self.dataset_populator.new_dataset(history_id, content="1 2 3\n4 5 6\n7 8 9\n", wait=True)
            storage_info = self.dataset_populator.dataset_storage_info(hda1["id"])
            assert storage_info["object_store_id"] == "default"

            # Set a quota of 1 byte so running a tool will pause the job
            self._define_quota_in_bytes(1)

            # Run a tool
            hda1_input = {"src": "hda", "id": hda1["id"]}
            response = _run_tool("multi_data_param", {"f1": hda1_input, "f2": hda1_input})
            paused_job_id = response["jobs"][0]["id"]
            storage_info, _ = self._storage_info_for_job_output(response)
            assert storage_info["object_store_id"] == "default"

            # The job should be paused because the default object store is over quota
            state = self.dataset_populator.wait_for_job(paused_job_id)
            assert state == "paused"

            # Set the user object store as the preferred object store
            self.dataset_populator.set_user_preferred_object_store_id(object_store_id)

            # Run the tool again
            response = _run_tool("multi_data_param", {"f1": hda1_input, "f2": hda1_input})
            job_id = response["jobs"][0]["id"]
            storage_info, _ = self._storage_info_for_job_output(response)
            assert storage_info["object_store_id"] == object_store_id

            # The job should not be paused because the user object store is not subject to quotas
            state = self.dataset_populator.wait_for_job(job_id)
            assert state == "ok"

    def _define_quota_in_bytes(self, bytes: int):
        quotas = self.dataset_populator.get_quotas()
        assert len(quotas) == 0

        payload = {
            "name": "defaultquota1",
            "description": "first default quota",
            "amount": f"{bytes} bytes",
            "operation": "=",
            "default": "registered",
        }
        self.dataset_populator.create_quota(payload)
