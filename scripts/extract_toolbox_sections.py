import os
import sys
from xml.etree import ElementTree as ET

# Todo: ""

def main():
    doc = ET.parse("tool_conf.xml")
    root = doc.getroot()
    
    for section in root.findall("section"):
        sectionname = section.attrib['name']
        for tool in section.findall("tool"):
            upgradeFile(tool, sectionname)
    for tool in root.findall("tool"):
        upgradeFile(tool, "")

def upgradeFile(tool, sectionname):
    toolfile = tool.attrib["file"]
    realtoolfile = os.path.join(os.getcwd(), "tools", toolfile)
    toolxmlfile = ET.parse(realtoolfile)
    localroot = toolxmlfile.getroot()

    for existingsectionelement in localroot.findall("section"):
        localroot.remove(existingsectionelement)
        
    for existingtagselement in localroot.findall("tags"):
        localroot.remove(existingtagselement)
    
    sectionelement = ET.Element("section")
    sectionelement.text = sectionname
    sectionelement.tail = "\n  "
    localroot.insert(0, sectionelement)
    
    tagselement = ET.Element("tags")
    tagselement.tail = "\n  "
    localroot.insert(1,tagselement)
    
    toolxmlfile.write(realtoolfile)
          

if __name__ == "__main__":
    main()
