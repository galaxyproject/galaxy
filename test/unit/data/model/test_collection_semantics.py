import pytest
import yaml
from pydantic import ValidationError

from galaxy.model.dataset_collections.types.semantics import (
    CollectionDefinition,
    DatasetsDeclaration,
    DocEntry,
    Example,
    ExampleEntry,
    ExampleTests,
    ToolDefinition,
    ToolRuntimeApi,
    ToolRuntimeFramework,
    YAMLRootModel,
    arg_parser,
    check,
    collect_docs_with_examples,
    elements_to_latex,
    expression_to_latex,
    validate_api_test_refs,
    validate_tool_refs,
    validate_workflow_editor_refs,
)
from galaxy.util.resources import resource_string



def _load_root_model() -> YAMLRootModel:
    raw = yaml.safe_load(
        resource_string("galaxy.model.dataset_collections.types", "collection_semantics.yml")
    )
    return YAMLRootModel.model_validate(raw)


def test_yaml_loads_and_parses():
    root = _load_root_model()
    assert len(root.root) > 0



def test_all_entries_are_doc_or_example():
    root = _load_root_model()
    for entry in root.root:
        assert isinstance(entry, (DocEntry, ExampleEntry))


def test_has_both_doc_and_example_entries():
    root = _load_root_model()
    has_doc = any(isinstance(e, DocEntry) for e in root.root)
    has_example = any(isinstance(e, ExampleEntry) for e in root.root)
    assert has_doc
    assert has_example



@pytest.mark.parametrize(
    "input_expr, expected_substr",
    [
        ("->", "\\rightarrow"),
        ("~>", "\\mapsto"),
        ("list", "\\text{list}"),
        ("forward", "\\text{forward}"),
        ("reverse", "\\text{reverse}"),
        ("mapOver", "\\text{mapOver}"),
        ("collection", "\\text{collection}"),
        ("dataset", "\\text{dataset}"),
    ],
)
def test_expression_to_latex_replacements(input_expr, expected_substr):
    result = expression_to_latex(input_expr)
    assert expected_substr in result


def test_expression_to_latex_paired_or_unpaired_atomic():
    result = expression_to_latex("paired_or_unpaired")
    assert "\\text{paired\\_or\\_unpaired}" in result
    # should NOT contain bare \text{paired} or \text{unpaired} separately
    without_pou = result.replace("\\text{paired\\_or\\_unpaired}", "")
    assert "\\text{paired}" not in without_pou
    assert "\\text{unpaired}" not in without_pou


def test_expression_to_latex_wrap_true():
    result = expression_to_latex("x", wrap=True)
    assert result.startswith("$ ")
    assert result.endswith(" $")


def test_expression_to_latex_wrap_false():
    result = expression_to_latex("x", wrap=False)
    assert not result.startswith("$ ")



def test_elements_to_latex_single_none():
    result = elements_to_latex({"a": None})
    assert "a" in result
    assert "\\left\\{" in result
    assert "\\right\\}" in result


def test_elements_to_latex_nested_dict():
    result = elements_to_latex({"outer": {"inner": None}})
    assert "\\text{ outer }" in result
    assert "inner" in result


def test_elements_to_latex_multiple_keys():
    result = elements_to_latex({"a": None, "b": None})
    assert "a" in result
    assert "b" in result
    assert "," in result



def test_datasets_declaration_as_latex_single():
    d = DatasetsDeclaration(datasets=["x"])
    assert d.as_latex() == "$ x $"


def test_datasets_declaration_as_latex_multiple():
    d = DatasetsDeclaration(datasets=["x", "y"])
    result = d.as_latex()
    assert "$ x $" in result
    assert "$ y $" in result


def test_tool_definition_as_latex():
    t = ToolDefinition(**{"in": {"i": "dataset"}, "out": {"o": "dataset"}})
    result = t.as_latex()
    assert "\\Rightarrow" in result
    assert "i:" in result
    assert "o:" in result


def test_collection_definition_as_latex():
    c = CollectionDefinition(collection_type="paired", elements={"forward": None, "reverse": None})
    result = c.as_latex()
    assert "paired" in result
    assert "forward" in result
    assert "reverse" in result



def _make_root(entries: list) -> YAMLRootModel:
    return YAMLRootModel.model_validate(entries)


def test_collect_doc_with_no_examples():
    root = _make_root([{"doc": "Some doc text"}])
    result = collect_docs_with_examples(root)
    assert len(result) == 1
    doc, examples = result[0]
    assert doc.doc == "Some doc text"
    assert examples == []


def test_collect_doc_with_examples():
    root = _make_root([
        {"doc": "Doc"},
        {"example": {"label": "EX1", "then": "a -> b"}},
    ])
    result = collect_docs_with_examples(root)
    assert len(result) == 1
    _, examples = result[0]
    assert len(examples) == 1
    assert examples[0].example.label == "EX1"


