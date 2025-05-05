from typing import (
    List,
    Optional,
    Type,
)

from yaml import safe_load

from galaxy.exceptions import (
    RequestParameterInvalidException,
    RequestParameterMissingException,
)
from galaxy.managers.object_store_instances import (
    CreateInstancePayload,
    ModifyInstancePayload,
    ObjectStoreInstancesManager,
    TestUpdateInstancePayload,
    TestUpgradeInstancePayload,
    UpdateInstancePayload,
    UpdateInstanceSecretPayload,
    UpgradeInstancePayload,
    UserConcreteObjectStoreModel,
)
from galaxy.objectstore import UserObjectStoresAppConfig
from galaxy.objectstore.templates import ConfiguredObjectStoreTemplates
from galaxy.objectstore.templates.examples import get_example
from galaxy.objectstore.unittest_utils import app_config
from galaxy.util.config_templates import RawTemplateConfig
from .base import BaseTestCase

SIMPLE_FILE_SOURCE_NAME = "myobjectstore"
SIMPLE_FILE_SOURCE_DESCRIPTION = "a description of my object store"


class Config:
    object_store_templates: Optional[List[RawTemplateConfig]] = None
    object_store_templates_config_file: Optional[str] = None

    def __init__(self, templates: List[RawTemplateConfig]):
        self.object_store_templates = templates


def simple_vault_template(tmp_path):
    return {
        "id": "simple_vault",
        "name": "Simple Vault",
        "description": "This is a simple description",
        "configuration": {
            "type": "disk",
            "files_dir": str(tmp_path / "{{ user.username }}/{{ secrets.sec1 }}"),
        },
        "secrets": {
            "sec1": {
                "help": "This is some simple help.",
            },
        },
    }


def simple_vault_template_with_undefined_jinja_problem(tmp_path):
    return {
        "id": "simple_vault",
        "name": "Simple Vault",
        "description": "This is a simple description",
        "configuration": {
            "type": "disk",
            "files_dir": str(tmp_path / "{{ username }}/{{ secrets.sec1 }}"),  # should be user.username
        },
        "secrets": {
            "sec1": {
                "help": "This is some simple help.",
            },
        },
    }


SIMPLE_VAULT_CREATE_PAYLOAD = CreateInstancePayload(
    name=SIMPLE_FILE_SOURCE_NAME,
    description=SIMPLE_FILE_SOURCE_DESCRIPTION,
    template_id="simple_vault",
    template_version=0,
    variables={},
    secrets={"sec1": "foosec"},
)


def simple_variable_template(tmp_path):
    return {
        "id": "simple_variable",
        "name": "Simple Variable",
        "description": "This is a simple description",
        "configuration": {
            "type": "disk",
            "files_dir": str(tmp_path / "{{ user.username }}/{{ variables.var1 }}"),
        },
        "variables": {
            "var1": {
                "type": "path_component",
                "help": "This is some simple help.",
            },
        },
    }


UPGRADE_EXAMPLE = get_example("testing_multi_version_with_secrets.yml")
UPGRADE_INITIAL_PAYLOAD = CreateInstancePayload(
    name="My Upgradable Disk",
    template_id="secure_disk",
    template_version=0,
    secrets={
        "sec1": "moocow",
    },
    variables={},
)


