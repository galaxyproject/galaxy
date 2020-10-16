"""
Graph content classes.
"""
import logging

from galaxy.util import simplegraph
from . import (
    data,
    dataproviders,
    tabular,
    xml
)

log = logging.getLogger(__name__)


@dataproviders.decorators.has_dataproviders
class Xgmml(xml.GenericXml):
    """
    XGMML graph format
    (http://wiki.cytoscape.org/Cytoscape_User_Manual/Network_Formats).
    """
    file_ext = "xgmml"

    def set_peek(self, dataset, is_multi_byte=False):
        """
        Set the peek and blurb text
        """
        if not dataset.dataset.purged:
            dataset.peek = data.get_file_peek(dataset.file_name)
            dataset.blurb = 'XGMML data'
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def sniff(self, filename):
        """
        Returns false and the user must manually set.
        """
        return False

    @staticmethod
    def merge(split_files, output_file):
        """
        Merging multiple XML files is non-trivial and must be done in subclasses.
        """
        if len(split_files) > 1:
            raise NotImplementedError("Merging multiple XML files is non-trivial " +
                                      "and must be implemented for each XML type")
        # For one file only, use base class method (move/copy)
        data.Text.merge(split_files, output_file)

    @dataproviders.decorators.dataprovider_factory('node-edge', dataproviders.hierarchy.XMLDataProvider.settings)
    def node_edge_dataprovider(self, dataset, **settings):
        dataset_source = dataproviders.dataset.DatasetDataProvider(dataset)
        return XGMMLGraphDataProvider(dataset_source, **settings)


@dataproviders.decorators.has_dataproviders
class Sif(tabular.Tabular):
    """
    SIF graph format
    (http://wiki.cytoscape.org/Cytoscape_User_Manual/Network_Formats).

    First column: node id
    Second column: relationship type
    Third to Nth column: target ids for link
    """
    file_ext = "sif"

    def set_peek(self, dataset, is_multi_byte=False):
        """
        Set the peek and blurb text
        """
        if not dataset.dataset.purged:
            dataset.peek = data.get_file_peek(dataset.file_name)
            dataset.blurb = 'SIF data'
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def sniff(self, filename):
        """
        Returns false and the user must manually set.
        """
        return False

    @staticmethod
    def merge(split_files, output_file):
        data.Text.merge(split_files, output_file)

    @dataproviders.decorators.dataprovider_factory('node-edge', dataproviders.column.ColumnarDataProvider.settings)
    def node_edge_dataprovider(self, dataset, **settings):
        dataset_source = dataproviders.dataset.DatasetDataProvider(dataset)
        return SIFGraphDataProvider(dataset_source, **settings)


# ----------------------------------------------------------------------------- graph specific data providers
class XGMMLGraphDataProvider(dataproviders.hierarchy.XMLDataProvider):
    """
    Provide two lists: nodes, edges::

        'nodes': contains objects of the form:
            { 'id' : <some string id>, 'data': <any extra data> }
        'edges': contains objects of the form:
            { 'source' : <an index into nodes>, 'target': <an index into nodes>, 'data': <any extra data> }
    """

    def __iter__(self):
        # use simple graph to store nodes and links, later providing them as a dict
        #   essentially this is a form of aggregation
        graph = simplegraph.SimpleGraph()

        parent_gen = super(XGMMLGraphDataProvider, self).__iter__()
        for graph_elem in parent_gen:
            if 'children' not in graph_elem:
                continue
            for elem in graph_elem['children']:
                # use endswith to work around Elementtree namespaces
                if elem['tag'].endswith('node'):
                    node_id = elem['attrib']['id']
                    # pass the entire, parsed xml element as the data
                    graph.add_node(node_id, **elem)

                elif elem['tag'].endswith('edge'):
                    source_id = elem['attrib']['source']
                    target_id = elem['attrib']['target']
                    graph.add_edge(source_id, target_id, **elem)

        yield graph.as_dict()


class SIFGraphDataProvider(dataproviders.column.ColumnarDataProvider):
    """
    Provide two lists: nodes, edges::

        'nodes': contains objects of the form:
            { 'id' : <some string id>, 'data': <any extra data> }
        'edges': contains objects of the form:
            { 'source' : <an index into nodes>, 'target': <an index into nodes>, 'data': <any extra data> }
    """

    def __iter__(self):
        # use simple graph to store nodes and links, later providing them as a dict
        #   essentially this is a form of aggregation
        graph = simplegraph.SimpleGraph()
        # SIF is tabular with the source, link-type, and all targets in the columns
        parent_gen = super(SIFGraphDataProvider, self).__iter__()
        for columns in parent_gen:
            if columns:
                source_id = columns[0]
                # there's no extra data for nodes (or links) in the examples I've seen
                graph.add_node(source_id)

                # targets are the (variadic) remaining columns
                if len(columns) >= 3:
                    relation = columns[1]
                    targets = columns[2:]
                    for target_id in targets:
                        graph.add_node(target_id)
                        graph.add_edge(source_id, target_id, type=relation)

        yield graph.as_dict()
