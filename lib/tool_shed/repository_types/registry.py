import logging
import generic
import tool_dependency_definition
from galaxy.util.odict import odict

log = logging.getLogger( __name__ )


class Registry( object ):

    def __init__( self ):
        self.repository_types_by_label = odict()
        self.repository_types_by_label[ 'generic' ] = generic.Generic()
        self.repository_types_by_label[ 'tool_dependency_definition' ] = tool_dependency_definition.ToolDependencyDefinition()

    def get_class_by_label( self, label ):
        return self.repository_types_by_label.get( label, None )
