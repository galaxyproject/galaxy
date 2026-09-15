"""App-independent base class for Galaxy tools.

Mirrors the ``AbstractToolBox``/``ToolBox`` split in :mod:`galaxy.tool_util.toolbox`:
``AbstractTool`` holds the subset of ``galaxy.tools.Tool`` behaviour (parsing,
metadata, simple lookups) that does not depend on a Galaxy application context,
so it can be referenced from lower-level packages without a circular dependency
on ``galaxy-app``.
"""

from typing import (
    Any,
    NamedTuple,
    TYPE_CHECKING,
)

from galaxy.tool_util.loader import (
    imported_macro_paths,
    raw_tool_xml_tree,
)
from galaxy.tool_util.parser import ToolOutputCollectionPart
from galaxy.tool_util.version import parse_version
from galaxy.util import string_as_bool
from galaxy.util.template import fill_template

if TYPE_CHECKING:
    from packaging.version import Version

    from galaxy.tool_util.parser.interface import ToolSource
    from galaxy.tool_util.parser.output_objects import (
        ToolOutputBase,
        ToolOutputCollection,
    )
    from galaxy.tool_util.parser.stdio import (
        ToolStdioExitCode,
        ToolStdioRegex,
    )
    from galaxy.tool_util.version import LegacyVersion
    from galaxy.util.path import StrPath


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
    name: str
    version: str
    tool_type: str
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

        # TODO: Anyway to capture tools that dynamically change their own
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
