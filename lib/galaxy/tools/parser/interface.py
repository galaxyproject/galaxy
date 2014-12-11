from abc import ABCMeta
from abc import abstractmethod

NOT_IMPLEMENTED_MESSAGE = "Galaxy tool format does not yet support this tool feature."


class ToolSource(object):
    """ This interface represents an abstract source to parse tool
    information from.
    """
    __metaclass__ = ABCMeta
    default_is_multi_byte = False

    @abstractmethod
    def parse_id(self):
        """ Parse an ID describing the abstract tool. This is not the
        GUID tracked by the tool shed but the simple id (there may be
        multiple tools loaded in Galaxy with this same simple id).
        """

    @abstractmethod
    def parse_version(self):
        """ Parse a version describing the abstract tool.
        """

    def parse_tool_module(self):
        """ Load Tool class from a custom module. (Optional).

        If not None, return pair containing module and class (as strings).
        """
        return None

    def parse_action_module(self):
        """ Load Tool class from a custom module. (Optional).

        If not None, return pair containing module and class (as strings).
        """
        return None

    def parse_tool_type(self):
        """ Load simple tool type string (e.g. 'data_source', 'default').
        """
        return None

    @abstractmethod
    def parse_name(self):
        """ Parse a short name for tool (required). """

    @abstractmethod
    def parse_description(self):
        """ Parse a description for tool. Longer than name, shorted than help. """

    def parse_is_multi_byte(self):
        """ Parse is_multi_byte from tool - TODO: figure out what this is and
        document.
        """
        return self.default_is_multi_byte

    def parse_display_interface(self, default):
        """ Parse display_interface - fallback to default for the tool type
        (supplied as default parameter) if not specified.
        """
        return default

    def parse_require_login(self, default):
        """ Parse whether the tool requires login (as a bool).
        """
        return default

    def parse_request_param_translation_elem(self):
        """ Return an XML element describing require parameter translation.

        If we wish to support this feature for non-XML based tools this should
        be converted to return some sort of object interface instead of a RAW
        XML element.
        """
        return None

    @abstractmethod
    def parse_command(self):
        """ Return string contianing command to run.
        """

    @abstractmethod
    def parse_interpreter(self):
        """ Return string containing the interpreter to prepend to the command
        (for instance this might be 'python' to run a Python wrapper located
        adjacent to the tool).
        """

    def parse_redirect_url_params_elem(self):
        """ Return an XML element describing redirect_url_params.

        If we wish to support this feature for non-XML based tools this should
        be converted to return some sort of object interface instead of a RAW
        XML element.
        """
        return None

    def parse_version_command(self):
        """ Parse command used to determine version of primary application
        driving the tool. Return None to not generate or record such a command.
        """
        return None

    def parse_version_command_interpreter(self):
        """ Parse command used to determine version of primary application
        driving the tool. Return None to not generate or record such a command.
        """
        return None

    def parse_parallelism(self):
        """ Return a galaxy.jobs.ParallismInfo object describing task splitting
        or None.
        """
        return None

    def parse_hidden(self):
        """ Return boolean indicating whether tool should be hidden in the tool menu.
        """
        return False

    @abstractmethod
    def parse_requirements_and_containers(self):
        """ Return pair of ToolRequirement and ContainerDescription lists. """

    @abstractmethod
    def parse_input_pages(self):
        """ Return a PagesSource representing inputs by page for tool. """

    @abstractmethod
    def parse_outputs(self, tool):
        """ Return a list of ToolOutput objects.
        """

    @abstractmethod
    def parse_stdio(self):
        """ Builds lists of ToolStdioExitCode and ToolStdioRegex objects
        to describe tool execution error conditions.
        """
        return [], []

    def parse_tests_to_dict(self):
        return {'tests': []}


class PagesSource(object):
    """ Contains a list of Pages - each a list of InputSources -
    each item in the outer list representing a page of inputs.
    Pages are deprecated so ideally this outer list will always
    be exactly a singleton.
    """
    def __init__(self, page_sources):
        self.page_sources = page_sources

    @property
    def inputs_defined(self):
        return True


class PageSource(object):
    __metaclass__ = ABCMeta

    def parse_display(self):
        return None

    @abstractmethod
    def parse_input_sources(self):
        """ Return a list of InputSource objects. """


class InputSource(object):
    __metaclass__ = ABCMeta
    default_optional = False

    def elem(self):
        # For things in transition that still depend on XML - provide a way
        # to grab it and just throw an error if feature is attempted to be
        # used with other tool sources.
        raise NotImplementedError(NOT_IMPLEMENTED_MESSAGE)

    @abstractmethod
    def get(self, key, value=None):
        """ Return simple named properties as string for this input source.
        keys to be supported depend on the parameter type.
        """

    @abstractmethod
    def get_bool(self, key, default):
        """ Return simple named properties as boolean for this input source.
        keys to be supported depend on the parameter type.
        """

    def parse_label(self):
        return self.get("label")

    def parse_help(self):
        return self.get("label")

    def parse_sanitizer_elem(self):
        """ Return an XML description of sanitizers. This is a stop gap
        until we can rework galaxy.tools.parameters.sanitize to not
        explicitly depend on XML.
        """
        return None

    def parse_validator_elems(self):
        """ Return an XML description of sanitizers. This is a stop gap
        until we can rework galaxy.tools.parameters.validation to not
        explicitly depend on XML.
        """
        return []

    def parse_optional(self, default=None):
        """ Return boolean indicating wheter parameter is optional. """
        if default is None:
            default = self.default_optional
        return self.get_bool( "optional", default )

    def parse_dynamic_options(self, param):
        """ Return a galaxy.tools.parameters.dynamic_options.DynamicOptions
        if appropriate.
        """
        return None

    def parse_static_options(self):
        """ Return list of static options if this is a select type without
        defining a dynamic options.
        """
        return []

    def parse_conversion_tuples(self):
        """ Return list of (name, extension) to describe explicit conversions.
        """
        return []

    def parse_nested_inputs_source(self):
        # For repeats
        raise NotImplementedError(NOT_IMPLEMENTED_MESSAGE)

    def parse_test_input_source(self):
        # For conditionals
        raise NotImplementedError(NOT_IMPLEMENTED_MESSAGE)

    def parse_when_input_sources(self):
        raise NotImplementedError(NOT_IMPLEMENTED_MESSAGE)
