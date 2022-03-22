import os
from collections import defaultdict
from xml.etree import ElementTree as ET

# Todo: ""
# execute from galaxy root dir

tooldict = defaultdict(list)


def main():
    doc = ET.parse("tool_conf.xml")
    root = doc.getroot()

    # index range 1-1000, current sections/tools divided between 250-750
    sectionindex = 250
    sectionfactor = int(500 / len(root))

    for rootchild in root:
        currentsectionlabel = ""
        if rootchild.tag == "section":
            sectionname = rootchild.attrib["name"]
            # per section tool index range 1-1000, current labels/tools
            # divided between 20 and 750
            toolindex = 250
            toolfactor = int(500 / len(rootchild))
            currentlabel = ""
            for sectionchild in rootchild:
                if sectionchild.tag == "tool":
                    addToToolDict(sectionchild, sectionname, sectionindex, toolindex, currentlabel)
                    toolindex += toolfactor
                elif sectionchild.tag == "label":
                    currentlabel = sectionchild.attrib["text"]
            sectionindex += sectionfactor
        elif rootchild.tag == "tool":
            addToToolDict(rootchild, "", sectionindex, None, currentsectionlabel)
            sectionindex += sectionfactor
        elif rootchild.tag == "label":
            currentsectionlabel = rootchild.attrib["text"]
            sectionindex += sectionfactor

    # scan galaxy root tools dir for tool-specific xmls
    toolconffilelist = getfnl(os.path.join(os.getcwd(), "tools"))

    # foreach tool xml:
    #   check if the tags element exists in the tool xml (as child of <tool>)
    #   if not, add empty tags element for later use
    #   if this tool is in the above tooldict, add the toolboxposition element to the tool xml
    #   if not, then nothing.
    for toolconffile in toolconffilelist:
        hastags = False
        hastoolboxpos = False

        # parse tool config file into a document structure as defined by the ElementTree
        tooldoc = ET.parse(toolconffile)
        # get the root element of the toolconfig file
        tooldocroot = tooldoc.getroot()
        # check tags element, set flag
        tagselement = tooldocroot.find("tags")
        if tagselement:
            hastags = True
        # check if toolboxposition element already exists in this tooconfig file
        toolboxposelement = tooldocroot.find("toolboxposition")
        if toolboxposelement:
            hastoolboxpos = True

        if not (hastags and hastoolboxpos):
            original = open(toolconffile)
            contents = original.readlines()
            original.close()

            # the new elements will be added directly below the root tool element
            addelementsatposition = 1
            # but what's on the first line? Root or not?
            if contents[0].startswith("<?"):
                addelementsatposition = 2
            newelements = []
            if not hastoolboxpos:
                if toolconffile in tooldict:
                    for attributes in tooldict[toolconffile]:
                        # create toolboxposition element
                        sectionelement = ET.Element("toolboxposition")
                        sectionelement.attrib = attributes
                        sectionelement.tail = "\n  "
                        newelements.append(ET.tostring(sectionelement, "utf-8"))

            if not hastags:
                # create empty tags element
                newelements.append("<tags/>\n  ")

            contents = contents[0:addelementsatposition] + newelements + contents[addelementsatposition:]

            # add .new for testing/safety purposes :P
            newtoolconffile = open(toolconffile, "w")
            newtoolconffile.writelines(contents)
            newtoolconffile.close()


def addToToolDict(tool, sectionname, sectionindex, toolindex, currentlabel):
    toolfile = tool.attrib["file"]
    realtoolfile = os.path.join(os.getcwd(), "tools", toolfile)

    # define attributes for the toolboxposition xml-tag
    attribdict = {}
    if sectionname:
        attribdict["section"] = sectionname
    if currentlabel:
        attribdict["label"] = currentlabel
    if sectionindex:
        attribdict["sectionorder"] = str(sectionindex)
    if toolindex:
        attribdict["order"] = str(toolindex)
    tooldict[realtoolfile].append(attribdict)


# Build a list of all toolconf xml files in the tools directory
def getfnl(startdir):
    filenamelist = []
    for root, _dirs, files in os.walk(startdir):
        for fn in files:
            fullfn = os.path.join(root, fn)
            if fn.endswith(".xml"):
                try:
                    doc = ET.parse(fullfn)
                except Exception as e:
                    raise Exception(f"Oops, bad XML in '{fullfn}': {e}")
                rootelement = doc.getroot()
                # here we check if this xml file actually is a tool conf xml!
                if rootelement.tag == "tool":
                    filenamelist.append(fullfn)
    return filenamelist


if __name__ == "__main__":
    main()
