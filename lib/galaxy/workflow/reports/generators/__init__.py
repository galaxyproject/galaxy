"""Module containing Galaxy workflow report generator plugins.
"""

from abc import (
    ABCMeta,
    abstractmethod,
)

from galaxy.managers import workflows
from galaxy.managers.markdown_util import (
    internal_galaxy_markdown_to_pdf,
    ready_galaxy_markdown_for_export,
    resolve_invocation_markdown,
)
from galaxy.schema import PdfDocumentType


class WorkflowReportGeneratorPlugin(metaclass=ABCMeta):
    """ """

    @property
    @abstractmethod
    def plugin_type(self):
        """Short string labelling this plugin."""

    @abstractmethod
    def generate_report_json(self, trans, invocation, runtime_report_config_json=None):
        """ """

    @abstractmethod
    def generate_report_pdf(self, trans, invocation, runtime_report_config_json=None):
        """ """


class WorkflowMarkdownGeneratorPlugin(WorkflowReportGeneratorPlugin, metaclass=ABCMeta):
    """WorkflowReportGeneratorPlugin that generates markdown as base report."""

    def generate_report_json(self, trans, invocation, runtime_report_config_json=None):
        """ """
        workflow_manager = workflows.WorkflowsManager(trans.app)
        workflow_encoded_id = trans.app.security.encode_id(invocation.workflow_id)
        workflow = workflow_manager.get_stored_accessible_workflow(trans, workflow_encoded_id, by_stored_id=False)
        internal_markdown = self._generate_internal_markdown(
            trans, invocation, runtime_report_config_json=runtime_report_config_json
        )
        export_markdown, extra_rendering_data = ready_galaxy_markdown_for_export(trans, internal_markdown)
        rval = {
            "render_format": "markdown",  # Presumably the frontend could render things other ways.
            "markdown": export_markdown,
            "invocation_markdown": export_markdown,
            "model_class": "Report",
            "id": trans.app.security.encode_id(invocation.workflow_id),
            "username": trans.user.username,
            "title": workflow.name,
        }
        rval.update(extra_rendering_data)
        return rval

    def generate_report_pdf(self, trans, invocation, runtime_report_config_json=None):
        internal_markdown = self._generate_internal_markdown(
            trans, invocation, runtime_report_config_json=runtime_report_config_json
        )
        return internal_galaxy_markdown_to_pdf(trans, internal_markdown, PdfDocumentType.invocation_report)

    @abstractmethod
    def _generate_report_markdown(self, trans, invocation, runtime_report_config_json=None):
        """ """

    def _generate_internal_markdown(self, trans, invocation, runtime_report_config_json=None):
        workflow_markdown = self._generate_report_markdown(
            trans, invocation, runtime_report_config_json=runtime_report_config_json
        )
        internal_markdown = resolve_invocation_markdown(trans, invocation, workflow_markdown)
        return internal_markdown
