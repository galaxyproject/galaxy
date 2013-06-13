"""
Lower level of visualization framework which does three main things:
    - associate visualizations with objects
    - create urls to visualizations based on some target object(s)
    - unpack a query string into the desired objects needed for rendering
"""
import os
import shutil

from galaxy import util
import galaxy.model
from galaxy.web import url_for

import logging
log = logging.getLogger( __name__ )

__TODO__ = """
    BUGS:
        anon users clicking a viz link gets 'must be' msg in galaxy_main (w/ masthead)
            should not show visualizations (no icon)?
        newick files aren't being sniffed prop? - datatype is txt

    have parsers create objects instead of dicts
    allow data_sources with no model_class but have tests (isAdmin, etc.)
        maybe that's an instance of User model_class?
    some confused vocabulary in docs, var names
    tests:
        anding, grouping, not
    data_sources:
        lists of
    add description element to visualization.
"""

class VisualizationsRegistry( object ):
    """
    Main responsibilities are:
        - testing if an object has a visualization that can be applied to it
        - generating a link to controllers.visualization.render with
            the appropriate params
        - validating and parsing params into resources (based on a context)
            used in the visualization template
    """
    # these should be handled somewhat differently - and be passed onto their resp. methods in ctrl.visualization
    #TODO: change/remove if/when they can be updated to use this system
    BUILT_IN_VISUALIZATIONS = [
        'trackster',
        'circster',
        'sweepster',
        'phyloviz'
    ]
    # where to search for visualiztion templates (relative to templates/webapps/galaxy)
    # this can be overridden individually in the config entries
    TEMPLATE_ROOT = 'visualization'

    def __str__( self ):
        listings_keys_str = ','.join( self.listings.keys() ) if self.listings else ''
        return 'VisualizationsRegistry(%s)' %( listings_keys_str )

    def __init__( self, galaxy_root, configuration_filepath ):
        # load the registry from the given xml file using the given parser
        configuration_filepath = os.path.join( galaxy_root, configuration_filepath )
        configuration_filepath = self.check_conf_filepath( configuration_filepath )
        self.configuration_filepath = configuration_filepath
        self.load()

        # what to use to parse query strings into resources/vars for the template
        self.resource_parser = ResourceParser()

    def check_conf_filepath( self, configuration_filepath ):
        """
        If given file at filepath exists, return that filepath. If not,
        see if filepath + '.sample' exists and, if so, copy that into filepath.

        If neither original or sample exist, throw an IOError (currently,
        this is a requireed file).
        """
        if os.path.exists( configuration_filepath ):
            return configuration_filepath
        else:
            sample_file = configuration_filepath + '.sample'
            if os.path.exists( sample_file ):
                shutil.copy2( sample_file, configuration_filepath )
                return configuration_filepath
        raise IOError( 'visualization configuration file (%s) not found' %( configuration_filepath ) )

    def load( self ):
        """
        Builds the registry by parsing the xml in `self.configuration_filepath`
        and stores the results in `self.listings`.

        Provided as separate method from `__init__` in order to re-load a
        new configuration without restarting the instance.
        """
        self.listings = VisualizationsConfigParser.parse( self.configuration_filepath )

    # -- building links to visualizations from objects --
    def get_visualizations( self, trans, target_object ):
        """
        Get the names of visualizations usable on the `target_object` and
        the urls to call in order to render the visualizations.
        """
        #TODO:?? a list of objects? YAGNI?
        # a little weird to pass trans because this registry is part of the trans.app
        applicable_visualizations = []
        for vis_name, listing_data in self.listings.items():

            data_sources = listing_data[ 'data_sources' ]
            for data_source in data_sources:
                # currently a model class is required
                model_class = data_source[ 'model_class' ]
                if not isinstance( target_object, model_class ):
                    continue

                # tests are optional - default is the above class test
                tests = data_source[ 'tests' ]
                if tests and not self.is_object_applicable( trans, target_object, tests ):
                    continue

                param_data = data_source[ 'to_params' ]
                url = self.get_visualization_url( trans, target_object, vis_name, param_data )
                link_text = listing_data.get( 'link_text', None )
                if not link_text:
                    # default to visualization name, titlecase, and replace underscores
                    link_text = vis_name.title().replace( '_', ' ' )
                render_location = listing_data.get( 'render_location' )
                # remap some of these vars for direct use in ui.js, PopupMenu (e.g. text->html)
                applicable_visualizations.append({
                    'href'  : url,
                    'html'  : link_text,
                    'target': render_location
                })

        return applicable_visualizations

    def is_object_applicable( self, trans, target_object, data_source_tests ):
        """
        Run a visualization's data_source tests to find out if
        it be applied to the target_object.
        """
        for test in data_source_tests:
            test_type   = test[ 'type' ]
            result_type = test[ 'result_type' ]
            test_result = test[ 'result' ]
            test_fn     = test[ 'fn' ]
            #log.debug( '%s %s: %s, %s, %s, %s', str( target_object ), 'is_object_applicable',
            #           test_type, result_type, test_result, test_fn )

            if test_type == 'isinstance':
                # parse test_result based on result_type (curr: only datatype has to do this)
                if result_type == 'datatype':
                    # convert datatypes to their actual classes (for use with isinstance)
                    test_result = trans.app.datatypes_registry.get_datatype_class_by_name( test_result )
                    if not test_result:
                        # warn if can't find class, but continue
                        log.warn( 'visualizations_registry cannot find class (%s) for applicability test', test_result )
                        continue

            if test_fn( target_object, test_result ):
                #log.debug( 'test passed' )
                return True

        return False

    def get_visualization_url( self, trans, target_object, visualization_name, param_data ):
        """
        Generates a url for the visualization with `visualization_name`
        for use with the given `target_object` with a query string built
        from the configuration data in `param_data`.
        """
        #precondition: the target_object should be usable by the visualization (accrd. to data_sources)
        # convert params using vis.data_source.to_params
        params = self.get_url_params( trans, target_object, param_data )

        # we want existing visualizations to work as normal but still be part of the registry (without mod'ing)
        #   so generate their urls differently
        url = None
        if visualization_name in self.BUILT_IN_VISUALIZATIONS:
            url = url_for( controller='visualization', action=visualization_name, **params )
        else:
            url = url_for( controller='visualization', action='render',
                           visualization_name=visualization_name, **params )

        #TODO:?? not sure if embedded would fit/used here? or added in client...
        return url

    def get_url_params( self, trans, target_object, param_data ):
        """
        Convert the applicable objects and assoc. data into a param dict
        for a url query string to add to the url that loads the visualization.
        """
        params = {}
        for to_param_name, to_param_data in param_data.items():
            #TODO??: look into params as well? what is required, etc.
            target_attr = to_param_data.get( 'param_attr', None )
            assign = to_param_data.get( 'assign', None )
            # one or the other is needed
            # assign takes precedence (goes last, overwrites)?
            #NOTE this is only one level
            if target_attr and hasattr( target_object, target_attr ):
                params[ to_param_name ] = getattr( target_object, target_attr )
            if assign:
                params[ to_param_name ] = assign

        #NOTE!: don't expose raw ids: encode id, _id
        if params:
            params = trans.security.encode_dict_ids( params )
        return params

    # -- getting resources for visualization templates from link query strings --
    def get_resource_params_and_modifiers( self, visualization_name ):
        """
        Get params and modifiers for the given visualization as a 2-tuple.

        Both `params` and `param_modifiers` default to an empty dictionary.
        """
        visualization = self.listings.get( visualization_name )
        expected_params = visualization.get( 'params', {} )
        param_modifiers = visualization.get( 'param_modifiers', {} )
        return ( expected_params, param_modifiers )

    def query_dict_to_resources( self, trans, controller, visualization_name, query_dict ):
        """
        Use a resource parser, controller, and a visualization's param configuration
        to convert a query string into the resources and variables a visualization
        template needs to start up.
        """
        param_confs, param_modifiers = self.get_resource_params_and_modifiers( visualization_name )
        resources = self.resource_parser.parse_parameter_dictionary(
            trans, controller, param_confs, query_dict, param_modifiers )
        return resources


