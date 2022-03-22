import re

from .baseparser import (
    Base_Parser,
    PhyloTree,
)


class Newick_Parser(Base_Parser):
    """For parsing trees stored in the newick format (.nhx)
    It is necessarily more complex because this parser is later extended by Nexus for parsing newick as well.."""

    def __init__(self):
        super().__init__()

    def parseFile(self, filePath):
        """Parses a newick file to obtain the string inside. Returns: jsonableDict"""
        with open(filePath) as newickFile:
            newickString = newickFile.read()
            newickString = newickString.replace("\n", "").replace("\r", "")
            return [self.parseData(newickString)], "Success"

    def parseData(self, newickString):
        """To be called on a newickString directly to parse it. Returns: jsonableDict"""
        return self._parseNewickToJson(newickString)

    def _parseNewickToJson(self, newickString, treeName=None, nameMap=None):
        """parses a newick representation of a tree into a PhyloTree data structure,
        which can be easily converted to json"""
        self.phyloTree = PhyloTree()
        newickString = self.cleanNewickString(newickString)
        if nameMap:
            newickString = self._mapName(newickString, nameMap)

        self.phyloTree.root = self.parseNode(newickString, 0)
        if nameMap:
            self.phyloTree.addAttributesToRoot({"treeName": treeName})

        return self.phyloTree.generateJsonableDict()

    def cleanNewickString(self, rawNewick):
        r"""removing semi colon, and illegal json characters (\,',") and white spaces"""
        return re.sub(r"\s|;|\"|\'|\\", r"", rawNewick)

    def _makeNodesFromString(self, string, depth):
        """elements separated by comma could be empty"""

        if string.find("(") != -1:
            raise Exception(f"Tree is not well form, location: {string}")

        childrenString = string.split(",")
        childrenNodes = []

        for childString in childrenString:
            if len(childString) == 0:
                continue
            nodeInfo = childString.split(":")
            name, length, bootstrap = "", None, -1.0
            if len(nodeInfo) == 2:  # has length info
                length = nodeInfo[1]
                # checking for bootstap values
                name = nodeInfo[0]
                try:  # Nexus may bootstrap in names position
                    name_as_float = float(name)
                    if 0 <= name_as_float <= 1:
                        bootstrap = name_as_float
                    elif 1 <= name_as_float <= 100:
                        bootstrap = name_as_float / 100
                    name = ""
                except ValueError:
                    name = nodeInfo[0]
            else:
                name = nodeInfo[0]  # string only contains name
            node = self.phyloTree.makeNode(name, length=length, depth=depth, bootstrap=bootstrap)
            childrenNodes += [node]
        return childrenNodes

    def _mapName(self, newickString, nameMap):
        """
        Necessary to replace names of terms inside nexus representation
        Also, it's here because Mailaud's doesnt deal with id_strings outside of quotes(" ")
        """
        newString = ""
        start = 0
        end = 0

        for i in range(len(newickString)):
            if newickString[i] == "(" or newickString[i] == ",":
                if re.match(r"[,(]", newickString[i + 1 :]):
                    continue
                else:
                    end = i + 1
                    # i now refers to the starting position of the term to be replaced,
                    # we will next find j which is the ending pos of the term
                    for j in range(i + 1, len(newickString)):
                        enclosingSymbol = newickString[
                            j
                        ]  # the immediate symbol after a common or left bracket which denotes the end of a term
                        if enclosingSymbol == ")" or enclosingSymbol == ":" or enclosingSymbol == ",":
                            termToReplace = newickString[end:j]

                            newString += newickString[start:end] + nameMap[termToReplace]  # + "'"  "'" +
                            start = j
                            break

        newString += newickString[start:]
        return newString

    def parseNode(self, string, depth):
        """
        Recursive method for parsing newick string, works by stripping down the string into substring
        of newick contained with brackers, which is used to call itself.

        Eg ... ( A, B, (D, E)C, F, G ) ...

        We will make the preceeding nodes first A, B, then the internal node C, its children D, E,
        and finally the succeeding nodes F, G
        """

        # Base case where there is only an empty string
        if string == "":
            return
            # Base case there it's only an internal claude
        if string.find("(") == -1:
            return self._makeNodesFromString(string, depth)

        nodes = []  # nodes refer to the nodes on this level
        start = 0
        lenOfPreceedingInternalNodeString = 0
        bracketStack = []

        for j in range(len(string)):
            if string[j] == "(":  # finding the positions of all the open brackets
                bracketStack.append(j)
                continue
            if string[j] == ")":  # finding the positions of all the closed brackets to extract claude
                i = bracketStack.pop()

                if len(bracketStack) == 0:  # is child of current node

                    InternalNode = None

                    # First flat call to make nodes of the same depth but from the preceeding string.
                    startSubstring = string[start + lenOfPreceedingInternalNodeString : i]
                    preceedingNodes = self._makeNodesFromString(startSubstring, depth)
                    nodes += preceedingNodes

                    # Then We will try to see if the substring has any internal nodes first, make it then make nodes preceeding it and succeeding it.
                    if j + 1 < len(string):
                        stringRightOfBracket = string[j + 1 :]  # Eg. '(b:0.4,a:0.3)c:0.3, stringRightOfBracket = c:0.3
                        match = re.search(r"[\)\,\(]", stringRightOfBracket)
                        if match:
                            indexOfNextSymbol = match.start()
                            stringRepOfInternalNode = stringRightOfBracket[:indexOfNextSymbol]
                            internalNodes = self._makeNodesFromString(stringRepOfInternalNode, depth)
                            if len(internalNodes) > 0:
                                InternalNode = internalNodes[0]
                            lenOfPreceedingInternalNodeString = len(stringRepOfInternalNode)
                        else:  # sometimes the node can be the last element of a string
                            InternalNode = self._makeNodesFromString(string[j + 1 :], depth)[0]
                            lenOfPreceedingInternalNodeString = len(string) - j
                    if InternalNode is None:  # creating a generic node if it is unnamed
                        InternalNode = self.phyloTree.makeNode(
                            "", depth=depth, isInternal=True
                        )  # "internal-" + str(depth)
                        lenOfPreceedingInternalNodeString = 0

                    # recussive call to make the internal claude
                    childSubString = string[i + 1 : j]
                    InternalNode.addChildNode(self.parseNode(childSubString, depth + 1))

                    nodes.append(InternalNode)  # we append the internal node later to preserve order

                    start = j + 1
                continue

        if depth == 0:  # if it's the root node, we do nothing about it and return
            return nodes[0]

        # Adding last most set of children
        endString = string[start:]
        if (
            string[start - 1] == ")"
        ):  # if the symbol belongs to an internal node which is created previously, then we remove it from the string left to parse
            match = re.search(r"[\)\,\(]", endString)
            if match:
                endOfNodeName = start + match.start() + 1
                endString = string[endOfNodeName:]
                nodes += self._makeNodesFromString(endString, depth)

        return nodes
