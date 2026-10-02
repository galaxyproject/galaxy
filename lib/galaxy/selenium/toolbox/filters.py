from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from galaxy.tool_util.toolbox.panel import ToolSection
    from galaxy.util.bunch import Bunch


def restrict_test(context: "Bunch", section: "ToolSection") -> bool:
    """
    Disable the Test Section section

    This tool filter will disable the Test Section section.
    """
    if section.name == "Test Section":
        return False
    return True
