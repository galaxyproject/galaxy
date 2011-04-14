import os
import sys
from xml.etree import ElementTree as ET

# Todo: Keep order by "prioritizing" tools in sections
# Todo: Labels (as lower level sections?)
# Todo: Some tools are switched "off" by default: it must be possible to "off"
#       a tool without having to remove it?

def prettify(elem):
    from xml.dom import minidom
    rough_string = ET.tostring(elem, 'utf-8')
    repaired = minidom.parseString(rough_string)
    return repaired.toprettyxml(indent='  ')

# Build a list of all toolconf xml files in the tools directory
def getfnl(startdir):
    filenamelist = []
    for root, dirs, files in os.walk(startdir):
        for fn in files:
            fullfn = os.path.join(root, fn)
            if fn.endswith('toolconf.xml'):
                filenamelist.append(fullfn)
            elif fn.endswith('.xml'):
                try:
                    doc = ET.parse(fullfn)
                except:
                    print "An OOPS on", fullfn
                    raise
                rootelement = doc.getroot()
                if rootelement.tag == 'tool':
                    if rootelement.findall('section'):
                        filenamelist.append(fullfn)
    return filenamelist

class ToolSections(object):
    def __init__(self):
        self.tools = {'':[]}
        self.sections = [''] # Empty section first

    def add(self, el, sectionelement):
        if sectionelement is not None:
            section = str(sectionelement.text)
            section = section.strip()
        else:
            section = ''
        if not self.tools.has_key(section):
            self.sections.append(section)
            self.tools[section]= []
        self.tools[section].append(el)

# Analyze all the toolconf xml files given in the filenamelist (fnl)
# Build a list of all sections
def scanfiles(fnl):
    ts = ToolSections()
    for fn in fnl: # specialized toolconf.xml files.
        doc = ET.parse(fn)
        root = doc.getroot()
        
        if root.tag == 'tool':
            tools = [root]
        else:
            tools = doc.findall('tool')
            
        for tool in tools:
            if tool.attrib.has_key('file'):
                fileattrib = os.path.join(os.getcwd(),
                                          os.path.dirname(fn),
                                          tool.attrib['file'])
            else: # It must be the current file
                fileattrib = os.path.join(os.getcwd(), fn)
            attrib = {'file': fileattrib}
            tags = tool.find('tags')
            if tags:
                tagarray = []
                for tag in tags.findall('tag'):
                    tagarray.append(tag.text)
                attrib['tags'] = ",".join(tagarray)
            toolelement = ET.Element('tool', attrib)
            if not 'off' in tagarray:
                ts.add(toolelement, tool.find('section'))
    return ts

def assemble():
    fnl = getfnl('tools')
    fnl.sort()

    ts = scanfiles(fnl)

    toolbox = ET.Element('toolbox')

    sectionnumber = 0
    for section in ts.sections:
        if section:
            sectionnumber += 1
            ident = "section%d" % sectionnumber
            sectionelement = ET.SubElement(toolbox,'section', {'name': section,
                                                               'id': ident})
            puttoolsin = sectionelement
        else:
            puttoolsin = toolbox
        for tool in ts.tools[section]:
            attrib = tool.attrib
            toolelement = ET.SubElement(puttoolsin, 'tool', attrib)

    print prettify(toolbox)
    
if __name__ == "__main__":
    assemble()
