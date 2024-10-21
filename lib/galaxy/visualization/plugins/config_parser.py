import logging
from typing import (
    Any,
    Dict,
    List,
)

import galaxy.model
from galaxy.util import asbool
from galaxy.util.xml_macros import load

log = logging.getLogger(__name__)


class ParsingException(ValueError):
    """
    An exception class for errors that occur during parsing of the visualizations
    framework configuration XML file.
    """


class VisualizationsConfigParser:
    """
    Class that parses a visualizations configuration XML file.

    Each visualization will get the following info:
        - how to load a visualization:
            -- how to find the proper template
            -- how to convert query string into DB models
        - when/how to generate a link to the visualization
            -- what provides the data
            -- what information needs to be added to the query string
    """

    #: what are the allowed 'entry_point_type' for entry_point elements
    ALLOWED_ENTRY_POINT_TYPES = ["mako", "html", "script", "chart"]
    #: what are the allowed href targets when clicking on a visualization anchor
    VALID_RENDER_TARGETS = ["galaxy_main", "_top", "_blank"]

    def __init__(self):
        # what parsers should be used for sub-components
        self.data_source_parser = DataSourceParser()
        self.param_parser = ParamParser()
        self.param_modifier_parser = ParamModifierParser()

    def parse_file(self, xml_filepath):
        """
        Parse the given XML file for visualizations data.
        :returns: visualization config dictionary
        """
        xml_tree = load(xml_filepath)
        visualization = self.parse_visualization(xml_tree.getroot())
        return visualization

    def parse_visualization(self, xml_tree):
        """
        Parse the template, name, and any data_sources and params from the
        given `xml_tree` for a visualization.
        """
        returned = {}

        # main tag specifies plugin type (visualization or other).
        returned["plugin_type"] = xml_tree.tag

        # a text display name for end user links
        returned["name"] = xml_tree.attrib.get("name", None)
        if not returned["name"]:
            raise ParsingException("Visualization needs a name attribute.")

        # allow manually turning off a vis by checking for a disabled property
        if "disabled" in xml_tree.attrib:
            log.info("Visualizations plugin disabled: %s. Skipping...", returned["name"])
            return None

        # record the embeddable flag - defaults to true
        returned["embeddable"] = True
        if "embeddable" in xml_tree.attrib:
            returned["embeddable"] = asbool(xml_tree.attrib.get("embeddable"))

        # a (for now) text description of what the visualization does
        description = xml_tree.find("description")
        returned["description"] = description.text.strip() if description is not None else None

        # data_sources are the kinds of objects/data associated with the visualization
        #   e.g. views on HDAs can use this to find out what visualizations are applicable to them
        data_sources = []
        data_sources_confs = xml_tree.find("data_sources")
        for data_source_conf in data_sources_confs.findall("data_source"):
            data_source = self.data_source_parser.parse(data_source_conf)
            if data_source:
                data_sources.append(data_source)
        # data_sources are not required
        if not data_sources:
            raise ParsingException("No valid data_sources for visualization")
        returned["data_sources"] = data_sources

        # TODO: this is effectively required due to param_confs.findall( 'param' )
        # parameters spell out how to convert query string params into resources and data
        #   that will be parsed, fetched, etc. and passed to the template
        # list or dict? ordered or not?
        params = {}
        param_confs = xml_tree.find("params")
        param_elements = param_confs.findall("param") if param_confs is not None else []
        for param_conf in param_elements:
            param = self.param_parser.parse(param_conf)
            if param:
                params[param_conf.text] = param
        # params are not required
        if params:
            returned["params"] = params

        # param modifiers provide extra information for other params (e.g. hda_ldda='hda' -> dataset_id is an hda id)
        # store these modifiers in a 2-level dictionary { target_param: { param_modifier_key: { param_mod_data }
        # ugh - wish we didn't need these
        param_modifiers: Dict[str, Any] = {}
        param_modifier_elements = param_confs.findall("param_modifier") if param_confs is not None else []
        for param_modifier_conf in param_modifier_elements:
            param_modifier = self.param_modifier_parser.parse(param_modifier_conf)
            # param modifiers map accrd. to the params they modify (for faster lookup)
            target_param = param_modifier_conf.get("modifies")
            param_modifier_key = param_modifier_conf.text
            if param_modifier and target_param in params:
                # multiple params can modify a single, other param,
                #   so store in a sub-dict, initializing if this is the first
                if target_param not in param_modifiers:
                    param_modifiers[target_param] = {}
                param_modifiers[target_param][param_modifier_key] = param_modifier

        # not required
        if param_modifiers:
            returned["param_modifiers"] = param_modifiers

        # entry_point: how will this plugin render/load? mako, script tag, or static html file?
        returned["entry_point"] = self.parse_entry_point(xml_tree)

        # link_text: the string to use for the text of any links/anchors to this visualization
        link_text = xml_tree.find("link_text")
        if link_text is not None and link_text.text:
            returned["link_text"] = link_text

        # render_target: where in the browser to open the rendered visualization
        # defaults to: galaxy_main
        render_target = xml_tree.find("render_target")
        if (render_target is not None and render_target.text) and (render_target.text in self.VALID_RENDER_TARGETS):
            returned["render_target"] = render_target.text
        else:
            returned["render_target"] = "galaxy_main"
        # consider unifying the above into its own element and parsing method

        # load optional custom configuration specifiers
        if (specs_section := xml_tree.find("specs")) is not None:
            returned["specs"] = DictParser(specs_section)

        # load tracks specifiers (allow 'groups' section for backward compatibility)
        if (tracks_section := xml_tree.find("tracks") or xml_tree.find("groups")) is not None:
            returned["tracks"] = ListParser(tracks_section)

        # load settings specifiers
        if (settings_section := xml_tree.find("settings")) is not None:
            returned["settings"] = ListParser(settings_section)

        return returned

    def parse_entry_point(self, xml_tree):
        """
        Parse the config file for an appropriate entry point: a mako template, a script tag,
        or an html file, returning as dictionary with: ``type``, ``file``, and ``attr`` (-ibutes) of
        the element.
        """
        # (older) mako-only syntax: the template to use in rendering the visualization
        template = xml_tree.find("template")
        if template is not None and template.text:
            log.info("template syntax is deprecated: use entry_point instead")
            return {"type": "mako", "file": template.text, "attr": {}}

        # need one of the two: (the deprecated) template or entry_point
        entry_point = xml_tree.find("entry_point")
        if entry_point is None:
            raise ParsingException("template or entry_point required")

        # parse by returning a sub-object and simply copying any attributes unused here
        entry_point_attrib = dict(entry_point.attrib)
        entry_point_type = entry_point_attrib.pop("entry_point_type", "mako")
        if entry_point_type not in self.ALLOWED_ENTRY_POINT_TYPES:
            raise ParsingException(f"Unknown entry_point type: {entry_point_type}")
        return {"type": entry_point_type, "file": entry_point.text, "attr": entry_point_attrib}


