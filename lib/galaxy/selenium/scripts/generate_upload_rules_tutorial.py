#!/usr/bin/env python
"""Generate tutorial documentation for building nested lists with Galaxy upload rules.

This script demonstrates using the Story class to create user documentation
outside of the test framework.

Usage:
    python generate_upload_rules_tutorial.py \
        --galaxy_url http://localhost:8081 \
        --story-output ./nested_lists_tutorial \
        --story-title "Building Nested Lists in Galaxy" \
        --story-description "Learn how to create hierarchical collection structures using Galaxy's Rule Builder"
"""
import argparse
import sys

from galaxy.selenium import cli

DESCRIPTION = "Generate tutorial for building nested lists with upload rules."


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    args = _arg_parser().parse_args(argv)
    driver_wrapper = cli.DriverWrapper(args)

    try:
        # Generate the tutorial
        generate_nested_lists_tutorial(driver_wrapper)

        # Finalize story if enabled
        if driver_wrapper.story:
            driver_wrapper.story.finalize()
            print(f"Tutorial generated in: {driver_wrapper.story.output_directory}")
    finally:
        driver_wrapper.finish()


def generate_nested_lists_tutorial(driver):
    """Generate nested lists tutorial with story documentation."""

    driver.document(
        """
    # Overview

    This tutorial demonstrates creating hierarchical collection structures using Galaxy's
    Rule Builder. We'll organize SRA datasets into nested lists where outer identifiers
    describe sample types and inner identifiers describe replicates.
    """
    )

    # Navigate to Galaxy home
    driver.home()

    driver.document(
        """
    ## Step 1: Upload Source Data

    First, we'll upload the SRA metadata table that we'll use to build our collection.
    """
    )

    # Upload the dataset
    driver.perform_upload(driver.get_filename("rules/PRJNA355367.tsv"))
    driver.history_panel_wait_for_hid_ok(1)
    driver.screenshot("source_data_uploaded", caption="SRA metadata uploaded to history")

    driver.document(
        """
    ## Step 2: Start Rule Builder

    Click the upload button and select 'Rule-based' to access the Rule Builder interface.
    """
    )

    driver.upload_rule_start()
    driver.upload_rule_set_data_type("Collections")
    driver.upload_rule_dataset_dialog()
    driver.upload_rule_set_dataset(1)
    driver.screenshot("rule_builder_start", caption="Rule Builder source selection")

    driver.document(
        """
    ## Step 3: Configure Rule Builder

    The Rule Builder loads with our metadata table. We'll now define how to transform
    this data into a nested list collection.
    """
    )

    driver.upload_rule_build()
    rule_builder = driver.components.rule_builder
    rule_builder._.wait_for_and_click()
    driver.screenshot("rules_landing", caption="Rule Builder interface with loaded data")

    driver.document(
        """
    ## Step 4: Set Basic Mappings

    Configure the URL column and data type for the collection.
    """
    )

    driver.rule_builder_filter_count(1)
    driver.rule_builder_set_mapping("url", "J")
    driver.rule_builder_set_extension("sra")
    driver.screenshot("basic_mappings", caption="URL and data type configured")

    driver.document(
        """
    ## Step 5: Extract Library Type with Regular Expression

    Apply a regular expression to extract library type categories from the data.
    The pattern `([^\\d]+)\\d+` strips trailing numbers to isolate category labels.
    """
    )

    driver.rule_builder_add_regex_groups("L", 1, r"([^\d]+)\d+")
    driver.screenshot("regex_applied", caption="Regular expression creates new column with library types")

    driver.document(
        """
    ## Step 6: Assign Multiple List Identifiers

    Set up the nested structure by assigning two levels of list identifiers:
    - Outer level: Library type categories
    - Inner level: Individual run identifiers
    """
    )

    driver.rule_builder_set_mapping("list-identifiers", ["M", "A"])
    driver.screenshot("list_identifiers", caption="Two-level list identifiers configured")

    driver.document(
        """
    ## Step 7: Name and Create Collection

    Give your collection a meaningful name and create it.
    """
    )

    driver.rule_builder_set_collection_name("PRJNA355367")
    driver.screenshot("collection_named", caption="Collection ready to create")

    driver.document(
        """
    ## Result

    The resulting nested list collection provides hierarchical organization of your datasets,
    making it easy to process related samples together in workflows.
    """
    )


def _arg_parser():
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser = cli.add_story_arguments(parser)
    return parser


if __name__ == "__main__":
    main()
