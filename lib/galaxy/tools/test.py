import new, sys
import os.path
import galaxy.util
import parameters
from parameters import basic
from parameters import grouping
from elementtree.ElementTree import XML
import logging

log = logging.getLogger( __name__ )

class ToolTestBuilder( object ):
    """
    Encapsulates information about a tool test, and allows creation of a 
    dynamic TestCase class (the unittest framework is very class oriented, 
    doing dynamic tests in this way allows better integration)
    """
    def __init__( self, tool, name, maxseconds ):
        self.tool = tool
        self.name = name
        self.maxseconds = maxseconds
        self.required_files = []
        self.inputs = []
        self.outputs = []
        self.error = False
        self.exception = None
    def add_param( self, name, value, extra ):
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
                    raise ValueError( "Unable to determine parameter type of test input '%s'. Ensure that the parameter exists and that any container groups are defined first." % name )
            elif isinstance( self.tool.inputs[name], basic.DataToolParameter ):
                value = self.__add_uploaded_dataset( name, value, extra, self.tool.inputs[name] )
        except Exception, e:
            log.debug( "Error in add_param for %s: %s" % ( name, e ) )
        self.inputs.append( ( name, value, extra ) )
    def add_output( self, name, file, extra ):
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
            self.required_files.append( ( value, extra ) ) #these files will be uploaded
        name_change = [ att for att in extra.get( 'edit_attributes', [] ) if att.get( 'type' ) == 'name' ]
        if name_change:
            name_change = name_change[-1].get( 'value' ) #only the last name change really matters
            value = name_change #change value for select to renamed uploaded file for e.g. composite dataset
        else:
            for end in [ '.zip', '.gz' ]:
                if value.endswith( end ):
                    value = value[ :-len( end ) ]
                    break
            value = os.path.basename( value ) #if uploading a file in a path other than root of test-data
        return value
