import os
from collections import defaultdict
from xml.dom import minidom
from xml.etree import ElementTree as ET


def prettify(elem):
    rough_string = ET.tostring(elem, "utf-8")
    repaired = minidom.parseString(rough_string)
    return repaired.toprettyxml(indent="  ")


# Build a list of all toolconf xml files in the tools directory
def getfilenamelist(startdir):
    filenamelist = []
    for root, _dirs, files in os.walk(startdir):
        for fn in files:
            fullfn = os.path.join(root, fn)
            if fn.endswith("toolconf.xml"):
                filenamelist.append(fullfn)
            elif fn.endswith(".xml"):
                try:
                    doc = ET.parse(fullfn)
                except Exception:
                    print("An OOPS on", fullfn)
                    raise
                rootelement = doc.getroot()
                # Only interpret those 'tool' XML files that have
                # the 'section' element.
                if rootelement.tag == "tool":
                    if rootelement.findall("toolboxposition"):
                        filenamelist.append(fullfn)
                    else:
                        print("DBG> tool config does not have a <section>:", fullfn)
    return filenamelist


class ToolBox:
    def __init__(self):
        self.tools = defaultdict(list)
        self.sectionorders = {}

    def add(self, toolelement, toolboxpositionelement):
        section = toolboxpositionelement.attrib.get("section", "")
        label = toolboxpositionelement.attrib.get("label", "")
        order = int(toolboxpositionelement.attrib.get("order", "0"))
        sectionorder = int(toolboxpositionelement.attrib.get("sectionorder", "0"))

        # If this is the first time we encounter the section, store its order
        # number. If we have seen it before, ignore the given order and use
        # the stored one instead
        if section not in self.sectionorders:
            self.sectionorders[section] = sectionorder
        else:
            sectionorder = self.sectionorders[section]

        # Sortorder: add intelligent mix to the front
        self.tools[(f"{sectionorder:05d}-{section}", label, order, section)].append(toolelement)

    def addElementsTo(self, rootelement):
        toolkeys = list(self.tools.keys())
        toolkeys.sort()

        # Initialize the loop: IDs to zero, current section and label to ''
        currentsection = ""
        sectionnumber = 0
        currentlabel = ""
        labelnumber = 0
        for toolkey in toolkeys:
            section = toolkey[3]
            # If we change sections, add the new section to the XML tree,
            # and start adding stuff to the new section. If the new section
            # is '', start adding stuff to the root again.
            if currentsection != section:
                currentsection = section
                # Start the section with empty label
                currentlabel = ""
                if section:
                    sectionnumber += 1
                    attrib = {"name": section, "id": f"section{sectionnumber}"}
                    sectionelement = ET.Element("section", attrib)
                    rootelement.append(sectionelement)
                    currentelement = sectionelement
                else:
                    currentelement = rootelement
            label = toolkey[1]

            # If we change labels, add the new label to the XML tree
            if currentlabel != label:
                currentlabel = label
                if label:
                    labelnumber += 1
                    attrib = {"text": label, "id": f"label{labelnumber}"}
                    labelelement = ET.Element("label", attrib)
                    currentelement.append(labelelement)

            # Add the tools that are in this place
            for toolelement in self.tools[toolkey]:
                currentelement.append(toolelement)


# Analyze all the toolconf xml files given in the filenamelist
# Build a list of all sections
def scanfiles(filenamelist):
    # Build an empty tool box
    toolbox = ToolBox()

    # Read each of the files in the list
    for fn in filenamelist:
        doc = ET.parse(fn)
        root = doc.getroot()

        if root.tag == "tool":
            toolelements = [root]
        else:
            toolelements = doc.findall("tool")

        for toolelement in toolelements:
            # Figure out where the tool XML file is, absolute path.
            if "file" in toolelement.attrib:
                # It is mentioned, we need to make it absolute
                fileattrib = os.path.join(os.getcwd(), os.path.dirname(fn), toolelement.attrib["file"])
            else:
                # It is the current file
                fileattrib = os.path.join(os.getcwd(), fn)

            # Store the file in the attibutes of the new tool element
            attrib = {"file": fileattrib}

            # Add the tags into the attributes
            tags = toolelement.find("tags")
            if tags:
                tagarray = []
                for tag in tags.findall("tag"):
                    tagarray.append(tag.text)
                attrib["tags"] = ",".join(tagarray)
            else:
                print("DBG> No tags in", fn)

            # Build the tool element
            newtoolelement = ET.Element("tool", attrib)
            toolboxpositionelements = toolelement.findall("toolboxposition")
            if not toolboxpositionelements:
                print(f"DBG> {fn} has no toolboxposition")
            else:
                for toolboxpositionelement in toolboxpositionelements:
                    toolbox.add(newtoolelement, toolboxpositionelement)
    return toolbox


def assemble():
    filenamelist = []
    for directorytree in ["tools"]:
        filenamelist.extend(getfilenamelist(directorytree))
    filenamelist.sort()

    toolbox = scanfiles(filenamelist)

    toolboxelement = ET.Element("toolbox")

    toolbox.addElementsTo(toolboxelement)

    print(prettify(toolboxelement))


if __name__ == "__main__":
    assemble()
