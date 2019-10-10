import os
import os.path
import shutil
import tempfile
import unittest
from math import isinf

from galaxy.tools.parser.factory import get_tool_source


TOOL_XML_1 = """
<tool name="BWA Mapper" id="bwa" version="1.0.1" is_multi_byte="true" display_interface="true" require_login="true" hidden="true">
    <description>The BWA Mapper</description>
    <version_command interpreter="python">bwa.py --version</version_command>
    <parallelism method="multi" split_inputs="input1" split_mode="to_size" split_size="1" merge_outputs="out_file1" />
    <command interpreter="python">bwa.py --arg1=42</command>
    <requirements>
        <container type="docker">mycool/bwa</container>
        <requirement type="package" version="1.0">bwa</requirement>
    </requirements>
    <outputs>
        <data name="out1" format="bam" from_work_dir="out1.bam" />
    </outputs>
    <stdio>
        <exit_code range="1:" level="fatal" />
    </stdio>
    <help>This is HELP TEXT1!!!</help>
    <tests>
        <test>
            <param name="foo" value="5" />
            <output name="out1" file="moo.txt" />
        </test>
        <test>
            <param name="foo" value="5">
            </param>
            <output name="out1" lines_diff="4" compare="sim_size">
                <metadata name="dbkey" value="hg19" />
            </output>
        </test>
    </tests>
</tool>
"""

TOOL_YAML_1 = """
name: "Bowtie Mapper"
class: GalaxyTool
id: bowtie
version: 1.0.2
description: "The Bowtie Mapper"
command: "bowtie_wrapper.pl --map-the-stuff"
interpreter: "perl"
runtime_version:
  command: "bowtie --version"
requirements:
  - type: package
    name: bwa
    version: 1.0.1
containers:
  - type: docker
    identifier: "awesome/bowtie"
outputs:
  out1:
    format: bam
    from_work_dir: out1.bam
inputs:
  - name: input1
    type: integer
    min: 7
    max: 8
  - name: moo
    label: cow
    type: repeat
    blocks:
      - name: nestinput
        type: data
      - name: nestsample
        type: text
help:
|
    This is HELP TEXT2!!!
tests:
   - inputs:
       foo: 5
     outputs:
       out1: moo.txt
   - inputs:
       foo:
         value: 5
     outputs:
       out1:
         lines_diff: 4
         compare: sim_size
"""


class BaseLoaderTestCase(unittest.TestCase):

    def setUp(self):
        self.temp_directory = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_directory)

    @property
    def _tool_source(self):
        return self._get_tool_source()

    def _get_tool_source(self, source_file_name=None, source_contents=None):
        if source_file_name is None:
            source_file_name = self.source_file_name
        if source_contents is None:
            source_contents = self.source_contents
        if not os.path.isabs(source_file_name):
            path = os.path.join(self.temp_directory, source_file_name)
            open(path, "w").write(source_contents)
        else:
            path = source_file_name
        tool_source = get_tool_source(path)
        return tool_source


