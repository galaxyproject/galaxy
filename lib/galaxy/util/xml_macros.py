import os
from copy import deepcopy
from xml.etree import ElementInclude, ElementTree


REQUIRED_PARAMETER = object()


def load_with_references(path):
    """Load XML documentation from file system and preprocesses XML macros.

    Return the XML representation of the expanded tree and paths to
    referenced files that were imported (macros).
    """
    tree = raw_xml_tree(path)
    root = tree.getroot()

    macro_paths = _import_macros(root, path)

    # Collect tokens
    tokens = _macros_of_type(root, 'token', lambda el: el.text or '')

    # Expand xml macros
    macro_dict = _macros_of_type(root, 'xml', lambda el: XmlMacroDef(el))
    _expand_macros([root], macro_dict, tokens)

    return tree, macro_paths


def load(path):
    tree, _ = load_with_references(path)
    return tree


def template_macro_params(root):
    """
    Look for template macros and populate param_dict (for cheetah)
    with these.
    """
    param_dict = {}
    macro_dict = _macros_of_type(root, 'template', lambda el: el.text)
    for key, value in macro_dict.items():
        param_dict[key] = value
    return param_dict


def raw_xml_tree(path):
    """ Load raw (no macro expansion) tree representation of XML represented
    at the specified path.
    """
    tree = _parse_xml(path)
    return tree


def imported_macro_paths(root):
    macros_el = _macros_el(root)
    return _imported_macro_paths_from_el(macros_el)


def _import_macros(root, path):
    xml_base_dir = os.path.dirname(path)
    macros_el = _macros_el(root)
    if macros_el is not None:
        macro_els, macro_paths = _load_macros(macros_el, xml_base_dir)
        _xml_set_children(macros_el, macro_els)
        return macro_paths


def _macros_el(root):
    return root.find('macros')


def _macros_of_type(root, type, el_func):
    macros_el = root.find('macros')
    macro_dict = {}
    if macros_el is not None:
        macro_els = macros_el.findall('macro')
        filtered_els = [(macro_el.get("name"), el_func(macro_el))
                        for macro_el in macro_els
                        if macro_el.get('type') == type]
        macro_dict = dict(filtered_els)
    return macro_dict


def _expand_tokens(elements, tokens):
    if not tokens or not elements:
        return

    for element in elements:
        _expand_tokens_for_el(element, tokens)


def _expand_tokens_for_el(element, tokens):
    value = element.text
    if value:
        new_value = _expand_tokens_str(element.text, tokens)
        if not (new_value is value):
            element.text = new_value
    for key, value in element.attrib.items():
        new_value = _expand_tokens_str(value, tokens)
        if not (new_value is value):
            element.attrib[key] = new_value
    _expand_tokens(list(element), tokens)


def _expand_tokens_str(str, tokens):
    for key, value in tokens.items():
        if str.find(key) > -1:
            str = str.replace(key, value)
    return str


def _expand_macros(elements, macros, tokens):
    if not macros and not tokens:
        return

    for element in elements:
        while True:
            expand_el = element.find('.//expand')
            if expand_el is None:
                break
            _expand_macro(element, expand_el, macros, tokens)

        _expand_tokens_for_el(element, tokens)


def _expand_macro(element, expand_el, macros, tokens):
    macro_name = expand_el.get('macro')
    macro_def = macros[macro_name]
    expanded_elements = deepcopy(macro_def.elements)

    _expand_yield_statements(expanded_elements, expand_el)

    # Recursively expand contained macros.
    _expand_macros(expanded_elements, macros, tokens)
    macro_tokens = macro_def.macro_tokens(expand_el)
    if macro_tokens:
        _expand_tokens(expanded_elements, macro_tokens)

    # HACK for elementtree, newer implementations (etree/lxml) won't
    # require this parent_map data structure but elementtree does not
    # track parents or recongnize .find('..').
    # TODO fix this now that we're not using elementtree
    parent_map = dict((c, p) for p in element.iter() for c in p)
    _xml_replace(expand_el, expanded_elements, parent_map)


