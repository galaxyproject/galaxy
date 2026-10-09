"""Test CWL conformance for version v1.2."""

import pytest

from ..test_workflows_cwl import BaseCwlWorkflowsApiTestCase


class TestCwlConformance(BaseCwlWorkflowsApiTestCase):
    """Test case mapping to CWL conformance tests for version v1.2."""

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_cl_basic_generation(self):
        """General test of command line generation

        Generated from::

            id: cl_basic_generation
            job: tests/bwa-mem-job.json
            output:
              args:
              - bwa
              - mem
              - -t
              - '2'
              - -I
              - 1,2,3,4
              - -m
              - '3'
              - chr20.fa
              - example_human_Illumina.pe_1.fastq
              - example_human_Illumina.pe_2.fastq
            tags:
            - required
            - command_line_tool
            tool: tests/bwa-mem-tool.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """General test of command line generation""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_nested_prefixes_arrays(self):
        """Test nested prefixes with arrays

        Generated from::

            id: nested_prefixes_arrays
            job: tests/bwa-mem-job.json
            output:
              args:
              - bwa
              - mem
              - chr20.fa
              - -XXX
              - -YYY
              - example_human_Illumina.pe_1.fastq
              - -YYY
              - example_human_Illumina.pe_2.fastq
            tags:
            - required
            - command_line_tool
            tool: tests/binding-test.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test nested prefixes with arrays""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.schema_def
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_nested_cl_bindings(self):
        """Test nested command line bindings

        Generated from::

            id: nested_cl_bindings
            job: tests/tmap-job.json
            output:
              args:
              - tmap
              - mapall
              - stage1
              - map1
              - --min-seq-length
              - '20'
              - map2
              - --min-seq-length
              - '20'
              - stage2
              - map1
              - --max-seq-length
              - '20'
              - --min-seq-length
              - '10'
              - --seed-length
              - '16'
              - map2
              - --max-seed-hits
              - '-1'
              - --max-seq-length
              - '20'
              - --min-seq-length
              - '10'
            tags:
            - schema_def
            - command_line_tool
            tool: tests/tmap-tool.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test nested command line bindings""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_cl_optional_inputs_missing(self):
        """Test command line with optional input (missing)

        Generated from::

            id: cl_optional_inputs_missing
            job: tests/cat-job.json
            output:
              args:
              - cat
              - hello.txt
            tags:
            - required
            - command_line_tool
            tool: tests/cat1-testcli.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test command line with optional input (missing)""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_cl_optional_bindings_provided(self):
        """Test command line with optional input (provided)

        Generated from::

            id: cl_optional_bindings_provided
            job: tests/cat-n-job.json
            output:
              args:
              - cat
              - -n
              - hello.txt
            tags:
            - required
            - command_line_tool
            tool: tests/cat1-testcli.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test command line with optional input (provided)""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.initial_work_dir
    @pytest.mark.inline_javascript
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_initworkdir_expreng_requirements(self):
        """Test InitialWorkDirRequirement ExpressionEngineRequirement.engineConfig feature

        Generated from::

            id: initworkdir_expreng_requirements
            job: tests/cat-job.json
            output:
              foo:
                checksum: sha1$63da67422622fbf9251a046d7a34b7ea0fd4fead
                class: File
                location: foo.txt
                size: 22
            tags:
            - initial_work_dir
            - inline_javascript
            - command_line_tool
            tool: tests/template-tool.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test InitialWorkDirRequirement ExpressionEngineRequirement.engineConfig feature""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.docker
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_stdout_redirect_docker(self):
        """Test command execution in Docker with stdout redirection

        Generated from::

            id: stdout_redirect_docker
            job: tests/cat-job.json
            output:
              output_file:
                checksum: sha1$47a013e660d408619d894b20806b1d5086aab03b
                class: File
                location: output.txt
                size: 13
            tags:
            - docker
            - command_line_tool
            tool: tests/cat3-tool.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test command execution in Docker with stdout redirection""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.docker
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_stdout_redirect_shortcut_docker(self):
        """Test command execution in Docker with shortcut stdout redirection

        Generated from::

            id: stdout_redirect_shortcut_docker
            job: tests/cat-job.json
            output:
              output_file:
                checksum: sha1$47a013e660d408619d894b20806b1d5086aab03b
                class: File
                location: Any
                size: 13
            tags:
            - docker
            - command_line_tool
            tool: tests/cat3-tool-shortcut.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test command execution in Docker with shortcut stdout redirection""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.docker
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_stdout_redirect_mediumcut_docker(self):
        """Test command execution in Docker with mediumcut stdout redirection

        Generated from::

            id: stdout_redirect_mediumcut_docker
            job: tests/cat-job.json
            output:
              output_file:
                checksum: sha1$47a013e660d408619d894b20806b1d5086aab03b
                class: File
                location: cat-out
                size: 13
            tags:
            - docker
            - command_line_tool
            tool: tests/cat3-tool-mediumcut.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test command execution in Docker with mediumcut stdout redirection""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.shell_command
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_stderr_redirect(self):
        """Test command line with stderr redirection

        Generated from::

            id: stderr_redirect
            job: tests/empty.json
            output:
              output_file:
                checksum: sha1$f1d2d2f924e986ac86fdf7b36c94bcdf32beec15
                class: File
                location: error.txt
                size: 4
            tags:
            - shell_command
            - command_line_tool
            tool: tests/stderr.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test command line with stderr redirection""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.shell_command
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_stderr_redirect_shortcut(self):
        """Test command line with stderr redirection, brief syntax

        Generated from::

            id: stderr_redirect_shortcut
            job: tests/empty.json
            output:
              output_file:
                checksum: sha1$f1d2d2f924e986ac86fdf7b36c94bcdf32beec15
                class: File
                location: Any
                size: 4
            tags:
            - shell_command
            - command_line_tool
            tool: tests/stderr-shortcut.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test command line with stderr redirection, brief syntax""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.shell_command
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_stderr_redirect_mediumcut(self):
        """Test command line with stderr redirection, named brief syntax

        Generated from::

            id: stderr_redirect_mediumcut
            job: tests/empty.json
            output:
              output_file:
                checksum: sha1$f1d2d2f924e986ac86fdf7b36c94bcdf32beec15
                class: File
                location: std.err
                size: 4
            tags:
            - shell_command
            - command_line_tool
            tool: tests/stderr-mediumcut.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test command line with stderr redirection, named brief syntax""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_stdinout_redirect_docker(self):
        """Test command execution in Docker with stdin and stdout redirection

        Generated from::

            id: stdinout_redirect_docker
            job: tests/cat-job.json
            output:
              output_txt:
                checksum: sha1$47a013e660d408619d894b20806b1d5086aab03b
                class: File
                location: output.txt
                size: 13
            tags:
            - required
            - command_line_tool
            tool: tests/cat4-tool.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test command execution in Docker with stdin and stdout redirection""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.inline_javascript
    @pytest.mark.expression_tool
    @pytest.mark.green
    def test_conformance_v1_2_expression_any(self):
        """Test default usage of Any in expressions.

        Generated from::

            id: expression_any
            job: tests/empty.json
            output:
              output: 1
            tags:
            - inline_javascript
            - expression_tool
            tool: tests/null-expression1-tool.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test default usage of Any in expressions.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.inline_javascript
    @pytest.mark.expression_tool
    @pytest.mark.green
    def test_conformance_v1_2_expression_any_null(self):
        """Test explicitly passing null to Any type inputs with default values.

        Generated from::

            id: expression_any_null
            job: tests/null-expression1-job.json
            output:
              output: 1
            tags:
            - inline_javascript
            - expression_tool
            tool: tests/null-expression1-tool.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test explicitly passing null to Any type inputs with default values.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.inline_javascript
    @pytest.mark.expression_tool
    @pytest.mark.green
    def test_conformance_v1_2_expression_any_string(self):
        """Testing the string 'null' does not trip up an Any with a default value.

        Generated from::

            id: expression_any_string
            job: tests/null-expression2-job.json
            output:
              output: 2
            tags:
            - inline_javascript
            - expression_tool
            tool: tests/null-expression1-tool.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Testing the string 'null' does not trip up an Any with a default value.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.inline_javascript
    @pytest.mark.expression_tool
    @pytest.mark.green
    def test_conformance_v1_2_expression_any_nodefaultany(self):
        """Test Any without defaults cannot be unspecified.

        Generated from::

            id: expression_any_nodefaultany
            job: tests/empty.json
            should_fail: true
            tags:
            - inline_javascript
            - expression_tool
            tool: tests/null-expression2-tool.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test Any without defaults cannot be unspecified.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.inline_javascript
    @pytest.mark.expression_tool
    @pytest.mark.green
    def test_conformance_v1_2_expression_any_null_nodefaultany(self):
        """Test explicitly passing null to Any type without a default value.

        Generated from::

            id: expression_any_null_nodefaultany
            job: tests/null-expression1-job.json
            should_fail: true
            tags:
            - inline_javascript
            - expression_tool
            tool: tests/null-expression2-tool.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test explicitly passing null to Any type without a default value.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.inline_javascript
    @pytest.mark.expression_tool
    @pytest.mark.green
    def test_conformance_v1_2_expression_any_nullstring_nodefaultany(self):
        """Testing the string 'null' does not trip up an Any without a default value.

        Generated from::

            id: expression_any_nullstring_nodefaultany
            job: tests/null-expression2-job.json
            output:
              output: 2
            tags:
            - inline_javascript
            - expression_tool
            tool: tests/null-expression2-tool.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Testing the string 'null' does not trip up an Any without a default value.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_2_any_outputSource_compatibility(self):
        """Testing Any type compatibility in outputSource

        Generated from::

            id: any_outputSource_compatibility
            job: tests/any-type-job.json
            output:
              output1:
              - hello
              - world
              output2:
              - foo
              - bar
              output3: hello
            tags:
            - required
            - workflow
            tool: tests/any-type-compat.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Testing Any type compatibility in outputSource""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_stdinout_redirect(self):
        """Test command execution in with stdin and stdout redirection

        Generated from::

            id: stdinout_redirect
            job: tests/cat-job.json
            output:
              output:
                checksum: sha1$47a013e660d408619d894b20806b1d5086aab03b
                class: File
                location: output
                size: 13
            tags:
            - required
            - command_line_tool
            tool: tests/cat-tool.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test command execution in with stdin and stdout redirection""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.inline_javascript
    @pytest.mark.expression_tool
    @pytest.mark.green
    def test_conformance_v1_2_expression_parseint(self):
        """Test ExpressionTool with Javascript engine

        Generated from::

            id: expression_parseint
            job: tests/parseInt-job.json
            output:
              output: 42
            tags:
            - inline_javascript
            - expression_tool
            tool: tests/parseInt-tool.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test ExpressionTool with Javascript engine""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.inline_javascript
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_expression_outputEval(self):
        """Test outputEval to transform output

        Generated from::

            id: expression_outputEval
            job: tests/wc-job.json
            output:
              output: 16
            tags:
            - inline_javascript
            - command_line_tool
            tool: tests/wc2-tool.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test outputEval to transform output""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.inline_javascript
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_2_wf_wc_parseInt(self):
        """Test two step workflow with imported tools

        Generated from::

            id: wf_wc_parseInt
            job: tests/wc-job.json
            output:
              count_output: 16
            tags:
            - inline_javascript
            - workflow
            tool: tests/count-lines1-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test two step workflow with imported tools""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.inline_javascript
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_2_wf_wc_expressiontool(self):
        """Test two step workflow with inline tools

        Generated from::

            id: wf_wc_expressiontool
            job: tests/wc-job.json
            output:
              count_output: 16
            tags:
            - inline_javascript
            - workflow
            tool: tests/count-lines2-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test two step workflow with inline tools""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.scatter
    @pytest.mark.inline_javascript
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_2_wf_wc_scatter(self):
        """Test single step workflow with Scatter step

        Generated from::

            id: wf_wc_scatter
            job: tests/count-lines3-job.json
            output:
              count_output:
              - 16
              - 1
            tags:
            - scatter
            - inline_javascript
            - workflow
            tool: tests/count-lines3-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test single step workflow with Scatter step""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.scatter
    @pytest.mark.multiple_input
    @pytest.mark.inline_javascript
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_2_wf_wc_scatter_multiple_merge(self):
        """Test single step workflow with Scatter step and two data links connected to same input, default merge behavior

        Generated from::

            id: wf_wc_scatter_multiple_merge
            job: tests/count-lines4-job.json
            output:
              count_output:
              - 16
              - 1
            tags:
            - scatter
            - multiple_input
            - inline_javascript
            - workflow
            tool: tests/count-lines4-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test single step workflow with Scatter step and two data links connected to same input, default merge behavior""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.scatter
    @pytest.mark.multiple_input
    @pytest.mark.inline_javascript
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_2_wf_wc_scatter_multiple_nested(self):
        """Test single step workflow with Scatter step and two data links connected to same input, nested merge behavior

        Generated from::

            id: wf_wc_scatter_multiple_nested
            job: tests/count-lines6-job.json
            output:
              count_output:
              - 32
              - 2
            tags:
            - scatter
            - multiple_input
            - inline_javascript
            - workflow
            tool: tests/count-lines6-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test single step workflow with Scatter step and two data links connected to same input, nested merge behavior""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.multiple_input
    @pytest.mark.inline_javascript
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_2_wf_wc_scatter_multiple_flattened(self):
        """Test single step workflow with Scatter step and two data links connected to same input, flattened merge behavior

        Generated from::

            id: wf_wc_scatter_multiple_flattened
            job: tests/count-lines6-job.json
            output:
              count_output: 34
            tags:
            - multiple_input
            - inline_javascript
            - workflow
            tool: tests/count-lines7-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test single step workflow with Scatter step and two data links connected to same input, flattened merge behavior""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.inline_javascript
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_2_wf_wc_nomultiple(self):
        """Test when step source is a single-item list and there is no linkMerge, then it not wrapped in a list, and that MultipleInputFeatureRequirement is not required.

        Generated from::

            id: wf_wc_nomultiple
            job: tests/count-lines4-job.json
            output:
              count_output: 16
            tags:
            - inline_javascript
            - workflow
            tool: tests/count-lines13-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test when step source is a single-item list and there is no linkMerge, then it not wrapped in a list, and that MultipleInputFeatureRequirement is not required.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.inline_javascript
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_2_wf_wc_nomultiple_merge_nested(self):
        """Test when step source is a single-item list and linkMerge is listed, then it is wrapped in a list.

        Generated from::

            id: wf_wc_nomultiple_merge_nested
            job: tests/count-lines4-job.json
            output:
              count_output: 16
            tags:
            - inline_javascript
            - workflow
            tool: tests/count-lines19-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test when step source is a single-item list and linkMerge is listed, then it is wrapped in a list.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.inline_javascript
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_2_wf_input_default_missing(self):
        """Test workflow with default value for input parameter (missing)

        Generated from::

            id: wf_input_default_missing
            job: tests/empty.json
            output:
              count_output: 1
            tags:
            - inline_javascript
            - workflow
            tool: tests/count-lines5-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test workflow with default value for input parameter (missing)""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.inline_javascript
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_2_wf_input_default_provided(self):
        """Test workflow with default value for input parameter (provided)

        Generated from::

            id: wf_input_default_provided
            job: tests/wc-job.json
            output:
              count_output: 16
            tags:
            - inline_javascript
            - workflow
            tool: tests/count-lines5-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test workflow with default value for input parameter (provided)""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_2_wf_default_tool_default(self):
        """Test that workflow defaults override tool defaults

        Generated from::

            id: wf_default_tool_default
            job: tests/empty.json
            output:
              default_output: workflow_default
            tags:
            - required
            - workflow
            tool: tests/echo-wf-default.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test that workflow defaults override tool defaults""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.env_var
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_envvar_req(self):
        """Test EnvVarRequirement

        Generated from::

            id: envvar_req
            job: tests/env-job.json
            output:
              out:
                checksum: sha1$b3ec4ed1749c207e52b3a6d08c59f31d83bff519
                class: File
                location: out
                size: 15
            tags:
            - env_var
            - command_line_tool
            tool: tests/env-tool1.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test EnvVarRequirement""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.scatter
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_2_wf_scatter_single_param(self):
        """Test workflow scatter with single scatter parameter

        Generated from::

            id: wf_scatter_single_param
            job: tests/scatter-job1.json
            output:
              out:
              - foo one
              - foo two
              - foo three
              - foo four
            tags:
            - scatter
            - workflow
            tool: tests/scatter-wf1.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test workflow scatter with single scatter parameter""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.scatter
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_2_wf_scatter_two_nested_crossproduct(self):
        """Test workflow scatter with two scatter parameters and nested_crossproduct join method

        Generated from::

            id: wf_scatter_two_nested_crossproduct
            job: tests/scatter-job2.json
            output:
              out:
              - - foo one three
                - foo one four
              - - foo two three
                - foo two four
            tags:
            - scatter
            - workflow
            tool: tests/scatter-wf2.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test workflow scatter with two scatter parameters and nested_crossproduct join method""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.scatter
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_2_wf_scatter_two_flat_crossproduct(self):
        """Test workflow scatter with two scatter parameters and flat_crossproduct join method

        Generated from::

            id: wf_scatter_two_flat_crossproduct
            job: tests/scatter-job2.json
            output:
              out:
              - foo one three
              - foo one four
              - foo two three
              - foo two four
            tags:
            - scatter
            - workflow
            tool: tests/scatter-wf3.cwl#main
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test workflow scatter with two scatter parameters and flat_crossproduct join method""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.scatter
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_2_wf_scatter_two_dotproduct(self):
        """Test workflow scatter with two scatter parameters and dotproduct join method

        Generated from::

            id: wf_scatter_two_dotproduct
            job: tests/scatter-job2.json
            output:
              out:
              - foo one three
              - foo two four
            tags:
            - scatter
            - workflow
            tool: tests/scatter-wf4.cwl#main
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test workflow scatter with two scatter parameters and dotproduct join method""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.scatter
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_2_wf_scatter_emptylist(self):
        """Test workflow scatter with single empty list parameter

        Generated from::

            id: wf_scatter_emptylist
            job: tests/scatter-empty-job1.json
            output:
              out: []
            tags:
            - scatter
            - workflow
            tool: tests/scatter-wf1.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test workflow scatter with single empty list parameter""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.scatter
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_2_wf_scatter_nested_crossproduct_secondempty(self):
        """Test workflow scatter with two scatter parameters and nested_crossproduct join method with second list empty

        Generated from::

            id: wf_scatter_nested_crossproduct_secondempty
            job: tests/scatter-empty-job2.json
            output:
              out:
              - []
              - []
            tags:
            - scatter
            - workflow
            tool: tests/scatter-wf2.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test workflow scatter with two scatter parameters and nested_crossproduct join method with second list empty""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.scatter
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_2_wf_scatter_nested_crossproduct_firstempty(self):
        """Test workflow scatter with two scatter parameters and nested_crossproduct join method with first list empty

        Generated from::

            id: wf_scatter_nested_crossproduct_firstempty
            job: tests/scatter-empty-job3.json
            output:
              out: []
            tags:
            - scatter
            - workflow
            tool: tests/scatter-wf3.cwl#main
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test workflow scatter with two scatter parameters and nested_crossproduct join method with first list empty""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.scatter
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_2_wf_scatter_flat_crossproduct_oneempty(self):
        """Test workflow scatter with two scatter parameters, one of which is empty and flat_crossproduct join method

        Generated from::

            id: wf_scatter_flat_crossproduct_oneempty
            job: tests/scatter-empty-job2.json
            output:
              out: []
            tags:
            - scatter
            - workflow
            tool: tests/scatter-wf3.cwl#main
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test workflow scatter with two scatter parameters, one of which is empty and flat_crossproduct join method""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.scatter
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_2_wf_scatter_dotproduct_twoempty(self):
        """Test workflow scatter with two empty scatter parameters and dotproduct join method

        Generated from::

            id: wf_scatter_dotproduct_twoempty
            job: tests/scatter-empty-job4.json
            output:
              out: []
            tags:
            - scatter
            - workflow
            tool: tests/scatter-wf4.cwl#main
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test workflow scatter with two empty scatter parameters and dotproduct join method""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_any_input_param(self):
        """Test Any type input parameter

        Generated from::

            id: any_input_param
            job: tests/env-job.json
            output:
              out: 'hello test env
            
                '
            tags:
            - required
            - command_line_tool
            tool: tests/echo-tool.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test Any type input parameter""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.subworkflow
    @pytest.mark.workflow
    @pytest.mark.inline_javascript
    @pytest.mark.green
    def test_conformance_v1_2_nested_workflow(self):
        """Test nested workflow

        Generated from::

            id: nested_workflow
            job: tests/wc-job.json
            output:
              count_output: 16
            tags:
            - subworkflow
            - workflow
            - inline_javascript
            tool: tests/count-lines8-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test nested workflow""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.env_var
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_2_requirement_priority(self):
        """Test requirement priority

        Generated from::

            id: requirement_priority
            job: tests/env-job.json
            output:
              out:
                checksum: sha1$b3ec4ed1749c207e52b3a6d08c59f31d83bff519
                class: File
                location: out
                size: 15
            tags:
            - env_var
            - workflow
            tool: tests/env-wf1.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test requirement priority""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.env_var
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_2_requirement_override_hints(self):
        """Test requirements override hints

        Generated from::

            id: requirement_override_hints
            job: tests/env-job.json
            output:
              out:
                checksum: sha1$cdc1e84968261d6a7575b5305945471f8be199b6
                class: File
                location: out
                size: 9
            tags:
            - env_var
            - workflow
            tool: tests/env-wf2.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test requirements override hints""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.env_var
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_2_requirement_workflow_steps(self):
        """Test requirements on workflow steps

        Generated from::

            id: requirement_workflow_steps
            job: tests/env-job.json
            output:
              out:
                checksum: sha1$cdc1e84968261d6a7575b5305945471f8be199b6
                class: File
                location: out
                size: 9
            tags:
            - env_var
            - workflow
            tool: tests/env-wf3.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test requirements on workflow steps""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.inline_javascript
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_2_step_input_default_value(self):
        """Test default value on step input parameter

        Generated from::

            id: step_input_default_value
            job: tests/empty.json
            output:
              count_output: 16
            tags:
            - inline_javascript
            - workflow
            tool: tests/count-lines9-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test default value on step input parameter""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.inline_javascript
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_2_step_input_default_value_nosource(self):
        """Test use default value on step input parameter with empty source

        Generated from::

            id: step_input_default_value_nosource
            job: tests/empty.json
            output:
              count_output: 16
            tags:
            - inline_javascript
            - workflow
            tool: tests/count-lines11-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test use default value on step input parameter with empty source""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.inline_javascript
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_2_step_input_default_value_nullsource(self):
        """Test use default value on step input parameter with null source

        Generated from::

            id: step_input_default_value_nullsource
            job: tests/file1-null.json
            output:
              count_output: 16
            tags:
            - inline_javascript
            - workflow
            tool: tests/count-lines11-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test use default value on step input parameter with null source""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.inline_javascript
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_2_step_input_default_value_overriden(self):
        """Test default value on step input parameter overridden by provided source

        Generated from::

            id: step_input_default_value_overriden
            job: tests/cat-job.json
            output:
              count_output: 1
            tags:
            - inline_javascript
            - workflow
            tool: tests/count-lines11-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test default value on step input parameter overridden by provided source""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_2_wf_simple(self):
        """Test simple workflow

        Generated from::

            id: wf_simple
            job: tests/revsort-job.json
            output:
              output:
                checksum: sha1$b9214658cc453331b62c2282b772a5c063dbd284
                class: File
                location: output.txt
                size: 1111
            tags:
            - required
            - workflow
            tool: tests/revsort.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test simple workflow""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_hints_unknown_ignored(self):
        """Test unknown hints are ignored.

        Generated from::

            id: hints_unknown_ignored
            job: tests/cat-job.json
            output:
              output_file:
                checksum: sha1$47a013e660d408619d894b20806b1d5086aab03b
                class: File
                location: output.txt
                size: 13
            tags:
            - required
            - command_line_tool
            tool: tests/cat5-tool.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test unknown hints are ignored.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.initial_work_dir
    @pytest.mark.inline_javascript
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_2_initial_workdir_secondary_files_expr(self):
        """Test InitialWorkDirRequirement linking input files and capturing secondaryFiles on input and output. Also tests the use of a variety of parameter references and expressions in the secondaryFiles field.

        Generated from::

            id: initial_workdir_secondary_files_expr
            job: tests/search-job.json
            output:
              indexedfile:
                checksum: sha1$327fc7aedf4f6b69a42a7c8b808dc5a7aff61376
                class: File
                location: input.txt
                secondaryFiles:
                - checksum: sha1$1f6fe811644355974cdd06d9eb695d6e859f3b44
                  class: File
                  location: input.txt.idx1
                  size: 1500
                - checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                  class: File
                  location: input.idx2
                  size: 0
                - checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                  class: File
                  location: input.txt.idx3
                  size: 0
                - checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                  class: File
                  location: input.txt.idx4
                  size: 0
                - checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                  class: File
                  location: input.txt.idx5
                  size: 0
                - checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                  class: File
                  location: input.idx6.txt
                  size: 0
                - checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                  class: File
                  location: input.txt.idx7
                  size: 0
                - checksum: sha1$47a013e660d408619d894b20806b1d5086aab03b
                  class: File
                  location: hello.txt
                  size: 13
                - class: Directory
                  listing:
                  - basename: index
                    checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                    class: File
                    location: index
                    size: 0
                  location: input.txt_idx8
                size: 1111
              outfile:
                checksum: sha1$e2dc9daaef945ac15f01c238ed2f1660f60909a0
                class: File
                location: result.txt
                size: 142
            tags:
            - initial_work_dir
            - inline_javascript
            - workflow
            tool: tests/search.cwl#main
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test InitialWorkDirRequirement linking input files and capturing secondaryFiles on input and output. Also tests the use of a variety of parameter references and expressions in the secondaryFiles field.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.initial_work_dir
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_rename(self):
        """Test InitialWorkDirRequirement with expression in filename.

        Generated from::

            id: rename
            job: tests/rename-job.json
            output:
              outfile:
                checksum: sha1$327fc7aedf4f6b69a42a7c8b808dc5a7aff61376
                class: File
                location: fish.txt
                size: 1111
            tags:
            - initial_work_dir
            - command_line_tool
            tool: tests/rename.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test InitialWorkDirRequirement with expression in filename.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.initial_work_dir
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_initial_workdir_trailingnl(self):
        """Test if trailing newline is present in file entry in InitialWorkDir

        Generated from::

            id: initial_workdir_trailingnl
            job: tests/string-job.json
            output:
              out:
                checksum: sha1$6a47aa22b2a9d13a66a24b3ee5eaed95ce4753cf
                class: File
                location: example.conf
                size: 16
            tags:
            - initial_work_dir
            - command_line_tool
            tool: tests/iwdr-entry.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test if trailing newline is present in file entry in InitialWorkDir""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.inline_javascript
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_inline_expressions(self):
        """Test inline expressions

        Generated from::

            id: inline_expressions
            job: tests/wc-job.json
            output:
              output: 16
            tags:
            - inline_javascript
            - command_line_tool
            tool: tests/wc4-tool.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test inline expressions""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.schema_def
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_schemadef_req_tool_param(self):
        """Test SchemaDefRequirement definition used in tool parameter

        Generated from::

            id: schemadef_req_tool_param
            job: tests/schemadef-job.json
            output:
              output:
                checksum: sha1$f12e6cfe70f3253f70b0dbde17c692e7fb0f1e5e
                class: File
                location: output.txt
                size: 12
            tags:
            - schema_def
            - command_line_tool
            tool: tests/schemadef-tool.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test SchemaDefRequirement definition used in tool parameter""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.schema_def
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_2_schemadef_req_wf_param(self):
        """Test SchemaDefRequirement definition used in workflow parameter

        Generated from::

            id: schemadef_req_wf_param
            job: tests/schemadef-job.json
            output:
              output:
                checksum: sha1$f12e6cfe70f3253f70b0dbde17c692e7fb0f1e5e
                class: File
                location: output.txt
                size: 12
            tags:
            - schema_def
            - workflow
            tool: tests/schemadef-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test SchemaDefRequirement definition used in workflow parameter""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_param_evaluation_noexpr(self):
        """Test parameter evaluation, no support for JS expressions

        Generated from::

            id: param_evaluation_noexpr
            job: tests/empty.json
            output:
              t1:
                bar:
                  b az: 2
                  b"az: null
                  b'az: true
                  baz: zab1
                  buz:
                  - a
                  - b
                  - c
              t10: true
              t11: true
              t12: null
              t13: -zab1
              t14: -zab1
              t15: -zab1
              t16: -zab1
              t17: zab1 zab1
              t18: zab1 zab1
              t19: zab1 zab1
              t2:
                b az: 2
                b"az: null
                b'az: true
                baz: zab1
                buz:
                - a
                - b
                - c
              t20: zab1 zab1
              t21: 2 2
              t22: true true
              t23: true true
              t24: null null
              t25: b
              t26: b b
              t27: null
              t28: 3
              t3:
                b az: 2
                b"az: null
                b'az: true
                baz: zab1
                buz:
                - a
                - b
                - c
              t4:
                b az: 2
                b"az: null
                b'az: true
                baz: zab1
                buz:
                - a
                - b
                - c
              t5: zab1
              t6: zab1
              t7: zab1
              t8: zab1
              t9: 2
            tags:
            - required
            - command_line_tool
            tool: tests/params.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test parameter evaluation, no support for JS expressions""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.inline_javascript
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_param_evaluation_expr(self):
        """Test parameter evaluation, with support for JS expressions

        Generated from::

            id: param_evaluation_expr
            job: tests/empty.json
            output:
              t1:
                bar:
                  b az: 2
                  b"az: null
                  b'az: true
                  baz: zab1
                  buz:
                  - a
                  - b
                  - c
              t10: true
              t11: true
              t12: null
              t13: -zab1
              t14: -zab1
              t15: -zab1
              t16: -zab1
              t17: zab1 zab1
              t18: zab1 zab1
              t19: zab1 zab1
              t2:
                b az: 2
                b"az: null
                b'az: true
                baz: zab1
                buz:
                - a
                - b
                - c
              t20: zab1 zab1
              t21: 2 2
              t22: true true
              t23: true true
              t24: null null
              t25: b
              t26: b b
              t27: null
              t28: 3
              t3:
                b az: 2
                b"az: null
                b'az: true
                baz: zab1
                buz:
                - a
                - b
                - c
              t4:
                b az: 2
                b"az: null
                b'az: true
                baz: zab1
                buz:
                - a
                - b
                - c
              t5: zab1
              t6: zab1
              t7: zab1
              t8: zab1
              t9: 2
            tags:
            - inline_javascript
            - command_line_tool
            tool: tests/params2.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test parameter evaluation, with support for JS expressions""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_metadata(self):
        """Test metadata

        Generated from::

            id: metadata
            job: tests/cat-job.json
            output: {}
            tags:
            - required
            - command_line_tool
            tool: tests/metadata.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test metadata""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_format_checking(self):
        """Test simple format checking.

        Generated from::

            id: format_checking
            job: tests/formattest-job.json
            output:
              output:
                checksum: sha1$97fe1b50b4582cebc7d853796ebd62e3e163aa3f
                class: File
                format: http://edamontology.org/format_2330
                location: output.txt
                size: 1111
            tags:
            - required
            - command_line_tool
            tool: tests/formattest.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test simple format checking.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_format_checking_subclass(self):
        """Test format checking against ontology using subclassOf.

        Generated from::

            id: format_checking_subclass
            job: tests/formattest2-job.json
            output:
              output:
                checksum: sha1$971d88faeda85a796752ecf752b7e2e34f1337ce
                class: File
                format: http://edamontology.org/format_1929
                location: output.txt
                size: 12010
            tags:
            - required
            - command_line_tool
            tool: tests/formattest2.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test format checking against ontology using subclassOf.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_format_checking_equivalentclass(self):
        """Test format checking against ontology using equivalentClass.

        Generated from::

            id: format_checking_equivalentclass
            job: tests/formattest2-job.json
            output:
              output:
                checksum: sha1$971d88faeda85a796752ecf752b7e2e34f1337ce
                class: File
                format: http://edamontology.org/format_1929
                location: output.txt
                size: 12010
            tags:
            - required
            - command_line_tool
            tool: tests/formattest3.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test format checking against ontology using equivalentClass.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.docker
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_output_secondaryfile_optional(self):
        """Test optional output file and optional secondaryFile on output.

        Generated from::

            id: output_secondaryfile_optional
            job: tests/cat-job.json
            output:
              optional_file: null
              output_file:
                checksum: sha1$47a013e660d408619d894b20806b1d5086aab03b
                class: File
                location: output.txt
                size: 13
            tags:
            - docker
            - command_line_tool
            tool: tests/optional-output.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test optional output file and optional secondaryFile on output.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.inline_javascript
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_valuefrom_ignored_null(self):
        """Test that valueFrom is ignored when the parameter is null

        Generated from::

            id: valuefrom_ignored_null
            job: tests/empty.json
            output:
              out: '
            
                '
            tags:
            - inline_javascript
            - command_line_tool
            tool: tests/vf-concat.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test that valueFrom is ignored when the parameter is null""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.inline_javascript
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_valuefrom_secondexpr_ignored(self):
        """Test that second expression in concatenated valueFrom is not ignored

        Generated from::

            id: valuefrom_secondexpr_ignored
            job: tests/cat-job.json
            output:
              out: 'a string
            
                '
            tags:
            - inline_javascript
            - command_line_tool
            tool: tests/vf-concat.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test that second expression in concatenated valueFrom is not ignored""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.step_input
    @pytest.mark.inline_javascript
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_2_valuefrom_wf_step(self):
        """Test valueFrom on workflow step.

        Generated from::

            id: valuefrom_wf_step
            job: tests/step-valuefrom-wf.json
            output:
              count_output: 16
            tags:
            - step_input
            - inline_javascript
            - workflow
            tool: tests/step-valuefrom-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test valueFrom on workflow step.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.step_input
    @pytest.mark.inline_javascript
    @pytest.mark.multiple_input
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_2_valuefrom_wf_step_multiple(self):
        """Test valueFrom on workflow step with multiple sources

        Generated from::

            id: valuefrom_wf_step_multiple
            job: tests/step-valuefrom-job.json
            output:
              val: '3
            
                '
            tags:
            - step_input
            - inline_javascript
            - multiple_input
            - workflow
            tool: tests/step-valuefrom2-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test valueFrom on workflow step with multiple sources""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.step_input
    @pytest.mark.inline_javascript
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_2_valuefrom_wf_step_other(self):
        """Test valueFrom on workflow step referencing other inputs

        Generated from::

            id: valuefrom_wf_step_other
            job: tests/step-valuefrom-job.json
            output:
              val: '3
            
                '
            tags:
            - step_input
            - inline_javascript
            - workflow
            tool: tests/step-valuefrom3-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test valueFrom on workflow step referencing other inputs""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.shell_command
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_record_output_binding(self):
        """Test record type output binding.

        Generated from::

            id: record_output_binding
            job: tests/record-output-job.json
            output:
              orec:
                obar:
                  checksum: sha1$aeb3d11bdf536511649129f4077d5cda6a324118
                  class: File
                  location: bar
                  size: 12010
                ofoo:
                  checksum: sha1$327fc7aedf4f6b69a42a7c8b808dc5a7aff61376
                  class: File
                  location: foo
                  size: 1111
            tags:
            - shell_command
            - command_line_tool
            tool: tests/record-output.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test record type output binding.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.shell_command
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_docker_json_output_path(self):
        """Test support for reading cwl.output.json when running in a Docker container and just 'path' is provided.

        Generated from::

            id: docker_json_output_path
            job: tests/empty.json
            output:
              foo:
                checksum: sha1$f1d2d2f924e986ac86fdf7b36c94bcdf32beec15
                class: File
                location: foo
                size: 4
            tags:
            - shell_command
            - command_line_tool
            tool: tests/test-cwl-out.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test support for reading cwl.output.json when running in a Docker container and just 'path' is provided.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.shell_command
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_docker_json_output_location(self):
        """Test support for reading cwl.output.json when running in a Docker container and just 'location' is provided.

        Generated from::

            id: docker_json_output_location
            job: tests/empty.json
            output:
              foo:
                checksum: sha1$f1d2d2f924e986ac86fdf7b36c94bcdf32beec15
                class: File
                location: foo
                size: 4
            tags:
            - shell_command
            - command_line_tool
            tool: tests/test-cwl-out2.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test support for reading cwl.output.json when running in a Docker container and just 'location' is provided.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_json_output_path_relative(self):
        """Test support for reading cwl.output.json where 'path' is relative path in output dir.

        Generated from::

            id: json_output_path_relative
            job: tests/empty.json
            output:
              foo:
                checksum: sha1$f1d2d2f924e986ac86fdf7b36c94bcdf32beec15
                class: File
                location: foo
                size: 4
            tags:
            - required
            - command_line_tool
            tool: tests/test-cwl-out3.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test support for reading cwl.output.json where 'path' is relative path in output dir.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_json_output_location_relative(self):
        """Test support for reading cwl.output.json where 'location' is relative reference to output dir.

        Generated from::

            id: json_output_location_relative
            job: tests/empty.json
            output:
              foo:
                checksum: sha1$f1d2d2f924e986ac86fdf7b36c94bcdf32beec15
                class: File
                location: foo
                size: 4
            tags:
            - required
            - command_line_tool
            tool: tests/test-cwl-out4.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test support for reading cwl.output.json where 'location' is relative reference to output dir.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_multiple_glob_expr_list(self):
        """Test support for returning multiple glob patterns from expression

        Generated from::

            id: multiple_glob_expr_list
            job: tests/abc.json
            output:
              files:
              - checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                class: File
                location: a
                size: 0
              - checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                class: File
                location: b
                size: 0
              - checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                class: File
                location: c
                size: 0
            tags:
            - required
            - command_line_tool
            tool: tests/glob-expr-list.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test support for returning multiple glob patterns from expression""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.scatter
    @pytest.mark.step_input
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_2_wf_scatter_oneparam_valuefrom(self):
        """Test workflow scatter with single scatter parameter and two valueFrom on step input (first and current el)

        Generated from::

            id: wf_scatter_oneparam_valuefrom
            job: tests/scatter-valuefrom-job1.json
            output:
              out:
              - foo one one
              - foo one two
              - foo one three
              - foo one four
            tags:
            - scatter
            - step_input
            - workflow
            tool: tests/scatter-valuefrom-wf1.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test workflow scatter with single scatter parameter and two valueFrom on step input (first and current el)""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.scatter
    @pytest.mark.step_input
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_2_wf_scatter_twoparam_nested_crossproduct_valuefrom(self):
        """Test workflow scatter with two scatter parameters and nested_crossproduct join method and valueFrom on step input

        Generated from::

            id: wf_scatter_twoparam_nested_crossproduct_valuefrom
            job: tests/scatter-valuefrom-job2.json
            output:
              out:
              - - foo one one three
                - foo one one four
              - - foo one two three
                - foo one two four
            tags:
            - scatter
            - step_input
            - workflow
            tool: tests/scatter-valuefrom-wf2.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test workflow scatter with two scatter parameters and nested_crossproduct join method and valueFrom on step input""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.scatter
    @pytest.mark.step_input
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_2_wf_scatter_twoparam_flat_crossproduct_valuefrom(self):
        """Test workflow scatter with two scatter parameters and flat_crossproduct join method and valueFrom on step input

        Generated from::

            id: wf_scatter_twoparam_flat_crossproduct_valuefrom
            job: tests/scatter-valuefrom-job2.json
            output:
              out:
              - foo one one three
              - foo one one four
              - foo one two three
              - foo one two four
            tags:
            - scatter
            - step_input
            - workflow
            tool: tests/scatter-valuefrom-wf3.cwl#main
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test workflow scatter with two scatter parameters and flat_crossproduct join method and valueFrom on step input""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.scatter
    @pytest.mark.step_input
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_2_wf_scatter_twoparam_dotproduct_valuefrom(self):
        """Test workflow scatter with two scatter parameters and dotproduct join method and valueFrom on step input

        Generated from::

            id: wf_scatter_twoparam_dotproduct_valuefrom
            job: tests/scatter-valuefrom-job2.json
            output:
              out:
              - foo one one three
              - foo one two four
            tags:
            - scatter
            - step_input
            - workflow
            tool: tests/scatter-valuefrom-wf4.cwl#main
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test workflow scatter with two scatter parameters and dotproduct join method and valueFrom on step input""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.scatter
    @pytest.mark.step_input
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_2_wf_scatter_oneparam_valuefrom_twice_current_el(self):
        """Test workflow scatter with single scatter parameter and two valueFrom on step input (current el twice)

        Generated from::

            id: wf_scatter_oneparam_valuefrom_twice_current_el
            job: tests/scatter-valuefrom-job1.json
            output:
              out:
              - foo one one
              - foo two two
              - foo three three
              - foo four four
            tags:
            - scatter
            - step_input
            - workflow
            tool: tests/scatter-valuefrom-wf5.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test workflow scatter with single scatter parameter and two valueFrom on step input (current el twice)""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.scatter
    @pytest.mark.step_input
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_2_wf_scatter_oneparam_valueFrom(self):
        """Test valueFrom eval on scattered input parameter

        Generated from::

            id: wf_scatter_oneparam_valueFrom
            job: tests/scatter-valuefrom-job3.json
            output:
              out_message:
              - checksum: sha1$98030575f6fc40e5021be5a8803a6bef94aee11f
                class: File
                location: Any
                size: 16
              - checksum: sha1$edcacd50778d98ae113015406b3195c165059dd8
                class: File
                location: Any
                size: 16
            tags:
            - scatter
            - step_input
            - workflow
            tool: tests/scatter-valuefrom-wf6.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test valueFrom eval on scattered input parameter""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_2_wf_two_inputfiles_namecollision(self):
        """Test workflow two input files with same name.

        Generated from::

            id: wf_two_inputfiles_namecollision
            job: tests/conflict-job.json
            output:
              fileout:
                checksum: sha1$a2d8d6e7b28295dc9977dc3bdb652ddd480995f0
                class: File
                location: out.txt
                size: 25
            tags:
            - required
            - workflow
            tool: tests/conflict-wf.cwl#collision
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test workflow two input files with same name.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.shell_command
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_directory_input_param_ref(self):
        """Test directory input with parameter reference

        Generated from::

            id: directory_input_param_ref
            job: tests/dir-job.yml
            output:
              outlist:
                checksum: sha1$13cda8661796ae241da3a18668fb552161a72592
                class: File
                location: output.txt
                size: 20
            tags:
            - shell_command
            - command_line_tool
            tool: tests/dir.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test directory input with parameter reference""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.shell_command
    @pytest.mark.green
    def test_conformance_v1_2_directory_input_docker(self):
        """Test directory input in Docker

        Generated from::

            id: directory_input_docker
            job: tests/dir-job.yml
            output:
              outlist:
                checksum: sha1$13cda8661796ae241da3a18668fb552161a72592
                class: File
                location: output.txt
                size: 20
            tags:
            - command_line_tool
            - shell_command
            tool: tests/dir2.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test directory input in Docker""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_directory_output(self):
        """Test directory output

        Generated from::

            id: directory_output
            job: tests/dir3-job.yml
            output:
              outdir:
                class: Directory
                listing:
                - checksum: sha1$dd0a4c4c49ba43004d6611771972b6cf969c1c01
                  class: File
                  location: goodbye.txt
                  size: 24
                - checksum: sha1$47a013e660d408619d894b20806b1d5086aab03b
                  class: File
                  location: hello.txt
                  size: 13
            tags:
            - required
            - command_line_tool
            tool: tests/dir3.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test directory output""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.shell_command
    @pytest.mark.command_line_tool
    @pytest.mark.red
    def test_conformance_v1_2_directory_secondaryfiles(self):
        """Test directories in secondaryFiles

        Generated from::

            id: directory_secondaryfiles
            job: tests/dir4-job.yml
            output:
              outlist:
                checksum: sha1$13cda8661796ae241da3a18668fb552161a72592
                class: File
                location: output.txt
                size: 20
            tags:
            - shell_command
            - command_line_tool
            tool: tests/dir4.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test directories in secondaryFiles""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.shell_command
    @pytest.mark.initial_work_dir
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_dynamic_initial_workdir(self):
        """Test dynamic initial work dir

        Generated from::

            id: dynamic_initial_workdir
            job: tests/dir-job.yml
            output:
              outlist:
                checksum: sha1$13cda8661796ae241da3a18668fb552161a72592
                class: File
                location: output.txt
                size: 20
            tags:
            - shell_command
            - initial_work_dir
            - command_line_tool
            tool: tests/dir5.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test dynamic initial work dir""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.initial_work_dir
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_writable_stagedfiles(self):
        """Test writable staged files.

        Generated from::

            id: writable_stagedfiles
            job: tests/stagefile-job.yml
            output:
              outfile:
                checksum: sha1$b769c7b2e316edd4b5eb2d24799b2c1f9d8c86e6
                class: File
                location: bob.txt
                size: 1111
            tags:
            - initial_work_dir
            - command_line_tool
            tool: tests/stagefile.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test writable staged files.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_input_file_literal(self):
        """Test file literal as input

        Generated from::

            id: input_file_literal
            job: tests/file-literal.yml
            output:
              output_file:
                checksum: sha1$d0e04ff6c413c7d57f9a0ca0a33cd3ab52e2dd9c
                class: File
                location: output.txt
                size: 18
            tags:
            - required
            - command_line_tool
            tool: tests/cat3-tool.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test file literal as input""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.initial_work_dir
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_initial_workdir_expr(self):
        """Test expression in InitialWorkDir listing

        Generated from::

            id: initial_workdir_expr
            job: tests/arguments-job.yml
            output:
              classfile:
                checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                class: File
                location: Hello.class
                size: 0
            tags:
            - initial_work_dir
            - command_line_tool
            tool: tests/linkfile.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test expression in InitialWorkDir listing""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_nameroot_nameext_stdout_expr(self):
        """Test nameroot/nameext expression in arguments, stdout

        Generated from::

            id: nameroot_nameext_stdout_expr
            job: tests/wc-job.json
            output:
              b:
                checksum: sha1$c4cfd130e7578714e3eef91c1d6d90e0e0b9db3e
                class: File
                location: whale.xtx
                size: 21
            tags:
            - required
            - command_line_tool
            tool: tests/nameroot.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test nameroot/nameext expression in arguments, stdout""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.shell_command
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_input_dir_inputbinding(self):
        """Test directory input with inputBinding

        Generated from::

            id: input_dir_inputbinding
            job: tests/dir-job.yml
            output:
              outlist:
                checksum: sha1$13cda8661796ae241da3a18668fb552161a72592
                class: File
                location: output.txt
                size: 20
            tags:
            - shell_command
            - command_line_tool
            tool: tests/dir6.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test directory input with inputBinding""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_cl_gen_arrayofarrays(self):
        """Test command line generation of array-of-arrays

        Generated from::

            id: cl_gen_arrayofarrays
            job: tests/nested-array-job.yml
            output:
              echo:
                checksum: sha1$3f786850e387550fdab836ed7e6dc881de23001b
                class: File
                location: echo.txt
                size: 2
            tags:
            - required
            - command_line_tool
            tool: tests/nested-array.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test command line generation of array-of-arrays""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.shell_command
    @pytest.mark.command_line_tool
    @pytest.mark.red
    def test_conformance_v1_2_env_home_tmpdir(self):
        """Test $HOME and $TMPDIR are set correctly

        Generated from::

            id: env_home_tmpdir
            job: tests/empty.json
            output: {}
            tags:
            - shell_command
            - command_line_tool
            tool: tests/envvar.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test $HOME and $TMPDIR are set correctly""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.shell_command
    @pytest.mark.command_line_tool
    @pytest.mark.red
    def test_conformance_v1_2_env_home_tmpdir_docker(self):
        """Test $HOME and $TMPDIR are set correctly in Docker

        Generated from::

            id: env_home_tmpdir_docker
            job: tests/empty.json
            output: {}
            tags:
            - shell_command
            - command_line_tool
            tool: tests/envvar2.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test $HOME and $TMPDIR are set correctly in Docker""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.inline_javascript
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_2_expressionlib_tool_wf_override(self):
        """Test that expressionLib requirement of individual tool step overrides expressionLib of workflow.

        Generated from::

            id: expressionlib_tool_wf_override
            job: tests/empty.json
            output:
              out:
                checksum: sha1$7448d8798a4380162d4b56f9b452e2f6f9e24e7a
                class: File
                location: whatever.txt
                size: 2
            tags:
            - inline_javascript
            - workflow
            tool: tests/js-expr-req-wf.cwl#wf
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test that expressionLib requirement of individual tool step overrides expressionLib of workflow.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.docker
    @pytest.mark.initial_work_dir
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_initial_workdir_output(self):
        """Test output of InitialWorkDir

        Generated from::

            id: initial_workdir_output
            job: tests/initialworkdirrequirement-docker-out-job.json
            output:
              OUTPUT:
                checksum: sha1$aeb3d11bdf536511649129f4077d5cda6a324118
                class: File
                location: ref.fasta
                secondaryFiles:
                - checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                  class: File
                  location: ref.fasta.fai
                  size: 0
                size: 12010
            tags:
            - docker
            - initial_work_dir
            - command_line_tool
            tool: tests/initialworkdirrequirement-docker-out.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test output of InitialWorkDir""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.subworkflow
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_2_embedded_subworkflow(self):
        """Test embedded subworkflow

        Generated from::

            id: embedded_subworkflow
            job: tests/wc-job.json
            output:
              count_output: 16
            tags:
            - subworkflow
            - workflow
            tool: tests/count-lines10-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test embedded subworkflow""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.docker
    @pytest.mark.inline_javascript
    @pytest.mark.shell_command
    @pytest.mark.command_line_tool
    @pytest.mark.red
    def test_conformance_v1_2_filesarray_secondaryfiles(self):
        """Test required, optional and null secondaryFiles on array of files.

        Generated from::

            id: filesarray_secondaryfiles
            job: tests/docker-array-secondaryfiles-job.json
            output:
              bai_list:
                checksum: sha1$081fc0e57d6efa5f75eeb237aab1d04031132be6
                class: File
                location: fai.list
                size: 386
            tags:
            - docker
            - inline_javascript
            - shell_command
            - command_line_tool
            tool: tests/docker-array-secondaryfiles.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test required, optional and null secondaryFiles on array of files.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.docker
    @pytest.mark.inline_javascript
    @pytest.mark.shell_command
    @pytest.mark.command_line_tool
    @pytest.mark.inputs_should_parse
    @pytest.mark.red
    def test_conformance_v1_2_filesarray_secondaryfiles2(self):
        """Test required, optional and null secondaryFiles on array of files.

        Generated from::

            id: filesarray_secondaryfiles2
            job: tests/docker-array-secondaryfiles-job2.json
            should_fail: true
            tags:
            - docker
            - inline_javascript
            - shell_command
            - command_line_tool
            - inputs_should_parse
            tool: tests/docker-array-secondaryfiles.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test required, optional and null secondaryFiles on array of files.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.inline_javascript
    @pytest.mark.expression_tool
    @pytest.mark.green
    def test_conformance_v1_2_exprtool_directory_literal(self):
        """Test directory literal output created by ExpressionTool

        Generated from::

            id: exprtool_directory_literal
            job: tests/dir7.yml
            output:
              dir:
                class: Directory
                listing:
                - checksum: sha1$327fc7aedf4f6b69a42a7c8b808dc5a7aff61376
                  class: File
                  location: whale.txt
                  size: 1111
                - checksum: sha1$47a013e660d408619d894b20806b1d5086aab03b
                  class: File
                  location: hello.txt
                  size: 13
                location: a_directory
            tags:
            - inline_javascript
            - expression_tool
            tool: tests/dir7.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test directory literal output created by ExpressionTool""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.inline_javascript
    @pytest.mark.expression_tool
    @pytest.mark.green
    def test_conformance_v1_2_exprtool_file_literal(self):
        """Test file literal output created by ExpressionTool

        Generated from::

            id: exprtool_file_literal
            job: tests/empty.json
            output:
              lit:
                checksum: sha1$fea23663b9c8ed71968f86415b5ec091bb111448
                class: File
                location: a_file
                size: 19
            tags:
            - inline_javascript
            - expression_tool
            tool: tests/file-literal-ex.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test file literal output created by ExpressionTool""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.docker
    @pytest.mark.command_line_tool
    @pytest.mark.red
    def test_conformance_v1_2_dockeroutputdir(self):
        """Test dockerOutputDirectory

        Generated from::

            id: dockeroutputdir
            job: tests/empty.json
            output:
              thing:
                checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                class: File
                location: thing
                size: 0
            tags:
            - docker
            - command_line_tool
            tool: tests/docker-output-dir.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test dockerOutputDirectory""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_hints_import(self):
        """Test hints with $import

        Generated from::

            id: hints_import
            job: tests/empty.json
            output:
              out:
                checksum: sha1$b3ec4ed1749c207e52b3a6d08c59f31d83bff519
                class: File
                location: out
                size: 15
            tags:
            - required
            - command_line_tool
            tool: tests/imported-hint.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test hints with $import""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_default_path_notfound_warning(self):
        """Test warning instead of error when default path is not found

        Generated from::

            id: default_path_notfound_warning
            job: tests/default_path_job.yml
            output: {}
            tags:
            - required
            - command_line_tool
            tool: tests/default_path.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test warning instead of error when default path is not found""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.inline_javascript
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_inlinejs_req_expressions(self):
        """Test InlineJavascriptRequirement with multiple expressions in the same tool

        Generated from::

            id: inlinejs_req_expressions
            job: tests/empty.json
            output:
              args:
              - -A
              - '2'
              - -B
              - baz
              - -C
              - '10'
              - '9'
              - '8'
              - '7'
              - '6'
              - '5'
              - '4'
              - '3'
              - '2'
              - '1'
              - -D
            tags:
            - inline_javascript
            - command_line_tool
            tool: tests/inline-js.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test InlineJavascriptRequirement with multiple expressions in the same tool""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.initial_work_dir
    @pytest.mark.shell_command
    @pytest.mark.command_line_tool
    @pytest.mark.red
    def test_conformance_v1_2_input_dir_recurs_copy_writable(self):
        """Test if a writable input directory is recursively copied and writable

        Generated from::

            id: input_dir_recurs_copy_writable
            job: tests/recursive-input-directory.yml
            output:
              output_dir:
                basename: work_dir
                class: Directory
                listing:
                - basename: a
                  checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                  class: File
                  location: work_dir/a
                  size: 0
                - basename: b
                  checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                  class: File
                  location: work_dir/b
                  size: 0
                - basename: c
                  class: Directory
                  listing:
                  - basename: d
                    checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                    class: File
                    location: work_dir/c/d
                    size: 0
                  location: work_dir/c
                - basename: e
                  checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                  class: File
                  location: work_dir/e
                  size: 0
                location: work_dir
              test_result:
                checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                class: File
                location: output.txt
                size: 0
            tags:
            - initial_work_dir
            - shell_command
            - command_line_tool
            tool: tests/recursive-input-directory.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test if a writable input directory is recursively copied and writable""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.inline_javascript
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_null_missing_params(self):
        """Test that missing parameters are null (not undefined) in expression

        Generated from::

            id: null_missing_params
            job: tests/empty.json
            output:
              out: 't
            
                '
            tags:
            - inline_javascript
            - command_line_tool
            tool: tests/null-defined.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test that missing parameters are null (not undefined) in expression""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.inline_javascript
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_param_notnull_expr(self):
        """Test that provided parameter is not null in expression

        Generated from::

            id: param_notnull_expr
            job: tests/cat-job.json
            output:
              out: 'f
            
                '
            tags:
            - inline_javascript
            - command_line_tool
            tool: tests/null-defined.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test that provided parameter is not null in expression""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_2_wf_compound_doc(self):
        """Test compound workflow document

        Generated from::

            id: wf_compound_doc
            job: tests/revsort-job.json
            output:
              output:
                checksum: sha1$b9214658cc453331b62c2282b772a5c063dbd284
                class: File
                location: output.txt
                size: 1111
            tags:
            - required
            - workflow
            tool: tests/revsort-packed.cwl#main
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test compound workflow document""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.step_input
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_2_nameroot_nameext_generated(self):
        """Test that nameroot and nameext are generated from basename at execution time by the runner

        Generated from::

            id: nameroot_nameext_generated
            job: tests/basename-fields-job.yml
            output:
              extFile:
                checksum: sha1$301a72c82a835e1737caf30f94d0eec210c4d9f1
                class: File
                location: Any
                path: Any
                size: 5
              rootFile:
                checksum: sha1$b4a583c391e234cf210e1d576f68f674c8ad7ecd
                class: File
                location: Any
                path: Any
                size: 10
            tags:
            - step_input
            - workflow
            tool: tests/basename-fields-test.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test that nameroot and nameext are generated from basename at execution time by the runner""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.initial_work_dir
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_initialworkpath_output(self):
        """Test that file path in $(inputs) for initialworkdir is in $(outdir).

        Generated from::

            id: initialworkpath_output
            job: tests/wc-job.json
            output: {}
            tags:
            - initial_work_dir
            - command_line_tool
            tool: tests/initialwork-path.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test that file path in $(inputs) for initialworkdir is in $(outdir).""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.multiple_input
    @pytest.mark.inline_javascript
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_2_wf_scatter_twopar_oneinput_flattenedmerge(self):
        """Test single step workflow with Scatter step and two data links connected to same input, flattened merge behavior. Workflow inputs are set as list

        Generated from::

            id: wf_scatter_twopar_oneinput_flattenedmerge
            job: tests/count-lines6-job.json
            output:
              count_output: 34
            tags:
            - multiple_input
            - inline_javascript
            - workflow
            tool: tests/count-lines12-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test single step workflow with Scatter step and two data links connected to same input, flattened merge behavior. Workflow inputs are set as list""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.step_input
    @pytest.mark.inline_javascript
    @pytest.mark.multiple_input
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_2_wf_multiplesources_multipletypes(self):
        """Test step input with multiple sources with multiple types

        Generated from::

            id: wf_multiplesources_multipletypes
            job: tests/sum-job.json
            output:
              result: 12
            tags:
            - step_input
            - inline_javascript
            - multiple_input
            - workflow
            tool: tests/sum-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test step input with multiple sources with multiple types""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_shelldir_notinterpreted(self):
        """Test that shell directives are not interpreted.

        Generated from::

            id: shelldir_notinterpreted
            job: tests/empty.json
            output:
              stderr_file:
                checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                class: File
                location: Any
                size: 0
              stdout_file:
                checksum: sha1$1555252d52d4ec3262538a4426a83a99cfff4402
                class: File
                location: Any
                size: 9
            tags:
            - required
            - command_line_tool
            tool: tests/shellchar.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test that shell directives are not interpreted.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.shell_command
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_shelldir_quoted(self):
        """Test that shell directives are quoted.

        Generated from::

            id: shelldir_quoted
            job: tests/empty.json
            output:
              stderr_file:
                checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                class: File
                location: Any
                size: 0
              stdout_file:
                checksum: sha1$1555252d52d4ec3262538a4426a83a99cfff4402
                class: File
                location: Any
                size: 9
            tags:
            - shell_command
            - command_line_tool
            tool: tests/shellchar2.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test that shell directives are quoted.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.inline_javascript
    @pytest.mark.initial_work_dir
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_initial_workdir_empty_writable(self):
        """Test empty writable dir with InitialWorkDirRequirement

        Generated from::

            id: initial_workdir_empty_writable
            job: tests/empty.json
            output:
              out:
                basename: emptyWritableDir
                class: Directory
                listing:
                - basename: blurg
                  checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                  class: File
                  location: blurg
                  size: 0
                location: emptyWritableDir
            tags:
            - inline_javascript
            - initial_work_dir
            - command_line_tool
            tool: tests/writable-dir.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test empty writable dir with InitialWorkDirRequirement""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.inline_javascript
    @pytest.mark.initial_work_dir
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_initial_workdir_empty_writable_docker(self):
        """Test empty writable dir with InitialWorkDirRequirement inside Docker

        Generated from::

            id: initial_workdir_empty_writable_docker
            job: tests/empty.json
            output:
              out:
                basename: emptyWritableDir
                class: Directory
                listing:
                - basename: blurg
                  checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                  class: File
                  location: blurg
                  size: 0
                location: emptyWritableDir
            tags:
            - inline_javascript
            - initial_work_dir
            - command_line_tool
            tool: tests/writable-dir-docker.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test empty writable dir with InitialWorkDirRequirement inside Docker""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.resource
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_dynamic_resreq_inputs(self):
        """Test dynamic resource reqs referencing inputs

        Generated from::

            id: dynamic_resreq_inputs
            job: tests/dynresreq-job.yaml
            output:
              output:
                checksum: sha1$7448d8798a4380162d4b56f9b452e2f6f9e24e7a
                class: File
                location: cores.txt
                size: 2
            tags:
            - resource
            - command_line_tool
            tool: tests/dynresreq.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test dynamic resource reqs referencing inputs""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_fileliteral_input_docker(self):
        """Test file literal as input without Docker

        Generated from::

            id: fileliteral_input_docker
            job: tests/file-literal.yml
            output:
              output_file:
                checksum: sha1$d0e04ff6c413c7d57f9a0ca0a33cd3ab52e2dd9c
                class: File
                location: output.txt
                size: 18
            tags:
            - required
            - command_line_tool
            tool: tests/cat3-nodocker.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test file literal as input without Docker""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_outputbinding_glob_sorted(self):
        """Test that OutputBinding.glob is sorted as specified by POSIX

        Generated from::

            id: outputbinding_glob_sorted
            job: tests/empty.json
            output:
              letters:
              - checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                class: File
                location: a
                size: 0
              - checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                class: File
                location: b
                size: 0
              - checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                class: File
                location: c
                size: 0
              - checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                class: File
                location: w
                size: 0
              - checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                class: File
                location: x
                size: 0
              - checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                class: File
                location: y
                size: 0
              - checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                class: File
                location: z
                size: 0
            tags:
            - required
            - command_line_tool
            tool: tests/glob_test.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test that OutputBinding.glob is sorted as specified by POSIX""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.initial_work_dir
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_2_initialworkdir_nesteddir(self):
        """Test InitialWorkDirRequirement with a nested directory structure from another step

        Generated from::

            id: initialworkdir_nesteddir
            job: tests/empty.json
            output:
              ya_empty:
                checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                class: File
                location: ya
                size: 0
            tags:
            - initial_work_dir
            - workflow
            tool: tests/iwdr_with_nested_dirs.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test InitialWorkDirRequirement with a nested directory structure from another step""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_booleanflags_cl_noinputbinding(self):
        """Test that boolean flags do not appear on command line if inputBinding is empty and not null

        Generated from::

            id: booleanflags_cl_noinputbinding
            job: tests/bool-empty-inputbinding-job.json
            output:
              args: []
            tags:
            - required
            - command_line_tool
            tool: tests/bool-empty-inputbinding.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test that boolean flags do not appear on command line if inputBinding is empty and not null""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_expr_reference_self_noinput(self):
        """Test that expression engine does not fail to evaluate reference to self with unprovided input

        Generated from::

            id: expr_reference_self_noinput
            job: tests/empty.json
            output:
              args: []
            tags:
            - required
            - command_line_tool
            tool: tests/stage-unprovided-file.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test that expression engine does not fail to evaluate reference to self with unprovided input""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_success_codes(self):
        """Test successCodes

        Generated from::

            id: success_codes
            job: tests/empty.json
            output: {}
            tags:
            - required
            - command_line_tool
            tool: tests/exit-success.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test successCodes""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.resource
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_2_dynamic_resreq_wf(self):
        """Test simple workflow with a dynamic resource requirement

        Generated from::

            id: dynamic_resreq_wf
            job: tests/dynresreq-job.yaml
            output:
              cores:
                checksum: sha1$7448d8798a4380162d4b56f9b452e2f6f9e24e7a
                class: File
                location: output
                size: 2
            tags:
            - resource
            - workflow
            tool: tests/dynresreq-workflow.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test simple workflow with a dynamic resource requirement""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_cl_empty_array_input(self):
        """Test that empty array input does not add anything to command line

        Generated from::

            id: cl_empty_array_input
            job: tests/empty-array-job.json
            output:
              args: []
            tags:
            - required
            - command_line_tool
            tool: tests/empty-array-input.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test that empty array input does not add anything to command line""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.resource
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_2_resreq_step_overrides_wf(self):
        """Test that ResourceRequirement on a step level redefines requirement on the workflow level

        Generated from::

            id: resreq_step_overrides_wf
            job: tests/empty.json
            output:
              out:
                checksum: sha1$e5fa44f2b31c1fb553b6021e7360d07d5d91ff5e
                class: File
                location: cores.txt
                size: 2
            tags:
            - resource
            - workflow
            tool: tests/steplevel-resreq.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test that ResourceRequirement on a step level redefines requirement on the workflow level""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_valuefrom_constant_overrides_inputs(self):
        """Test valueFrom with constant value overriding provided array inputs

        Generated from::

            id: valuefrom_constant_overrides_inputs
            job: tests/array-of-strings-job.yml
            output:
              args:
              - replacementValue
            tags:
            - required
            - command_line_tool
            tool: tests/valueFrom-constant.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test valueFrom with constant value overriding provided array inputs""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.resource
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_dynamic_resreq_filesizes(self):
        """Test dynamic resource reqs referencing the size of Files inside a Directory

        Generated from::

            id: dynamic_resreq_filesizes
            job: tests/dynresreq-dir-job.yaml
            output:
              output:
                checksum: sha1$7448d8798a4380162d4b56f9b452e2f6f9e24e7a
                class: File
                location: cores.txt
                size: 2
            tags:
            - resource
            - command_line_tool
            tool: tests/dynresreq-dir.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test dynamic resource reqs referencing the size of Files inside a Directory""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_2_wf_step_connect_undeclared_param(self):
        """Test that it is not an error to connect a parameter to a workflow step, even if the parameter doesn't appear in the `run` process inputs.

        Generated from::

            id: wf_step_connect_undeclared_param
            job: tests/empty.json
            output:
              out: 'hello inp1
            
                '
            tags:
            - required
            - workflow
            tool: tests/pass-unconnected.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test that it is not an error to connect a parameter to a workflow step, even if the parameter doesn't appear in the `run` process inputs.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.workflow
    @pytest.mark.inputs_should_parse
    @pytest.mark.green
    def test_conformance_v1_2_wf_step_access_undeclared_param(self):
        """Test that parameters that don't appear in the `run` process inputs are not present in the input object used to run the tool.

        Generated from::

            id: wf_step_access_undeclared_param
            job: tests/empty.json
            should_fail: true
            tags:
            - required
            - workflow
            - inputs_should_parse
            tool: tests/fail-unconnected.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test that parameters that don't appear in the `run` process inputs are not present in the input object used to run the tool.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.shell_command
    @pytest.mark.command_line_tool
    @pytest.mark.red
    def test_conformance_v1_2_env_home_tmpdir_docker_no_return_code(self):
        """Test $HOME and $TMPDIR are set correctly in Docker without using return code

        Generated from::

            id: env_home_tmpdir_docker_no_return_code
            job: tests/empty.json
            output:
              results:
                basename: results
                checksum: sha1$7d5ca8c0c03e883c56c4eb1ef6f6bb9bccad4d86
                class: File
                size: 8
            tags:
            - shell_command
            - command_line_tool
            tool: tests/envvar3.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test $HOME and $TMPDIR are set correctly in Docker without using return code""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.scatter
    @pytest.mark.step_input
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_2_wf_scatter_oneparam_valuefrom_inputs(self):
        """Test workflow scatter with single scatter parameter and two valueFrom using $inputs (first and current el)

        Generated from::

            id: wf_scatter_oneparam_valuefrom_inputs
            job: tests/scatter-valuefrom-job1.json
            output:
              out:
              - foo one one
              - foo one two
              - foo one three
              - foo one four
            tags:
            - scatter
            - step_input
            - workflow
            tool: tests/scatter-valuefrom-inputs-wf1.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test workflow scatter with single scatter parameter and two valueFrom using $inputs (first and current el)""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.schema_def
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_2_packed_import_schema(self):
        """SchemaDefRequirement with $import, and packed

        Generated from::

            id: packed_import_schema
            job: tests/import_schema-def_job.yml
            output:
              output_bam:
                basename: a.bam
                checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                class: File
                size: 0
            tags:
            - schema_def
            - workflow
            tool: tests/import_schema-def_packed.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """SchemaDefRequirement with $import, and packed""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.shell_command
    @pytest.mark.command_line_tool
    @pytest.mark.red
    def test_conformance_v1_2_job_input_secondary_subdirs(self):
        """Test specifying secondaryFiles in subdirectories of the job input document.

        Generated from::

            id: job_input_secondary_subdirs
            job: tests/dir4-subdir-1-job.yml
            output:
              outlist:
                checksum: sha1$9d9bc8f5252d39274b5dfbac64216c6e888f5dfc
                class: File
                location: output.txt
                size: 14
            tags:
            - shell_command
            - command_line_tool
            tool: tests/dir4.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test specifying secondaryFiles in subdirectories of the job input document.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.shell_command
    @pytest.mark.command_line_tool
    @pytest.mark.red
    def test_conformance_v1_2_job_input_subdir_primary_and_secondary_subdirs(self):
        """Test specifying secondaryFiles in same subdirectory of the job input as the primary input file.

        Generated from::

            id: job_input_subdir_primary_and_secondary_subdirs
            job: tests/dir4-subdir-2-job.yml
            output:
              outlist:
                checksum: sha1$9d9bc8f5252d39274b5dfbac64216c6e888f5dfc
                class: File
                location: output.txt
                size: 14
            tags:
            - shell_command
            - command_line_tool
            tool: tests/dir4.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test specifying secondaryFiles in same subdirectory of the job input as the primary input file.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.inline_javascript
    @pytest.mark.red
    def test_conformance_v1_2_scatter_embedded_subworkflow(self):
        """Test simple scatter over an embedded subworkflow

        Generated from::

            id: scatter_embedded_subworkflow
            job: tests/count-lines3-job.json
            output:
              count_output:
              - 16
              - 1
            tags:
            - workflow
            - inline_javascript
            tool: tests/count-lines18-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test simple scatter over an embedded subworkflow""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.scatter
    @pytest.mark.subworkflow
    @pytest.mark.multiple_input
    @pytest.mark.inline_javascript
    @pytest.mark.red
    def test_conformance_v1_2_scatter_multi_input_embedded_subworkflow(self):
        """Test simple multiple input scatter over an embedded subworkflow

        Generated from::

            id: scatter_multi_input_embedded_subworkflow
            job: tests/count-lines4-job.json
            output:
              count_output:
              - 16
              - 1
            tags:
            - workflow
            - scatter
            - subworkflow
            - multiple_input
            - inline_javascript
            tool: tests/count-lines14-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test simple multiple input scatter over an embedded subworkflow""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.subworkflow
    @pytest.mark.inline_javascript
    @pytest.mark.red
    def test_conformance_v1_2_workflow_embedded_subworkflow_embedded_subsubworkflow(self):
        """Test twice nested subworkflow

        Generated from::

            id: workflow_embedded_subworkflow_embedded_subsubworkflow
            job: tests/wc-job.json
            output:
              count_output: 16
            tags:
            - workflow
            - subworkflow
            - inline_javascript
            tool: tests/count-lines15-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test twice nested subworkflow""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.subworkflow
    @pytest.mark.inline_javascript
    @pytest.mark.red
    def test_conformance_v1_2_workflow_embedded_subworkflow_with_tool_and_subsubworkflow(self):
        """Test subworkflow of mixed depth with tool first

        Generated from::

            id: workflow_embedded_subworkflow_with_tool_and_subsubworkflow
            job: tests/wc-job.json
            output:
              count_output: 16
            tags:
            - workflow
            - subworkflow
            - inline_javascript
            tool: tests/count-lines16-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test subworkflow of mixed depth with tool first""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.subworkflow
    @pytest.mark.inline_javascript
    @pytest.mark.red
    def test_conformance_v1_2_workflow_embedded_subworkflow_with_subsubworkflow_and_tool(self):
        """Test subworkflow of mixed depth with tool after

        Generated from::

            id: workflow_embedded_subworkflow_with_subsubworkflow_and_tool
            job: tests/wc-job.json
            output:
              count_output: 16
            tags:
            - workflow
            - subworkflow
            - inline_javascript
            tool: tests/count-lines17-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test subworkflow of mixed depth with tool after""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.shell_command
    @pytest.mark.green
    def test_conformance_v1_2_workflow_records_inputs_and_outputs(self):
        """Test record type inputs to and outputs from workflows.

        Generated from::

            id: workflow_records_inputs_and_outputs
            job: tests/record-output-job.json
            output:
              orec:
                obar:
                  checksum: sha1$aeb3d11bdf536511649129f4077d5cda6a324118
                  class: File
                  location: bar
                  size: 12010
                ofoo:
                  checksum: sha1$327fc7aedf4f6b69a42a7c8b808dc5a7aff61376
                  class: File
                  location: foo
                  size: 1111
            tags:
            - workflow
            - shell_command
            tool: tests/record-output-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test record type inputs to and outputs from workflows.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.inline_javascript
    @pytest.mark.expression_tool
    @pytest.mark.green
    def test_conformance_v1_2_workflow_integer_input(self):
        """Test integer workflow input and outputs

        Generated from::

            id: workflow_integer_input
            job: tests/io-int.json
            output:
              o: 10
            tags:
            - workflow
            - inline_javascript
            - expression_tool
            tool: tests/io-int-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test integer workflow input and outputs""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.inline_javascript
    @pytest.mark.expression_tool
    @pytest.mark.green
    def test_conformance_v1_2_workflow_integer_input_optional_specified(self):
        """Test optional integer workflow inputs (specified)

        Generated from::

            id: workflow_integer_input_optional_specified
            job: tests/io-int.json
            output:
              o: 10
            tags:
            - workflow
            - inline_javascript
            - expression_tool
            tool: tests/io-int-optional-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test optional integer workflow inputs (specified)""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.inline_javascript
    @pytest.mark.expression_tool
    @pytest.mark.red
    def test_conformance_v1_2_workflow_integer_input_optional_unspecified(self):
        """Test optional integer workflow inputs (unspecified)

        Generated from::

            id: workflow_integer_input_optional_unspecified
            job: tests/empty.json
            output:
              o: 4
            tags:
            - workflow
            - inline_javascript
            - expression_tool
            tool: tests/io-int-optional-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test optional integer workflow inputs (unspecified)""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.inline_javascript
    @pytest.mark.expression_tool
    @pytest.mark.green
    def test_conformance_v1_2_workflow_integer_input_default_specified(self):
        """Test default integer workflow inputs (specified)

        Generated from::

            id: workflow_integer_input_default_specified
            job: tests/io-int.json
            output:
              o: 10
            tags:
            - workflow
            - inline_javascript
            - expression_tool
            tool: tests/io-int-default-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test default integer workflow inputs (specified)""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.inline_javascript
    @pytest.mark.expression_tool
    @pytest.mark.green
    def test_conformance_v1_2_workflow_integer_input_default_unspecified(self):
        """Test default integer workflow inputs (unspecified)

        Generated from::

            id: workflow_integer_input_default_unspecified
            job: tests/empty.json
            output:
              o: 8
            tags:
            - workflow
            - inline_javascript
            - expression_tool
            tool: tests/io-int-default-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test default integer workflow inputs (unspecified)""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.inline_javascript
    @pytest.mark.expression_tool
    @pytest.mark.green
    def test_conformance_v1_2_workflow_integer_input_default_and_tool_integer_input_default(self):
        """Test default integer tool and workflow inputs (unspecified)

        Generated from::

            id: workflow_integer_input_default_and_tool_integer_input_default
            job: tests/empty.json
            output:
              o: 13
            tags:
            - workflow
            - inline_javascript
            - expression_tool
            tool: tests/io-int-default-tool-and-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test default integer tool and workflow inputs (unspecified)""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_2_workflow_file_input_default_unspecified(self):
        """Test File input with default unspecified to workflow

        Generated from::

            id: workflow_file_input_default_unspecified
            job: tests/empty.json
            output:
              o:
                basename: output
                checksum: sha1$327fc7aedf4f6b69a42a7c8b808dc5a7aff61376
                class: File
                location: Any
                size: 1111
            tags:
            - workflow
            tool: tests/io-file-default-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test File input with default unspecified to workflow""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_2_workflow_file_input_default_specified(self):
        """Test File input with default specified to workflow

        Generated from::

            id: workflow_file_input_default_specified
            job: tests/default_path_job.yml
            output:
              o:
                basename: output
                checksum: sha1$47a013e660d408619d894b20806b1d5086aab03b
                class: File
                location: Any
                size: 13
            tags:
            - workflow
            tool: tests/io-file-default-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test File input with default specified to workflow""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.inline_javascript
    @pytest.mark.green
    def test_conformance_v1_2_clt_optional_union_input_file_or_files_with_array_of_one_file_provided(self):
        """Test input union type or File or File array to a tool with one file in array specified.

        Generated from::

            id: clt_optional_union_input_file_or_files_with_array_of_one_file_provided
            job: tests/job-input-array-one-empty-file.json
            output:
              output_file:
                basename: output.txt
                checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                class: File
                location: Any
                size: 0
            tags:
            - command_line_tool
            - inline_javascript
            tool: tests/io-file-or-files.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test input union type or File or File array to a tool with one file in array specified.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.inline_javascript
    @pytest.mark.green
    def test_conformance_v1_2_clt_optional_union_input_file_or_files_with_many_files_provided(self):
        """Test input union type or File or File array to a tool with a few files in array specified.

        Generated from::

            id: clt_optional_union_input_file_or_files_with_many_files_provided
            job: tests/job-input-array-few-files.json
            output:
              output_file:
                basename: output.txt
                checksum: sha1$6d1723861ad5a1260f1c3c07c93076c5a215f646
                class: File
                location: Any
                size: 1114
            tags:
            - command_line_tool
            - inline_javascript
            tool: tests/io-file-or-files.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test input union type or File or File array to a tool with a few files in array specified.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.inline_javascript
    @pytest.mark.green
    def test_conformance_v1_2_clt_optional_union_input_file_or_files_with_single_file_provided(self):
        """Test input union type or File or File array to a tool with one file specified.

        Generated from::

            id: clt_optional_union_input_file_or_files_with_single_file_provided
            job: tests/job-input-one-file.json
            output:
              output_file:
                basename: output.txt
                checksum: sha1$327fc7aedf4f6b69a42a7c8b808dc5a7aff61376
                class: File
                location: Any
                size: 1111
            tags:
            - command_line_tool
            - inline_javascript
            tool: tests/io-file-or-files.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test input union type or File or File array to a tool with one file specified.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.inline_javascript
    @pytest.mark.green
    def test_conformance_v1_2_clt_optional_union_input_file_or_files_with_nothing_provided(self):
        """Test input union type or File or File array to a tool with null specified.

        Generated from::

            id: clt_optional_union_input_file_or_files_with_nothing_provided
            job: tests/job-input-null.json
            output:
              output_file:
                basename: output.txt
                checksum: sha1$503458abf7614be3fb26d85ff5d8f3e17aa0a552
                class: File
                location: Any
                size: 10
            tags:
            - command_line_tool
            - inline_javascript
            tool: tests/io-file-or-files.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test input union type or File or File array to a tool with null specified.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.inline_javascript
    @pytest.mark.green
    def test_conformance_v1_2_clt_any_input_with_integer_provided(self):
        """Test Any parameter with integer input to a tool

        Generated from::

            id: clt_any_input_with_integer_provided
            job: tests/io-any-int.json
            output:
              t1: 7
            tags:
            - command_line_tool
            - inline_javascript
            tool: tests/io-any-1.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test Any parameter with integer input to a tool""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.inline_javascript
    @pytest.mark.green
    def test_conformance_v1_2_clt_any_input_with_string_provided(self):
        """Test Any parameter with string input to a tool

        Generated from::

            id: clt_any_input_with_string_provided
            job: tests/io-any-string.json
            output:
              t1: '7'
            tags:
            - command_line_tool
            - inline_javascript
            tool: tests/io-any-1.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test Any parameter with string input to a tool""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.inline_javascript
    @pytest.mark.green
    def test_conformance_v1_2_clt_any_input_with_file_provided(self):
        """Test Any parameter with file input to a tool

        Generated from::

            id: clt_any_input_with_file_provided
            job: tests/io-any-file.json
            output:
              t1: File
            tags:
            - command_line_tool
            - inline_javascript
            tool: tests/io-any-1.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test Any parameter with file input to a tool""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.inline_javascript
    @pytest.mark.red
    def test_conformance_v1_2_clt_any_input_with_mixed_array_provided(self):
        """Test Any parameter with array input to a tool

        Generated from::

            id: clt_any_input_with_mixed_array_provided
            job: tests/io-any-array.json
            output:
              t1:
              - 1
              - moocow
            tags:
            - command_line_tool
            - inline_javascript
            tool: tests/io-any-1.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test Any parameter with array input to a tool""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.inline_javascript
    @pytest.mark.green
    def test_conformance_v1_2_clt_any_input_with_record_provided(self):
        """Test Any parameter with record input to a tool

        Generated from::

            id: clt_any_input_with_record_provided
            job: tests/io-any-record.json
            output:
              t1:
                cow: 5
                moo: 1
            tags:
            - command_line_tool
            - inline_javascript
            tool: tests/io-any-1.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test Any parameter with record input to a tool""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.inline_javascript
    @pytest.mark.green
    def test_conformance_v1_2_workflow_any_input_with_integer_provided(self):
        """Test Any parameter with integer input to a workflow

        Generated from::

            id: workflow_any_input_with_integer_provided
            job: tests/io-any-int.json
            output:
              t1: 7
            tags:
            - workflow
            - inline_javascript
            tool: tests/io-any-wf-1.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test Any parameter with integer input to a workflow""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.inline_javascript
    @pytest.mark.green
    def test_conformance_v1_2_workflow_any_input_with_string_provided(self):
        """Test Any parameter with string input to a workflow

        Generated from::

            id: workflow_any_input_with_string_provided
            job: tests/io-any-string.json
            output:
              t1: '7'
            tags:
            - workflow
            - inline_javascript
            tool: tests/io-any-wf-1.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test Any parameter with string input to a workflow""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.inline_javascript
    @pytest.mark.green
    def test_conformance_v1_2_workflow_any_input_with_file_provided(self):
        """Test Any parameter with file input to a workflow

        Generated from::

            id: workflow_any_input_with_file_provided
            job: tests/io-any-file.json
            output:
              t1: File
            tags:
            - workflow
            - inline_javascript
            tool: tests/io-any-wf-1.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test Any parameter with file input to a workflow""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.inline_javascript
    @pytest.mark.green
    def test_conformance_v1_2_workflow_any_input_with_mixed_array_provided(self):
        """Test Any parameter with array input to a workflow

        Generated from::

            id: workflow_any_input_with_mixed_array_provided
            job: tests/io-any-array.json
            output:
              t1:
              - 1
              - moocow
            tags:
            - workflow
            - inline_javascript
            tool: tests/io-any-wf-1.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test Any parameter with array input to a workflow""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.inline_javascript
    @pytest.mark.green
    def test_conformance_v1_2_workflow_any_input_with_record_provided(self):
        """Test Any parameter with record input to a tool

        Generated from::

            id: workflow_any_input_with_record_provided
            job: tests/io-any-record.json
            output:
              t1:
                cow: 5
                moo: 1
            tags:
            - workflow
            - inline_javascript
            tool: tests/io-any-wf-1.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test Any parameter with record input to a tool""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.inline_javascript
    @pytest.mark.expression_tool
    @pytest.mark.green
    def test_conformance_v1_2_workflow_union_default_input_unspecified(self):
        """Test union type input to workflow with default unspecified

        Generated from::

            id: workflow_union_default_input_unspecified
            job: tests/empty.json
            output:
              o: the default value
            tags:
            - workflow
            - inline_javascript
            - expression_tool
            tool: tests/io-union-input-default-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test union type input to workflow with default unspecified""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.inline_javascript
    @pytest.mark.expression_tool
    @pytest.mark.green
    def test_conformance_v1_2_workflow_union_default_input_with_file_provided(self):
        """Test union type input to workflow with default specified as file

        Generated from::

            id: workflow_union_default_input_with_file_provided
            job: tests/io-any-file.json
            output:
              o: File
            tags:
            - workflow
            - inline_javascript
            - expression_tool
            tool: tests/io-union-input-default-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test union type input to workflow with default specified as file""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.step_input
    @pytest.mark.green
    def test_conformance_v1_2_workflowstep_valuefrom_string(self):
        """Test valueFrom on workflow step from literal (string).

        Generated from::

            id: workflowstep_valuefrom_string
            job: tests/empty.json
            output:
              val: 'moocow
            
                '
            tags:
            - workflow
            - step_input
            tool: tests/step-valuefrom4-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test valueFrom on workflow step from literal (string).""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.step_input
    @pytest.mark.green
    def test_conformance_v1_2_workflowstep_valuefrom_file_basename(self):
        """Test valueFrom on workflow step using basename.

        Generated from::

            id: workflowstep_valuefrom_file_basename
            job: tests/wc-job.json
            output:
              val1: 'whale.txt
            
                '
              val2: 'step1_out
            
                '
            tags:
            - workflow
            - step_input
            tool: tests/step-valuefrom5-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test valueFrom on workflow step using basename.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.expression_tool
    @pytest.mark.inline_javascript
    @pytest.mark.green
    def test_conformance_v1_2_expression_tool_int_array_output(self):
        """Test output arrays in a tool (with ints).

        Generated from::

            id: expression_tool_int_array_output
            job: tests/output-arrays-int-job.json
            output:
              o:
              - 0
              - 1
              - 2
            tags:
            - expression_tool
            - inline_javascript
            tool: tests/output-arrays-int.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test output arrays in a tool (with ints).""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.expression_tool
    @pytest.mark.inline_javascript
    @pytest.mark.green
    def test_conformance_v1_2_workflowstep_int_array_input_output(self):
        """Test output arrays in a workflow (with ints).

        Generated from::

            id: workflowstep_int_array_input_output
            job: tests/output-arrays-int-job.json
            output:
              o: 12
            tags:
            - workflow
            - expression_tool
            - inline_javascript
            tool: tests/output-arrays-int-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test output arrays in a workflow (with ints).""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.expression_tool
    @pytest.mark.inline_javascript
    @pytest.mark.red
    def test_conformance_v1_2_workflow_file_array_output(self):
        """Test output arrays in a workflow (with Files).

        Generated from::

            id: workflow_file_array_output
            job: tests/output-arrays-file-job.json
            output:
              o:
              - basename: moo
                checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                class: File
                location: Any
                size: 0
              - basename: cow
                checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                class: File
                location: Any
                size: 0
            tags:
            - workflow
            - expression_tool
            - inline_javascript
            tool: tests/output-arrays-file-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test output arrays in a workflow (with Files).""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.docker
    @pytest.mark.red
    def test_conformance_v1_2_docker_entrypoint(self):
        """Test Docker ENTRYPOINT usage

        Generated from::

            id: docker_entrypoint
            job: tests/empty.json
            output:
              cow:
                basename: cow
                checksum: sha1$7a788f56fa49ae0ba5ebde780efe4d6a89b5db47
                class: File
                location: Any
                size: 4
            tags:
            - command_line_tool
            - docker
            tool: tests/docker-run-cmd.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test Docker ENTRYPOINT usage""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.inline_javascript
    @pytest.mark.green
    def test_conformance_v1_2_clt_file_size_property_with_empty_file(self):
        """Test use of size in expressions for an empty file

        Generated from::

            id: clt_file_size_property_with_empty_file
            job: tests/job-input-array-one-empty-file.json
            output:
              output_file:
                basename: output.txt
                checksum: sha1$dad5a8472b87f6c5ef87d8fc6ef1458defc57250
                class: File
                location: Any
                size: 11
            tags:
            - command_line_tool
            - inline_javascript
            tool: tests/size-expression-tool.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test use of size in expressions for an empty file""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.inline_javascript
    @pytest.mark.green
    def test_conformance_v1_2_clt_file_size_property_with_multi_file(self):
        """Test use of size in expressions for a few files

        Generated from::

            id: clt_file_size_property_with_multi_file
            job: tests/job-input-array-few-files.json
            output:
              output_file:
                basename: output.txt
                checksum: sha1$9def39730e8012bd09bf8387648982728501737d
                class: File
                location: Any
                size: 31
            tags:
            - command_line_tool
            - inline_javascript
            tool: tests/size-expression-tool.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test use of size in expressions for a few files""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.required
    @pytest.mark.green
    def test_conformance_v1_2_any_without_defaults_unspecified_fails(self):
        """Test Any without defaults, unspecified, should fail.

        Generated from::

            id: any_without_defaults_unspecified_fails
            job: tests/null-expression-echo-job.json
            should_fail: true
            tags:
            - command_line_tool
            - required
            tool: tests/echo-tool.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test Any without defaults, unspecified, should fail.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.required
    @pytest.mark.green
    def test_conformance_v1_2_any_without_defaults_specified_fails(self):
        """Test Any without defaults, specified, should fail.

        Generated from::

            id: any_without_defaults_specified_fails
            job: tests/null-expression1-job.json
            should_fail: true
            tags:
            - command_line_tool
            - required
            tool: tests/echo-tool.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test Any without defaults, specified, should fail.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.required
    @pytest.mark.green
    def test_conformance_v1_2_step_input_default_value_noexp(self):
        """Test default value on step input parameter, no ExpressionTool

        Generated from::

            id: step_input_default_value_noexp
            job: tests/empty.json
            output:
              wc_output:
                checksum: sha1$3596ea087bfdaf52380eae441077572ed289d657
                class: File
                size: 3
            tags:
            - workflow
            - required
            tool: tests/count-lines9-wf-noET.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test default value on step input parameter, no ExpressionTool""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.required
    @pytest.mark.red
    def test_conformance_v1_2_step_input_default_value_overriden_noexp(self):
        """Test default value on step input parameter overridden by provided source, no ExpressionTool

        Generated from::

            id: step_input_default_value_overriden_noexp
            job: tests/cat-job.json
            output:
              wc_output:
                checksum: sha1$e5fa44f2b31c1fb553b6021e7360d07d5d91ff5e
                class: File
                size: 2
            tags:
            - workflow
            - required
            tool: tests/count-lines11-wf-noET.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test default value on step input parameter overridden by provided source, no ExpressionTool""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.subworkflow
    @pytest.mark.green
    def test_conformance_v1_2_nested_workflow_noexp(self):
        """Test nested workflow, without ExpressionTool

        Generated from::

            id: nested_workflow_noexp
            job: tests/wc-job.json
            output:
              wc_output:
                checksum: sha1$3596ea087bfdaf52380eae441077572ed289d657
                class: File
                size: 3
            tags:
            - workflow
            - subworkflow
            tool: tests/count-lines8-wf-noET.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test nested workflow, without ExpressionTool""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.step_input
    @pytest.mark.inline_javascript
    @pytest.mark.multiple_input
    @pytest.mark.red
    def test_conformance_v1_2_wf_multiplesources_multipletypes_noexp(self):
        """Test step input with multiple sources with multiple types, without ExpressionTool

        Generated from::

            id: wf_multiplesources_multipletypes_noexp
            job: tests/sum-job.json
            output:
              result:
                checksum: sha1$ad552e6dc057d1d825bf49df79d6b98eba846ebe
                class: File
                size: 3
            tags:
            - workflow
            - step_input
            - inline_javascript
            - multiple_input
            tool: tests/sum-wf-noET.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test step input with multiple sources with multiple types, without ExpressionTool""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.resource
    @pytest.mark.red
    def test_conformance_v1_2_dynamic_resreq_wf_optional_file_default(self):
        """Within a workflow, test accessing the size attribute of an optional input File as part of a CommandLineTool's ResourceRequirement calculation. The CommandLineTool input has a default value (a local file) and the workflow nor the workflow step does not provide any value for this input.

        Generated from::

            id: dynamic_resreq_wf_optional_file_default
            job: tests/empty.json
            output:
              cores:
                checksum: sha1$7448d8798a4380162d4b56f9b452e2f6f9e24e7a
                class: File
                location: output
                size: 2
            tags:
            - workflow
            - resource
            tool: tests/dynresreq-workflow-tooldefault.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Within a workflow, test accessing the size attribute of an optional input File as part of a CommandLineTool's ResourceRequirement calculation. The CommandLineTool input has a default value (a local file) and the workflow nor the workflow step does not provide any value for this input.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.resource
    @pytest.mark.green
    def test_conformance_v1_2_dynamic_resreq_wf_optional_file_step_default(self):
        """Within a workflow, test accessing the size attribute of an optional input File as part of a CommandLineTool's ResourceRequirement calculation. The workflow step provides a default value (a local file) for this input and the workflow itself does not provide any value for this input.

        Generated from::

            id: dynamic_resreq_wf_optional_file_step_default
            job: tests/empty.json
            output:
              cores:
                checksum: sha1$7448d8798a4380162d4b56f9b452e2f6f9e24e7a
                class: File
                location: output
                size: 2
            tags:
            - workflow
            - resource
            tool: tests/dynresreq-workflow-stepdefault.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Within a workflow, test accessing the size attribute of an optional input File as part of a CommandLineTool's ResourceRequirement calculation. The workflow step provides a default value (a local file) for this input and the workflow itself does not provide any value for this input.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.resource
    @pytest.mark.red
    def test_conformance_v1_2_dynamic_resreq_wf_optional_file_wf_default(self):
        """Within a workflow, test accessing the size attribute of an optional input File as part of a CommandLineTool's ResourceRequirement calculation. The workflow itself provides a default value (a local file) for this input.

        Generated from::

            id: dynamic_resreq_wf_optional_file_wf_default
            job: tests/empty.json
            output:
              cores:
                checksum: sha1$7448d8798a4380162d4b56f9b452e2f6f9e24e7a
                class: File
                location: output
                size: 2
            tags:
            - workflow
            - resource
            tool: tests/dynresreq-workflow-inputdefault.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Within a workflow, test accessing the size attribute of an optional input File as part of a CommandLineTool's ResourceRequirement calculation. The workflow itself provides a default value (a local file) for this input.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.inline_javascript
    @pytest.mark.red
    def test_conformance_v1_2_step_input_default_value_overriden_2nd_step(self):
        """Test default value on step input parameter overridden by provided source. With passthrough first step

        Generated from::

            id: step_input_default_value_overriden_2nd_step
            job: tests/cat-job.json
            output:
              count_output: 1
            tags:
            - workflow
            - inline_javascript
            tool: tests/count-lines11-extra-step-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test default value on step input parameter overridden by provided source. With passthrough first step""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.required
    @pytest.mark.red
    def test_conformance_v1_2_step_input_default_value_overriden_2nd_step_noexp(self):
        """Test default value on step input parameter overridden by provided source. With passthrough first step and no ExpressionTool

        Generated from::

            id: step_input_default_value_overriden_2nd_step_noexp
            job: tests/cat-job.json
            output:
              wc_output:
                checksum: sha1$e5fa44f2b31c1fb553b6021e7360d07d5d91ff5e
                class: File
                size: 2
            tags:
            - workflow
            - required
            tool: tests/count-lines11-extra-step-wf-noET.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test default value on step input parameter overridden by provided source. With passthrough first step and no ExpressionTool""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.inline_javascript
    @pytest.mark.green
    def test_conformance_v1_2_step_input_default_value_overriden_2nd_step_null(self):
        """Test default value on step input parameter overridden by provided source. With null producing first step

        Generated from::

            id: step_input_default_value_overriden_2nd_step_null
            job: tests/empty.json
            output:
              count_output: 16
            tags:
            - workflow
            - inline_javascript
            tool: tests/count-lines11-null-step-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test default value on step input parameter overridden by provided source. With null producing first step""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.required
    @pytest.mark.green
    def test_conformance_v1_2_step_input_default_value_overriden_2nd_step_null_noexp(self):
        """Test default value on step input parameter overridden by provided source. With null producing first step and no ExpressionTool

        Generated from::

            id: step_input_default_value_overriden_2nd_step_null_noexp
            job: tests/empty.json
            output:
              wc_output:
                checksum: sha1$3596ea087bfdaf52380eae441077572ed289d657
                class: File
                size: 3
            tags:
            - workflow
            - required
            tool: tests/count-lines11-null-step-wf-noET.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test default value on step input parameter overridden by provided source. With null producing first step and no ExpressionTool""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.required
    @pytest.mark.green
    def test_conformance_v1_2_stdin_from_directory_literal_with_local_file(self):
        """Pipe to stdin from user provided local File via a Directory literal

        Generated from::

            id: stdin_from_directory_literal_with_local_file
            job: tests/cat-from-dir-job.yaml
            output:
              output:
                checksum: sha1$47a013e660d408619d894b20806b1d5086aab03b
                class: File
                size: 13
            tags:
            - command_line_tool
            - required
            tool: tests/cat-from-dir.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Pipe to stdin from user provided local File via a Directory literal""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.required
    @pytest.mark.green
    def test_conformance_v1_2_stdin_from_directory_literal_with_literal_file(self):
        """Pipe to stdin from literal File via a Directory literal

        Generated from::

            id: stdin_from_directory_literal_with_literal_file
            job: tests/cat-from-dir-with-literal-file.yaml
            output:
              output:
                checksum: sha1$ef88e689559565999700d6fea7cf7ba306d04360
                class: File
                size: 26
            tags:
            - command_line_tool
            - required
            tool: tests/cat-from-dir.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Pipe to stdin from literal File via a Directory literal""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.required
    @pytest.mark.green
    def test_conformance_v1_2_directory_literal_with_literal_file_nostdin(self):
        """Test non-stdin reference to literal File via a Directory literal

        Generated from::

            id: directory_literal_with_literal_file_nostdin
            job: tests/cat-from-dir-with-literal-file.yaml
            output:
              output_file:
                checksum: sha1$ef88e689559565999700d6fea7cf7ba306d04360
                class: File
                size: 26
            tags:
            - command_line_tool
            - required
            tool: tests/cat3-from-dir.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test non-stdin reference to literal File via a Directory literal""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.required
    @pytest.mark.green
    def test_conformance_v1_2_no_inputs_commandlinetool(self):
        """Test CommandLineTool without inputs

        Generated from::

            id: no_inputs_commandlinetool
            output:
              output:
                checksum: sha1$1334e67fe9eb70db8ae14ccfa6cfb59e2cc24eae
                class: File
                location: output
                size: 4
            tags:
            - command_line_tool
            - required
            tool: tests/no-inputs-tool.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test CommandLineTool without inputs""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.required
    @pytest.mark.green
    def test_conformance_v1_2_no_outputs_commandlinetool(self):
        """Test CommandLineTool without outputs

        Generated from::

            id: no_outputs_commandlinetool
            job: tests/cat-job.json
            output: {}
            tags:
            - command_line_tool
            - required
            tool: tests/no-outputs-tool.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test CommandLineTool without outputs""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.required
    @pytest.mark.green
    def test_conformance_v1_2_no_inputs_workflow(self):
        """Test Workflow without inputs

        Generated from::

            id: no_inputs_workflow
            output:
              output:
                checksum: sha1$1334e67fe9eb70db8ae14ccfa6cfb59e2cc24eae
                class: File
                location: output
                size: 4
            tags:
            - workflow
            - required
            tool: tests/no-inputs-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test Workflow without inputs""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.required
    @pytest.mark.green
    def test_conformance_v1_2_no_outputs_workflow(self):
        """Test Workflow without outputs

        Generated from::

            id: no_outputs_workflow
            job: tests/cat-job.json
            output: {}
            tags:
            - workflow
            - required
            tool: tests/no-outputs-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test Workflow without outputs""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.required
    @pytest.mark.green
    def test_conformance_v1_2_anonymous_enum_in_array(self):
        """Test an anonymous enum inside an array inside a record

        Generated from::

            id: anonymous_enum_in_array
            job: tests/anon_enum_inside_array.yml
            output:
              result:
                checksum: sha1$2132943d72c39423e0b9425cbc40dfd5bf3e9cb2
                class: File
                size: 39
            tags:
            - command_line_tool
            - required
            tool: tests/anon_enum_inside_array.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test an anonymous enum inside an array inside a record""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.schema_def
    @pytest.mark.green
    def test_conformance_v1_2_schema_def_anonymous_enum_in_array(self):
        """Test an anonymous enum inside an array inside a record, SchemaDefRequirement

        Generated from::

            id: schema-def_anonymous_enum_in_array
            job: tests/anon_enum_inside_array_inside_schemadef.yml
            output:
              result:
                checksum: sha1$f17c7d81f66e1520fca25b96b90eeeae5bbf08b0
                class: File
                size: 39
            tags:
            - command_line_tool
            - schema_def
            tool: tests/anon_enum_inside_array_inside_schemadef.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test an anonymous enum inside an array inside a record, SchemaDefRequirement""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.docker
    @pytest.mark.green
    def test_conformance_v1_2_stdin_shorcut(self):
        """Test command execution in with stdin and stdout redirection using stdin shortcut

        Generated from::

            id: stdin_shorcut
            job: tests/wc-job.json
            output:
              output:
                checksum: sha1$327fc7aedf4f6b69a42a7c8b808dc5a7aff61376
                class: File
                location: output
                size: 1111
            tags:
            - command_line_tool
            - docker
            tool: tests/cat-tool-shortcut.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test command execution in with stdin and stdout redirection using stdin shortcut""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.required
    @pytest.mark.red
    def test_conformance_v1_2_secondary_files_in_unnamed_records(self):
        """Test secondaryFiles on anonymous record fields

        Generated from::

            id: secondary_files_in_unnamed_records
            job: tests/record-secondaryFiles-job.yml
            output: {}
            tags:
            - command_line_tool
            - required
            tool: tests/record-in-secondaryFiles.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test secondaryFiles on anonymous record fields""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.schema_def
    @pytest.mark.red
    def test_conformance_v1_2_secondary_files_in_named_records(self):
        """Test secondaryFiles on SchemaDefRequirement record fields

        Generated from::

            id: secondary_files_in_named_records
            job: tests/record-secondaryFiles-job.yml
            output: {}
            tags:
            - command_line_tool
            - schema_def
            tool: tests/record-sd-secondaryFiles.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test secondaryFiles on SchemaDefRequirement record fields""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.required
    @pytest.mark.red
    def test_conformance_v1_2_secondary_files_in_output_records(self):
        """Test secondaryFiles on output record fields

        Generated from::

            id: secondary_files_in_output_records
            job: tests/empty.json
            output:
              record_output:
                f1:
                  checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                  class: File
                  location: A
                  secondaryFiles:
                  - checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                    class: File
                    location: A.s2
                    size: 0
                  size: 0
                f2:
                - checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                  class: File
                  location: B
                  secondaryFiles:
                  - checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                    class: File
                    location: B.s3
                    size: 0
                  size: 0
                - checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                  class: File
                  location: C
                  secondaryFiles:
                  - checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                    class: File
                    location: C.s3
                    size: 0
                  size: 0
            tags:
            - command_line_tool
            - required
            tool: tests/record-out-secondaryFiles.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test secondaryFiles on output record fields""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.required
    @pytest.mark.green
    def test_conformance_v1_2_secondary_files_workflow_propagation(self):
        """Test secondaryFiles propagation through workflow

        Generated from::

            id: secondary_files_workflow_propagation
            job: tests/record-secondaryFiles-job.yml
            output: {}
            tags:
            - workflow
            - required
            tool: tests/record-in-secondaryFiles-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test secondaryFiles propagation through workflow""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.required
    @pytest.mark.inputs_should_parse
    @pytest.mark.red
    def test_conformance_v1_2_secondary_files_missing(self):
        """Test checking when secondaryFiles are missing

        Generated from::

            id: secondary_files_missing
            job: tests/record-secondaryFiles-job.yml
            should_fail: true
            tags:
            - workflow
            - required
            - inputs_should_parse
            tool: tests/record-in-secondaryFiles-missing-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test checking when secondaryFiles are missing""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.required
    @pytest.mark.red
    def test_conformance_v1_2_input_records_file_entry_with_format(self):
        """Test format on anonymous record fields

        Generated from::

            id: input_records_file_entry_with_format
            job: tests/record-format-job.yml
            output: {}
            tags:
            - command_line_tool
            - required
            tool: tests/record-in-format.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test format on anonymous record fields""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.format_checking
    @pytest.mark.inputs_should_parse
    @pytest.mark.green
    def test_conformance_v1_2_input_records_file_entry_with_format_and_bad_regular_input_file_format(self):
        """Test file format checking on parameter

        Generated from::

            id: input_records_file_entry_with_format_and_bad_regular_input_file_format
            job: tests/record-format-job2.yml
            should_fail: true
            tags:
            - command_line_tool
            - format_checking
            - inputs_should_parse
            tool: tests/record-in-format.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test file format checking on parameter""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.format_checking
    @pytest.mark.inputs_should_parse
    @pytest.mark.green
    def test_conformance_v1_2_input_records_file_entry_with_format_and_bad_entry_file_format(self):
        """Test file format checking on record field

        Generated from::

            id: input_records_file_entry_with_format_and_bad_entry_file_format
            job: tests/record-format-job3.yml
            should_fail: true
            tags:
            - command_line_tool
            - format_checking
            - inputs_should_parse
            tool: tests/record-in-format.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test file format checking on record field""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.format_checking
    @pytest.mark.inputs_should_parse
    @pytest.mark.green
    def test_conformance_v1_2_input_records_file_entry_with_format_and_bad_entry_array_file_format(self):
        """Test file format checking on array item

        Generated from::

            id: input_records_file_entry_with_format_and_bad_entry_array_file_format
            job: tests/record-format-job4.yml
            should_fail: true
            tags:
            - command_line_tool
            - format_checking
            - inputs_should_parse
            tool: tests/record-in-format.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test file format checking on array item""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.format_checking
    @pytest.mark.red
    def test_conformance_v1_2_record_output_file_entry_format(self):
        """Test format on output record fields

        Generated from::

            id: record_output_file_entry_format
            job: tests/record-secondaryFiles-job.yml
            output:
              f1out:
                checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                class: File
                format: http://example.com/format1
                location: A
                size: 0
              record_output:
                f2out:
                  checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                  class: File
                  format: http://example.com/format2
                  location: B
                  size: 0
            tags:
            - command_line_tool
            - format_checking
            tool: tests/record-out-format.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test format on output record fields""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.step_input
    @pytest.mark.inline_javascript
    @pytest.mark.expression_tool
    @pytest.mark.red
    def test_conformance_v1_2_workflow_input_inputBinding_loadContents(self):
        """Test WorkflowInputParameter.inputBinding.loadContents

        Generated from::

            id: workflow_input_inputBinding_loadContents
            job: tests/wf-loadContents-job.yml
            output:
              my_int: 42
            tags:
            - workflow
            - step_input
            - inline_javascript
            - expression_tool
            tool: tests/wf-loadContents.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test WorkflowInputParameter.inputBinding.loadContents""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.step_input
    @pytest.mark.inline_javascript
    @pytest.mark.expression_tool
    @pytest.mark.red
    def test_conformance_v1_2_workflow_input_loadContents_without_inputBinding(self):
        """Test WorkflowInputParameter.loadContents

        Generated from::

            id: workflow_input_loadContents_without_inputBinding
            job: tests/wf-loadContents-job.yml
            output:
              my_int: 42
            tags:
            - workflow
            - step_input
            - inline_javascript
            - expression_tool
            tool: tests/wf-loadContents2.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test WorkflowInputParameter.loadContents""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.step_input
    @pytest.mark.inline_javascript
    @pytest.mark.expression_tool
    @pytest.mark.green
    def test_conformance_v1_2_expression_tool_input_loadContents(self):
        """Test loadContents on InputParameter.loadContents (expression)

        Generated from::

            id: expression_tool_input_loadContents
            job: tests/wf-loadContents-job.yml
            output:
              my_int: 42
            tags:
            - workflow
            - step_input
            - inline_javascript
            - expression_tool
            tool: tests/wf-loadContents3.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test loadContents on InputParameter.loadContents (expression)""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.step_input
    @pytest.mark.inline_javascript
    @pytest.mark.expression_tool
    @pytest.mark.red
    def test_conformance_v1_2_workflow_step_in_loadContents(self):
        """Test WorkflowStepInput.loadContents

        Generated from::

            id: workflow_step_in_loadContents
            job: tests/wf-loadContents-job.yml
            output:
              my_int: 42
            tags:
            - workflow
            - step_input
            - inline_javascript
            - expression_tool
            tool: tests/wf-loadContents4.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test WorkflowStepInput.loadContents""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.timelimit
    @pytest.mark.work_reuse
    @pytest.mark.inputs_should_parse
    @pytest.mark.green
    def test_conformance_v1_2_timelimit_basic(self):
        """Test that job fails when exceeding time limit

        Generated from::

            id: timelimit_basic
            job: tests/empty.json
            should_fail: true
            tags:
            - command_line_tool
            - timelimit
            - work_reuse
            - inputs_should_parse
            tool: tests/timelimit.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test that job fails when exceeding time limit""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.timelimit
    @pytest.mark.json_schema_invalid
    @pytest.mark.inputs_should_parse
    @pytest.mark.green
    def test_conformance_v1_2_timelimit_invalid(self):
        """Test invalid time limit value

        Generated from::

            id: timelimit_invalid
            job: tests/empty.json
            should_fail: true
            tags:
            - command_line_tool
            - timelimit
            - json_schema_invalid
            - inputs_should_parse
            tool: tests/timelimit2.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test invalid time limit value""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.timelimit
    @pytest.mark.work_reuse
    @pytest.mark.red
    def test_conformance_v1_2_timelimit_zero_unlimited(self):
        """Test zero timelimit means no limit

        Generated from::

            id: timelimit_zero_unlimited
            job: tests/empty.json
            output: {}
            tags:
            - command_line_tool
            - timelimit
            - work_reuse
            tool: tests/timelimit3.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test zero timelimit means no limit""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.timelimit
    @pytest.mark.inline_javascript
    @pytest.mark.work_reuse
    @pytest.mark.inputs_should_parse
    @pytest.mark.green
    def test_conformance_v1_2_timelimit_from_expression(self):
        """Test expression in time limit

        Generated from::

            id: timelimit_from_expression
            job: tests/empty.json
            should_fail: true
            tags:
            - command_line_tool
            - timelimit
            - inline_javascript
            - work_reuse
            - inputs_should_parse
            tool: tests/timelimit4.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test expression in time limit""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.expression_tool
    @pytest.mark.timelimit
    @pytest.mark.inline_javascript
    @pytest.mark.red
    def test_conformance_v1_2_timelimit_expressiontool(self):
        """Test timelimit in expressiontool is ignored

        Generated from::

            id: timelimit_expressiontool
            job: tests/empty.json
            output:
              status: Done
            tags:
            - expression_tool
            - timelimit
            - inline_javascript
            tool: tests/timelimit5.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test timelimit in expressiontool is ignored""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.timelimit
    @pytest.mark.inputs_should_parse
    @pytest.mark.green
    def test_conformance_v1_2_timelimit_basic_wf(self):
        """Test that tool in workflow fails when exceeding time limit

        Generated from::

            id: timelimit_basic_wf
            job: tests/empty.json
            should_fail: true
            tags:
            - workflow
            - timelimit
            - inputs_should_parse
            tool: tests/timelimit-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test that tool in workflow fails when exceeding time limit""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.timelimit
    @pytest.mark.inline_javascript
    @pytest.mark.red
    def test_conformance_v1_2_timelimit_invalid_wf(self):
        """Test that workflow level time limit is not applied to workflow execution time

        Generated from::

            id: timelimit_invalid_wf
            job: tests/empty.json
            output:
              o: time passed
            tags:
            - workflow
            - timelimit
            - inline_javascript
            tool: tests/timelimit2-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test that workflow level time limit is not applied to workflow execution time""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.timelimit
    @pytest.mark.inline_javascript
    @pytest.mark.work_reuse
    @pytest.mark.red
    def test_conformance_v1_2_timelimit_zero_unlimited_wf(self):
        """Test zero timelimit means no limit in workflow

        Generated from::

            id: timelimit_zero_unlimited_wf
            job: tests/empty.json
            output:
              o: time passed
            tags:
            - workflow
            - timelimit
            - inline_javascript
            - work_reuse
            tool: tests/timelimit3-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test zero timelimit means no limit in workflow""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.timelimit
    @pytest.mark.inline_javascript
    @pytest.mark.work_reuse
    @pytest.mark.inputs_should_parse
    @pytest.mark.green
    def test_conformance_v1_2_timelimit_from_expression_wf(self):
        """Test expression in time limit in workflow

        Generated from::

            id: timelimit_from_expression_wf
            job: tests/empty.json
            should_fail: true
            tags:
            - workflow
            - timelimit
            - inline_javascript
            - work_reuse
            - inputs_should_parse
            tool: tests/timelimit4-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test expression in time limit in workflow""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.networkaccess
    @pytest.mark.red
    def test_conformance_v1_2_networkaccess(self):
        """Test networkaccess enabled

        Generated from::

            id: networkaccess
            job: tests/empty.json
            output: {}
            tags:
            - command_line_tool
            - networkaccess
            tool: tests/networkaccess.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test networkaccess enabled""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.networkaccess
    @pytest.mark.command_line_tool
    @pytest.mark.inputs_should_parse
    @pytest.mark.red
    def test_conformance_v1_2_networkaccess_disabled(self):
        """Test networkaccess is disabled by default

        Generated from::

            id: networkaccess_disabled
            job: tests/empty.json
            should_fail: true
            tags:
            - networkaccess
            - command_line_tool
            - inputs_should_parse
            tool: tests/networkaccess2.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test networkaccess is disabled by default""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.resource
    @pytest.mark.command_line_tool
    @pytest.mark.initial_work_dir
    @pytest.mark.red
    def test_conformance_v1_2_initial_work_dir_for_null_and_arrays(self):
        """Test null and array input in InitialWorkDirRequirement

        Generated from::

            id: initial_work_dir_for_null_and_arrays
            job: tests/stage-array-job.json
            output:
              output:
                basename: lsout
                checksum: sha1$e453d26efd859a9abc80ae1a1d9d63db72376053
                class: File
                location: lsout
                size: 32
            tags:
            - resource
            - command_line_tool
            - initial_work_dir
            tool: tests/stage-array.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test null and array input in InitialWorkDirRequirement""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.resource
    @pytest.mark.command_line_tool
    @pytest.mark.initial_work_dir
    @pytest.mark.red
    def test_conformance_v1_2_initial_work_dir_for_array_dirs(self):
        """Test array of directories InitialWorkDirRequirement

        Generated from::

            id: initial_work_dir_for_array_dirs
            job: tests/stage-array-dirs-job.yml
            output:
              output:
              - checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                class: File
                location: a
                size: 0
              - checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                class: File
                location: B
                size: 0
            tags:
            - resource
            - command_line_tool
            - initial_work_dir
            tool: tests/stage-array-dirs.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test array of directories InitialWorkDirRequirement""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.input_object_requirements
    @pytest.mark.red
    def test_conformance_v1_2_cwl_requirements_addition(self):
        """Test requirements in input document via EnvVarRequirement

        Generated from::

            id: cwl_requirements_addition
            job: tests/env-job3.yaml
            output:
              out:
                checksum: sha1$b3ec4ed1749c207e52b3a6d08c59f31d83bff519
                class: File
                location: out
                size: 15
            tags:
            - command_line_tool
            - input_object_requirements
            tool: tests/env-tool3.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test requirements in input document via EnvVarRequirement""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.input_object_requirements
    @pytest.mark.red
    def test_conformance_v1_2_cwl_requirements_override_expression(self):
        """Test conflicting requirements in input document via EnvVarRequirement and expression

        Generated from::

            id: cwl_requirements_override_expression
            job: tests/env-job3.yaml
            output:
              out:
                checksum: sha1$b3ec4ed1749c207e52b3a6d08c59f31d83bff519
                class: File
                location: out
                size: 15
            tags:
            - command_line_tool
            - input_object_requirements
            tool: tests/env-tool4.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test conflicting requirements in input document via EnvVarRequirement and expression""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.input_object_requirements
    @pytest.mark.red
    def test_conformance_v1_2_cwl_requirements_override_static(self):
        """Test conflicting requirements in input document via EnvVarRequirement

        Generated from::

            id: cwl_requirements_override_static
            job: tests/env-job4.yaml
            output:
              out:
                checksum: sha1$715e62184492851512a020c36ab7118eca114a59
                class: File
                location: out
                size: 23
            tags:
            - command_line_tool
            - input_object_requirements
            tool: tests/env-tool3.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test conflicting requirements in input document via EnvVarRequirement""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.initial_work_dir
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_initial_workdir_output_glob(self):
        """Test full path glob output of InitialWorkDir

        Generated from::

            id: initial_workdir_output_glob
            job: tests/initialworkdirrequirement-docker-out-job.json
            output:
              OUTPUT:
                checksum: sha1$aeb3d11bdf536511649129f4077d5cda6a324118
                class: File
                location: ref.fasta
                secondaryFiles:
                - checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                  class: File
                  location: ref.fasta.fai
                  size: 0
                size: 12010
            tags:
            - initial_work_dir
            - command_line_tool
            tool: tests/initialworkdir-glob-fullpath.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test full path glob output of InitialWorkDir""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.docker
    @pytest.mark.inputs_should_parse
    @pytest.mark.red
    def test_conformance_v1_2_glob_outside_outputs_fails(self):
        """Test fail trying to glob outside output directory

        Generated from::

            id: glob_outside_outputs_fails
            job: tests/empty.json
            should_fail: true
            tags:
            - command_line_tool
            - docker
            - inputs_should_parse
            tool: tests/glob-path-error.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test fail trying to glob outside output directory""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.inputs_should_parse
    @pytest.mark.red
    def test_conformance_v1_2_illegal_symlink(self):
        """symlink to file outside of working directory should NOT be retrieved

        Generated from::

            id: illegal_symlink
            job: tests/empty.json
            output:
              output_file:
                baesname: symlink.txt
                checksum: sha1$cd28ec34f3f9425aca544b6332453708e8aaa82a
                class: File
                size: 27
            should_fail: true
            tags:
            - command_line_tool
            - inputs_should_parse
            tool: tests/symlink-illegal.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """symlink to file outside of working directory should NOT be retrieved""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_legal_symlink(self):
        """symlink to file inside of working directory should be retrieved

        Generated from::

            id: legal_symlink
            job: tests/empty.json
            output:
              output_file:
                basename: symlink.txt
                checksum: sha1$cd28ec34f3f9425aca544b6332453708e8aaa82a
                class: File
                size: 27
            tags:
            - command_line_tool
            tool: tests/symlink-legal.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """symlink to file inside of working directory should be retrieved""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.inplace_update
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_2_modify_file_content(self):
        """inplace update has side effect on file content

        Generated from::

            id: modify_file_content
            job: tests/empty.json
            output:
              a: 4
              b: 4
            tags:
            - inplace_update
            - workflow
            tool: tests/inp_update_wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """inplace update has side effect on file content""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.inplace_update
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_2_modify_directory_content(self):
        """inplace update has side effect on directory content

        Generated from::

            id: modify_directory_content
            job: tests/empty.json
            output:
              a:
              - basename: blurb
                class: File
                location: blurb
              b:
              - basename: blurb
                class: File
                location: blurb
            tags:
            - inplace_update
            - workflow
            tool: tests/inpdir_update_wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """inplace update has side effect on directory content""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.red
    def test_conformance_v1_2_outputbinding_glob_directory(self):
        """Test that OutputBinding.glob accepts Directories

        Generated from::

            id: outputbinding_glob_directory
            job: tests/empty.json
            output:
              directories:
              - basename: a_dir
                class: Directory
                listing: []
              - basename: b_dir
                class: Directory
                listing: []
              - basename: c_dir
                class: Directory
                listing: []
            tags:
            - required
            - command_line_tool
            tool: tests/glob_directory.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test that OutputBinding.glob accepts Directories""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.initial_work_dir
    @pytest.mark.inline_javascript
    @pytest.mark.red
    def test_conformance_v1_2_stage_file_array(self):
        """Test that array of input files can be staged to directory with entryname

        Generated from::

            id: stage_file_array
            job: tests/stage_file_array.job.json
            output:
              output:
              - basename: sfa-1.txt
                checksum: sha1$4c1cd0638ab3580310823fd1556d27ecb4816df6
                class: File
                size: 49
              - basename: sfa-1.txt.sec
                checksum: sha1$40f4ee1bcd1a9466fcd2e48cf7fc3798025d2f9a
                class: File
                size: 59
              - basename: sfa-2.txt
                checksum: sha1$4c1cd0638ab3580310823fd1556d27ecb4816df6
                class: File
                size: 49
              - basename: sfa-2.txt.sec
                checksum: sha1$40f4ee1bcd1a9466fcd2e48cf7fc3798025d2f9a
                class: File
                size: 59
            tags:
            - command_line_tool
            - initial_work_dir
            - inline_javascript
            tool: tests/stage_file_array.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test that array of input files can be staged to directory with entryname""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.initial_work_dir
    @pytest.mark.inline_javascript
    @pytest.mark.red
    def test_conformance_v1_2_stage_file_array_basename(self):
        """Test that array of input files can be staged to directory with basename

        Generated from::

            id: stage_file_array_basename
            job: tests/stage_file_array.job.json
            output:
              output:
              - basename: sfa-1.txt
                checksum: sha1$4c1cd0638ab3580310823fd1556d27ecb4816df6
                class: File
                size: 49
              - basename: sfa-1.txt.sec
                checksum: sha1$40f4ee1bcd1a9466fcd2e48cf7fc3798025d2f9a
                class: File
                size: 59
              - basename: sfa-2.txt
                checksum: sha1$4c1cd0638ab3580310823fd1556d27ecb4816df6
                class: File
                size: 49
              - basename: sfa-2.txt.sec
                checksum: sha1$40f4ee1bcd1a9466fcd2e48cf7fc3798025d2f9a
                class: File
                size: 59
            tags:
            - command_line_tool
            - initial_work_dir
            - inline_javascript
            tool: tests/stage_file_array_basename.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test that array of input files can be staged to directory with basename""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.initial_work_dir
    @pytest.mark.inline_javascript
    @pytest.mark.red
    def test_conformance_v1_2_stage_file_array_entryname_overrides(self):
        """Test that if array of input files are staged to directory with basename and entryname, entryname overrides

        Generated from::

            id: stage_file_array_entryname_overrides
            job: tests/stage_file_array.job.json
            output:
              output:
              - basename: sfa-1.txt
                checksum: sha1$4c1cd0638ab3580310823fd1556d27ecb4816df6
                class: File
                size: 49
              - basename: sfa-1.txt.sec
                checksum: sha1$40f4ee1bcd1a9466fcd2e48cf7fc3798025d2f9a
                class: File
                size: 59
              - basename: sfa-2.txt
                checksum: sha1$4c1cd0638ab3580310823fd1556d27ecb4816df6
                class: File
                size: 49
              - basename: sfa-2.txt.sec
                checksum: sha1$40f4ee1bcd1a9466fcd2e48cf7fc3798025d2f9a
                class: File
                size: 59
            tags:
            - command_line_tool
            - initial_work_dir
            - inline_javascript
            tool: tests/stage_file_array_basename_and_entryname.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test that if array of input files are staged to directory with basename and entryname, entryname overrides""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.red
    def test_conformance_v1_2_tmpdir_is_not_outdir(self):
        """Test that runtime.tmpdir is not runtime.outdir

        Generated from::

            id: tmpdir_is_not_outdir
            job: tests/empty.json
            output:
              foo:
                basename: foo
                checksum: sha1$fa98d6085770a79e44853d575cd3ab40c0f1f4de
                class: File
            tags:
            - command_line_tool
            tool: tests/runtime-paths-distinct.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test that runtime.tmpdir is not runtime.outdir""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_listing_default_none(self):
        """Test that default behavior is 'no_listing' if not specified

        Generated from::

            id: listing_default_none
            job: tests/listing-job.yml
            output:
              out: true
            tags:
            - command_line_tool
            tool: tests/listing_none1.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test that default behavior is 'no_listing' if not specified""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.load_listing
    @pytest.mark.green
    def test_conformance_v1_2_listing_requirement_none(self):
        """Test that 'listing' is not present when LoadListingRequirement is 'no_listing'

        Generated from::

            id: listing_requirement_none
            job: tests/listing-job.yml
            output:
              out: true
            tags:
            - command_line_tool
            - load_listing
            tool: tests/listing_none2.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test that 'listing' is not present when LoadListingRequirement is 'no_listing'""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_listing_loadListing_none(self):
        """Test that 'listing' is not present when loadListing on input parameter is 'no_listing'

        Generated from::

            id: listing_loadListing_none
            job: tests/listing-job.yml
            output:
              out: true
            tags:
            - command_line_tool
            tool: tests/listing_none3.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test that 'listing' is not present when loadListing on input parameter is 'no_listing'""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.load_listing
    @pytest.mark.green
    def test_conformance_v1_2_listing_requirement_shallow(self):
        """Test that 'listing' is present in top directory object but not subdirectory object when LoadListingRequirement is 'shallow_listing'


        Generated from::

            id: listing_requirement_shallow
            job: tests/listing-job.yml
            output:
              out: true
            tags:
            - command_line_tool
            - load_listing
            tool: tests/listing_shallow1.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test that 'listing' is present in top directory object but not subdirectory object when LoadListingRequirement is 'shallow_listing'
""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_listing_loadListing_shallow(self):
        """Test that 'listing' is present in top directory object but not subdirectory object when loadListing on input parameter loadListing is 'shallow_listing'


        Generated from::

            id: listing_loadListing_shallow
            job: tests/listing-job.yml
            output:
              out: true
            tags:
            - command_line_tool
            tool: tests/listing_shallow2.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test that 'listing' is present in top directory object but not subdirectory object when loadListing on input parameter loadListing is 'shallow_listing'