class XmlLoaderTestCase(BaseLoaderTestCase):
    source_file_name = "bwa.xml"
    source_contents = TOOL_XML_1

    def test_tool_source_to_string(self):
        # Previously this threw an Exception - test for regression.
        str(self._tool_source)

    def test_version(self):
        assert self._tool_source.parse_version() == "1.0.1"

    def test_id(self):
        assert self._tool_source.parse_id() == "bwa"

    def test_module_and_type(self):
        assert self._tool_source.parse_tool_module() is None
        assert self._tool_source.parse_tool_type() is None

    def test_name(self):
        assert self._tool_source.parse_name() == "BWA Mapper"

    def test_is_multi_byte(self):
        assert self._tool_source.parse_is_multi_byte()

    def test_display_interface(self):
        assert self._tool_source.parse_display_interface(False)

    def test_require_login(self):
        assert self._tool_source.parse_require_login(False)

    def test_parse_request_param_translation_elem(self):
        assert self._tool_source.parse_request_param_translation_elem() is None

    def test_command_parsing(self):
        assert self._tool_source.parse_command() == "bwa.py --arg1=42"
        assert self._tool_source.parse_interpreter() == "python"

    def test_descripting_parsing(self):
        assert self._tool_source.parse_description() == "The BWA Mapper"

    def test_version_command(self):
        assert self._tool_source.parse_version_command() == "bwa.py --version"
        assert self._tool_source.parse_version_command_interpreter() == "python"

    def test_parallelism(self):
        parallelism_info = self._tool_source.parse_parallelism()
        assert parallelism_info.method == "multi"
        assert parallelism_info.attributes["split_inputs"] == "input1"

    def test_hidden(self):
        assert self._tool_source.parse_hidden()

    def test_action(self):
        assert self._tool_source.parse_action_module() is None

    def test_requirements(self):
        requirements, containers = self._tool_source.parse_requirements_and_containers()
        assert requirements[0].type == "package"
        assert list(containers)[0].identifier == "mycool/bwa"

    def test_outputs(self):
        outputs, output_collections = self._tool_source.parse_outputs(object())
        assert len(outputs) == 1, outputs
        assert len(output_collections) == 0

    def test_stdio(self):
        exit, regexes = self._tool_source.parse_stdio()
        assert len(exit) == 1
        assert len(regexes) == 0
        assert exit[0].range_start == 1
        assert isinf(exit[0].range_end)

    def test_help(self):
        help_text = self._tool_source.parse_help()
        assert help_text.strip() == "This is HELP TEXT1!!!"

    def test_tests(self):
        tests_dict = self._tool_source.parse_tests_to_dict()
        tests = tests_dict["tests"]
        assert len(tests) == 2
        test_dict = tests[0]
        inputs = test_dict["inputs"]
        assert len(inputs) == 1, test_dict
        input1 = inputs[0]
        assert input1["name"] == "foo", input1
        assert input1["value"] == "5"

        outputs = test_dict["outputs"]
        assert len(outputs) == 1
        output1 = outputs[0]
        assert output1["name"] == 'out1'
        assert output1["value"] == 'moo.txt'
        attributes1 = output1["attributes"]
        assert attributes1["compare"] == "diff"
        assert attributes1["lines_diff"] == 0

        test2 = tests[1]
        outputs = test2["outputs"]
        assert len(outputs) == 1
        output2 = outputs[0]
        assert output2["name"] == 'out1'
        assert output2["value"] is None
        attributes1 = output2["attributes"]
        assert attributes1["compare"] == "sim_size"
        assert attributes1["lines_diff"] == 4

    def test_exit_code(self):
        tool_source = self._get_tool_source(source_contents="""<tool id="bwa" name="bwa">
            <command detect_errors="exit_code">
                ls
            </command>
        </tool>
        """)
        exit, regexes = tool_source.parse_stdio()
        assert len(exit) == 2, exit
        assert len(regexes) == 0, regexes

        tool_source = self._get_tool_source(source_contents="""<tool id="bwa" name="bwa">
            <command detect_errors="aggressive">
                ls
            </command>
        </tool>
        """)
        exit, regexes = tool_source.parse_stdio()
        assert len(exit) == 2, exit
        # error:, exception: various memory exception...
        assert len(regexes) > 2, regexes

    def test_sanitize_option(self):
        assert self._tool_source.parse_sanitize() is True

    def test_refresh_option(self):
        assert self._tool_source.parse_refresh() is False


