"""Administrator-defined extra user preferences, configured in ``user_preferences_extra_conf.yml``.

Values not kept in the vault are stored as one JSON object in the user's
``extra_user_preferences`` preference, keyed ``<section>|<input>``. File source
templates read them by that key, so the storage format is fixed; only the API
around it is shaped here.
"""

import json
import logging
from typing import Any

from pydantic import ValidationError

from galaxy import (
    exceptions,
    util,
)
from galaxy.config import GalaxyAppConfiguration
from galaxy.model import (
    required_object_session,
    User,
)
from galaxy.schema.schema import (
    ExtraPreferenceInputDefinition,
    ExtraPreferenceSecretState,
    ExtraPreferenceSectionDefinition,
    ExtraPreferenceValue,
    UserExtraPreferences,
)
from galaxy.security.vault import (
    is_vault_configured,
    UserVaultWrapper,
    Vault,
)

log = logging.getLogger(__name__)

EXTRA_PREFERENCES_KEY = "extra_user_preferences"

# Sent in place of a sensitive value by the form of the deprecated
# ``information/inputs`` endpoint, and sent back unchanged when the user did not
# edit the field.
LEGACY_SECRET_PLACEHOLDER = "__SECRET_PLACEHOLDER__"

_Change = tuple[ExtraPreferenceSectionDefinition, ExtraPreferenceInputDefinition, Any]


class ExtraPreferencesManager:
    def __init__(self, config: GalaxyAppConfiguration, vault: Vault):
        self.config = config
        self.vault = vault
        # The parsed definition, with the loaded YAML it was parsed from.
        self._definition: tuple[Any, list[ExtraPreferenceSectionDefinition]] | None = None

    def definition(self) -> list[ExtraPreferenceSectionDefinition]:
        preferences = self.config.user_preferences_extra["preferences"]
        if self._definition is None or self._definition[0] is not preferences:
            self._definition = (preferences, _parse_definition(preferences))
        return self._definition[1]

    def values(self, user: User) -> UserExtraPreferences:
        stored = user.extra_preferences
        user_vault = UserVaultWrapper(self.vault, user)
        values: dict[str, dict[str, ExtraPreferenceValue | ExtraPreferenceSecretState | None]] = {}
        for section in self.definition():
            section_values: dict[str, ExtraPreferenceValue | ExtraPreferenceSecretState | None] = {}
            for field in section.inputs:
                if field.in_vault:
                    # Without a vault there is nowhere a value could have been stored. A
                    # cleared vault entry holds an empty string.
                    raw = (user_vault.read_secret(_vault_key(section, field)) if self._has_vault else None) or None
                else:
                    raw = stored[_stored_key(section, field)]
                if field.sensitive:
                    section_values[field.name] = ExtraPreferenceSecretState(is_set=raw not in (None, ""))
                else:
                    section_values[field.name] = _decode(field, raw)
            values[section.name] = section_values
        return UserExtraPreferences(values)

    def update(
        self, user: User, payload: dict[str, dict[str, ExtraPreferenceValue | None]], *, commit: bool = True
    ) -> None:
        """Change the given values, leaving every input that is not in ``payload`` as it is.

        The whole payload is validated before anything is written, because vault
        backends commit their writes independently of the database session.
        """
        sections = {section.name: section for section in self.definition()}
        changes: list[_Change] = []
        for section_name, inputs in payload.items():
            if (section := sections.get(section_name)) is None:
                raise exceptions.RequestParameterInvalidException(
                    f"Unknown extra preferences section '{section_name}'."
                )
            for field_name, value in inputs.items():
                if (field := _find_field(section, field_name)) is None:
                    raise exceptions.RequestParameterInvalidException(
                        f"Unknown extra preference '{field_name}' in section '{section_name}'."
                    )
                if field.required and value in (None, "", []):
                    raise _required_error(section, field)
                _check_type(section, field, value)
                self._check_storable(section, field)
                changes.append((section, field, value))
        self._apply(user, changes)
        if commit:
            required_object_session(user).commit()

    def legacy_form_inputs(self, user: User) -> list[dict[str, Any]]:
        """Form-builder sections for the deprecated ``information/inputs`` endpoint."""
        values = self.values(user).root
        form_sections = []
        for section in self.definition():
            form_inputs = []
            for field in section.inputs:
                form_input = field.model_dump(exclude_none=True)
                required = "Required" if field.required else ""
                form_input["help"] = f"{field.help} {required}" if field.help else required
                if field.sensitive:
                    form_input["value"] = LEGACY_SECRET_PLACEHOLDER
                    # the generic form masks password inputs
                    form_input["type"] = "password"
                elif (value := values[section.name][field.name]) is not None:
                    form_input["value"] = value
                form_inputs.append(form_input)
            form_sections.append(
                {
                    "type": "section",
                    "title": section.description,
                    "name": section.name,
                    "expanded": True,
                    "inputs": form_inputs,
                }
            )
        return form_sections

    def update_from_legacy_form(self, user: User, payload: dict[str, Any], *, commit: bool = True) -> None:
        """Store the extra preferences of a flat ``<section>|<input>`` form submission.

        The same form carries the account fields, so keys that do not name a
        configured input are not extra preferences and are skipped. Values are
        stored as the form sent them; reading decodes them per input type.
        """
        sections = {section.name: section for section in self.definition()}
        changes: list[_Change] = []
        for key, value in payload.items():
            section_name, separator, field_name = key.partition("|")
            if not separator or (section := sections.get(section_name)) is None:
                continue
            if (field := _find_field(section, field_name)) is None:
                continue
            if field.sensitive and value == LEGACY_SECRET_PLACEHOLDER:
                continue
            # The form sends unfilled inputs as empty strings.
            if field.required and value == "":
                raise _required_error(section, field)
            self._check_storable(section, field)
            changes.append((section, field, value))
        self._apply(user, changes)
        if commit:
            required_object_session(user).commit()

    @property
    def _has_vault(self) -> bool:
        return is_vault_configured(self.vault)

    def _check_storable(self, section: ExtraPreferenceSectionDefinition, field: ExtraPreferenceInputDefinition) -> None:
        if field.in_vault and not self._has_vault:
            raise exceptions.ConfigDoesNotAllowException(
                f"'{_display_name(field)}' in '{section.description}' is stored in a vault, "
                "but this Galaxy has no vault configured."
            )

    def _apply(self, user: User, changes: list[_Change]) -> None:
        stored = dict(user.extra_preferences)
        stored_changed = False
        user_vault = UserVaultWrapper(self.vault, user)
        for section, field, value in changes:
            if field.in_vault:
                if value is None:
                    user_vault.delete_secret(_vault_key(section, field))
                else:
                    encoded = value if isinstance(value, str) else json.dumps(value)
                    user_vault.write_secret(_vault_key(section, field), encoded)
            else:
                if value is None:
                    stored.pop(_stored_key(section, field), None)
                else:
                    stored[_stored_key(section, field)] = value
                stored_changed = True
        if stored_changed:
            user.preferences[EXTRA_PREFERENCES_KEY] = json.dumps(stored)