def test_collect_example_without_then_excluded():
    root = _make_root([
        {"doc": "Doc"},
        {"example": {"label": "NO_THEN"}},
        {"example": {"label": "HAS_THEN", "then": "x -> y"}},
    ])
    result = collect_docs_with_examples(root)
    _, examples = result[0]
    assert len(examples) == 1
    assert examples[0].example.label == "HAS_THEN"


def test_collect_multiple_doc_sections():
    root = _make_root([
        {"doc": "Doc1"},
        {"example": {"label": "EX1", "then": "a"}},
        {"doc": "Doc2"},
        {"example": {"label": "EX2", "then": "b"}},
    ])
    result = collect_docs_with_examples(root)
    assert len(result) == 2
    assert result[0][0].doc == "Doc1"
    assert result[1][0].doc == "Doc2"
    assert len(result[0][1]) == 1
    assert len(result[1][1]) == 1



def test_arg_parser_default():
    args = arg_parser().parse_args([])
    assert args.check is False


def test_arg_parser_check_flag():
    args = arg_parser().parse_args(["--check"])
    assert args.check is True


def test_arg_parser_check_short_flag():
    args = arg_parser().parse_args(["-c"])
    assert args.check is True



def test_example_tests_rejects_unknown_keys():
    with pytest.raises(ValidationError):
        ExampleTests(**{"wf_editor": "some value"})


def test_example_tests_accepts_valid_keys():
    et = ExampleTests(workflow_editor="some test description")
    assert et.workflow_editor == "some test description"



def _extract_examples(root: YAMLRootModel) -> list[Example]:
    return [e.example for e in root.root if isinstance(e, ExampleEntry)]


def test_validate_api_test_refs_clean():
    """Current YAML should have no api_test reference errors."""
    root = _load_root_model()
    examples = _extract_examples(root)
    errors = validate_api_test_refs(examples)
    assert errors == []


def test_validate_api_test_refs_bad_file():
    """Mutated api_test ref with nonexistent file should be caught."""
    ex = Example(
        label="BAD_FILE",
        tests=ExampleTests(
            tool_runtime=ToolRuntimeApi(api_test="nonexistent_file.py::some_func")
        ),
    )
    errors = validate_api_test_refs([ex])
    assert len(errors) == 1
    assert "nonexistent_file.py" in errors[0]


def test_validate_api_test_refs_bad_function():
    """Mutated api_test ref with real file but nonexistent function should be caught."""
    ex = Example(
        label="BAD_FUNC",
        tests=ExampleTests(
            tool_runtime=ToolRuntimeApi(api_test="test_tool_execute.py::nonexistent_function")
        ),
    )
    errors = validate_api_test_refs([ex])
    assert len(errors) == 1
    assert "nonexistent_function" in errors[0]


def test_validate_api_test_refs_bad_method():
    """Mutated api_test ref with real class but nonexistent method should be caught."""
    ex = Example(
        label="BAD_METHOD",
        tests=ExampleTests(
            tool_runtime=ToolRuntimeApi(api_test="test_tools.py::TestToolsApi::nonexistent_method")
        ),
    )
    errors = validate_api_test_refs([ex])
    assert len(errors) == 1
    assert "nonexistent_method" in errors[0]



def test_validate_tool_refs_clean():
    """Current YAML should have no framework tool reference errors."""
    root = _load_root_model()
    examples = _extract_examples(root)
    errors = validate_tool_refs(examples)
    assert errors == []


def test_validate_tool_refs_bad_tool():
    """Nonexistent tool XML should be caught."""
    ex = Example(
        label="BAD_TOOL",
        tests=ExampleTests(
            tool_runtime=ToolRuntimeFramework(tool="nonexistent_tool_xyz")
        ),
    )
    errors = validate_tool_refs([ex])
    assert len(errors) == 1
    assert "nonexistent_tool_xyz" in errors[0]



def test_validate_workflow_editor_refs_clean():
    """Current YAML should have no workflow_editor reference errors."""
    root = _load_root_model()
    examples = _extract_examples(root)
    errors = validate_workflow_editor_refs(examples)
    assert errors == []


def test_validate_workflow_editor_refs_bad_ref():
    """Nonexistent workflow_editor description should be caught."""
    ex = Example(
        label="BAD_WF",
        tests=ExampleTests(workflow_editor="totally nonexistent test description xyz"),
    )
    errors = validate_workflow_editor_refs([ex])
    assert len(errors) == 1
    assert "totally nonexistent test description xyz" in errors[0]



def test_all_tested_examples_have_then():
    """Every example with test references should also have a then expression."""
    root = _load_root_model()
    missing = []
    for entry in root.root:
        if isinstance(entry, ExampleEntry):
            ex = entry.example
            if ex.tests and not ex.then:
                missing.append(ex.label)
    assert missing == [], f"Examples with tests but no then: {missing}"


def test_check_returns_no_errors():
    """check() against current YAML should return empty error list."""
    errors = check()
    assert errors == []
