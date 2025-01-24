import abc
import itertools
import re
from typing import (
    List,
    Type,
)

import yaml

from galaxy.util.resources import resource_string


def get_rules_specification():
    return yaml.safe_load(resource_string(__name__, "rules_dsl_spec.yml"))


def _ensure_rule_contains_keys(rule, keys):
    for key, instance_class in keys.items():
        if key not in rule:
            raise ValueError(f"Rule of type [{rule['type']}] does not contain key [{key}].")
        value = rule[key]
        if not isinstance(value, instance_class):
            raise ValueError(f"Rule of type [{rule['type']}] does not contain correct value type for key [{key}].")


def _ensure_key_value_in(rule, key, values):
    value = rule[key]
    if value not in values:
        raise ValueError(f"Invalid value [{value}] for [{key}] encountered.")


def _ensure_valid_pattern(expression):
    re.compile(expression)


def apply_regex(regex, target, data, replacement=None, group_count=None):
    pattern = re.compile(regex)

    def new_row(row):
        source = row[target]
        if replacement is None:
            match = pattern.search(source)
            if not match:
                raise Exception(f"Problem applying regular expression [{regex}] to [{source}].")

            if group_count:
                if len(match.groups()) != group_count:
                    raise Exception("Problem applying regular expression, wrong number of groups found.")

                result = row + list(match.groups())
            else:
                result = row + [match.group(0)]
        else:
            result = row + [pattern.search(source).expand(replacement)]

        return result

    new_data = list(map(new_row, data))
    return new_data


class BaseRuleDefinition(metaclass=abc.ABCMeta):
    @property
    @abc.abstractmethod
    def rule_type(self):
        """Short string describing type of rule (plugin class) to use."""

    @abc.abstractmethod
    def validate_rule(self, rule):
        """Validate dictified rule definition of this type."""

    @abc.abstractmethod
    def apply(self, rule, data, sources):
        """Apply validated, dictified rule definition to supplied data."""


class AddColumnMetadataRuleDefinition(BaseRuleDefinition):
    rule_type = "add_column_metadata"

    def validate_rule(self, rule):
        _ensure_rule_contains_keys(rule, {"value": str})

    def apply(self, rule, data, sources):
        rule_value = rule["value"]
        if rule_value.startswith("identifier"):
            identifier_index = int(rule_value[len("identifier") :])

            new_rows = []
            for index, row in enumerate(data):
                new_rows.append(row + [sources[index]["identifiers"][identifier_index]])

        elif rule_value == "tags":

            def sorted_tags(index):
                tags = sorted(sources[index]["tags"])
                return [",".join(tags)]

            new_rows = []
            for index, row in enumerate(data):
                new_rows.append(row + sorted_tags(index))

        return new_rows, sources


class AddColumnGroupTagValueRuleDefinition(BaseRuleDefinition):
    rule_type = "add_column_group_tag_value"

    def validate_rule(self, rule):
        _ensure_rule_contains_keys(rule, {"value": str})

    def apply(self, rule, data, sources):
        rule_value = rule["value"]
        tag_prefix = f"group:{rule_value}:"

        new_rows = []
        for index, row in enumerate(data):
            group_tag_value = None
            source = sources[index]
            tags = source["tags"]
            for tag in sorted(tags):
                if tag.startswith(tag_prefix):
                    group_tag_value = tag[len(tag_prefix) :]
                    break

            if group_tag_value is None:
                group_tag_value = rule.get("default_value", "")

            new_rows.append(row + [group_tag_value])

        return new_rows, sources


class AddColumnConcatenateRuleDefinition(BaseRuleDefinition):
    rule_type = "add_column_concatenate"

    def validate_rule(self, rule):
        _ensure_rule_contains_keys(rule, {"target_column_0": int, "target_column_1": int})

    def apply(self, rule, data, sources):
        column_0 = rule["target_column_0"]
        column_1 = rule["target_column_1"]

        new_rows = []
        for row in data:
            new_rows.append(row + [row[column_0] + row[column_1]])

        return new_rows, sources


