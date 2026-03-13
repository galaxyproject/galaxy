import pytest
import yaml
from pydantic import ValidationError

from galaxy.model.dataset_collections.types.semantics import (
    _assumption_elements_to_latex,
    arg_parser,
    check,
    collect_docs_with_examples,
    CollectionDefinition,
    CollectionInput,
    CollectionOutput,
    DatasetInput,
    DatasetListInput,
    DatasetOutput,
    DatasetsDeclaration,
    DocEntry,
    EllipsisMarker,
    EquivalenceThen,
    Example,
    ExampleEntry,
    ExampleTests,
    expression_to_latex,
    generate_docs,
    InvalidThen,
    MapOverInput,
    MapOverThen,
    NestedElements,
    ReductionThen,
    ToolDefinition,
    ToolInvocation,
    ToolOutputRef,
    ToolRuntimeApi,
    ToolRuntimeFramework,
    validate_api_test_refs,
    validate_tool_refs,
    validate_workflow_editor_refs,
    YAMLRootModel,
)
from galaxy.util.resources import resource_string


def _load_root_model() -> YAMLRootModel:
    raw = yaml.safe_load(resource_string("galaxy.model.dataset_collections.types", "collection_semantics.yml"))
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


def test_assumption_elements_to_latex_single_none():
    result = _assumption_elements_to_latex({"a": None})
    assert "a" in result
    assert "\\left\\{" in result
    assert "\\right\\}" in result


def test_assumption_elements_to_latex_nested_dict():
    result = _assumption_elements_to_latex({"outer": {"inner": None}})
    assert "\\text{ outer }" in result
    assert "inner" in result


def test_assumption_elements_to_latex_multiple_keys():
    result = _assumption_elements_to_latex({"a": None, "b": None})
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


_SIMPLE_THEN = {"type": "invalid", "invocation": {"inputs": {"i": {"type": "collection", "ref": "C"}}}}


def test_collect_doc_with_examples():
    root = _make_root(
        [
            {"doc": "Doc"},
            {"example": {"label": "EX1", "then": _SIMPLE_THEN}},
        ]
    )
    result = collect_docs_with_examples(root)
    assert len(result) == 1
    _, examples = result[0]
    assert len(examples) == 1
    assert examples[0].example.label == "EX1"


def test_collect_example_without_then_excluded():
    root = _make_root(
        [
            {"doc": "Doc"},
            {"example": {"label": "NO_THEN"}},
            {"example": {"label": "HAS_THEN", "then": _SIMPLE_THEN}},
        ]
    )
    result = collect_docs_with_examples(root)
    _, examples = result[0]
    assert len(examples) == 1
    assert examples[0].example.label == "HAS_THEN"


def test_collect_multiple_doc_sections():
    root = _make_root(
        [
            {"doc": "Doc1"},
            {"example": {"label": "EX1", "then": _SIMPLE_THEN}},
            {"doc": "Doc2"},
            {"example": {"label": "EX2", "then": _SIMPLE_THEN}},
        ]
    )
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
        tests=ExampleTests(tool_runtime=ToolRuntimeApi(api_test="nonexistent_file.py::some_func")),
    )
    errors = validate_api_test_refs([ex])
    assert len(errors) == 1
    assert "nonexistent_file.py" in errors[0]


def test_validate_api_test_refs_bad_function():
    """Mutated api_test ref with real file but nonexistent function should be caught."""
    ex = Example(
        label="BAD_FUNC",
        tests=ExampleTests(tool_runtime=ToolRuntimeApi(api_test="test_tool_execute.py::nonexistent_function")),
    )
    errors = validate_api_test_refs([ex])
    assert len(errors) == 1
    assert "nonexistent_function" in errors[0]


