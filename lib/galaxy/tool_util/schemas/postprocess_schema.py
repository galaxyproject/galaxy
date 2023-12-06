import ast
from collections import defaultdict
from importlib.resources import files

import generated

SCHEMA_PATH = "generated/galaxy.py"

LIST_TO_UNION_LIST_ELEMENT = [
    "TestOutput.assert_contents",
    "TestOutputCollection.element",
    "TestAssertions.has_size",
    "TestAssertions.has_text",
    "TestAssertions.not_has_text",
    "TestAssertions.has_text_matching",
    "TestAssertions.has_line",
    "TestAssertions.has_line_matching",
    "TestAssertions.has_n_lines",
    "TestAssertions.has_n_columns",
    "TestAssertions.is_valid_xml",
    "TestAssertions.xml_element",
    "TestAssertions.has_element_with_path",
    "TestAssertions.has_n_elements_with_path",
    "TestAssertions.element_text_matches",
    "TestAssertions.element_text_is",
    "TestAssertions.attribute_matches",
    "TestAssertions.attribute_is",
    "TestAssertions.element_text",
    "TestAssertions.has_json_property_with_value",
    "TestAssertions.has_json_property_with_text",
    "TestAssertions.has_h5_keys",
    "TestAssertions.has_h5_attribute",
]
ATTRIBUTES_TO_DELETE = [
    "TestOutputCollection.name",
    "TestOutputCollection.type_value",
    "TestOutput.element",
]

MODIFICATION_BY_MODULE: dict[str, dict[str, str]] = defaultdict(dict)
for element in LIST_TO_UNION_LIST_ELEMENT:
    node_name, target_id = element.split(".")
    MODIFICATION_BY_MODULE[node_name][target_id] = "to_union"
for element in ATTRIBUTES_TO_DELETE:
    node_name, target_id = element.split(".")
    MODIFICATION_BY_MODULE[node_name][target_id] = "delete"


def modify_tree(tree: ast.Module):
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for field in node.body:
                if isinstance(field, ast.AnnAssign) and field.value and hasattr(field.value, "keywords"):
                    # Replace the "doc" key in the metadata for each field with "description"
                    for keyword in field.value.keywords:
                        if keyword.arg == "metadata":
                            for key in keyword.value.keys:
                                if key.value == "doc":
                                    # import IPython; IPython.embed(); import sys; sys.exit()
                                    key.value = "description"

            if node.name in MODIFICATION_BY_MODULE:
                target_ids = MODIFICATION_BY_MODULE[node.name]
                new_body = []
                for field in node.body:
                    if (
                        isinstance(field, ast.AnnAssign)
                        and hasattr(field.target, "id")
                        and field.target.id in target_ids
                    ):
                        modification = target_ids[field.target.id]
                        if modification == "to_union" and hasattr(field.annotation, "slice"):
                            original_slice = field.annotation.slice
                            list_type = ast.Subscript(
                                value=ast.Name(id="List", ctx=ast.Load()),
                                slice=original_slice,
                                ctx=ast.Load(),
                            )

                            field.annotation = ast.Subscript(
                                value=ast.Name(id="Union", ctx=ast.Load()),
                                slice=ast.Index(
                                    value=ast.Tuple(
                                        elts=[list_type, original_slice, ast.NameConstant(value=None)], ctx=ast.Load()
                                    )
                                ),
                                ctx=ast.Load(),
                            )
                            if field.value and hasattr(field.value, "keywords"):
                                for keyword in field.value.keywords:
                                    if keyword.arg == "default_factory":
                                        keyword.arg = "default"
                                        keyword.value = ast.NameConstant(value=None)
                        elif modification == "delete":
                            continue
                    new_body.append(field)
                node.body = new_body
    return ast.unparse(tree)


def modify_assert_contents_type_annotation(source_code):
    tree = ast.parse(source_code)
    modified_code = modify_tree(tree)
    return modified_code


if __name__ == "__main__":
    schema_path = files(generated) / "galaxy.py"
    with schema_path.open() as file:
        source_code = file.read()

    modified_code = modify_assert_contents_type_annotation(source_code)

    with schema_path.open("w") as file:
        file.write(f"from typing import Union\n{modified_code}")
