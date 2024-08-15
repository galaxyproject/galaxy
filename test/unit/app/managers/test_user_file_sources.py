import os
from typing import (
    cast,
    List,
    Optional,
    Type,
)

from yaml import safe_load

from galaxy.exceptions import (
    RequestParameterInvalidException,
    RequestParameterMissingException,
)
from galaxy.files import FileSourcesUserContext
from galaxy.files.templates import ConfiguredFileSourceTemplates
from galaxy.files.templates.examples import get_example
from galaxy.managers.file_source_instances import (
    CreateInstancePayload,
    FileSourceInstancesManager,
    ModifyInstancePayload,
    UpdateInstancePayload,
    UpdateInstanceSecretPayload,
    UpgradeInstancePayload,
    USER_FILE_SOURCES_SCHEME,
    UserDefinedFileSourcesConfig,
    UserDefinedFileSourcesImpl,
    UserFileSourceModel,
)
from galaxy.util.config_templates import RawTemplateConfig
from .base import BaseTestCase

SIMPLE_FILE_SOURCE_NAME = "myfilesource"
SIMPLE_FILE_SOURCE_DESCRIPTION = "a description of my file source"


class Config:
    file_source_templates: Optional[List[RawTemplateConfig]] = None
    file_source_templates_config_file: Optional[str] = None

    def __init__(self, templates: List[RawTemplateConfig]):
        self.file_source_templates = templates


def home_directory_template(tmp_path):
    return {
        "id": "home_directory",
        "name": "Home Directory",
        "description": "Your Home Directory on this System",
        "configuration": {
            "type": "posix",
            "root": str(tmp_path / "{{ user.username }}"),
            "writable": True,
        },
    }


def invalid_home_directory_template(tmp_path):
    # create a jinja runtime problem - so the template loads but the expansion fails.
    return {
        "id": "invalid_home_directory",
        "name": "Home Directory",
        "description": "Your Home Directory on this System",
        "configuration": {
            "type": "posix",
            "root": str(tmp_path / "{{ username }}"),  # should be user.username
            "writable": True,
        },
    }


def invalid_home_directory_template_type_error(tmp_path):
    # create a runtime problem - so the template loads but the expansion fails
    # because pydantic error related to typing
    return {
        "id": "invalid_home_directory",
        "name": "Home Directory",
        "description": "Your Home Directory on this System",
        "configuration": {
            "type": "posix",
            "root": str(tmp_path / "{{ user.username }}"),
            "writable": "{{ username }}",
        },
    }


def secret_directory_template(tmp_path):
    return {
        "id": "admin_secret_directory",
        "name": "Secret Directory",
        "description": "An directory constructed from admin secrets.",
        "configuration": {
            "type": "posix",
            "root": str(tmp_path / "{{ environment.var }}/{{ environment.sec }}"),
            "writable": True,
        },
        "environment": {
            "var": {
                "type": "variable",
                "variable": "GX_UNIT_TEST_SECRET_HOME_VAR",
            },
            "sec": {
                "type": "secret",
                "vault_key": "secret_directory_file_source/my_secret",
            },
        },
    }


def secret_directory_template_with_defaults(tmp_path):
    return {
        "id": "admin_secret_directory",
        "name": "Secret Directory",
        "description": "An directory constructed from admin secrets.",
        "configuration": {
            "type": "posix",
            "root": str(tmp_path / "{{ environment.var }}/{{ environment.sec }}"),
            "writable": True,
        },
        "environment": {
            "var": {
                "type": "variable",
                "variable": "GX_UNIT_TEST_SECRET_HOME_VAR_2",
                "default": "fine_default_var",
            },
            "sec": {
                "type": "secret",
                "vault_key": "secret_directory_file_source/my_secret_2",
                "default": "fine_default_sec",
            },
        },
    }


