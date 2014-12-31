from galaxy.util import bunch
from galaxy.model import mapping


class MockTrans( object ):

    def __init__( self ):
        self.app = TestApp()


class TestApp( object ):

    def __init__( self ):
        self.config = bunch.Bunch(
            tool_secret="awesome_secret",
        )
        self.model = mapping.init(
            "/tmp",
            "sqlite:///:memory:",
            create_tables=True
        )
        self.toolbox = TestToolbox()
        self.datatypes_registry = TestDatatypesRegistry()


class TestDatatypesRegistry( object ):

    def __init__( self ):
        pass

    def get_datatype_by_extension( self, ext ):
        return ext


class TestToolbox( object ):

    def __init__( self ):
        self.tools = {}

    def get_tool( self, tool_id, tool_version=None ):
        # Real tool box returns None of missing tool also
        return self.tools.get( tool_id, None )

    def get_tool_id( self, tool_id ):
        tool = self.get_tool( tool_id )
        return tool and tool.id
