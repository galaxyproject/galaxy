"""Site-wide settings saved from Admin panel extension forms."""

import logging
import threading
import time
from typing import Any

from sqlalchemy import select

from galaxy.exceptions import RequestParameterInvalidException
from galaxy.managers.admin_extensions import AdminExtensionsManager
from galaxy.model import (
    AdminSetting,
    User,
)
from galaxy.model.scoped_session import galaxy_scoped_session
from galaxy.schema.admin_extensions import (
    AdminExtensionFormInput,
    AdminExtensionFormItem,
    coerce_setting_value,
    SettingValue,
)
from galaxy.structured_app import StructuredApp

log = logging.getLogger(__name__)

RELOAD_TASK = "reload_admin_settings"
CACHE_TTL_SECONDS = 30.0


class AdminSettingsManager:
    """Reads and writes settings declared by Admin panel extension forms.

    Only keys declared by a loaded extension are honoured: a stored value for an
    undeclared key is invisible to readers, so removing an extension cannot leave
    a hidden override in effect. Values are cached per process for a short time
    and the cache is cleared in every process when a form is saved.
    """

    def __init__(self, app: StructuredApp, sa_session: galaxy_scoped_session, extensions: AdminExtensionsManager):
        # The app reference is only used to reach the control queue, which has no injectable type.
        self._app = app
        self._sa_session = sa_session
        self._extensions = extensions
        self._cache: dict[str, Any] | None = None
        self._cache_loaded_at = 0.0
        self._lock = threading.Lock()

    def get(self, key: str, default: SettingValue = None) -> SettingValue:
        """Return the saved value for a declared key, else the input's declared default, else ``default``.

        A stored value that no longer fits its declaration is ignored and logged.
        """
        input_def = self._extensions.declared_input(key)
        if input_def is None:
            return default
        stored = self._stored_values()
        if key in stored:
            try:
                return coerce_setting_value(input_def, stored[key])
            except ValueError as e:
                log.warning("Ignoring stored admin setting %s: %s", key, e)
        if input_def.default is not None:
            return input_def.default
        return default

    def form_values(self, item: AdminExtensionFormItem) -> dict[str, SettingValue]:
        """Current value of every input of a form item, keyed by input name."""
        return {input_def.name: self.get(_key(input_def), input_def.default) for input_def in item.inputs}

    def update_form_values(
        self, item: AdminExtensionFormItem, values: dict[str, SettingValue], user: User | None
    ) -> dict[str, SettingValue]:
        """Validate and save submitted values for a form item; return the values as saved.

        Inputs missing from ``values`` are left unchanged.

        :raises RequestParameterInvalidException: if a name is not an input of the
            item or a value does not fit its declaration.
        """
        by_name = {input_def.name: input_def for input_def in item.inputs}
        unknown = sorted(set(values) - set(by_name))
        if unknown:
            raise RequestParameterInvalidException(f"Unknown form inputs: {', '.join(unknown)}")
        coerced: dict[str, SettingValue] = {}
        for name, value in values.items():
            try:
                coerced[name] = coerce_setting_value(by_name[name], value)
            except ValueError as e:
                raise RequestParameterInvalidException(str(e))
        for name, value in coerced.items():
            key = _key(by_name[name])
            row = self._sa_session.get(AdminSetting, key)
            if row is None:
                row = AdminSetting(key=key)
                self._sa_session.add(row)
            row.value = value
            row.user_id = user.id if user else None
        self._sa_session.commit()
        self._broadcast_reload()
        return self.form_values(item)

    def form_inputs(self, item: AdminExtensionFormItem) -> list[dict[str, Any]]:
        """Describe a form item's inputs, with current values, for the client's generic form component."""
        values = self.form_values(item)
        inputs = []
        for input_def in item.inputs:
            entry: dict[str, Any] = {
                "name": input_def.name,
                "type": input_def.type,
                "label": input_def.label,
                "help": input_def.help or "",
                "value": values[input_def.name],
                "optional": True,
            }
            if input_def.type == "select":
                entry["options"] = [[option, option] for option in input_def.options or []]
            if input_def.min is not None:
                entry["min"] = input_def.min
            if input_def.max is not None:
                entry["max"] = input_def.max
            inputs.append(entry)
        return inputs

    def invalidate(self) -> None:
        """Drop this process's cached values so the next read hits the database."""
        with self._lock:
            self._cache = None

    def _stored_values(self) -> dict[str, Any]:
        with self._lock:
            if self._cache is not None and time.monotonic() - self._cache_loaded_at < CACHE_TTL_SECONDS:
                return self._cache
        rows = self._sa_session.execute(select(AdminSetting.key, AdminSetting.value)).all()
        loaded = dict(rows)
        with self._lock:
            self._cache = loaded
            self._cache_loaded_at = time.monotonic()
        return loaded

    def _broadcast_reload(self) -> None:
        self.invalidate()
        queue_worker = getattr(self._app, "queue_worker", None)
        if queue_worker is None:
            return
        try:
            queue_worker.send_control_task(RELOAD_TASK, noop_self=True)
        except Exception:
            log.exception(
                "Failed to broadcast admin settings reload; other processes refresh within %ss", CACHE_TTL_SECONDS
            )


def _key(input_def: AdminExtensionFormInput) -> str:
    assert input_def.key is not None  # assigned when the extension was loaded
    return input_def.key
