import logging
import os
from typing import (
    Any,
    cast,
    Dict,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
)

from pydantic import (
    BaseModel,
    UUID4,
)
from typing_extensions import TypedDict

from galaxy.exceptions import (
    InconsistentDatabase,
    ObjectNotFound,
    RequestParameterInvalidException,
    RequestParameterMissingException,
)
from galaxy.managers.context import ProvidesUserContext
from galaxy.model import (
    CONFIGURATION_TEMPLATE_CONFIGURATION_VARIABLES_TYPE,
    HasConfigEnvironment,
    HasConfigSecrets,
    HasConfigTemplate,
    User,
    UsesTemplatesAppConfig,
)
from galaxy.model.scoped_session import galaxy_scoped_session
from galaxy.security.vault import (
    UserVaultWrapper,
    Vault,
)
from galaxy.util import config_templates  # defer get_token_from_refresh_raw access for monkey patching
from galaxy.util.config_templates import (
    EnvironmentDict,
    find_template_by,
    ImplicitConfigurationParameters,
    OAuth2ClientPair,
    OAuth2Configuration,
    PluginAspectStatus,
    secrets_as_dict,
    SecretsDict,
    Template,
    TemplateEnvironmentEntry,
    TemplateEnvironmentSecret,
    TemplateEnvironmentVariable,
    TemplateReference,
    TemplateVariableValueType,
    validate_no_extra_variables_defined,
    validate_specified_datatypes_variables,
)
from galaxy.work.context import SessionRequestContext

log = logging.getLogger(__name__)

SuppliedVariables = Dict[str, TemplateVariableValueType]
SuppliedSecrets = Dict[str, str]


class CreateInstancePayload(BaseModel):
    name: str
    description: Optional[str] = None
    template_id: str
    template_version: int
    variables: SuppliedVariables
    secrets: SuppliedSecrets
    uuid: Optional[UUID4] = None


