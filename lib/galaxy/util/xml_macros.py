import os
from copy import deepcopy
from typing import (
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Tuple,
    TYPE_CHECKING,
    TypeVar,
    Union,
)

from galaxy.util import (
    parse_xml,
    unicodify,
)

if TYPE_CHECKING:
    from galaxy.util import (
        Element,
        ElementTree,
    )
    from galaxy.util.path import StrPath

MacrosDictT = Dict[str, List["Element"]]


def load_with_references(path: "StrPath") -> Tuple["ElementTree", Optional[List[str]]]:
    """Load XML documentation from file system and preprocesses XML macros.

    Return the XML representation of the expanded tree and paths to
    referenced files that were imported (macros).
    """
    tree = raw_xml_tree(path)
    root = tree.getroot()

    macros_el = _macros_el(root)
    if macros_el is None:
        return tree, []

    macros: MacrosDictT = {}
    macro_paths = _import_macros(macros_el, path, macros)
    macros_el.clear()

    # Collect tokens
    tokens: Dict[str, str] = {}
    for m in macros.get("token", []):
        token_name = m.get("name")
        assert token_name
        tokens[token_name] = m.text or ""
    tokens = expand_nested_tokens(tokens)

    # Expand xml macros
    macro_dict: Dict[str, XmlMacroDef] = {}
    for m in macros.get("xml", []):
        macro_name = m.get("name")
        assert macro_name
        macro_dict[macro_name] = XmlMacroDef(m)
    _expand_macros([root], macro_dict, tokens)

    # reinsert template macro which are used during tool execution
    for m in macros.get("template", []):
        macros_el.append(m)
    _expand_tokens_for_el(root, tokens)
    return tree, macro_paths


def load(path: "StrPath") -> "ElementTree":
    tree, _ = load_with_references(path)
    return tree


def template_macro_params(root: "Element") -> Dict[str, Union[str, None]]:
    """
    Look for template macros and populate param_dict (for cheetah)
    with these.
    """
    macros_el = _macros_el(root)
    if macros_el is not None:
        return _macros_of_type(macros_el, "template", lambda el: el.text)
    return {}


def raw_xml_tree(path: "StrPath") -> "ElementTree":
    """Load raw (no macro expansion) tree representation of XML represented
    at the specified path.
    """
    tree = parse_xml(path, strip_whitespace=False, remove_comments=True)
    return tree


def imported_macro_paths(root: "Element") -> List[str]:
    macros_el = _macros_el(root)
    if macros_el is None:
        return []
    return _imported_macro_paths_from_el(macros_el)


def _import_macros(macros_el: "Element", path: "StrPath", macros: MacrosDictT) -> Optional[List[str]]:
    """
    root the parsed XML tree
    path the path to the main xml document
    """
    xml_base_dir = os.path.dirname(path)
    macro_paths = _load_macros(macros_el, xml_base_dir, macros)
    # _xml_set_children(macros_el, macro_els)
    return macro_paths


def _macros_el(root: "Element") -> Union["Element", None]:
    return root.find("macros")


T = TypeVar("T")


def _macros_of_type(macros_el: "Element", type: str, el_func: Callable[["Element"], T]) -> Dict[str, T]:
    macro_els = macros_el.findall("macro")
    ret: Dict[str, T] = {}
    for macro_el in macro_els:
        if macro_el.get("type") == type:
            macro_name = macro_el.get("name")
            assert macro_name
            ret[macro_name] = el_func(macro_el)
    return ret


def expand_nested_tokens(tokens: Dict[str, str]) -> Dict[str, str]:
    for token_name in tokens.keys():
        for current_token_name, current_token_value in tokens.items():
            if token_name in current_token_value:
                if token_name == current_token_name:
                    raise Exception(f"Token '{token_name}' cannot contain itself")
                tokens[current_token_name] = current_token_value.replace(token_name, tokens[token_name])
    return tokens


def _expand_tokens(elements: Iterable["Element"], tokens: Dict[str, str]) -> None:
    if not tokens:
        return

    for element in elements:
        _expand_tokens_for_el(element, tokens)


