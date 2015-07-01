import weakref

import galaxy.model
from galaxy import util
from galaxy.visualization.plugins import utils as vis_utils

import logging
log = logging.getLogger( __name__ )


# -------------------------------------------------------------------
class ParsingException( ValueError ):
    """
    An exception class for errors that occur during parsing of the visualizations
    framework configuration XML file.
    """
    pass


# -------------------------------------------------------------------
class VisualizationsConfigParser( object ):
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
    ALLOWED_ENTRY_POINT_TYPES = ['mako', 'html', 'script']
    #: what are the allowed href targets when clicking on a visualization anchor
    VALID_RENDER_TARGETS = [ 'galaxy_main', '_top', '_blank' ]

    def __init__( self, app ):
        self.app = weakref.ref( app )
        # what parsers should be used for sub-components
        self.data_source_parser = DataSourceParser( app )
        self.param_parser = ParamParser()
        self.param_modifier_parser = ParamModifierParser()

    def parse_file( self, xml_filepath ):
        """
        Parse the given XML file for visualizations data.
        :returns: visualization config dictionary
        """
        xml_tree = util.parse_xml( xml_filepath )
        visualization = self.parse_visualization( xml_tree.getroot() )
        return visualization

    def parse_visualization( self, xml_tree ):
        """
        Parse the template, name, and any data_sources and params from the
        given `xml_tree` for a visualization.
        """
        returned = {}

        # main tag specifies plugin type (visualization or
        # interactive_enviornment).
        returned[ 'plugin_type' ] = xml_tree.tag

        # a text display name for end user links
        returned[ 'name' ] = xml_tree.attrib.get( 'name', None )
        if not returned[ 'name' ]:
            raise ParsingException( 'visualization needs a name attribute' )

        # allow manually turning off a vis by checking for a disabled property
        if 'disabled' in xml_tree.attrib:
            log.info( 'Visualizations plugin disabled: %s. Skipping...', returned[ 'name' ] )
            return None

        # record the embeddable flag - defaults to false
        #   this is a design by contract promise that the visualization can be rendered inside another page
        #   often by rendering only a DOM fragment. Since this is an advanced feature that requires a bit more
        #   work from the creator's side - it defaults to False
        returned[ 'embeddable' ] = False
        if 'embeddable' in xml_tree.attrib:
            returned[ 'embeddable' ] = xml_tree.attrib.get( 'embeddable', False ) == 'true'

        # a (for now) text description of what the visualization does
        description = xml_tree.find( 'description' )
        returned[ 'description' ] = description.text.strip() if description is not None else None

        # data_sources are the kinds of objects/data associated with the visualization
        #   e.g. views on HDAs can use this to find out what visualizations are applicable to them
        data_sources = []
        data_sources_confs = xml_tree.find( 'data_sources' )
        for data_source_conf in data_sources_confs.findall( 'data_source' ):
            data_source = self.data_source_parser.parse( data_source_conf )
            data_sources.append( data_source )

        # data source groups are lists of objects/models where all objects must be applicable
        # in order for the visualization to be considered applicable
        # (they are otherwise treated as and have the same interface as data_sources)
        for data_source_group in data_sources_confs.findall( 'data_source_group' ):
            data_source = self.parse_data_source_group( data_source_group )
            data_sources.append( data_source )

        # data_sources are not required
        if not data_sources:
            raise ParsingException( 'No valid data_sources for visualization' )
        returned[ 'data_sources' ] = data_sources

        # TODO: this is effectively required due to param_confs.findall( 'param' )
        # parameters spell out how to convert query string params into resources and data
        #   that will be parsed, fetched, etc. and passed to the template
        # list or dict? ordered or not?
        params = {}
        param_confs = xml_tree.find( 'params' )
        param_elements = param_confs.findall( 'param' ) if param_confs is not None else []
        for param_conf in param_elements:
            param = self.param_parser.parse( param_conf )
            if param:
                params[ param_conf.text ] = param
        # params are not required
        if params:
            returned[ 'params' ] = params

        # param modifiers provide extra information for other params (e.g. hda_ldda='hda' -> dataset_id is an hda id)
        # store these modifiers in a 2-level dictionary { target_param: { param_modifier_key: { param_mod_data }
        # ugh - wish we didn't need these
        param_modifiers = {}
        param_modifier_elements = param_confs.findall( 'param_modifier' ) if param_confs is not None else []
        for param_modifier_conf in param_modifier_elements:
            param_modifier = self.param_modifier_parser.parse( param_modifier_conf )
            # param modifiers map accrd. to the params they modify (for faster lookup)
            target_param = param_modifier_conf.get( 'modifies' )
            param_modifier_key = param_modifier_conf.text
            if param_modifier and target_param in params:
                # multiple params can modify a single, other param,
                #   so store in a sub-dict, initializing if this is the first
                if target_param not in param_modifiers:
                    param_modifiers[ target_param ] = {}
                param_modifiers[ target_param ][ param_modifier_key ] = param_modifier

        # not required
        if param_modifiers:
            returned[ 'param_modifiers' ] = param_modifiers

        # entry_point: how will this plugin render/load? mako, script tag, or static html file?
        returned[ 'entry_point' ] = self.parse_entry_point( xml_tree )

        # link_text: the string to use for the text of any links/anchors to this visualization
        link_text = xml_tree.find( 'link_text' )
        if link_text is not None and link_text.text:
            returned[ 'link_text' ] = link_text

        # render_target: where in the browser to open the rendered visualization
        # defaults to: galaxy_main
        render_target = xml_tree.find( 'render_target' )
        if( ( render_target is not None and render_target.text )
        and ( render_target.text in self.VALID_RENDER_TARGETS ) ):
            returned[ 'render_target' ] = render_target.text
        else:
            returned[ 'render_target' ] = 'galaxy_main'
        # consider unifying the above into its own element and parsing method

        return returned

    def parse_data_source_group( self, data_source_group ):
        """
        Parse multiple `data_source`s into a `DataSourceGroup`.
        """
        sources = []
        for source in data_source_group.findall( 'data_source' ):
            sources.append( self.data_source_parser.parse( source ) )
        group = DataSourceGroup( sources=sources )
        return group

    def parse_entry_point( self, xml_tree ):
        """
        Parse the config file for an appropriate entry point: a mako template, a script tag,
        or an html file, returning as dictionary with: `type`, `file`, and `attr`ibutes of
        the element.
        """
        # (older) mako-only syntax: the template to use in rendering the visualization
        template = xml_tree.find( 'template' )
        if template is not None and template.text:
            log.info( 'template syntax is deprecated: use entry_point instead' )
            return {
                'type' : 'mako',
                'file' : template.text,
                'attr' : {}
            }

        # need one of the two: (the deprecated) template or entry_point
        entry_point = xml_tree.find( 'entry_point' )
        if entry_point is None:
            raise ParsingException( 'template or entry_point required' )

        # parse by returning a sub-object and simply copying any attributes unused here
        entry_point_attrib = entry_point.attrib.copy()
        entry_point_type = entry_point_attrib.pop( 'entry_point_type', 'mako' )
        if entry_point_type not in self.ALLOWED_ENTRY_POINT_TYPES:
            raise ParsingException( 'Unknown entry_point type: ' + entry_point_type )
        return {
            'type' : entry_point_type,
            'file' : entry_point.text,
            'attr' : entry_point_attrib
        }