def test_validate_api_test_refs_bad_method():
    """Mutated api_test ref with real class but nonexistent method should be caught."""
    ex = Example(
        label="BAD_METHOD",
        tests=ExampleTests(tool_runtime=ToolRuntimeApi(api_test="test_tools.py::TestToolsApi::nonexistent_method")),
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
        tests=ExampleTests(tool_runtime=ToolRuntimeFramework(tool="nonexistent_tool_xyz")),
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


# --- Structured Then Expression Model Tests ---


def test_invalid_then_collection_input():
    """InvalidThen with collection input: tool(i=C)"""
    then = InvalidThen(
        type="invalid",
        invocation=ToolInvocation(inputs={"i": CollectionInput(type="collection", ref="C")}),
    )
    assert then.as_latex() == expression_to_latex("tool(i=C)", wrap=False)


def test_invalid_then_map_over_with_sub_collection():
    """InvalidThen with mapOver sub-collection: tool(i=mapOver(C, 'paired'))"""
    then = InvalidThen(
        type="invalid",
        invocation=ToolInvocation(
            inputs={"i": MapOverInput(type="map_over", collection="C", sub_collection_type="paired")}
        ),
    )
    assert then.as_latex() == expression_to_latex("tool(i=mapOver(C, 'paired'))", wrap=False)


def test_invalid_then_map_over_paired_or_unpaired():
    """InvalidThen with mapOver paired_or_unpaired sub-collection."""
    then = InvalidThen(
        type="invalid",
        invocation=ToolInvocation(
            inputs={"i": MapOverInput(type="map_over", collection="C", sub_collection_type="paired_or_unpaired")}
        ),
    )
    assert then.as_latex() == expression_to_latex("tool(i=mapOver(C, 'paired_or_unpaired'))", wrap=False)


def test_invalid_then_map_over_no_sub_collection():
    """InvalidThen with bare mapOver: tool(i=mapOver(C))"""
    then = InvalidThen(
        type="invalid",
        invocation=ToolInvocation(inputs={"i": MapOverInput(type="map_over", collection="C")}),
    )
    assert then.as_latex() == expression_to_latex("tool(i=mapOver(C))", wrap=False)


def test_reduction_then():
    """ReductionThen: tool(i=C) -> {o: dataset}"""
    then = ReductionThen(
        type="reduction",
        invocation=ToolInvocation(inputs={"i": CollectionInput(type="collection", ref="C")}),
        produces={"o": DatasetOutput(type="dataset")},
    )
    assert then.as_latex() == expression_to_latex("tool(i=C) -> {o: dataset}", wrap=False)


def test_equivalence_then_list_reduction():
    """EquivalenceThen: tool(i=C) == tool(i=[d_1,...,d_n])"""
    then = EquivalenceThen(
        type="equivalence",
        left=ToolInvocation(inputs={"i": CollectionInput(type="collection", ref="C")}),
        right=ToolInvocation(inputs={"i": DatasetListInput(type="dataset_list", refs=["d_1", "...", "d_n"])}),
    )
    assert then.as_latex() == expression_to_latex("tool(i=C) == tool(i=[d_1,...,d_n])", wrap=False)


def test_equivalence_then_collection_refs():
    """EquivalenceThen: tool(i=C) == tool(i=C_AS_MIXED)"""
    then = EquivalenceThen(
        type="equivalence",
        left=ToolInvocation(inputs={"i": CollectionInput(type="collection", ref="C")}),
        right=ToolInvocation(inputs={"i": CollectionInput(type="collection", ref="C_AS_MIXED")}),
    )
    assert then.as_latex() == expression_to_latex("tool(i=C) == tool(i=C_AS_MIXED)", wrap=False)


def test_map_over_then_paired():
    """MapOverThen for BASIC_MAPPING_PAIRED pattern."""
    then = MapOverThen(
        type="map_over",
        invocation=ToolInvocation(inputs={"i": MapOverInput(type="map_over", collection="C")}),
        produces={
            "o": CollectionOutput(
                type="collection",
                collection_type="paired",
                elements={
                    "forward": ToolOutputRef(
                        type="tool_output_ref",
                        invocation=ToolInvocation(inputs={"i": DatasetInput(type="dataset", ref="d_f")}),
                        output="o",
                    ),
                    "reverse": ToolOutputRef(
                        type="tool_output_ref",
                        invocation=ToolInvocation(inputs={"i": DatasetInput(type="dataset", ref="d_r")}),
                        output="o",
                    ),
                },
            )
        },
    )
    result = then.as_latex()
    assert "\\text{mapOver}(C)" in result
    assert "\\text{paired}" in result
    assert "\\mapsto" in result
    assert "tool(i=d_f)[o]" in result
    assert "tool(i=d_r)[o]" in result


def test_map_over_then_sub_collection():
    """MapOverThen for sub-collection mapping (MAPPING_LIST_PAIRED_OVER_PAIRED)."""
    then = MapOverThen(
        type="map_over",
        invocation=ToolInvocation(
            inputs={"i": MapOverInput(type="map_over", collection="C", sub_collection_type="paired")}
        ),
        produces={
            "o": CollectionOutput(
                type="collection",
                collection_type="list",
                elements={
                    "el1": ToolOutputRef(
                        type="tool_output_ref",
                        invocation=ToolInvocation(inputs={"i": CollectionInput(type="collection", ref="C\\_PAIRED")}),
                        output="o",
                    ),
                },
            )
        },
    )
    result = then.as_latex()
    assert "\\text{mapOver}(C, '\\text{paired}')" in result
    assert "\\text{list}" in result
    assert "C\\_PAIRED" in result


def test_pydantic_parse_invalid_then_yaml():
    """Structured InvalidThen parses from dict (simulating YAML load)."""
    data = {
        "type": "invalid",
        "invocation": {"inputs": {"i": {"type": "collection", "ref": "C"}}},
    }
    then = InvalidThen.model_validate(data)
    assert isinstance(then.invocation.inputs["i"], CollectionInput)
    assert then.invocation.inputs["i"].ref == "C"


def test_pydantic_parse_reduction_then_yaml():
    """Structured ReductionThen parses from dict."""
    data = {
        "type": "reduction",
        "invocation": {"inputs": {"i": {"type": "collection", "ref": "C"}}},
        "produces": {"o": {"type": "dataset"}},
    }
    then = ReductionThen.model_validate(data)
    assert isinstance(then.produces["o"], DatasetOutput)


def test_example_accepts_structured_then():
    """Example model accepts structured then expression."""
    data = {
        "label": "TEST",
        "then": {
            "type": "invalid",
            "invocation": {"inputs": {"i": {"type": "collection", "ref": "C"}}},
        },
        "is_valid": False,
    }
    ex = Example.model_validate(data)
    assert isinstance(ex.then, InvalidThen)
    assert ex.is_valid is False


def test_example_rejects_string_then():
    """Example model no longer accepts string then after migration."""
    with pytest.raises(ValidationError):
        Example(label="TEST", then="tool(i=C) -> {o: dataset}")


# --- Smoke Tests (Steps 3-4) ---


def test_all_then_as_latex_succeeds():
    """Every then expression produces valid LaTeX without error."""
    root = _load_root_model()
    for entry in root.root:
        if isinstance(entry, ExampleEntry) and entry.example.then:
            latex = entry.example.then.as_latex()
            assert isinstance(latex, str)
            assert len(latex) > 0, f"{entry.example.label} produced empty LaTeX"


def test_generate_docs_succeeds():
    """generate_docs() runs to completion without errors."""
    generate_docs()


# --- Unit Tests for Uncovered Models (Step 5) ---


def test_ellipsis_marker_as_latex():
    m = EllipsisMarker(type="ellipsis")
    assert m.as_latex() == "..."


def test_dataset_list_input_as_latex():
    d = DatasetListInput(type="dataset_list", refs=["d_1", "...", "d_n"])
    assert d.as_latex() == "[d_1,...,d_n]"


def test_nested_elements_as_latex():
    ne = NestedElements.model_validate(
        {
            "type": "nested_elements",
            "elements": {
                "forward": {
                    "type": "tool_output_ref",
                    "invocation": {"inputs": {"i": {"type": "dataset", "ref": "d_f"}}},
                    "output": "o",
                },
                "reverse": {
                    "type": "tool_output_ref",
                    "invocation": {"inputs": {"i": {"type": "dataset", "ref": "d_r"}}},
                    "output": "o",
                },
            },
        }
    )
    result = ne.as_latex()
    assert "\\text{forward}=" in result
    assert "\\text{reverse}=" in result
    assert "tool(i=d_f)[o]" in result


def test_collection_output_with_ellipsis_as_latex():
    co = CollectionOutput.model_validate(
        {
            "type": "collection",
            "collection_type": "list",
            "elements": {
                "el1": {
                    "type": "tool_output_ref",
                    "invocation": {"inputs": {"i": {"type": "dataset", "ref": "d_1"}}},
                    "output": "o",
                },
                "...": {"type": "ellipsis"},
                "eln": {
                    "type": "tool_output_ref",
                    "invocation": {"inputs": {"i": {"type": "dataset", "ref": "d_n"}}},
                    "output": "o",
                },
            },
        }
    )
    result = co.as_latex()
    assert "\\text{list}" in result
    assert ",...," in result


def test_map_over_input_compound_sub_collection_type():
    mi = MapOverInput(type="map_over", collection="C", sub_collection_type="list:paired_or_unpaired")
    result = mi.as_latex()
    assert "\\text{list}:\\text{paired\\_or\\_unpaired}" in result


def test_map_over_then_produces_dataset():
    then = MapOverThen(
        type="map_over",
        invocation=ToolInvocation(inputs={"i": MapOverInput(type="map_over", collection="C")}),
        produces={"o": DatasetOutput(type="dataset")},
    )
    result = then.as_latex()
    assert "\\mapsto" in result
    assert "\\text{dataset}" in result
