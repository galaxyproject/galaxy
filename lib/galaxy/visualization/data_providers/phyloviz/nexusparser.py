import re

from .newickparser import Newick_Parser

MAX_READLINES = 200000


class Nexus_Parser(Newick_Parser):
    def __init__(self):
        super().__init__()

    def parseFile(self, filePath):
        """passes a file and extracts its Nexus content."""
        return self.parseNexus(filePath)

    def parseNexus(self, filename):
        """Nexus data is stored in blocks between a line starting with begin and another line starting with end;
        Commends inside square brackets are to be ignored,
        For more information: http://wiki.christophchamp.com/index.php/NEXUS_file_format
        Nexus can store multiple trees
        """

        with open(filename) as nex_file:
            nexlines = nex_file.readlines()

        rowCount = 0
        inTreeBlock = False  # sentinel to check if we are in a tree block
        intranslateBlock = (
            False  # sentinel to check if we are in the translate region of the tree. Stores synonyms of the labellings
        )
        self.inCommentBlock = False
        self.nameMapping = None  # stores mapping representation used in nexus format
        treeNames = []

        for line in nexlines:
            line = line.replace(";\n", "")
            lline = line.lower()

            if rowCount > MAX_READLINES or (not nex_file):
                break
            rowCount += 1
            # We are only interested in the tree block.
            if "begin" in lline and "tree" in lline and not inTreeBlock:
                inTreeBlock = True
                continue
            if inTreeBlock and "end" in lline[:3]:
                inTreeBlock, currPhyloTree = False, None
                continue

            if inTreeBlock:

                if "title" in lline:  # Adding title to the tree
                    continue

                if "translate" in lline:
                    intranslateBlock = True
                    self.nameMapping = {}
                    continue

                if intranslateBlock:
                    mappingLine = self.splitLinebyWhitespaces(line)
                    key, value = mappingLine[1], mappingLine[2].replace(",", "").replace(
                        "'", ""
                    )  # replacing illegal json characters
                    self.nameMapping[key] = value

                # Extracting newick Trees
                if "tree" in lline:
                    intranslateBlock = False

                    treeLineCols = self.splitLinebyWhitespaces(line)
                    treeName, newick = treeLineCols[2], treeLineCols[-1]

                    if newick == "":  # Empty lines can be found in tree blocks
                        continue

                    currPhyloTree = self._parseNewickToJson(newick, treeName, nameMap=self.nameMapping)

                    self.phyloTrees.append(currPhyloTree)
                    treeIndex = len(self.phyloTrees) - 1
                    treeNames.append((treeName, treeIndex))  # appending name of tree, and its index
                    continue

        return self.phyloTrees, treeNames

    def splitLinebyWhitespaces(self, line):
        """replace tabs and write spaces to a single write space, so we can properly split it."""
        return re.split(r"\s+", line)

    def checkComments(self, line):
        """Check to see if the line/lines is a comment."""
        if not self.inCommentBlock:
            if "[" in line:
                if "]" not in line:
                    self.inCommentBlock = True
                else:
                    return "Nextline"  # need to move on to the nextline after getting out of comment
        else:
            if "]" in line:
                if line.rfind("[") > line.rfind("]"):
                    pass  # a comment block is closed but another is open.
                else:
                    self.inCommentBlock = False
                    return "Nextline"  # need to move on to the nextline after getting out of comment
        return ""
