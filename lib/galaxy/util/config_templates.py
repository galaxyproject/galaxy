"""Utilities for defining user configuration bits from admin templates.

This is capturing code shared by file source templates and object store templates.
"""

import logging
import os
from typing import (
    Any,
    cast,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
)
from urllib.parse import urlencode

import requests
import yaml
from boltons.iterutils import remap
from pydantic import (
    BaseModel,
    ConfigDict,
    RootModel,
    ValidationError,
)
from typing_extensions import (
    Literal,
    NotRequired,
    Protocol,
    TypedDict,
)

try:
    from jinja2 import (
        StrictUndefined,
        UndefinedError,
    )
    from jinja2.nativetypes import NativeEnvironment
except ImportError:
    NativeEnvironment = None  # type:ignore[assignment, misc, unused-ignore]
    StrictUndefined = None  # type:ignore[assignment, misc, unused-ignore]
    UndefinedError = None  # type:ignore[assignment, misc, unused-ignore]

from galaxy.exceptions import (
    ObjectNotFound,
    RequestParameterInvalidException,
    RequestParameterMissingException,
)
from galaxy.util import asbool

log = logging.getLogger(__name__)

TemplateVariableType = Literal["string", "path_component", "boolean", "integer"]
TemplateVariableValueType = Union[str, bool, int]
TemplateExpansion = str
MarkdownContent = str
RawTemplateConfig = Dict[str, Any]
UserDetailsDict = Dict[str, Any]
VariablesDict = Dict[str, TemplateVariableValueType]
SecretsDict = Dict[str, str]
EnvironmentDict = Dict[str, str]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", coerce_numbers_to_str=True)


class BaseTemplateVariable(StrictModel):
    name: str
    label: Optional[str] = None
    help: Optional[MarkdownContent]


class TemplateVariableString(BaseTemplateVariable):
    type: Literal["string"]
    default: str = ""
    # add non-empty validation?


class TemplateVariableInteger(BaseTemplateVariable):
    type: Literal["integer"]
    default: int = 0
    # add min/max


class TemplateVariablePathComponent(BaseTemplateVariable):
    type: Literal["path_component"]
    default: Optional[str] = None


class TemplateVariableBoolean(BaseTemplateVariable):
    type: Literal["boolean"]
    default: bool = False


TemplateVariable = Union[
    TemplateVariableString, TemplateVariableInteger, TemplateVariablePathComponent, TemplateVariableBoolean
]


class TemplateSecret(StrictModel):
    name: str
    label: Optional[str] = None
    help: Optional[MarkdownContent]


class TemplateEnvironmentSecret(StrictModel):
    type: Literal["secret"]
    name: str
    vault_key: str
    default: Optional[str] = None


class TemplateEnvironmentVariable(StrictModel):
    type: Literal["variable"]
    name: str
    variable: str
    default: Optional[str] = None


TemplateEnvironmentEntry = Union[TemplateEnvironmentVariable, TemplateEnvironmentSecret]
TemplateEnvironment = RootModel[List[TemplateEnvironmentEntry]]


def _ensure_path_component(input: Any):
    input_as_string = str(input)
    if not acts_as_simple_path_component(input_as_string):
        raise Exception("Path manipulation detected, failing evaluation")
    return input


# NativeEnvironment preserves Python types
def _environment(template_start: str, template_end: str) -> NativeEnvironment:
    env = NativeEnvironment(
        variable_start_string=template_start,
        variable_end_string=template_end,
        undefined=StrictUndefined,
    )
    env.filters["ensure_path_component"] = _ensure_path_component
    env.filters["asbool"] = asbool
    return env


