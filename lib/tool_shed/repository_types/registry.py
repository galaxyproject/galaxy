import logging

from galaxy.util.odict import odict

from . import repository_suite_definition
from . import tool_dependency_definition
from . import unrestricted
from . import interactive_tour

log = logging.getLogger( __name__ )


class Registry( object ):

    def __init__( self ):
        self.repository_types_by_label = odict()
        self.repository_types_by_label[ 'unrestricted' ] = unrestricted.Unrestricted()
        self.repository_types_by_label[ 'repository_suite_definition' ] = repository_suite_definition.RepositorySuiteDefinition()
        self.repository_types_by_label[ 'tool_dependency_definition' ] = tool_dependency_definition.ToolDependencyDefinition()
        self.repository_types_by_label[ 'interactive_tour' ] = interactive_tour.InteractiveTour()

    def get_class_by_label( self, label ):
        return self.repository_types_by_label.get( label, None )
