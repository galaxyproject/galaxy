from xml.etree import ElementTree

from .baseparser import (
    Base_Parser,
    Node,
    PhyloTree
)


class Phyloxml_Parser(Base_Parser):
    """Parses a phyloxml file into a json file that will be passed to PhyloViz for display"""

    def __init__(self):
        super(Phyloxml_Parser, self).__init__()
        self.phyloTree = PhyloTree()
        self.tagsOfInterest = {
            "clade": "",
            "name" : "name",
            "branch_length" : "length",
            "confidence"    : "bootstrap",
            "events"        : "events"
        }

    def parseFile(self, filePath):
        """passes a file and extracts its Phylogeny Tree content."""
        phyloXmlFile = open(filePath, "r")

        xmlTree = ElementTree.parse(phyloXmlFile)
        xmlRoot = xmlTree.getroot()[0]
        self.nameSpaceIndex = xmlRoot.tag.rfind("}") + 1  # used later by the clean tag method to remove the name space in every element.tag

        phyloRoot = None
        for child in xmlRoot:
            childTag = self.cleanTag(child.tag)
            if childTag == "clade":
                phyloRoot = child
            elif childTag == "name":
                self.phyloTree.title = child.text

        self.phyloTree.root = self.parseNode(phyloRoot, 0)
        jsonDict = self.phyloTree.generateJsonableDict()
        return [jsonDict], "Success"

    def parseNode(self, node, depth):
        """Parses any node within a phyloxml tree and looks out for claude, which signals the creation of
        nodes - internal OR leaf"""

        tag = self.cleanTag(node.tag)
        if not tag == "clade":
            return None
        hasInnerClade = False

        # peeking once for parent and once for child to check if the node is internal
        for child in node:
            childTag = self.cleanTag(child.tag)
            if childTag == "clade":
                hasInnerClade = True
                break

        if hasInnerClade:       # this node is an internal node
            currentNode = self._makeInternalNode(node, depth=depth)
            for child in node:
                child = self.parseNode(child, depth + 1)
                if isinstance(child, Node):
                    currentNode.addChildNode(child)

        else:                   # this node is a leaf node
            currentNode = self._makeLeafNode(node, depth=depth + 1)

        return currentNode

    def _makeLeafNode(self, leafNode, depth=0):
        """Makes leaf nodes by calling Phylotree methods"""
        node = {}
        for child in leafNode:
            childTag = self.cleanTag(child.tag)
            if childTag in self.tagsOfInterest:
                key = self.tagsOfInterest[childTag]    # need to map phyloxml terms to ours
                node[key] = child.text

        node["depth"] = depth
        return self.phyloTree.makeNode(self._getNodeName(leafNode), **node)

    def _getNodeName(self, node, depth=-1):
        """Gets the name of a claude. It handles the case where a taxonomy node is involved"""

        def getTagFromTaxonomyNode(node):
            """Returns the name of a taxonomy node. A taxonomy node have to be treated differently as the name
            is embedded one level deeper"""
            phyloxmlTaxoNames = {
                "common_name" : "",
                "scientific_name" : "",
                "code"  : ""
            }
            for child in node:
                childTag = self.cleanTag(child.tag)
                if childTag in phyloxmlTaxoNames:
                    return child.text
            return ""

        nodeName = ""
        for child in node:
            childTag = self.cleanTag(child.tag)
            if childTag == "name" :
                nodeName = child.text
                break
            elif childTag == "taxonomy":
                nodeName = getTagFromTaxonomyNode(child)
                break

        return nodeName

    def _makeInternalNode(self, internalNode, depth=0):
        """ Makes an internal node from an element object that is guranteed to be a parent node.
        Gets the value of interests like events and appends it to a custom node object that will be passed to PhyloTree to make nodes
        """
        node = {}
        for child in internalNode:
            childTag = self.cleanTag(child.tag)
            if childTag == "clade":
                continue
            elif childTag in self.tagsOfInterest:
                if childTag == "events":    # events is nested 1 more level deeper than others
                    key, text = "events", self.cleanTag(child[0].tag)
                else:
                    key = self.tagsOfInterest[childTag]
                    text = child.text
                node[key] = text

        return self.phyloTree.makeNode(self._getNodeName(internalNode, depth), **node)

    def cleanTag(self, tagString):
        return tagString[self.nameSpaceIndex:]