# ------------------------------------------------------------------- parsing the config file
class ParsingException( ValueError ):
    """
    An exception class for errors that occur during parsing of the visualizations
    framework configuration XML file.
    """
    pass


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
    VALID_RENDER_LOCATIONS = [ 'galaxy_main', '_top', '_blank' ]

    @classmethod
    def parse( cls, xml_filepath, debug=True ):
        """
        Static class interface
        """
        return cls( debug ).parse_file( xml_filepath )

    def __init__( self, debug=False ):
        self.debug = debug

        # what parsers should be used for sub-components
        self.data_source_parser = DataSourceParser()
        self.param_parser = ParamParser()
        self.param_modifier_parser = ParamModifierParser()

    def parse_file( self, xml_filepath ):
        """
        Parse the given XML file for visualizations data.

        If an error occurs while parsing a visualizations entry it is skipped.
        """
        returned = {}
        try:
            xml_tree = galaxy.util.parse_xml( xml_filepath )
            for visualization_conf in xml_tree.getroot().findall( 'visualization' ):
                visualization = None
                visualization_name = visualization_conf.get( 'name' )

                try:
                    visualization = self.parse_visualization( visualization_conf )
                # skip vis' with parsing errors - don't shutdown the startup
                except ParsingException, parse_exc:
                    log.error( 'Skipped visualization configuration "%s" due to parsing errors: %s',
                        visualization_name, str( parse_exc ), exc_info=self.debug )

                if visualization:
                    returned[ visualization_name ] = visualization

        except Exception, exc:
            log.error( 'Error parsing visualization configuration file %s: %s',
                xml_filepath, str( exc ), exc_info=( not self.debug ) )
            #TODO: change when this is required
            if self.debug:
                raise

        return returned

    def parse_visualization( self, xml_tree ):
        """
        Parse the template, name, and any data_sources and params from the
        given `xml_tree` for a visualization.
        """
        returned = {}

        # data_sources are the kinds of objects/data associated with the visualization
        #   e.g. views on HDAs can use this to find out what visualizations are applicable to them
        data_sources = []
        data_sources_confs = xml_tree.find( 'data_sources' )
        for data_source_conf in data_sources_confs.findall( 'data_source' ):
            data_source = self.data_source_parser.parse( data_source_conf )
            if data_source:
                data_sources.append( data_source )
        # data_sources are not required
        if not data_sources:
            raise ParsingException( 'No valid data_sources for visualization' )
        returned[ 'data_sources' ] = data_sources

        # parameters spell out how to convert query string params into resources and data
        #   that will be parsed, fetched, etc. and passed to the template
        # list or dict? ordered or not?
        params = {}
        param_confs = xml_tree.find( 'params' )
        for param_conf in param_confs.findall( 'param' ):
            param = self.param_parser.parse( param_conf )
            if param:
                params[ param_conf.text ]= param
        # params are not required
        if params:
            returned[ 'params' ] = params

        # param modifiers provide extra information for other params (e.g. hda_ldda='hda' -> dataset_id is an hda id)
        # store these modifiers in a 2-level dictionary { target_param: { param_modifier_key: { param_mod_data }
        # ugh - wish we didn't need these
        param_modifiers = {}
        for param_modifier_conf in param_confs.findall( 'param_modifier' ):
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

        # the template to use in rendering the visualization (required)
        template = xml_tree.find( 'template' )
        if template == None or not template.text:
            raise ParsingException( 'template filename required' )
        returned[ 'template' ] = template.text

        # link_text: the string to use for the text of any links/anchors to this visualization
        link_text = xml_tree.find( 'link_text' )
        if link_text != None and link_text.text:
            returned[ 'link_text' ] = link_text

        # render_location: where in the browser to open the rendered visualization
        # defaults to: galaxy_main
        render_location = xml_tree.find( 'render_location' )
        if( ( render_location != None and render_location.text )
        and ( render_location.text in self.VALID_RENDER_LOCATIONS ) ):
            returned[ 'render_location' ] = render_location.text
        else:
            returned[ 'render_location' ] = 'galaxy_main'
        # consider unifying the above into it's own element and parsing method

        return returned