class TemplateConfiguration(Protocol):

    def model_dump(self) -> Dict[str, Any]:
        """Implements a pydantic model dump to build simple JSON dictionary."""

    @property
    def template_start(self) -> Optional[str]:
        """Set a custom variable start for Jinja variable substitution.

        https://stackoverflow.com/questions/12083319/add-custom-tokens-in-jinja2-e-g-somevar
        """

    @property
    def template_end(self) -> Optional[str]:
        """Set a custom variable end for Jinja variable substitution.

        https://stackoverflow.com/questions/12083319/add-custom-tokens-in-jinja2-e-g-somevar
        """


def populate_default_variables(variables: Optional[List[TemplateVariable]], variable_values: VariablesDict):
    if variables:
        for variable in variables:
            name = variable.name
            if name not in variable_values and variable.default is not None:
                variable_values[name] = variable.default


def expand_raw_config(
    template_configuration: TemplateConfiguration,
    variables: VariablesDict,
    secrets: SecretsDict,
    user_details: UserDetailsDict,
    environment: EnvironmentDict,
) -> RawTemplateConfig:
    template_variables = {
        "variables": variables,
        "secrets": secrets,
        "user": user_details,
        "environment": environment,
    }

    return _expand_raw_config(template_configuration, template_variables)


def _expand_raw_config(
    template_configuration: TemplateConfiguration, template_variables: Dict[str, Any]
) -> RawTemplateConfig:
    template_start = template_configuration.template_start or "{{"
    template_end = template_configuration.template_end or "}}"

    def expand_template(_, key, value):
        if isinstance(value, str) and template_start in value and template_end in value:
            template = _environment(template_start, template_end).from_string(value)
            return key, template.render(**template_variables)
        return key, value

    template_model_as_json = template_configuration.model_dump()
    raw_config = remap(template_model_as_json, visit=expand_template)
    _clean_template_meta_parameters(raw_config)
    return raw_config


def merge_implicit_parameters(raw_config: RawTemplateConfig, implicit: Optional["ImplicitConfigurationParameters"]):
    if implicit:
        raw_config.update(implicit)
        raw_config.pop("oauth2_client_id", None)
        raw_config.pop("oauth2_client_secret", None)
        raw_config.pop("oauth2_scope", None)


def verify_vault_configured_if_uses_secrets(catalog, vault_configured: bool, exception_message: str) -> None:
    if _catalog_uses_secrets(catalog) and not vault_configured:
        raise Exception(exception_message)


def _catalog_uses_secrets(catalog) -> bool:
    templates = catalog.root
    for template in templates:
        if template.secrets and len(template.secrets) > 0:
            return True
    return False


def _clean_template_meta_parameters(config: RawTemplateConfig) -> RawTemplateConfig:
    # slight templating differences between what is allowed in the template definition
    # and what is allowed in the actual configuration objects we send to respective modules
    # to instantiate plugins. In particular, descriptions of how templating is done should
    # eliminated after templates have been expanded.
    meta_parameters = ["template_start", "template_end"]
    for meta_parameter in meta_parameters:
        if meta_parameter in config:
            del config[meta_parameter]
    return config


# cwl-like - convert simple dictionary to list of dictionaries for quickly
# configuring variables and secrets
def apply_syntactic_sugar(raw_templates: List[RawTemplateConfig]) -> List[RawTemplateConfig]:
    templates = []
    expanded_raw_templates = _expand_includes(raw_templates)
    for template in expanded_raw_templates:
        _force_key_to_list(template, "variables")
        _force_key_to_list(template, "secrets")
        _force_key_to_list(template, "environment")
        templates.append(template)
    return templates


def _expand_includes(raw_templates: List[RawTemplateConfig]) -> List[RawTemplateConfig]:
    expanded_raw_templates = []
    for raw_template in raw_templates:
        expanded_raw_templates.extend(_expand_include(raw_template))
    return expanded_raw_templates


def _expand_include(raw_template: RawTemplateConfig) -> List[RawTemplateConfig]:
    has_one_key = len(raw_template.keys()) == 1
    has_include = "include" in raw_template

    if has_one_key and has_include:
        include = raw_template["include"]
        with open(include) as f:
            included = yaml.safe_load(f)
            raw_templates: List[RawTemplateConfig]
            if isinstance(included, list):
                raw_templates = included
            else:
                raw_templates = [included]
            return _expand_includes(raw_templates)
    else:
        return [raw_template]