""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_listing_outputBinding_loadListing(self):
        """Test that loadListing works when used on outputBinding.


        Generated from::

            id: listing_outputBinding_loadListing
            job: tests/listing-job.yml
            output:
              out:
                basename: file2
                checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                class: File
                location: file2
                size: 0
            tags:
            - command_line_tool
            tool: tests/listing_shallow3.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test that loadListing works when used on outputBinding.
""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.load_listing
    @pytest.mark.green
    def test_conformance_v1_2_listing_requirement_deep(self):
        """Test that 'listing' is present in top directory object and in subdirectory objects when LoadListingRequirement is 'deep_listing'


        Generated from::

            id: listing_requirement_deep
            job: tests/listing-job.yml
            output:
              out: true
            tags:
            - command_line_tool
            - load_listing
            tool: tests/listing_deep1.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test that 'listing' is present in top directory object and in subdirectory objects when LoadListingRequirement is 'deep_listing'
""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_listing_loadListing_deep(self):
        """Test that 'listing' is present in top directory object and in subdirectory objects when input parameter loadListing is 'deep_listing'


        Generated from::

            id: listing_loadListing_deep
            job: tests/listing-job.yml
            output:
              out: true
            tags:
            - command_line_tool
            tool: tests/listing_deep2.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test that 'listing' is present in top directory object and in subdirectory objects when input parameter loadListing is 'deep_listing'
""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.required
    @pytest.mark.green
    def test_conformance_v1_2_inputBinding_position_expr(self):
        """Test for expression in the InputBinding.position field; also test using emoji in CWL document and tool output


        Generated from::

            id: inputBinding_position_expr
            job: tests/echo-position-expr-job.yml
            output:
              out: "\U0001F57A 1 singular sensation!\n"
            tags:
            - command_line_tool
            - required
            tool: tests/echo-position-expr.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test for expression in the InputBinding.position field; also test using emoji in CWL document and tool output