# ------------------------------------------------------------------- parsing a query string into resources
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
        'HistoryDatasetAssociation',
        'LibraryDatasetDatasetAssociation'
    ]
    ATTRIBUTE_SPLIT_CHAR = '.'
    # these are the allowed object attributes to use in data source tests
    #   any attribute element not in this list will throw a parsing ParsingExcepion
    ALLOWED_DATA_SOURCE_ATTRIBUTES = [
        'datatype'
    ]

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
        to_params = self.parse_to_params( xml_tree.findall( 'to_param' ) )
        if to_params:
            returned[ 'to_params' ] = to_params

        return returned

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
            log.debug( 'available data_source model_classes: %s' %( str( self.ALLOWED_MODEL_CLASSES ) ) )
            raise ParsingException( 'Invalid data_source model_class: %s' %( xml_tree.text ) )

        # look up the model from the model module returning an empty data_source if not found
        model_class = getattr( galaxy.model, xml_tree.text, None )
        return model_class

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
        return lambda o: getattr( self._build_getattr_lambda( attr_name_list[:-1] ), next_attr_name )

    def parse_tests( self, xml_tree_list ):
        """
        Returns a list of test dictionaries that the registry can use
        against a given object to determine if the visualization can be
        used with the object.
        """
        # tests should NOT include expensive operations: reading file data, running jobs, etc.
        # do as much here as possible to reduce the overhead of seeing if a visualization is applicable
        # currently tests are or'd only (could be and'd or made into compound boolean tests)
        tests = []
        if not xml_tree_list:
            return tests

        for test_elem in xml_tree_list:
            test_type = test_elem.get( 'type' )
            test_result = test_elem.text
            if not test_type or not test_result:
                log.warn( 'Skipping test. Needs both type attribute and text node to be parsed: '
                        + '%s, %s' %( test_type, test_elem.text ) )
                continue

            # test_attr can be a dot separated chain of object attributes (e.g. dataset.datatype) - convert to list
            #TODO: too dangerous - constrain these to some allowed list
            test_attr = test_elem.get( 'test_attr' )
            test_attr = test_attr.split( self.ATTRIBUTE_SPLIT_CHAR ) if isinstance( test_attr, str ) else []
            # build a lambda function that gets the desired attribute to test
            getter = self._build_getattr_lambda( test_attr )

            # result type should tell the registry how to convert the result before the test
            test_result_type = test_elem.get( 'result_type' ) or 'string'

            # test functions should be sent an object to test, and the parsed result expected from the test
            #TODO: currently, isinstance and string equivalance are the only test types supported
            if test_type == 'isinstance':
                #TODO: wish we could take this further but it would mean passing in the datatypes_registry
                test_fn = lambda o, result: isinstance( getter( o ), result )

            # default to simple (string) equilavance (coercing the test_attr to a string)
            else:
                test_fn = lambda o, result: str( getter( o ) ) == result

            tests.append({
                'type'          : test_type,
                'result'        : test_result,
                'result_type'   : test_result_type,
                'fn'            : test_fn
            })

        return tests

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
            if assign != None:
                param[ 'assign' ] = assign

            # param_attr is the attribute of the object (that the visualization will be applied to)
            #   that should be converted into a query param (e.g. param_attr="id" -> dataset_id)
            #TODO:?? use the build attr getter here?
            # simple (1 lvl) attrs for now
            param_attr = element.get( 'param_attr' )
            if param_attr != None:
                param[ 'param_attr' ] = param_attr
            # element must have either param_attr or assign? what about no params (the object itself)
            if not param_attr and not assign:
                raise ParsingException( 'to_param requires either assign or param_attr attributes: %s', param_name )

            #TODO: consider making the to_param name an attribute (param="hda_ldda") and the text what would
            #           be used for the conversion - this would allow CDATA values to be passed
            #<to_param param="json" type="assign"><![CDATA[{ "one": 1, "two": 2 }]]></to_param>

            if param:
                to_param_dict[ param_name ] = param

        return to_param_dict


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
        #TODO: currently unused
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
        #TODO: set parsers and validaters, convert here
        return param_type


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


