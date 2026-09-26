"""App-independent base class for Galaxy tools.

Mirrors the ``AbstractToolBox``/``ToolBox`` split in :mod:`galaxy.tool_util.toolbox`:
``AbstractTool`` holds the subset of ``galaxy.tools.Tool`` behaviour (parsing,
metadata, simple lookups) that does not depend on a Galaxy application context,
so it can be referenced from lower-level packages without a circular dependency
on ``galaxy-app``.
"""

import itertools
import json
import logging
import os
from collections.abc import Sequence
from pathlib import Path
from typing import (
    Any,
    NamedTuple,
    TYPE_CHECKING,
)

from packaging.version import Version

from galaxy.tool_util.loader import (
    imported_macro_paths,
    raw_tool_xml_tree,
)
from galaxy.tool_util.model_factory import parse_tool
from galaxy.tool_util.ontologies.ontology_data import biotools_reference
from galaxy.tool_util.parser import (
    get_tool_source,
    ToolOutputCollectionPart,
)
from galaxy.tool_util.parser.output_objects import (
    ToolExpressionOutput,
    ToolOutput,
    ToolOutputCollection,
)
from galaxy.tool_util.verify.parse import parse_tool_test_descriptions
from galaxy.tool_util.version import parse_version
from galaxy.util import (
    parse_xml_string_to_etree,
    rst_to_html,
    string_as_bool,
)
from galaxy.util.template import (
    fill_template,
    refactoring_tool,
)

if TYPE_CHECKING:
    from galaxy.tool_util.deps.requirements import ToolRequirements
    from galaxy.tool_util.parser.interface import ToolSource
    from galaxy.tool_util.parser.output_objects import ToolOutputBase
    from galaxy.tool_util.parser.stdio import (
        ToolStdioExitCode,
        ToolStdioRegex,
    )
    from galaxy.tool_util.toolbox.lineages.interface import ToolLineage
    from galaxy.tool_util.version import LegacyVersion
    from galaxy.tool_util_models import ParsedTool
    from galaxy.tool_util_models.parameters import ToolParameterT
    from galaxy.tool_util_models.tool_source import (
        FileSourceConfigFile,
        HelpContent,
        InputConfigFile,
        TemplateConfigFile,
        XrefDict,
    )
    from galaxy.util.path import StrPath


log = logging.getLogger(__name__)


class RawToolSource(NamedTuple):
    """Compact representation of a tool's raw source for transport/serialization.

    Attributes:
        raw_tool_source: String form of the tool source (typically XML or YAML).
        tool_source_class: The class name of the ToolSource implementation (e.g., 'XmlToolSource').
    """

    raw_tool_source: str
    tool_source_class: str


def parse_tool_version_for_comparison(version: str) -> "LegacyVersion | Version":
    """Parse Galaxy's numeric ``+galaxyN`` suffix as a PEP 440 version."""
    suffix_marker = "+galaxy"
    if suffix_marker in version:
        base, suffix = version.split(suffix_marker, 1)
        if suffix:
            version = f"{base}{suffix_marker}.{suffix.lstrip('.')}"
    return parse_version(version)