class YamlLoaderTestCase(BaseLoaderTestCase):
    source_file_name = "bwa.yml"
    source_contents = TOOL_YAML_1

    def test_version(self):
        assert self._tool_source.parse_version() == "1.0.2"

    def test_id(self):
        assert self._tool_source.parse_id() == "bowtie"

    def test_module_and_type(self):
        # These just rely on defaults
        assert self._tool_source.parse_tool_module() is None
        assert self._tool_source.parse_tool_type() is None

    def test_name(self):
        assert self._tool_source.parse_name() == "Bowtie Mapper"

    def test_is_multi_byte(self):
        assert not self._tool_source.parse_is_multi_byte()

    def test_display_interface(self):
        assert not self._tool_source.parse_display_interface(False)
        assert self._tool_source.parse_display_interface(True)

    def test_require_login(self):
        assert not self._tool_source.parse_require_login(False)

    def test_parse_request_param_translation_elem(self):
        assert self._tool_source.parse_request_param_translation_elem() is None

    def test_command_parsing(self):
        assert self._tool_source.parse_command() == "bowtie_wrapper.pl --map-the-stuff"
        assert self._tool_source.parse_interpreter() == "perl"

    def test_parse_redirect_url_params_elem(self):
        assert self._tool_source.parse_redirect_url_params_elem() is None

    def test_descripting_parsing(self):
        assert self._tool_source.parse_description() == "The Bowtie Mapper"

    def test_version_command(self):
        assert self._tool_source.parse_version_command() == "bowtie --version"
        assert self._tool_source.parse_version_command_interpreter() is None

    def test_parallelism(self):
        assert self._tool_source.parse_parallelism() is None

    def test_hidden(self):
        assert not self._tool_source.parse_hidden()

    def test_action(self):
        assert self._tool_source.parse_action_module() is None

    def test_requirements(self):
        requirements, containers = self._tool_source.parse_requirements_and_containers()
        assert requirements[0].type == "package"
        assert requirements[0].name == "bwa"
        assert containers[0].identifier == "awesome/bowtie"

    def test_outputs(self):
        outputs, output_collections = self._tool_source.parse_outputs(object())
        assert len(outputs) == 1
        assert len(output_collections) == 0

    def test_stdio(self):
        exit, regexes = self._tool_source.parse_stdio()
        assert len(exit) == 2

        assert isinf(exit[0].range_start)
        assert exit[0].range_start == float("-inf")

        assert exit[1].range_start == 1
        assert isinf(exit[1].range_end)

    def test_help(self):
        help_text = self._tool_source.parse_help()
        assert help_text.strip() == "This is HELP TEXT2!!!"

    def test_inputs(self):
        input_pages = self._tool_source.parse_input_pages()
        assert input_pages.inputs_defined
        page_sources = input_pages.page_sources
        assert len(page_sources) == 1
        page_source = page_sources[0]
        input_sources = list(page_source.parse_input_sources())
        assert len(input_sources) == 2

    def test_tests(self):
        tests_dict = self._tool_source.parse_tests_to_dict()
        tests = tests_dict["tests"]
        assert len(tests) == 2
        test_dict = tests[0]
        inputs = test_dict["inputs"]
        assert len(inputs) == 1
        input1 = inputs[0]
        assert input1["name"] == "foo"
        assert input1["value"] == 5

        outputs = test_dict["outputs"]
        assert len(outputs) == 1
        output1 = outputs[0]
        assert output1["name"] == 'out1'
        assert output1["value"] == 'moo.txt'
        attributes1 = output1["attributes"]
        assert attributes1["compare"] == "diff"
        assert attributes1["lines_diff"] == 0

        test2 = tests[1]
        outputs = test2["outputs"]
        assert len(outputs) == 1
        output2 = outputs[0]
        assert output2["name"] == 'out1'
        assert output2["value"] is None
        attributes1 = output2["attributes"]
        assert attributes1["compare"] == "sim_size"
        assert attributes1["lines_diff"] == 4

    def test_sanitize(self):
        assert self._tool_source.parse_sanitize() is True


class DataSourceLoaderTestCase(BaseLoaderTestCase):
    source_file_name = "ds.xml"
    source_contents = """<?xml version="1.0"?>
<tool name="YeastMine" id="yeastmine" tool_type="data_source">
    <description>server</description>
    <command interpreter="python">data_source.py $output $__app__.config.output_size_limit</command>
    <inputs action="http://yeastmine.yeastgenome.org/yeastmine/begin.do" check_values="false" method="get">
        <display>go to yeastMine server $GALAXY_URL</display>
    </inputs>
    <request_param_translation>
        <request_param galaxy_name="data_type" remote_name="data_type" missing="auto" >
            <value_translation>
                <value galaxy_value="auto" remote_value="txt" /> <!-- intermine currently always provides 'txt', make this auto detect -->
            </value_translation>
        </request_param>
    </request_param_translation>
    <!-- Following block doesn't really belong here - not sure what block is suppose to do actually cannot
         find actual usage. -->
    <redirect_url_params>cow</redirect_url_params>
    <uihints minwidth="800"/>
    <outputs>
        <data name="output" format="txt" />
    </outputs>
    <options sanitize="False" refresh="True"/>
</tool>
"""

    def test_sanitize_option(self):
        assert self._tool_source.parse_sanitize() is False

    def test_refresh_option(self):
        assert self._tool_source.parse_refresh() is True

    def test_tool_type(self):
        assert self._tool_source.parse_tool_type() == "data_source"

    def test_parse_request_param_translation_elem(self):
        assert self._tool_source.parse_request_param_translation_elem() is not None

    def test_redirect_url_params_elem(self):
        assert self._tool_source.parse_redirect_url_params_elem() is not None

    def test_parallelism(self):
        assert self._tool_source.parse_parallelism() is None

    def test_hidden(self):
        assert not self._tool_source.parse_hidden()


