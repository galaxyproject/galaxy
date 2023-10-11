import logging

import galaxy.tools
from galaxy.tool_shed.util.tool_util import (
    copy_sample_file,
    copy_sample_files,
    generate_message_for_invalid_tools,
)
from galaxy.util.expressions import ExpressionContext

log = logging.getLogger(__name__)


def new_state(trans, tool, invalid=False):
    """Create a new `DefaultToolState` for the received tool.  Only inputs on the first page will be initialized."""
    state = galaxy.tools.DefaultToolState()
    state.inputs = {}
    if invalid:
        # We're attempting to display a tool in the tool shed that has been determined to have errors, so is invalid.
        return state
    try:
        # Attempt to generate the tool state using the standard Galaxy-side code
        return tool.new_state(trans)
    except Exception as e:
        # Fall back to building tool state as below
        log.debug(
            'Failed to build tool state for tool "%s" using standard method, will try to fall back on custom method: %s',
            tool.id,
            e,
        )
    inputs = tool.inputs_by_page[0]
    context = ExpressionContext(state.inputs, parent=None)
    for input in inputs.values():
        try:
            state.inputs[input.name] = input.get_initial_value(trans, context)
        except Exception:
            # FIXME: not all values should be an empty list
            state.inputs[input.name] = []
    return state


__all__ = (
    "copy_sample_file",
    "copy_sample_files",
    "generate_message_for_invalid_tools",
    "new_state",
)
