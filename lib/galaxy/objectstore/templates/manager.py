import os
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from typing_extensions import Protocol
from yaml import safe_load

from galaxy.exceptions import (
    ObjectNotFound,
    RequestParameterMissingException,
)
from galaxy.objectstore.badges import serialize_badges
from .models import (
    ObjectStoreTemplate,
    ObjectStoreTemplateCatalog,
    ObjectStoreTemplateSummaries,
)

RawTemplateConfig = Dict[str, Any]


class AppConfigProtocol(Protocol):
    object_store_templates: Optional[List[RawTemplateConfig]]
    object_store_templates_config_file: Optional[str]


class TemplateReference(Protocol):
    template_id: str
    template_version: int


class InstanceDefinition(TemplateReference, Protocol):
    variables: Dict[str, Any]
    secrets: Dict[str, str]


SECRETS_NEED_VAULT_MESSAGE = "The object store templates configuration can not be used - a Galaxy vault must be configured for templates that use secrets - please set the vault_config_file configuration option to point at a valid vault configuration."


class ConfiguredObjectStoreTemplates:
    catalog: ObjectStoreTemplateCatalog

    def __init__(self, catalog: ObjectStoreTemplateCatalog):
        self.catalog = catalog

    @staticmethod
    def from_app_config(config: AppConfigProtocol, vault_configured=None) -> "ConfiguredObjectStoreTemplates":
        raw_config = config.object_store_templates
        if raw_config is None:
            config_file = config.object_store_templates_config_file
            if config_file and os.path.exists(config_file):
                with open(config_file) as f:
                    raw_config = safe_load(f)
        if raw_config is None:
            raw_config = []
        templates = ConfiguredObjectStoreTemplates(raw_config_to_catalog(raw_config))
        if vault_configured is False and templates.configuration_uses_secrets:
            raise Exception(SECRETS_NEED_VAULT_MESSAGE)
        return templates

    @property
    def configuration_uses_secrets(self) -> bool:
        templates = self.catalog.root
        for template in templates:
            if template.secrets and len(template.secrets) > 0:
                return True
        return False

    @property
    def summaries(self) -> ObjectStoreTemplateSummaries:
        templates = self.catalog.root
        summaries = []
        for template in templates:
            template_dict = template.model_dump()
            configuration = template_dict.pop("configuration")
            stored_badges = configuration["badges"] or []
            object_store_type = configuration["type"]
            badges = serialize_badges(stored_badges, False, True, True, object_store_type in ["azure", "s3"])
            template_dict["badges"] = badges
            template_dict["type"] = object_store_type
            summaries.append(template_dict)
        return ObjectStoreTemplateSummaries.model_validate(summaries)

    def find_template(self, instance_reference: TemplateReference) -> ObjectStoreTemplate:
        """Find the corresponding template and throw ObjectNotFound if not available."""
        template_id = instance_reference.template_id
        template_version = instance_reference.template_version
        return self.find_template_by(template_id, template_version)

    def find_template_by(self, template_id: str, template_version: int) -> ObjectStoreTemplate:
        templates = self.catalog.root

        for template in templates:
            if template.id == template_id and template.version == template_version:
                return template

        raise ObjectNotFound(
            f"Could not find a object store template with id {template_id} and version {template_version}"
        )

    def validate(self, instance: InstanceDefinition):
        template = self.find_template(instance)
        secrets = instance.secrets
        for template_secret in template.secrets or []:
            name = template_secret.name
            if name not in secrets:
                raise RequestParameterMissingException(f"Must define secret '{name}'")
        variables = instance.variables
        for template_variable in template.variables or []:
            name = template_variable.name
            if name not in variables:
                raise RequestParameterMissingException(f"Must define variable '{name}'")
        # TODO: validate no extra variables


def raw_config_to_catalog(raw_config: List[RawTemplateConfig]) -> ObjectStoreTemplateCatalog:
    effective_root = _apply_syntactic_sugar(raw_config)
    return ObjectStoreTemplateCatalog.model_validate(effective_root)


def _apply_syntactic_sugar(raw_templates: List[RawTemplateConfig]) -> List[RawTemplateConfig]:
    templates = []
    for template in raw_templates:
        _force_key_to_list(template, "variables")
        _force_key_to_list(template, "secrets")
        templates.append(template)
    return templates


def _force_key_to_list(template: RawTemplateConfig, key: str) -> None:
    value = template.get(key, None)
    if isinstance(value, dict):
        value_as_list = []
        for key_name, key_value in value.items():
            key_value["name"] = key_name
            value_as_list.append(key_value)
        template[key] = value_as_list
