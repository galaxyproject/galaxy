import string
import unittest
from xml.etree.ElementTree import XML

from galaxy import model
from galaxy.exceptions import UserActivationRequiredException
from galaxy.tools.actions import (
    DefaultToolAction,
    determine_output_format,
    on_text_for_names
)
from galaxy.tools.parser.output_objects import ToolOutput
from .. import tools_support


# I cannot think of a saner way to test if data is being wrapped than use a
# data param in the output label - though you would probably never want to do
# this.
DATA_IN_LABEL_TOOL_CONTENTS = '''<tool id="test_tool" name="Test Tool">
    <command>echo "$param1" &lt; $out1</command>
    <inputs>
        <repeat name="repeat1" label="The Repeat">
            <param type="data" name="param1" value="" />
        </repeat>
    </inputs>
    <outputs>
        <data name="out1" format="data" label="Output (${repeat1[0].param1})" />
    </outputs>
</tool>
'''

# Tool with two outputs - used to verify all datasets within same job get same
# object store id.
TWO_OUTPUTS = '''<tool id="test_tool" name="Test Tool">
    <command>echo "$param1" &lt; $out1</command>
    <inputs>
        <param type="text" name="param1" value="" />
    </inputs>
    <outputs>
        <data name="out1" format="data" label="Output ($param1)" />
        <data name="out2" format="data" label="Output 2 ($param1)" />
    </outputs>
</tool>
'''


def test_on_text_for_names():
    def assert_on_text_is(expected, *names):
        on_text = on_text_for_names(names)
        assert on_text == expected, "Wrong on text value %s, expected %s" % (on_text, expected)

    assert_on_text_is("data 1", "data 1")
    assert_on_text_is("data 1 and data 2", "data 1", "data 2")
    assert_on_text_is("data 1, data 2, and data 3", "data 1", "data 2", "data 3")
    assert_on_text_is("data 1, data 2, and others", "data 1", "data 2", "data 3", "data 4")

    assert_on_text_is("data 1 and data 2", "data 1", "data 1", "data 2")


class DefaultToolActionTestCase(unittest.TestCase, tools_support.UsesApp, tools_support.UsesTools):

    def setUp(self):
        self.setup_app()
        history = model.History()
        self.history = history
        self.trans = MockTrans(
            self.app,
            self.history
        )
        self.app.model.context.add(history)
        self.app.model.context.flush()
        self.action = DefaultToolAction()
        self.app.config.len_file_path = "moocow"
        self.app.object_store = MockObjectStore()

    def test_output_created(self):
        _, output = self._simple_execute()
        assert len(output) == 1
        assert "out1" in output

    def test_output_label(self):
        _, output = self._simple_execute()
        self.assertEqual(output["out1"].name, "Output (moo)")

    def test_output_label_data(self):
        hda1 = self.__add_dataset()
        hda2 = self.__add_dataset()
        incoming = {
            "param1": hda1,
            "repeat1": [
                {"param2": hda2},
            ]
        }
        job, output = self._simple_execute(
            tools_support.SIMPLE_CAT_TOOL_CONTENTS,
            incoming,
        )
        self.assertEqual(output["out1"].name, "Test Tool on data 2 and data 1")

    def test_object_store_ids(self):
        _, output = self._simple_execute(contents=TWO_OUTPUTS)
        self.assertEqual(output["out1"].name, "Output (moo)")
        self.assertEqual(output["out2"].name, "Output 2 (moo)")

    def test_params_wrapped(self):
        hda1 = self.__add_dataset()
        _, output = self._simple_execute(
            contents=DATA_IN_LABEL_TOOL_CONTENTS,
            incoming=dict(repeat1=[dict(param1=hda1)]),
        )
        # Again this is a stupid way to ensure data parameters are wrapped.
        self.assertEqual(output["out1"].name, "Output (%s)" % hda1.dataset.get_file_name())

    def test_inactive_user_job_create_failure(self):
        self.trans.user_is_active = False
        try:
            self._simple_execute()
        except UserActivationRequiredException:
            return
        assert False, "Tool execution succeeded for inactive user!"

    def __add_dataset(self, state='ok'):
        hda = model.HistoryDatasetAssociation()
        hda.dataset = model.Dataset()
        hda.dataset.state = 'ok'
        hda.dataset.external_filename = "/tmp/datasets/dataset_001.dat"
        self.history.add_dataset(hda)
        self.app.model.context.flush()
        return hda

    def _simple_execute(self, contents=None, incoming=None):
        if contents is None:
            contents = tools_support.SIMPLE_TOOL_CONTENTS
        if incoming is None:
            incoming = dict(param1="moo")
        self._init_tool(contents)
        return self.action.execute(
            tool=self.tool,
            trans=self.trans,
            history=self.history,
            incoming=incoming,
        )