def _force_key_to_list(template: RawTemplateConfig, key: str) -> None:
    value = template.get(key, None)
    if isinstance(value, dict):
        value_as_list = []
        for key_name, key_value in value.items():
            key_value["name"] = key_name
            value_as_list.append(key_value)
        template[key] = value_as_list


class TemplateReference(Protocol):
    template_id: str
    template_version: int


class InstanceDefinition(TemplateReference, Protocol):
    variables: Dict[str, Any]
    secrets: SecretsDict


class Template(Protocol):
    @property
    def id(self) -> str: ...

    @property
    def version(self) -> int: ...

    @property
    def type(self) -> str: ...

    @property
    def variables(self) -> Optional[List[TemplateVariable]]: ...

    @property
    def secrets(self) -> Optional[List[TemplateSecret]]: ...

    @property
    def environment(self) -> Optional[List[TemplateEnvironmentEntry]]: ...


T = TypeVar("T", bound=Template, covariant=True)


def find_template(templates: List[T], instance_reference: TemplateReference, what: str) -> T:
    template_id = instance_reference.template_id
    template_version = instance_reference.template_version
    return find_template_by(templates, template_id, template_version, what)


def find_template_by(templates: List[T], template_id: str, template_version: int, what: str) -> T:
    for template in templates:
        if template.id == template_id and template.version == template_version:
            return template

    raise ObjectNotFound(f"Could not find a {what} template with id {template_id} and version {template_version}")


def validate_variable_types(instance: InstanceDefinition, template: Template) -> None:
    pass


def validate_defines_all_required_secrets(instance: InstanceDefinition, template: Template):
    secrets = instance.secrets
    for template_secret in template.secrets or []:
        name = template_secret.name
        if name not in secrets:
            raise RequestParameterMissingException(f"Must define secret '{name}'")


def validate_defines_all_required_variables(instance: InstanceDefinition, template: Template):
    variables = instance.variables
    for template_variable in template.variables or []:
        name = template_variable.name
        has_default = template_variable.default is not None
        if name not in variables and not has_default:
            raise RequestParameterMissingException(f"Must define variable '{name}'")


def validate_specified_datatypes(instance: InstanceDefinition, template: Template):
    secrets = instance.secrets
    for name, value in secrets.items():
        if not isinstance(value, str):
            raise RequestParameterInvalidException(f"Secret value for secret '{name}' must be of type string")
    variables = instance.variables
    validate_specified_datatypes_variables(variables, template)


def validate_specified_datatypes_variables(variables: Dict[str, Any], template: Template):
    for template_variable in template.variables or []:
        name = template_variable.name
        variable_value = variables.get(name, template_variable.default)
        template_type = template_variable.type
        if template_type in ["string", "path_component"]:
            if not isinstance(variable_value, str):
                raise RequestParameterInvalidException(f"Variable value for variable '{name}' must be of type str")
            if template_type == "path_component":
                if ".." in variable_value or "/" in variable_value:
                    raise RequestParameterInvalidException(
                        f"Variable value for variable '{name}' must be simple path component, invalid characters found"
                    )
                if not acts_as_simple_path_component(variable_value):
                    raise RequestParameterInvalidException(
                        f"Variable value for variable '{name}' must be simple path component, invalid characters found"
                    )
        if template_type == "integer":
            if not _is_of_exact_type(variable_value, int):
                raise RequestParameterInvalidException(f"Variable value for variable '{name}' must be of type int")
        if template_type == "boolean":
            if not _is_of_exact_type(variable_value, bool):
                raise RequestParameterInvalidException(f"Variable value for variable '{name}' must be of type bool")