""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.required
    @pytest.mark.red
    def test_conformance_v1_2_outputEval_exitCode(self):
        """Can access exit code in outputEval

        Generated from::

            id: outputEval_exitCode
            job: tests/empty.json
            output:
              code: 7
            tags:
            - command_line_tool
            - required
            tool: tests/exitcode.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Can access exit code in outputEval""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_any_input_param_graph_no_default(self):
        """Test use of $graph without specifying which process to run

        Generated from::

            id: any_input_param_graph_no_default
            job: tests/env-job.json
            output:
              out: 'hello test env
            
                '
            tags:
            - required
            - command_line_tool
            tool: tests/echo-tool-packed.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test use of $graph without specifying which process to run""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_any_input_param_graph_no_default_hashmain(self):
        """Test use of $graph without specifying which process to run, hash-prefixed "main"


        Generated from::

            id: any_input_param_graph_no_default_hashmain
            job: tests/env-job.json
            output:
              out: 'hello test env
            
                '
            tags:
            - required
            - command_line_tool
            tool: tests/echo-tool-packed2.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test use of $graph without specifying which process to run, hash-prefixed "main"
""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.inline_javascript
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_optional_numerical_output_returns_0_not_null(self):
        """Test that optional number output is returned as 0, not null


        Generated from::

            id: optional_numerical_output_returns_0_not_null
            job: tests/empty.json
            output:
              out: 0
            tags:
            - inline_javascript
            - command_line_tool
            tool: tests/optional-numerical-output-0.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test that optional number output is returned as 0, not null
