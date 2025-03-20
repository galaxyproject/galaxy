from galaxy.tool_util.ontologies.ontology_data import expand_ontology_data
from .test_parsing import (
    get_test_tool_source,
    TOOL_YAML_1,
)

TOOL_YAML_2 = """
name: "Bowtie Mapper"
class: GalaxyTool
id: bowtie
version: 1.0.2
description: "The Bowtie Mapper"
xrefs:
  - type: bio.tools
    value: bwa
command: "bowtie --map-the-stuff"
outputs:
  out1:
    format: bam
    from_work_dir: out1.bam
edam_operations:
 - operation_0335
edam_topics:
 - topic_0102
inputs:
  - name: input1
    type: integer
"""

TOOL_YAML_3 = """
name: "Bowtie Mapper"
class: GalaxyTool
id: sort1
version: 1.0.2
description: "The Bowtie Mapper"
xrefs:
  - type: bio.tools
    value: bwa
command: "bowtie --map-the-stuff"
outputs:
  out1:
    format: bam
    from_work_dir: out1.bam
inputs:
  - name: input1
    type: integer
"""

TOOL_YAML_NO_EXPLICIT_XREFS = """
name: "Bowtie Mapper"
class: GalaxyTool
id: sort1
version: 1.0.2
description: "The Bowtie Mapper"
command: "bowtie --map-the-stuff"
outputs:
  out1:
    format: bam
    from_work_dir: out1.bam
inputs:
  - name: input1
    type: integer
"""


def test_parse_edam_empty():
    test_source = get_test_tool_source(source_file_name="testtool.yml", source_contents=TOOL_YAML_1)
    ontology_data = expand_ontology_data(test_source, ["bowtie"], None)
    assert ontology_data.edam_operations == []
    assert ontology_data.edam_topics == []


def test_parse_edam_direct():
    test_source = get_test_tool_source(source_file_name="testtool.yml", source_contents=TOOL_YAML_2)
    ontology_data = expand_ontology_data(test_source, ["bowtie"], None)
    assert ontology_data.edam_operations == ["operation_0335"]
    assert ontology_data.edam_topics == ["topic_0102"]


def test_parse_edam_mapping_operations_legacy():
    test_source = get_test_tool_source(source_file_name="testtool.yml", source_contents=TOOL_YAML_3)
    ontology_data = expand_ontology_data(test_source, ["sort1"], None)
    assert ontology_data.edam_operations == ["operation_3802"]
    assert ontology_data.edam_topics == []


def test_parse_biotools_default_mapping():
    test_source = get_test_tool_source(source_file_name="testtool.yml", source_contents=TOOL_YAML_NO_EXPLICIT_XREFS)
    ontology_data = expand_ontology_data(test_source, ["cheetah_problem_unbound_var_input"], None)
    assert ontology_data.xrefs[0]["reftype"] == "bio.tools"
    assert ontology_data.xrefs[0]["value"] == "bwa"

    test_source = get_test_tool_source(source_file_name="testtool.yml", source_contents=TOOL_YAML_NO_EXPLICIT_XREFS)
    ontology_data = expand_ontology_data(test_source, ["rxlr_motifs"], None)
    assert len(ontology_data.xrefs) == 2
    values = [x["value"] for x in ontology_data.xrefs]
    assert "signalp" in values
    assert "hmmer2" in values
