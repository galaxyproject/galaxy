"""Module containing Galaxy workflow report generator plugins.
"""
from abc import (
    ABCMeta,
    abstractmethod
)

import six

from galaxy.managers.markdown_util import (
    ready_galaxy_markdown_for_export,
    resolve_invocation_markdown,
)


@six.add_metaclass(ABCMeta)
class WorkflowReportGeneratorPlugin(object):
    """
    """

    @property
    @abstractmethod
    def plugin_type(self):
        """Short string labelling this plugin."""

    @abstractmethod
    def generate_report_json(self, trans, invocation, runtime_report_config_json=None):
        """
        """

    @abstractmethod
    def generate_report_pdf(self, trans, invocation, runtime_report_config_json=None):
        """
        """


@six.add_metaclass(ABCMeta)
class WorkflowMarkdownGeneratorPlugin(WorkflowReportGeneratorPlugin):
    """WorkflowReportGeneratorPlugin that generates markdown as base report."""

    def generate_report_json(self, trans, invocation, runtime_report_config_json=None):
        """
        """
        workflow_markdown = self._generate_report_markdown(trans, invocation, runtime_report_config_json=runtime_report_config_json)
        internal_markdown = resolve_invocation_markdown(trans, invocation, workflow_markdown)
        export_markdown, extra_rendering_data = ready_galaxy_markdown_for_export(trans, internal_markdown)
        rval = {
            "render_format": "markdown",  # Presumably the frontend could render things other ways.
            "markdown": export_markdown,
            "invocation_markdown": workflow_markdown,
        }
        rval.update(extra_rendering_data)
        return rval

    def generate_report_pdf(self, trans, invocation, runtime_report_config_json=None):
        # TODO: translate markdown to a PDF
        raise NotImplementedError()

    @abstractmethod
    def _generate_report_markdown(self, trans, invocation, runtime_report_config_json=None):
        """ """