""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.resource
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_cores_float(self):
        """Test float value for coresMin(Max) is rounded up in runtime.cores

        Generated from::

            id: cores_float
            job: tests/empty.json
            output:
              output:
                checksum: sha1$7448d8798a4380162d4b56f9b452e2f6f9e24e7a
                class: File
                location: cores.txt
                size: 2
            tags:
            - resource
            - command_line_tool
            tool: tests/cores_float.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test float value for coresMin(Max) is rounded up in runtime.cores""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.resource
    @pytest.mark.command_line_tool
    @pytest.mark.red
    def test_conformance_v1_2_storage_float(self):
        """Test float value for ram/tmpdir/outdir Min(Max) is rounded up

        Generated from::

            id: storage_float
            job: tests/empty.json
            output:
              output:
                basename: values.txt
                checksum: sha1$c73f68407c144c5336a6c14e7ec79ee470231bd7
                class: File
                location: values.txt
                size: 12
            tags:
            - resource
            - command_line_tool
            tool: tests/storage_float.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test float value for ram/tmpdir/outdir Min(Max) is rounded up""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_cat_synthetic_file(self):
        """Test the generation of a synthetic file with inline contents.

        Generated from::

            id: cat_synthetic_file
            job: tests/synth-file-job.yml
            output:
              sequence:
                checksum: sha1$5d64b71392b1e00a3ad893db02d381d58262c2d6
                class: File
                size: 7
            tags:
            - required
            - command_line_tool
            tool: tests/synth-file.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test the generation of a synthetic file with inline contents.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.inline_javascript
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_continuation(self):
        """Line continuations in bash scripts should behave correctly

        Generated from::

            id: continuation
            output:
              out:
                checksum: sha1$47d8510dce768c907f4dea6bcaf90f8d59cb265c
                class: File
                location: out.txt
                size: 48
            tags:
            - inline_javascript
            - command_line_tool
            tool: bash-line-continuation.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Line continuations in bash scripts should behave correctly""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.inline_javascript
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_continuation_expression(self):
        """Line continuations in bash scripts should always behave correctly

        Generated from::

            id: continuation_expression
            output:
              out:
                checksum: sha1$47d8510dce768c907f4dea6bcaf90f8d59cb265c
                class: File
                location: out.txt
                size: 48
            tags:
            - inline_javascript
            - command_line_tool
            tool: bash-line-continuation-with-expression.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Line continuations in bash scripts should always behave correctly""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.inline_javascript
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_quoting_multiple_backslashes(self):
        """Test quoting multiple backslashes

        Generated from::

            id: quoting_multiple_backslashes
            output:
              out:
                checksum: sha1$acfdc38aef5354c03b976cbb6d9f7d08a179951d
                class: File
                location: out.txt
                size: 246
            tags:
            - inline_javascript
            - command_line_tool
            tool: bash-dollar-quote.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test quoting multiple backslashes""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.inline_javascript
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_escaping_expression_no_extra_quotes(self):
        """Strings returned from JS expressions should not have extra quotes around them

        Generated from::

            id: escaping_expression_no_extra_quotes
            output:
              out:
                checksum: sha1$726e9e616f278d9028b4a870653b01c125c2fc89
                class: File
                location: file.txt
                size: 14
            tags:
            - inline_javascript
            - command_line_tool
            tool: js-quote.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Strings returned from JS expressions should not have extra quotes around them""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.conditional
    @pytest.mark.inline_javascript
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_2_direct_optional_null_result(self):
        """Simplest conditional pattern (False)

        Generated from::

            id: direct_optional_null_result
            job: val.1.job.yaml
            output:
              out1: null
            tags:
            - conditional
            - inline_javascript
            - workflow
            tool: cond-wf-001.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Simplest conditional pattern (False)""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.conditional
    @pytest.mark.inline_javascript
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_2_direct_optional_nonnull_result(self):
        """Simplest conditional pattern (True)

        Generated from::

            id: direct_optional_nonnull_result
            job: val.3.job.yaml
            output:
              out1: foo 3
            tags:
            - conditional
            - inline_javascript
            - workflow
            tool: cond-wf-001.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Simplest conditional pattern (True)""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.conditional
    @pytest.mark.inline_javascript
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_2_direct_required(self):
        """Conditional using intermediate WorkflowStep.in input

        Generated from::

            id: direct_required
            job: val.1.job.yaml
            output:
              out1: null
            tags:
            - conditional
            - inline_javascript
            - workflow
            tool: cond-wf-002.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Conditional using intermediate WorkflowStep.in input""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.conditional
    @pytest.mark.inline_javascript
    @pytest.mark.multiple_input
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_2_pass_through_required_false_when(self):
        """Pass through pattern with pickValue: first_non_null; 'when' is false

        Generated from::

            id: pass_through_required_false_when
            job: val.1.job.yaml
            output:
              out1: Direct
            tags:
            - conditional
            - inline_javascript
            - multiple_input
            - workflow
            tool: cond-wf-003.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Pass through pattern with pickValue: first_non_null; 'when' is false""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.conditional
    @pytest.mark.inline_javascript
    @pytest.mark.multiple_input
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_2_pass_through_required_true_when(self):
        """pass through pattern with pickvalue: first_non_null; 'when' is true

        Generated from::

            id: pass_through_required_true_when
            job: val.3.job.yaml
            output:
              out1: foo 3
            tags:
            - conditional
            - inline_javascript
            - multiple_input
            - workflow
            tool: cond-wf-003.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """pass through pattern with pickvalue: first_non_null; 'when' is true""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.conditional
    @pytest.mark.inline_javascript
    @pytest.mark.multiple_input
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_2_first_non_null_first_non_null(self):
        """pickValue: first_non_null first item is non null

        Generated from::

            id: first_non_null_first_non_null
            job: val.0.job.yaml
            output:
              out1: foo 0
            tags:
            - conditional
            - inline_javascript
            - multiple_input
            - workflow
            tool: cond-wf-003.1.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """pickValue: first_non_null first item is non null""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.conditional
    @pytest.mark.inline_javascript
    @pytest.mark.multiple_input
    @pytest.mark.workflow
    @pytest.mark.inputs_should_parse
    @pytest.mark.green
    def test_conformance_v1_2_first_non_null_all_null(self):
        """pickValue: first_non_null needs at least one non null

        Generated from::

            id: first_non_null_all_null
            job: val.1.job.yaml
            should_fail: true
            tags:
            - conditional
            - inline_javascript
            - multiple_input
            - workflow
            - inputs_should_parse
            tool: cond-wf-003.1.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """pickValue: first_non_null needs at least one non null""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.conditional
    @pytest.mark.inline_javascript
    @pytest.mark.multiple_input
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_2_first_non_null_second_non_null(self):
        """pickValue: first_non_null second item is non null

        Generated from::

            id: first_non_null_second_non_null
            job: val.3.job.yaml
            output:
              out1: foo 3
            tags:
            - conditional
            - inline_javascript
            - multiple_input
            - workflow
            tool: cond-wf-003.1.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """pickValue: first_non_null second item is non null""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.conditional
    @pytest.mark.inline_javascript
    @pytest.mark.multiple_input
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_2_pass_through_required_the_only_non_null(self):
        """pickvalue: the_only_non_null will pass, only for false condition

        Generated from::

            id: pass_through_required_the_only_non_null
            job: val.1.job.yaml
            output:
              out1: Direct
            tags:
            - conditional
            - inline_javascript
            - multiple_input
            - workflow
            tool: cond-wf-004.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """pickvalue: the_only_non_null will pass, only for false condition""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.conditional
    @pytest.mark.inline_javascript
    @pytest.mark.multiple_input
    @pytest.mark.workflow
    @pytest.mark.inputs_should_parse
    @pytest.mark.green
    def test_conformance_v1_2_pass_through_required_fail(self):
        """pickValue: the_only_non_null will fail due to multiple non nulls

        Generated from::

            id: pass_through_required_fail
            job: val.3.job.yaml
            should_fail: true
            tags:
            - conditional
            - inline_javascript
            - multiple_input
            - workflow
            - inputs_should_parse
            tool: cond-wf-004.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """pickValue: the_only_non_null will fail due to multiple non nulls""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.conditional
    @pytest.mark.inline_javascript
    @pytest.mark.multiple_input
    @pytest.mark.workflow
    @pytest.mark.inputs_should_parse
    @pytest.mark.green
    def test_conformance_v1_2_all_non_null_multi_with_non_array_output(self):
        """pickValue: all_non_null will fail validation

        Generated from::

            id: all_non_null_multi_with_non_array_output
            job: val.3.job.yaml
            should_fail: true
            tags:
            - conditional
            - inline_javascript
            - multiple_input
            - workflow
            - inputs_should_parse
            tool: cond-wf-005.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """pickValue: all_non_null will fail validation""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.conditional
    @pytest.mark.inline_javascript
    @pytest.mark.multiple_input
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_2_the_only_non_null_single_true(self):
        """pickValue: the_only_non_null will pass for only one active node

        Generated from::

            id: the_only_non_null_single_true
            job: val.1.job.yaml
            output:
              out1: bar 1
            tags:
            - conditional
            - inline_javascript
            - multiple_input
            - workflow
            tool: cond-wf-006.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """pickValue: the_only_non_null will pass for only one active node""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.conditional
    @pytest.mark.inline_javascript
    @pytest.mark.multiple_input
    @pytest.mark.workflow
    @pytest.mark.inputs_should_parse
    @pytest.mark.green
    def test_conformance_v1_2_the_only_non_null_multi_true(self):
        """pickValue: the_only_non_null will fail with two active nodes

        Generated from::

            id: the_only_non_null_multi_true
            job: val.3.job.yaml
            should_fail: true
            tags:
            - conditional
            - inline_javascript
            - multiple_input
            - workflow
            - inputs_should_parse
            tool: cond-wf-006.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """pickValue: the_only_non_null will fail with two active nodes""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.conditional
    @pytest.mark.inline_javascript
    @pytest.mark.multiple_input
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_2_all_non_null_all_null(self):
        """pickValue: all_non_null will produce a list, even if empty

        Generated from::

            id: all_non_null_all_null
            job: val.0.job.yaml
            output:
              out1: []
            tags:
            - conditional
            - inline_javascript
            - multiple_input
            - workflow
            tool: cond-wf-007.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """pickValue: all_non_null will produce a list, even if empty""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.conditional
    @pytest.mark.inline_javascript
    @pytest.mark.multiple_input
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_2_all_non_null_one_non_null(self):
        """pickValue: all_non_null will produce a list; even if single item list

        Generated from::

            id: all_non_null_one_non_null
            job: val.1.job.yaml
            output:
              out1:
              - bar 1
            tags:
            - conditional
            - inline_javascript
            - multiple_input
            - workflow
            tool: cond-wf-007.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """pickValue: all_non_null will produce a list; even if single item list""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.conditional
    @pytest.mark.inline_javascript
    @pytest.mark.multiple_input
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_2_all_non_null_multi_non_null(self):
        """pickValue: all_non_null will produce a list

        Generated from::

            id: all_non_null_multi_non_null
            job: val.3.job.yaml
            output:
              out1:
              - foo 3
              - bar 3
            tags:
            - conditional
            - inline_javascript
            - multiple_input
            - workflow
            tool: cond-wf-007.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """pickValue: all_non_null will produce a list""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.conditional
    @pytest.mark.inline_javascript
    @pytest.mark.scatter
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_2_condifional_scatter_on_nonscattered_false(self):
        """Simple scatter: conditional on a non scattered variable (False)

        Generated from::

            id: condifional_scatter_on_nonscattered_false
            job: cond15.job.yaml
            output:
              out1: []
            tags:
            - conditional
            - inline_javascript
            - scatter
            - workflow
            tool: cond-wf-009.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Simple scatter: conditional on a non scattered variable (False)""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.conditional
    @pytest.mark.inline_javascript
    @pytest.mark.scatter
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_2_condifional_scatter_on_nonscattered_true(self):
        """Simple scatter: conditional on a non scattered variable (True)

        Generated from::

            id: condifional_scatter_on_nonscattered_true
            job: cond16.job.yaml
            output:
              out1:
              - foo 1
              - foo 2
              - foo 3
              - foo 4
              - foo 5
              - foo 6
            tags:
            - conditional
            - inline_javascript
            - scatter
            - workflow
            tool: cond-wf-009.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Simple scatter: conditional on a non scattered variable (True)""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.conditional
    @pytest.mark.inline_javascript
    @pytest.mark.scatter
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_2_scatter_on_scattered_conditional(self):
        """Simple scatter: Add conditional variable to scatter

        Generated from::

            id: scatter_on_scattered_conditional
            job: val.6.list.job.yaml
            output:
              out1:
              - foo 4
              - foo 5
              - foo 6
            tags:
            - conditional
            - inline_javascript
            - scatter
            - workflow
            tool: cond-wf-010.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Simple scatter: Add conditional variable to scatter""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.conditional
    @pytest.mark.inline_javascript
    @pytest.mark.scatter
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_2_conditionals_nested_cross_scatter(self):
        """nested cross product scatter with condition on one dimension

        Generated from::

            id: conditionals_nested_cross_scatter
            job: cond18.job.yaml
            output:
              out1:
              - - - null
                  - '112'
                  - null
                  - '114'
                - - null
                  - '122'
                  - null
                  - '124'
                - - null
                  - '132'
                  - null
                  - '134'
              - - - null
                  - '212'
                  - null
                  - '214'
                - - null
                  - '222'
                  - null
                  - '224'
                - - null
                  - '232'
                  - null
                  - '234'
            tags:
            - conditional
            - inline_javascript
            - scatter
            - workflow
            tool: cond-wf-011.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """nested cross product scatter with condition on one dimension""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.conditional
    @pytest.mark.inline_javascript
    @pytest.mark.workflow
    @pytest.mark.inputs_should_parse
    @pytest.mark.red
    def test_conformance_v1_2_conditionals_non_boolean_fail(self):
        """Non-boolean values from "when" should fail

        Generated from::

            id: conditionals_non_boolean_fail
            job: val.1.job.yaml
            should_fail: true
            tags:
            - conditional
            - inline_javascript
            - workflow
            - inputs_should_parse
            tool: cond-wf-012.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Non-boolean values from "when" should fail""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.conditional
    @pytest.mark.inline_javascript
    @pytest.mark.scatter
    @pytest.mark.multiple
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_2_conditionals_multi_scatter(self):
        """Scatter two steps, flatten result + pickValue

        Generated from::

            id: conditionals_multi_scatter
            job: cond20.job.yaml
            output:
              out1:
              - foo 2
              - foo 4
              - foo 6
              - bar 1
              - bar 3
              - bar 5
            tags:
            - conditional
            - inline_javascript
            - scatter
            - multiple
            - workflow
            tool: cond-wf-013.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Scatter two steps, flatten result + pickValue""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.conditional
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_2_direct_optional_null_result_nojs(self):
        """simplest conditional pattern (true), no javascript

        Generated from::

            id: direct_optional_null_result_nojs
            job: test-true.yml
            output:
              out1: foo 23
            tags:
            - conditional
            - workflow
            tool: cond-wf-001_nojs.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """simplest conditional pattern (true), no javascript""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.conditional
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_2_direct_optional_nonnull_result_nojs(self):
        """simplest conditional pattern (false), no javascript

        Generated from::

            id: direct_optional_nonnull_result_nojs
            job: test-false.yml
            output:
              out1: null
            tags:
            - conditional
            - workflow
            tool: cond-wf-001_nojs.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """simplest conditional pattern (false), no javascript""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.conditional
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_2_direct_required_nojs(self):
        """Conditional using intermediate WorkflowStep.in input; no javascript

        Generated from::

            id: direct_required_nojs
            job: val.1.job.yaml
            output:
              out1: null
            tags:
            - conditional
            - workflow
            tool: cond-wf-002_nojs.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Conditional using intermediate WorkflowStep.in input; no javascript""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.conditional
    @pytest.mark.multiple_input
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_2_pass_through_required_false_when_nojs(self):
        """Pass through pattern with pickValue: first_non_null; 'when' is false'; no javascript

        Generated from::

            id: pass_through_required_false_when_nojs
            job: test-false.yml
            output:
              out1: Direct
            tags:
            - conditional
            - multiple_input
            - workflow
            tool: cond-wf-003_nojs.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Pass through pattern with pickValue: first_non_null; 'when' is false'; no javascript""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.conditional
    @pytest.mark.multiple_input
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_2_pass_through_required_true_when_nojs(self):
        """pass through pattern with pickvalue: first_non_null; 'when' is true'; no javascript

        Generated from::

            id: pass_through_required_true_when_nojs
            job: test-true.yml
            output:
              out1: foo 23
            tags:
            - conditional
            - multiple_input
            - workflow
            tool: cond-wf-003_nojs.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """pass through pattern with pickvalue: first_non_null; 'when' is true'; no javascript""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.conditional
    @pytest.mark.multiple_input
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_2_first_non_null_first_non_null_nojs(self):
        """pickValue: first_non_null first item is non null; no javascript

        Generated from::

            id: first_non_null_first_non_null_nojs
            job: first-true.yml
            output:
              out1: foo 23
            tags:
            - conditional
            - multiple_input
            - workflow
            tool: cond-wf-003.1_nojs.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """pickValue: first_non_null first item is non null; no javascript""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.conditional
    @pytest.mark.multiple_input
    @pytest.mark.workflow
    @pytest.mark.inputs_should_parse
    @pytest.mark.green
    def test_conformance_v1_2_first_non_null_all_null_nojs(self):
        """pickValue: first_non_null needs at least one non null; no javascript

        Generated from::

            id: first_non_null_all_null_nojs
            job: both-false.yml
            should_fail: true
            tags:
            - conditional
            - multiple_input
            - workflow
            - inputs_should_parse
            tool: cond-wf-003.1_nojs.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """pickValue: first_non_null needs at least one non null; no javascript""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.conditional
    @pytest.mark.multiple_input
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_2_first_non_null_second_non_null_nojs(self):
        """pickValue: first_non_null second item is non null; no javascript

        Generated from::

            id: first_non_null_second_non_null_nojs
            job: second-true.yml
            output:
              out1: foo 23
            tags:
            - conditional
            - multiple_input
            - workflow
            tool: cond-wf-003.1_nojs.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """pickValue: first_non_null second item is non null; no javascript""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.conditional
    @pytest.mark.multiple_input
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_2_pass_through_required_the_only_non_null_nojs(self):
        """pickvalue: the_only_non_null will pass, only for false condition; no javascript

        Generated from::

            id: pass_through_required_the_only_non_null_nojs
            job: test-false.yml
            output:
              out1: Direct
            tags:
            - conditional
            - multiple_input
            - workflow
            tool: cond-wf-004_nojs.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """pickvalue: the_only_non_null will pass, only for false condition; no javascript""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.conditional
    @pytest.mark.multiple_input
    @pytest.mark.workflow
    @pytest.mark.inputs_should_parse
    @pytest.mark.green
    def test_conformance_v1_2_pass_through_required_fail_nojs(self):
        """pickValue: the_only_non_null will fail due to multiple non nulls; no javascript

        Generated from::

            id: pass_through_required_fail_nojs
            job: test-true.yml
            should_fail: true
            tags:
            - conditional
            - multiple_input
            - workflow
            - inputs_should_parse
            tool: cond-wf-004_nojs.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """pickValue: the_only_non_null will fail due to multiple non nulls; no javascript""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.conditional
    @pytest.mark.multiple_input
    @pytest.mark.workflow
    @pytest.mark.inputs_should_parse
    @pytest.mark.green
    def test_conformance_v1_2_all_non_null_multi_with_non_array_output_nojs(self):
        """pickValue: all_non_null will fail validation; no javascript

        Generated from::

            id: all_non_null_multi_with_non_array_output_nojs
            job: test-true.yml
            should_fail: true
            tags:
            - conditional
            - multiple_input
            - workflow
            - inputs_should_parse
            tool: cond-wf-005_nojs.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """pickValue: all_non_null will fail validation; no javascript""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.conditional
    @pytest.mark.multiple_input
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_2_the_only_non_null_single_true_nojs(self):
        """pickValue: the_only_non_null will pass for only one active node; no javascript

        Generated from::

            id: the_only_non_null_single_true_nojs
            job: second-true.yml
            output:
              out1: bar 23
            tags:
            - conditional
            - multiple_input
            - workflow
            tool: cond-wf-006_nojs.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """pickValue: the_only_non_null will pass for only one active node; no javascript""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.conditional
    @pytest.mark.multiple_input
    @pytest.mark.workflow
    @pytest.mark.inputs_should_parse
    @pytest.mark.green
    def test_conformance_v1_2_the_only_non_null_multi_true_nojs(self):
        """pickValue: the_only_non_null will fail with two active nodes; no javascript

        Generated from::

            id: the_only_non_null_multi_true_nojs
            job: both-true.yml
            should_fail: true
            tags:
            - conditional
            - multiple_input
            - workflow
            - inputs_should_parse
            tool: cond-wf-006_nojs.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """pickValue: the_only_non_null will fail with two active nodes; no javascript""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.conditional
    @pytest.mark.multiple_input
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_2_all_non_null_all_null_nojs(self):
        """pickValue: all_non_null will produce a list, even if empty; no javascript

        Generated from::

            id: all_non_null_all_null_nojs
            job: both-false.yml
            output:
              out1: []
            tags:
            - conditional
            - multiple_input
            - workflow
            tool: cond-wf-007_nojs.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """pickValue: all_non_null will produce a list, even if empty; no javascript""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.conditional
    @pytest.mark.multiple_input
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_2_all_non_null_one_non_null_nojs(self):
        """pickValue: all_non_null will produce a list; even if single item list; no javascript

        Generated from::

            id: all_non_null_one_non_null_nojs
            job: second-true.yml
            output:
              out1:
              - bar 23
            tags:
            - conditional
            - multiple_input
            - workflow
            tool: cond-wf-007_nojs.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """pickValue: all_non_null will produce a list; even if single item list; no javascript""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.conditional
    @pytest.mark.multiple_input
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_2_all_non_null_multi_non_null_nojs(self):
        """pickValue: all_non_null will produce a list; no javascript

        Generated from::

            id: all_non_null_multi_non_null_nojs
            job: both-true.yml
            output:
              out1:
              - foo 23
              - bar 23
            tags:
            - conditional
            - multiple_input
            - workflow
            tool: cond-wf-007_nojs.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """pickValue: all_non_null will produce a list; no javascript""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.conditional
    @pytest.mark.scatter
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_2_condifional_scatter_on_nonscattered_false_nojs(self):
        """Simple scatter: conditional on a non scattered variable (False); no javascript

        Generated from::

            id: condifional_scatter_on_nonscattered_false_nojs
            job: test-false.yml
            output:
              out1: []
            tags:
            - conditional
            - scatter
            - workflow
            tool: cond-wf-009_nojs.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Simple scatter: conditional on a non scattered variable (False); no javascript""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.conditional
    @pytest.mark.scatter
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_2_condifional_scatter_on_nonscattered_true_nojs(self):
        """Simple scatter: conditional on a non scattered variable (True); no javascript

        Generated from::

            id: condifional_scatter_on_nonscattered_true_nojs
            job: test-true.yml
            output:
              out1:
              - foo 1
              - foo 2
              - foo 3
              - foo 4
              - foo 5
              - foo 6
            tags:
            - conditional
            - scatter
            - workflow
            tool: cond-wf-009_nojs.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Simple scatter: conditional on a non scattered variable (True); no javascript""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.conditional
    @pytest.mark.scatter
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_2_scatter_on_scattered_conditional_nojs(self):
        """Simple scatter: Add conditional variable to scatter; no javascript

        Generated from::

            id: scatter_on_scattered_conditional_nojs
            job: ../empty.json
            output:
              out1:
              - foo 4
              - foo 5
              - foo 6
            tags:
            - conditional
            - scatter
            - workflow
            tool: cond-wf-010_nojs.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Simple scatter: Add conditional variable to scatter; no javascript""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.conditional
    @pytest.mark.scatter
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_2_conditionals_nested_cross_scatter_nojs(self):
        """nested cross product scatter with condition on one dimension; no javascript

        Generated from::

            id: conditionals_nested_cross_scatter_nojs
            job: ../empty.json
            output:
              out1:
              - - - null
                  - '1123'
                  - null
                  - '1123'
                - - null
                  - '1223'
                  - null
                  - '1223'
                - - null
                  - '1323'
                  - null
                  - '1323'
              - - - null
                  - '2123'
                  - null
                  - '2123'
                - - null
                  - '2223'
                  - null
                  - '2223'
                - - null
                  - '2323'
                  - null
                  - '2323'
            tags:
            - conditional
            - scatter
            - workflow
            tool: cond-wf-011_nojs.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """nested cross product scatter with condition on one dimension; no javascript""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.conditional
    @pytest.mark.workflow
    @pytest.mark.inputs_should_parse
    @pytest.mark.red
    def test_conformance_v1_2_conditionals_non_boolean_fail_nojs(self):
        """Non-boolean values from "when" should fail; no javascript

        Generated from::

            id: conditionals_non_boolean_fail_nojs
            job: ../empty.json
            should_fail: true
            tags:
            - conditional
            - workflow
            - inputs_should_parse
            tool: cond-wf-012_nojs.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Non-boolean values from "when" should fail; no javascript""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.conditional
    @pytest.mark.scatter
    @pytest.mark.multiple
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_2_conditionals_multi_scatter_nojs(self):
        """Scatter two steps, flatten result + pickValue; no javascript

        Generated from::

            id: conditionals_multi_scatter_nojs
            job: ../empty.json
            output:
              out1:
              - foo 2
              - foo 4
              - foo 6
              - bar 1
              - bar 3
              - bar 5
            tags:
            - conditional
            - scatter
            - multiple
            - workflow
            tool: cond-wf-013_nojs.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Scatter two steps, flatten result + pickValue; no javascript""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.conditional
    @pytest.mark.scatter
    @pytest.mark.multiple
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_2_cond_with_defaults_1(self):
        """Default inputs, choose step to run based on what was provided, first case

        Generated from::

            id: cond-with-defaults-1
            job: cond-job.yaml
            output:
              out_file:
              - basename: filename_paired1
                checksum: sha1$668326847b11f0fcaf4a0fba94d79ccf8b9f9213
                class: File
                location: filename_paired1
                size: 34
              - basename: filename_paired2
                checksum: sha1$da959696a42552d21c03f5f1df5d1949a856845e
                class: File
                location: filename_paired2
                size: 34
            tags:
            - conditional
            - scatter
            - multiple
            - workflow
            tool: cond-with-defaults.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Default inputs, choose step to run based on what was provided, first case""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.conditional
    @pytest.mark.scatter
    @pytest.mark.multiple
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_2_cond_with_defaults_2(self):
        """Default inputs, choose step to run based on what was provided, second case

        Generated from::

            id: cond-with-defaults-2
            job: cond-job2.yaml
            output:
              out_file:
              - basename: filename_single
                checksum: sha1$648695b8ae770ae22b24ff7fe798801c9c370dc1
                class: File
                location: filename_single
                size: 12
            tags:
            - conditional
            - scatter
            - multiple
            - workflow
            tool: cond-with-defaults.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Default inputs, choose step to run based on what was provided, second case""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.inline_javascript
    @pytest.mark.secondary_files
    @pytest.mark.command_line_tool
    @pytest.mark.shell_command
    @pytest.mark.red
    def test_conformance_v1_2_command_input_file_expression(self):
        """Confirm CommandInputParameter expression can receive a File object

        Generated from::

            id: command_input_file_expression
            job: rename-inputs.yml
            output:
              output_file:
                checksum: sha1$901c3d387a263c57eaed6f24a82517c1fb0e198d
                class: File
                location: result
                size: 54
            tags:
            - inline_javascript
            - secondary_files
            - command_line_tool
            - shell_command
            tool: rename-inputs.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Confirm CommandInputParameter expression can receive a File object""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.inline_javascript
    @pytest.mark.secondary_files
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_command_output_file_expression(self):
        """Confirm CommandOutputParameter expression can receive a File object

        Generated from::

            id: command_output_file_expression
            output:
              output_file:
                checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                class: File
                location: secondary_file_test.txt
                secondaryFiles:
                - checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                  class: File
                  location: secondary_file_test.txt.accessory
                  size: 0
                size: 0
            tags:
            - inline_javascript
            - secondary_files
            - command_line_tool
            tool: rename-outputs.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Confirm CommandOutputParameter expression can receive a File object""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_2_mixed_version_v10_wf(self):
        """test v1.0 workflow document that runs other versions

        Generated from::

            id: mixed_version_v10_wf
            job: null
            output: {}
            tags:
            - workflow
            tool: wf-v10.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """test v1.0 workflow document that runs other versions""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_2_mixed_version_v11_wf(self):
        """test v1.1 workflow document that runs other versions

        Generated from::

            id: mixed_version_v11_wf
            job: null
            output: {}
            tags:
            - workflow
            tool: wf-v11.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """test v1.1 workflow document that runs other versions""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_2_mixed_version_v12_wf(self):
        """test v1.2 workflow document that runs other versions

        Generated from::

            id: mixed_version_v12_wf
            job: null
            output: {}
            tags:
            - workflow
            tool: wf-v12.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """test v1.2 workflow document that runs other versions""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.json_schema_invalid
    @pytest.mark.green
    def test_conformance_v1_2_invalid_syntax_v10_uses_v12_tool(self):
        """test tool with v1.2 syntax marked as v1.0 (should fail)

        Generated from::

            id: invalid_syntax_v10_uses_v12_tool
            job: null
            should_fail: true
            tags:
            - command_line_tool
            - json_schema_invalid
            tool: invalid-tool-v10.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """test tool with v1.2 syntax marked as v1.0 (should fail)""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.json_schema_invalid
    @pytest.mark.green
    def test_conformance_v1_2_invalid_syntax_v11_uses_v12_tool(self):
        """test tool with v1.2 syntax marked as v1.1 (should fail)

        Generated from::

            id: invalid_syntax_v11_uses_v12_tool
            job: null
            should_fail: true
            tags:
            - command_line_tool
            - json_schema_invalid
            tool: invalid-tool-v11.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """test tool with v1.2 syntax marked as v1.1 (should fail)""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_2_invalid_syntax_v10_uses_v12_workflow(self):
        """test wf with v1.2 syntax marked as v1.0 (should fail)

        Generated from::

            id: invalid_syntax_v10_uses_v12_workflow
            job: null
            should_fail: true
            tags:
            - workflow
            tool: invalid-wf-v10.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """test wf with v1.2 syntax marked as v1.0 (should fail)""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_2_invalid_syntax_v11_uses_v12_workflow(self):
        """test wf with v1.2 syntax marked as v1.1 (should fail)

        Generated from::

            id: invalid_syntax_v11_uses_v12_workflow
            job: null
            should_fail: true
            tags:
            - workflow
            tool: invalid-wf-v11.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """test wf with v1.2 syntax marked as v1.1 (should fail)""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.inputs_should_parse
    @pytest.mark.green
    def test_conformance_v1_2_invalid_syntax_mixed_v12_workflow(self):
        """test 1.2 wf that includes tools that are marked as v1.0 and v1.1 that