class ApplyRulesToolLoaderTestCase(BaseLoaderTestCase):
    source_file_name = os.path.join(os.getcwd(), "lib/galaxy/tools/apply_rules.xml")
    source_contents = None

    def test_tool_type(self):
        tool_module = self._tool_source.parse_tool_module()
        assert tool_module[0] == "galaxy.tools"
        assert tool_module[1] == "ApplyRulesTool"
        assert self._tool_source.parse_tool_type() == "apply_rules_to_collection"

    def test_outputs(self):
        outputs, output_collections = self._tool_source.parse_outputs(object())
        assert len(outputs) == 1
        assert len(output_collections) == 1


class BuildListToolLoaderTestCase(BaseLoaderTestCase):
    source_file_name = os.path.join(os.getcwd(), "lib/galaxy/tools/build_list.xml")
    source_contents = None

    def test_tool_type(self):
        tool_module = self._tool_source.parse_tool_module()
        assert tool_module[0] == "galaxy.tools"
        assert tool_module[1] == "BuildListCollectionTool"


class SpecialToolLoaderTestCase(BaseLoaderTestCase):
    source_file_name = os.path.join(os.getcwd(), "lib/galaxy/tools/imp_exp/exp_history_to_archive.xml")
    source_contents = None

    def test_tool_type(self):
        tool_module = self._tool_source.parse_tool_module()
        # Probably we don't parse_tool_module any more? -
        # tool_type seems sufficient.
        assert tool_module[0] == "galaxy.tools"
        assert tool_module[1] == "ExportHistoryTool"
        assert self._tool_source.parse_tool_type() == "export_history"

    def test_is_multi_byte(self):
        assert not self._tool_source.parse_is_multi_byte()

    def test_version_command(self):
        assert self._tool_source.parse_version_command() is None
        assert self._tool_source.parse_version_command_interpreter() is None

    def test_action(self):
        action = self._tool_source.parse_action_module()
        assert action[0] == "galaxy.tools.actions.history_imp_exp"
        assert action[1] == "ExportHistoryToolAction"


class CollectionTestCase(BaseLoaderTestCase):
    source_file_name = os.path.join(os.getcwd(), "test/functional/tools/collection_two_paired.xml")
    source_contents = None

    def test_tests(self):
        tests_dict = self._tool_source.parse_tests_to_dict()
        tests = tests_dict["tests"]
        assert len(tests) == 2
        assert len(tests[0]["inputs"]) == 3, tests[0]
        outputs, output_collections = self._tool_source.parse_outputs(None)
        assert len(output_collections) == 0


class CollectionOutputXmlTestCase(BaseLoaderTestCase):
    source_file_name = os.path.join(os.getcwd(), "test/functional/tools/collection_creates_pair.xml")
    source_contents = None

    def test_tests(self):
        outputs, output_collections = self._tool_source.parse_outputs(None)
        assert len(output_collections) == 1


class CollectionOutputYamlTestCase(BaseLoaderTestCase):
    source_file_name = os.path.join(os.getcwd(), "test/functional/tools/collection_creates_pair_y.yml")
    source_contents = None

    def test_tests(self):
        outputs, output_collections = self._tool_source.parse_outputs(None)
        assert len(output_collections) == 1
