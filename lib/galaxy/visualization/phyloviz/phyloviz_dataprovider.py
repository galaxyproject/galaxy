from newickparser import Newick_Parser
from nexusparser import Nexus_Parser
from phyloxmlparser import Phyloxml_Parser

class Phyloviz_DataProvider(object):

    def __init__(self):
        pass

    def parseFile(self, filepath, fileExt):
        """returns [trees], meta
            Trees are actually an array of JsonDicts. It's usually one tree, except in the case of Nexus
        """
        jsonDicts, meta = [], {}
        try:
            if fileExt == "nhx": # parses newick files
                newickParser = Newick_Parser()
                jsonDicts, parseMsg = newickParser.parseFile(filepath)
            elif fileExt == "phyloxml": # parses phyloXML files
                phyloxmlParser = Phyloxml_Parser()
                jsonDicts, parseMsg = phyloxmlParser.parseFile(filepath)
            elif fileExt == "nex": # parses nexus files
                nexusParser = Nexus_Parser()
                jsonDicts, parseMsg = nexusParser.parseFile(filepath)
                meta["trees"] = parseMsg
            else:
                raise Exception("File type is not supported")

            meta["msg"] = parseMsg

        except Exception:
            jsonDicts, meta["msg"] = [], "Parse failed"

        return jsonDicts, meta