class AddColumnBasenameRuleDefinition(BaseRuleDefinition):
    rule_type = "add_column_basename"

    def validate_rule(self, rule):
        _ensure_rule_contains_keys(rule, {"target_column": int})

    def apply(self, rule, data, sources):
        column = rule["target_column"]
        re = r"[^/]*$"
        return apply_regex(re, column, data), sources


class AddColumnRegexRuleDefinition(BaseRuleDefinition):
    rule_type = "add_column_regex"

    def validate_rule(self, rule):
        _ensure_rule_contains_keys(rule, {"target_column": int, "expression": str})
        _ensure_valid_pattern(rule["expression"])

    def apply(self, rule, data, sources):
        target = rule["target_column"]
        expression = rule["expression"]
        replacement = rule.get("replacement")
        group_count = rule.get("group_count")

        return apply_regex(expression, target, data, replacement, group_count), sources


class AddColumnRownumRuleDefinition(BaseRuleDefinition):
    rule_type = "add_column_rownum"

    def validate_rule(self, rule):
        _ensure_rule_contains_keys(rule, {"start": int})

    def apply(self, rule, data, sources):
        start = rule["start"]

        new_rows = []
        for index, row in enumerate(data):
            new_rows.append(row + [f"{index + start}"])

        return new_rows, sources


class AddColumnValueRuleDefinition(BaseRuleDefinition):
    rule_type = "add_column_value"

    def validate_rule(self, rule):
        _ensure_rule_contains_keys(rule, {"value": str})

    def apply(self, rule, data, sources):
        value = rule["value"]

        new_rows = []
        for row in data:
            new_rows.append(row + [str(value)])

        return new_rows, sources


class AddColumnSubstrRuleDefinition(BaseRuleDefinition):
    rule_type = "add_column_substr"

    def validate_rule(self, rule):
        _ensure_rule_contains_keys(
            rule,
            {
                "target_column": int,
                "length": int,
                "substr_type": str,
            },
        )
        _ensure_key_value_in(rule, "substr_type", ["keep_prefix", "drop_prefix", "keep_suffix", "drop_suffix"])

    def apply(self, rule, data, sources):
        target = rule["target_column"]
        length = rule["length"]
        substr_type = rule["substr_type"]

        def new_row(row):
            original_value = row[target]
            start = 0
            end = len(original_value)

            if substr_type == "keep_prefix":
                end = length
            elif substr_type == "drop_prefix":
                start = length
            elif substr_type == "keep_suffix":
                start = end - length
                if start < 0:
                    start = 0
            else:
                end = end - length
                if end < 0:
                    end = 0

            return row + [original_value[start:end]]

        return list(map(new_row, data)), sources


class RemoveColumnsRuleDefinition(BaseRuleDefinition):
    rule_type = "remove_columns"

    def validate_rule(self, rule):
        _ensure_rule_contains_keys(
            rule,
            {
                "target_columns": list,
            },
        )

    def apply(self, rule, data, sources):
        target_columns = rule["target_columns"]

        def new_row(row):
            new = []
            for index, val in enumerate(row):
                if index not in target_columns:
                    new.append(val)
            return new

        return list(map(new_row, data)), sources


def _filter_index(func, iterable):
    result = []
    for index, x in enumerate(iterable):
        if func(index):
            result.append(x)

    return result


class AddFilterRegexRuleDefinition(BaseRuleDefinition):
    rule_type = "add_filter_regex"

    def validate_rule(self, rule):
        _ensure_rule_contains_keys(
            rule,
            {
                "target_column": int,
                "invert": bool,
                "expression": str,
            },
        )
        _ensure_valid_pattern(rule["expression"])

    def apply(self, rule, data, sources):
        target_column = rule["target_column"]
        invert = rule["invert"]
        regex = rule["expression"]

        def _filter(index):
            row = data[index]
            val = row[target_column]
            pattern = re.compile(regex)
            return not invert if pattern.search(val) else invert

        return _filter_index(_filter, data), _filter_index(_filter, sources)


