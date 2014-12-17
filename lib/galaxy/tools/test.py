import os
import os.path
import galaxy.tools.parameters.basic
import galaxy.tools.parameters.grouping
from galaxy.util import string_as_bool
try:
    from nose.tools import nottest
except ImportError:
    nottest = lambda x: x
import logging

log = logging.getLogger( __name__ )

DEFAULT_FTYPE = 'auto'
DEFAULT_DBKEY = 'hg17'
DEFAULT_INTERACTOR = "api"  # Default mechanism test code uses for interacting with Galaxy instance.
DEFAULT_MAX_SECS = 120


@nottest
def parse_tests(tool, tests_source):
    """
    Build ToolTestBuilder objects for each "<test>" elements and
    return default interactor (if any).
    """
    default_interactor = os.environ.get( 'GALAXY_TEST_DEFAULT_INTERACTOR', DEFAULT_INTERACTOR )
    tests_dict = tests_source.parse_tests_to_dict()
    tests_default_interactor = tests_dict.get( 'interactor', default_interactor )
    tests = []
    for i, test_dict in enumerate(tests_dict.get('tests', [])):
        test = ToolTestBuilder( tool, test_dict, i, default_interactor=tests_default_interactor )
        tests.append( test )
    return tests


class ToolTestBuilder( object ):
    """
    Encapsulates information about a tool test, and allows creation of a
    dynamic TestCase class (the unittest framework is very class oriented,
    doing dynamic tests in this way allows better integration)
    """

    def __init__( self, tool, test_dict, i, default_interactor ):
        name = test_dict.get( 'name', 'Test-%d' % (i + 1) )
        maxseconds = int( test_dict.get( 'maxseconds', DEFAULT_MAX_SECS ) )

        self.tool = tool
        self.name = name
        self.maxseconds = maxseconds
        self.required_files = []
        self.inputs = []
        self.outputs = []
        self.num_outputs = None  # By default do not making assertions on
                                 # number of outputs - but to test filtering
                                 # allow explicitly state number of outputs.
        self.error = False
        self.exception = None

        self.__handle_test_dict( test_dict, i, default_interactor )

    def test_data( self ):
        """
        Iterator over metadata representing the required files for upload.
        """
        return test_data_iter( self.required_files )

    def __matching_case_for_value( self, cond, declared_value ):
        test_param = cond.test_param
        if isinstance(test_param, galaxy.tools.parameters.basic.BooleanToolParameter):
            if declared_value is None:
                # No explicit value for param in test case, determine from default
                query_value = test_param.checked
            else:
                # Test case supplied value, check cases against this.
                query_value = string_as_bool( declared_value )
            matches_declared_value = lambda case_value: string_as_bool(case_value) == query_value
        elif isinstance(test_param, galaxy.tools.parameters.basic.SelectToolParameter):
            if declared_value is not None:
                # Test case supplied explicit value to check against.
                matches_declared_value = lambda case_value: case_value == declared_value
            elif test_param.static_options:
                # No explicit value in test case, not much to do if options are dynamic but
                # if static options are available can find the one specified as default or
                # fallback on top most option (like GUI).
                for (name, value, selected) in test_param.static_options:
                    if selected:
                        default_option = name
                else:
                    first_option = test_param.static_options[0]
                    first_option_value = first_option[1]
                    default_option = first_option_value
                matches_declared_value = lambda case_value: case_value == default_option
            else:
                # No explicit value for this param and cannot determine a
                # default - give up. Previously this would just result in a key
                # error exception.
                msg = "Failed to find test parameter value specification required for conditional %s" % cond.name
                raise Exception( msg )

        # Check the tool's defined cases against predicate to determine
        # selected or default.
        for i, case in enumerate( cond.cases ):
            if matches_declared_value( case.value ):
                return case
        else:
            msg_template = "%s - Failed to find case matching value (%s) for test parameter specification for conditional %s. Remainder of test behavior is unspecified."
            msg = msg_template % ( self.tool.id, declared_value, cond.name )
            log.info( msg )

    def __split_if_str( self, value ):
        split = isinstance(value, str)
        if split:
            value = value.split(",")
        return value

    def __handle_test_dict( self, test_dict, i, default_interactor ):
        try:
            # Mechanism test code uses for interacting with Galaxy instance,
            # until 'api' is the default switch this to API to use its new
            # features. Once 'api' is the default set to 'twill' to use legacy
            # features or workarounds.
            self.interactor = test_dict.get( 'interactor', default_interactor )

            self.inputs = self.__process_raw_inputs( self.tool.inputs, test_dict["inputs"] )
            self.outputs = test_dict["outputs"]
            num_outputs = test_dict.get( 'expect_num_outputs', None )
            if num_outputs:
                num_outputs = int( num_outputs )
            self.num_outputs = num_outputs
            self.command_line = test_dict.get("command", None)
            self.stdout = test_dict.get("stdout", None)
            self.stderr = test_dict.get("stderr", None)
            self.expect_exit_code = test_dict.get("expect_exit_code", None)
            self.expect_failure = test_dict.get("expect_failure", False)
        except Exception, e:
            self.error = True
            self.exception = e

    def __process_raw_inputs( self, tool_inputs, raw_inputs, parent_context=None ):
        """
        Recursively expand flat list of inputs into "tree" form of flat list
        (| using to nest to new levels) structure and expand dataset
        information as proceeding to populate self.required_files.
        """
        parent_context = parent_context or RootParamContext()
        expanded_inputs = {}
        for key, value in tool_inputs.items():
            if isinstance( value, galaxy.tools.parameters.grouping.Conditional ):
                cond_context = ParamContext( name=value.name, parent_context=parent_context )
                case_context = ParamContext( name=value.test_param.name, parent_context=cond_context )
                raw_input = case_context.extract_value( raw_inputs )
                case_value = raw_input[ 1 ] if raw_input else None
                case = self.__matching_case_for_value( value, case_value )
                if case:
                    for input_name, input_value in case.inputs.items():
                        case_inputs = self.__process_raw_inputs( { input_name: input_value }, raw_inputs, parent_context=cond_context )
                        expanded_inputs.update( case_inputs )
                    expanded_case_value = self.__split_if_str( case.value )
                    if case_value is not None:
                        # A bit tricky here - we are growing inputs with value
                        # that may be implicit (i.e. not defined by user just
                        # a default defined in tool). So we do not want to grow
                        # expanded_inputs and risk repeat block viewing this
                        # as a new instance with value defined and hence enter
                        # an infinite loop - hence the "case_value is not None"
                        # check.
                        expanded_inputs[ case_context.for_state() ] = expanded_case_value

            elif isinstance( value, galaxy.tools.parameters.grouping.Repeat ):
                repeat_index = 0
                while True:
                    context = ParamContext( name=value.name, index=repeat_index, parent_context=parent_context )
                    updated = False
                    for r_name, r_value in value.inputs.iteritems():
                        expanded_input = self.__process_raw_inputs( { context.for_state(): r_value }, raw_inputs, parent_context=context )
                        if expanded_input:
                            expanded_inputs.update( expanded_input )
                            updated = True
                    if not updated:
                        break
                    repeat_index += 1
            else:
                context = ParamContext( name=value.name, parent_context=parent_context )
                raw_input = context.extract_value( raw_inputs )
                if raw_input:
                    (name, param_value, param_extra) = raw_input
                    param_value = self.__split_if_str( param_value )
                    if isinstance( value, galaxy.tools.parameters.basic.DataToolParameter ):
                        if not isinstance(param_value, list):
                            param_value = [ param_value ]
                        map( lambda v: self.__add_uploaded_dataset( context.for_state(), v, param_extra, value ), param_value )
                        processed_value = param_value
                    elif isinstance( value, galaxy.tools.parameters.basic.DataCollectionToolParameter ):
                        assert 'collection' in param_extra
                        collection_def = param_extra[ 'collection' ]
                        for ( name, value, extra ) in collection_def.collect_inputs():
                            require_file( name, value, extra, self.required_files )
                        processed_value = collection_def
                    elif isinstance( value, galaxy.tools.parameters.basic.SelectToolParameter ) and hasattr( value, 'static_options' ):
                        # Tests may specify values as either raw value or the value
                        # as they appear in the list - the API doesn't and shouldn't
                        # accept the text value - so we need to convert the text
                        # into the form value.
                        def process_param_value( param_value ):
                            found_value = False
                            value_for_text = None
                            if value.static_options:
                                for (text, opt_value, selected) in value.static_options:
                                    if param_value == opt_value:
                                        found_value = True
                                    if value_for_text is None and param_value == text:
                                        value_for_text = opt_value
                            if not found_value and value_for_text is not None:
                                processed_value = value_for_text
                            else:
                                processed_value = param_value
                            return processed_value
                        # Do replacement described above for lists or singleton
                        # values.
                        if isinstance( param_value, list ):
                            processed_value = map( process_param_value, param_value )
                        else:
                            processed_value = process_param_value( param_value )
                    else:
                        processed_value = param_value
                    expanded_inputs[ context.for_state() ] = processed_value
        return expanded_inputs

    def __add_uploaded_dataset( self, name, value, extra, input_parameter ):
        if value is None:
            assert input_parameter.optional, '%s is not optional. You must provide a valid filename.' % name
            return value
        return require_file( name, value, extra, self.required_files )