contain v1.2 features (should fail)


        Generated from::

            id: invalid_syntax_mixed_v12_workflow
            job: null
            should_fail: true
            tags:
            - workflow
            - inputs_should_parse
            tool: invalid-wf-v12.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """test 1.2 wf that includes tools that are marked as v1.0 and v1.1 that
contain v1.2 features (should fail)
""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.required
    @pytest.mark.red
    def test_conformance_v1_2_cwloutput_nolimit(self):
        """Test that loading from cwl.output.json isn't limited to 64k

        Generated from::

            id: cwloutput_nolimit
            job: null
            output:
              $import: compare-output.json
            tags:
            - command_line_tool
            - required
            tool: cwloutput-nolimit.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test that loading from cwl.output.json isn't limited to 64k""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.required
    @pytest.mark.json_schema_invalid
    @pytest.mark.inputs_should_parse
    @pytest.mark.green
    def test_conformance_v1_2_loadcontents_limit(self):
        """Test that loadContents on a file larger than 64k fails

        Generated from::

            id: loadcontents_limit
            job: input.yml
            output: {}
            should_fail: true
            tags:
            - command_line_tool
            - required
            - json_schema_invalid
            - inputs_should_parse
            tool: loadContents-limit.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test that loadContents on a file larger than 64k fails""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.initial_work_dir
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_iwd_nolimit(self):
        """Test that InitialWorkDir contents can be bigger than 64k

        Generated from::

            id: iwd-nolimit
            job: null
            output:
              filelist:
                basename: out-filelist.txt
                checksum: sha1$57f77b36009332d236b52b4beca77301b503b27c
                class: File
                location: out-filelist.txt
                size: 268866
            tags:
            - initial_work_dir
            - command_line_tool
            tool: iwd-nolimit.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test that InitialWorkDir contents can be bigger than 64k""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.initial_work_dir
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_iwd_jsondump1(self):
        """Test dump object to JSON in InitialWorkDir file contents, no trailing newline

        Generated from::

            id: iwd-jsondump1
            job: null
            output:
              filelist:
                basename: out-filelist.json
                checksum: sha1$5bbeb2a75327927cb97d7e9716c8299682001b36
                class: File
                location: out-filelist.json
                size: 298863
            tags:
            - initial_work_dir
            - command_line_tool
            tool: iwd-jsondump1.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test dump object to JSON in InitialWorkDir file contents, no trailing newline""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.initial_work_dir
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_iwd_jsondump1_nl(self):
        """Test dump object to JSON in InitialWorkDir file contents, with trailing newline

        Generated from::

            id: iwd-jsondump1-nl
            job: null
            output:
              filelist:
                basename: out-filelist.json
                checksum: sha1$7307f027449371b3642c1f7c32124218af0e41b5
                class: File
                location: out-filelist.json
                size: 298864
            tags:
            - initial_work_dir
            - command_line_tool
            tool: iwd-jsondump1-nl.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test dump object to JSON in InitialWorkDir file contents, with trailing newline""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.initial_work_dir
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_iwd_jsondump2(self):
        """Test array to JSON in InitialWorkDir file contents, no trailing newline

        Generated from::

            id: iwd-jsondump2
            job: null
            output:
              filelist:
                basename: out-filelist.json
                checksum: sha1$a0e2225d47c9ed2f07e7633d00dd19d1cbf65c9f
                class: File
                location: out-filelist.json
                size: 298877
            tags:
            - initial_work_dir
            - command_line_tool
            tool: iwd-jsondump2.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test array to JSON in InitialWorkDir file contents, no trailing newline""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.initial_work_dir
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_iwd_jsondump2_nl(self):
        """Test array to JSON in InitialWorkDir file contents, with trailing newline

        Generated from::

            id: iwd-jsondump2-nl
            job: null
            output:
              filelist:
                basename: out-filelist.json
                checksum: sha1$750c95cb45561cd1d863506f82a1a75fffd53a54
                class: File
                location: out-filelist.json
                size: 298878
            tags:
            - initial_work_dir
            - command_line_tool
            tool: iwd-jsondump2-nl.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test array to JSON in InitialWorkDir file contents, with trailing newline""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.initial_work_dir
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_iwd_jsondump3(self):
        """Test number to JSON in InitialWorkDir file contents, no trailing newline

        Generated from::

            id: iwd-jsondump3
            job: null
            output:
              filelist:
                basename: out-number.json
                checksum: sha1$356b190d3274c960b34c2c9538023dda438d67d4
                class: File
                location: out-number.json
                size: 4
            tags:
            - initial_work_dir
            - command_line_tool
            tool: iwd-jsondump3.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test number to JSON in InitialWorkDir file contents, no trailing newline""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.initial_work_dir
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_iwd_jsondump3_nl(self):
        """Test number to JSON in InitialWorkDir file contents, with trailing newline

        Generated from::

            id: iwd-jsondump3-nl
            job: null
            output:
              filelist:
                basename: out-number.json
                checksum: sha1$0b02e6b07d199025bfdcfc6b9830d550a0a6bde9
                class: File
                location: out-number.json
                size: 5
            tags:
            - initial_work_dir
            - command_line_tool
            tool: iwd-jsondump3-nl.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test number to JSON in InitialWorkDir file contents, with trailing newline""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.initial_work_dir
    @pytest.mark.command_line_tool
    @pytest.mark.red
    def test_conformance_v1_2_iwd_passthrough1(self):
        """Test InitialWorkDir file passthrough

        Generated from::

            id: iwd-passthrough1
            job: ../loadContents/input.yml
            output:
              filelist:
                basename: renamed-filelist.txt
                checksum: sha1$57f77b36009332d236b52b4beca77301b503b27c
                class: File
                location: renamed-filelist.txt
                size: 268866
            tags:
            - initial_work_dir
            - command_line_tool
            tool: iwd-passthrough1.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test InitialWorkDir file passthrough""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.initial_work_dir
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_iwd_passthrough2(self):
        """Test InitialWorkDir file object is serialized to json

        Generated from::

            id: iwd-passthrough2
            job: ../loadContents/input.yml
            output:
              out:
                basename: out.txt
                checksum: sha1$406e83b1cd694780f1b3ea4fe8fbb754511fe3f7
                class: File
                location: out.txt
                size: 49
            tags:
            - initial_work_dir
            - command_line_tool
            tool: iwd-passthrough2.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test InitialWorkDir file object is serialized to json""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.initial_work_dir
    @pytest.mark.command_line_tool
    @pytest.mark.red
    def test_conformance_v1_2_iwd_passthrough3(self):
        """Test InitialWorkDir file object is passed through

        Generated from::

            id: iwd-passthrough3
            job: ../loadContents/input.yml
            output:
              filelist:
                basename: renamed-filelist.txt
                checksum: sha1$57f77b36009332d236b52b4beca77301b503b27c
                class: File
                location: renamed-filelist.txt
                size: 268866
            tags:
            - initial_work_dir
            - command_line_tool
            tool: iwd-passthrough3.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test InitialWorkDir file object is passed through""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.initial_work_dir
    @pytest.mark.command_line_tool
    @pytest.mark.red
    def test_conformance_v1_2_iwd_passthrough4(self):
        """Test InitialWorkDir file object is passed through

        Generated from::

            id: iwd-passthrough4
            job: ../loadContents/input.yml
            output:
              filelist:
                basename: inp-filelist.txt
                checksum: sha1$57f77b36009332d236b52b4beca77301b503b27c
                class: File
                location: inp-filelist.txt
                size: 268866
            tags:
            - initial_work_dir
            - command_line_tool
            tool: iwd-passthrough4.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test InitialWorkDir file object is passed through""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.initial_work_dir
    @pytest.mark.command_line_tool
    @pytest.mark.red
    def test_conformance_v1_2_iwd_fileobjs1(self):
        """Test File and Directory object in listing

        Generated from::

            id: iwd-fileobjs1
            job: null
            output:
              filelist:
                basename: inp-filelist.txt
                checksum: sha1$57f77b36009332d236b52b4beca77301b503b27c
                class: File
                location: inp-filelist.txt
                size: 268866
              testdir:
                basename: testdir
                class: Directory
                listing:
                - basename: b
                  checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                  class: File
                  location: b
                  size: 0
                - basename: c
                  class: Directory
                  listing:
                  - basename: d
                    checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                    class: File
                    location: d
                    size: 0
                  location: c
                - basename: a
                  checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                  class: File
                  location: a
                  size: 0
                location: testdir
            tags:
            - initial_work_dir
            - command_line_tool
            tool: iwd-fileobjs1.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test File and Directory object in listing""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.initial_work_dir
    @pytest.mark.command_line_tool
    @pytest.mark.red
    def test_conformance_v1_2_iwd_fileobjs2(self):
        """Test File and Directory object in listing

        Generated from::

            id: iwd-fileobjs2
            job: null
            output:
              filelist:
                basename: inp-filelist.txt
                checksum: sha1$57f77b36009332d236b52b4beca77301b503b27c
                class: File
                location: inp-filelist.txt
                size: 268866
              testdir:
                basename: testdir
                class: Directory
                listing:
                - basename: b
                  checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                  class: File
                  location: b
                  size: 0
                - basename: c
                  class: Directory
                  listing:
                  - basename: d
                    checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                    class: File
                    location: d
                    size: 0
                  location: c
                - basename: a
                  checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                  class: File
                  location: a
                  size: 0
                location: testdir
            tags:
            - initial_work_dir
            - command_line_tool
            tool: iwd-fileobjs2.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test File and Directory object in listing""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.initial_work_dir
    @pytest.mark.command_line_tool
    @pytest.mark.red
    def test_conformance_v1_2_iwd_container_entryname1(self):
        """Test input mount locations when container required

        Generated from::

            id: iwd-container-entryname1
            job: ../loadContents/input.yml
            output:
              head:
                basename: head.txt
                checksum: sha1$8b5071fa49953fcdb8729b16345b7c894b493f83
                class: File
                location: head.txt
                size: 241
            tags:
            - initial_work_dir
            - command_line_tool
            tool: iwd-container-entryname1.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test input mount locations when container required""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.initial_work_dir
    @pytest.mark.command_line_tool
    @pytest.mark.inputs_should_parse
    @pytest.mark.green
    def test_conformance_v1_2_iwd_container_entryname2(self):
        """Test input mount locations when no container (should fail)

        Generated from::

            id: iwd-container-entryname2
            job: ../loadContents/input.yml
            should_fail: true
            tags:
            - initial_work_dir
            - command_line_tool
            - inputs_should_parse
            tool: iwd-container-entryname2.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test input mount locations when no container (should fail)""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.initial_work_dir
    @pytest.mark.command_line_tool
    @pytest.mark.inputs_should_parse
    @pytest.mark.green
    def test_conformance_v1_2_iwd_container_entryname3(self):
        """Test input mount locations when container is a hint (should fail)

        Generated from::

            id: iwd-container-entryname3
            job: ../loadContents/input.yml
            should_fail: true
            tags:
            - initial_work_dir
            - command_line_tool
            - inputs_should_parse
            tool: iwd-container-entryname3.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test input mount locations when container is a hint (should fail)""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.initial_work_dir
    @pytest.mark.command_line_tool
    @pytest.mark.inputs_should_parse
    @pytest.mark.green
    def test_conformance_v1_2_iwd_container_entryname4(self):
        """Must fail if entryname starts with ../

        Generated from::

            id: iwd-container-entryname4
            job: ../loadContents/input.yml
            should_fail: true
            tags:
            - initial_work_dir
            - command_line_tool
            - inputs_should_parse
            tool: iwd-container-entryname4.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Must fail if entryname starts with ../""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.initial_work_dir
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_iwdr_dir_literal_real_file(self):
        """Test directory literal containing a real file

        Generated from::

            id: iwdr_dir_literal_real_file
            job: ../loadContents/input.yml
            output:
              same:
                basename: inp-filelist.txt
                checksum: sha1$57f77b36009332d236b52b4beca77301b503b27c
                class: File
                location: inp-filelist.txt
                size: 268866
            tags:
            - initial_work_dir
            - command_line_tool
            tool: iwdr_dir_literal_real_file.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test directory literal containing a real file""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.initial_work_dir
    @pytest.mark.command_line_tool
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_2_iwd_subdir(self):
        """Test emitting a subdirectory from initial workdir

        Generated from::

            id: iwd-subdir
            job: iwd-subdir-job.yml
            output:
              out:
                basename: c
                class: Directory
                listing:
                - basename: d
                  checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                  class: File
                  location: d
                  size: 0
                location: c
            tags:
            - initial_work_dir
            - command_line_tool
            - workflow
            tool: iwd-subdir-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test emitting a subdirectory from initial workdir""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.subworkflow
    @pytest.mark.scatter
    @pytest.mark.inline_javascript
    @pytest.mark.expression_tool
    @pytest.mark.green
    def test_conformance_v1_2_simple_simple_scatter(self):
        """Two level nested scatter

        Generated from::

            id: simple_simple_scatter
            job: scatter-job.yml
            output:
              result:
              - - ^1a$
                - ^2a$
                - ^3a$
                - ^4a$
              - - ^1b$
                - ^2b$
                - ^3b$
                - ^4b$
              - - ^1c$
                - ^2c$
                - ^3c$
                - ^4c$
              - - ^1d$
                - ^2d$
                - ^3d$
                - ^4d$
            tags:
            - workflow
            - subworkflow
            - scatter
            - inline_javascript
            - expression_tool
            tool: simple-simple-scatter.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Two level nested scatter""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.subworkflow
    @pytest.mark.scatter
    @pytest.mark.inline_javascript
    @pytest.mark.expression_tool
    @pytest.mark.green
    def test_conformance_v1_2_dotproduct_simple_scatter(self):
        """Two level nested scatter: external dotproduct and internal simple

        Generated from::

            id: dotproduct_simple_scatter
            job: scatter2-job.yml
            output:
              result:
              - - ^1aw$
                - ^2aw$
                - ^3aw$
                - ^4aw$
              - - ^1bx$
                - ^2bx$
                - ^3bx$
                - ^4bx$
              - - ^1cy$
                - ^2cy$
                - ^3cy$
                - ^4cy$
              - - ^1dz$
                - ^2dz$
                - ^3dz$
                - ^4dz$
            tags:
            - workflow
            - subworkflow
            - scatter
            - inline_javascript
            - expression_tool
            tool: dotproduct-simple-scatter.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Two level nested scatter: external dotproduct and internal simple""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.subworkflow
    @pytest.mark.scatter
    @pytest.mark.inline_javascript
    @pytest.mark.expression_tool
    @pytest.mark.green
    def test_conformance_v1_2_simple_dotproduct_scatter(self):
        """Two level nested scatter: external simple and internal dotproduct

        Generated from::

            id: simple_dotproduct_scatter
            job: scatter3-job.yml
            output:
              result:
              - - ^15a$
                - ^26a$
                - ^37a$
                - ^48a$
              - - ^15b$
                - ^26b$
                - ^37b$
                - ^48b$
              - - ^15c$
                - ^26c$
                - ^37c$
                - ^48c$
              - - ^15d$
                - ^26d$
                - ^37d$
                - ^48d$
            tags:
            - workflow
            - subworkflow
            - scatter
            - inline_javascript
            - expression_tool
            tool: simple-dotproduct-scatter.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Two level nested scatter: external simple and internal dotproduct""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.subworkflow
    @pytest.mark.scatter
    @pytest.mark.inline_javascript
    @pytest.mark.expression_tool
    @pytest.mark.green
    def test_conformance_v1_2_dotproduct_dotproduct_scatter(self):
        """Two level nested scatter: external dotproduct and internal dotproduct

        Generated from::

            id: dotproduct_dotproduct_scatter
            job: scatter4-job.yml
            output:
              result:
              - - ^15aw$
                - ^26aw$
                - ^37aw$
                - ^48aw$
              - - ^15bx$
                - ^26bx$
                - ^37bx$
                - ^48bx$
              - - ^15cy$
                - ^26cy$
                - ^37cy$
                - ^48cy$
              - - ^15dz$
                - ^26dz$
                - ^37dz$
                - ^48dz$
            tags:
            - workflow
            - subworkflow
            - scatter
            - inline_javascript
            - expression_tool
            tool: dotproduct-dotproduct-scatter.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Two level nested scatter: external dotproduct and internal dotproduct""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.subworkflow
    @pytest.mark.scatter
    @pytest.mark.inline_javascript
    @pytest.mark.expression_tool
    @pytest.mark.green
    def test_conformance_v1_2_flat_crossproduct_simple_scatter(self):
        """Two level nested scatter: external flat_crossproduct and internal simple

        Generated from::

            id: flat_crossproduct_simple_scatter
            job: scatter2-job.yml
            output:
              result:
              - - ^1aw$
                - ^2aw$
                - ^3aw$
                - ^4aw$
              - - ^1ax$
                - ^2ax$
                - ^3ax$
                - ^4ax$
              - - ^1ay$
                - ^2ay$
                - ^3ay$
                - ^4ay$
              - - ^1az$
                - ^2az$
                - ^3az$
                - ^4az$
              - - ^1bw$
                - ^2bw$
                - ^3bw$
                - ^4bw$
              - - ^1bx$
                - ^2bx$
                - ^3bx$
                - ^4bx$
              - - ^1by$
                - ^2by$
                - ^3by$
                - ^4by$
              - - ^1bz$
                - ^2bz$
                - ^3bz$
                - ^4bz$
              - - ^1cw$
                - ^2cw$
                - ^3cw$
                - ^4cw$
              - - ^1cx$
                - ^2cx$
                - ^3cx$
                - ^4cx$
              - - ^1cy$
                - ^2cy$
                - ^3cy$
                - ^4cy$
              - - ^1cz$
                - ^2cz$
                - ^3cz$
                - ^4cz$
              - - ^1dw$
                - ^2dw$
                - ^3dw$
                - ^4dw$
              - - ^1dx$
                - ^2dx$
                - ^3dx$
                - ^4dx$
              - - ^1dy$
                - ^2dy$
                - ^3dy$
                - ^4dy$
              - - ^1dz$
                - ^2dz$
                - ^3dz$
                - ^4dz$
            tags:
            - workflow
            - subworkflow
            - scatter
            - inline_javascript
            - expression_tool
            tool: flat-crossproduct-simple-scatter.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Two level nested scatter: external flat_crossproduct and internal simple""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.subworkflow
    @pytest.mark.scatter
    @pytest.mark.inline_javascript
    @pytest.mark.expression_tool
    @pytest.mark.green
    def test_conformance_v1_2_simple_flat_crossproduct_scatter(self):
        """Two level nested scatter: external simple and internal flat_crossproduct

        Generated from::

            id: simple_flat_crossproduct_scatter
            job: scatter3-job.yml
            output:
              result:
              - - ^15a$
                - ^16a$
                - ^17a$
                - ^18a$
                - ^25a$
                - ^26a$
                - ^27a$
                - ^28a$
                - ^35a$
                - ^36a$
                - ^37a$
                - ^38a$
                - ^45a$
                - ^46a$
                - ^47a$
                - ^48a$
              - - ^15b$
                - ^16b$
                - ^17b$
                - ^18b$
                - ^25b$
                - ^26b$
                - ^27b$
                - ^28b$
                - ^35b$
                - ^36b$
                - ^37b$
                - ^38b$
                - ^45b$
                - ^46b$
                - ^47b$
                - ^48b$
              - - ^15c$
                - ^16c$
                - ^17c$
                - ^18c$
                - ^25c$
                - ^26c$
                - ^27c$
                - ^28c$
                - ^35c$
                - ^36c$
                - ^37c$
                - ^38c$
                - ^45c$
                - ^46c$
                - ^47c$
                - ^48c$
              - - ^15d$
                - ^16d$
                - ^17d$
                - ^18d$
                - ^25d$
                - ^26d$
                - ^27d$
                - ^28d$
                - ^35d$
                - ^36d$
                - ^37d$
                - ^38d$
                - ^45d$
                - ^46d$
                - ^47d$
                - ^48d$
            tags:
            - workflow
            - subworkflow
            - scatter
            - inline_javascript
            - expression_tool
            tool: simple-flat-crossproduct-scatter.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Two level nested scatter: external simple and internal flat_crossproduct""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.subworkflow
    @pytest.mark.scatter
    @pytest.mark.inline_javascript
    @pytest.mark.expression_tool
    @pytest.mark.green
    def test_conformance_v1_2_flat_crossproduct_flat_crossproduct_scatter(self):
        """Two level nested scatter: external flat_crossproduct and internal flat_crossproduct

        Generated from::

            id: flat_crossproduct_flat_crossproduct_scatter
            job: scatter4-job.yml
            output:
              result:
              - - ^15aw$
                - ^16aw$
                - ^17aw$
                - ^18aw$
                - ^25aw$
                - ^26aw$
                - ^27aw$
                - ^28aw$
                - ^35aw$
                - ^36aw$
                - ^37aw$
                - ^38aw$
                - ^45aw$
                - ^46aw$
                - ^47aw$
                - ^48aw$
              - - ^15ax$
                - ^16ax$
                - ^17ax$
                - ^18ax$
                - ^25ax$
                - ^26ax$
                - ^27ax$
                - ^28ax$
                - ^35ax$
                - ^36ax$
                - ^37ax$
                - ^38ax$
                - ^45ax$
                - ^46ax$
                - ^47ax$
                - ^48ax$
              - - ^15ay$
                - ^16ay$
                - ^17ay$
                - ^18ay$
                - ^25ay$
                - ^26ay$
                - ^27ay$
                - ^28ay$
                - ^35ay$
                - ^36ay$
                - ^37ay$
                - ^38ay$
                - ^45ay$
                - ^46ay$
                - ^47ay$
                - ^48ay$
              - - ^15az$
                - ^16az$
                - ^17az$
                - ^18az$
                - ^25az$
                - ^26az$
                - ^27az$
                - ^28az$
                - ^35az$
                - ^36az$
                - ^37az$
                - ^38az$
                - ^45az$
                - ^46az$
                - ^47az$
                - ^48az$
              - - ^15bw$
                - ^16bw$
                - ^17bw$
                - ^18bw$
                - ^25bw$
                - ^26bw$
                - ^27bw$
                - ^28bw$
                - ^35bw$
                - ^36bw$
                - ^37bw$
                - ^38bw$
                - ^45bw$
                - ^46bw$
                - ^47bw$
                - ^48bw$
              - - ^15bx$
                - ^16bx$
                - ^17bx$
                - ^18bx$
                - ^25bx$
                - ^26bx$
                - ^27bx$
                - ^28bx$
                - ^35bx$
                - ^36bx$
                - ^37bx$
                - ^38bx$
                - ^45bx$
                - ^46bx$
                - ^47bx$
                - ^48bx$
              - - ^15by$
                - ^16by$
                - ^17by$
                - ^18by$
                - ^25by$
                - ^26by$
                - ^27by$
                - ^28by$
                - ^35by$
                - ^36by$
                - ^37by$
                - ^38by$
                - ^45by$
                - ^46by$
                - ^47by$
                - ^48by$
              - - ^15bz$
                - ^16bz$
                - ^17bz$
                - ^18bz$
                - ^25bz$
                - ^26bz$
                - ^27bz$
                - ^28bz$
                - ^35bz$
                - ^36bz$
                - ^37bz$
                - ^38bz$
                - ^45bz$
                - ^46bz$
                - ^47bz$
                - ^48bz$
              - - ^15cw$
                - ^16cw$
                - ^17cw$
                - ^18cw$
                - ^25cw$
                - ^26cw$
                - ^27cw$
                - ^28cw$
                - ^35cw$
                - ^36cw$
                - ^37cw$
                - ^38cw$
                - ^45cw$
                - ^46cw$
                - ^47cw$
                - ^48cw$
              - - ^15cx$
                - ^16cx$
                - ^17cx$
                - ^18cx$
                - ^25cx$
                - ^26cx$
                - ^27cx$
                - ^28cx$
                - ^35cx$
                - ^36cx$
                - ^37cx$
                - ^38cx$
                - ^45cx$
                - ^46cx$
                - ^47cx$
                - ^48cx$
              - - ^15cy$
                - ^16cy$
                - ^17cy$
                - ^18cy$
                - ^25cy$
                - ^26cy$
                - ^27cy$
                - ^28cy$
                - ^35cy$
                - ^36cy$
                - ^37cy$
                - ^38cy$
                - ^45cy$
                - ^46cy$
                - ^47cy$
                - ^48cy$
              - - ^15cz$
                - ^16cz$
                - ^17cz$
                - ^18cz$
                - ^25cz$
                - ^26cz$
                - ^27cz$
                - ^28cz$
                - ^35cz$
                - ^36cz$
                - ^37cz$
                - ^38cz$
                - ^45cz$
                - ^46cz$
                - ^47cz$
                - ^48cz$
              - - ^15dw$
                - ^16dw$
                - ^17dw$
                - ^18dw$
                - ^25dw$
                - ^26dw$
                - ^27dw$
                - ^28dw$
                - ^35dw$
                - ^36dw$
                - ^37dw$
                - ^38dw$
                - ^45dw$
                - ^46dw$
                - ^47dw$
                - ^48dw$
              - - ^15dx$
                - ^16dx$
                - ^17dx$
                - ^18dx$
                - ^25dx$
                - ^26dx$
                - ^27dx$
                - ^28dx$
                - ^35dx$
                - ^36dx$
                - ^37dx$
                - ^38dx$
                - ^45dx$
                - ^46dx$
                - ^47dx$
                - ^48dx$
              - - ^15dy$
                - ^16dy$
                - ^17dy$
                - ^18dy$
                - ^25dy$
                - ^26dy$
                - ^27dy$
                - ^28dy$
                - ^35dy$
                - ^36dy$
                - ^37dy$
                - ^38dy$
                - ^45dy$
                - ^46dy$
                - ^47dy$
                - ^48dy$
              - - ^15dz$
                - ^16dz$
                - ^17dz$
                - ^18dz$
                - ^25dz$
                - ^26dz$
                - ^27dz$
                - ^28dz$
                - ^35dz$
                - ^36dz$
                - ^37dz$
                - ^38dz$
                - ^45dz$
                - ^46dz$
                - ^47dz$
                - ^48dz$
            tags:
            - workflow
            - subworkflow
            - scatter
            - inline_javascript
            - expression_tool
            tool: flat-crossproduct-flat-crossproduct-scatter.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Two level nested scatter: external flat_crossproduct and internal flat_crossproduct""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.subworkflow
    @pytest.mark.scatter
    @pytest.mark.inline_javascript
    @pytest.mark.expression_tool
    @pytest.mark.green
    def test_conformance_v1_2_nested_crossproduct_simple_scatter(self):
        """Two level nested scatter: external nested_crossproduct and internal simple

        Generated from::

            id: nested_crossproduct_simple_scatter
            job: scatter2-job.yml
            output:
              result:
              - - - ^1aw$
                  - ^2aw$
                  - ^3aw$
                  - ^4aw$
                - - ^1ax$
                  - ^2ax$
                  - ^3ax$
                  - ^4ax$
                - - ^1ay$
                  - ^2ay$
                  - ^3ay$
                  - ^4ay$
                - - ^1az$
                  - ^2az$
                  - ^3az$
                  - ^4az$
              - - - ^1bw$
                  - ^2bw$
                  - ^3bw$
                  - ^4bw$
                - - ^1bx$
                  - ^2bx$
                  - ^3bx$
                  - ^4bx$
                - - ^1by$
                  - ^2by$
                  - ^3by$
                  - ^4by$
                - - ^1bz$
                  - ^2bz$
                  - ^3bz$
                  - ^4bz$
              - - - ^1cw$
                  - ^2cw$
                  - ^3cw$
                  - ^4cw$
                - - ^1cx$
                  - ^2cx$
                  - ^3cx$
                  - ^4cx$
                - - ^1cy$
                  - ^2cy$
                  - ^3cy$
                  - ^4cy$
                - - ^1cz$
                  - ^2cz$
                  - ^3cz$
                  - ^4cz$
              - - - ^1dw$
                  - ^2dw$
                  - ^3dw$
                  - ^4dw$
                - - ^1dx$
                  - ^2dx$
                  - ^3dx$
                  - ^4dx$
                - - ^1dy$
                  - ^2dy$
                  - ^3dy$
                  - ^4dy$
                - - ^1dz$
                  - ^2dz$
                  - ^3dz$
                  - ^4dz$
            tags:
            - workflow
            - subworkflow
            - scatter
            - inline_javascript
            - expression_tool
            tool: nested-crossproduct-simple-scatter.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Two level nested scatter: external nested_crossproduct and internal simple""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.subworkflow
    @pytest.mark.scatter
    @pytest.mark.inline_javascript
    @pytest.mark.expression_tool
    @pytest.mark.green
    def test_conformance_v1_2_simple_nested_crossproduct_scatter(self):
        """Two level nested scatter: external simple and internal nested_crossproduct

        Generated from::

            id: simple_nested_crossproduct_scatter
            job: scatter3-job.yml
            output:
              result:
              - - - ^15a$
                  - ^16a$
                  - ^17a$
                  - ^18a$
                - - ^25a$
                  - ^26a$
                  - ^27a$
                  - ^28a$
                - - ^35a$
                  - ^36a$
                  - ^37a$
                  - ^38a$
                - - ^45a$
                  - ^46a$
                  - ^47a$
                  - ^48a$
              - - - ^15b$
                  - ^16b$
                  - ^17b$
                  - ^18b$
                - - ^25b$
                  - ^26b$
                  - ^27b$
                  - ^28b$
                - - ^35b$
                  - ^36b$
                  - ^37b$
                  - ^38b$
                - - ^45b$
                  - ^46b$
                  - ^47b$
                  - ^48b$
              - - - ^15c$
                  - ^16c$
                  - ^17c$
                  - ^18c$
                - - ^25c$
                  - ^26c$
                  - ^27c$
                  - ^28c$
                - - ^35c$
                  - ^36c$
                  - ^37c$
                  - ^38c$
                - - ^45c$
                  - ^46c$
                  - ^47c$
                  - ^48c$
              - - - ^15d$
                  - ^16d$
                  - ^17d$
                  - ^18d$
                - - ^25d$
                  - ^26d$
                  - ^27d$
                  - ^28d$
                - - ^35d$
                  - ^36d$
                  - ^37d$
                  - ^38d$
                - - ^45d$
                  - ^46d$
                  - ^47d$
                  - ^48d$
            tags:
            - workflow
            - subworkflow
            - scatter
            - inline_javascript
            - expression_tool
            tool: simple-nested-crossproduct-scatter.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Two level nested scatter: external simple and internal nested_crossproduct""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.subworkflow
    @pytest.mark.scatter
    @pytest.mark.inline_javascript
    @pytest.mark.expression_tool
    @pytest.mark.green
    def test_conformance_v1_2_nested_crossproduct_nested_crossproduct_scatter(self):
        """Two level nested scatter: external nested_crossproduct and internal nested_crossproduct

        Generated from::

            id: nested_crossproduct_nested_crossproduct_scatter
            job: scatter4-job.yml
            output:
              result:
              - - - - ^15aw$
                    - ^16aw$
                    - ^17aw$
                    - ^18aw$
                  - - ^25aw$
                    - ^26aw$
                    - ^27aw$
                    - ^28aw$
                  - - ^35aw$
                    - ^36aw$
                    - ^37aw$
                    - ^38aw$
                  - - ^45aw$
                    - ^46aw$
                    - ^47aw$
                    - ^48aw$
                - - - ^15ax$
                    - ^16ax$
                    - ^17ax$
                    - ^18ax$
                  - - ^25ax$
                    - ^26ax$
                    - ^27ax$
                    - ^28ax$
                  - - ^35ax$
                    - ^36ax$
                    - ^37ax$
                    - ^38ax$
                  - - ^45ax$
                    - ^46ax$
                    - ^47ax$
                    - ^48ax$
                - - - ^15ay$
                    - ^16ay$
                    - ^17ay$
                    - ^18ay$
                  - - ^25ay$
                    - ^26ay$
                    - ^27ay$
                    - ^28ay$
                  - - ^35ay$
                    - ^36ay$
                    - ^37ay$
                    - ^38ay$
                  - - ^45ay$
                    - ^46ay$
                    - ^47ay$
                    - ^48ay$
                - - - ^15az$
                    - ^16az$
                    - ^17az$
                    - ^18az$
                  - - ^25az$
                    - ^26az$
                    - ^27az$
                    - ^28az$
                  - - ^35az$
                    - ^36az$
                    - ^37az$
                    - ^38az$
                  - - ^45az$
                    - ^46az$
                    - ^47az$
                    - ^48az$
              - - - - ^15bw$
                    - ^16bw$
                    - ^17bw$
                    - ^18bw$
                  - - ^25bw$
                    - ^26bw$
                    - ^27bw$
                    - ^28bw$
                  - - ^35bw$
                    - ^36bw$
                    - ^37bw$
                    - ^38bw$
                  - - ^45bw$
                    - ^46bw$
                    - ^47bw$
                    - ^48bw$
                - - - ^15bx$
                    - ^16bx$
                    - ^17bx$
                    - ^18bx$
                  - - ^25bx$
                    - ^26bx$
                    - ^27bx$
                    - ^28bx$
                  - - ^35bx$
                    - ^36bx$
                    - ^37bx$
                    - ^38bx$
                  - - ^45bx$
                    - ^46bx$
                    - ^47bx$
                    - ^48bx$
                - - - ^15by$
                    - ^16by$
                    - ^17by$
                    - ^18by$
                  - - ^25by$
                    - ^26by$
                    - ^27by$
                    - ^28by$
                  - - ^35by$
                    - ^36by$
                    - ^37by$
                    - ^38by$
                  - - ^45by$
                    - ^46by$
                    - ^47by$
                    - ^48by$
                - - - ^15bz$
                    - ^16bz$
                    - ^17bz$
                    - ^18bz$
                  - - ^25bz$
                    - ^26bz$
                    - ^27bz$
                    - ^28bz$
                  - - ^35bz$
                    - ^36bz$
                    - ^37bz$
                    - ^38bz$
                  - - ^45bz$
                    - ^46bz$
                    - ^47bz$
                    - ^48bz$
              - - - - ^15cw$
                    - ^16cw$
                    - ^17cw$
                    - ^18cw$
                  - - ^25cw$
                    - ^26cw$
                    - ^27cw$
                    - ^28cw$
                  - - ^35cw$
                    - ^36cw$
                    - ^37cw$
                    - ^38cw$
                  - - ^45cw$
                    - ^46cw$
                    - ^47cw$
                    - ^48cw$
                - - - ^15cx$
                    - ^16cx$
                    - ^17cx$
                    - ^18cx$
                  - - ^25cx$
                    - ^26cx$
                    - ^27cx$
                    - ^28cx$
                  - - ^35cx$
                    - ^36cx$
                    - ^37cx$
                    - ^38cx$
                  - - ^45cx$
                    - ^46cx$
                    - ^47cx$
                    - ^48cx$
                - - - ^15cy$
                    - ^16cy$
                    - ^17cy$
                    - ^18cy$
                  - - ^25cy$
                    - ^26cy$
                    - ^27cy$
                    - ^28cy$
                  - - ^35cy$
                    - ^36cy$
                    - ^37cy$
                    - ^38cy$
                  - - ^45cy$
                    - ^46cy$
                    - ^47cy$
                    - ^48cy$
                - - - ^15cz$
                    - ^16cz$
                    - ^17cz$
                    - ^18cz$
                  - - ^25cz$
                    - ^26cz$
                    - ^27cz$
                    - ^28cz$
                  - - ^35cz$
                    - ^36cz$
                    - ^37cz$
                    - ^38cz$
                  - - ^45cz$
                    - ^46cz$
                    - ^47cz$
                    - ^48cz$
              - - - - ^15dw$
                    - ^16dw$
                    - ^17dw$
                    - ^18dw$
                  - - ^25dw$
                    - ^26dw$
                    - ^27dw$
                    - ^28dw$
                  - - ^35dw$
                    - ^36dw$
                    - ^37dw$
                    - ^38dw$
                  - - ^45dw$
                    - ^46dw$
                    - ^47dw$
                    - ^48dw$
                - - - ^15dx$
                    - ^16dx$
                    - ^17dx$
                    - ^18dx$
                  - - ^25dx$
                    - ^26dx$
                    - ^27dx$
                    - ^28dx$
                  - - ^35dx$
                    - ^36dx$
                    - ^37dx$
                    - ^38dx$
                  - - ^45dx$
                    - ^46dx$
                    - ^47dx$
                    - ^48dx$
                - - - ^15dy$
                    - ^16dy$
                    - ^17dy$
                    - ^18dy$
                  - - ^25dy$
                    - ^26dy$
                    - ^27dy$
                    - ^28dy$
                  - - ^35dy$
                    - ^36dy$
                    - ^37dy$
                    - ^38dy$
                  - - ^45dy$
                    - ^46dy$
                    - ^47dy$
                    - ^48dy$
                - - - ^15dz$
                    - ^16dz$
                    - ^17dz$
                    - ^18dz$
                  - - ^25dz$
                    - ^26dz$
                    - ^27dz$
                    - ^28dz$
                  - - ^35dz$
                    - ^36dz$
                    - ^37dz$
                    - ^38dz$
                  - - ^45dz$
                    - ^46dz$
                    - ^47dz$
                    - ^48dz$
            tags:
            - workflow
            - subworkflow
            - scatter
            - inline_javascript
            - expression_tool
            tool: nested-crossproduct-nested-crossproduct-scatter.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Two level nested scatter: external nested_crossproduct and internal nested_crossproduct""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.inputs_should_parse
    @pytest.mark.green
    def test_conformance_v1_2_params_broken_null(self):
        """Test parameter reference that refers to null.something

        Generated from::

            id: params_broken_null
            job: tests/empty.json
            should_fail: true
            tags:
            - required
            - command_line_tool
            - inputs_should_parse
            tool: tests/params_broken_null.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test parameter reference that refers to null.something""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.inputs_should_parse
    @pytest.mark.green
    def test_conformance_v1_2_length_for_non_array(self):
        """Test parameter reference that refers to length of non-array input

        Generated from::

            id: length_for_non_array
            job: tests/empty.json
            should_fail: true
            tags:
            - required
            - command_line_tool
            - inputs_should_parse
            tool: tests/params_broken_length_of_non_list.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test parameter reference that refers to length of non-array input""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_user_defined_length_in_parameter_reference(self):
        """Test 'length' in parameter reference where it does not refer to length of an array input

        Generated from::

            id: user_defined_length_in_parameter_reference
            job: tests/length_non_array_input.yml
            output:
              output1: 1
              output2: 2
              output3: 3
            tags:
            - required
            - command_line_tool
            tool: tests/params_input_length_non_array.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test 'length' in parameter reference where it does not refer to length of an array input""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.required
    @pytest.mark.green
    def test_conformance_v1_2_directory_literal_with_literal_file_in_subdir_nostdin(self):
        """Test non-stdin reference to literal File via a nested Directory literal

        Generated from::

            id: directory_literal_with_literal_file_in_subdir_nostdin
            job: tests/cat-from-dir-with-literal-file-in-subdir.yaml
            output:
              output_file:
                checksum: sha1$ef88e689559565999700d6fea7cf7ba306d04360
                class: File
                size: 26
            tags:
            - command_line_tool
            - required
            tool: tests/cat4-from-dir.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test non-stdin reference to literal File via a nested Directory literal""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_colon_in_paths(self):
        """Confirm that colons are tolerated in input paths, string values, stdout shortcut, and output file & directory names

        Generated from::

            id: colon_in_paths
            job: tests/colon:test:job.yaml
            output:
              log:
                basename: re:sult
                checksum: sha1$d7d6491030bfa0ce17bab3a648e603f2a55bf503
                class: File
                size: 14
              result:
                basename: A:Gln2Cys_result
                class: Directory
                listing:
                - basename: A:Gln2Cys
                  checksum: sha1$2928c9c6fa02098aee8c31bf44099f3bf8c91013
                  class: File
                  size: 18
            tags:
            - required
            - command_line_tool
            tool: tests/colon:test.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Confirm that colons are tolerated in input paths, string values, stdout shortcut, and output file & directory names""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_colon_in_output_path(self):
        """Confirm that colons are tolerated in output directory names

        Generated from::

            id: colon_in_output_path
            job: tests/colon_test_output_job.yaml
            output:
              result:
                basename: A:Gln2Cys_result
                class: Directory
                listing:
                - basename: hello.txt
                  checksum: sha1$47a013e660d408619d894b20806b1d5086aab03b
                  class: File
                  size: 13
            tags:
            - required
            - command_line_tool
            tool: tests/colon_test_output.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Confirm that colons are tolerated in output directory names""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_record_with_default(self):
        """Confirm that records with defaults are accepted

        Generated from::

            id: record_with_default
            output:
              same_record:
                fifth: 4200000000000000000000000000000000000000000
                first: y
                fourth: 4242424242
                second: 23
                sixth:
                  basename: whale.txt
                  checksum: sha1$327fc7aedf4f6b69a42a7c8b808dc5a7aff61376
                  class: File
                  size: 1111
                third: 2.3
            tags:
            - required
            - command_line_tool
            tool: tests/paramref_arguments_roundtrip.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Confirm that records with defaults are accepted""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.inline_javascript
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_record_outputeval(self):
        """Use of outputEval on a record itself, not the fields of the record

        Generated from::

            id: record_outputeval
            output:
              references:
                annotation_gtf:
                  basename: gencode.vM21.primary_assembly.annotation.gtf
                  checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                  class: File
                  size: 0
                genome_fa:
                  basename: GRCm38.primary_assembly.genome.fa
                  checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                  class: File
                  size: 0
            tags:
            - inline_javascript
            - command_line_tool
            tool: tests/record_outputeval.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Use of outputEval on a record itself, not the fields of the record""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_record_outputeval_nojs(self):
        """Use of outputEval on a record itself, not the fields of the record (without javascript)

        Generated from::

            id: record_outputeval_nojs
            output:
              references:
                annotation_gtf: gencode.vM21.primary_assembly.annotation.gtf
                genome_fa: GRCm38.primary_assembly.genome.fa
              summary:
                checksum: sha1$c0bf6c4db73d4fc08ee24c7288825c09f9cb3cea
                class: File
                size: 79
            tags:
            - required
            - command_line_tool
            tool: tests/record_outputeval_nojs.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Use of outputEval on a record itself, not the fields of the record (without javascript)""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.inline_javascript
    @pytest.mark.expression_tool
    @pytest.mark.green
    def test_conformance_v1_2_staging_basename(self):
        """Use of expression tool to change basename of file, then correctly staging
