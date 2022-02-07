import os
import string
import sys

import yaml

THIS_DIRECTORY = os.path.dirname(os.path.realpath(__file__))
GALAXY_ROOT_DIR = os.path.abspath(os.path.join(THIS_DIRECTORY, os.pardir))
CWL_API_TESTS_DIRECTORY = os.path.join(GALAXY_ROOT_DIR, "lib", "galaxy_test", "api", "cwl")

TEST_FILE_TEMPLATE = string.Template(
    '''"""Test CWL conformance for version ${version}."""

import pytest

from ..test_workflows_cwl import BaseCwlWorkflowTestCase


class CwlConformanceTestCase(BaseCwlWorkflowTestCase):
    """Test case mapping to CWL conformance tests for version ${version}."""
$tests'''
)

TEST_TEMPLATE = string.Template(
    '''
${marks}    def test_conformance_${version_simple}_${label}(self):
        """${doc}

        Generated from::

${cwl_test_def}
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""${version}""", """${doc}""")
'''
)

RED_TESTS = {
    "v1.0": [
        # required
        "directory_literal_with_literal_file_nostdin",
        "format_checking",
        "format_checking_equivalentclass",
        "format_checking_subclass",
        "stdin_from_directory_literal_with_literal_file",
        "stdin_from_directory_literal_with_local_file",
        "step_input_default_value_overriden_2nd_step_noexp",
        "step_input_default_value_overriden_noexp",
        # not required
        "clt_any_input_with_mixed_array_provided",
        "clt_any_input_with_record_provided",
        "clt_optional_union_input_file_or_files_with_array_of_one_file_provided",
        "clt_optional_union_input_file_or_files_with_many_files_provided",
        "directory_secondaryfiles",
        "docker_entrypoint",
        "dockeroutputdir",
        "dynamic_initial_workdir",
        "dynamic_resreq_filesizes",
        "dynamic_resreq_wf_optional_file_default",
        "dynamic_resreq_wf_optional_file_wf_default",
        "env_home_tmpdir",
        "env_home_tmpdir_docker",
        "env_home_tmpdir_docker_complex",
        "filesarray_secondaryfiles",
        "initialworkdir_nesteddir",
        "input_dir_recurs_copy_writable",
        "job_input_secondary_subdirs",
        "job_input_subdir_primary_and_secondary_subdirs",
        "record_output_binding",
        "resreq_step_overrides_wf",
        "step_input_default_value_overriden",
        "step_input_default_value_overriden_2nd_step",
        "valuefrom_wf_step",
        "valuefrom_wf_step_multiple",
        "wf_multiplesources_multipletypes",
        "wf_multiplesources_multipletypes_noexp",
        "wf_scatter_flat_crossproduct_oneempty",
        "wf_scatter_nested_crossproduct_firstempty",
        "wf_scatter_nested_crossproduct_secondempty",
        "wf_scatter_oneparam_valuefrom",
        "wf_scatter_oneparam_valuefrom_inputs",
        "wf_scatter_two_flat_crossproduct",
        "wf_scatter_two_nested_crossproduct",
        "wf_scatter_twoparam_dotproduct_valuefrom",
        "wf_scatter_twoparam_flat_crossproduct_valuefrom",
        "wf_scatter_twoparam_nested_crossproduct_valuefrom",
        "workflow_any_input_with_record_provided",
        "workflow_embedded_subworkflow_embedded_subsubworkflow",
        "workflow_embedded_subworkflow_with_subsubworkflow_and_tool",
        "workflow_embedded_subworkflow_with_tool_and_subsubworkflow",
        "workflow_file_array_output",
        "workflow_file_input_default_unspecified",
        "workflow_integer_input_optional_unspecified",
        "workflow_records_inputs_and_outputs",
    ],
    "v1.1": [
        # required
        "any_input_param_graph_no_default",
        "any_input_param_graph_no_default_hashmain",
        "directory_literal_with_literal_file_nostdin",
        "fail_glob_outside_output_dir",
        "format_checking",
        "format_checking_equivalentclass",
        "format_checking_subclass",
        "input_records_file_entry_with_format",
        "outputEval_exitCode",
        "outputbinding_glob_directory",
        "secondary_files_in_output_records",
        "secondary_files_in_unnamed_records",
        "secondary_files_missing",
        "stage_file_array_to_dir",
        "stage_file_array_to_dir_basename",
        "stage_file_array_to_dir_basename_entryname",
        "stdin_from_directory_literal_with_literal_file",
        "stdin_from_directory_literal_with_local_file",
        "step_input_default_value_overriden_2nd_step_noexp",
        "step_input_default_value_overriden_noexp",
        # not required
        "clt_any_input_with_mixed_array_provided",
        "clt_any_input_with_record_provided",
        "clt_optional_union_input_file_or_files_with_array_of_one_file_provided",
        "clt_optional_union_input_file_or_files_with_many_files_provided",
        "cwl_requirements_addition",
        "cwl_requirements_override_expression",
        "cwl_requirements_override_static",
        "directory_secondaryfiles",
        "docker_entrypoint",
        "dockeroutputdir",
        "dynamic_resreq_filesizes",
        "dynamic_resreq_wf_optional_file_default",
        "dynamic_resreq_wf_optional_file_wf_default",
        "embedded_subworkflow",
        "env_home_tmpdir",
        "env_home_tmpdir_docker",
        "env_home_tmpdir_docker_no_return_code",
        "filesarray_secondaryfiles",
        "filesarray_secondaryfiles2",
        "initialworkdir_nesteddir",
        "inplace_update_on_dir_content",
        "inplace_update_on_file_content",
        "input_dir_recurs_copy_writable",
        "job_input_secondary_subdirs",
        "job_input_subdir_primary_and_secondary_subdirs",
        "listing_requirement_deep",
        "listing_requirement_none",
        "listing_requirement_shallow",
        "networkaccess",
        "networkaccess_disabled",
        "record_output_binding",
        "record_output_file_entry_format",
        "resreq_step_overrides_wf",
        "scatter_embedded_subworkflow",
        "scatter_multi_input_embedded_subworkflow",
        "secondary_files_in_named_records",
        "stage_array_dirs",
        "stage_null_array",
        "stdin_shorcut",
        "step_input_default_value_overriden",
        "step_input_default_value_overriden_2nd_step",
        "symlink_to_file_out_of_workdir_illegal",
        "timelimit_expressiontool",
        "timelimit_invalid_wf",
        "timelimit_zero_unlimited",
        "timelimit_zero_unlimited_wf",
        "tmpdir_is_not_outdir",
        "valuefrom_wf_step",
        "valuefrom_wf_step_multiple",
        "wf_multiplesources_multipletypes",
        "wf_multiplesources_multipletypes_noexp",
        "wf_scatter_flat_crossproduct_oneempty",
        "wf_scatter_nested_crossproduct_firstempty",
        "wf_scatter_nested_crossproduct_secondempty",
        "wf_scatter_oneparam_valuefrom",
        "wf_scatter_oneparam_valuefrom_inputs",
        "wf_scatter_two_flat_crossproduct",
        "wf_scatter_two_nested_crossproduct",
        "wf_scatter_twoparam_dotproduct_valuefrom",
        "wf_scatter_twoparam_flat_crossproduct_valuefrom",
        "wf_scatter_twoparam_nested_crossproduct_valuefrom",
        "workflow_any_input_with_record_provided",
        "workflow_embedded_subworkflow_embedded_subsubworkflow",
        "workflow_embedded_subworkflow_with_subsubworkflow_and_tool",
        "workflow_embedded_subworkflow_with_tool_and_subsubworkflow",
        "workflow_file_array_output",
        "workflow_file_input_default_unspecified",
        "workflow_input_inputBinding_loadContents",
        "workflow_input_loadContents_without_inputBinding",
        "workflow_integer_input_optional_unspecified",
        "workflow_records_inputs_and_outputs",
        "workflow_step_in_loadContents",
    ],
    "v1.2": [
        # required
        "any_input_param_graph_no_default",
        "any_input_param_graph_no_default_hashmain",
        "directory_literal_with_literal_file_nostdin",
        "format_checking",
        "format_checking_equivalentclass",
        "format_checking_subclass",
        "glob_outside_outputs_fails",
        "input_records_file_entry_with_format",
        "outputEval_exitCode",
        "outputbinding_glob_directory",
        "secondary_files_in_output_records",
        "secondary_files_in_unnamed_records",
        "secondary_files_missing",
        "stage_file_array",
        "stage_file_array_basename",
        "stage_file_array_entryname_overrides",
        "stdin_from_directory_literal_with_literal_file",
        "stdin_from_directory_literal_with_local_file",
        "step_input_default_value_overriden_2nd_step_noexp",
        "step_input_default_value_overriden_noexp",
        # not required
        "225",
        "226",
        "233",
        "235",
        "236",
        "306",
        "307",
        "all_non_null_all_null",
        "all_non_null_all_null_nojs",
        "all_non_null_multi_non_null",
        "all_non_null_multi_non_null_nojs",
        "all_non_null_one_non_null",
        "all_non_null_one_non_null_nojs",
        "clt_any_input_with_mixed_array_provided",
        "clt_any_input_with_record_provided",
        "clt_any_input_with_string_provided",
        "clt_optional_union_input_file_or_files_with_array_of_one_file_provided",
        "clt_optional_union_input_file_or_files_with_many_files_provided",
        "command_input_file_expression",
        "condifional_scatter_on_nonscattered_false",
        "condifional_scatter_on_nonscattered_false_nojs",
        "condifional_scatter_on_nonscattered_true_nojs",
        "conditionals_multi_scatter",
        "conditionals_multi_scatter_nojs",
        "conditionals_nested_cross_scatter",
        "conditionals_nested_cross_scatter_nojs",
        "conditionals_non_boolean_fail",
        "conditionals_non_boolean_fail_nojs",
        "cwl_requirements_addition",
        "cwl_requirements_override_expression",
        "cwl_requirements_override_static",
        "cwloutput_nolimit",
        "direct_optional_nonnull_result_nojs",
        "direct_optional_null_result",
        "direct_required",
        "direct_required_nojs",
        "directory_secondaryfiles",
        "docker_entrypoint",
        "dockeroutputdir",
        "dynamic_resreq_filesizes",
        "dynamic_resreq_wf_optional_file_default",
        "dynamic_resreq_wf_optional_file_wf_default",
        "embedded_subworkflow",
        "env_home_tmpdir",
        "env_home_tmpdir_docker",
        "env_home_tmpdir_docker_no_return_code",
        "filesarray_secondaryfiles",
        "filesarray_secondaryfiles2",
        "first_non_null_first_non_null",
        "first_non_null_first_non_null_nojs",
        "first_non_null_second_non_null",
        "first_non_null_second_non_null_nojs",
        "initialworkdir_nesteddir",
        "input_dir_recurs_copy_writable",
        "iwd-container-entryname1",
        "iwd-fileobjs1",
        "iwd-fileobjs2",
        "iwd-passthrough1",
        "iwd-passthrough3",
        "iwd-passthrough4",
        "job_input_secondary_subdirs",
        "job_input_subdir_primary_and_secondary_subdirs",
        "listing_requirement_deep",
        "listing_requirement_none",
        "listing_requirement_shallow",
        "networkaccess",
        "networkaccess_disabled",
        "pass_through_required_false_when",
        "pass_through_required_false_when_nojs",
        "pass_through_required_the_only_non_null",
        "pass_through_required_the_only_non_null_nojs",
        "pass_through_required_true_when",
        "pass_through_required_true_when_nojs",
        "record_output_binding",
        "record_output_file_entry_format",
        "resreq_step_overrides_wf",
        "scatter_embedded_subworkflow",
        "scatter_multi_input_embedded_subworkflow",
        "scatter_on_scattered_conditional",
        "scatter_on_scattered_conditional_nojs",
        "secondary_files_in_named_records",
        "step_input_default_value_overriden",
        "step_input_default_value_overriden_2nd_step",
        "storage_float",
        "the_only_non_null_single_true",
        "the_only_non_null_single_true_nojs",
        "timelimit_expressiontool",
        "timelimit_invalid_wf",
        "timelimit_zero_unlimited",
        "timelimit_zero_unlimited_wf",
        "tmpdir_is_not_outdir",
        "valuefrom_wf_step",
        "valuefrom_wf_step_multiple",
        "wf_multiplesources_multipletypes",
        "wf_multiplesources_multipletypes_noexp",
        "wf_scatter_flat_crossproduct_oneempty",
        "wf_scatter_nested_crossproduct_firstempty",
        "wf_scatter_nested_crossproduct_secondempty",
        "wf_scatter_oneparam_valuefrom",
        "wf_scatter_oneparam_valuefrom_inputs",
        "wf_scatter_two_flat_crossproduct",
        "wf_scatter_two_nested_crossproduct",
        "wf_scatter_twoparam_dotproduct_valuefrom",
        "wf_scatter_twoparam_flat_crossproduct_valuefrom",
        "wf_scatter_twoparam_nested_crossproduct_valuefrom",
        "wf_wc_nomultiple_merge_nested",
        "workflow_any_input_with_record_provided",
        "workflow_embedded_subworkflow_embedded_subsubworkflow",
        "workflow_embedded_subworkflow_with_subsubworkflow_and_tool",
        "workflow_embedded_subworkflow_with_tool_and_subsubworkflow",
        "workflow_file_array_output",
        "workflow_file_input_default_unspecified",
        "workflow_input_inputBinding_loadContents",
        "workflow_input_loadContents_without_inputBinding",
        "workflow_integer_input_optional_unspecified",
        "workflow_records_inputs_and_outputs",
        "workflow_step_in_loadContents",
    ],
}


