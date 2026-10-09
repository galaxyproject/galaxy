"""Models describing Admin panel extensions.

An admin extension is a directory containing a ``config.yml`` that declares a
section for the Admin panel and the items shown under it. Extensions are
declarative: they ship no JavaScript, and the client renders them from these
models alone.
"""

import math
from typing import (
    Annotated,
    Any,
    Literal,
)

from pydantic import (
    Field,
    model_validator,
    StringConstraints,
)

from galaxy.schema.schema import Model

IdentifierStr = Annotated[str, StringConstraints(pattern=r"^[A-Za-z][A-Za-z0-9_-]*$", max_length=64)]
SettingKeyStr = Annotated[
    str, StringConstraints(pattern=r"^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z][A-Za-z0-9_]*)+$", max_length=255)
]
SettingValue = bool | int | float | str | None


class AdminExtensionLinkItem(Model):
    """A panel entry that opens a URL, either framed inside Galaxy or in a new tab."""

    id: IdentifierStr = Field(..., description="Identifier of the item, unique within its extension.")
    type: Literal["link"] = Field("link", description="Item type.")
    title: str = Field(..., min_length=1, max_length=255, description="Text shown in the Admin panel.")
    url: str = Field(..., min_length=1, description="URL to open. Relative URLs are resolved against Galaxy's root.")
    target: Literal["iframe", "new_tab"] = Field(
        "iframe", description="Whether to show the URL inside the Galaxy center panel or open it in a new tab."
    )


class AdminExtensionFormInput(Model):
    """One field of a form item, bound to a settings key.

    The code that reads a setting owns its key and documents it (for example a job
    runner documents ``gcp_batch.pool_ttl_seconds``). An input names that key
    explicitly so any extension can offer a form for it; without ``key`` the input
    gets one built from the extension, item and input ids at load time.
    """

    name: IdentifierStr = Field(..., description="Identifier of the input, unique within its form.")
    key: SettingKeyStr | None = Field(
        None, description="Settings key this input reads and writes. Defaults to <extension>.<item>.<name>."
    )
    type: Literal["boolean", "integer", "float", "text", "select"] = Field(..., description="Input type.")
    label: str = Field(..., min_length=1, max_length=255, description="Label shown next to the input.")
    help: str | None = Field(None, max_length=2000, description="Help text shown under the input.")
    default: SettingValue = Field(None, description="Value used when nothing has been saved.")
    options: list[str] | None = Field(None, description="Choices for a select input.")
    min: float | None = Field(None, description="Lower bound for integer and float inputs.")
    max: float | None = Field(None, description="Upper bound for integer and float inputs.")

    @model_validator(mode="after")
    def _check_shape(self) -> "AdminExtensionFormInput":
        if self.type == "select":
            if not self.options:
                raise ValueError("a select input needs at least one option")
        elif self.options is not None:
            raise ValueError("options are only valid for select inputs")
        if self.type not in ("integer", "float") and (self.min is not None or self.max is not None):
            raise ValueError("min and max are only valid for integer and float inputs")
        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValueError("min must not exceed max")
        if self.default is not None:
            # Keep the canonical form so readers get the declared type (False, not "false") before any save.
            self.default = coerce_setting_value(self, self.default)
        return self


class AdminExtensionFormItem(Model):
    """A panel entry that shows a settings form rendered from the declared inputs."""

    id: IdentifierStr = Field(..., description="Identifier of the item, unique within its extension.")
    type: Literal["form"] = Field(..., description="Item type.")
    title: str = Field(..., min_length=1, max_length=255, description="Text shown in the Admin panel.")
    description: str | None = Field(None, max_length=2000, description="Text shown above the form.")
    inputs: list[AdminExtensionFormInput] = Field(..., min_length=1, description="Fields of the form.")

    @model_validator(mode="after")
    def _check_unique_names(self) -> "AdminExtensionFormItem":
        names = [i.name for i in self.inputs]
        if len(names) != len(set(names)):
            raise ValueError("input names must be unique within a form")
        return self


AdminExtensionItem = Annotated[AdminExtensionLinkItem | AdminExtensionFormItem, Field(discriminator="type")]


class AdminExtension(Model):
    """One extension: a titled section of the Admin panel and its items."""

    id: IdentifierStr = Field(..., description="Identifier of the extension, unique across all loaded extensions.")
    section: str = Field(..., min_length=1, max_length=255, description="Section title shown in the Admin panel.")
    items: list[AdminExtensionItem] = Field(..., min_length=1, description="Items shown under the section.")

    @model_validator(mode="after")
    def _check_unique_item_ids(self) -> "AdminExtension":
        ids = [i.id for i in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("item ids must be unique within an extension")
        return self


def coerce_setting_value(input_def: AdminExtensionFormInput, value: SettingValue) -> SettingValue:
    """Check a submitted value against an input declaration and return it in canonical form.

    :raises ValueError: if the value does not fit the input's type, bounds or options.
    """
    label = input_def.name
    if value is None:
        return None
    if input_def.type == "boolean":
        if isinstance(value, bool):
            return value
        if isinstance(value, str) and value.lower() in ("true", "false"):
            return value.lower() == "true"
        raise ValueError(f"{label}: expected true or false")
    if input_def.type == "integer":
        if isinstance(value, bool) or not isinstance(value, (int, float, str)):
            raise ValueError(f"{label}: expected an integer")
        try:
            number = int(str(value))
        except ValueError:
            raise ValueError(f"{label}: expected an integer")
        _check_bounds(input_def, number)
        return number
    if input_def.type == "float":
        if isinstance(value, bool) or not isinstance(value, (int, float, str)):
            raise ValueError(f"{label}: expected a number")
        try:
            number_f = float(str(value))
        except ValueError:
            raise ValueError(f"{label}: expected a number")
        if not math.isfinite(number_f):
            # NaN compares false against any bound and neither NaN nor infinity is valid JSON.
            raise ValueError(f"{label}: expected a finite number")
        _check_bounds(input_def, number_f)
        return number_f
    if input_def.type == "select":
        if not isinstance(value, str) or value not in (input_def.options or []):
            raise ValueError(f"{label}: expected one of {', '.join(input_def.options or [])}")
        return value
    if not isinstance(value, (str, int, float)) or isinstance(value, bool):
        raise ValueError(f"{label}: expected text")
    return str(value)


def _check_bounds(input_def: AdminExtensionFormInput, number: float) -> None:
    if input_def.min is not None and number < input_def.min:
        raise ValueError(f"{input_def.name}: must be at least {input_def.min:g}")
    if input_def.max is not None and number > input_def.max:
        raise ValueError(f"{input_def.name}: must be at most {input_def.max:g}")


class AdminExtensionSettings(Model):
    """Current values of a form item's inputs, keyed by input name."""

    values: dict[str, SettingValue] = Field(..., description="Value per input name.")


class AdminExtensionFormResponse(Model):
    """A form item rendered for the client's generic form component."""

    title: str
    message: str | None = None
    inputs: list[dict[str, Any]] = Field(..., description="Galaxy form input definitions with current values.")