@nottest
def test_data_iter( required_files ):
    for fname, extra in required_files:
        data_dict = dict(
            fname=fname,
            metadata=extra.get( 'metadata', [] ),
            composite_data=extra.get( 'composite_data', [] ),
            ftype=extra.get( 'ftype', DEFAULT_FTYPE ),
            dbkey=extra.get( 'dbkey', DEFAULT_DBKEY ),
        )
        edit_attributes = extra.get( 'edit_attributes', [] )

        #currently only renaming is supported
        for edit_att in edit_attributes:
            if edit_att.get( 'type', None ) == 'name':
                new_name = edit_att.get( 'value', None )
                assert new_name, 'You must supply the new dataset name as the value tag of the edit_attributes tag'
                data_dict['name'] = new_name
            else:
                raise Exception( 'edit_attributes type (%s) is unimplemented' % edit_att.get( 'type', None ) )

        yield data_dict


def require_file( name, value, extra, required_files ):
    if ( value, extra ) not in required_files:
        required_files.append( ( value, extra ) )  # these files will be uploaded
    name_change = [ att for att in extra.get( 'edit_attributes', [] ) if att.get( 'type' ) == 'name' ]
    if name_change:
        name_change = name_change[-1].get( 'value' )  # only the last name change really matters
        value = name_change  # change value for select to renamed uploaded file for e.g. composite dataset
    else:
        for end in [ '.zip', '.gz' ]:
            if value.endswith( end ):
                value = value[ :-len( end ) ]
                break
        value = os.path.basename( value )  # if uploading a file in a path other than root of test-data
    return value


