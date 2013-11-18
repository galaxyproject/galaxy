import os.path
from parameters import basic
from parameters import grouping
from galaxy.util import string_as_bool
import logging

log = logging.getLogger( __name__ )


class ToolTestBuilder( object ):
    """
    Encapsulates information about a tool test, and allows creation of a
    dynamic TestCase class (the unittest framework is very class oriented,
    doing dynamic tests in this way allows better integration)
    """

    def __init__( self, tool, test_elem, i ):
        name = test_elem.get( 'name', 'Test-%d' % (i + 1) )
        maxseconds = int( test_elem.get( 'maxseconds', '120' ) )

        self.tool = tool
        self.name = name
        self.maxseconds = maxseconds
        self.required_files = []
        self.inputs = []
        self.outputs = []
        self.error = False
        self.exception = None

        self.__parse_elem( test_elem, i )

    def __parse_elem( self, test_elem, i ):
        # Composite datasets need a unique name: each test occurs in a fresh
        # history, but we'll keep it unique per set of tests - use i (test #)
        # and composite_data_names_counter (instance per test #)
        composite_data_names_counter = 0
        try:
            for param_elem in test_elem.findall( "param" ):
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
                                # fresh history
                                composite_data_name = '_COMPOSITE_RENAMED_t%i_d%i' \
                                    % ( i, composite_data_names_counter )
                                composite_data_names_counter += 1
                        elif child.tag == 'metadata':
                            attrib['metadata'].append( child )
                        elif child.tag == 'metadata':
                            attrib['metadata'].append( child )
                        elif child.tag == 'edit_attributes':
                            attrib['edit_attributes'].append( child )
                    if composite_data_name:
                        # Composite datasets need implicit renaming;
                        # inserted at front of list so explicit declarations
                        # take precedence
                        attrib['edit_attributes'].insert( 0, { 'type': 'name', 'value': composite_data_name } )
                self.__add_param( attrib.pop( 'name' ), value, attrib )
            for output_elem in test_elem.findall( "output" ):
                attrib = dict( output_elem.attrib )
                name = attrib.pop( 'name', None )
                if name is None:
                    raise Exception( "Test output does not have a 'name'" )

                assert_list = self.__parse_assert_list( output_elem )
                file = attrib.pop( 'file', None )
                # File no longer required if an list of assertions was present.
                if not assert_list and file is None:
                    raise Exception( "Test output does not have a 'file' to compare with or list of assertions to check")
                attributes = {}
                # Method of comparison
                attributes['compare'] = attrib.pop( 'compare', 'diff' ).lower()
                # Number of lines to allow to vary in logs (for dates, etc)
                attributes['lines_diff'] = int( attrib.pop( 'lines_diff', '0' ) )
                # Allow a file size to vary if sim_size compare
                attributes['delta'] = int( attrib.pop( 'delta', '10000' ) )
                attributes['sort'] = string_as_bool( attrib.pop( 'sort', False ) )
                attributes['extra_files'] = []
                attributes['assert_list'] = assert_list
                if 'ftype' in attrib:
                    attributes['ftype'] = attrib['ftype']
                for extra in output_elem.findall( 'extra_files' ):
                    attributes['extra_files'].append( self.__parse_extra_files_elem( extra ) )
                self.__add_output( name, file, attributes )
        except Exception, e:
            self.error = True
            self.exception = e

    def __parse_assert_list( self, output_elem ):
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

    def __parse_extra_files_elem( self, extra ):
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

    def __add_param( self, name, value, extra ):
        try:
            if name not in self.tool.inputs:
                found_parameter = False
                for input_name, input_value in self.tool.inputs.items():
                    if isinstance( input_value, grouping.Group ):
                        found_parameter, new_value = self.__expand_grouping_for_data_input(name, value, extra, input_name, input_value)
                        if found_parameter:
                            value = new_value
                            break
                if not found_parameter:
                    raise ValueError( "Unable to determine parameter type of test input '%s'. "
                                      "Ensure that the parameter exists and that any container groups are defined first."
                                      % name )
            elif isinstance( self.tool.inputs[name], basic.DataToolParameter ):
                value = self.__add_uploaded_dataset( name, value, extra, self.tool.inputs[name] )
        except Exception, e:
            log.debug( "Error for tool %s: could not add test parameter %s. %s" % ( self.tool.id, name, e ) )
        self.inputs.append( ( name, value, extra ) )

    def __add_output( self, name, file, extra ):
        self.outputs.append( ( name, file, extra ) )

    def __expand_grouping_for_data_input( self, name, value, extra, grouping_name, grouping_value ):
        # Currently handles grouping.Conditional and grouping.Repeat
        if isinstance( grouping_value, grouping.Conditional  ):
            if name == grouping_value.test_param.name:
                return True, value
            case_test_param_value = None
            for input in self.inputs:
                if input[0] == grouping_value.test_param.name:
                    case_test_param_value = input[1]
                    break
            if case_test_param_value is None:
                #case for this group has not been set yet
                return False, value
            for case in grouping_value.cases:
                if case.value == case_test_param_value:
                    break
            if case.value != case_test_param_value:
                return False, value
            #assert case.value == case_test_param_value, "Current case could not be determined for parameter '%s'. Provided value '%s' could not be found in '%s'." % ( grouping_value.name, value, grouping_value.test_param.name )
            if name in case.inputs:
                if isinstance( case.inputs[name], basic.DataToolParameter ):
                    return True, self.__add_uploaded_dataset( name, value, extra, case.inputs[name] )
                else:
                    return True, value
            else:
                for input_name, input_parameter in case.inputs.iteritems():
                    if isinstance( input_parameter, grouping.Group ):
                        found_parameter, new_value = self.__expand_grouping_for_data_input( name, value, extra, input_name, input_parameter )
                        if found_parameter:
                            return True, new_value
        elif isinstance( grouping_value, grouping.Repeat ):
            # FIXME: grouping.Repeat can only handle 1 repeat param element since the param name
            # is something like "input2" and the expanded page display is something like "queries_0|input2".
            # The problem is that the only param name on the page is "input2", and adding more test input params
            # with the same name ( "input2" ) is not yet supported in our test code ( the last one added is the only
            # one used ).
            if name in grouping_value.inputs:
                if isinstance( grouping_value.inputs[name], basic.DataToolParameter ):
                    return True, self.__add_uploaded_dataset( name, value, extra, grouping_value.inputs[name] )
                else:
                    return True, value
            else:
                for input_name, input_parameter in grouping_value.inputs.iteritems():
                    if isinstance( input_parameter, grouping.Group ):
                        found_parameter, new_value = self.__expand_grouping_for_data_input( name, value, extra, input_name, input_parameter )
                        if found_parameter:
                            return True, new_value
        return False, value

    def __add_uploaded_dataset( self, name, value, extra, input_parameter ):
        if value is None:
            assert input_parameter.optional, '%s is not optional. You must provide a valid filename.' % name
            return value
        if ( value, extra ) not in self.required_files:
            self.required_files.append( ( value, extra ) )  # these files will be uploaded
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
