"""Run rule_target_column_specification.yml defined tests using pytest."""

import yaml

from galaxy.model.dataset_collections.rule_target_columns import column_title_to_target_type
from galaxy.util.resources import resource_string


def test_column_to_target_mapping():
    rule_target_tests_str = resource_string("galaxy.model.dataset_collections", "rule_target_column_specification.yml")
    rule_target_tests = yaml.safe_load(rule_target_tests_str)
    for rule_target_test in rule_target_tests:
        # - doc: "NAME (all uppercase) maps directly to the name target type"
        #   column_header: "NAME"
        #   maps_to: "name"
        doc = rule_target_test.get("doc", "")
        column_header = rule_target_test["column_header"]
        maps_to = rule_target_test["maps_to"]
        assert (
            column_title_to_target_type(column_header) == maps_to
        ), f"Failed for column header '{column_header}' with doc '{doc}'"