class TestUserObjectStoreTestCase(BaseTestCase):
    manager: ObjectStoreInstancesManager

    def test_show(self, tmp_path):
        user_object_store = self._init_and_create_simple(tmp_path)
        user_object_store_showed = self.manager.show(self.trans, user_object_store.uuid)
        assert user_object_store_showed
        assert user_object_store_showed.uuid == user_object_store.uuid

    def test_simple_update(self, tmp_path):
        self._init_managers(tmp_path, config_dict=simple_variable_template(tmp_path))
        create_payload = CreateInstancePayload(
            name=SIMPLE_FILE_SOURCE_NAME,
            description=SIMPLE_FILE_SOURCE_DESCRIPTION,
            template_id="simple_variable",
            template_version=0,
            variables={"var1": "originalvarval"},
            secrets={},
        )
        user_object_store = self._create_instance(create_payload)
        assert user_object_store.variables
        assert user_object_store.variables["var1"] == "originalvarval"

        update = UpdateInstancePayload(
            variables={
                "var1": "newval",
            }
        )

        # assert response includes updated variable as well as a fresh show()
        response = self._modify(user_object_store, update)
        assert response.variables
        assert response.variables["var1"] == "newval"

        user_object_store_showed = self.manager.show(self.trans, user_object_store.uuid)
        assert user_object_store_showed.variables
        assert user_object_store_showed.variables["var1"] == "newval"

    def test_update_errors_on_extra_variables(self, tmp_path):
        self._init_managers(tmp_path, config_dict=simple_variable_template(tmp_path))
        create_payload = CreateInstancePayload(
            name=SIMPLE_FILE_SOURCE_NAME,
            description=SIMPLE_FILE_SOURCE_DESCRIPTION,
            template_id="simple_variable",
            template_version=0,
            variables={"var1": "originalvarval"},
            secrets={},
        )
        user_object_store = self._create_instance(create_payload)
        update = UpdateInstancePayload(
            variables={
                "var1": "newval",
                "extra_var": "ghostval",
            }
        )
        self._assert_modify_throws_exception(user_object_store, update, RequestParameterInvalidException)

    def test_update_errors_on_invalid_variable_type(self, tmp_path):
        self._init_managers(tmp_path, config_dict=simple_variable_template(tmp_path))
        create_payload = CreateInstancePayload(
            name=SIMPLE_FILE_SOURCE_NAME,
            description=SIMPLE_FILE_SOURCE_DESCRIPTION,
            template_id="simple_variable",
            template_version=0,
            variables={"var1": "originalvarval"},
            secrets={},
        )
        user_object_store = self._create_instance(create_payload)
        update = UpdateInstancePayload(
            variables={
                "var1": 13,
            }
        )

        self._assert_modify_throws_exception(user_object_store, update, RequestParameterInvalidException)

    def test_hide(self, tmp_path):
        user_object_store = self._init_and_create_simple(tmp_path)

        user_object_store_showed = self.manager.show(self.trans, user_object_store.uuid)
        assert not user_object_store_showed.hidden

        hide = UpdateInstancePayload(hidden=True)
        self._modify(user_object_store, hide)

        user_object_store_showed = self.manager.show(self.trans, user_object_store.uuid)
        assert user_object_store_showed.hidden

    def test_deactivate(self, tmp_path):
        user_object_store = self._init_and_create_simple(tmp_path)

        user_object_store_showed = self.manager.show(self.trans, user_object_store.uuid)
        assert not user_object_store_showed.hidden
        assert user_object_store_showed.active
        assert not user_object_store_showed.purged

        deactivate = UpdateInstancePayload(active=False)
        self._modify(user_object_store, deactivate)

        user_object_store_showed = self.manager.show(self.trans, user_object_store.uuid)
        assert user_object_store_showed.hidden
        assert not user_object_store_showed.active
        assert not user_object_store_showed.purged

    def test_purge(self, tmp_path):
        self._init_managers(tmp_path, simple_vault_template(tmp_path))
        user_object_store = self._create_instance(SIMPLE_VAULT_CREATE_PAYLOAD)
        self._assert_secret_is(user_object_store, "sec1", "foosec")
        self.manager.purge_instance(self.trans, user_object_store.uuid)
        self._assert_secret_absent(user_object_store, "sec1")

    def test_update_secret(self, tmp_path):
        self._init_managers(tmp_path, simple_vault_template(tmp_path))
        user_object_store = self._create_instance(SIMPLE_VAULT_CREATE_PAYLOAD)
        self._assert_secret_is(user_object_store, "sec1", "foosec")
        update = UpdateInstanceSecretPayload(secret_name="sec1", secret_value="newvalue")
        self._modify(user_object_store, update)
        self._assert_secret_is(user_object_store, "sec1", "newvalue")

    def test_cannot_update_invalid_secret(self, tmp_path):
        self._init_managers(tmp_path, simple_vault_template(tmp_path))
        user_object_store = self._create_instance(SIMPLE_VAULT_CREATE_PAYLOAD)
        update = UpdateInstanceSecretPayload(secret_name="undefinedsec", secret_value="newvalue")
        self._assert_modify_throws_exception(user_object_store, update, RequestParameterInvalidException)

    def test_upgrade(self, tmp_path):
        user_object_store = self._init_upgrade_test_case(tmp_path)
        assert "sec1" in user_object_store.secrets
        assert "sec2" not in user_object_store.secrets
        self._assert_secret_is(user_object_store, "sec1", "moocow")
        self._assert_secret_absent(user_object_store, "foobarxyz")
        self._assert_secret_absent(user_object_store, "sec2")
        upgrade_to_1 = UpgradeInstancePayload(
            template_version=1,
            secrets={
                "sec1": "moocow",
                "sec2": "aftersec2",
            },
            variables={},
        )
        user_object_store = self._modify(user_object_store, upgrade_to_1)
        assert "sec1" in user_object_store.secrets
        assert "sec2" in user_object_store.secrets
        self._assert_secret_is(user_object_store, "sec1", "moocow")
        self._assert_secret_is(user_object_store, "sec2", "aftersec2")
        upgrade_to_2 = UpgradeInstancePayload(
            template_version=2,
            secrets={},
            variables={},
        )

        user_object_store = self._modify(user_object_store, upgrade_to_2)
        assert "sec1" not in user_object_store.secrets
        assert "sec2" in user_object_store.secrets
        self._assert_secret_absent(user_object_store, "sec1")
        self._assert_secret_is(user_object_store, "sec2", "aftersec2")

    def test_upgrade_does_not_allow_extra_variables(self, tmp_path):
        user_object_store = self._init_upgrade_test_case(tmp_path)
        upgrade_to_1 = UpgradeInstancePayload(
            template_version=1,
            variables={
                "extra_variable": "moocow",
            },
            secrets={
                "sec1": "moocow",
                "sec2": "aftersec2",
            },
        )

        self._assert_modify_throws_exception(user_object_store, upgrade_to_1, RequestParameterInvalidException)

    def test_upgrade_does_not_allow_extra_secrets(self, tmp_path):
        user_object_store = self._init_upgrade_test_case(tmp_path)
        upgrade_to_1 = UpgradeInstancePayload(
            template_version=1,
            variables={},
            secrets={
                "sec1": "moocow",
                "sec2": "aftersec2",
                "extrasec": "moo345",
            },
        )

        self._assert_modify_throws_exception(user_object_store, upgrade_to_1, RequestParameterInvalidException)

    def test_upgrade_fails_if_new_secrets_absent(self, tmp_path):
        user_object_store = self._init_upgrade_test_case(tmp_path)
        upgrade_to_1 = UpgradeInstancePayload(
            template_version=1,
            variables={},
            secrets={
                "sec1": "moocow",
            },
        )

        self._assert_modify_throws_exception(user_object_store, upgrade_to_1, RequestParameterMissingException)

    def test_status_valid(self, tmp_path):
        self.init_user_in_database()
        self._init_managers(tmp_path, simple_vault_template(tmp_path))
        create_payload = CreateInstancePayload(
            name=SIMPLE_FILE_SOURCE_NAME,
            description=SIMPLE_FILE_SOURCE_DESCRIPTION,
            template_id="simple_vault",
            template_version=0,
            variables={},
            secrets={"sec1": "foosec"},
        )
        status = self.manager.plugin_status(self.trans, create_payload)
        assert status.connection
        assert not status.connection.is_not_ok
        assert not status.template_definition.is_not_ok
        assert status.template_settings
        assert not status.template_settings.is_not_ok

    def test_status_existing_valid(self, tmp_path):
        self.init_user_in_database()
        self._init_managers(tmp_path, simple_vault_template(tmp_path))
        create_payload = CreateInstancePayload(
            name=SIMPLE_FILE_SOURCE_NAME,
            description=SIMPLE_FILE_SOURCE_DESCRIPTION,
            template_id="simple_vault",
            template_version=0,
            variables={},
            secrets={"sec1": "foosec"},
        )
        user_object_store = self._create_instance(create_payload)
        status = self.manager.plugin_status_for_instance(self.trans, user_object_store.uuid)
        assert status.connection
        assert not status.connection.is_not_ok
        assert not status.template_definition.is_not_ok
        assert status.template_settings
        assert not status.template_settings.is_not_ok

    def test_status_invalid_settings_undefined_variable(self, tmp_path):
        self.init_user_in_database()
        self._init_managers(tmp_path, config_dict=simple_vault_template_with_undefined_jinja_problem(tmp_path))
        create_payload = CreateInstancePayload(
            name=SIMPLE_FILE_SOURCE_NAME,
            description=SIMPLE_FILE_SOURCE_DESCRIPTION,
            template_id="simple_vault",
            template_version=0,
            variables={},
            secrets={},
        )
        status = self.manager.plugin_status(self.trans, create_payload)
        assert not status.template_definition.is_not_ok
        assert status.template_settings
        assert status.template_settings.is_not_ok
        assert (
            "Problem with template definition causing invalid settings resolution" in status.template_settings.message
        )
        assert status.connection is None

    def test_status_update_valid(self, tmp_path):
        self._init_managers(tmp_path, config_dict=simple_variable_template(tmp_path))
        create_payload = CreateInstancePayload(
            name=SIMPLE_FILE_SOURCE_NAME,
            description=SIMPLE_FILE_SOURCE_DESCRIPTION,
            template_id="simple_variable",
            template_version=0,
            variables={"var1": "originalvarval"},
            secrets={},
        )
        user_object_store = self._create_instance(create_payload)

        update = TestUpdateInstancePayload(
            variables={
                "var1": "newval",
            }
        )
        status = self.manager.test_modify_instance(self.trans, user_object_store.uuid, update)
        assert not status.template_definition.is_not_ok
        assert status.template_settings
        assert not status.template_settings.is_not_ok
        assert status.connection
        assert not status.connection.is_not_ok

    def test_status_upgrade_valid(self, tmp_path):
        user_object_store = self._init_upgrade_test_case(tmp_path)
        assert "sec1" in user_object_store.secrets
        assert "sec2" not in user_object_store.secrets
        self._assert_secret_is(user_object_store, "sec1", "moocow")
        self._assert_secret_absent(user_object_store, "foobarxyz")
        self._assert_secret_absent(user_object_store, "sec2")
        upgrade_to_1 = TestUpgradeInstancePayload(
            template_version=1,
            secrets={
                "sec1": "moocow",
                "sec2": "aftersec2",
            },
            variables={},
        )
        status = self.manager.test_modify_instance(self.trans, user_object_store.uuid, upgrade_to_1)
        assert not status.template_definition.is_not_ok
        assert status.template_settings
        assert not status.template_settings.is_not_ok
        assert status.connection
        assert not status.connection.is_not_ok

    def test_status_upgrade_invalid(self, tmp_path):
        user_object_store = self._init_invalid_upgrade_test_case(tmp_path)
        upgrade_to_1 = TestUpgradeInstancePayload(
            template_version=1,
            secrets={},
            variables={},
        )
        status = self.manager.test_modify_instance(self.trans, user_object_store.uuid, upgrade_to_1)
        assert not status.template_definition.is_not_ok
        assert status.template_settings
        assert status.template_settings.is_not_ok
        assert (
            "Problem with template definition causing invalid settings resolution" in status.template_settings.message
        )
        assert status.connection is None

    def _init_upgrade_test_case(self, tmp_path) -> UserConcreteObjectStoreModel:
        example_yaml_str = UPGRADE_EXAMPLE
        example_yaml_str.replace("/data", str(tmp_path))
        config = safe_load(example_yaml_str)
        self._init_managers(tmp_path, config)
        user_object_store = self._create_instance(UPGRADE_INITIAL_PAYLOAD)
        return user_object_store

    def _init_invalid_upgrade_test_case(self, tmp_path) -> UserConcreteObjectStoreModel:
        version_0 = simple_vault_template(tmp_path)
        version_0["version"] = 0
        version_1 = simple_vault_template_with_undefined_jinja_problem(tmp_path)
        version_1["version"] = 1
        version_1["id"] = version_0["id"]
        config_dict = [
            version_0,
            version_1,
        ]
        self._init_managers(tmp_path, config_dict=config_dict)
        create_payload = CreateInstancePayload(
            name=SIMPLE_FILE_SOURCE_NAME,
            description=SIMPLE_FILE_SOURCE_DESCRIPTION,
            template_id="simple_vault",
            template_version=0,
            variables={},
            secrets={"sec1": "foosec"},
        )
        user_object_store = self._create_instance(create_payload)
        return user_object_store

    def _read_secret(self, user_object_store: UserConcreteObjectStoreModel, secret_name: str) -> str:
        user_vault = self.trans.user_vault
        config_secret_key = f"object_store_config/{user_object_store.uuid}/{secret_name}"
        return user_vault.read_secret(config_secret_key)

    def _assert_secret_is(self, user_object_store: UserConcreteObjectStoreModel, secret_name: str, expected_value: str):
        assert self._read_secret(user_object_store, secret_name) == expected_value

    def _assert_secret_absent(self, user_object_store: UserConcreteObjectStoreModel, secret_name: str):
        sec_val = self._read_secret(user_object_store, secret_name)
        # deleting vs never inserted...
        assert sec_val in ["", None]

    def _init_and_create_simple(self, tmp_path) -> UserConcreteObjectStoreModel:
        self._init_managers(tmp_path, simple_vault_template(tmp_path))
        create_payload = CreateInstancePayload(
            name=SIMPLE_FILE_SOURCE_NAME,
            description=SIMPLE_FILE_SOURCE_DESCRIPTION,
            template_id="simple_vault",
            template_version=0,
            variables={},
            secrets={"sec1": "foosec"},
        )
        user_object_store = self._create_instance(create_payload)
        return user_object_store

    def _init_managers(self, tmp_path, config_dict=None):
        object_stores_config = app_config(tmp_path)
        self.app[UserObjectStoresAppConfig] = object_stores_config
        self.app.setup_test_vault()
        if isinstance(config_dict, dict):
            templates_config = Config([config_dict])
        else:
            templates_config = Config(config_dict)
        templates = ConfiguredObjectStoreTemplates.from_app_config(
            templates_config,
            vault_configured=True,
        )
        self.app[ConfiguredObjectStoreTemplates] = templates
        manager = self.app[ObjectStoreInstancesManager]
        self.manager = manager

    def _assert_modify_throws_exception(
        self,
        user_object_store: UserConcreteObjectStoreModel,
        modify: ModifyInstancePayload,
        exception_type: Type[Exception],
    ):
        exception_thrown = False
        try:
            self._modify(user_object_store, modify)
        except exception_type:
            exception_thrown = True
        assert exception_thrown

    def _modify(
        self, user_object_store: UserConcreteObjectStoreModel, modify: ModifyInstancePayload
    ) -> UserConcreteObjectStoreModel:
        return self.manager.modify_instance(self.trans, user_object_store.uuid, modify)

    def _create_instance(self, create_payload: CreateInstancePayload) -> UserConcreteObjectStoreModel:
        user_object_store = self.manager.create_instance(self.trans, create_payload)
        return user_object_store
