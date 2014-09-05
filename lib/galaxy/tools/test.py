import os
import os.path
import uuid
from parameters import basic
from parameters import grouping
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
def parse_tests_elem(tool, tests_elem):
    """
    Build ToolTestBuilder objects for each "<test>" elements and
    return default interactor (if any).
    """
    default_interactor = os.environ.get( 'GALAXY_TEST_DEFAULT_INTERACTOR', DEFAULT_INTERACTOR )
    tests_default_interactor = tests_elem.get( 'interactor', default_interactor )
    tests = []
    for i, test_elem in enumerate( tests_elem.findall( 'test' ) ):
        test = ToolTestBuilder( tool, test_elem, i, default_interactor=tests_default_interactor )
        tests.append( test )
    return tests


class ToolTestBuilder( object ):
    """
    Encapsulates information about a tool test, and allows creation of a
    dynamic TestCase class (the unittest framework is very class oriented,
    doing dynamic tests in this way allows better integration)
    """

    def __init__( self, tool, test_elem, i, default_interactor ):
        name = test_elem.get( 'name', 'Test-%d' % (i + 1) )
        maxseconds = int( test_elem.get( 'maxseconds', DEFAULT_MAX_SECS ) )

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

        self.__parse_elem( test_elem, i, default_interactor )

    def test_data( self ):
        """
        Iterator over metadata representing the required files for upload.
        """
        return test_data_iter( self.required_files )

    def __matching_case_for_value( self, cond, declared_value ):
        test_param = cond.test_param
        if isinstance(test_param, basic.BooleanToolParameter):
            if declared_value is None:
                # No explicit value for param in test case, determine from default
                query_value = test_param.checked
            else:
                # Test case supplied value, check cases against this.
                query_value = string_as_bool( declared_value )
            matches_declared_value = lambda case_value: string_as_bool(case_value) == query_value
        elif isinstance(test_param, basic.SelectToolParameter):
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

    def __parse_elem( self, test_elem, i, default_interactor ):
        try:
            # Mechanism test code uses for interacting with Galaxy instance,
            # until 'api' is the default switch this to API to use its new
            # features. Once 'api' is the default set to 'twill' to use legacy
            # features or workarounds.
            self.interactor = test_elem.get( 'interactor', default_interactor )

            self.__preprocess_input_elems( test_elem )
            self.__parse_inputs_elems( test_elem, i )

            self.outputs = parse_output_elems( test_elem )
            num_outputs = test_elem.get( 'expect_num_outputs', None )
            if num_outputs:
                num_outputs = int( num_outputs )
            self.num_outputs = num_outputs
        except Exception, e:
            self.error = True
            self.exception = e

    def __preprocess_input_elems( self, test_elem ):
        expand_input_elems( test_elem )

    def __parse_inputs_elems( self, test_elem, i ):
        raw_inputs = []
        for param_elem in test_elem.findall( "param" ):
            name, value, attrib = parse_param_elem( param_elem, i )
            raw_inputs.append( ( name, value, attrib ) )
        self.inputs = self.__process_raw_inputs( self.tool.inputs, raw_inputs )

    def __process_raw_inputs( self, tool_inputs, raw_inputs, parent_context=None ):
        """
        Recursively expand flat list of inputs into "tree" form of flat list
        (| using to nest to new levels) structure and expand dataset
        information as proceeding to populate self.required_files.
        """
        parent_context = parent_context or RootParamContext()
        expanded_inputs = {}
        for key, value in tool_inputs.items():
            if isinstance( value, grouping.Conditional ):
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

            elif isinstance( value, grouping.Repeat ):
                repeat_index = 0
                while True:
                    context = ParamContext( name=value.name, index=repeat_index, parent_context=parent_context )
                    updated = False
                    for r_name, r_value in value.inputs.iteritems():
                        expanded_input = self.__process_raw_inputs( { context.for_state() : r_value }, raw_inputs, parent_context=context )
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
                    if isinstance( value, basic.DataToolParameter ):
                        if not isinstance(param_value, list):
                            param_value = [ param_value ]
                        processed_value = [ self.__add_uploaded_dataset( context.for_state(), v, param_extra, value ) for v in param_value ]
                    if isinstance( value, basic.DataCollectionToolParameter ):
                        assert 'collection' in param_extra
                        collection_def = param_extra[ 'collection' ]
                        for ( name, value, extra ) in collection_def.collect_inputs():
                            require_file( name, value, extra, self.required_files )
                        processed_value = collection_def
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


def parse_param_elem( param_elem, i=0 ):
    attrib = dict( param_elem.attrib )
    if 'values' in attrib:
        value = attrib[ 'values' ].split( ',' )
    elif 'value' in attrib:
        value = attrib['value']
    else:
        value = None
    attrib['children'] = list( param_elem.getchildren() )
    if attrib['children']:
        # At this time, we can assume having children only
        # occurs on DataToolParameter test items but this could
        # change and would cause the below parsing to change
        # based upon differences in children items
        attrib['metadata'] = []
        attrib['composite_data'] = []
        attrib['edit_attributes'] = []
        # Composite datasets need to be renamed uniquely
        composite_data_name = None
        for child in attrib['children']:
            if child.tag == 'composite_data':
                attrib['composite_data'].append( child )
                if composite_data_name is None:
                    # Generate a unique name; each test uses a
                    # fresh history.
                    composite_data_name = '_COMPOSITE_RENAMED_t%d_%s' \
                        % ( i, uuid.uuid1().hex )
            elif child.tag == 'metadata':
                attrib['metadata'].append( child )
            elif child.tag == 'metadata':
                attrib['metadata'].append( child )
            elif child.tag == 'edit_attributes':
                attrib['edit_attributes'].append( child )
            elif child.tag == 'collection':
                attrib[ 'collection' ] = TestCollectionDef( child )
        if composite_data_name:
            # Composite datasets need implicit renaming;
            # inserted at front of list so explicit declarations
            # take precedence
            attrib['edit_attributes'].insert( 0, { 'type': 'name', 'value': composite_data_name } )
    name = attrib.pop( 'name' )
    return ( name, value, attrib )


