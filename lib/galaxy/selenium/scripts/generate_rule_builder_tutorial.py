#!/usr/bin/env python
"""Script to generate a tutorial for the Galaxy Rule Builder.

This script demonstrates using the Story class to create user documentation
outside of the test framework.

Usage:
    python generate_rule_builder_tutorial.py \
        --galaxy_url http://localhost:8081 \
        --story-output ./rules_tutorial \
"""
import argparse
import sys
from contextlib import contextmanager

from galaxy.selenium import cli

DESCRIPTION = __doc__


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    args = _arg_parser().parse_args(argv)
    if not args.story_title:
        args.story_title = "Galaxy Rule Builder Tutorial"
    if not args.story_description:
        args.story_description = "Tutorial demonstrating automatic and manual usage of Galaxy's Rule Builder."
    driver_wrapper = cli.DriverWrapper(args)

    include_result = args.perform_uploads

    try:
        # Generate the tutorial
        generate_rule_builder_tutorial(driver_wrapper, include_result=include_result)

        # Finalize story if enabled
        if driver_wrapper.story.enabled:
            driver_wrapper.story.finalize()
            print(f"Tutorial generated in: {driver_wrapper.story.output_directory}")
    finally:
        driver_wrapper.finish()


def generate_rule_builder_tutorial(has_driver, include_result=False):
    """Generate a tutorial documenting the Galaxy Rule Builder features."""

    has_driver.home()
    has_driver.register()

    has_driver.home()
    has_driver.ensure_rules_activity_enabled()

    with example_history(has_driver, "Workbook Example 1"):
        has_driver.upload_workbook_example_1(include_result=include_result)
    with example_history(has_driver, "Workbook Example 2"):
        has_driver.upload_workbook_example_2(include_result=include_result)
    with example_history(has_driver, "Workbook Example 3"):
        has_driver.upload_workbook_example_3(include_result=include_result)
    with example_history(has_driver, "Workbook Example 4"):
        has_driver.upload_workbook_example_4(include_result=include_result)

    with example_history(has_driver, "Rules Example 1"):
        has_driver.upload_rules_example_1(include_result=include_result)
    with example_history(has_driver, "Rules Example 2"):
        has_driver.upload_rules_example_2(include_result=include_result)
    with example_history(has_driver, "Rules Example 3"):
        has_driver.upload_rules_example_3(include_result=include_result)
    with example_history(has_driver, "Rules Example 4"):
        has_driver.upload_rules_example_4(include_result=include_result)
    with example_history(has_driver, "Rules Example 5"):
        has_driver.upload_rules_example_5(include_result=include_result)
    with example_history(has_driver, "Rules Example 6"):
        has_driver.upload_rules_example_6(include_result=include_result)


@contextmanager
def example_history(driver, title: str):
    """Context manager to create an example history for the tutorial."""
    try:
        driver.home()
        history = driver.history_panel_create_new_with_name(title)
        yield history
    finally:
        # potentially delete history here?
        pass


def _arg_parser():
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser = cli.add_story_arguments(parser)
    parser.add_argument(
        "--perform-uploads",
        action="store_true",
        help="Actually perform uploads and include final screenshots in the tutorial.",
    )
    return parser


if __name__ == "__main__":
    main()
