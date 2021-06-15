"""
Fencepost-simple graph structure implementation.
"""
# Currently (2013.7.12) only used in easing the parsing of graph datatype data.


class SimpleGraphNode:
    """
    Node representation.
    """

    def __init__(self, index, **data):
        """
        :param index: index of this node in some parent list
        :type index: int
        :param data: any extra data that needs to be saved
        :type data: (variadic dictionary)
        """
        # a bit application specific (could be 'id')
        self.index = index
        self.data = data


class SimpleGraphEdge:
    """
    Edge representation.
    """

    def __init__(self, source_index, target_index, **data):
        """
        :param source_index: index of the edge's source node in some parent list
        :type source_index: int
        :param target_index: index of the edge's target node in some parent list
        :type target_index: int
        :param data: any extra data that needs to be saved
        :type data: (variadic dictionary)
        """
        self.source_index = source_index
        self.target_index = target_index
        self.data = data


class SimpleGraph:
    """
    Each node is unique (by id) and stores its own index in the node list/odict.
    Each edge is represented as two indeces into the node list/odict.
    Both nodes and edges allow storing extra information if needed.

    Allows:
        multiple edges between two nodes
        self referential edges (an edge from a node to itself)

    These graphs are not specifically directed but since source and targets on the
    edges are listed - it could easily be used that way.
    """

    def __init__(self, nodes=None, edges=None):
        # use an odict so that edge indeces actually match the final node list indeces
        self.nodes = nodes or {}
        self.edges = edges or []

    def add_node(self, node_id, **data):
        """
        Adds a new node only if it doesn't already exist.
        :param node_id: some unique identifier
        :type node_id: (hashable)
        :param data: any extra data that needs to be saved
        :type data: (variadic dictionary)
        :returns: the new node
        """
        if node_id in self.nodes:
            return self.nodes[node_id]
        node_index = len(self.nodes)
        new_node = SimpleGraphNode(node_index, **data)
        self.nodes[node_id] = new_node
        return new_node

    def add_edge(self, source_id, target_id, **data):
        """
        Adds a new node only if it doesn't already exist.
        :param source_id: the id of the source node
        :type source_id: (hashable)
        :param target_id: the id of the target node
        :type target_id: (hashable)
        :param data: any extra data that needs to be saved for the edge
        :type data: (variadic dictionary)
        :returns: the new node

        ..note: that, although this will create new nodes if necessary, there's
        no way to pass `data` to them - so if you need to assoc. more data with
        the nodes, use `add_node` first.
        """
        # adds target_id to source_id's edge list
        #   adding source_id and/or target_id to nodes if not there already
        if source_id not in self.nodes:
            self.add_node(source_id)
        if target_id not in self.nodes:
            self.add_node(target_id)
        new_edge = SimpleGraphEdge(self.nodes[source_id].index, self.nodes[target_id].index, **data)
        self.edges.append(new_edge)
        return new_edge

    def gen_node_dicts(self):
        """
        Returns a generator that yields node dictionaries in the form:
            { 'id': <the nodes unique id>, 'data': <any additional node data> }
        """
        for node_id, node in self.nodes.items():
            yield {'id': node_id, 'data': node.data}

    def gen_edge_dicts(self):
        """
        Returns a generator that yields node dictionaries in the form::

            {
                'source': <the index of the source node in the graph's node list>,
                'target': <the index of the target node in the graph's node list>,
                'data'  : <any additional edge data>
            }
        """
        for edge in self.edges:
            yield {'source': edge.source_index, 'target': edge.target_index, 'data': edge.data}

    def as_dict(self):
        """
        Returns a dictionary of the form::

            { 'nodes': <a list of node dictionaries>, 'edges': <a list of node dictionaries> }
        """
        return {'nodes': list(self.gen_node_dicts()), 'edges': list(self.gen_edge_dicts())}
