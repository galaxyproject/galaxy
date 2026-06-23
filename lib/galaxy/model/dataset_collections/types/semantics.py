#!/usr/bin/env python

# how to use this function...
# PYTHONPATH=lib python lib/galaxy/model/dataset_collections/types/semantics.py
import argparse
import ast
import os
import re
import sys
from io import StringIO
from typing import (
    Annotated,
    Any,
    Literal,
    NamedTuple,
    Optional,
    Union,
)

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    RootModel,
)

from galaxy.util import galaxy_directory
from galaxy.util.resources import resource_string

DESCRIPTION = """This script parses the collection_semantics.yml file and creates Markdown documentation from it.
"""


class DocEntry(BaseModel):
    doc: str


class ToolRuntimeApi(BaseModel):
    api_test: str


class ToolRuntimeFramework(BaseModel):
    tool: str


ToolRuntimeTest = Union[ToolRuntimeApi, ToolRuntimeFramework]


class WorkflowRuntimeTest(BaseModel):
    api_test: Optional[str] = None
    framework_test: Optional[str] = None


class ExampleTests(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_runtime: Optional[ToolRuntimeTest] = None
    workflow_runtime: Optional[WorkflowRuntimeTest] = None
    workflow_editor: Optional[str] = None


class DatasetsDeclaration(BaseModel):
    datasets: list[str]

    def as_latex(self) -> str:
        return ", ".join([f"$ {d} $" for d in self.datasets])


class ToolDefinition(BaseModel):
    inputs: dict[str, str] = Field(alias="in")
    outputs: dict[str, str] = Field(alias="out")

    def as_latex(self) -> str:
        inputs = ", ".join([f"{k}: \\text{{ {_escape_underscores(v)} }}" for (k, v) in self.inputs.items()])
        outputs = ", ".join([f"{k}: \\text{{ {_escape_underscores(v)} }}" for (k, v) in self.outputs.items()])
        return f"tool \\text{{ is }} ({inputs}) \\Rightarrow \\{{ {outputs} \\}}"


class ToolDeclaration(BaseModel):
    tool: ToolDefinition

    def as_latex(self) -> str:
        return self.tool.as_latex()


def _assumption_elements_to_latex(elements: dict[str, Any]):
    elements_as_strings = []
    for identifier, value in elements.items():
        if value is None:
            elements_as_strings.append(identifier)
        else:
            if isinstance(value, dict):
                value_str = _assumption_elements_to_latex(value)
            else:
                value_str = str(value)
            elements_as_strings.append(f"\\text{{ {identifier} }}={value_str}")
    unwrapped_elements = ", ".join(elements_as_strings)
    return f"\\left\\{{ {unwrapped_elements} \\right\\}}"


class CollectionDefinition(NamedTuple):
    collection_type: str
    elements: dict[str, Any]

    def as_latex(self) -> str:
        ct = _latex_collection_type(self.collection_type)
        return f"\\text{{CollectionInstance<}}{ct},{_assumption_elements_to_latex(self.elements)}\\text{{>}}"


class CollectionDeclarations(BaseModel):
    collections: dict[str, CollectionDefinition]


Expression = Union[str, DatasetsDeclaration, ToolDeclaration, CollectionDeclarations]


# --- Structured Then Expression Models ---


def _escape_underscores(text: str) -> str:
    return text.replace("_", "\\_")


def _latex_type_word(word: str) -> str:
    if "_" in word:
        escaped = word.replace("_", "\\_")
        return "\\text{" + escaped + "}"
    return "\\text{" + word + "}"


def _latex_collection_type(ct: str) -> str:
    return ":".join(_latex_type_word(p) for p in ct.split(":"))


def _output_elements_to_latex(elements: dict) -> str:
    parts = []
    for key, value in elements.items():
        if key == "...":
            parts.append("...")
        else:
            parts.append(f"\\text{{{key}}}={value.as_latex()}")
    # Join without spaces around ellipsis entries
    result = ""
    for i, part in enumerate(parts):
        if i > 0:
            if part == "..." or parts[i - 1] == "...":
                result += ","
            else:
                result += ", "
        result += part
    return "\\left\\{" + result + "\\right\\}"


def _produces_to_latex(produces: dict) -> str:
    parts = []
    for key, value in produces.items():
        parts.append(f"{key}: {value.as_latex()}")
    return "\\left\\{" + ", ".join(parts) + "\\right\\}"


class DatasetInput(BaseModel):
    type: Literal["dataset"]
    ref: str

    def as_latex(self) -> str:
        return self.ref


class MapOverInput(BaseModel):
    type: Literal["map_over"]
    collection: str
    sub_collection_type: Optional[str] = None

    def as_latex(self) -> str:
        if self.sub_collection_type:
            sct = _latex_collection_type(self.sub_collection_type)
            return f"\\text{{mapOver}}({self.collection}, '{sct}')"
        return f"\\text{{mapOver}}({self.collection})"


class CollectionInput(BaseModel):
    type: Literal["collection"]
    ref: str

    def as_latex(self) -> str:
        return self.ref


class DatasetListInput(BaseModel):
    type: Literal["dataset_list"]
    refs: list[str]

    def as_latex(self) -> str:
        return "[" + ",".join(self.refs) + "]"


InputBinding = Annotated[
    Union[DatasetInput, MapOverInput, CollectionInput, DatasetListInput], Field(discriminator="type")
]


class ToolInvocation(BaseModel):
    inputs: dict[str, InputBinding]

    def as_latex(self) -> str:
        args = ", ".join(f"{k}={v.as_latex()}" for k, v in self.inputs.items())
        return f"tool({args})"


class DatasetOutput(BaseModel):
    type: Literal["dataset"]

    def as_latex(self) -> str:
        return "\\text{dataset}"


class EllipsisMarker(BaseModel):
    type: Literal["ellipsis"]

    def as_latex(self) -> str:
        return "..."


class ToolOutputRef(BaseModel):
    type: Literal["tool_output_ref"]
    invocation: ToolInvocation
    output: str

    def as_latex(self) -> str:
        return f"{self.invocation.as_latex()}[{self.output}]"


class NestedElements(BaseModel):
    type: Literal["nested_elements"]
    elements: dict[str, "OutputBinding"]

    def as_latex(self) -> str:
        return _output_elements_to_latex(self.elements)


OutputBinding = Annotated[
    Union[DatasetOutput, EllipsisMarker, ToolOutputRef, NestedElements], Field(discriminator="type")
]
NestedElements.model_rebuild()


class CollectionOutput(BaseModel):
    type: Literal["collection"]
    collection_type: str
    elements: dict[str, OutputBinding]

    def as_latex(self) -> str:
        ct = _latex_collection_type(self.collection_type)
        el = _output_elements_to_latex(self.elements)
        return f"\\text{{collection}}<{ct},{el}>"


OutputSpec = Annotated[Union[DatasetOutput, CollectionOutput], Field(discriminator="type")]


class MapOverThen(BaseModel):
    type: Literal["map_over"]
    invocation: ToolInvocation
    produces: dict[str, OutputSpec]

    def as_latex(self) -> str:
        return f"{self.invocation.as_latex()} \\mapsto {_produces_to_latex(self.produces)}"


class ReductionThen(BaseModel):
    type: Literal["reduction"]
    invocation: ToolInvocation
    produces: dict[str, OutputSpec]

    def as_latex(self) -> str:
        return f"{self.invocation.as_latex()} \\rightarrow {_produces_to_latex(self.produces)}"


class EquivalenceThen(BaseModel):
    type: Literal["equivalence"]
    left: ToolInvocation
    right: ToolInvocation

    def as_latex(self) -> str:
        return f"{self.left.as_latex()} == {self.right.as_latex()}"


class InvalidThen(BaseModel):
    type: Literal["invalid"]
    invocation: ToolInvocation

    def as_latex(self) -> str:
        return self.invocation.as_latex()


ThenExpression = Annotated[Union[MapOverThen, ReductionThen, EquivalenceThen, InvalidThen], Field(discriminator="type")]


class Example(BaseModel):
    label: str
    assumptions: Optional[list[Expression]] = None
    then: Optional[ThenExpression] = None
    is_valid: bool = True
    tests: Optional[ExampleTests] = None


class ExampleEntry(BaseModel):
    example: Example


YAMLRootModel = RootModel[list[Union[DocEntry, ExampleEntry]]]


WORDS_TO_TEXTIFY = ["list", "forward", "reverse", "mapOver", "collection", "dataset", "inner"]
_POU_PLACEHOLDER = "\x00POU\x00"
_UNPAIRED_PLACEHOLDER = "\x00UNPAIRED\x00"
_SINGLE_DATASETS_PLACEHOLDER = "\x00SINGLEDATASETS\x00"
_SAMPLE_SHEET_PLACEHOLDER = "\x00SAMPLESHEET\x00"


def expression_to_latex(expression: str, wrap: bool = True):
    expression = expression.replace("->", "\\rightarrow")
    expression = expression.replace("~>", "\\mapsto")
    expression = expression.replace("{", "\\left\\{")
    expression = expression.replace("}", "\\right\\}")
    # Replace multi-word identifiers with placeholders before WORDS_TO_TEXTIFY
    # to prevent double-replacement (e.g. "dataset" inside "single_datasets")
    expression = expression.replace("single_datasets", _SINGLE_DATASETS_PLACEHOLDER)
    expression = expression.replace("sample_sheet", _SAMPLE_SHEET_PLACEHOLDER)
    expression = expression.replace("paired_or_unpaired", _POU_PLACEHOLDER)
    expression = expression.replace("unpaired", _UNPAIRED_PLACEHOLDER)
    expression = expression.replace("paired", "\\text{paired}")
    expression = expression.replace(_UNPAIRED_PLACEHOLDER, "\\text{unpaired}")
    expression = expression.replace(_POU_PLACEHOLDER, "\\text{paired\\_or\\_unpaired}")
    for word in WORDS_TO_TEXTIFY:
        expression = expression.replace(word, "\\text{" + word + "}")
    expression = expression.replace(_SINGLE_DATASETS_PLACEHOLDER, "\\text{single\\_datasets}")
    expression = expression.replace(_SAMPLE_SHEET_PLACEHOLDER, "\\text{sample\\_sheet}")
    if wrap:
        return f"$ {expression} $"
    else:
        return f"{expression}"


def collect_docs_with_examples(root: YAMLRootModel) -> list[tuple[DocEntry, list[ExampleEntry]]]:
    docs_with_examples = []

    current_doc: Optional[DocEntry] = None
    current_examples: list[ExampleEntry] = []
    for entry in root.root:
        if isinstance(entry, DocEntry):
            if current_doc:
                docs_with_examples.append((current_doc, current_examples))
            current_examples = []
            current_doc = entry
        if isinstance(entry, ExampleEntry):
            if entry.example.then:
                current_examples.append(entry)

    if current_doc:
        docs_with_examples.append((current_doc, current_examples))
    return docs_with_examples


def main(argv=None) -> None:
    if argv is None:
        argv = sys.argv[1:]

    args = arg_parser().parse_args(argv)
    if args.check:
        check()

    generate_docs()


def _load_examples() -> list["Example"]:
    semantics_yaml = yaml.safe_load(
        resource_string("galaxy.model.dataset_collections.types", "collection_semantics.yml")
    )
    root = YAMLRootModel.model_validate(semantics_yaml)
    return [e.example for e in root.root if isinstance(e, ExampleEntry)]


def check() -> list[str]:
    examples = _load_examples()
    errors: list[str] = []
    errors.extend(validate_api_test_refs(examples))
    errors.extend(validate_tool_refs(examples))
    errors.extend(validate_workflow_editor_refs(examples))
    return errors


def _validate_api_test_ref(label: str, ref: str, api_test_dir: str) -> Optional[str]:
    parts = ref.split("::")
    filename = parts[0]
    filepath = os.path.join(api_test_dir, filename)
    if not os.path.exists(filepath):
        return f"[{label}] api_test file not found: {filename}"
    with open(filepath) as f:
        tree = ast.parse(f.read(), filename=filepath)
    if len(parts) == 2:
        func_name = parts[1]
        found = any(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func_name
            for node in ast.walk(tree)
        )
        if not found:
            return f"[{label}] api_test function not found: {ref}"
    elif len(parts) == 3:
        class_name, method_name = parts[1], parts[2]
        found = False
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                found = any(
                    isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name == method_name
                    for child in node.body
                )
                break
        if not found:
            return f"[{label}] api_test method not found: {ref}"
    return None


def _validate_framework_test_ref(label: str, ref: str, workflow_dir: str) -> Optional[str]:
    """Validate a framework test ref like 'collection_semantics_cat_0'."""
    parts = ref.rsplit("_", 1)
    if len(parts) != 2 or not parts[1].isdigit():
        return f"[{label}] framework_test must be 'workflow_name_index': {ref}"
    workflow_name = parts[0]
    workflow_file = os.path.join(workflow_dir, f"{workflow_name}.gxwf.yml")
    if not os.path.exists(workflow_file):
        return f"[{label}] framework_test workflow not found: {workflow_name}.gxwf.yml"
    test_file = os.path.join(workflow_dir, f"{workflow_name}.gxwf-tests.yml")
    if not os.path.exists(test_file):
        return f"[{label}] framework_test test file not found: {workflow_name}.gxwf-tests.yml"
    return None


def validate_api_test_refs(examples: list["Example"]) -> list[str]:
    errors: list[str] = []
    api_test_dir = os.path.join(galaxy_directory(), "lib", "galaxy_test", "api")
    workflow_dir = os.path.join(galaxy_directory(), "lib", "galaxy_test", "workflow")
    for ex in examples:
        if ex.tests and ex.tests.tool_runtime and isinstance(ex.tests.tool_runtime, ToolRuntimeApi):
            error = _validate_api_test_ref(ex.label, ex.tests.tool_runtime.api_test, api_test_dir)
            if error:
                errors.append(error)
        if ex.tests and ex.tests.workflow_runtime:
            if ex.tests.workflow_runtime.api_test:
                error = _validate_api_test_ref(ex.label, ex.tests.workflow_runtime.api_test, api_test_dir)
                if error:
                    errors.append(error)
            if ex.tests.workflow_runtime.framework_test:
                error = _validate_framework_test_ref(ex.label, ex.tests.workflow_runtime.framework_test, workflow_dir)
                if error:
                    errors.append(error)
    return errors


def validate_tool_refs(examples: list["Example"]) -> list[str]:
    errors: list[str] = []
    tools_dir = os.path.join(galaxy_directory(), "test", "functional", "tools")
    for ex in examples:
        if not ex.tests or not ex.tests.tool_runtime:
            continue
        if not isinstance(ex.tests.tool_runtime, ToolRuntimeFramework):
            continue
        tool_id = ex.tests.tool_runtime.tool
        tool_path = os.path.join(tools_dir, f"{tool_id}.xml")
        if not os.path.exists(tool_path):
            errors.append(f"[{ex.label}] framework tool XML not found: {tool_id}.xml")
    return errors


def validate_workflow_editor_refs(examples: list["Example"]) -> list[str]:
    errors: list[str] = []
    test_file = os.path.join(
        galaxy_directory(),
        "client",
        "src",
        "components",
        "Workflow",
        "Editor",
        "modules",
        "terminals.test.ts",
    )
    if not os.path.exists(test_file):
        return [f"workflow editor test file not found: {test_file}"]
    with open(test_file) as f:
        content = f.read()
    it_descriptions = set(re.findall(r'it\(["\'](.+?)["\']\s*,', content))
    for ex in examples:
        if not ex.tests or not ex.tests.workflow_editor:
            continue
        desc = ex.tests.workflow_editor
        if desc not in it_descriptions:
            errors.append(f'[{ex.label}] workflow_editor test not found: "{desc}"')
    return errors


def generate_docs():
    semantics_yaml = yaml.safe_load(
        resource_string("galaxy.model.dataset_collections.types", "collection_semantics.yml")
    )

    # Parse the YAML and extract doc elements
    root_model = YAMLRootModel.model_validate(semantics_yaml)

    docs_with_examples = collect_docs_with_examples(root_model)
    markdown_content = StringIO()
    for doc_with_examples in docs_with_examples:
        doc_entry, examples = doc_with_examples
        markdown_content.write(doc_entry.doc)
        if len(examples):
            markdown_content.write("\n\n")
            for example_entry in examples:
                markdown_content.write(f"({example_entry.example.label})=\n")
            markdown_content.write("<details><summary>Examples</summary>")
            for example_entry in examples:

                example = example_entry.example
                markdown_content.write("\n\n")
                markdown_content.write(f":::{{admonition}} Example: `{example.label}` \n")
                markdown_content.write(":class: note\n\n")
                if example.assumptions:
                    markdown_content.write("Assuming,")
                    markdown_content.write("\n\n")
                    for assumption in example.assumptions:
                        if isinstance(assumption, DatasetsDeclaration):
                            markdown_content.write(f"* {assumption.as_latex()}")
                            if len(assumption.datasets) == 1 and "..." not in assumption.datasets[0]:
                                markdown_content.write(" is a dataset\n")
                            else:
                                markdown_content.write(" are datasets\n")
                        elif isinstance(assumption, ToolDeclaration):
                            markdown_content.write(f"* $ {assumption.as_latex()} $\n")
                        elif isinstance(assumption, CollectionDeclarations):
                            for name, collection in assumption.collections.items():
                                markdown_content.write(f"* $ {name} $ is $ {collection.as_latex()} $\n")
                        else:
                            markdown_content.write(f"* {expression_to_latex(assumption)}\n")
                if example.then:
                    validity_str = ""
                    if not example.is_valid:
                        validity_str = "\\text{ is invalid}"
                    then_latex = example.then.as_latex()
                    markdown_content.write(f"\n\nthen\n\n$${then_latex}{validity_str}$$\n\n")
                markdown_content.write(":::\n\n")
            markdown_content.write("\n\n</details><br>\n\n")
        markdown_content.write("\n\n")

    # Extract and concatenate doc elements
    with open(os.path.join(galaxy_directory(), "doc/source/dev/collection_semantics.md"), "w") as f:
        f.write(markdown_content.getvalue())


def arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument("-c", "--check", action="store_true", default=False)
    return parser


if __name__ == "__main__":
    main()
