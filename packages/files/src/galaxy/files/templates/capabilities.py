"""Provider-specific behavior for interactive file-source template forms.

The template manager owns the generic lifecycle; capabilities own remote-service
lookups and validation that are meaningful only for one file-source type.
"""

from collections.abc import Callable
from dataclasses import (
    dataclass,
    field,
)
from typing import Protocol

from galaxy.exceptions import RequestParameterInvalidException
from galaxy.files.sources.github_fsspec import list_authorized_repositories
from galaxy.util.config_templates import (
    StrictModel,
    TemplateVariableSelect,
    TemplateVariableValueType,
)
from .models import (
    FileSourceTemplate,
    FileSourceTemplateAlertVariant,
)


class TemplateFormMessage(StrictModel):
    content: str
    variant: FileSourceTemplateAlertVariant = "info"


@dataclass
class TemplateFormData:
    dynamic_options: dict[str, list[tuple[str, str]]] = field(default_factory=dict)
    messages: list[TemplateFormMessage] = field(default_factory=list)


class FileSourceTemplateCapability(Protocol):
    def form_data(
        self,
        template: FileSourceTemplate,
        variables: dict[str, TemplateVariableValueType],
        access_token: Callable[[], str],
    ) -> TemplateFormData: ...

    def validate_creation(
        self,
        template: FileSourceTemplate,
        variables: dict[str, TemplateVariableValueType],
        access_token: Callable[[], str],
    ) -> None: ...


def _select_variable_name(template: FileSourceTemplate, provider_kind: str) -> str | None:
    for variable in template.variables or []:
        if isinstance(variable, TemplateVariableSelect) and variable.options_provider:
            if variable.options_provider.kind == provider_kind:
                return variable.name
    return None


class GithubTemplateCapability:
    """Populate and validate repository selectors from GitHub App grants."""

    owner_provider = "github_authorized_repository_owners"
    repository_provider = "github_authorized_repository_names"

    def _field_names(self, template: FileSourceTemplate) -> tuple[str | None, str | None]:
        return (
            _select_variable_name(template, self.owner_provider),
            _select_variable_name(template, self.repository_provider),
        )

    def _repositories(self, access_token: Callable[[], str]) -> list[dict[str, str]]:
        return list_authorized_repositories(access_token())

    def form_data(self, template, variables, access_token) -> TemplateFormData:
        owner_name, repository_name = self._field_names(template)
        if not owner_name or not repository_name:
            return TemplateFormData()

        granted_repositories = self._repositories(access_token)
        if not granted_repositories:
            return TemplateFormData(
                messages=[
                    TemplateFormMessage(
                        variant="warning",
                        content=(
                            "The GitHub App isn't installed on any repository you can access, so there are no owners "
                            "or repositories to choose. Install it on at least one repository from your "
                            '<a href="https://github.com/settings/installations" target="_blank" '
                            'rel="noopener noreferrer">installed GitHub Apps</a>, then reload this page.'
                        ),
                    )
                ]
            )

        owner = variables.get(owner_name)
        owners = sorted({repository["owner"] for repository in granted_repositories})
        options = {owner_name: [(value, value) for value in owners]}
        options[repository_name] = (
            [
                (repository["repo"], repository["repo"])
                for repository in granted_repositories
                if repository["owner"] == owner
            ]
            if isinstance(owner, str)
            else []
        )
        return TemplateFormData(
            dynamic_options=options,
            messages=[
                TemplateFormMessage(
                    content=(
                        "Need access to another repository? Update the GitHub App's repository access from your "
                        '<a href="https://github.com/settings/installations" target="_blank" '
                        'rel="noopener noreferrer">installed GitHub Apps</a> in a new tab, then reload this page.'
                    )
                )
            ],
        )

    def validate_creation(self, template, variables, access_token) -> None:
        owner_name, repository_name = self._field_names(template)
        if not owner_name or not repository_name:
            return
        owner = variables.get(owner_name)
        repository = variables.get(repository_name)
        if not isinstance(owner, str) or not isinstance(repository, str):
            return
        full_name = f"{owner}/{repository}"
        if not any(candidate["full_name"] == full_name for candidate in self._repositories(access_token)):
            raise RequestParameterInvalidException(
                f"The GitHub App isn't installed on {full_name}. Authorize access to this "
                "repository on GitHub, or pick one of the repositories you have granted access to."
            )


_CAPABILITIES: dict[str, FileSourceTemplateCapability] = {"github": GithubTemplateCapability()}


def capability_for(template: FileSourceTemplate) -> FileSourceTemplateCapability | None:
    return _CAPABILITIES.get(template.configuration.type)
