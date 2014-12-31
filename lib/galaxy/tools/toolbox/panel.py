from galaxy.util.odict import odict


class ToolPanelElements( odict ):
    """ Represents an ordered dictionary of tool entries - abstraction
    used both by tool panel itself (normal and integrated) and its sections.
    """

    def has_tool_with_id( self, tool_id ):
        key = 'tool_%s' % tool_id
        return key in self

    def replace_tool( self, previous_tool_id, new_tool_id, tool ):
        previous_key = 'tool_%s' % previous_tool_id
        new_key = 'tool_%s' % new_tool_id
        index = self.keys().index( previous_key )
        del self[ previous_key ]
        self.insert( index, new_key, tool )

    def index_of_tool_id( self, tool_id ):
        query_key = 'tool_%s' % tool_id
        for index, target_key in enumerate( self.keys() ):
            if query_key == target_key:
                return index
        return None

    def insert_tool( self, index, tool ):
        key = "tool_%s" % tool.id
        self.insert( index, key, tool )

    def get_tool_with_id( self, tool_id ):
        key = "tool_%s" % tool_id
        return self[ key ]

    def append_tool( self, tool ):
        key = "tool_%s" % tool.id
        self[ key ] = tool