class AddFilterCountRuleDefinition(BaseRuleDefinition):
    rule_type = "add_filter_count"

    def validate_rule(self, rule):
        _ensure_rule_contains_keys(
            rule,
            {
                "count": int,
                "invert": bool,
                "which": str,
            },
        )
        _ensure_key_value_in(rule, "which", ["first", "last"])

    def apply(self, rule, data, sources):
        num_rows = len(data)
        invert = rule["invert"]
        n = rule["count"]
        which = rule["which"]

        def _filter(index):
            if which == "first":
                matches = index >= n
            else:
                matches = index < (num_rows - n)
            return not invert if matches else invert

        return _filter_index(_filter, data), _filter_index(_filter, sources)


class AddFilterEmptyRuleDefinition(BaseRuleDefinition):
    rule_type = "add_filter_empty"

    def validate_rule(self, rule):
        _ensure_rule_contains_keys(rule, {"target_column": int, "invert": bool})

    def apply(self, rule, data, sources):
        invert = rule["invert"]
        target_column = rule["target_column"]

        def _filter(index):
            non_empty = len(data[index][target_column]) != 0
            return not invert if non_empty else invert

        return _filter_index(_filter, data), _filter_index(_filter, sources)


class AddFilterMatchesRuleDefinition(BaseRuleDefinition):
    rule_type = "add_filter_matches"

    def validate_rule(self, rule):
        _ensure_rule_contains_keys(
            rule,
            {
                "target_column": int,
                "invert": bool,
                "value": str,
            },
        )

    def apply(self, rule, data, sources):
        invert = rule["invert"]
        target_column = rule["target_column"]
        value = rule["value"]

        def _filter(index):
            row = data[index]
            val = row[target_column]
            return not invert if val == value else invert

        return _filter_index(_filter, data), _filter_index(_filter, sources)


class AddFilterCompareRuleDefinition(BaseRuleDefinition):
    rule_type = "add_filter_compare"

    def validate_rule(self, rule):
        _ensure_rule_contains_keys(
            rule,
            {
                "target_column": int,
                "value": int,
                "compare_type": str,
            },
        )
        _ensure_key_value_in(
            rule, "compare_type", ["less_than", "less_than_equal", "greater_than", "greater_than_equal"]
        )

    def apply(self, rule, data, sources):
        target_column = rule["target_column"]
        value = rule["value"]
        compare_type = rule["compare_type"]

        def _filter(index):
            row = data[index]
            target_value = float(row[target_column])
            if compare_type == "less_than":
                matches = target_value < value
            elif compare_type == "less_than_equal":
                matches = target_value <= value
            elif compare_type == "greater_than":
                matches = target_value > value
            elif compare_type == "greater_than_equal":
                matches = target_value >= value

            return matches

        return _filter_index(_filter, data), _filter_index(_filter, sources)


class SortRuleDefinition(BaseRuleDefinition):
    rule_type = "sort"

    def validate_rule(self, rule):
        _ensure_rule_contains_keys(
            rule,
            {
                "target_column": int,
                "numeric": bool,
            },
        )

    def apply(self, rule, data, sources):
        target = rule["target_column"]
        numeric = rule["numeric"]

        sortable = zip(data, sources)

        def sort_func(item):
            a_val = item[0][target]
            if numeric:
                a_val = float(a_val)
            return a_val

        sorted_data = sorted(sortable, key=sort_func)

        new_data = []
        new_sources = []

        for row, source in sorted_data:
            new_data.append(row)
            new_sources.append(source)

        return new_data, new_sources


class SwapColumnsRuleDefinition(BaseRuleDefinition):
    rule_type = "swap_columns"

    def validate_rule(self, rule):
        _ensure_rule_contains_keys(
            rule,
            {
                "target_column_0": int,
                "target_column_1": int,
            },
        )

    def apply(self, rule, data, sources):
        target_column_0 = rule["target_column_0"]
        target_column_1 = rule["target_column_1"]

        def new_row(row):
            row_copy = row[:]
            row_copy[target_column_0] = row[target_column_1]
            row_copy[target_column_1] = row[target_column_0]
            return row_copy

        return list(map(new_row, data)), sources