def validate_no_extra_secrets_defined(secrets: Dict[str, str], template: Template) -> None:
    template_secrets = secrets_as_dict(template.secrets)
    for secret in secrets.keys():
        if secret not in template_secrets:
            raise RequestParameterInvalidException(f"No secret named {secret} for this template")


def validate_no_extra_variables_defined(variables: Dict[str, Any], template: Template):
    template_variables = _variables_as_dict(template.variables)
    for variable in variables.keys():
        if variable not in template_variables:
            raise RequestParameterInvalidException(f"No variable named {variable} for this template")


def validate_secrets_and_variables(instance: InstanceDefinition, template: Template) -> None:
    validate_defines_all_required_secrets(instance, template)
    validate_defines_all_required_variables(instance, template)
    validate_specified_datatypes(instance, template)
    validate_no_extra_secrets_defined(instance.secrets, template)
    validate_no_extra_variables_defined(instance.variables, template)


def secrets_as_dict(secrets: Optional[List[TemplateSecret]]) -> Dict[str, TemplateSecret]:
    as_dict = {}
    for secret in secrets or []:
        as_dict[secret.name] = secret
    return as_dict


def _variables_as_dict(variables: Optional[List[TemplateVariable]]) -> Dict[str, TemplateVariable]:
    as_dict = {}
    for variable in variables or []:
        as_dict[variable.name] = variable
    return as_dict


def _is_of_exact_type(object: Any, target_type: Type):
    # isinstance(False, int) and False == 0 are both True in Python...
    # We are creating a DSL here that is intentionally more strict than Python
    # so we are using type() instead of isinstance and we have the test coverage
    # to ensure this is the desired behavior and remains. Think JSON typing, not
    # pythonic typing. Galaxy's internals as a Python project should not be
    # exposed here.
    return type(object) == target_type  # noqa: E721


def acts_as_simple_path_component(value: str):
    cwd = os.getcwd()
    abs_path = os.path.abspath(f"{cwd}/{value}")
    unaffected_by_normpath = os.path.normpath(abs_path) == abs_path
    if not unaffected_by_normpath:
        return False
    should_be_cwd, should_be_value = os.path.split(abs_path)
    if should_be_cwd != cwd:
        return False
    if should_be_value != value:
        return False
    return True


class PluginAspectStatus(StrictModel):
    state: Literal["ok", "not_ok", "unknown"]
    message: str

    @property
    def is_not_ok(self):
        return self.state == "not_ok"


class PluginStatus(StrictModel):
    template_definition: PluginAspectStatus
    template_settings: Optional[PluginAspectStatus] = None
    connection: Optional[PluginAspectStatus] = None
    # I would love to disambiguate connection vs auth errors but would
    # attempting to do that cause confusion. Maybe not if the user interface
    # skipped presenting the one that couldn't be disambiguated for that
    # particular plugin?

    # TODO: Fill in writable checks.
    # writable: Optional[PluginAspectStatus] = None
    oauth2_access_token_generation: Optional[PluginAspectStatus] = None


def status_template_definition(template: Optional[Template]) -> PluginAspectStatus:
    # if we found a template in the catalog, it was validated at load time. Reflect
    # this as a PluginAspectStatus
    if template:
        return PluginAspectStatus(state="ok", message="Template definition found and validates against schema")
    else:
        return PluginAspectStatus(state="not_ok", message="Template not found or not loaded")


def settings_exception_to_status(exception: Optional[Exception]) -> PluginAspectStatus:
    if exception is None:
        status = PluginAspectStatus(state="ok", message="Valid configuration resulted from supplied settings")
    elif isinstance(exception, UndefinedError):
        message = f"Problem with template definition causing invalid settings resolution, please contact admin to correct template: {exception}"
        status = PluginAspectStatus(state="not_ok", message=message)
    elif isinstance(exception, ValidationError):
        message = f"Problem with template definition causing invalid configuration, template expanded without error but resulting configuration is invalid. please contact admin to correct template: {exception}"
        status = PluginAspectStatus(state="not_ok", message=message)
    else:
        message = f"Unknown problem with resolving configuration from supplied settings: {exception}"
        status = PluginAspectStatus(state="not_ok", message=message)
    return status


