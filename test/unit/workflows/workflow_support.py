import yaml

from galaxy.util import bunch
from galaxy import model
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


def yaml_to_model(has_dict):
    if isinstance(has_dict, str):
        has_dict = yaml.load(has_dict)

    workflow = model.Workflow()
    workflow.steps = []
    for i, step in enumerate(has_dict.get("steps", [])):
        workflow_step = model.WorkflowStep()
        if "order_index" not in step:
            step["order_index"] = i
        if "id" not in step:
            # Fixed Offset ids just to test against assuption order_index != id
            step["id"] = i + 100
        for key, value in step.iteritems():
            if key == "input_connections":
                connections = []
                for conn_dict in value:
                    conn = model.WorkflowStepConnection()
                    for conn_key, conn_value in conn_dict.iteritems():
                        if conn_key == "@output_step":
                            step = workflow.steps[conn_value]
                            conn_value = step
                            conn_key = "output_step"

                        setattr(conn, conn_key, conn_value)
                    connections.append(conn)
                value = connections
            setattr(workflow_step, key, value)
        workflow.steps.append( workflow_step )

    return workflow