def _expand_yield_statements(macro_def, expand_el):
    yield_els = [yield_el for macro_def_el in macro_def for yield_el in macro_def_el.findall('.//yield')]

    expand_el_children = list(expand_el)
    macro_def_parent_map = \
        dict((c, p) for macro_def_el in macro_def for p in macro_def_el.iter() for c in p)

    for yield_el in yield_els:
        _xml_replace(yield_el, expand_el_children, macro_def_parent_map)

    # Replace yields at the top level of a macro, seems hacky approach
    replace_yield = True
    while replace_yield:
        for i, macro_def_el in enumerate(macro_def):
            if macro_def_el.tag == "yield":
                for target in expand_el_children:
                    i += 1
                    macro_def.insert(i, deepcopy(target))
                macro_def.remove(macro_def_el)
                continue

        replace_yield = False


def _load_macros(macros_el, xml_base_dir):
    macros = []
    # Import macros from external files.
    imported_macros, macro_paths = _load_imported_macros(macros_el, xml_base_dir)
    macros.extend(imported_macros)
    # Load all directly defined macros.
    macros.extend(_load_embedded_macros(macros_el, xml_base_dir))
    return macros, macro_paths


def _load_embedded_macros(macros_el, xml_base_dir):
    macros = []

    macro_els = []
    # attribute typed macro
    if macros_el is not None:
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
        if macros_el is not None:
            macro_els = macros_el.findall(tag)
        for macro_el in macro_els:
            macro_el.attrib['type'] = tag
            macro_el.tag = 'macro'
            macros.append(macro_el)

    return macros


def _load_imported_macros(macros_el, xml_base_dir):
    macros = []
    macro_paths = []

    for tool_relative_import_path in _imported_macro_paths_from_el(macros_el):
        import_path = \
            os.path.join(xml_base_dir, tool_relative_import_path)
        macro_paths.append(import_path)
        file_macros, current_macro_paths = _load_macro_file(import_path, xml_base_dir)
        macros.extend(file_macros)
        macro_paths.extend(current_macro_paths)

    return macros, macro_paths


def _imported_macro_paths_from_el(macros_el):
    imported_macro_paths = []
    macro_import_els = []
    if macros_el is not None:
        macro_import_els = macros_el.findall("import")
    for macro_import_el in macro_import_els:
        raw_import_path = macro_import_el.text
        imported_macro_paths.append(raw_import_path)
    return imported_macro_paths


def _load_macro_file(path, xml_base_dir):
    tree = _parse_xml(path)
    root = tree.getroot()
    return _load_macros(root, xml_base_dir)


def _xml_set_children(element, new_children):
    for old_child in element:
        element.remove(old_child)
    for i, new_child in enumerate(new_children):
        element.insert(i, new_child)


def _xml_replace(query, targets, parent_map):
    # parent_el = query.find('..') ## Something like this would be better with newer xml library
    parent_el = parent_map[query]
    matching_index = -1
    # for index, el in enumerate(parent_el.iter('.')):  ## Something like this for newer implementation
    for index, el in enumerate(list(parent_el)):
        if el == query:
            matching_index = index
            break
    assert matching_index >= 0
    current_index = matching_index
    for target in targets:
        current_index += 1
        parent_el.insert(current_index, deepcopy(target))
    parent_el.remove(query)


class XmlMacroDef(object):

    def __init__(self, el):
        self.elements = list(el)
        parameters = {}
        tokens = []
        token_quote = "@"
        for key, value in el.attrib.items():
            if key == "token_quote":
                token_quote = value
            if key == "tokens":
                for token in value.split(","):
                    tokens.append((token, REQUIRED_PARAMETER))
            elif key.startswith("token_"):
                token = key[len("token_"):]
                tokens.append((token, value))
        for name, default in tokens:
            parameters[name] = (token_quote, default)
        self.parameters = parameters

    def macro_tokens(self, expand_el):
        tokens = {}
        for key, (wrap_char, default_val) in self.parameters.items():
            token_value = expand_el.attrib.get(key, default_val)
            if token_value is REQUIRED_PARAMETER:
                message = "Failed to expand macro - missing required parameter [%s]."
                raise ValueError(message % key)
            token_name = "%s%s%s" % (wrap_char, key.upper(), wrap_char)
            tokens[token_name] = token_value
        return tokens


def _parse_xml(fname):
    tree = ElementTree.parse(fname)
    root = tree.getroot()
    ElementInclude.include(root)
    return tree


__all__ = (
    "imported_macro_paths",
    "load",
    "load_with_references",
    "raw_xml_tree",
    "template_macro_params",
)