# -------------------------------------------------------------------
class DataSource( object ):
    """
    A validator that:
        tests if a visualization is applicable to (can be run with) an object/model
        parses the to_params from the applicable objects into query string params
    """

    def __init__( self, model_class=None, tests=None, to_params=None ):
        self.model_class = model_class
        self.tests = tests or []
        self.to_params = to_params or {}

    # public interface
    def is_applicable( self, target ):
        """
        Can the plugin use this object/model within the visualization.
        """
        # bail early if not matching model_class
        if self.model_class and not isinstance( target, self.model_class ):
            return False

        for test in self.tests:
            test_result = test[ 'result' ]
            test_fn = test[ 'fn' ]

            # NOTE: tests are (normally) OR'd, if any test passes - the visualization can be applied
            test_passed = test_fn( target, test_result )
            if test_passed:
                return True

        return False

    def params( self, trans, target_object ):
        """
        Return a dictionary suitable for query string parameters
        that describe the source `target_object` according to the config file.
        """
        to_params = self.to_params
        target_params = {}
        for to_param_name, to_param_data in to_params.items():
            # TODO??: look into params as well? what is required, etc.
            target_attr = to_param_data.get( 'param_attr', None )
            assign = to_param_data.get( 'assign', None )
            # one or the other is needed
            # assign takes precedence (goes last, overwrites)?
            # NOTE this is only one level

            if target_attr and vis_utils.hasattr_recursive( target_object, target_attr ):
                target_params[ to_param_name ] = vis_utils.getattr_recursive( target_object, target_attr )

            if assign:
                target_params[ to_param_name ] = assign

        # NOTE!: don't expose raw ids: encode id, _id
        # TODO: double encodes if from config
        if target_params:
            target_params = trans.security.encode_dict_ids( target_params )
        return target_params

    def __str__( self ):
        return 'DataSource({params})'.format( params=self.to_params )


