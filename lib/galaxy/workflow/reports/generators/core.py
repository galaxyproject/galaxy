"""The class defines the default stock Galaxy workflow reporting plugin
"""
import logging
import string

from ..generators import WorkflowMarkdownGeneratorPlugin

log = logging.getLogger(__name__)

DEFAULT_SECTIONS = [{"type": "inputs"}, {"type": "qc"}, {"type": "outputs"}, {"type": "workflow"}]


class CoreWorkflowMarkdownReportGeneratorPlugin(WorkflowMarkdownGeneratorPlugin):
    plugin_type = "core"

    def _generate_report_markdown(self, trans, invocation, runtime_report_config_json=None):
        reports_config = (invocation.workflow.reports_config or {}).copy()
        # TODO: more intelligent merge here.
        reports_config.update(runtime_report_config_json or {})
        title = reports_config.get("title", "Workflow Execution Summary of %s" % invocation.workflow.stored_workflow.name)
        template_kwds = {"title": title}
        report_markdown = """# ${title}\n"""

        def title_section_line(section, default):
            title = section.get("title", default)
            if title is not None:
                return "## %s\n" % title
            else:
                return ''

        def generate_section(section):
            section_type = section.get("type")
            section_markdown = ""
            if section_type == "outputs":
                section_markdown += title_section_line(section, "Workflow Outputs")
                for output_assoc in invocation.output_associations:
                    if not output_assoc.workflow_output.label:
                        continue

                    if output_assoc.history_content_type == "dataset":
                        section_markdown += """#### Output Dataset: %s
::: history_dataset_display output=%s
:::
""" % (output_assoc.workflow_output.label, output_assoc.workflow_output.label)
                    else:
                        section_markdown += """#### Output Dataset Collection: %s
::: history_dataset_collection_display output=%s
:::
""" % (output_assoc.workflow_output.label)
            elif section_type == "qc":
                section_markdown += title_section_line(section, "QC")
                section_markdown += "**Not yet implemented...**\n"
            elif section_type == "inputs":
                section_markdown += title_section_line(section, "Workflow Inputs")
                for input_assoc in invocation.input_associations:
                    if not input_assoc.workflow_step.label:
                        continue

                    if input_assoc.history_content_type == "dataset":
                        section_markdown += """#### Input Dataset: %s
::: history_dataset_display input=%s
:::
""" % (input_assoc.workflow_step.label, input_assoc.workflow_step.label)
                    else:
                        section_markdown += """#### Input Dataset Collection: %s
::: history_dataset_collection_display input=%s
:::
""" % (input_assoc.workflow_step.label, input_assoc.workflow_step.label)
            elif section_type == "workflow":
                section_markdown += title_section_line(section, "Workflow")
                section_markdown += "::: workflow_display\n:::\n"
            elif section_type == "free_markdown":
                content = section.get("content")
                section_markdown += title_section_line(section, None)
                section_markdown += content
            return section_markdown

        sections = reports_config.get("sections", DEFAULT_SECTIONS)
        for section in sections:
            report_markdown += generate_section(section)

        report_markdown = string.Template(report_markdown).safe_substitute(**template_kwds)
        return report_markdown


__all__ = ('CoreWorkflowMarkdownReportGeneratorPlugin', )