# -------------------------------------------------------------------
class DataSourceParser:
    """
    Component class of VisualizationsConfigParser that parses data_source elements
    within visualization elements.

    data_sources are (in the extreme) any object that can be used to produce
    data for the visualization to consume (e.g. HDAs, LDDAs, Jobs, Users, etc.).
    There can be more than one data_source associated with a visualization.
    """

    # these are the allowed classes to associate visualizations with (as strings)
    #   any model_class element not in this list will throw a parsing ParsingExcepion
    ALLOWED_MODEL_CLASSES = ["Visualization", "HistoryDatasetAssociation", "LibraryDatasetDatasetAssociation"]
    ATTRIBUTE_SPLIT_CHAR = "."
    # these are the allowed object attributes to use in data source tests
    #   any attribute element not in this list will throw a parsing ParsingExcepion
    ALLOWED_DATA_SOURCE_ATTRIBUTES = ["datatype"]

    def parse(self, xml_tree):
        """
        Return a visualization data_source dictionary parsed from the given
        XML element.
        """
        returned = {}
        # model_class (required, only one) - look up and convert model_class to actual galaxy model class
        model_class = self.parse_model_class(xml_tree.find("model_class"))
        if not model_class:
            raise ParsingException("data_source needs a model class")
        returned["model_class"] = model_class

        # tests (optional, 0 or more) - data for boolean test: 'is the visualization usable by this object?'
        # when no tests are given, default to isinstance( object, model_class )
        returned["tests"] = self.parse_tests(xml_tree.findall("test"))

        # to_params (optional, 0 or more) - tells the registry to set certain params based on the model_class, tests
        returned["to_params"] = {}
        if to_params := self.parse_to_params(xml_tree.findall("to_param")):
            returned["to_params"] = to_params

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
            # log.debug( 'available data_source model_classes: %s' %( str( self.ALLOWED_MODEL_CLASSES ) ) )
            raise ParsingException(f"Invalid data_source model_class: {xml_tree.text}")

        # look up the model from the model module returning an empty data_source if not found
        model_class = getattr(galaxy.model, xml_tree.text, None)
        return model_class

    def _build_getattr_lambda(self, attr_name_list):
        """
        Recursively builds a compound lambda function of getattr's
        from the attribute names given in `attr_name_list`.
        """
        if len(attr_name_list) == 0:
            # identity - if list is empty, return object itself
            return lambda o: o

        next_attr_name = attr_name_list[-1]
        if len(attr_name_list) == 1:
            # recursive base case
            return lambda o: getattr(o, next_attr_name)

        # recursive case
        return lambda o: getattr(self._build_getattr_lambda(attr_name_list[:-1])(o), next_attr_name)

    def parse_tests(self, xml_tree_list):
        """
        Returns a list of test dictionaries that the registry can use
        against a given object to determine if the visualization can be
        used with the object.
        """
        # tests should NOT include expensive operations: reading file data, running jobs, etc.
        # do as much here as possible to reduce the overhead of seeing if a visualization is applicable
        # currently tests are or'd only (could be and'd or made into compound boolean tests)
        tests: List[Dict[str, Any]] = []
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
            test_result = test_result.strip()

            # test_attr can be a dot separated chain of object attributes (e.g. dataset.datatype) - convert to list
            # TODO: too dangerous - constrain these to some allowed list
            # TODO: does this err if no test_attr - it should...
            test_attr = test_elem.get("test_attr")
            test_attr = test_attr.split(self.ATTRIBUTE_SPLIT_CHAR) if isinstance(test_attr, str) else []
            # log.debug( 'test_type: %s, test_attr: %s, test_result: %s', test_type, test_attr, test_result )

            # build a lambda function that gets the desired attribute to test
            getter = self._build_getattr_lambda(test_attr)
            # result type should tell the registry how to convert the result before the test
            test_result_type = test_elem.get("result_type", "string")

            # test functions should be sent an object to test, and the parsed result expected from the test
            if test_type == "isinstance":
                # is test_attr attribute an instance of result
                # TODO: wish we could take this further but it would mean passing in the datatypes_registry
                def test_fn(o, result, getter=getter):
                    return isinstance(getter(o), result)

            elif test_type == "has_dataprovider":
                # does the object itself have a datatype attr and does that datatype have the given dataprovider
                def test_fn(o, result, getter=getter):
                    return hasattr(getter(o), "has_dataprovider") and getter(o).has_dataprovider(result)

            elif test_type == "has_attribute":
                # does the object itself have attr in 'result' (no equivalence checking)
                def test_fn(o, result, getter=getter):
                    return hasattr(getter(o), result)

            elif test_type == "not_eq":

                def test_fn(o, result, getter=getter):
                    return str(getter(o)) != result

            else:
                # default to simple (string) equilavance (coercing the test_attr to a string)
                def test_fn(o, result, getter=getter):
                    return str(getter(o)) == result

            tests.append({"type": test_type, "result": test_result, "result_type": test_result_type, "fn": test_fn})

        return tests

    def parse_to_params(self, xml_tree_list):
        """
        Given a list of `to_param` elements, returns a dictionary that allows
        the registry to convert the data_source into one or more appropriate
        params for the visualization.
        """
        to_param_dict: Dict[str, Any] = {}
        if not xml_tree_list:
            return to_param_dict

        for element in xml_tree_list:
            # param_name required
            param_name = element.text
            if not param_name:
                raise ParsingException("to_param requires text (the param name)")

            param = {}
            # assign is a shortcut param_attr that assigns a value to a param (as text)
            assign = element.get("assign")
            if assign is not None:
                param["assign"] = assign

            # param_attr is the attribute of the object (that the visualization will be applied to)
            #   that should be converted into a query param (e.g. param_attr="id" -> dataset_id)
            # TODO:?? use the build attr getter here?
            # simple (1 lvl) attrs for now
            param_attr = element.get("param_attr")
            if param_attr is not None:
                param["param_attr"] = param_attr
            # element must have either param_attr or assign? what about no params (the object itself)
            if not param_attr and not assign:
                raise ParsingException("to_param requires either assign or param_attr attributes: %s", param_name)

            # TODO: consider making the to_param name an attribute (param="hda_ldda") and the text what would
            #           be used for the conversion - this would allow CDATA values to be passed
            # <to_param param="json" type="assign"><![CDATA[{ "one": 1, "two": 2 }]]></to_param>

            if param:
                to_param_dict[param_name] = param

        return to_param_dict


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
    Component class of VisualizationsConfigParser that parses param elements
    within visualization elements.

    params are parameters that will be parsed (based on their `type`, etc.)
    and sent to the visualization template by controllers.visualization.render.
    """

    DEFAULT_PARAM_TYPE = "str"

    def parse(self, xml_tree):
        """
        Parse a visualization parameter from the given `xml_tree`.
        """
        returned = {}

        # don't store key, just check it
        param_key = xml_tree.text
        if not param_key:
            raise ParsingException("Param entry requires text")

        returned["type"] = self.parse_param_type(xml_tree)

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

        # does the param have to be within a list of certain values
        # NOTE: the interpretation of this list is deferred till parsing and based on param type
        #   e.g. it could be 'val in constrain_to', or 'constrain_to is min, max for number', etc.
        # TODO: currently unused
        if constrain_to := xml_tree.get("constrain_to"):
            returned["constrain_to"] = constrain_to.split(",")

        # is the param a comma-separated-value list?
        returned["csv"] = xml_tree.get("csv") == "true"

        # remap keys in the params/query string to the var names used in the template
        if var_name_in_template := xml_tree.get("var_name_in_template"):
            returned["var_name_in_template"] = var_name_in_template

        return returned

    def parse_param_type(self, xml_tree):
        """
        Parse a param type from the given `xml_tree`.
        """
        # default to string as param_type
        param_type = xml_tree.get("type") or self.DEFAULT_PARAM_TYPE
        # TODO: set parsers and validaters, convert here
        return param_type


class ParamModifierParser(ParamParser):
    """
    Component class of VisualizationsConfigParser that parses param_modifier
    elements within visualization elements.

    param_modifiers are params from a dictionary (such as a query string)
    that are not standalone but modify the parsing/conversion of a separate
    (normal) param (e.g. 'hda_ldda' can equal 'hda' or 'ldda' and control
    whether a visualizations 'dataset_id' param is for an HDA or LDDA).
    """

    def parse(self, element):
        # modifies is required
        modifies = element.get("modifies")
        if not modifies:
            raise ParsingException('param_modifier entry requires a target param key (attribute "modifies")')
        returned = super().parse(element)
        return returned