def _expand_tokens_for_el(element: "Element", tokens: Dict[str, str]) -> None:
    """
    expand tokens in element and (recursively) in its children
    replacements of text attributes and attribute values are
    possible
    """
    element_text = element.text
    if element_text:
        new_value = _expand_tokens_str(element_text, tokens)
        if new_value is not element_text:
            element.text = new_value
    for key, value in element.attrib.items():
        new_value = _expand_tokens_str(unicodify(value), tokens)
        if new_value is not value:
            element.attrib[key] = new_value
        new_key = _expand_tokens_str(unicodify(key), tokens)
        if new_key is not key:
            element.attrib[new_key] = element.attrib[key]
            del element.attrib[key]
    # recursively expand in childrens
    _expand_tokens(element.__iter__(), tokens)


def _expand_tokens_str(s: str, tokens: Dict[str, str]) -> str:
    for key, value in tokens.items():
        if key in s:
            s = s.replace(key, value)
    return s


def _expand_macros(
    elements: Iterable["Element"],
    macros: Dict[str, "XmlMacroDef"],
    tokens: Dict[str, str],
    visited: Optional[List[str]] = None,
) -> None:
    if not macros and not tokens:
        return

    if visited is None:
        visited = []

    for element in elements:
        while True:
            expand_el = element.find(".//expand")
            if expand_el is None:
                break
            _expand_macro(expand_el, macros, tokens, visited)


def _expand_macro(
    expand_el: "Element", macros: Dict[str, "XmlMacroDef"], tokens: Dict[str, str], visited: List[str]
) -> None:
    macro_name = expand_el.get("macro")
    assert macro_name is not None, "Attempted to expand macro with no 'macro' attribute defined."
    # check for cycles in the nested macro expansion
    assert (
        macro_name not in visited
    ), f"Cycle in nested macros: already expanded {visited} can't expand '{macro_name}' again"
    visited.append(macro_name)

    assert macro_name in macros, f"No macro named {macro_name} found, known macros are {', '.join(macros.keys())}."
    macro_def = macros[macro_name]
    macro_el = deepcopy(macro_def.element)
    _expand_yield_statements(macro_el, expand_el)

    macro_tokens = macro_def.macro_tokens(expand_el)
    if macro_tokens:
        _expand_tokens(macro_el.__iter__(), macro_tokens)

    # Recursively expand contained macros.
    _expand_macros(macro_el.__iter__(), macros, tokens, visited)
    _xml_replace(expand_el, macro_el.__iter__())
    del visited[-1]


def _expand_yield_statements(macro_el: "Element", expand_el: "Element") -> None:
    """
    Modifies the macro_el element by replacing
    1. all named yield tags by the content of the corresponding token tags
       - token tags need to be direct children of the expand
       - processed in order of definition of the token tags
    2. all unnamed yield tags by the non-token children of the expand tag
    """
    # replace named yields
    for token_el in expand_el.findall("./token"):
        name = token_el.attrib.get("name")
        assert name is not None, "Found unnamed token" + str(token_el.attrib)
        yield_els = list(macro_el.findall(f".//yield[@name='{name}']"))
        assert len(yield_els) > 0, f"No named yield found for named token {name}"
        for yield_el in yield_els:
            _xml_replace(yield_el, token_el.__iter__())

    # replace unnamed yields
    yield_els = list(macro_el.findall(".//yield"))
    expand_el_children = [c for c in expand_el if c.tag != "token"]
    for yield_el in yield_els:
        _xml_replace(yield_el, expand_el_children)


def _load_macros(macros_el: "Element", xml_base_dir: str, macros: MacrosDictT) -> List[str]:
    # Import macros from external files.
    macro_paths = _load_imported_macros(macros_el, xml_base_dir, macros)
    # Load all directly defined macros.
    _load_embedded_macros(macros_el, macros)
    return macro_paths