def connection_exception_to_status(what: str, exception: Optional[Exception]) -> PluginAspectStatus:
    if exception is None:
        connection_status = PluginAspectStatus(state="ok", message="Valid connection resulted from supplied settings")
    else:
        message = f"Failed to connect to a {what} with supplied settings: {exception}"
        connection_status = PluginAspectStatus(state="not_ok", message=message)
    return connection_status


class OAuth2Info(StrictModel):
    authorize_url: str


class OAuth2Configuration(StrictModel):
    authorize_url: str
    token_url: str
    authorize_params: Optional[Dict[str, str]]
    scope: Optional[str] = None


ConfiguredOAuth2Sources = Dict[str, OAuth2Configuration]


class OAuth2ClientPair(StrictModel):
    client_id: str
    client_secret: str


def get_authorize_url(
    client_id_or_pair: Union[str, OAuth2ClientPair],
    config: OAuth2Configuration,
    redirect_uri: Optional[str],
    state: Optional[str] = None,
    scope: Optional[str] = None,
) -> str:
    client_id = client_id_or_pair if isinstance(client_id_or_pair, str) else client_id_or_pair.client_id
    query_data = dict(
        client_id=client_id,
        response_type="code",
    )
    if redirect_uri is not None:
        query_data["redirect_uri"] = redirect_uri
    if state is not None:
        query_data["state"] = state
    if scope is not None:
        query_data["scope"] = scope
    elif config.scope is not None:
        query_data["scope"] = config.scope
    query_data.update(config.authorize_params or {})
    query = urlencode(query_data)
    return f"{config.authorize_url}?{query}"


def get_token_from_code_raw(
    code: str, client_pair: OAuth2ClientPair, config: OAuth2Configuration, redirect_uri: Optional[str]
) -> requests.Response:
    data = {
        "code": code,
        "grant_type": "authorization_code",
        "client_id": client_pair.client_id,
        "client_secret": client_pair.client_secret,
    }
    if redirect_uri is not None:
        data["redirect_uri"] = redirect_uri

    return requests.post(config.token_url, data=data)


def get_token_from_refresh_raw(
    refresh_token: str, client_pair: OAuth2ClientPair, config: OAuth2Configuration
) -> requests.Response:
    data = {
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
        "client_id": client_pair.client_id,
        "client_secret": client_pair.client_secret,
    }

    return requests.post(config.token_url, data=data)


def get_oauth2_config_from(template, sources: ConfiguredOAuth2Sources) -> OAuth2Configuration:
    template_type = template.configuration.type
    if template_type not in sources:
        raise ObjectNotFound(f"oauth information not available for template type {template_type}")
    return sources[template_type]


def read_oauth2_info_from_configuration(
    template_configuration: TemplateConfiguration,
    user_details: UserDetailsDict,
    environment: EnvironmentDict,
) -> Tuple[OAuth2ClientPair, Optional[str]]:
    template_variables = {
        "user": user_details,
        "environment": environment,
    }

    expanded_config = _expand_raw_config(template_configuration, template_variables)
    oauth2_client_id = expanded_config["oauth2_client_id"]
    oauth2_client_secret = expanded_config["oauth2_client_secret"]
    oauth2_scope = cast(Optional[str], expanded_config.get("oauth2_scope"))
    client_pair = OAuth2ClientPair(client_id=oauth2_client_id, client_secret=oauth2_client_secret)
    return client_pair, oauth2_scope


# Things added to configuration dictionary not managed by the template
# but injected dynamically. Currently only `oauth2_access_token`.
class ImplicitConfigurationParameters(TypedDict):
    oauth2_access_token: NotRequired[str]