def _parse_definition(preferences: Any) -> list[ExtraPreferenceSectionDefinition]:
    """Parse the loaded YAML, skipping (and logging) inputs that do not describe a form input.

    One malformed input must not break the account pages that render the rest.
    """
    sections = []
    for name, section in (preferences or {}).items():
        # A section key with nothing under it loads as None and declares no inputs.
        if not isinstance(section, dict):
            continue
        fields = []
        for raw in section.get("inputs") or []:
            try:
                field = ExtraPreferenceInputDefinition.model_validate(raw)
            except ValidationError as e:
                log.warning("Skipping invalid input %r of extra preferences section %r: %s", raw, name, e)
                continue
            # A default for a password or secret is never shown or used, and the
            # definition is served to every user.
            fields.append(field.model_copy(update={"value": None}) if field.sensitive else field)
        sections.append(
            ExtraPreferenceSectionDefinition(
                name=name, description=str(section.get("description", name)), inputs=fields
            )
        )
    return sections


def _find_field(section: ExtraPreferenceSectionDefinition, name: str) -> ExtraPreferenceInputDefinition | None:
    return next((field for field in section.inputs if field.name == name), None)


def _stored_key(section: ExtraPreferenceSectionDefinition, field: ExtraPreferenceInputDefinition) -> str:
    return f"{section.name}|{field.name}"


def _vault_key(section: ExtraPreferenceSectionDefinition, field: ExtraPreferenceInputDefinition) -> str:
    return f"preferences/{section.name}/{field.name}"


def _display_name(field: ExtraPreferenceInputDefinition) -> str:
    return field.label or field.name


def _required_error(
    section: ExtraPreferenceSectionDefinition, field: ExtraPreferenceInputDefinition
) -> exceptions.RequestParameterInvalidException:
    return exceptions.RequestParameterInvalidException(
        f"'{_display_name(field)}' in '{section.description}' is required."
    )


def _is_scalar(value: Any) -> bool:
    return isinstance(value, (str, int, float, bool))


def _decode(field: ExtraPreferenceInputDefinition, raw: Any) -> ExtraPreferenceValue | None:
    """The stored value in the input's declared type, or None if it cannot be read as one.

    Vault values are strings, and values stored through the deprecated form are
    whatever its clients sent, e.g. ``"true"`` for a boolean.
    """
    if raw is None:
        return None
    try:
        if field.multiple:
            values = json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(values, list) and all(_is_scalar(value) for value in values):
                return values
            return None
        if field.kind == "select" and field.options and isinstance(raw, str) and raw not in field.option_values:
            # vault values are strings; a non-string option was stored JSON encoded
            return next((option for option in field.option_values if json.dumps(option) == raw), None)
        if field.kind == "boolean":
            return raw if isinstance(raw, bool) else util.string_as_bool(raw)
        if field.kind == "integer":
            return raw if isinstance(raw, int) and not isinstance(raw, bool) else int(raw)
        if field.kind == "float":
            return raw if isinstance(raw, (int, float)) and not isinstance(raw, bool) else float(raw)
    except (TypeError, ValueError):
        return None
    return raw if _is_scalar(raw) else None


def _check_type(
    section: ExtraPreferenceSectionDefinition, field: ExtraPreferenceInputDefinition, value: ExtraPreferenceValue | None
) -> None:
    if value is None:
        return
    # bool is a subclass of int, so it is excluded from the numeric types explicitly.
    if field.kind == "boolean":
        valid = isinstance(value, bool)
    elif field.kind == "integer":
        valid = isinstance(value, int) and not isinstance(value, bool)
    elif field.kind == "float":
        valid = isinstance(value, (int, float)) and not isinstance(value, bool)
    elif field.kind == "select" and field.options:
        options = field.option_values
        if field.multiple:
            valid = isinstance(value, list) and all(_is_scalar(item) and item in options for item in value)
        else:
            valid = _is_scalar(value) and value in options
    else:
        valid = isinstance(value, str)
    if not valid:
        raise exceptions.RequestParameterInvalidException(
            f"Invalid value for '{_display_name(field)}' in '{section.description}'."
        )