def test_determine_output_format():
    # Test simple case of explicitly defined output with no changes.
    direct_output = quick_output("txt")
    __assert_output_format_is("txt", direct_output)

    # Test if format is "input" (which just uses the last input on the form.)
    input_based_output = quick_output("input")
    __assert_output_format_is("fastq", input_based_output, [("i1", "fasta"), ("i2", "fastq")])

    # Test using format_source (testing a couple different positions)
    input_based_output = quick_output("txt", format_source="i1")
    __assert_output_format_is("fasta", input_based_output, [("i1", "fasta"), ("i2", "fastq")])

    input_based_output = quick_output("fastq", format_source="hdcai[0]")
    __assert_output_format_is("txt", input_based_output, [("i1", "fasta"), ("i2", "fastq")], add_collection=True)

    input_based_output = quick_output("fastq", format_source="""hdcai["forward"]""")
    __assert_output_format_is("txt", input_based_output, [("i1", "fasta"), ("i2", "fastq")], add_collection=True)

    input_based_output = quick_output("fastq", format_source="""hdcai['forward']""")
    __assert_output_format_is("txt", input_based_output, [("i1", "fasta"), ("i2", "fastq")], add_collection=True)

    input_based_output = quick_output("txt", format_source="i2")
    __assert_output_format_is("fastq", input_based_output, [("i1", "fasta"), ("i2", "fastq")])

    change_format_xml = """<data><change_format>
        <when input="options_type.output_type" value="solexa" format="fastqsolexa" />
        <when input="options_type.output_type" value="illumina" format="fastqillumina" />
    </change_format></data>"""

    change_format_output = quick_output("fastq", change_format_xml=change_format_xml)
    # Test maching a change_format when.
    __assert_output_format_is("fastqillumina", change_format_output, param_context={"options_type": {"output_type": "illumina"}})
    # Test change_format but no match
    __assert_output_format_is("fastq", change_format_output, param_context={"options_type": {"output_type": "sanger"}})

    change_on_metadata_xml_template = string.Template("""<data><change_format>
        <when input_dataset="${input}" attribute="random_field" value="1" format="fastqsolexa" />
        <when input_dataset="${input}" attribute="random_field" value="2" format="fastqillumina" />
    </change_format></data>""")

    change_on_metadata_illumina = change_on_metadata_xml_template.safe_substitute({'input': "i2"})
    change_on_metadata_output = quick_output("fastq", change_format_xml=change_on_metadata_illumina)
    __assert_output_format_is("fastqillumina", change_on_metadata_output, [("i1", "txt"), ("i2", "txt")])

    change_on_metadata_solexa = change_on_metadata_xml_template.safe_substitute({'input': "i1"})
    change_on_metadata_output = quick_output("fastq", change_format_xml=change_on_metadata_solexa)
    __assert_output_format_is("fastqsolexa", change_on_metadata_output, [("i1", "txt"), ("i2", "txt")])


def __assert_output_format_is(expected, output, input_extensions=[], param_context=[], add_collection=False):
    inputs = {}
    last_ext = "data"
    i = 1
    for name, ext in input_extensions:
        hda = model.HistoryDatasetAssociation(extension=ext)
        hda.metadata.random_field = str(i)  # Populate a random metadata field for testing
        inputs[name] = hda
        last_ext = ext
        i += 1

    input_collections = {}
    if add_collection:
        hda_forward = model.HistoryDatasetAssociation(extension="txt")
        hda_reverse = model.HistoryDatasetAssociation(extension="txt")
        c1 = model.DatasetCollection(collection_type="pair")
        hc1 = model.HistoryDatasetCollectionAssociation(collection=c1, name="HistoryCollectionTest1")

        dce1 = model.DatasetCollectionElement(collection=c1, element=hda_forward, element_identifier="forward", element_index=0)
        dce2 = model.DatasetCollectionElement(collection=c1, element=hda_reverse, element_identifier="reverse", element_index=1)
        c1.elements = [dce1, dce2]

        input_collections["hdcai"] = [(hc1, False)]

    actual_format = determine_output_format(output, param_context, inputs, input_collections, last_ext)
    assert actual_format == expected, "Actual format %s, does not match expected %s" % (actual_format, expected)


def quick_output(format, format_source=None, change_format_xml=None):
    test_output = ToolOutput("test_output")
    test_output.format = format
    test_output.format_source = format_source
    if change_format_xml:
        test_output.change_format = XML(change_format_xml)
    else:
        test_output.change_format = None
    return test_output


class MockTrans(object):

    def __init__(self, app, history, user=None):
        self.app = app
        self.history = history
        self.user = user
        self.sa_session = self.app.model.context
        self.model = app.model
        self._user_is_active = True

    def get_user_is_active(self):
        # NOTE: the real user_is_active also checks whether activation is enabled in the config
        return self._user_is_active

    def set_user_is_active(self, active):
        self._user_is_active = active

    user_is_active = property(get_user_is_active, set_user_is_active)

    def check_user_activation(self):
        if not self.user_is_active:
            raise UserActivationRequiredException()

    def db_dataset_for(self, input_db_key):
        return None

    def get_galaxy_session(self):
        return model.GalaxySession()

    def get_current_user_roles(self):
        return []

    def log_event(self, *args, **kwargs):
        pass


class MockObjectStore(object):

    def __init__(self):
        self.created_datasets = []
        self.first_create = True
        self.object_store_id = "mycoolid"

    def create(self, dataset):
        self.created_datasets.append(dataset)
        if self.first_create:
            self.first_create = False
            assert dataset.object_store_id is None
            dataset.object_store_id = self.object_store_id
        else:
            assert dataset.object_store_id == self.object_store_id