the file using the new name.


        Generated from::

            id: staging-basename
            output: {}
            tags:
            - workflow
            - inline_javascript
            - expression_tool
            tool: tests/staging-basename/wf_ren.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Use of expression tool to change basename of file, then correctly staging
the file using the new name.
""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_runtime_outdir(self):
        """Use of $(runtime.outdir) for outputBinding glob.


        Generated from::

            id: runtime-outdir
            output:
              stuff:
                class: Directory
                listing:
                - basename: baz.txt
                  checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                  class: File
                  size: 0
                - basename: foo
                  class: Directory
                  listing:
                  - basename: bar.txt
                    checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                    class: File
                    size: 0
            tags:
            - required
            - command_line_tool
            tool: tests/runtime-outdir.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Use of $(runtime.outdir) for outputBinding glob.
""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.command_line_tool
    @pytest.mark.required
    @pytest.mark.green
    def test_conformance_v1_2_record_order_with_input_bindings(self):
        """Test sorting arguments at each level (inputBinding for all levels)

        Generated from::

            id: record_order_with_input_bindings
            job: tests/record-order-job.json
            output:
              args:
              - -a
              - -b
              - '1'
              - -c
              - '3'
              - -d
              - -e
              - '2'
              - -f
              - '4'
            tags:
            - command_line_tool
            - required
            tool: tests/record-order.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test sorting arguments at each level (inputBinding for all levels)""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_2_output_reference_workflow_input(self):
        """Direct use of Workflow level input fields in the outputs.


        Generated from::

            id: output_reference_workflow_input
            output:
              last: me
            tags:
            - required
            - workflow
            tool: tests/output_reference_workflow_input.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Direct use of Workflow level input fields in the outputs.
""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.shell_command
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_stdout_chained_commands(self):
        """Test that chaining two echo calls causes the workflow tool to emit the output to stdout.
