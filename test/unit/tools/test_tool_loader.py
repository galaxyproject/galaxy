from tempfile import mkdtemp
from shutil import rmtree
import os

from galaxy.util import parse_xml
from galaxy.tools.loader import template_macro_params, load_tool

def test_loader():

    class TestToolDirectory(object):
        def __init__(self):
            self.temp_directory = mkdtemp()

        def __enter__(self):
            return self

        def __exit__(self, type, value, tb):
            rmtree(self.temp_directory)

        def write(self, contents, name="tool.xml"):
            open(os.path.join(self.temp_directory, name), "w").write(contents)

        def load(self, name="tool.xml", preprocess=True):
            if preprocess:
                loader = load_tool
            else:
                loader = parse_xml
            return loader(os.path.join(self.temp_directory, name))

    ## Test simple macro replacement.
    with TestToolDirectory() as tool_dir:
        tool_dir.write('''
<tool>
    <expand macro="inputs" />
    <macros>
        <macro name="inputs">
            <inputs />
        </macro>
    </macros>
</tool>''')
        xml = tool_dir.load(preprocess=False)
        assert xml.find("inputs") is None
        xml = tool_dir.load(preprocess=True)
        assert xml.find("inputs") is not None

    # Test importing macros from external files
    with TestToolDirectory() as tool_dir:
        tool_dir.write('''
<tool>
    <expand macro="inputs" />
    <macros>
        <import>external.xml</import>
    </macros>
</tool>''')

        tool_dir.write('''
<macros>
    <macro name="inputs">
        <inputs />
    </macro>
</macros>''', name="external.xml")
        xml = tool_dir.load(preprocess=False)
        assert xml.find("inputs") is None
        xml = tool_dir.load(preprocess=True)
        assert xml.find("inputs") is not None

    # Test macros with unnamed yield statements.
    with TestToolDirectory() as tool_dir:
        tool_dir.write('''
<tool>
    <expand macro="inputs">
        <input name="first_input" />
    </expand>
    <macros>
        <macro name="inputs">
            <inputs>
                <yield />
            </inputs>
        </macro>
    </macros>
</tool>''')
        xml = tool_dir.load()
        assert xml.find("inputs").find("input").get("name") == "first_input"

    # Test recursive macro applications.
    with TestToolDirectory() as tool_dir:
        tool_dir.write('''
<tool>
    <expand macro="inputs">
        <input name="first_input" />
        <expand macro="second" />
    </expand>
    <macros>
        <macro name="inputs">
            <inputs>
                <yield />
            </inputs>
        </macro>
        <macro name="second">
            <input name="second_input" />
        </macro>
    </macros>
</tool>''')
        xml = tool_dir.load()
        assert xml.find("inputs").findall("input")[1].get("name") == "second_input"

    # Test recursive macro applications.
    with TestToolDirectory() as tool_dir:
        tool_dir.write('''
<tool>
    <expand macro="inputs">
        <input name="first_input" />
        <expand macro="second" />
    </expand>
    <macros>
        <macro name="inputs">
            <inputs>
                <yield />
            </inputs>
        </macro>
        <macro name="second">
            <expand macro="second_delegate" />
        </macro>
        <macro name="second_delegate">
            <input name="second_input" />
        </macro>
    </macros>
</tool>''')
        xml = tool_dir.load()
        assert xml.find("inputs").findall("input")[1].get("name") == "second_input"

    # Test <xml> is shortcut for macro type="xml"
    with TestToolDirectory() as tool_dir:
        tool_dir.write('''
<tool>
    <expand macro="inputs" />
    <macros>
        <xml name="inputs">
            <inputs />
        </xml>
    </macros>
</tool>''')
        xml = tool_dir.load()
        assert xml.find("inputs") is not None

    with TestToolDirectory() as tool_dir:
        tool_dir.write('''
<tool>
    <command interpreter="python">tool_wrapper.py
    #include source=$tool_params
    </command>
    <macros>
        <template name="tool_params">-a 1 -b 2</template>
    </macros>
</tool>
''')
        xml = tool_dir.load()
        params_dict = template_macro_params(xml.getroot())
        assert params_dict['tool_params'] == "-a 1 -b 2"

    with TestToolDirectory() as tool_dir:
        tool_dir.write('''
<tool>
    <macros>
        <token name="@CITATION@">The citation.</token>
    </macros>
    <help>@CITATION@</help>
    <another>
        <tag />
    </another>
</tool>
''')
        xml = tool_dir.load()
        help_el = xml.find("help")
        assert help_el.text == "The citation.", help_el.text

    with TestToolDirectory() as tool_dir:
        tool_dir.write('''
<tool>
    <macros>
        <token name="@TAG_VAL@">The value.</token>
    </macros>
    <another>
        <tag value="@TAG_VAL@" />
    </another>
</tool>
''')
        xml = tool_dir.load()
        tag_el = xml.find("another").find("tag")
        value = tag_el.get('value')
        assert value == "The value.", value
