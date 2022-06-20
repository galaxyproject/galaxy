import os
import os.path
import shutil
import tempfile
import unittest
from math import isinf
from typing import Optional

from galaxy.tool_util.parser.factory import get_tool_source
from galaxy.util import galaxy_directory

TOOL_XML_1 = """
<tool name="BWA Mapper" id="bwa" version="1.0.1" display_interface="true" require_login="true" hidden="true">
    <description>The BWA Mapper</description>
    <xrefs>
        <xref type="bio.tools">bwa</xref>
    </xrefs>
    <creator>
        <person
            givenName="Björn"
            familyName="Grüning"
            identifier="http://orcid.org/0000-0002-3079-6586" />
        <organization
            url="https://galaxyproject.org/iuc/"
            name="Galaxy IUC" />
    </creator>
    <version_command interpreter="python">bwa.py --version</version_command>
    <parallelism method="multi" split_inputs="input1" split_mode="to_size" split_size="1" merge_outputs="out_file1" />
    <command interpreter="python">bwa.py --arg1=42</command>
    <requirements>
        <container type="docker">mycool/bwa</container>
        <requirement type="package" version="1.0">bwa</requirement>
        <resource type="cores_min">1</resource>
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

TOOL_WITH_TOKEN = r"""
<tool id="tool_with_token" name="Token" version="1">
    <macros>
        <token name="@ESCAPE_IDENTIFIER@">
<![CDATA[
#set identifier = re.sub('[^\s\w\-]', '_', str($file.element_identifier))
        ]]></token>
        <token name="@NESTED_TOKEN@">
<![CDATA[
    before
    @ESCAPE_IDENTIFIER@
    after
        ]]></token>
    </macros>
    <command>
@NESTED_TOKEN@
    </command>
</tool>
"""

TOOL_WTIH_TOKEN_FROM_MACRO_FILE = r"""
<tool id="tool_with_token" name="Token" version="1">
    <macros>
        <import>macros.xml</import>
    </macros>
    <command detect_errors="exit_code"><![CDATA[@CATS@]]></command>
</tool>
"""

MACRO_CONTENTS = r"""<?xml version="1.0"?>
<macros>
    <token name="@CATS@">cat   </token>
</macros>
"""

TOOL_WITH_RECURSIVE_TOKEN = r"""
<tool id="tool_with_recursive_token" name="Token" version="1">
    <macros>
        <token name="@NESTED_TOKEN@">
<![CDATA[
    before
    @NESTED_TOKEN@
    after
        ]]></token>
    </macros>
    <command>
@NESTED_TOKEN@
    </command>
</tool>
"""

TOOL_YAML_1 = """
name: "Bowtie Mapper"
class: GalaxyTool
id: bowtie
version: 1.0.2
description: "The Bowtie Mapper"
xrefs:
  - type: bio.tools
    value: bwa
command: "bowtie_wrapper.pl --map-the-stuff"
interpreter: "perl"
runtime_version:
  command: "bowtie --version"
requirements:
  - type: package
    name: bwa
    version: 1.0.1
  - type: resource
    cores_min: 1
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

TOOL_EXPRESSION_XML_1 = """
<tool name="parse_int" id="parse_int" version="0.1.0" tool_type="expression">
    <description>Parse Int</description>
    <expression type="ecma5.1">
        {return {'output': parseInt($job.input1)};}
    </expression>
    <inputs>
        <input type="text" label="Text to parse." name="input1" />
    </inputs>
    <outputs>
        <output type="integer" name="out1" from="output" />
    </outputs>
    <help>Parse an integer from text.</help>
</tool>
"""


TOOL_EXPRESSION_YAML_1 = """
class: GalaxyExpressionTool
name: "parse_int"
id: parse_int
version: 1.0.2
expression: "{return {'output': parseInt($job.input1)};}"
inputs:
 - name: input1
   label: Text to parse
   type: text
outputs:
  out1:
    type: integer
    from: "#output"
"""