# -------------------------------------------------------------------
class DataSourceGroup( DataSource ):
    """
    Defines a set of sources that must match a target set
    of objects/models in order for the plugin to be applicable.
    """

    def __init__( self, sources=None ):
        self.sources = sources or []

    def is_applicable( self, targets ):
        """
        Override to cycle through all sources in the group.
        """
        if not isinstance( targets, list ):
            return False
        matching_targets = self._match_source_to_targets( targets )
        if len( matching_targets ) == len( self.sources ):
            return True
        return False

    def _match_source_to_targets( self, targets ):
        # note: order of both sources and targets matter
        # TODO: revisit - seems like this could be simplified
        working_targets = targets[:]
        matching_targets = []
        for source in self.sources:
            new_working_targets = []
            for target in working_targets:
                if source.is_applicable( target ):
                    matching_targets.append( ( source, target ) )
                else:
                    new_working_targets.append( target )
            working_targets = new_working_targets
        return matching_targets

    def params( self, trans, target_objects ):
        """
        Override to cycle through all sources in the group.
        """
        params = {}
        for source, target in self._match_source_to_targets( target_objects ):
            source_params = source.params( trans, target )
            params.update( source_params )
        return params


# -------------------------------------------------------------------
class DataSourceParser( object ):
    """
    Component class of VisualizationsConfigParser that parses data_source elements
    within visualization elements.

    data_sources are (in the extreme) any object that can be used to produce
    data for the visualization to consume (e.g. HDAs, LDDAs, Jobs, Users, etc.).
    There can be more than one data_source associated with a visualization.
    """

    # these are the allowed classes to associate visualizations with (as strings)
    #   any model_class element not in this list will throw a parsing ParsingExcepion
    ALLOWED_MODEL_CLASSES = [
        'Visualization',
        'HistoryDatasetAssociation',
        'LibraryDatasetDatasetAssociation'
    ]

    ATTRIBUTE_SPLIT_CHAR = '.'
    # these are the allowed object attributes to use in data source tests
    #   any attribute element not in this list will throw a parsing ParsingExcepion
    # ALLOWED_DATA_SOURCE_ATTRIBUTES = [
    #     'datatype'
    # ]

    def __init__( self, app ):
        self.app = weakref.ref( app )

    def parse( self, xml_tree ):
        """
        Return a visualization data_source dictionary parsed from the given
        XML element.
        """
        returned = {}
        # model_class (required, only one) - look up and convert model_class to actual galaxy model class
        model_class = self.parse_model_class( xml_tree.find( 'model_class' ) )
        if not model_class:
            raise ParsingException( 'data_source needs a model class' )
        returned[ 'model_class' ] = model_class

        # tests (optional, 0 or more) - data for boolean test: 'is the visualization usable by this object?'
        tests = self.parse_tests( xml_tree.findall( 'test' ) )
        # when no tests are given, default to isinstance( object, model_class )
        if tests:
            returned[ 'tests' ] = tests

        # to_params (optional, 0 or more) - tells the registry to set certain params based on the model_clas, tests
        returned[ 'to_params' ] = {}
        to_params = self.parse_to_params( xml_tree.findall( 'to_param' ) )
        if to_params:
            returned[ 'to_params' ] = to_params

        data_source = DataSource( model_class=model_class, tests=tests, to_params=to_params )
        return data_source

    def parse_model_class( self, xml_tree ):
        """
        Convert xml model_class element to a galaxy model class
        (or None if model class is not found).

        This element is required and only the first element is used.
        The model_class string must be in ALLOWED_MODEL_CLASSES.
        """
        if xml_tree is None or not xml_tree.text:
            raise ParsingException( 'data_source entry requires a model_class' )

        if xml_tree.text not in self.ALLOWED_MODEL_CLASSES:
            # log.debug( 'available data_source model_classes: %s' %( str( self.ALLOWED_MODEL_CLASSES ) ) )
            raise ParsingException( 'Invalid data_source model_class: %s' % ( xml_tree.text ) )

        # look up the model from the model module returning an empty data_source if not found
        model_class = getattr( galaxy.model, xml_tree.text, None )
        return model_class

    def parse_tests( self, test_element_list ):
        """
        Returns a list of test dictionaries that the registry can use
        against a given object to determine if the visualization can be
        used with the object.
        """
        # tests should NOT include expensive operations: reading file data, running jobs, etc.
        # do as much here as possible to reduce the overhead of seeing if a visualization is applicable
        tests = []
        if not test_element_list:
            return tests

        for test_elem in test_element_list:
            test_type = test_elem.get( 'type', 'eq' )
            if test_type == 'and':
                tests.append( self.parse_anded_test( test_elem ) )
                continue
            # log.debug( 'test_type: %s, test_result: %s', test_type, test_result )
            test_attr = test_elem.get( 'test_attr', None )
            # result type should tell the registry how to convert the result before the test
            test_result_type, test_result = self.parse_expected_test_result( test_elem, test_type )
            if not test_result:
                log.warn( 'Skipping test. Needs text node to parse for test result: %s', test_elem.text )
                continue
            test_fn = self.build_test_fn( test_type, test_attr, test_result_type, test_result )
            tests.append({
                'type'          : test_type,
                'result'        : test_result,
                'result_type'   : test_result_type,
                'fn'            : test_fn
            })

        return tests

    def parse_expected_test_result( self, test_element, test_type ):
        """
        Validate 'result_type' in `test_element` for non-string comparison in tests.

        'datatype' classes are pulled from the registry here for use in 'isinstance'.
        """
        # result type should tell the registry how to convert the result before the test
        result_type = test_element.get( 'result_type', 'string' )
        expected_result = test_element.text.strip() if test_element.text else None

        if test_type == 'isinstance' and result_type == 'datatype':
            # convert datatypes to their actual classes (for use with isinstance)
            datatype_class_name = expected_result
            expected_result = self.app().datatypes_registry.get_datatype_class_by_name( datatype_class_name )
            if not expected_result:
                log.debug( 'config_parser cannot find datatype class: %s', datatype_class_name )

        return result_type, expected_result

    def build_test_fn( self, test_type, attr_to_test, result_type, result_should_be ):
        """
        Return the final test function for plugin applicability.
        """
        # test_attr can be a dot separated chain of object attributes (e.g. dataset.datatype) - convert to list
        # TODO: too dangerous - constrain these to some allowed list
        # TODO: does this err if no test_attr - it should...
        test_attr = attr_to_test.split( self.ATTRIBUTE_SPLIT_CHAR ) if isinstance( attr_to_test, str ) else []
        # build a lambda function that gets the desired attribute to test
        getter = self._build_getattr_lambda( test_attr )

        # test functions should be sent an object to test, and the parsed result expected from the test

        # is test_attr attribute an instance of result
        if test_type == 'isinstance':
            test_fn = lambda o, result: isinstance( getter( o ), result )

        # does the object itself have a datatype attr and does that datatype have the given dataprovider
        elif test_type == 'has_dataprovider':
            test_fn = lambda o, result: (     hasattr( getter( o ), 'has_dataprovider' )
                                          and getter( o ).has_dataprovider( result ) )

        # does the object itself have the attribute in result
        elif test_type == 'has_attribute':
            test_fn = lambda o, result: hasattr( getter( o ), result )

        # does the object attr contain 'result'
        elif test_type == 'contains':
            test_fn = lambda o, result: result in getter( o )

        # (string) non-equivalence
        elif test_type == 'not_eq':
            test_fn = lambda o, result: str( getter( o ) ) != result

        # default to simple (string) equilavance (coercing the test_attr to a string)
        else:
            test_fn = lambda o, result: str( getter( o ) ) == result

        return test_fn

    def _build_getattr_lambda( self, attr_name_list ):
        """
        Recursively builds a compound lambda function of getattr's
        from the attribute names given in `attr_name_list`.
        """
        if len( attr_name_list ) == 0:
            # identity - if list is empty, return object itself
            return lambda o: o

        next_attr_name = attr_name_list[-1]
        if len( attr_name_list ) == 1:
            # recursive base case
            return lambda o: getattr( o, next_attr_name )

        # recursive case
        return lambda o: getattr( self._build_getattr_lambda( attr_name_list[:-1] )( o ), next_attr_name )

    def parse_anded_test( self, and_element ):
        """
        Parse a compound test where all sub-tests must pass for it to pass.
        """
        # cycle through sub-tests using parse_tests recursively
        tests = and_element.findall( 'test' )
        tests = self.parse_tests( tests )

        # build anded_test_fn by calling all sub-tests within 'all'
        def _anded_test_fn( target, result ):
            subtest_results = []
            for test in tests:
                fn = test[ 'fn' ]
                expected = test[ 'result' ]
                result = fn( target, expected )
                subtest_results.append( result )
            return all( subtest_results )

        return {
            'type'          : 'and',
            'fn'            : _anded_test_fn,
            # TODO: these aren't really needed
            'result'        : True,
            'result_type'   : 'bool'
        }

    def parse_to_params( self, xml_tree_list ):
        """
        Given a list of `to_param` elements, returns a dictionary that allows
        the registry to convert the data_source into one or more appropriate
        params for the visualization.
        """
        to_param_dict = {}
        if not xml_tree_list:
            return to_param_dict

        for element in xml_tree_list:
            # param_name required
            param_name = element.text
            if not param_name:
                raise ParsingException( 'to_param requires text (the param name)' )

            param = {}
            # assign is a shortcut param_attr that assigns a value to a param (as text)
            assign = element.get( 'assign' )
            if assign is not None:
                param[ 'assign' ] = assign

            # param_attr is the attribute of the object (that the visualization will be applied to)
            #   that should be converted into a query param (e.g. param_attr="id" -> dataset_id)
            # TODO:?? use the build attr getter here?
            # simple (1 lvl) attrs for now
            param_attr = element.get( 'param_attr' )
            if param_attr is not None:
                param[ 'param_attr' ] = param_attr
            # element must have either param_attr or assign? what about no params (the object itself)
            if not param_attr and not assign:
                raise ParsingException( 'to_param requires either assign or param_attr attributes: %s', param_name )

            # TODO: consider making the to_param name an attribute (param="hda_ldda") and the text what would
            #           be used for the conversion - this would allow CDATA values to be passed
            # <to_param param="json" type="assign"><![CDATA[{ "one": 1, "two": 2 }]]></to_param>

            if param:
                to_param_dict[ param_name ] = param

        return to_param_dict


