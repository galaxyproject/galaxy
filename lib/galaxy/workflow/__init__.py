from galaxy.tools import DefaultToolState
from galaxy.util.topsort import topsort, topsort_levels, CycleError

class Workflow( object ):
 
    def __init__( self ):
        self.steps = {}
        self.has_cycles = None
        self.has_errors = None
        self.node_order = None
        
    @staticmethod
    def from_simple( data ):
        """
        Create from simple (list/dict only) representation
        """
        workflow = Workflow()
        workflow.has_errors = False
        for id, step_data in data['steps'].iteritems():
            step = WorkflowStep.from_simple( step_data )
            if step.has_errors:
                workflow.has_errors = True
            workflow.steps[ id ] = step
        return workflow
    
    def to_simple( self ):
        """
        Convert to simple (list/dict only) representation
        """
        steps = {}
        for id, step in self.steps.iteritems():
            steps[ id ] = step.to_simple()
        return dict( steps=steps,
                     has_cycles=self.has_cycles,
                     has_errors=self.has_errors )

    def edge_list( self ):
        edges = []
        all_ids = set( self.steps.keys() )
        for step in self.steps.values():
            edges.append( ( step.id, step.id ) )
            for name, conn in step.input_connections.iteritems():
                if conn is not None:
                    other_node_id, _ = conn
                    edges.append( ( other_node_id, step.id ) )
        return edges

    def order_nodes( self ):
        """
        Perform topological sort of the steps, return an ordered list of ids
        """
        self.has_cycles = False
        edges = self.edge_list()
        try:
            node_order = topsort( edges )
            #node_order_set = set( node_order )
            #node_order.extend( [ id for id in all_ids if id not in node_order ] )
            self.node_order = node_order
            return self.node_order
        except CycleError:
            self.has_cycles = True
            self.node_order = None
            return None
        
    def order_nodes_levels( self ):
        edges = self.edge_list()
        try:
            return topsort_levels( edges )
        except CycleError:
            return None
        
class WorkflowStep( object ):

    def __init__( self ):
        self.id = None
        self.tool_id = None
        self.tool_inputs = None
        self.has_errors = False
        self.input_connections = {}
        # TODO: How to handle layout in a sufficiently general way
        self.position = None

    @staticmethod
    def from_simple( data ):
        step = WorkflowStep()
        step.id = data['id']
        step.tool_id = data['tool_id']
        step.has_errors = data['has_errors']
        step.tool_inputs = data['tool_inputs']
        # Position
        step.position = data.get( 'position', None )
        # Connections
        for input_name, conn in data['input_connections'].iteritems():
            print "!!!", input_name, conn
            if conn is None:
                step.input_connections[ input_name ] = None
            else:
                step.input_connections[ input_name ] = ( conn['node_id'], conn['output_name' ] )
        return step
    
    def to_simple( self ):
        input_connections = {}
        for name, conn in self.input_connections.iteritems():
            if conn is None:
                input_connections[ name ] = None
            else:
                input_connections[ name ] = dict( node_id = conn[0], output_name = conn[1] )
        return dict( id = self.id,
                     tool_id = self.tool_id,
                     has_errors = self.has_errors,
                     tool_inputs = self.tool_inputs,
                     position = self.position,
                     input_connections = input_connections )