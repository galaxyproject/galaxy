import new, sys
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
    doing dynamic tests in this was allows better integration)
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
                for input_name, input_value in self.tool.inputs.items():
                    if isinstance( input_value, grouping.Conditional ) or isinstance( input_value, grouping.Repeat ):
                        self.__expand_grouping_for_data_input(name, value, extra, input_name, input_value)
            elif isinstance( self.tool.inputs[name], parameters.DataToolParameter ) and ( value, extra ) not in self.required_files:
                if value is None:
                    assert self.tool.inputs[name].optional, '%s is not optional. You must provide a valid filename.' % name
                else:
                    self.required_files.append( ( value, extra ) )
        except Exception, e:
            log.debug( "Error in add_param for %s: %s" % ( name, e ) )
        self.inputs.append( ( name, value, extra ) )
    def add_output( self, name, file, extra ):
        self.outputs.append( ( name, file, extra ) )
    def __expand_grouping_for_data_input( self, name, value, extra, grouping_name, grouping_value ):
        # Currently handles grouping.Conditional and grouping.Repeat
        if isinstance( grouping_value, grouping.Conditional  ):
            if name != grouping_value.test_param.name:
                for case in grouping_value.cases:
                    for case_input_name, case_input_value in case.inputs.items():
                        if case_input_name == name and isinstance( case_input_value, basic.DataToolParameter ) and ( value, extra ) not in self.required_files:
                            if value is None:
                                assert case_input_value.optional, '%s is not optional. You must provide a valid filename.' % name
                            else:
                                self.required_files.append( ( value, extra ) )
                            return True
                        elif isinstance( case_input_value, grouping.Conditional ):
                            self.__expand_grouping_for_data_input(name, value, extra, case_input_name, case_input_value)
        elif isinstance( grouping_value, grouping.Repeat ):
            # FIXME: grouping.Repeat can only handle 1 repeat param element since the param name
            # is something like "input2" and the expanded page display is something like "queries_0|input2".
            # The problem is that the only param name on the page is "input2", and adding more test input params
            # with the same name ( "input2" ) is not yet supported in our test code ( the lat one added is the only
            # one used ).
            for input_name, input_value in grouping_value.inputs.items():
                if input_name == name and isinstance( input_value, basic.DataToolParameter ) and ( value, extra ) not in self.required_files:
                    if value is None:
                        assert input_value.optional, '%s is not optional. You must provide a valid filename.' % name
                    else:
                        self.required_files.append( ( value, extra ) )
                    return True