def simple_variable_template(tmp_path):
    return {
        "id": "simple_variable",
        "name": "Simple Variable Driven Example",
        "description": "This is a simple description",
        "configuration": {
            "type": "posix",
            "root": str(tmp_path / "{{ user.username }}/{{ variables.var1 }}"),
        },
        "variables": {
            "var1": {
                "type": "string",
                "help": "This is some simple help.",
            },
        },
    }


def simple_vault_template(tmp_path):
    return {
        "id": "simple_vault",
        "name": "Simple Vault",
        "description": "This is a simple description",
        "configuration": {
            "type": "posix",
            "root": str(tmp_path / "{{ user.username }}/{{ secrets.sec1 }}"),
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


class TestFileSourcesTestCase(BaseTestCase):
    manager: FileSourceInstancesManager
    file_sources: UserDefinedFileSourcesImpl

    def test_create_posix(self, tmp_path):
        self._init_managers(tmp_path)
        user_file_source = self._create_user_file_source()
        uri_root = user_file_source.uri_root
        match = self.file_sources.find_best_match(uri_root)
        assert match
        assert match.score == len(uri_root)
        file_source = match.file_source
        assert file_source
        assert file_source.label == SIMPLE_FILE_SOURCE_NAME
        assert file_source.doc == SIMPLE_FILE_SOURCE_DESCRIPTION
        assert file_source.get_scheme() == USER_FILE_SOURCES_SCHEME
        assert file_source.get_uri_root() == uri_root

    def test_io(self, tmp_path):
        self._init_managers(tmp_path)
        user_file_source = self._create_user_file_source()
        uri_root = user_file_source.uri_root
        match = self.file_sources.find_best_match(uri_root)
        assert match
        file_source = match.file_source

        temp_file = tmp_path / "tmp_file"
        temp_file.write_text("Moo Cow", "utf-8")
        file_source.write_from("/moo", str(temp_file))
        target = tmp_path / "round_trip"
        file_source.realize_to("/moo", target)
        assert target.read_text("utf-8") == "Moo Cow"

    def test_to_dict_filters_hidden(self, tmp_path):
        self.init_user_in_database()
        self._init_managers(tmp_path)
        user_file_source = self._create_user_file_source()
        assert user_file_source.uri_root in self._uri_roots()
        hide = UpdateInstancePayload(hidden=True)
        self._modify(user_file_source, hide)
        assert user_file_source.uri_root not in self._uri_roots()

    def test_find_best_match_not_filters_hidden(self, tmp_path):
        self.init_user_in_database()
        self._init_managers(tmp_path)
        user_file_source = self._create_user_file_source()
        hide = UpdateInstancePayload(hidden=True)
        self._modify(user_file_source, hide)
        match = self.file_sources.find_best_match(user_file_source.uri_root)
        assert match

    def test_find_best_match_filters_deactivated(self, tmp_path):
        self.init_user_in_database()
        self._init_managers(tmp_path)
        user_file_source = self._create_user_file_source()
        deactivate = UpdateInstancePayload(active=False)
        self._modify(user_file_source, deactivate)
        match = self.file_sources.find_best_match(user_file_source.uri_root)
        assert not match

    def _uri_roots(self) -> List[str]:
        sources_as_dicts = self.file_sources.user_file_sources_to_dicts(
            False,
            cast(FileSourcesUserContext, self.trans),
        )
        return [s["uri_root"] for s in sources_as_dicts]

    def test_environment_injection(self, tmp_path):
        self._init_managers(tmp_path, config_dict=secret_directory_template(tmp_path))

        expected_target = tmp_path / "cool_var" / "cool_sec"
        assert not expected_target.exists()

        os.environ["GX_UNIT_TEST_SECRET_HOME_VAR"] = "cool_var"
        self.app.vault.write_secret("secret_directory_file_source/my_secret", "cool_sec")

        user_file_source = self._create_user_file_source("admin_secret_directory")
        uri_root = user_file_source.uri_root
        match = self.file_sources.find_best_match(uri_root)
        assert match
        file_source = match.file_source

        temp_file = tmp_path / "tmp_file"
        temp_file.write_text("Moo Cow", "utf-8")
        file_source.write_from("/moo", str(temp_file))
        assert expected_target.exists()
        assert (expected_target / "moo").exists()

    def test_environment_defaults(self, tmp_path):
        self._init_managers(tmp_path, config_dict=secret_directory_template_with_defaults(tmp_path))

        expected_target = tmp_path / "fine_default_var" / "fine_default_sec"
        assert not expected_target.exists()

        user_file_source = self._create_user_file_source("admin_secret_directory")
        uri_root = user_file_source.uri_root
        match = self.file_sources.find_best_match(uri_root)
        assert match
        file_source = match.file_source

        temp_file = tmp_path / "tmp_file"
        temp_file.write_text("Moo Cow", "utf-8")
        file_source.write_from("/moo", str(temp_file))
        assert expected_target.exists()
        assert (expected_target / "moo").exists()

    def test_show(self, tmp_path):
        self._init_managers(tmp_path)
        user_file_source = self._create_user_file_source()
        user_file_source_showed = self.manager.show(self.trans, user_file_source.uuid)
        assert user_file_source_showed
        assert user_file_source_showed.uuid == user_file_source.uuid

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
        user_file_source = self._create_instance(create_payload)
        assert user_file_source.variables
        assert user_file_source.variables["var1"] == "originalvarval"

        update = UpdateInstancePayload(
            variables={
                "var1": "newval",
            }
        )

        # assert response includes updated variable as well as a fresh show()
        response = self._modify(user_file_source, update)
        assert response.variables
        assert response.variables["var1"] == "newval"

        user_file_source_showed = self.manager.show(self.trans, user_file_source.uuid)
        assert user_file_source_showed.variables
        assert user_file_source_showed.variables["var1"] == "newval"

    def test_hide(self, tmp_path):
        user_file_source = self._init_and_create_simple(tmp_path)

        user_file_source_showed = self.manager.show(self.trans, user_file_source.uuid)
        assert not user_file_source_showed.hidden

        hide = UpdateInstancePayload(hidden=True)
        self._modify(user_file_source, hide)

        user_file_source_showed = self.manager.show(self.trans, user_file_source.uuid)
        assert user_file_source_showed.hidden

    def test_deactivate(self, tmp_path):
        user_file_source = self._init_and_create_simple(tmp_path)

        user_file_source_showed = self.manager.show(self.trans, user_file_source.uuid)
        assert not user_file_source_showed.hidden
        assert user_file_source_showed.active
        assert not user_file_source_showed.purged

        deactivate = UpdateInstancePayload(active=False)
        self._modify(user_file_source, deactivate)

        user_file_source_showed = self.manager.show(self.trans, user_file_source.uuid)
        assert user_file_source_showed.hidden
        assert not user_file_source_showed.active
        assert not user_file_source_showed.purged

    def test_purge(self, tmp_path):
        self._init_managers(tmp_path, simple_vault_template(tmp_path))
        user_file_source = self._create_instance(SIMPLE_VAULT_CREATE_PAYLOAD)
        assert "sec1" in user_file_source.secrets
        self._assert_secret_is(user_file_source, "sec1", "foosec")
        self.manager.purge_instance(self.trans, user_file_source.uuid)
        self._assert_secret_absent(user_file_source, "sec1")

    def test_update_secret(self, tmp_path):
        self._init_managers(tmp_path, simple_vault_template(tmp_path))
        user_file_source = self._create_instance(SIMPLE_VAULT_CREATE_PAYLOAD)
        self._assert_secret_is(user_file_source, "sec1", "foosec")
        update = UpdateInstanceSecretPayload(secret_name="sec1", secret_value="newvalue")
        self._modify(user_file_source, update)
        self._assert_secret_is(user_file_source, "sec1", "newvalue")

    def test_cannot_update_invalid_secret(self, tmp_path):
        self._init_managers(tmp_path, simple_vault_template(tmp_path))
        user_file_source = self._create_instance(SIMPLE_VAULT_CREATE_PAYLOAD)
        update = UpdateInstanceSecretPayload(secret_name="undefinedsec", secret_value="newvalue")
        self._assert_modify_throws_exception(user_file_source, update, RequestParameterInvalidException)

    def test_upgrade(self, tmp_path):
        user_file_source = self._init_upgrade_test_case(tmp_path)
        assert "sec1" in user_file_source.secrets
        assert "sec2" not in user_file_source.secrets
        self._assert_secret_is(user_file_source, "sec1", "moocow")
        self._assert_secret_absent(user_file_source, "foobarxyz")
        self._assert_secret_absent(user_file_source, "sec2")
        upgrade_to_1 = UpgradeInstancePayload(
            template_version=1,
            secrets={
                "sec1": "moocow",
                "sec2": "aftersec2",
            },
            variables={},
        )
        user_file_source = self._modify(user_file_source, upgrade_to_1)
        assert "sec1" in user_file_source.secrets
        assert "sec2" in user_file_source.secrets
        self._assert_secret_is(user_file_source, "sec1", "moocow")
        self._assert_secret_is(user_file_source, "sec2", "aftersec2")
        upgrade_to_2 = UpgradeInstancePayload(
            template_version=2,
            secrets={},
            variables={},
        )

        user_file_source = self._modify(user_file_source, upgrade_to_2)
        assert "sec1" not in user_file_source.secrets
        assert "sec2" in user_file_source.secrets
        self._assert_secret_absent(user_file_source, "sec1")
        self._assert_secret_is(user_file_source, "sec2", "aftersec2")

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
        self._init_managers(tmp_path)
        (tmp_path / self.trans.user.username).mkdir()
        create_payload = CreateInstancePayload(
            name=SIMPLE_FILE_SOURCE_NAME,
            description=SIMPLE_FILE_SOURCE_DESCRIPTION,
            template_id="home_directory",
            template_version=0,
            variables={},
            secrets={},
        )
        status = self.manager.plugin_status(self.trans, create_payload)
        assert status.connection
        assert not status.connection.is_not_ok
        assert not status.template_definition.is_not_ok
        assert status.template_settings
        assert not status.template_settings.is_not_ok

    def test_status_invalid_connection(self, tmp_path):
        self.init_user_in_database()
        self._init_managers(tmp_path)
        # We don't make the directory like above so it doesn't exist
        # (tmp_path / self.trans.user.username).mkdir()
        create_payload = CreateInstancePayload(
            name=SIMPLE_FILE_SOURCE_NAME,
            description=SIMPLE_FILE_SOURCE_DESCRIPTION,
            template_id="home_directory",
            template_version=0,
            variables={},
            secrets={},
        )
        status = self.manager.plugin_status(self.trans, create_payload)
        assert not status.template_definition.is_not_ok
        assert status.template_settings
        assert not status.template_settings.is_not_ok
        # Language is weird with the local disk stuff but the "connection"
        # is invalid. Do we search for better language or loosen the framework
        # structure in someway and push these specific checks into the plugins?
        assert status.connection
        assert status.connection.is_not_ok

    def test_status_invalid_settings_undefined_variable(self, tmp_path):
        self.init_user_in_database()
        self._init_managers(tmp_path, config_dict=invalid_home_directory_template(tmp_path))
        create_payload = CreateInstancePayload(
            name=SIMPLE_FILE_SOURCE_NAME,
            description=SIMPLE_FILE_SOURCE_DESCRIPTION,
            template_id="invalid_home_directory",
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

    def test_status_invalid_settings_configuration_validation(self, tmp_path):
        self.init_user_in_database()
        self._init_managers(tmp_path, config_dict=invalid_home_directory_template_type_error(tmp_path))
        create_payload = CreateInstancePayload(
            name=SIMPLE_FILE_SOURCE_NAME,
            description=SIMPLE_FILE_SOURCE_DESCRIPTION,
            template_id="invalid_home_directory",
            template_version=0,
            variables={},
            secrets={},
        )
        status = self.manager.plugin_status(self.trans, create_payload)
        assert not status.template_definition.is_not_ok
        assert status.template_settings
        assert status.template_settings.is_not_ok
        assert "Input should be a valid boolean" in status.template_settings.message
        assert status.connection is None

    def _init_upgrade_test_case(self, tmp_path) -> UserFileSourceModel:
        example_yaml_str = UPGRADE_EXAMPLE
        example_yaml_str.replace("/data", str(tmp_path))
        config = safe_load(example_yaml_str)
        self._init_managers(tmp_path, config)
        user_file_source = self._create_instance(UPGRADE_INITIAL_PAYLOAD)
        return user_file_source

    def _init_and_create_simple(self, tmp_path) -> UserFileSourceModel:
        self._init_managers(tmp_path)
        user_file_source = self._create_user_file_source()
        return user_file_source

    def _create_user_file_source(self, template_id="home_directory") -> UserFileSourceModel:
        create_payload = CreateInstancePayload(
            name=SIMPLE_FILE_SOURCE_NAME,
            description=SIMPLE_FILE_SOURCE_DESCRIPTION,
            template_id=template_id,
            template_version=0,
            variables={},
            secrets={},
        )
        return self._create_instance(create_payload)

    def _read_secret(self, user_file_source: UserFileSourceModel, secret_name: str) -> str:
        user_vault = self.trans.user_vault
        config_secret_key = f"file_source_config/{user_file_source.uuid}/{secret_name}"
        return user_vault.read_secret(config_secret_key)

    def _assert_secret_is(self, user_file_source: UserFileSourceModel, secret_name: str, expected_value: str):
        assert self._read_secret(user_file_source, secret_name) == expected_value

    def _assert_secret_absent(self, user_file_source: UserFileSourceModel, secret_name: str):
        sec_val = self._read_secret(user_file_source, secret_name)
        # deleting vs never inserted...
        assert sec_val in ["", None]

    def _assert_modify_throws_exception(
        self, user_file_source: UserFileSourceModel, modify: ModifyInstancePayload, exception_type: Type
    ):
        exception_thrown = False
        try:
            self._modify(user_file_source, modify)
        except exception_type:
            exception_thrown = True
        assert exception_thrown

    def _modify(self, user_file_source: UserFileSourceModel, modify: ModifyInstancePayload) -> UserFileSourceModel:
        return self.manager.modify_instance(self.trans, user_file_source.uuid, modify)

    def _create_instance(self, create_payload: CreateInstancePayload) -> UserFileSourceModel:
        user_file_source = self.manager.create_instance(self.trans, create_payload)
        return user_file_source

    def _init_managers(self, tmp_path, config_dict=None):
        file_sources_config = UserDefinedFileSourcesConfig(
            user_config_templates_index_by="uuid",
            user_config_templates_use_saved_configuration="fallback",
        )
        self.app[UserDefinedFileSourcesConfig] = file_sources_config
        self.app.setup_test_vault()
        if config_dict is None:
            config_dict = home_directory_template(tmp_path)
        if isinstance(config_dict, dict):
            templates_config = Config([config_dict])
        else:
            templates_config = Config(config_dict)
        templates = ConfiguredFileSourceTemplates.from_app_config(
            templates_config,
            vault_configured=True,
        )
        self.app[ConfiguredFileSourceTemplates] = templates
        file_sources = self.app[UserDefinedFileSourcesImpl]
        manager = self.app[FileSourceInstancesManager]
        self.file_sources = file_sources
        self.manager = manager