def conformance_tests_gen(directory, filename="conformance_tests.yaml"):
    conformance_tests_path = os.path.join(directory, filename)
    with open(conformance_tests_path) as f:
        conformance_tests = yaml.safe_load(f)

    for conformance_test in conformance_tests:
        if "$import" in conformance_test:
            import_path = conformance_test["$import"]
            yield from conformance_tests_gen(directory, import_path)
        else:
            yield conformance_test


def main():
    if len(sys.argv) != 3:
        raise Exception("Expecting 2 arguments: conformance_tests_dir version")
    conformance_tests_dir = sys.argv[1]
    version = sys.argv[2]
    version_simple = version.replace(".", "_")

    red_tests_list = RED_TESTS[version]
    red_tests_found = set()
    all_tests_found = set()

    tests = ""

    for i, conformance_test in enumerate(conformance_tests_gen(os.path.join(conformance_tests_dir, version))):
        test_with_doc = conformance_test.copy()
        if "doc" not in test_with_doc:
            raise Exception(f"No doc in test [{test_with_doc}]")
        del test_with_doc["doc"]
        cwl_test_def = yaml.dump(test_with_doc, default_flow_style=False)
        cwl_test_def = "\n".join(f"            {line}" for line in cwl_test_def.splitlines())
        label = conformance_test.get("label", str(i))
        tags = conformance_test.get("tags", [])
        is_red = label in red_tests_list

        marks = "    @pytest.mark.cwl_conformance\n"
        marks += f"    @pytest.mark.cwl_conformance_{version_simple}\n"
        for tag in tags:
            marks += f"    @pytest.mark.{tag}\n"
        if is_red:
            marks += "    @pytest.mark.red\n"
        else:
            marks += "    @pytest.mark.green\n"

        if not {"command_line_tool", "expression_tool", "workflow"}.intersection(tags):
            print(
                f"PROBLEM - test [{label}] tagged with neither command_line_tool, expression_tool, nor workflow",
                file=sys.stderr,
            )

        template_kwargs = {
            "version_simple": version_simple,
            "version": version,
            "doc": conformance_test["doc"],
            "cwl_test_def": cwl_test_def,
            "label": label.replace("-", "_"),
            "marks": marks,
        }
        test_body = TEST_TEMPLATE.safe_substitute(template_kwargs)
        tests += test_body

        if label in all_tests_found:
            print(f"PROBLEM - Duplicate label found [{label}]", file=sys.stderr)
        all_tests_found.add(label)
        if is_red:
            red_tests_found.add(label)

    test_file_contents = TEST_FILE_TEMPLATE.safe_substitute(
        {
            "version": version,
            "version_simple": version_simple,
            "tests": tests,
        }
    )

    test_file = os.path.join(CWL_API_TESTS_DIRECTORY, f"test_cwl_conformance_{version_simple}.py")
    with open(test_file, "w") as f:
        f.write(test_file_contents)
    print(f"Finished writing {test_file}")

    for red_test in red_tests_list:
        if red_test not in red_tests_found:
            print(f"PROBLEM - Failed to find annotated red test [{red_test}]", file=sys.stderr)


if __name__ == "__main__":
    main()