class SplitColumnsRuleDefinition(BaseRuleDefinition):
    rule_type = "split_columns"

    def validate_rule(self, rule):
        _ensure_rule_contains_keys(
            rule,
            {
                "target_columns_0": list,
                "target_columns_1": list,
            },
        )

    def apply(self, rule, data, sources):
        target_columns_0 = rule["target_columns_0"]
        target_columns_1 = rule["target_columns_1"]

        def split_row(row):
            new_row_0 = []
            new_row_1 = []
            for index, el in enumerate(row):
                if index in target_columns_0:
                    new_row_0.append(el)
                elif index in target_columns_1:
                    new_row_1.append(el)
                else:
                    new_row_0.append(el)
                    new_row_1.append(el)

            return [new_row_0, new_row_1]

        data = flat_map(split_row, data)
        sources = flat_map(lambda x: [x, x], sources)

        return data, sources


def flat_map(f, items):
    return list(itertools.chain.from_iterable(map(f, items)))


class RuleSet:
    def __init__(self, rule_set_as_dict):
        self.raw_rules = rule_set_as_dict["rules"]
        self.raw_mapping = rule_set_as_dict.get("mapping", [])

    @property
    def rules(self):
        return self.raw_rules

    def _rules_with_definitions(self):
        for rule in self.raw_rules:
            yield (rule, RULES_DEFINITIONS[rule["type"]])

    def apply(self, data, sources):
        for rule, rule_definition in self._rules_with_definitions():
            rule_definition.validate_rule(rule)
            data, sources = rule_definition.apply(rule, data, sources)

        return data, sources

    @property
    def has_errors(self):
        errored = False
        try:
            for rule, rule_definition in self._rules_with_definitions():
                rule_definition.validate_rule(rule)
        except Exception:
            errored = True
        return errored

    @property
    def mapping_as_dict(self):
        as_dict = {}
        for mapping in self.raw_mapping:
            as_dict[mapping["type"]] = mapping

        return as_dict

    # Rest of this is generic, things here are Galaxy collection specific, think about about
    # subclass of RuleSet for collection creation.
    @property
    def identifier_columns(self):
        mapping_as_dict = self.mapping_as_dict
        identifier_columns = []
        if "list_identifiers" in mapping_as_dict:
            identifier_columns.extend(mapping_as_dict["list_identifiers"]["columns"])
        if "paired_identifier" in mapping_as_dict:
            identifier_columns.append(mapping_as_dict["paired_identifier"]["columns"][0])

        return identifier_columns

    @property
    def collection_type(self):
        mapping_as_dict = self.mapping_as_dict
        list_columns = mapping_as_dict.get("list_identifiers", {"columns": []})["columns"]
        collection_type = ":".join("list" for c in list_columns)
        if "paired_identifier" in mapping_as_dict:
            if collection_type:
                collection_type += ":paired"
            else:
                collection_type = "paired"
        return collection_type

    @property
    def display(self):
        message = "Rules:\n"
        message += "".join(f"- {r}\n" for r in self.raw_rules)
        message += "Column Definitions:\n"
        message += "".join(f"- {m}\n" for m in self.raw_mapping)
        return message


RULES_DEFINITION_CLASSES: List[Type[BaseRuleDefinition]] = [
    AddColumnMetadataRuleDefinition,
    AddColumnGroupTagValueRuleDefinition,
    AddColumnConcatenateRuleDefinition,
    AddColumnBasenameRuleDefinition,
    AddColumnRegexRuleDefinition,
    AddColumnRownumRuleDefinition,
    AddColumnValueRuleDefinition,
    AddColumnSubstrRuleDefinition,
    RemoveColumnsRuleDefinition,
    AddFilterRegexRuleDefinition,
    AddFilterCountRuleDefinition,
    AddFilterEmptyRuleDefinition,
    AddFilterMatchesRuleDefinition,
    AddFilterCompareRuleDefinition,
    SortRuleDefinition,
    SwapColumnsRuleDefinition,
    SplitColumnsRuleDefinition,
]
RULES_DEFINITIONS = {}
for rule_class in RULES_DEFINITION_CLASSES:
    RULES_DEFINITIONS[rule_class.rule_type] = rule_class()
