from .cwltool_deps import (
    needs_shell_quoting,
    shellescape,
)
from .parser import tool_proxy
from .parser import workflow_proxy
from .representation import to_cwl_job, to_galaxy_parameters
from .runtime_actions import handle_outputs


__all__ = [
    'tool_proxy',
    'workflow_proxy',
    'handle_outputs',
    'to_cwl_job',
    'to_galaxy_parameters',
    'needs_shell_quoting',
    'shellescape',
]
