"""Loading and lookup of Admin panel extensions."""

import logging
import os

import yaml
from pydantic import ValidationError

from galaxy.config import GalaxyAppConfiguration
from galaxy.exceptions import ObjectNotFound
from galaxy.schema.admin_extensions import (
    AdminExtension,
    AdminExtensionFormInput,
    AdminExtensionFormItem,
    AdminExtensionItem,
)
from galaxy.util import config_directories_from_setting

log = logging.getLogger(__name__)

CONFIG_FILE_NAMES = ("config.yml", "config.yaml")


def load_extensions(directories_setting: str | None) -> list[AdminExtension]:
    """Load every valid extension found under the configured directories.

    :param directories_setting: comma-separated directories to search, each
        containing one subdirectory per extension.
    :returns: the extensions in the order found. An extension whose config is
        missing, unparseable or invalid is skipped and logged. An extension whose
        id duplicates one already loaded is skipped and logged.
    """
    extensions: list[AdminExtension] = []
    seen: set[str] = set()
    key_types: dict[str, str] = {}
    for base_dir in config_directories_from_setting(directories_setting):
        if not os.path.isdir(base_dir):
            continue
        for name in sorted(os.listdir(base_dir)):
            extension_dir = os.path.join(base_dir, name)
            if not os.path.isdir(extension_dir):
                continue
            extension = _load_extension_dir(extension_dir)
            if extension is None:
                continue
            if extension.id in seen:
                log.error(
                    "Admin extension '%s' in %s duplicates an already loaded id, skipping", extension.id, extension_dir
                )
                continue
            _assign_default_keys(extension)
            conflict = _conflicting_key(extension, key_types)
            if conflict is not None:
                log.error(
                    "Admin extension '%s' in %s declares key '%s' with a different type than an already "
                    "loaded extension, skipping",
                    extension.id,
                    extension_dir,
                    conflict,
                )
                continue
            seen.add(extension.id)
            extensions.append(extension)
    return extensions


def _default_key(extension_id: str, item_id: str, input_name: str) -> str:
    return ".".join(part.replace("-", "_") for part in (extension_id, item_id, input_name))


def _assign_default_keys(extension: AdminExtension) -> None:
    for item in extension.items:
        if isinstance(item, AdminExtensionFormItem):
            for input_def in item.inputs:
                if input_def.key is None:
                    input_def.key = _default_key(extension.id, item.id, input_def.name)


def _conflicting_key(extension: AdminExtension, key_types: dict[str, str]) -> str | None:
    """Record the extension's keys in ``key_types``; return the first key whose type disagrees."""
    for item in extension.items:
        if not isinstance(item, AdminExtensionFormItem):
            continue
        for input_def in item.inputs:
            assert input_def.key is not None  # assigned by _assign_default_keys
            declared = key_types.get(input_def.key)
            if declared is not None and declared != input_def.type:
                return input_def.key
    for item in extension.items:
        if isinstance(item, AdminExtensionFormItem):
            for input_def in item.inputs:
                assert input_def.key is not None
                key_types[input_def.key] = input_def.type
    return None


def _load_extension_dir(extension_dir: str) -> AdminExtension | None:
    config_path = next(
        (os.path.join(extension_dir, n) for n in CONFIG_FILE_NAMES if os.path.isfile(os.path.join(extension_dir, n))),
        None,
    )
    if config_path is None:
        log.warning("Admin extension directory %s has no config.yml, skipping", extension_dir)
        return None
    try:
        with open(config_path) as fh:
            raw = yaml.safe_load(fh)
        return AdminExtension.model_validate(raw)
    except (OSError, yaml.YAMLError, ValidationError):
        log.exception("Failed to load admin extension from %s", config_path)
        return None


class AdminExtensionsManager:
    """Registry of Admin panel extensions loaded at startup."""

    def __init__(self, config: GalaxyAppConfiguration) -> None:
        self._extensions = load_extensions(config.admin_extensions_dir)
        self._inputs_by_key: dict[str, AdminExtensionFormInput] = {}
        for extension in self._extensions:
            for item in extension.items:
                if isinstance(item, AdminExtensionFormItem):
                    for input_def in item.inputs:
                        assert input_def.key is not None
                        self._inputs_by_key.setdefault(input_def.key, input_def)

    @property
    def extensions(self) -> list[AdminExtension]:
        """All loaded extensions."""
        return list(self._extensions)

    def get_extension(self, extension_id: str) -> AdminExtension:
        """Return the extension with the given id.

        :raises ObjectNotFound: if no loaded extension has that id.
        """
        for extension in self._extensions:
            if extension.id == extension_id:
                return extension
        raise ObjectNotFound(f"No admin extension with id '{extension_id}'")

    def get_item(self, extension_id: str, item_id: str) -> AdminExtensionItem:
        """Return one item of an extension.

        :raises ObjectNotFound: if the extension or the item does not exist.
        """
        extension = self.get_extension(extension_id)
        for item in extension.items:
            if item.id == item_id:
                return item
        raise ObjectNotFound(f"No item '{item_id}' in admin extension '{extension_id}'")

    def get_form_item(self, extension_id: str, item_id: str) -> AdminExtensionFormItem:
        """Return one form item of an extension.

        :raises ObjectNotFound: if the extension or the item does not exist, or the item is not a form.
        """
        item = self.get_item(extension_id, item_id)
        if not isinstance(item, AdminExtensionFormItem):
            raise ObjectNotFound(f"Item '{item_id}' in admin extension '{extension_id}' is not a form")
        return item

    def declared_input(self, key: str) -> AdminExtensionFormInput | None:
        """Return the input declaration for a settings key, or None if no loaded extension declares it."""
        return self._inputs_by_key.get(key)
