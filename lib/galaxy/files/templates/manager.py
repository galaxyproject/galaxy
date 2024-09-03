import os
from typing import (
    List,
    Optional,
    Protocol,
)

from yaml import safe_load

from galaxy.util.config_templates import (
    apply_syntactic_sugar,
    find_template,
    find_template_by,
    InstanceDefinition,
    RawTemplateConfig,
    TemplateReference,
    validate_secrets_and_variables,
    verify_vault_configured_if_uses_secrets,
)
from .models import (
    FileSourceTemplate,
    FileSourceTemplateCatalog,
    FileSourceTemplateSummaries,
)

SECRETS_NEED_VAULT_MESSAGE = "The file source templates configuration can not be used - a Galaxy vault must be configured for templates that use secrets - please set the vault_config_file configuration option to point at a valid vault configuration."


class AppConfigProtocol(Protocol):
    file_source_templates: Optional[List[RawTemplateConfig]]
    file_source_templates_config_file: Optional[str]


class ConfiguredFileSourceTemplates:
    catalog: FileSourceTemplateCatalog

    def __init__(self, catalog: FileSourceTemplateCatalog):
        self.catalog = catalog

    @staticmethod
    def from_app_config(config: AppConfigProtocol, vault_configured=None) -> "ConfiguredFileSourceTemplates":
        raw_config = config.file_source_templates
        if raw_config is None:
            config_file = config.file_source_templates_config_file
            if config_file and os.path.exists(config_file):
                with open(config_file) as f:
                    raw_config = safe_load(f)
        if raw_config is None:
            raw_config = []
        catalog = raw_config_to_catalog(raw_config)
        verify_vault_configured_if_uses_secrets(
            catalog,
            vault_configured,
            SECRETS_NEED_VAULT_MESSAGE,
        )
        templates = ConfiguredFileSourceTemplates(catalog)
        return templates

    @property
    def summaries(self) -> FileSourceTemplateSummaries:
        templates = self.catalog.root
        summaries = []
        for template in templates:
            template_dict = template.model_dump()
            configuration = template_dict.pop("configuration")
            template_dict.pop("environment")
            object_store_type = configuration["type"]
            template_dict["type"] = object_store_type
            summaries.append(template_dict)
        return FileSourceTemplateSummaries.model_validate(summaries)

    def find_template(self, instance_reference: TemplateReference) -> FileSourceTemplate:
        """Find the corresponding template and throw ObjectNotFound if not available."""
        return find_template(self.catalog.root, instance_reference, "file source")

    def find_template_by(self, template_id: str, template_version: int) -> FileSourceTemplate:
        return find_template_by(self.catalog.root, template_id, template_version, "file source")

    def validate(self, instance: InstanceDefinition):
        template = self.find_template(instance)
        validate_secrets_and_variables(instance, template)


def raw_config_to_catalog(raw_config: List[RawTemplateConfig]) -> FileSourceTemplateCatalog:
    effective_root = apply_syntactic_sugar(raw_config)
    return FileSourceTemplateCatalog.model_validate(effective_root)