def parse_output_elems( test_elem ):
    outputs = []
    for output_elem in test_elem.findall( "output" ):
        name, file, attributes = __parse_output_elem( output_elem )
        outputs.append( ( name, file, attributes ) )
    return outputs


def __parse_output_elem( output_elem ):
    attrib = dict( output_elem.attrib )
    name = attrib.pop( 'name', None )
    if name is None:
        raise Exception( "Test output does not have a 'name'" )

    file, attributes = __parse_test_attributes( output_elem, attrib )
    primary_datasets = {}
    for primary_elem in ( output_elem.findall( "discovered_dataset" ) or [] ):
        primary_attrib = dict( primary_elem.attrib )
        designation = primary_attrib.pop( 'designation', None )
        if designation is None:
            raise Exception( "Test primary dataset does not have a 'designation'" )
        primary_datasets[ designation ] = __parse_test_attributes( primary_elem, primary_attrib )
    attributes[ "primary_datasets" ] = primary_datasets
    return name, file, attributes


def __parse_test_attributes( output_elem, attrib ):
    assert_list = __parse_assert_list( output_elem )
    file = attrib.pop( 'file', None )
    # File no longer required if an list of assertions was present.
    attributes = {}
    # Method of comparison
    attributes['compare'] = attrib.pop( 'compare', 'diff' ).lower()
    # Number of lines to allow to vary in logs (for dates, etc)
    attributes['lines_diff'] = int( attrib.pop( 'lines_diff', '0' ) )
    # Allow a file size to vary if sim_size compare
    attributes['delta'] = int( attrib.pop( 'delta', '10000' ) )
    attributes['sort'] = string_as_bool( attrib.pop( 'sort', False ) )
    extra_files = []
    if 'ftype' in attrib:
        attributes['ftype'] = attrib['ftype']
    for extra in output_elem.findall( 'extra_files' ):
        extra_files.append( __parse_extra_files_elem( extra ) )
    metadata = {}
    for metadata_elem in output_elem.findall( 'metadata' ):
        metadata[ metadata_elem.get('name') ] = metadata_elem.get( 'value' )
    if not (assert_list or file or extra_files or metadata):
        raise Exception( "Test output defines nothting to check (e.g. must have a 'file' check against, assertions to check, etc...)")
    attributes['assert_list'] = assert_list
    attributes['extra_files'] = extra_files
    attributes['metadata'] = metadata
    return file, attributes


def __parse_assert_list( output_elem ):
    assert_elem = output_elem.find("assert_contents")
    assert_list = None

    # Trying to keep testing patch as localized as
    # possible, this function should be relocated
    # somewhere more conventional.
    def convert_elem(elem):
        """ Converts and XML element to a dictionary format, used by assertion checking code. """
        tag = elem.tag
        attributes = dict( elem.attrib )
        child_elems = list( elem.getchildren() )
        converted_children = []
        for child_elem in child_elems:
            converted_children.append( convert_elem(child_elem) )
        return {"tag": tag, "attributes": attributes, "children": converted_children}
    if assert_elem is not None:
        assert_list = []
        for assert_child in list(assert_elem):
            assert_list.append(convert_elem(assert_child))

    return assert_list


def __parse_extra_files_elem( extra ):
    # File or directory, when directory, compare basename
    # by basename
    extra_type = extra.get( 'type', 'file' )
    extra_name = extra.get( 'name', None )
    assert extra_type == 'directory' or extra_name is not None, \
        'extra_files type (%s) requires a name attribute' % extra_type
    extra_value = extra.get( 'value', None )
    assert extra_value is not None, 'extra_files requires a value attribute'
    extra_attributes = {}
    extra_attributes['compare'] = extra.get( 'compare', 'diff' ).lower()
    extra_attributes['delta'] = extra.get( 'delta', '0' )
    extra_attributes['lines_diff'] = int( extra.get( 'lines_diff', '0' ) )
    extra_attributes['sort'] = string_as_bool( extra.get( 'sort', False ) )
    return extra_type, extra_value, extra_name, extra_attributes


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


class TestCollectionDef( object ):

    def __init__( self, elem ):
        self.elements = []
        attrib = dict( elem.attrib )
        self.collection_type = attrib[ "type" ]
        self.name = attrib.get( "name", "Unnamed Collection" )
        for element in elem.findall( "element" ):
            element_attrib = dict( element.attrib )
            element_identifier = element_attrib[ "name" ]
            nested_collection_elem = element.find( "collection" )
            if nested_collection_elem:
                self.elements.append( ( element_identifier, TestCollectionDef( nested_collection_elem ) ) )
            else:
                self.elements.append( ( element_identifier, parse_param_elem( element ) ) )

    def collect_inputs( self ):
        inputs = []
        for element in self.elements:
            value = element[ 1 ]
            if isinstance( value, TestCollectionDef ):
                inputs.extend( value.collect_inputs() )
            else:
                inputs.append( value )
        return inputs


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