class AbstractTool:
    """
    App-independent surface of a Galaxy tool: parsing, metadata, and simple
    lookups over already-parsed instance state. Application-level concerns
    (jobs, database, security) live on ``galaxy.tools.Tool`` instead.
    """

    tool_source: "ToolSource"
    id: str | None
    old_id: str | None
    name: str
    version: str
    profile: float
    tool_type: str
    hidden: bool
    tool_dir: "StrPath | None"
    command: str | None
    interpreter: str | None
    shell_command: str | None
    base_command: list[str] | None
    arguments: list[str] | None
    stdio_exit_codes: "list[ToolStdioExitCode]"
    stdio_regexes: "list[ToolStdioRegex]"
    inputs: dict[str, Any]
    outputs: "dict[str, ToolOutputBase]"
    output_collections: "dict[str, ToolOutputCollection]"
    has_multiple_pages: bool
    code_namespace: dict[str, Any]
    hook_map: dict[str, str]
    redirect_url_params: str | None
    dynamic_tool_id: int | None
    python_template_version: Version | None
    _allow_code_files: bool
    _lineage: "ToolLineage | None"
    is_workflow_compatible: bool
    tool_shed: str | None
    repository_name: str | None
    installed_changeset_revision: str | None
    raw_help: "HelpContent | None"
    xrefs: "list[XrefDict]"
    config_files: "Sequence[TemplateConfigFile | InputConfigFile | FileSourceConfigFile]"
    requirements: "ToolRequirements"
    parameters: "list[ToolParameterT] | None"
    _tests: str | None
    _tests_parsed: bool

    @property
    def version_object(self) -> "LegacyVersion | Version":
        """Parse version string, handling special Galaxy version format."""
        return parse_tool_version_for_comparison(self.version)

    def to_raw_tool_source(self) -> RawToolSource:
        """Return a compact representation of this tool's source for external processing.

        Provides both the raw tool source string and the concrete ToolSource class name.
        """
        return RawToolSource(
            raw_tool_source=self.tool_source.to_string(),
            tool_source_class=type(self.tool_source).__name__,
        )

    def parsed_tool(self) -> "ParsedTool":
        """Return a ParsedTool model for this tool.

        After tool loading, mem_optimize destroys the XML tree to save memory.
        When that has happened, re-parse from the stored string representation.
        """
        tool_source = self.tool_source
        if getattr(tool_source, "root", None) is None:
            tool_source = get_tool_source(xml_tree=parse_xml_string_to_etree(tool_source.to_string()))
        return parse_tool(tool_source)

    @property
    def lineage(self) -> "ToolLineage | None":
        """Return ToolLineage for this tool."""
        return self._lineage

    @property
    def tool_versions(self) -> list[str]:
        # If we have versions, return them.
        if self.lineage:
            return list(self.lineage.tool_versions)
        else:
            return []

    @property
    def is_latest_version(self) -> bool:
        tool_versions = self.tool_versions
        return not tool_versions or self.version == tool_versions[-1]

    @property
    def produces_collections_with_unknown_structure(self) -> bool:
        def output_is_dynamic(output: "ToolOutputBase") -> bool:
            if not isinstance(output, ToolOutputCollection):
                return False
            return output.dynamic_structure

        return any(map(output_is_dynamic, self.outputs.values()))

    def _parse_legacy_features(self, tool_source: "ToolSource") -> None:
        self.code_namespace = {}
        self.hook_map = {}

        if not hasattr(tool_source, "root"):
            return

        # TODO: Move following logic into XmlToolSource.
        root = tool_source.root
        # Load any tool specific code (optional) Edit: INS 5/29/2007,
        # allow code files to have access to the individual tool's
        # "module" if it has one.  Allows us to reuse code files, etc.
        for code_elem in root.findall("code"):
            for hook_elem in code_elem.findall("hook"):
                for key, value in hook_elem.items():
                    # map hook to function
                    self.hook_map[key] = value
            file_name = code_elem.get("file")
            assert self.tool_dir is not None
            code_path = os.path.join(self.tool_dir, file_name)
            if self._allow_code_files:
                with open(code_path) as f:
                    code_string = f.read()
                try:
                    compiled_code = compile(code_string, code_path, "exec")
                    exec(compiled_code, self.code_namespace)
                except Exception:
                    if (
                        refactoring_tool
                        and self.python_template_version
                        and self.python_template_version.release[0] < 3
                    ):
                        # Could be a code file that uses python 2 syntax
                        translated_code = str(
                            refactoring_tool.refactor_string(code_string, name="auto_translated_code_file")
                        )
                        compiled_code = compile(translated_code, f"futurized_{code_path}", "exec")
                        exec(compiled_code, self.code_namespace)
                    else:
                        raise

    def _parse_config_files(self, tool_source: "ToolSource") -> None:
        self.config_files = []

        self.config_files.extend(tool_source.parse_input_configfiles())
        self.config_files.extend(tool_source.parse_template_configfiles())
        self.config_files.extend(tool_source.parse_file_sources())

    def parse_tests(self) -> None:
        self._tests_parsed = True
        source = self.tool_source
        # ``Tool.__init__`` calls ``tool_source.mem_optimize()`` after parsing,
        # which frees an ``XmlToolSource``'s element tree (``root`` becomes
        # ``None``). A deferred test parse therefore rebuilds the source from
        # its retained string — the same round-trip a stored tool source uses.
        # Non-XML sources have no ``root`` and keep their data, so they parse
        # directly.
        if getattr(source, "root", False) is None:
            try:
                source = get_tool_source(raw_tool_source=source.to_string(), tool_source_class=type(source).__name__)
            except Exception:
                self._tests = None
                log.exception("Failed to rebuild tool source for deferred test parsing of '%s'", self.id)
                return
        test_descriptions = parse_tool_test_descriptions(source, self.id, self.parameters)
        try:
            self._tests = json.dumps([t.to_dict() for t in test_descriptions], indent=None)
        except Exception:
            self._tests = None
            log.exception("Failed to parse tool tests for tool '%s'", self.id)

    @property
    def _repository_dir(self) -> str | None:
        """If tool shed installed tool, the base directory of the repository installed."""
        if self.tool_shed:
            assert self.tool_dir is not None
            tool_dir = Path(self.tool_dir)
            for repo_dir in itertools.chain([tool_dir], tool_dir.parents):
                if repo_dir.name == self.repository_name and repo_dir.parent.name == self.installed_changeset_revision:
                    return str(repo_dir)
            else:
                log.error(f"Problem finding repository dir for tool '{self.id}'")

        return None

    @property
    def allows_external_output_paths(self) -> bool:
        return self.old_id == "__DATA_FETCH__" and self.dynamic_tool_id is None

    def _uses_tool_provided_metadata(self, tool_source: "ToolSource") -> bool:
        if not tool_source.allows_tool_provided_metadata():
            return False
        if self.old_id in ("upload1", "__DATA_FETCH__") or tool_source.parse_provided_metadata_is_explicit():
            return True

        def output_uses_tool_provided_metadata(output: "ToolOutputBase") -> bool:
            if isinstance(output, ToolOutputCollection):
                if any(
                    description.discover_via == "tool_provided_metadata"
                    for description in output.structure.dataset_collector_descriptions or []
                ):
                    return True
                return any(output_uses_tool_provided_metadata(child) for child in output.outputs.values())

            assert isinstance(output, (ToolOutput, ToolExpressionOutput))
            if output.format == "auto":
                return True
            return any(
                description.discover_via == "tool_provided_metadata"
                for description in output.dataset_collector_descriptions
            )

        if any(output_uses_tool_provided_metadata(output) for output in self.outputs.values()):
            return True

        return not (self.tool_type == "interactive" or Version(str(self.profile)) >= Version("26.2"))

    @property
    def help_html(self) -> str:
        """Returns the help content converted from RST to HTML (without variable substitution)."""
        help_content = self.raw_help
        assert help_content
        assert help_content.format == "restructuredtext"
        try:
            return rst_to_html(help_content.content)
        except Exception:
            log.warning("Exception while parsing help for tool with id '%s'", self.id, exc_info=True)
            return ""

    def render_help(self, static_path: str, host_url: str) -> str:
        """Renders the help HTML with variable substitution for static_path and host_url."""
        help_html = self.help_html
        # Replace Mako-style variables with actual values
        help_html = help_html.replace("${static_path}", static_path)
        help_html = help_html.replace("${host_url}", host_url)
        return help_html

    @property
    def biotools_reference(self) -> str | None:
        """Return a bio.tools ID if external reference to it is found.

        If multiple bio.tools references are found, return just the first one.
        """
        return biotools_reference(self.xrefs)

    def parse_command(self, tool_source: "ToolSource") -> None:
        """ """
        # Command line (template). Optional for tools that do not invoke a local program
        if (command := tool_source.parse_command()) is not None:
            self.command = command.lstrip()  # get rid of leading whitespace
            # Must pre-pend this AFTER processing the cheetah command template
            self.interpreter = tool_source.parse_interpreter()
        else:
            self.command = ""
            self.interpreter = None

    def parse_shell_command(self, tool_source: "ToolSource") -> None:
        self.shell_command = tool_source.parse_shell_command()

    def parse_base_command(self, tool_source: "ToolSource") -> None:
        self.base_command = tool_source.parse_base_command()

    def parse_arguments(self, tool_source: "ToolSource") -> None:
        self.arguments = tool_source.parse_arguments()

    def parse_environment_variables(self, tool_source: "ToolSource") -> list[dict[str, Any]]:
        return tool_source.parse_environment_variables()

    # TODO: Include the tool's name in any parsing warnings.
    def parse_stdio(self, tool_source: "ToolSource") -> None:
        """
        Parse <stdio> element(s) and fill in self.return_codes,
        self.stderr_rules, and self.stdout_rules. Return codes have a range
        and an error type (fault or warning).  Stderr and stdout rules have
        a regular expression and an error level (fault or warning).
        """
        exit_codes, regexes = tool_source.parse_stdio()
        self.stdio_exit_codes = exit_codes
        self.stdio_regexes = regexes

    def find_output_def(self, name: str) -> "ToolOutputBase | None":
        # name is JobToOutputDatasetAssociation name.
        # TODO: to defensive, just throw IndexError and catch somewhere
        # up that stack.
        if ToolOutputCollectionPart.is_named_collection_part_name(name):
            collection_name, part = ToolOutputCollectionPart.split_output_name(name)
            collection_def = self.output_collections.get(collection_name, None)
            if not collection_def:
                return None
            return collection_def.outputs.get(part, None)
        else:
            return self.outputs.get(name, None)

    @property
    def output_discover_patterns(self) -> list[str]:
        # patterns to collect for remote job execution
        patterns = []
        for output in self.outputs.values():
            patterns.extend(output.output_discover_patterns)
        return patterns

    @property
    def tool_requirements(self) -> "ToolRequirements":
        """
        Return all requirements of type package
        """
        return self.requirements.packages

    def check_workflow_compatible(self, tool_source: "ToolSource") -> bool:
        """
        Determine if a tool can be used in workflows. External tools and the
        upload tool are currently not supported by workflows.
        """
        # Multiple page tools are not supported -- we're eliminating most
        # of these anyway
        if self.has_multiple_pages:
            return False
        # This is probably the best bet for detecting external web tools
        # right now
        if self.tool_type.startswith("data_source"):
            return False

        if hasattr(tool_source, "root"):
            root = tool_source.root
            if not string_as_bool(root.get("workflow_compatible", "True")):
                return False

        # TODO: Any way to capture tools that dynamically change their own
        #       outputs?
        return True

    def get_param(self, key: str) -> Any:
        """
        Returns the parameter named `key` or None if there is no such
        parameter.
        """
        return self.inputs.get(key, None)

    def get_hook(self, name: str) -> Any:
        """
        Returns an object from the code file referenced by `code_namespace`
        (this will normally be a callable object)
        """
        if self.code_namespace:
            # Try to look up hook in self.hook_map, otherwise resort to default
            if name in self.hook_map and self.hook_map[name] in self.code_namespace:
                return self.code_namespace[self.hook_map[name]]
            elif name in self.code_namespace:
                return self.code_namespace[name]
        return None

    def call_hook(self, hook_name: str, *args: Any, **kwargs: Any) -> Any:
        """
        Call the custom code hook function identified by 'hook_name' if any,
        and return the results
        """
        try:
            code = self.get_hook(hook_name)
            if code:
                return code(*args, **kwargs)
        except Exception as e:
            original_message = ""
            if len(e.args):
                original_message = e.args[0]
            e.args = (f"Error in '{self.name}' hook '{hook_name}', original message: {original_message}",)
            raise

    def build_redirect_url_params(self, param_dict: dict[str, Any]) -> str | None:
        """
        Substitute parameter values into self.redirect_url_params
        """
        if not self.redirect_url_params:
            return None
        # Substituting parameter values into the url params
        redirect_url_params = fill_template(self.redirect_url_params, context=param_dict)
        # Remove newlines
        redirect_url_params = redirect_url_params.replace("\n", " ").replace("\r", " ")
        return redirect_url_params

    @classmethod
    def get_externally_referenced_paths(cls, path: "StrPath") -> list[str]:
        """Return relative paths to externally referenced files by the tool
        described by file at `path`. External components should not assume things
        about the structure of tool xml files (this is the tool's responsibility).
        """
        tree = raw_tool_xml_tree(path)
        root = tree.getroot()
        external_paths = []
        for code_elem in root.findall("code"):
            external_path = code_elem.get("file")
            if external_path:
                external_paths.append(external_path)
        external_paths.extend(imported_macro_paths(root))
        # May also need to load external citation files as well at some point.
        return external_paths