class ResourceParser( object ):
    """
    Given a parameter dictionary (often a converted query string) and a
    configuration dictionary (curr. only VisualizationsRegistry uses this),
    convert the entries in the parameter dictionary into resources (Galaxy
    models, primitive types, lists of either, etc.) and return
    in a new dictionary.

    The keys used to store the new values can optionally be re-mapped to
    new keys (e.g. dataset_id="NNN" -> hda=<HistoryDatasetAsscoation>).
    """
    #TODO: kinda torn as to whether this belongs here or in controllers.visualization
    #   taking the (questionable) design path of passing a controller in
    #       (which is the responsible party for getting model, etc. resources )
    # consider making this a base controller? use get_object for the model resources
    #   don't like passing in the app, tho
    def parse_parameter_dictionary( self, trans, controller, param_config_dict, query_params, param_modifiers=None ):
        """
        Parse all expected params from the query dictionary `query_params`.

        If param is required and not present, raises a `KeyError`.
        """
        # parse the modifiers first since they modify the params coming next
        #TODO: this is all really for hda_ldda - which we could replace with model polymorphism
        params_that_modify_other_params = self.parse_parameter_modifiers(
            trans, controller, param_modifiers, query_params )

        resources = {}
        for param_name, param_config in param_config_dict.items():
            # optionally rename the variable returned, defaulting to the original name
            var_name_in_template = param_config.get( 'var_name_in_template', param_name )

            # if the param is present, get it's value, any param modifiers for that param, and parse it into a resource
            # use try catch here and not caller to fall back on the default value or re-raise if required
            resource = None
            query_val = query_params.get( param_name, None )
            if query_val is not None:
                try:
                    target_param_modifiers = params_that_modify_other_params.get( param_name, None )
                    resource = self.parse_parameter( trans, controller, param_config,
                        query_val, param_modifiers=target_param_modifiers )

                except Exception, exception:
                    log.warn( 'Exception parsing visualization param from query: '
                            + '%s, %s, (%s) %s' %( param_name, query_val, str( type( exception ) ), str( exception ) ))
                    resource = None

            # here - we've either had no value in the query_params or there was a failure to parse
            #   so: error if required, otherwise get a default (which itself defaults to None)
            if resource == None:
                if param_config[ 'required' ]:
                    raise KeyError( 'required param %s not found in URL' %( param_name ) )
                resource = self.parse_parameter_default( trans, param_config )

            resources[ var_name_in_template ] = resource

        return resources

    #TODO: I would LOVE to rip modifiers out completely
    def parse_parameter_modifiers( self, trans, controller, param_modifiers, query_params ):
        """
        Parse and return parameters that are meant to modify other parameters,
        be grouped with them, or are needed to successfully parse other parameters.
        """
        # only one level of modification - down that road lies madness
        # parse the modifiers out of query_params first since they modify the other params coming next
        parsed_modifiers = {}
        if not param_modifiers:
            return parsed_modifiers
        #precondition: expects a two level dictionary
        # { target_param_name -> { param_modifier_name -> { param_modifier_data }}}
        for target_param_name, modifier_dict in param_modifiers.items():
            parsed_modifiers[ target_param_name ] = target_modifiers = {}

            for modifier_name, modifier_config in modifier_dict.items():
                query_val = query_params.get( modifier_name, None )
                if query_val is not None:
                    modifier = self.parse_parameter( trans, controller, modifier_config, query_val )
                    target_modifiers[ modifier_name ] = modifier
                else:
                    #TODO: required attr?
                    target_modifiers[ modifier_name ] = self.parse_parameter_default( trans, modifier_config )

        return parsed_modifiers

    def parse_parameter_default( self, trans, param_config ):
        """
        Parse any default values for the given param, defaulting the default
        to `None`.
        """
        # currently, *default* default is None, so this is quaranteed to be part of the dictionary
        default = param_config[ 'default' ]
        # if default is None, do not attempt to parse it
        if default == None:
            return default
        # otherwise, parse (currently param_config['default'] is a string just like query param and needs to be parsed)
        #   this saves us the trouble of parsing the default when the config file is read
        #   (and adding this code to the xml parser)
        return self.parse_parameter( trans, param_config, default )

    def parse_parameter( self, trans, controller, expected_param_data, query_param,
                         recurse=True, param_modifiers=None ):
        """
        Use data in `expected_param_data` to parse `query_param` from a string into
        a resource usable directly by a template.

        'Primitive' types (string, int, etc.) are parsed here and more complex
        resources (such as ORM models) are parsed via the `controller` passed
        in.
        """
        param_type = expected_param_data.get( 'type' )
        constrain_to = expected_param_data.get( 'constrain_to' )
        csv = expected_param_data.get( 'csv' )

        parsed_param = None

        # handle recursion for csv values
        if csv and recurse:
            parsed_param = []
            query_param_list = galaxy.util.listify( query_param )
            for query_param in query_param_list:
                parsed_param.append( self._parse_param( trans, expected_param_data, query_param, recurse=False ) )
            return parsed_param

        primitive_parsers = {
            'str'   : lambda param: galaxy.util.sanitize_html.sanitize_html( param, 'utf-8' ),
            'bool'  : lambda param: galaxy.util.string_as_bool( param ),
            'int'   : lambda param: int( param ),
            'float' : lambda param: float( param ),
            #'date'  : lambda param: ,
            'json'  : ( lambda param: galaxy.util.json.from_json_string(
                            galaxy.util.sanitize_html.sanitize_html( param ) ) ),
        }
        parser = primitive_parsers.get( param_type, None )
        if parser:
            #TODO: what about param modifiers on primitives?
            parsed_param = parser( query_param )

        #TODO: constrain_to
        # this gets complicated - for strings - relatively simple but still requires splitting and using in
        # for more complicated cases (ints, json) this gets weird quick
        #TODO:?? remove?

        # db models
        #TODO: subclass here?
        elif param_type == 'visualization':
            encoded_visualization_id = query_param
            #TODO:?? some fallback if there's no get_X in controller that's passed?
            parsed_param = controller.get_visualization( trans, encoded_visualization_id,
                check_ownership=False, check_accessible=True )

        elif param_type == 'dataset':
            encoded_dataset_id = query_param
            # really an hda...
            parsed_param = controller.get_dataset( trans, encoded_dataset_id,
                check_ownership=False, check_accessible=True )

        elif param_type == 'hda_or_ldda':
            encoded_dataset_id = query_param
            # needs info from another param...
            hda_ldda = param_modifiers.get( 'hda_ldda' )
            parsed_param = controller.get_hda_or_ldda( trans, hda_ldda, encoded_dataset_id )

        #TODO: ideally this would check v. a list of valid dbkeys
        elif param_type == 'dbkey':
            dbkey = query_param
            parsed_param = galaxy.util.sanitize_html.sanitize_html( dbkey, 'utf-8' )

        #print ( '%s, %s -> %s, %s' %( param_type, query_param, str( type( parsed_param ) ), parsed_param ) )
        return parsed_param
