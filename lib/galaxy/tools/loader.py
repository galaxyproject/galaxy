from __future__ import with_statement

from copy import deepcopy
import os

from galaxy.util import parse_xml


def load_tool(path):
    """
    Loads tool from file system and preprocesses tool macros.
    """
    tree = parse_xml(path)
    root = tree.getroot()

    _import_macros(root, path)

    # Expand xml macros
    macro_dict = _macros_of_type(root, 'xml', lambda el: list(el.getchildren()))
    _expand_macros([root], macro_dict)

    # Expand tokens
    macro_dict = _macros_of_type(root, 'token', lambda el: el.text)
    _expand_tokens([root], macro_dict)

    return tree


def template_macro_params(root):
    """
    Look for template macros and populate param_dict (for cheetah)
    with these.
    """
    param_dict = {}
    macro_dict = _macros_of_type(root, 'template', lambda el: el.text)
    for key, value in macro_dict.iteritems():
        param_dict[key] = value
    return param_dict


def _import_macros(root, path):
    tool_dir = os.path.dirname(path)
    macros_el = root.find('macros')
    if macros_el:
        macro_els = _load_macros(macros_el, tool_dir)
        _xml_set_children(macros_el, macro_els)


def _macros_of_type(root, type, el_func):
    macros_el = root.find('macros')
    macro_dict = {}
    if macros_el:
        macro_els = macros_el.findall('macro')
        macro_dict = dict([(macro_el.get("name"), el_func(macro_el)) \
            for macro_el in macro_els \
            if macro_el.get('type') == type])
    return macro_dict


def _expand_tokens(elements, tokens):
    if not tokens or not elements:
        return

    for element in elements:
        value = element.text
        if value:
            new_value = _expand_tokens_str(element.text, tokens)
            if not (new_value is value):
                element.text = new_value
        for key, value in element.attrib.iteritems():
            new_value = _expand_tokens_str(value, tokens)
            if not (new_value is value):
                element.attrib[key] = new_value
        _expand_tokens(list(element.getchildren()), tokens)


def _expand_tokens_str(str, tokens):
    for key, value in tokens.iteritems():
        if str.find(key) > -1:
            str = str.replace(key, value)
    return str


def _expand_macros(elements, macros):
    if not macros:
        return

    for element in elements:
        # HACK for elementtree, newer implementations (etree/lxml) won't
        # require this parent_map data structure but elementtree does not
        # track parents or recongnize .find('..').
        parent_map = dict((c, p) for p in element.getiterator() for c in p)
        for expand_el in element.findall('.//expand'):
            macro_name = expand_el.get('macro')
            macro_def = deepcopy(macros[macro_name])  # deepcopy needed?

            yield_els = [yield_el for macro_def_el in macro_def for yield_el in macro_def_el.findall('.//yield')]

            expand_el_children = expand_el.getchildren()
            macro_def_parent_map = \
                dict((c, p) for macro_def_el in macro_def for p in macro_def_el.getiterator() for c in p)

            for yield_el in yield_els:
                _xml_replace(yield_el, expand_el_children, macro_def_parent_map)

            # Recursively expand contained macros.
            _expand_macros(macro_def, macros)
            _xml_replace(expand_el, macro_def, parent_map)


def _load_macros(macros_el, tool_dir):
    macros = []
    # Import macros from external files.
    macros.extend(_load_imported_macros(macros_el, tool_dir))
    # Load all directly defined macros.
    macros.extend(_load_embedded_macros(macros_el, tool_dir))
    return macros


def _load_embedded_macros(macros_el, tool_dir):
    macros = []

    macro_els = []
    # attribute typed macro
    if macros_el:
        macro_els = macros_el.findall("macro")
    for macro in macro_els:
        if 'type' not in macro.attrib:
            macro.attrib['type'] = 'xml'
        macros.append(macro)

    # type shortcuts (<xml> is a shortcut for <macro type="xml",
    # likewise for <template>.
    typed_tag = ['template', 'xml', 'token']
    for tag in typed_tag:
        macro_els = []
        if macros_el:
            macro_els = macros_el.findall(tag)
        for macro_el in macro_els:
            macro_el.attrib['type'] = tag
            macro_el.tag = 'macro'
            macros.append(macro_el)

    return macros


def _load_imported_macros(macros_el, tool_dir):
    macros = []

    macro_import_els = []
    if macros_el:
        macro_import_els = macros_el.findall("import")
    for macro_import_el in macro_import_els:
        raw_import_path = macro_import_el.text
        tool_relative_import_path = \
            os.path.basename(raw_import_path)  # Sanitize this
        import_path = \
            os.path.join(tool_dir, tool_relative_import_path)
        file_macros = _load_macro_file(import_path, tool_dir)
        macros.extend(file_macros)

    return macros


def _load_macro_file(path, tool_dir):
    tree = parse_xml(path)
    root = tree.getroot()
    return _load_macros(root, tool_dir)


def _xml_set_children(element, new_children):
    for old_child in element.getchildren():
        element.remove(old_child)
    for i, new_child in enumerate(new_children):
        element.insert(i, new_child)


def _xml_replace(query, targets, parent_map):
    #parent_el = query.find('..') ## Something like this would be better with newer xml library
    parent_el = parent_map[query]
    matching_index = -1
    #for index, el in enumerate(parent_el.iter('.')):  ## Something like this for newer implementation
    for index, el in enumerate(parent_el.getchildren()):
        if el == query:
            matching_index = index
            break
    assert matching_index >= 0
    current_index = matching_index
    for target in targets:
        current_index += 1
        parent_el.insert(current_index, deepcopy(target))
    parent_el.remove(query)


def test_loader():
    """
    Function to test this module. Galaxy doesn't seem to have a
    place to put unit tests that are not doctests. These tests can
    be run with nosetests via the following command:

        % nosetests lib/galaxy/tools/loader.py

    """
    from tempfile import mkdtemp
    from shutil import rmtree

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
