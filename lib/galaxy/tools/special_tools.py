import logging
import os

log = logging.getLogger(__name__)

# Tool files Galaxy's ``load_lib_tools`` loads after the normal config walk.
# Paths are relative to this file's directory (``lib/galaxy/tools/``).
SPECIAL_TOOLS = {
    "history export": "imp_exp/exp_history_to_archive.xml",
    "history export to uri": "imp_exp/exp_history_to_uri.xml",
    "history import": "imp_exp/imp_history_from_archive.xml",
    "data fetch": "data_fetch.xml",
}

# ``set_metadata_tool`` is loaded separately by
# ``datatypes_registry.load_external_metadata_tool``. Listed here so the
# populator (via ``hidden_lib_tool_paths``) indexes it alongside the
# config-discovered tools — without it, ``LazyToolBox.create_tool`` would
# raise on the post-boot ``load_hidden_lib_tool`` call.
_EXTRA_HIDDEN_LIB_TOOLS = {
    "set metadata": "../datatypes/set_metadata_tool.xml",
}


def hidden_lib_tool_paths() -> list[str]:
    """Absolute paths of every Galaxy-internal "hidden lib" tool.

    Used by :func:`galaxy.tools.source_store.discover.discover_tools` so the
    populator indexes these tools alongside the conf-discovered ones. The
    eager ``load_hidden_lib_tool`` calls that run after boot then resolve
    through ``LazyToolBox.create_tool``'s index lookup — the seam stays
    strict (raise on miss).
    """
    base = os.path.dirname(__file__)
    return [
        os.path.abspath(os.path.join(base, p)) for p in (*SPECIAL_TOOLS.values(), *_EXTRA_HIDDEN_LIB_TOOLS.values())
    ]


def load_lib_tools(toolbox):
    base = os.path.dirname(__file__)
    for name, path in SPECIAL_TOOLS.items():
        tool = toolbox.load_hidden_lib_tool(os.path.abspath(os.path.join(base, path)))
        log.debug("Loaded %s tool: %s", name, tool.id)