class UpdateInstancePayload(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    variables: Optional[SuppliedVariables] = None
    hidden: Optional[bool] = None
    active: Optional[bool] = None


class UpdateInstanceSecretPayload(BaseModel):
    secret_name: str
    secret_value: str


class UpgradeInstancePayload(BaseModel):
    template_version: int
    variables: SuppliedVariables
    secrets: SuppliedSecrets


class TestUpdateInstancePayload(BaseModel):
    variables: Optional[SuppliedVariables] = None


class TestUpgradeInstancePayload(BaseModel):
    template_version: int
    variables: SuppliedVariables
    secrets: SuppliedSecrets


class UpgradeTestTarget:
    instance: HasConfigTemplate
    payload: TestUpgradeInstancePayload

    def __init__(self, instance: HasConfigTemplate, payload: TestUpgradeInstancePayload):
        self.instance = instance
        self.payload = payload


class UpdateTestTarget:
    instance: HasConfigTemplate
    payload: TestUpdateInstancePayload

    def __init__(self, instance: HasConfigTemplate, payload: TestUpdateInstancePayload):
        self.instance = instance
        self.payload = payload


class CreateTestTarget:
    payload: CreateInstancePayload
    instance_class: Type[HasConfigSecrets]

    def __init__(self, payload: CreateInstancePayload, instance_class: Type[HasConfigSecrets]):
        self.payload = payload
        self.instance_class = instance_class


ModifyInstancePayload = Union[UpdateInstanceSecretPayload, UpgradeInstancePayload, UpdateInstancePayload]
TestModifyInstancePayload = Union[TestUpgradeInstancePayload, TestUpdateInstancePayload]
CanTestPluginStatus = Union[HasConfigTemplate, CreateTestTarget, UpgradeTestTarget, UpdateTestTarget]


def recover_secrets(
    user_object_store: HasConfigSecrets, vault: Union[UserVaultWrapper, Vault], app_config: UsesTemplatesAppConfig
) -> SecretsDict:
    if isinstance(vault, UserVaultWrapper):
        user_vault = vault
    else:
        user: User = user_object_store.user
        user_vault = UserVaultWrapper(vault, user)
    secrets: SecretsDict = {}
    # now we could recover the list of secrets to fetch from...
    # ones recorded as written in the persisted object, the ones
    # expected in the catalog, or the ones expected in the definition
    # persisted.
    persisted_secret_names = user_object_store.template_secrets or []
    for secret in persisted_secret_names:
        vault_key = user_object_store.vault_key(secret, app_config)
        secret_value = user_vault.read_secret(vault_key)
        if secret_value is not None:
            secrets[secret] = secret_value
    return secrets


class TemplateParameters(TypedDict):
    secrets: SuppliedSecrets
    variables: SuppliedVariables
    environment: EnvironmentDict
    user_details: Dict[str, Any]
    implicit: Optional[ImplicitConfigurationParameters]


class TemplateServerConfiguration:
    """Extra configuration relevant to a given template.

    For state defined in the server but not defined in the template JSON/YAML directly.
    Currently this only contains optional oauth2 client credentials and oauth2 configuration
    information (provider URLs and provider specific configuration for the oauth2 flow).
    """

    oauth2_client_pair: Optional[OAuth2ClientPair]
    oauth2_configuration: Optional[OAuth2Configuration]

    def __init__(
        self,
        oauth2_client_pair: Optional[OAuth2ClientPair] = None,
        oauth2_configuration: Optional[OAuth2Configuration] = None,
        oauth2_scope: Optional[str] = None,
    ):
        self.oauth2_client_pair = oauth2_client_pair
        self.oauth2_configuration = oauth2_configuration
        self.oauth2_scope = oauth2_scope

    @property
    def uses_oauth2(self):
        return self.oauth2_configuration is not None


def prepare_template_parameters_for_testing(
    trans: ProvidesUserContext,
    template: Template,
    template_server_configuration: TemplateServerConfiguration,
    target: CanTestPluginStatus,
    vault: Vault,
    app_config: UsesTemplatesAppConfig,
) -> TemplateParameters:
    secrets = _secrets_for_plugin_status_test(target, trans.user_vault, app_config)
    variables = _variables_for_plugin_status_test(target)
    environment = prepare_environment_from_root(template.environment, vault, app_config)
    user_details = trans.user.config_template_details()
    implicit = implicit_parameters_for_testing(
        trans,
        template_server_configuration,
        target,
        app_config,
    )
    return TemplateParameters(
        {
            "secrets": secrets,
            "variables": variables,
            "environment": environment,
            "user_details": user_details,
            "implicit": implicit,
        }
    )


def _variables_for_plugin_status_test(target: CanTestPluginStatus) -> SuppliedVariables:
    if isinstance(target, CreateTestTarget):
        return target.payload.variables
    elif isinstance(target, UpgradeTestTarget) or isinstance(target, UpdateTestTarget):
        if target.instance.template_variables:
            variables = target.instance.template_variables.copy()
        else:
            variables = {}
        new_variables = target.payload.variables or {}
        for new_variable in new_variables:
            variables[new_variable] = new_variables[new_variable]
        return new_variables
    else:
        return target.template_variables or {}


def _secrets_for_plugin_status_test(
    target: CanTestPluginStatus, user_vault: UserVaultWrapper, app_config: UsesTemplatesAppConfig
) -> SecretsDict:
    if isinstance(target, CreateTestTarget):
        payload = target.payload
        secrets = payload.secrets.copy()
        return secrets
    elif isinstance(target, UpgradeTestTarget):
        secrets = recover_secrets(target.instance, user_vault, app_config)
        new_secrets = target.payload.secrets or {}
        for new_secret in new_secrets:
            secrets[new_secret] = new_secrets[new_secret]
        return secrets
    elif isinstance(target, UpdateTestTarget):
        secrets = recover_secrets(target.instance, user_vault, app_config)
        return secrets
    else:
        secrets = recover_secrets(target, user_vault, app_config)
        return secrets


def to_template_reference(persisted_instance: HasConfigTemplate) -> TemplateReference:
    # for mypy convert Mapped[X] -> X
    return cast(TemplateReference, persisted_instance)


def prepare_environment(
    configuration_template: HasConfigEnvironment, vault: Vault, app_config: UsesTemplatesAppConfig
) -> EnvironmentDict:
    return prepare_environment_from_root(configuration_template.template_environment.root, vault, app_config)


def prepare_environment_from_root(
    root: Optional[List[TemplateEnvironmentEntry]], vault: Vault, app_config: UsesTemplatesAppConfig
) -> EnvironmentDict:
    environment: EnvironmentDict = {}
    for environment_entry in root or []:
        e_type = environment_entry.type
        e_name = environment_entry.name
        if e_type == "secret":
            template_secret = cast(TemplateEnvironmentSecret, environment_entry)
            secret_value = vault.read_secret(template_secret.vault_key) or template_secret.default
            if secret_value:
                environment[e_name] = secret_value
        elif e_type == "variable":
            template_variable = cast(TemplateEnvironmentVariable, environment_entry)
            variable_value = os.environ.get(template_variable.variable)
            if variable_value is None:
                variable_value = template_variable.default
            if variable_value:
                environment[e_name] = variable_value
        else:
            raise Exception(f"Unknown environment entry type detected [{e_type}]")

    return environment


def update_template_instance(
    sa_session: galaxy_scoped_session,
    template_instance: HasConfigTemplate,
    payload: UpdateInstancePayload,
    template: Template,
):
    validate_specified_datatypes_variables(payload.variables or {}, template)
    validate_no_extra_variables_defined(payload.variables or {}, template)
    if payload.name is not None:
        template_instance.name = payload.name
    if payload.description is not None:
        template_instance.description = payload.description
    if payload.variables is not None:
        actual_variables = updated_template_variables(payload.variables, template_instance, template)
        template_instance.template_variables = actual_variables
    if payload.hidden is not None:
        template_instance.hidden = payload.hidden
    if payload.active is not None:
        if payload.active:
            # unhide and activate
            template_instance.active = True
            template_instance.hidden = False
        else:
            # deactivate and hide
            template_instance.active = False
            template_instance.hidden = True
    save_template_instance(sa_session, template_instance)
    return template_instance


def updated_template_variables(
    supplied_variables: SuppliedVariables, template_instance: HasConfigTemplate, template: Template
):
    old_variables = template_instance.template_variables or {}
    updated_variables: CONFIGURATION_TEMPLATE_CONFIGURATION_VARIABLES_TYPE = {}
    for variable in template.variables or []:
        variable_name = variable.name
        old_value = old_variables.get(variable_name)
        updated_value = supplied_variables.get(variable_name, old_value)
        if updated_value:
            updated_variables[variable_name] = updated_value
    return updated_variables


def purge_template_instance(
    trans: ProvidesUserContext, template_instance: HasConfigTemplate, app_config: UsesTemplatesAppConfig
):
    user_vault = trans.user_vault
    user_vault_key_prefix = template_instance.vault_id_prefix(app_config)
    # it would be nice to just list the secrets but none of them do that... so catch NotImplemented
    # and try with the secrets as we have record in the database of recording them.
    try:
        for secret in user_vault.list_secrets(user_vault_key_prefix):
            user_vault.delete_secret(secret)
    except NotImplementedError:
        for secret in template_instance.template_secrets or []:
            user_vault.delete_secret(f"{user_vault_key_prefix}/{secret}")
    template_instance.active = False
    template_instance.purged = True
    save_template_instance(trans.sa_session, template_instance)


def update_instance_secret(
    trans: ProvidesUserContext,
    template_instance: HasConfigTemplate,
    template: Template,
    payload: UpdateInstanceSecretPayload,
    app_config: UsesTemplatesAppConfig,
):
    template_secrets = secrets_as_dict(template.secrets or [])
    secret_name = payload.secret_name
    if secret_name not in template_secrets:
        raise RequestParameterInvalidException(f"Configuration template does not specify a secret named {secret_name}")

    user_vault = trans.user_vault
    key = template_instance.vault_key(payload.secret_name, app_config)
    user_vault.write_secret(key, payload.secret_value)


def upgrade_secrets(
    trans: ProvidesUserContext,
    template_instance: HasConfigTemplate,
    target_template: Template,
    payload: UpgradeInstancePayload,
    app_config: UsesTemplatesAppConfig,
):
    recorded_secrets = template_instance.template_secrets or []

    old_secrets = template_instance.template_secrets or []
    new_secrets = payload.secrets

    user_vault = trans.user_vault
    upgraded_template_secrets = []
    for secret in target_template.secrets or []:
        secret_name = secret.name
        upgraded_template_secrets.append(secret_name)
        if secret_name not in new_secrets and secret_name not in old_secrets:
            raise RequestParameterMissingException(f"secret {secret_name} not set in supplied request")
        if secret_name not in new_secrets:
            # keep old value
            continue

        secret_value = new_secrets[secret_name]
        key = template_instance.vault_key(secret_name, app_config)
        user_vault.write_secret(key, secret_value)
        if secret_name not in recorded_secrets:
            recorded_secrets.append(secret_name)

    secrets_to_delete: List[str] = []
    for recorded_secret in recorded_secrets:
        if recorded_secret not in upgraded_template_secrets:
            key = template_instance.vault_key(recorded_secret, app_config)
            log.info(f"deleting {key} from user vault")
            user_vault.delete_secret(key)
            secrets_to_delete.append(recorded_secret)

    for secret_to_delete in secrets_to_delete:
        recorded_secrets.remove(secret_to_delete)

    template_instance.template_secrets = recorded_secrets


def save_template_instance(sa_session: galaxy_scoped_session, template_instance: HasConfigTemplate):
    sa_session.add(template_instance)
    sa_session.flush([template_instance])
    sa_session.commit()


T = TypeVar("T", bound=Template, covariant=True)


def sort_templates(config, catalog: List[T], instance: HasConfigTemplate) -> List[T]:
    configured_template: Optional[T] = None
    try:
        configured_template = find_template_by(
            catalog, instance.template_id, instance.template_version, "config template"
        )
    except ObjectNotFound:
        if config.user_config_templates_use_saved_configuration == "never":
            raise
    stored_template: T = instance.template
    if config.user_config_templates_use_saved_configuration == "preferred" and configured_template:
        templates = [stored_template, configured_template]
    elif configured_template:
        templates = [configured_template, stored_template]
    else:
        templates = [stored_template]
    return templates


def implicit_parameters_for_testing(
    trans: ProvidesUserContext,
    template_server_configuration: TemplateServerConfiguration,
    target: CanTestPluginStatus,
    app_config: UsesTemplatesAppConfig,
) -> Optional[ImplicitConfigurationParameters]:
    implicit: ImplicitConfigurationParameters = {}
    if template_server_configuration.oauth2_configuration:
        refresh_token_key = None
        oauth2_refresh_token = None
        if isinstance(target, CreateTestTarget):
            if target.payload.uuid:
                refresh_token_key = target.instance_class.vault_key_from_uuid(
                    target.payload.uuid, "_oauth2_refresh_token", app_config
                )
        else:
            if isinstance(target, (UpgradeTestTarget, UpdateTestTarget)):
                instance = target.instance
            else:
                instance = target
            refresh_token_key = instance.vault_key_from_uuid(instance.uuid, "_oauth2_refresh_token", app_config)
        oauth2_refresh_token = trans.user_vault.read_secret(refresh_token_key)
        if not oauth2_refresh_token:
            raise InconsistentDatabase(
                f"Failed to recover oauth2 refresh token from vault at location {refresh_token_key}, Galaxy is in an inconsistent state and probably requires admin intervention"
            )
        _inject_oauth2_access_token(implicit, oauth2_refresh_token, template_server_configuration)

    return implicit


def implicit_parameters_for_instance(
    user_instance: HasConfigSecrets,
    template_server_configuration: TemplateServerConfiguration,
    vault: Vault,
    app_config: UsesTemplatesAppConfig,
) -> ImplicitConfigurationParameters:
    implicit: ImplicitConfigurationParameters = {}

    if template_server_configuration.oauth2_configuration:
        refresh_token_key = user_instance.__class__.vault_key_from_uuid(
            str(user_instance.uuid), "_oauth2_refresh_token", app_config
        )
        user_vault = UserVaultWrapper(vault, user_instance.user)
        oauth2_refresh_token = user_vault.read_secret(refresh_token_key)
        if not oauth2_refresh_token:
            raise Exception("null refresh token key read from user vault")
        _inject_oauth2_access_token(implicit, oauth2_refresh_token, template_server_configuration)

    return implicit


def _inject_oauth2_access_token(
    implicit: ImplicitConfigurationParameters,
    oauth2_refresh_token: str,
    template_server_configuration: TemplateServerConfiguration,
) -> None:
    oauth2_client_pair = template_server_configuration.oauth2_client_pair
    oauth2_configuration = template_server_configuration.oauth2_configuration
    assert oauth2_client_pair
    assert oauth2_configuration
    response = config_templates.get_token_from_refresh_raw(
        oauth2_refresh_token, oauth2_client_pair, oauth2_configuration
    )
    response.raise_for_status()
    implicit["oauth2_access_token"] = response.json()["access_token"]


def oauth2_refresh_token_status(
    template_server_configuration: TemplateServerConfiguration, exception: Optional[Exception]
) -> Optional[PluginAspectStatus]:
    if not template_server_configuration.uses_oauth2:
        # no oauth enabled, don't report a status associated with
        return None
    else:
        if not exception:
            return PluginAspectStatus(
                state="ok", message="OAuth2 secret refresh token generated an access token for this resource"
            )
        else:
            return PluginAspectStatus(
                state="not_ok",
                message=f"OAuth2 secret refresh token failed to generate an access token for this resource: {exception}",
            )


def oauth2_redirect_uri(trans: SessionRequestContext) -> str:
    galaxy_root = trans.request.url_path
    redirect_uri = f"{galaxy_root}oauth2_callback"
    return redirect_uri
