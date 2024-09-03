"""The class defines the default stock Galaxy workflow reporting plugin
"""

import logging
import string

from . import WorkflowMarkdownGeneratorPlugin

log = logging.getLogger(__name__)

DEFAULT_MARKDOWN = """
# ${title}

## Workflow Inputs
```galaxy
invocation_inputs()
```

## Workflow Outputs
```galaxy
invocation_outputs()
```

## Workflow
```galaxy
workflow_display()
```
"""


class MarkdownWorkflowMarkdownReportGeneratorPlugin(WorkflowMarkdownGeneratorPlugin):
    plugin_type = "markdown"

    def _generate_report_markdown(self, trans, invocation, runtime_report_config_json=None):
        reports_config = (invocation.workflow.reports_config or {}).copy()
        # TODO: more intelligent merge here.
        reports_config.update(runtime_report_config_json or {})
        title = reports_config.get("title", f"Workflow Execution Summary of {invocation.workflow.stored_workflow.name}")
        markdown = reports_config.get("markdown")
        if markdown is None:
            template_kwds = {"title": title}
            markdown = string.Template(DEFAULT_MARKDOWN).safe_substitute(**template_kwds)

        return markdown


__all__ = ("MarkdownWorkflowMarkdownReportGeneratorPlugin",)