class ParamContext(object):

    def __init__( self, name, index=None, parent_context=None ):
        self.parent_context = parent_context
        self.name = name
        self.index = None if index is None else int( index )

    def for_state( self ):
        name = self.name if self.index is None else "%s_%d" % ( self.name, self.index )
        parent_for_state = self.parent_context.for_state()
        if parent_for_state:
            return "%s|%s" % ( parent_for_state, name )
        else:
            return name

    def __str__( self ):
        return "Context[for_state=%s]" % self.for_state()

    def param_names( self ):
        for parent_context_param in self.parent_context.param_names():
            if self.index is not None:
                yield "%s|%s_%d" % ( parent_context_param, self.name, self.index )
            else:
                yield "%s|%s" % ( parent_context_param, self.name )
        if self.index is not None:
            yield "%s_%d" % ( self.name, self.index )
        else:
            yield self.name

    def extract_value( self, raw_inputs ):
        for param_name in self.param_names():
            value = self.__raw_param_found( param_name, raw_inputs)
            if value:
                return value
        return None

    def __raw_param_found( self, param_name, raw_inputs ):
        index = None
        for i, raw_input in enumerate( raw_inputs ):
            if raw_input[ 0 ] == param_name:
                index = i
        if index is not None:
            raw_input = raw_inputs[ index ]
            del raw_inputs[ index ]
            return raw_input
        else:
            return None


class RootParamContext(object):

    def __init__( self ):
        pass

    def for_state( self ):
        return ""

    def param_names( self ):
        return []

    def get_index( self ):
        return 0


def expand_input_elems( root_elem, prefix="" ):
    __append_prefix_to_params( root_elem, prefix )

    repeat_elems = root_elem.findall( 'repeat' )
    indices = {}
    for repeat_elem in repeat_elems:
        name = repeat_elem.get( "name" )
        if name not in indices:
            indices[ name ] = 0
            index = 0
        else:
            index = indices[ name ] + 1
            indices[ name ] = index

        new_prefix = __prefix_join( prefix, name, index=index )
        expand_input_elems( repeat_elem, new_prefix )
        __pull_up_params( root_elem, repeat_elem )
        root_elem.remove( repeat_elem )

    cond_elems = root_elem.findall( 'conditional' )
    for cond_elem in cond_elems:
        new_prefix = __prefix_join( prefix, cond_elem.get( "name" ) )
        expand_input_elems( cond_elem, new_prefix )
        __pull_up_params( root_elem, cond_elem )
        root_elem.remove( cond_elem )


def __append_prefix_to_params( elem, prefix ):
    for param_elem in elem.findall( 'param' ):
        param_elem.set( "name", __prefix_join( prefix, param_elem.get( "name" ) ) )


def __pull_up_params( parent_elem, child_elem ):
    for param_elem in child_elem.findall( 'param' ):
        parent_elem.append( param_elem )
        child_elem.remove( param_elem )


def __prefix_join( prefix, name, index=None ):
    name = name if index is None else "%s_%d" % ( name, index )
    return name if not prefix else "%s|%s" % ( prefix, name )
