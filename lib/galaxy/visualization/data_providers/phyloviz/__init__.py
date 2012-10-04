""" Data providers code for PhyloViz """

from galaxy.visualization.data_providers.basic import BaseDataProvider
from galaxy.visualization.data_providers.phyloviz.nexusparser import Nexus_Parser
from galaxy.visualization.data_providers.phyloviz.newickparser import Newick_Parser
from galaxy.visualization.data_providers.phyloviz.phyloxmlparser import Phyloxml_Parser

class PhylovizDataProvider( BaseDataProvider ):

    def __init__( self, original_dataset=None ):
        super( PhylovizDataProvider, self ).__init__( original_dataset=original_dataset )

    def get_data( self ):
        """returns [trees], meta
            Trees are actually an array of JsonDicts. It's usually one tree, except in the case of Nexus
        """

        jsonDicts, meta = [], {}
        file_ext = self.original_dataset.datatype.file_ext
        file_name = self.original_dataset.file_name
        try:
            if file_ext == "nhx": # parses newick files
                newickParser = Newick_Parser()
                jsonDicts, parseMsg = newickParser.parseFile( file_name )
            elif file_ext == "phyloxml": # parses phyloXML files
                phyloxmlParser = Phyloxml_Parser()
                jsonDicts, parseMsg = phyloxmlParser.parseFile( file_name )
            elif file_ext == "nex": # parses nexus files
                nexusParser = Nexus_Parser()
                jsonDicts, parseMsg = nexusParser.parseFile( file_name )
                meta["trees"] = parseMsg
            else:
                raise Exception("File type is not supported")

            meta["msg"] = parseMsg

        except Exception, e:
            raise e
            jsonDicts, meta["msg"] = [], "Parse failed"

        return jsonDicts, meta

