import json
from typing import (
    Any,
    Dict,
)


class Node:
    """Node class of PhyloTree, which represents a CLAUDE in a phylogenetic tree"""

    def __init__(self, nodeName, **kwargs):
        """Creates a node and adds in the typical annotations"""
        self.name, self.id = nodeName, kwargs.get("id", 0)
        self.depth = kwargs.get("depth", 0)
        self.children = []

        self.isInternal = kwargs.get("isInternal", 0)
        self.length, self.bootstrap = kwargs.get("length", 0), kwargs.get("bootstrap", None)
        self.events = kwargs.get("events", "")

        self.parent = None

        # clean up boot strap values
        if self.bootstrap == -1:
            self.bootstrap = None

    def addChildNode(self, child):
        """Adds a child node to the current node"""
        if isinstance(child, Node):
            self.children.append(child)
        else:
            self.children += child

    def __str__(self):
        return f"{self.name} id:{str(self.id)}, depth: {str(self.depth)}"

    def toJson(self) -> Dict[str, Any]:
        """Converts the data in the node to a dict representation of json"""
        thisJson = {"name": self.name, "id": self.id, "depth": self.depth, "dist": self.length}
        thisJson = self.addChildrenToJson(thisJson)
        thisJson = self.addMiscToJson(thisJson)
        return thisJson

    def addChildrenToJson(self, jsonDict):
        """Needs a special method to addChildren, such that the key does not appear in the Jsondict when the children is empty
        this requirement is due to the layout algorithm used by d3 layout for hiding subtree"""
        if len(self.children) > 0:
            children = [node.toJson() for node in self.children]
            jsonDict["children"] = children
        return jsonDict

    def addMiscToJson(self, jsonDict):
        """Adds other misc attributes to json if they are present"""
        if not self.events == "":
            jsonDict["events"] = self.events
        if self.bootstrap is not None:
            jsonDict["bootstrap"] = self.bootstrap
        return jsonDict


class PhyloTree:
    """Standardized python based class to represent the phylogenetic tree parsed from different
    phylogenetic file formats."""

    def __init__(self):
        self.root, self.rootAttr = None, {}
        self.nodes = {}
        self.title = None
        self.id = 1

    def addAttributesToRoot(self, attrDict):
        """Adds attributes to root, but first we put it in a temp store and bind it with root when .toJson is called"""
        for key, value in attrDict.items():
            self.rootAttr[key] = value

    def makeNode(self, nodeName, **kwargs):
        """Called to make a node within PhyloTree, arbitrary kwargs can be passed to annotate nodes
        Tracks the number of nodes via internally incremented id"""
        kwargs["id"] = self.id
        self.id += 1
        return Node(nodeName, **kwargs)

    def addRoot(self, root: Node):
        """Creates a root for phyloTree"""
        assert isinstance(root, Node)
        root.parent = None
        self.root = root

    def generateJsonableDict(self):
        """Changes itself into a dictonary by recurssively calling the tojson on all its nodes. Think of it
        as a dict in an array of dict in an array of dict and so on..."""
        jsonTree: Dict[str, Any]
        if self.root:
            assert isinstance(self.root, Node)
            jsonTree = self.root.toJson()
            for key, value in self.rootAttr.items():
                # transfer temporary stored attr to root
                jsonTree[key] = value
        else:
            raise Exception("Root is not assigned!")
        return jsonTree


class Base_Parser:
    """Base parsers contain all the methods to handle phylogeny tree creation and
    converting the data to json that all parsers should have"""

    def __init__(self):
        self.phyloTrees = []

    def parseFile(self, filePath):
        """Base method that all phylogeny file parser should have"""
        raise Exception("Base method for phylogeny file parsers is not implemented")

    def toJson(self, jsonDict):
        """Convenience method to get a json string from a python json dict"""
        return json.dumps(jsonDict)

    def _writeJsonToFile(self, filepath, json):
        """Writes the file out to the system"""
        f = open(filepath, "w")
        f.writelines(json)
        f.close()
