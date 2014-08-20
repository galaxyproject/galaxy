from __future__ import with_statement

from copy import deepcopy
import os

from galaxy.util import parse_xml


def load_tool(path):
    """
    Loads tool from file system and preprocesses tool macros.
    """
    tree = raw_tool_xml_tree(path)
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


def raw_tool_xml_tree(path):
    """ Load raw (no macro expansion) tree representation of tool represented
    at the specified path.
    """
    tree = parse_xml(path)
    return tree


def imported_macro_paths(root):
    macros_el = _macros_el(root)
    return _imported_macro_paths_from_el(macros_el)


def _import_macros(root, path):
    tool_dir = os.path.dirname(path)
    macros_el = _macros_el(root)
    if macros_el:
        macro_els = _load_macros(macros_el, tool_dir)
        _xml_set_children(macros_el, macro_els)


def _macros_el(root):
    return root.find('macros')


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
        while True:
            expand_el = element.find('.//expand')
            if expand_el is None:
                break
            _expand_macro(element, expand_el, macros)


def _expand_macro(element, expand_el, macros):
    macro_name = expand_el.get('macro')
    macro_def = deepcopy(macros[macro_name])

    _expand_yield_statements(macro_def, expand_el)

    # Recursively expand contained macros.
    _expand_macros(macro_def, macros)

    # HACK for elementtree, newer implementations (etree/lxml) won't
    # require this parent_map data structure but elementtree does not
    # track parents or recongnize .find('..').
    parent_map = dict((c, p) for p in element.getiterator() for c in p)
    _xml_replace(expand_el, macro_def, parent_map)


def _expand_yield_statements(macro_def, expand_el):
    yield_els = [yield_el for macro_def_el in macro_def for yield_el in macro_def_el.findall('.//yield')]

    expand_el_children = expand_el.getchildren()
    macro_def_parent_map = \
        dict((c, p) for macro_def_el in macro_def for p in macro_def_el.getiterator() for c in p)

    for yield_el in yield_els:
        _xml_replace(yield_el, expand_el_children, macro_def_parent_map)


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

    for tool_relative_import_path in _imported_macro_paths_from_el(macros_el):
        import_path = \
            os.path.join(tool_dir, tool_relative_import_path)
        file_macros = _load_macro_file(import_path, tool_dir)
        macros.extend(file_macros)

    return macros


def _imported_macro_paths_from_el(macros_el):
    imported_macro_paths = []
    macro_import_els = []
    if macros_el:
        macro_import_els = macros_el.findall("import")
    for macro_import_el in macro_import_els:
        raw_import_path = macro_import_el.text
        tool_relative_import_path = \
            os.path.basename(raw_import_path)  # Sanitize this
        imported_macro_paths.append( tool_relative_import_path )
    return imported_macro_paths


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
