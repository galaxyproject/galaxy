import logging
import os

from galaxy.model_tools import MODEL_TOOLS_PATH

log = logging.getLogger(__name__)

SPECIAL_TOOLS = {
    "history export": "imp_exp/exp_history_to_archive.xml",
    "history import": "imp_exp/imp_history_from_archive.xml",
    "data fetch": "data_fetch.xml",
}


def load_lib_tools(toolbox):
    for name, path in SPECIAL_TOOLS.items():
        tool = toolbox.load_hidden_lib_tool(os.path.abspath(os.path.join(MODEL_TOOLS_PATH, path)))
        log.debug("Loaded %s tool: %s", name, tool.id)
