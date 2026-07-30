import logging
import sys
from copy import deepcopy
from typing import (
    Protocol,
    runtime_checkable,
    TYPE_CHECKING,
)

from galaxy.util import listify

if TYPE_CHECKING:
    from galaxy.managers.context import ProvidesUserContext

log = logging.getLogger(__name__)


@runtime_checkable
class ToolFilterContext(Protocol):
    """The attribute surface that toolbox filters are allowed to read.

    ``galaxy.tools.Tool`` implements this protocol, and any lighter-weight
    stand-in a toolbox implementation hands to the filter layer must too.
    Admin / user-configured filter functions should only read fields
    documented here — it is the contract that lets the filter pass run
    against something cheaper than a fully-parsed ``Tool``.
    """

    id: str
    name: str
    description: str
    hidden: bool
    require_login: bool
    tool_type: str
    labels: list[str]
    tags: list[str]

    def allow_user_access(self, user, attempting_access: bool = True) -> bool:
        """Return ``True`` if ``user`` may see/run this tool.

        ``Tool`` implements this directly (with subclass overrides for
        admin-only flavours like ``DataManagerTool``); implementations
        should answer from their own state so the filter layer never
        needs to reach through ``context.trans.app.config``.
        """
        ...


class FilterFactory:
    """
    An instance of this class is responsible for filtering the list
    of tools presented to a given user in a given context.
    """

    def __init__(self, toolbox):
        self.toolbox = toolbox

        # Prepopulate dict containing filters that are always checked,
        # other filters that get checked depending on context.
        self.default_filters = dict(tool=[_not_hidden, _handle_authorization], section=[], label=[])
        # Add dynamic filters to these default filters.
        config = toolbox.app.config
        self.__base_modules = listify(
            getattr(config, "toolbox_filter_base_modules", "galaxy.tool_util.toolbox.filters")
        )
        self.__init_filters("tool", getattr(config, "tool_filters", ""), self.default_filters)
        self.__init_filters("section", getattr(config, "tool_section_filters", ""), self.default_filters)
        self.__init_filters("label", getattr(config, "tool_label_filters", ""), self.default_filters)

    def build_filters(self, trans: "ProvidesUserContext", **kwds):
        """
        Build list of filters to check tools against given current context.
        """
        filters = deepcopy(self.default_filters)
        if trans.user:
            for name, value in trans.user.preferences.items():
                if value and value.strip():
                    user_filters = listify(value, do_strip=True)
                    category = ""
                    if name == "toolbox_tool_filters":
                        category = "tool"
                    elif name == "toolbox_section_filters":
                        category = "section"
                    elif name == "toolbox_label_filters":
                        category = "label"
                    if category:
                        validate = getattr(trans.app.config, f"user_tool_{category}_filters", [])
                        self.__init_filters(category, user_filters, filters, validate=validate)

        return filters

    def __init_filters(self, key, filters, toolbox_filters, validate=None):
        for filter in filters:
            if validate is None or filter in validate or filter in self.default_filters:
                filter_function = self.build_filter_function(filter)
                if filter_function is not None:
                    toolbox_filters[key].append(filter_function)
            else:
                log.warning("Refusing to load %s filter '%s' which is not defined in config", key, filter)
        return toolbox_filters

    def build_filter_function(self, filter_name):
        """Obtain python function (importing a submodule if needed)
        corresponding to filter_name.
        """
        if ":" in filter_name:
            # Should be a submodule of filters (e.g. examples:restrict_development_tools)
            module_name, function_name = filter_name.rsplit(":", 1)
            function = self._import_filter(module_name, function_name)
        else:
            # No module found, just load a function from this file or
            # one that has be explicitly imported.
            function = globals()[filter_name.strip()]
        return function

    def _import_filter(self, module_name, function_name):
        function_name = function_name.strip()
        for base_module in self.__base_modules:
            full_module_name = f"{base_module}.{module_name.strip()}"
            try:
                __import__(full_module_name)
            except ImportError:
                continue
            module = sys.modules[full_module_name]
            if hasattr(module, function_name):
                return getattr(module, function_name)
        log.warning("Failed to load module for '%s.%s'.", module_name, function_name, exc_info=True)


# Stock Filter Functions
def _not_hidden(context, tool: ToolFilterContext) -> bool:
    return not tool.hidden


def _handle_authorization(context, tool: ToolFilterContext) -> bool:
    user = context.trans.user
    if tool.require_login and not user:
        return False
    if not tool.allow_user_access(user, attempting_access=False):
        return False
    return True