def get_test_tool_source(source_file_name=None, source_contents=None, macro_contents=None, temp_directory=None):
    source_directory = temp_directory or tempfile.mkdtemp()
    macro_paths = []
    if not os.path.isabs(source_file_name):
        path = os.path.join(source_directory, source_file_name)
        with open(path, "w") as out:
            out.write(source_contents)
        if macro_contents:
            macro_path = os.path.join(source_directory, "macros.xml")
            with open(macro_path, "w") as out:
                out.write(macro_contents)
            macro_paths = [macro_path]
    else:
        path = source_file_name
    tool_source = get_tool_source(path, macro_paths=macro_paths)
    if temp_directory is None:
        shutil.rmtree(source_directory)
    return tool_source


class BaseLoaderTestCase(unittest.TestCase):
    source_file_name: Optional[str] = None
    source_contents: Optional[str] = None

    def setUp(self):
        self.temp_directory = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_directory)

    @property
    def _tool_source(self):
        return self._get_tool_source()

    def _get_tool_source(self, source_file_name=None, source_contents=None, macro_contents=None):
        if source_file_name is None:
            source_file_name = self.source_file_name
        if source_contents is None:
            source_contents = self.source_contents
        return get_test_tool_source(
            source_file_name,
            source_contents,
            macro_contents,
            self.temp_directory,
        )


class XmlExpressionLoaderTestCase(BaseLoaderTestCase):
    source_file_name = "expression.xml"
    source_contents = TOOL_EXPRESSION_XML_1

    def test_expression(self):
        assert self._tool_source.parse_expression().strip() == "{return {'output': parseInt($job.input1)};}"

    def test_tool_type(self):
        assert self._tool_source.parse_tool_type() == "expression"


