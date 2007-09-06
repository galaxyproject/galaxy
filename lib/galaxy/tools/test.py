import new, sys
import galaxy.util
import parameters
import grouping
from elementtree.ElementTree import XML

class ToolTestBuilder( object ):
    """
    Encapsulates information about a tool test, and allows creation of a 
    dynamic TestCase class (the unittest framework is very class oriented, 
    doing dynamic tests in this was allows better integration)
    """
    def __init__( self, tool, name ):
        self.tool = tool
        self.name = name
        self.required_files = []
        self.inputs = []
        self.outputs = []
        self.error = False
        self.exception = None
    def add_param( self, name, value, extra ):
        # FIXME: This needs to be updated for parameter grouping support
        try:
            if name not in self.tool.inputs:
                for input_name, input_value in self.tool.inputs.items():
                    if isinstance( input_value, grouping.Conditional ):
                        self.__expand_grouping_for_data_input(name, value, extra, input_name, input_value)
            elif isinstance( self.tool.inputs[name], parameters.DataToolParameter ):
                self.required_files.append( ( value, extra ) )
        except: pass
        self.inputs.append( ( name, value, extra ) )
    def add_output( self, name, file ):
        self.outputs.append( ( name, file ) )
    def __expand_grouping_for_data_input(self, name, value, extra, grouping_name, grouping_value):
        if name != grouping_value.test_param.name:
            for case in grouping_value.cases:
                for case_input_name, case_input_value in case.inputs.items():
                    if case_input_name == name and isinstance( case_input_value, parameters.DataToolParameter ):
                        self.required_files.append( ( value, extra ) )
                        return True
                    elif isinstance( case_input_value, grouping.Conditional ):
                        self.__expand_grouping_for_data_input(name, value, extra, case_input_name, case_input_value)