# -------------------------------------------------------------------
class ParamParser( object ):
    """
    Component class of VisualizationsConfigParser that parses param elements
    within visualization elements.

    params are parameters that will be parsed (based on their `type`, etc.)
    and sent to the visualization template by controllers.visualization.render.
    """
    DEFAULT_PARAM_TYPE = 'str'

    def parse( self, xml_tree ):
        """
        Parse a visualization parameter from the given `xml_tree`.
        """
        returned = {}

        # don't store key, just check it
        param_key = xml_tree.text
        if not param_key:
            raise ParsingException( 'Param entry requires text' )

        returned[ 'type' ] = self.parse_param_type( xml_tree )

        # is the parameter required in the template and,
        #   if not, what is the default value?
        required = xml_tree.get( 'required' ) == "true"
        returned[ 'required' ] = required
        if not required:
            # default defaults to None
            default = None
            if 'default' in xml_tree.attrib:
                default = xml_tree.get( 'default' )
                # convert default based on param_type here
            returned[ 'default' ] = default

        # does the param have to be within a list of certain values
        # NOTE: the interpretation of this list is deferred till parsing and based on param type
        #   e.g. it could be 'val in constrain_to', or 'constrain_to is min, max for number', etc.
        # TODO: currently unused
        constrain_to = xml_tree.get( 'constrain_to' )
        if constrain_to:
            returned[ 'constrain_to' ] = constrain_to.split( ',' )

        # is the param a comma-separated-value list?
        returned[ 'csv' ] = xml_tree.get( 'csv' ) == "true"

        # remap keys in the params/query string to the var names used in the template
        var_name_in_template = xml_tree.get( 'var_name_in_template' )
        if var_name_in_template:
            returned[ 'var_name_in_template' ] = var_name_in_template

        return returned

    def parse_param_type( self, xml_tree ):
        """
        Parse a param type from the given `xml_tree`.
        """
        # default to string as param_type
        param_type = xml_tree.get( 'type' ) or self.DEFAULT_PARAM_TYPE
        # TODO: set parsers and validaters, convert here
        return param_type


# -------------------------------------------------------------------
class ParamModifierParser( ParamParser ):
    """
    Component class of VisualizationsConfigParser that parses param_modifier
    elements within visualization elements.

    param_modifiers are params from a dictionary (such as a query string)
    that are not standalone but modify the parsing/conversion of a separate
    (normal) param (e.g. 'hda_ldda' can equal 'hda' or 'ldda' and control
    whether a visualizations 'dataset_id' param is for an HDA or LDDA).
    """
    def parse( self, element ):
        # modifies is required
        modifies = element.get( 'modifies' )
        if not modifies:
            raise ParsingException( 'param_modifier entry requires a target param key (attribute "modifies")' )
        returned = super( ParamModifierParser, self).parse( element )
        return returned