class YamlExpressionLoaderTestCase(BaseLoaderTestCase):
    source_file_name = "expression.yml"
    source_contents = TOOL_EXPRESSION_XML_1


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
        requirements, containers, resource_requirements = self._tool_source.parse_requirements_and_containers()
        assert requirements[0].type == "package"
        assert list(containers)[0].identifier == "mycool/bwa"
        assert resource_requirements[0].resource_type == "cores_min"
        assert not resource_requirements[0].runtime_required

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
        assert output1["name"] == "out1"
        assert output1["value"] == "moo.txt"
        attributes1 = output1["attributes"]
        assert attributes1["compare"] == "diff"
        assert attributes1["lines_diff"] == 0

        test2 = tests[1]
        outputs = test2["outputs"]
        assert len(outputs) == 1
        output2 = outputs[0]
        assert output2["name"] == "out1"
        assert output2["value"] is None
        attributes1 = output2["attributes"]
        assert attributes1["compare"] == "sim_size"
        assert attributes1["lines_diff"] == 4

    def test_xrefs(self):
        xrefs = self._tool_source.parse_xrefs()
        assert xrefs == [{"value": "bwa", "reftype": "bio.tools"}]

    def test_exit_code(self):
        tool_source = self._get_tool_source(
            source_contents="""<tool id="bwa" name="bwa">
            <command detect_errors="exit_code">
                ls
            </command>
        </tool>
        """
        )
        exit, regexes = tool_source.parse_stdio()
        assert len(exit) == 2, exit
        assert len(regexes) == 0, regexes

        tool_source = self._get_tool_source(
            source_contents="""<tool id="bwa" name="bwa">
            <command detect_errors="aggressive">
                ls
            </command>
        </tool>
        """
        )
        exit, regexes = tool_source.parse_stdio()
        assert len(exit) == 2, exit
        # error:, exception: various memory exception...
        assert len(regexes) > 2, regexes

    def test_sanitize_option(self):
        assert self._tool_source.parse_sanitize() is True

    def test_refresh_option(self):
        assert self._tool_source.parse_refresh() is False

    def test_nested_token(self):
        tool_source = self._get_tool_source(source_contents=TOOL_WITH_TOKEN)
        command = tool_source.parse_command()
        assert command
        assert "@" not in command

    def test_token_significant_whitespace(self):
        tool_source = self._get_tool_source(
            source_contents=TOOL_WTIH_TOKEN_FROM_MACRO_FILE, macro_contents=MACRO_CONTENTS
        )
        command = tool_source.parse_command()
        assert command == "cat   "
        assert "@" not in command

    def test_recursive_token(self):
        with self.assertRaisesRegex(Exception, "^Token '@NESTED_TOKEN@' cannot contain itself$"):
            self._get_tool_source(source_contents=TOOL_WITH_RECURSIVE_TOKEN)

    def test_creator(self):
        creators = self._tool_source.parse_creator()
        assert len(creators) == 2
        creator1 = creators[0]
        assert creator1["class"] == "Person"
        assert creator1["identifier"] == "http://orcid.org/0000-0002-3079-6586"

        creator2 = creators[1]
        assert creator2["class"] == "Organization"
        assert creator2["name"] == "Galaxy IUC"


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
        requirements, containers, resource_requirements = self._tool_source.parse_requirements_and_containers()
        assert requirements[0].type == "package"
        assert requirements[0].name == "bwa"
        assert containers[0].identifier == "awesome/bowtie"
        assert resource_requirements[0].resource_type == "cores_min"

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
        input_sources = page_source.parse_input_sources()
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
        assert output1["name"] == "out1"
        assert output1["value"] == "moo.txt"
        attributes1 = output1["attributes"]
        assert attributes1["compare"] == "diff"
        assert attributes1["lines_diff"] == 0

        test2 = tests[1]
        outputs = test2["outputs"]
        assert len(outputs) == 1
        output2 = outputs[0]
        assert output2["name"] == "out1"
        assert output2["value"] is None
        attributes1 = output2["attributes"]
        assert attributes1["compare"] == "sim_size"
        assert attributes1["lines_diff"] == 4

    def test_xrefs(self):
        xrefs = self._tool_source.parse_xrefs()
        assert xrefs == [{"value": "bwa", "reftype": "bio.tools"}]

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
    source_file_name = os.path.join(galaxy_directory(), "lib/galaxy/tools/apply_rules.xml")
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
    source_file_name = os.path.join(galaxy_directory(), "lib/galaxy/tools/build_list.xml")
    source_contents = None

    def test_tool_type(self):
        tool_module = self._tool_source.parse_tool_module()
        assert tool_module[0] == "galaxy.tools"
        assert tool_module[1] == "BuildListCollectionTool"


class ExpressionTestToolLoaderTestCase(BaseLoaderTestCase):
    source_file_name = os.path.join(galaxy_directory(), "test/functional/tools/expression_null_handling_boolean.xml")
    source_contents = None

    def test_test(self):
        test_dicts = self._tool_source.parse_tests_to_dict()["tests"]
        assert len(test_dicts) == 3
        test_dict_0 = test_dicts[0]
        assert "outputs" in test_dict_0, test_dict_0
        outputs = test_dict_0["outputs"]
        output0 = outputs[0]
        assert "object" in output0["attributes"]
        assert output0["attributes"]["object"] is True

        test_dict_1 = test_dicts[1]
        assert "outputs" in test_dict_1, test_dict_1
        outputs = test_dict_1["outputs"]
        output0 = outputs[0]
        assert "object" in output0["attributes"]
        assert output0["attributes"]["object"] is False

        test_dict_2 = test_dicts[2]
        assert "outputs" in test_dict_2, test_dict_2
        outputs = test_dict_2["outputs"]
        output0 = outputs[0]
        assert "object" in output0["attributes"]
        assert output0["attributes"]["object"] is None


class ExpressionOutputDataToolLoaderTestCase(BaseLoaderTestCase):
    source_file_name = os.path.join(galaxy_directory(), "test/functional/tools/expression_pick_larger_file.xml")
    source_contents = None

    def test_output_parsing(self):
        outputs, _ = self._tool_source.parse_outputs(None)
        assert "larger_file" in outputs
        tool_output = outputs["larger_file"]
        assert tool_output.format == "data"
        assert tool_output.from_expression == "output"


