"""This script loads a Galaxy datatypes registry against Galaxy's datatypes_conf.xml.sample file
and uses it to generate a tabular file with four columns

 - Galaxy datatype as short extension (e.g. bam)
 - EDAM format (e.g. format_XXXX)
 - EDAM label.
 - EDAM definition.

This file is printed to standard out. This script is designed to be
run from the Galaxy root.

 % python script/edam_mapping.py > edam_mapping.tsv
"""
from __future__ import absolute_import
from __future__ import print_function

import os
import sys
import urllib2
from xml import etree

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, 'lib')))

import galaxy.model
import galaxy.datatypes.registry

SCRIPTS_DIR = os.path.dirname(__file__)
PROJECT_DIR = os.path.abspath(os.path.join(SCRIPTS_DIR, os.pardir))
CONFIG_FILE = os.path.join(PROJECT_DIR, "config", "datatypes_conf.xml.sample")

datatypes_registry = galaxy.datatypes.registry.Registry()
datatypes_registry.load_datatypes(root_dir=PROJECT_DIR, config=CONFIG_FILE)

EDAM_OWL_URL = "http://data.bioontology.org/ontologies/EDAM/submissions/25/download?apikey=8b5b7825-538d-40e0-9e9e-5ab9274a9aeb"


if not os.path.exists("/tmp/edam.owl"):
    open("/tmp/edam.owl", "w").write( urllib2.urlopen( EDAM_OWL_URL ).read() )


owl_xml_tree = etree.ElementTree.parse("/tmp/edam.owl")
format_info = {}
for child in owl_xml_tree.getroot().findall('{http://www.w3.org/2002/07/owl#}Class'):
    about = child.attrib.get("{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about")
    if not about:
        continue
    if not about.startswith("http://edamontology.org/format_"):
        continue
    the_format = about[len("http://edamontology.org/"):]
    label = child.find("{http://www.w3.org/2000/01/rdf-schema#}label").text
    definition = ""
    def_el = child.find("{http://www.geneontology.org/formats/oboInOwl#}hasDefinition")
    if def_el is not None:
        definition = def_el.text
    format_info[the_format] = {"label": label, "definition": definition}

for ext, edam_format in sorted(datatypes_registry.edam_formats.items()):
    edam_info = format_info[edam_format]
    edam_label = edam_info["label"]
    edam_definition = edam_info["definition"]
    print("%s\t%s\t%s\t%s" % (ext, edam_format, edam_label, edam_definition))
