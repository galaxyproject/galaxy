"""Linter for CWL tools."""

from typing import TYPE_CHECKING

lint_tool_types = ["cwl"]

from galaxy.tool_util.cwl.schema import schema_loader
from galaxy.tool_util.lint import Linter

if TYPE_CHECKING:
    from galaxy.tool_util.lint import LintContext
    from galaxy.tool_util.parser import ToolSource


class CWLValid(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        raw_reference = schema_loader.raw_process_reference(tool_source.source_path)
        try:
            schema_loader.process_definition(raw_reference)
        except Exception:
            return
        lint_ctx.info("CWL appears to be valid.", linter=cls.name())


class CWLInValid(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        raw_reference = schema_loader.raw_process_reference(tool_source.source_path)
        try:
            schema_loader.process_definition(raw_reference)
        except Exception as e:
            lint_ctx.error(f"Failed to valdiate CWL artifact: {e}", linter=cls.name())


class CWLVersionMissing(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        raw_reference = schema_loader.raw_process_reference(tool_source.source_path)
        cwl_version = raw_reference.process_object.get("cwlVersion", None)
        if cwl_version is None:
            lint_ctx.error("CWL file does not contain a 'cwlVersion'", linter=cls.name())


class CWLVersionUnknown(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        raw_reference = schema_loader.raw_process_reference(tool_source.source_path)
        cwl_version = raw_reference.process_object.get("cwlVersion", None)
        if cwl_version not in ["v1.0"]:
            lint_ctx.warn(f"CWL version [{cwl_version}] is unknown, we recommend the v1.0 the stable release.", linter=cls.name())


class CWLVersionGood(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        raw_reference = schema_loader.raw_process_reference(tool_source.source_path)
        cwl_version = raw_reference.process_object.get("cwlVersion", None)
        if cwl_version in ["v1.0"]:
            lint_ctx.info(f"Modern CWL version [{cwl_version}].", linter=cls.name())


class CWLDockerMissing(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        _, containers, *_ = tool_source.parse_requirements_and_containers()
        if len(containers) == 0:
            lint_ctx.warn("Tool does not specify a DockerPull source.", linter=cls.name())


class CWLDockerGood(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        _, containers, *_ = tool_source.parse_requirements_and_containers()
        if len(containers) > 0:
            identifier = containers[0].identifier
            lint_ctx.info(f"Tool will run in Docker image [{identifier}].", linter=cls.name())


class CWLDescriptionMissing(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        help = tool_source.parse_help()
        if not help:
            lint_ctx.warn("Description of tool is empty or absent.", linter=cls.name())


class CWLHelpTODO(Linter):
    @classmethod
    def lint(cls, tool_source: "ToolSource", lint_ctx: "LintContext"):
        help = tool_source.parse_help()
        if help and "TODO" in help.content:
            lint_ctx.warn("Help contains TODO text.", linter=cls.name())