This is to confirm that the workflow tool will **not** create an expression such as
`echo a && echo b > out.txt`, but instead will produce the correct `echo a && echo b`,
and capture the output correctly.


        Generated from::

            id: stdout_chained_commands
            output:
              out: 'a
            
                b
            
                '
            tags:
            - shell_command
            - command_line_tool
            tool: tests/stdout_chained_commands.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test that chaining two echo calls causes the workflow tool to emit the output to stdout.
This is to confirm that the workflow tool will **not** create an expression such as
`echo a && echo b > out.txt`, but instead will produce the correct `echo a && echo b`,
and capture the output correctly.
""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.multiple_input
    @pytest.mark.green
    def test_conformance_v1_2_multiple_input_feature_requirement(self):
        """MultipleInputFeatureRequirement on workflow outputs.


        Generated from::

            id: multiple-input-feature-requirement
            output:
              hello_world_in_two_lines:
              - 'hello
            
                '
              - 'world
            
                '
            tags:
            - workflow
            - multiple_input
            tool: tests/multiple_input_feature_requirement.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """MultipleInputFeatureRequirement on workflow outputs.
""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.inline_javascript
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_js_input_record(self):
        """A test case for JS with an input record.


        Generated from::

            id: js-input-record
            job: tests/js-input-record.json
            output:
              out: 'JS
            
                with
            
                record'
            tags:
            - inline_javascript
            - command_line_tool
            tool: tests/js-input-record.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """A test case for JS with an input record.
