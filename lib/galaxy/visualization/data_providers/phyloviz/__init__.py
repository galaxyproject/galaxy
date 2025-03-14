"""Data providers code for PhyloViz"""

from typing import (
    Any,
    Dict,
)

from galaxy.visualization.data_providers.basic import BaseDataProvider
from galaxy.visualization.data_providers.phyloviz.newickparser import Newick_Parser
from galaxy.visualization.data_providers.phyloviz.nexusparser import Nexus_Parser
from galaxy.visualization.data_providers.phyloviz.phyloxmlparser import Phyloxml_Parser


class PhylovizDataProvider(BaseDataProvider):
    dataset_type = "phylo"

    def __init__(self, original_dataset=None):
        super().__init__(original_dataset=original_dataset)

    def get_data(self, tree_index=0):
        """
        Returns trees.
        Trees are actually an array of JsonDicts. It's usually one tree, except in the case of Nexus
        """

        file_ext = self.original_dataset.datatype.file_ext
        file_name = self.original_dataset.get_file_name()
        parseMsg = None
        jsonDicts = []
        rval: Dict[str, Any] = {"dataset_type": self.dataset_type}

        if file_ext in ["newick", "nhx"]:  # parses newick files
            newickParser = Newick_Parser()
            jsonDicts, parseMsg = newickParser.parseFile(file_name)
        elif file_ext == "phyloxml":  # parses phyloXML files
            phyloxmlParser = Phyloxml_Parser()
            jsonDicts, parseMsg = phyloxmlParser.parseFile(file_name)
        elif file_ext == "nex":  # parses nexus files
            nexusParser = Nexus_Parser()
            jsonDicts, parseMsg = nexusParser.parseFile(file_name)
            jsonDicts = jsonDicts[int(tree_index)]
            rval["trees"] = parseMsg

        rval["data"] = jsonDicts
        rval["msg"] = parseMsg

        return rval
