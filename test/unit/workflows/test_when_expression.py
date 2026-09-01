import yaml

from galaxy.util.resources import resource_string
from galaxy.workflow.when_expression import (
    analyze_input_references,
    expression_references_input,
)


def test_shared_when_expression_spec():
    cases = yaml.safe_load(resource_string("galaxy.workflow", "when_expression_spec.yml"))

    for case in cases:
        expression = case["expression"]
        expected = case["expect"]
        analysis = analyze_input_references(expression)

        if "static_paths" in expected:
            assert analysis.static_paths == expected["static_paths"], case["doc"]
        if "dynamic" in expected:
            assert analysis.has_dynamic_inputs_access is expected["dynamic"], case["doc"]
        if "references_input" in expected:
            assert expression_references_input(expression, case["input"]) is expected["references_input"], case["doc"]