def _load_embedded_macros(macros_el: "Element", macros: MacrosDictT) -> None:
    # attribute typed macro
    for macro in macros_el.iterfind("macro"):
        if "type" not in macro.attrib:
            macro.attrib["type"] = "xml"
        macro_type = unicodify(macro.attrib["type"])
        try:
            macros[macro_type].append(macro)
        except KeyError:
            macros[macro_type] = [macro]

    # type shortcuts (<xml> is a shortcut for <macro type="xml",
    # likewise for <template>.
    for tag in ["template", "xml", "token"]:
        for macro_el in macros_el.iterfind(tag):
            macro_el.attrib["type"] = tag
            macro_el.tag = "macro"
            try:
                macros[tag].append(macro_el)
            except KeyError:
                macros[tag] = [macro_el]


def _load_imported_macros(macros_el: "Element", xml_base_dir: str, macros: MacrosDictT) -> List[str]:
    macro_paths = []

    for tool_relative_import_path in _imported_macro_paths_from_el(macros_el):
        import_path = os.path.join(xml_base_dir, tool_relative_import_path)
        macro_paths.append(import_path)
        current_macro_paths = _load_macro_file(import_path, xml_base_dir, macros)
        macro_paths.extend(current_macro_paths)
    return macro_paths


def _imported_macro_paths_from_el(macros_el: "Element") -> List[str]:
    imported_macro_paths = []
    for macro_import_el in macros_el.findall("import"):
        raw_import_path = macro_import_el.text
        assert raw_import_path
        imported_macro_paths.append(raw_import_path)
    return imported_macro_paths


def _load_macro_file(path: "StrPath", xml_base_dir: str, macros: MacrosDictT) -> List[str]:
    tree = parse_xml(path, strip_whitespace=False)
    root = tree.getroot()
    return _load_macros(root, xml_base_dir, macros)


def _xml_replace(query: "Element", targets: Iterable["Element"]) -> None:
    parent_el = query.find("..")
    assert parent_el is not None
    matching_index = -1
    # for index, el in enumerate(parent_el.iter('.')):  ## Something like this for newer implementation
    for index, el in enumerate(parent_el):
        if el == query:
            matching_index = index
            break
    assert matching_index >= 0
    current_index = matching_index
    for target in targets:
        current_index += 1
        parent_el.insert(current_index, deepcopy(target))
    parent_el.remove(query)


class XmlMacroDef:
    """
    representation of a (Galaxy) XML macro

    stores the root element of the macro and the parameters.
    each parameter is represented as pair containing
    - the quote character, default '@'
    - parameter name

    Parameter names can be given as comma separated list using the
    `tokens` attribute or as attributes `token_XXX` (where `XXX` is the name).
    The former option should be used to specify required attributes of the
    macro and the latter for optional attributes of the macro (the value of
    `token_XXX is used as default value).

    TODO: `token_quote` forbids `"quote"` as character name of optional
    parameters
    """

    def __init__(self, el: "Element") -> None:
        self.element = el
        tokens: Dict[str, Union[str, None]] = {}
        self.token_quote = "@"
        for key, value in el.attrib.items():
            key = unicodify(key)
            value = unicodify(value)
            if key == "token_quote":
                self.token_quote = value
            if key == "tokens":
                for token in value.split(","):
                    tokens[token] = None  # here None means that the token is a required parameter
            elif key.startswith("token_"):
                token = key[len("token_") :]
                tokens[token] = value
        self.tokens = tokens

    def macro_tokens(self, expand_el: "Element") -> Dict[str, str]:
        """
        get a dictionary mapping token names to values. The names are the
        parameter names surrounded by the quote character. Values are taken
        from the expand_el if absent default values of optional parameters are
        used.
        """
        tokens: Dict[str, str] = {}
        for key, default_val in self.tokens.items():
            token_value = expand_el.attrib.get(key, default_val)
            if token_value is None:
                raise ValueError(f"Failed to expand macro - missing required parameter [{key}].")
            token_name = f"{self.token_quote}{key.upper()}{self.token_quote}"
            tokens[token_name] = token_value
        return tokens


__all__ = (
    "imported_macro_paths",
    "load",
    "load_with_references",
    "raw_xml_tree",
    "template_macro_params",
)