class SpecialToolLoaderTestCase(BaseLoaderTestCase):
    source_file_name = os.path.join(galaxy_directory(), "lib/galaxy/tools/imp_exp/exp_history_to_archive.xml")
    source_contents = None

    def test_tool_type(self):
        tool_module = self._tool_source.parse_tool_module()
        # Probably we don't parse_tool_module any more? -
        # tool_type seems sufficient.
        assert tool_module[0] == "galaxy.tools"
        assert tool_module[1] == "ExportHistoryTool"
        assert self._tool_source.parse_tool_type() == "export_history"

    def test_version_command(self):
        assert self._tool_source.parse_version_command() is None
        assert self._tool_source.parse_version_command_interpreter() is None

    def test_action(self):
        action = self._tool_source.parse_action_module()
        assert action[0] == "galaxy.tools.actions.history_imp_exp"
        assert action[1] == "ExportHistoryToolAction"


class CollectionTestCase(BaseLoaderTestCase):
    source_file_name = os.path.join(galaxy_directory(), "test/functional/tools/collection_two_paired.xml")
    source_contents = None

    def test_tests(self):
        tests_dict = self._tool_source.parse_tests_to_dict()
        tests = tests_dict["tests"]
        assert len(tests) == 2
        assert len(tests[0]["inputs"]) == 3, tests[0]

        outputs, output_collections = self._tool_source.parse_outputs(None)
        assert len(output_collections) == 0


class CollectionOutputXmlTestCase(BaseLoaderTestCase):
    source_file_name = os.path.join(galaxy_directory(), "test/functional/tools/collection_creates_pair.xml")
    source_contents = None

    def test_tests(self):
        outputs, output_collections = self._tool_source.parse_outputs(None)
        assert len(output_collections) == 1


class CollectionOutputYamlTestCase(BaseLoaderTestCase):
    source_file_name = os.path.join(galaxy_directory(), "test/functional/tools/collection_creates_pair_y.yml")
    source_contents = None

    def test_tests(self):
        outputs, output_collections = self._tool_source.parse_outputs(None)
        assert len(output_collections) == 1


class EnvironmentVariablesTestCase(BaseLoaderTestCase):
    source_file_name = os.path.join(galaxy_directory(), "test/functional/tools/environment_variables.xml")
    source_contents = None

    def test_tests(self):
        tests_dict = self._tool_source.parse_tests_to_dict()
        tests = tests_dict["tests"]
        assert len(tests) == 1


class ExpectationsTestCase(BaseLoaderTestCase):
    source_file_name = os.path.join(galaxy_directory(), "test/functional/tools/detect_errors.xml")
    source_contents = None

    def test_tests(self):
        tests_dict = self._tool_source.parse_tests_to_dict()
        tests = tests_dict["tests"]
        assert len(tests) == 10
        test_0 = tests[0]
        assert len(test_0["stderr"]) == 1
        assert len(test_0["stdout"]) == 2


class ExpectationsCommandVersionTestCase(BaseLoaderTestCase):
    source_file_name = os.path.join(galaxy_directory(), "test/functional/tools/job_properties.xml")
    source_contents = None

    def test_tests(self):
        tests_dict = self._tool_source.parse_tests_to_dict()
        tests = tests_dict["tests"]
        assert len(tests) > 0
        test_0 = tests[0]
        assert len(test_0["command_version"]) == 1


class QcStdioTestCase(BaseLoaderTestCase):
    source_file_name = os.path.join(galaxy_directory(), "test/functional/tools/qc_stdout.xml")
    source_contents = None

    def test_tests(self):
        exit, regexes = self._tool_source.parse_stdio()
        assert len(exit) == 2
        assert len(regexes) == 1
        regex = regexes[0]
        assert regex.error_level == 1.1
