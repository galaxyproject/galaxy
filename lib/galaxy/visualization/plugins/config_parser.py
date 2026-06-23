import logging
from typing import (
    Any,
)

from galaxy.util import (
    asbool,
    listify,
)
from galaxy.util.xml_macros import load

log = logging.getLogger(__name__)


class ParsingException(ValueError):
    """
    An exception class for errors that occur during parsing of the plugin
    framework configuration XML file.
    """


class PluginConfigParser:
    """
    Class that parses a plugin configuration XML file.

    Each plugin will get the following info:
        - how to load a plugin:
            -- how to find the proper template
            -- how to convert query string into DB models
        - when/how to generate a link to the plugin
            -- what provides the data
            -- what information needs to be added to the query string
    """

    def __init__(self):
        # what parsers should be used for sub-components
        self.data_source_parser = DataSourceParser()
        self.param_parser = ParamParser()

    def parse_file(self, xml_filepath):
        """
        Parse the given XML file for plugin data.
        :returns: plugin config dictionary
        """
        xml_tree = load(xml_filepath)
        plugin = self.parse_plugin(xml_tree.getroot())
        return plugin

    def parse_plugin(self, xml_tree):
        """
        Parse the template, name, and any data_sources and params from the
        given `xml_tree` for a plugin.
        """
        returned = {}

        # a text display name for end user links
        returned["name"] = xml_tree.attrib.get("name", None)
        if not returned["name"]:
            raise ParsingException("Plugin needs a name attribute.")

        # allow manually turning off a plugin by checking for a disabled property
        if "disabled" in xml_tree.attrib:
            log.info("Plugin disabled: %s. Skipping...", returned["name"])
            return None

        # record boolean flags - defaults to False
        for keyword in ["embeddable", "hidden"]:
            returned[keyword] = False
            if keyword in xml_tree.attrib:
                returned[keyword] = asbool(xml_tree.attrib.get(keyword))

        # a (for now) text description of what the plugin does
        description = xml_tree.find("description")
        returned["description"] = description.text.strip() if description is not None else None

        # help text of what the plugin does
        help = xml_tree.find("help")
        returned["help"] = help.text if help is not None else None

        # data_sources are the kinds of objects/data associated with the plugin
        #   e.g. views on HDAs can use this to find out what plugins are applicable to them
        data_sources = []
        data_sources_confs = xml_tree.find("data_sources")
        for data_source_conf in data_sources_confs.findall("data_source"):
            data_source = self.data_source_parser.parse(data_source_conf)
            if data_source:
                data_sources.append(data_source)
        # data_sources are not required
        if not data_sources:
            raise ParsingException("No valid data_sources for plugin")
        returned["data_sources"] = data_sources

        # parameters specify which values are required for the plugin
        params = {}
        param_confs = xml_tree.find("params")
        param_elements = param_confs.findall("param") if param_confs is not None else []
        for param_conf in param_elements:
            param = self.param_parser.parse(param_conf)
            if param:
                params[param_conf.text] = param
        if params:
            returned["params"] = params

        # entry_point: how will this plugin render/load? mako, script tag, or static html file?
        returned["entry_point"] = self.parse_entry_point(xml_tree)

        # load optional custom configuration specifiers
        if (specs_section := xml_tree.find("specs")) is not None:
            returned["specs"] = DictParser(specs_section)

        # load optional tags specifiers
        if (tag_section := xml_tree.find("tags")) is not None:
            returned["tags"] = ListParser(tag_section)

        # load tracks specifiers (allow 'groups' section for backward compatibility)
        if (tracks_section := xml_tree.find("tracks")) is not None:
            returned["tracks"] = ListParser(tracks_section)

        # load settings specifiers
        if (settings_section := xml_tree.find("settings")) is not None:
            returned["settings"] = ListParser(settings_section)

        # load tests specifiers
        if (test_section := xml_tree.find("tests")) is not None:
            returned["tests"] = ListParser(test_section)

        return returned

    def parse_entry_point(self, xml_tree):
        """
        Parse the config file for script entry point attributes like ``src`` and ``css`.
        """
        # verify entry_point exists
        entry_point = xml_tree.find("entry_point")
        if entry_point is None:
            raise ParsingException("template or entry_point required")

        # parse by returning a sub-object
        entry_point_attrib = dict(entry_point.attrib)
        return {"attr": entry_point_attrib}