""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.workflow
    @pytest.mark.schema_def
    @pytest.mark.green
    def test_conformance_v1_2_schemadef_types_with_import(self):
        """Test SchemaDefRequirement with a workflow, with the `$import` under types. It is similar to schemadef-wf, but the `$import` is different.

        Generated from::

            id: schemadef_types_with_import
            job: tests/schemadef_types_with_import-job.json
            output:
              out: '1970-01-01T00:00:00Z
            
                '
            tags:
            - workflow
            - schema_def
            tool: tests/schemadef_types_with_import-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test SchemaDefRequirement with a workflow, with the `$import` under types. It is similar to schemadef-wf, but the `$import` is different.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_filename_with_hash_mark(self):
        """Test for correct handling of URL-quoting in filename to refer to filename containing a hash mark

        Generated from::

            id: filename_with_hash_mark
            job: tests/octo.yml
            output:
              output:
                basename: output
                checksum: sha1$06b0c59808c236447d065db8f7d2a60de0a805bf
                class: File
                location: output
                size: 8
            tags:
            - required
            - command_line_tool
            tool: tests/cat-tool.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test for correct handling of URL-quoting in filename to refer to filename containing a hash mark""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.inputs_should_parse
    @pytest.mark.green
    def test_conformance_v1_2_capture_files(self):
        """Test that a type error is raised if directories are returned by glob evaluation when type is File

        Generated from::

            id: capture_files
            job: tests/dir-job.yml
            should_fail: true
            tags:
            - required
            - command_line_tool
            - inputs_should_parse
            tool: tests/capture-files.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test that a type error is raised if directories are returned by glob evaluation when type is File""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.inputs_should_parse
    @pytest.mark.green
    def test_conformance_v1_2_capture_dirs(self):
        """Test that a type error is raised if files are returned by glob evaluation when type is Directory

        Generated from::

            id: capture_dirs
            job: tests/dir-job.yml
            should_fail: true
            tags:
            - required
            - command_line_tool
            - inputs_should_parse
            tool: tests/capture-dirs.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test that a type error is raised if files are returned by glob evaluation when type is Directory""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_capture_files_and_dirs(self):
        """Test that both files and directories are captured by glob evaluation when type is [Directory, File]

        Generated from::

            id: capture_files_and_dirs
            job: tests/dir-job.yml
            output:
              result:
              - basename: a
                checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                class: File
                size: 0
              - basename: b
                checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                class: File
                size: 0
              - basename: c
                class: Directory
                listing:
                - basename: d
                  checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                  class: File
                  size: 0
            tags:
            - required
            - command_line_tool
            tool: tests/capture-files-and-dirs.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Test that both files and directories are captured by glob evaluation when type is [Directory, File]""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.inline_javascript
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_very_big_and_very_floats(self):
        """Confirm that very big and very small numbers are represented using decimals, not scientific notation

        Generated from::

            id: very_big_and_very_floats
            job: tests/empty.json
            output:
              result: 0.00001 0.0000123 123000 1230000
            tags:
            - inline_javascript
            - command_line_tool
            tool: tests/floats_small_and_large.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Confirm that very big and very small numbers are represented using decimals, not scientific notation""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_very_big_and_very_floats_nojs(self):
        """Confirm that very big and very small numbers are represented using decimals, not scientific notation

        Generated from::

            id: very_big_and_very_floats_nojs
            job: tests/empty.json
            output:
              result:
                basename: dump
                checksum: sha1$8a3913a553b8f29d47b99c1f4b0f6c2ee833cdc2
                class: File
                size: 32
            tags:
            - required
            - command_line_tool
            tool: tests/floats_small_and_large_nojs.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Confirm that very big and very small numbers are represented using decimals, not scientific notation""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.step_input
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_2_default_with_falsey_value(self):
        """Confirms that "false"-like (but not 'null') values override any default

        Generated from::

            id: default_with_falsey_value
            job: tests/empty.json
            output:
              out:
                basename: file.txt
                checksum: sha1$0074b1841ab5103cc0442f739d9fb41a33b602ee
                class: File
                size: 14
            tags:
            - step_input
            - workflow
            tool: tests/default_with_falsey_value.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """Confirms that "false"-like (but not 'null') values override any default""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_nested_types(self):
        """demonstrate usage of nested types

        Generated from::

            id: nested_types
            job: tests/nested_types.yaml
            output:
              their_name: Foo Bar
            tags:
            - required
            - command_line_tool
            tool: tests/nested_types.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """demonstrate usage of nested types""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_paramref_arguments_runtime(self):
        """confirm that $runtime is available to parameter references in arguments

        Generated from::

            id: paramref_arguments_runtime
            job: tests/empty.json
            output:
              runtime:
                cores: Any
                outdir: Any
                outdirSize: Any
                ram: Any
                tmpdir: Any
                tmpdirSize: Any
            tags:
            - required
            - command_line_tool
            tool: tests/paramref_arguments_runtime.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """confirm that $runtime is available to parameter references in arguments""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_paramref_arguments_self(self):
        """confirm that $self is available and set to null in arguments

        Generated from::

            id: paramref_arguments_self
            job: tests/empty.json
            output:
              self: null
            tags:
            - required
            - command_line_tool
            tool: tests/paramref_arguments_self.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """confirm that $self is available and set to null in arguments""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_2
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_2_paramref_arguments_inputs(self):
        """confirm that $inputs is available to parameter references in arguments

        Generated from::

            id: paramref_arguments_inputs
            job: tests/empty.json
            output:
              result:
                a_double: 1000000000000000000000000000000000000000000
                a_float: 4.2
                a_long: 4147483647
                a_string: z
                a_string_array:
                - a
                - b
                - c
                a_true: true
                an_array_of_doubles:
                - 1000000000000000000000000000000000000000000
                - -1000000000000000000000000000000000000000000
                an_array_of_falses:
                - false
                - false
                - false
                an_array_of_floats:
                - 2.3
                - 4.2
                an_array_of_ints:
                - 42
                - 23
                an_array_of_longs:
                - 4147483647
                - -4147483647
                an_array_of_mixed_booleans:
                - false
                - true
                - false
                an_array_of_trues:
                - true
                - true
                - true
                an_int: 42
            tags:
            - required
            - command_line_tool
            tool: tests/paramref_arguments_inputs.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.2""", """confirm that $inputs is available to parameter references in arguments""")
