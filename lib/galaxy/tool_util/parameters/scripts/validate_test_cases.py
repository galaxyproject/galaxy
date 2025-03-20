import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import (
    List,
    Optional,
)

from galaxy.tool_util.parameters.case import (
    TestCaseStateValidationResult,
    validate_test_cases_for_tool_source,
)
from galaxy.tool_util.parser import get_tool_source

DESCRIPTION = """
A small utility to load a Galaxy tool file and run tool test validation code on it.

This is not meant to be an end-user application or part of the typical tool developer tool
chain. This functionality will be integrated into Planemo with the typical polish that
entails. This purpose of this utility is for Galaxy developers and people wishing to
make informed decisions about the tool test schema and best practices to apply the tool
state validation code in isolation. This script can also be used to integrate this functionality
in non-Python tool chains.
"""


def arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument("tool_source")
    parser.add_argument(
        "-l",
        "--latest",
        dest="latest",
        default=False,
        action="store_true",
        help="Validate test against latest tool profile version regardless of explicit tool profile version specified in tool source file.",
    )
    parser.add_argument(
        "-j",
        "--json",
        default=False,
        action="store_true",
        help="Output validation results as JSON.",
    )
    return parser


@dataclass
class ToolTestValidationResults:
    tool_id: str
    tool_version: Optional[str]
    tool_profile: str
    tool_path: str
    results: List[TestCaseStateValidationResult]
    load_error: Optional[Exception]

    def to_dict(self):
        return {
            "tool_id": self.tool_id,
            "tool_version": self.tool_version,
            "tool_path": str(self.tool_path),
            "results": [r.to_dict() for r in self.results],
            "load_error": str(self.load_error) if self.load_error else None,
        }


def report_results(results_for_tool: ToolTestValidationResults) -> None:
    test_results = results_for_tool.results
    print(
        f"Found {len(test_results)} test cases to validate for tool {results_for_tool.tool_id} / {results_for_tool.tool_version} (@ {results_for_tool.tool_path})"
    )
    for i, result in enumerate(test_results):
        if result.validation_error is not None:
            print(f"Test Case {i + 1}: validation failed - {str(result.validation_error)}")
        elif len(result.warnings) == 0:
            print(f"Test Case {i + 1}: validated")
        else:
            print(f"Test case {i + 1}: test case validated with warnings:")
            for test_warning in result.warnings:
                print(f"- {test_warning}")


class NotValidToolException(Exception):
    pass


def validate_tool(tool_path, latest) -> ToolTestValidationResults:
    try:
        tool_source = get_tool_source(tool_path)
    except Exception:
        # probably not a Galaxy tool... just skip
        raise NotValidToolException()
    tool_id = tool_source.parse_id()
    if tool_id is None:
        raise NotValidToolException()
    load_error: Optional[Exception] = None
    try:
        results = validate_test_cases_for_tool_source(tool_source, use_latest_profile=latest)
    except Exception as e:
        load_error = e
        results = []
    return ToolTestValidationResults(
        tool_id,
        tool_source.parse_version(),
        tool_source.parse_profile(),
        tool_path,
        results,
        load_error,
    )


def validate_test_cases(args):
    path = args.tool_source
    latest = args.latest
    if not os.path.isdir(path):
        results = validate_tool(path, latest)
        if args.json:
            print(json.dumps(results.to_dict()))
        else:
            report_results(results)
    else:
        xml_files = Path(path).glob("**/*.xml")
        all_results = []
        for xml_file in xml_files:
            if "test-data" in str(xml_file):
                continue
            try:
                results = validate_tool(xml_file, latest)
                all_results.append(results)
            except NotValidToolException:
                continue

        if args.json:
            print(json.dumps([r.to_dict() for r in all_results], indent=4))
        else:
            for results in all_results:
                report_results(results)


def main(argv=None) -> None:
    if argv is None:
        argv = sys.argv[1:]

    args = arg_parser().parse_args(argv)
    validate_test_cases(args)


if __name__ == "__main__":
    main()
