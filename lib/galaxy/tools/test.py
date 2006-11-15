import new, sys
import galaxy.util
import parameters

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
    def add_param( self, name, value, extra ):
        if isinstance( self.tool.param_map[name], parameters.DataToolParameter ):
            self.required_files.append( ( value, extra ) )
        self.inputs.append( ( name, value, extra ) )
    def add_output( self, name, file ):
        self.outputs.append( ( name, file ) )