# -------------------------------------------------------------------
class DataSourceParser:
    """
    Component class of PluginConfigParser that parses data_source elements
    within plugin elements.

    data_sources are (in the extreme) any object that can be used to produce
    data for the plugin to consume (e.g. HDAs, LDDAs, Jobs, Users, etc.).
    There can be more than one data_source associated with a plugin.
    """

    # these are the allowed classes to associate plugins with (as strings)
    #   any model_class element not in this list will throw a parsing ParsingExcepion
    ALLOWED_MODEL_CLASSES = ["Visualization", "HistoryDatasetAssociation", "LibraryDatasetDatasetAssociation"]

    def parse(self, xml_tree):
        """
        Return a plugin data_source dictionary parsed from the given
        XML element.
        """
        returned = {}
        # model_class (required, only one) - look up and convert model_class to actual galaxy model class
        model_class = self.parse_model_class(xml_tree.find("model_class"))
        if not model_class:
            raise ParsingException("data_source needs a model class")
        returned["model_class"] = model_class

        # tests (optional, 0 or more) - data for boolean test: 'is the plugin usable by this object?'
        # when no tests are given, default to isinstance( object, model_class )
        returned["tests"] = self.parse_tests(xml_tree.findall("test"))

        return returned

    def parse_model_class(self, xml_tree):
        """
        Convert xml model_class element to a galaxy model class
        (or None if model class is not found).

        This element is required and only the first element is used.
        The model_class string must be in ALLOWED_MODEL_CLASSES.
        """
        if xml_tree is None or not xml_tree.text:
            raise ParsingException("data_source entry requires a model_class")

        if xml_tree.text not in self.ALLOWED_MODEL_CLASSES:
            raise ParsingException(f"Invalid data_source model_class: {xml_tree.text}")

        return xml_tree.text

    def parse_tests(self, xml_tree_list):
        """
        Returns a list of test dictionaries that the registry can use
        against a given object to determine if the plugin can be
        used with the object.
        """
        # tests should NOT include expensive operations: reading file data, running jobs, etc.
        # do as much here as possible to reduce the overhead of seeing if a plugin is applicable
        # currently tests are or'd only (could be and'd or made into compound boolean tests)
        tests: list[dict[str, Any]] = []
        if not xml_tree_list:
            return tests

        for test_elem in xml_tree_list:
            test_type = test_elem.get("type", "eq")
            test_result = test_elem.text.strip() if test_elem.text else None
            if not test_type or not test_result:
                log.warning(
                    "Skipping test. Needs both type attribute and text node to be parsed: %s, %s",
                    test_type,
                    test_elem.text,
                )
                continue

            # collect test attribute
            test_attr = test_elem.get("test_attr")

            # collect expected test result
            test_result = test_result.strip()

            # allow_uri_if_protocol indicates that the plugin can work with deferred data_sources which source URI
            # matches any of the given protocols in this list. This is useful for plugins that can work with URIs.
            # Can only be used with isinstance tests. By default, an empty list means that the plugin doesn't support
            # deferred data_sources.
            allow_uri_if_protocol = listify(test_elem.get("allow_uri_if_protocol"))

            # append serializable test details for evaluation in registry
            tests.append(
                {
                    "attr": test_attr,
                    "type": test_type,
                    "result": test_result,
                    "allow_uri_if_protocol": allow_uri_if_protocol,
                }
            )

        return tests


class ListParser(list):
    """
    Converts a xml structure into an array
    See: http://code.activestate.com/recipes/410469-xml-as-dictionary/
    """

    def __init__(self, aList):
        for element in aList:
            if len(element) > 0:
                if element.tag == element[0].tag:
                    self.append(ListParser(element))
                else:
                    self.append(DictParser(element))
            elif element.text:
                text = element.text.strip()
                if text:
                    self.append(text)


class DictParser(dict):
    """
    Converts a xml structure into a dictionary
    See: http://code.activestate.com/recipes/410469-xml-as-dictionary/
    """

    def __init__(self, parent_element):
        if parent_element.items():
            self.update(dict(parent_element.items()))
        for element in parent_element:
            if len(element) > 0:
                asJson: Any
                if element.tag == element[0].tag:
                    asJson = ListParser(element)
                else:
                    aDict = DictParser(element)
                    if element.items():
                        aDict.update(dict(element.items()))
                    asJson = aDict
                self.update({element.tag: asJson})
            elif element.items():
                self.update({element.tag: dict(element.items())})
            else:
                self.update({element.tag: element.text})


class ParamParser:
    """
    Component class of PluginConfigParser that parses param elements
    within plugin elements.

    params are parameters that will be parsed (based on their `type`, etc.)
    and sent to the plugin template by controllers.
    """

    DEFAULT_PARAM_TYPE = "str"

    def parse(self, xml_tree):
        """
        Parse a plugin parameter from the given `xml_tree`.
        """
        returned = {}

        # don't store key, just check it
        param_key = xml_tree.text
        if not param_key:
            raise ParsingException("Param entry requires text")

        # determine parameter type
        returned["type"] = xml_tree.get("type") or self.DEFAULT_PARAM_TYPE

        # is the parameter required in the template and,
        #   if not, what is the default value?
        required = xml_tree.get("required") == "true"
        returned["required"] = required
        if not required:
            # default defaults to None
            default = None
            if "default" in xml_tree.attrib:
                default = xml_tree.get("default")
                # convert default based on param_type here
            returned["default"] = default

        return returned
