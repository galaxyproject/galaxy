"""Test CWL conformance for version v1.0."""

import pytest

from ..test_workflows_cwl import BaseCwlWorkflowsApiTestCase


class TestCwlConformance(BaseCwlWorkflowsApiTestCase):
    """Test case mapping to CWL conformance tests for version v1.0."""

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_cl_basic_generation(self):
        """General test of command line generation

        Generated from::

            id: cl_basic_generation
            job: v1.0/bwa-mem-job.json
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
            tool: v1.0/bwa-mem-tool.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """General test of command line generation""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_nested_prefixes_arrays(self):
        """Test nested prefixes with arrays

        Generated from::

            id: nested_prefixes_arrays
            job: v1.0/bwa-mem-job.json
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
            tool: v1.0/binding-test.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test nested prefixes with arrays""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.schema_def
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_nested_cl_bindings(self):
        """Test nested command line bindings

        Generated from::

            id: nested_cl_bindings
            job: v1.0/tmap-job.json
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
            tool: v1.0/tmap-tool.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test nested command line bindings""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_cl_optional_inputs_missing(self):
        """Test command line with optional input (missing)

        Generated from::

            id: cl_optional_inputs_missing
            job: v1.0/cat-job.json
            output:
              args:
              - cat
              - hello.txt
            tags:
            - required
            - command_line_tool
            tool: v1.0/cat1-testcli.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test command line with optional input (missing)""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_cl_optional_bindings_provided(self):
        """Test command line with optional input (provided)

        Generated from::

            id: cl_optional_bindings_provided
            job: v1.0/cat-n-job.json
            output:
              args:
              - cat
              - -n
              - hello.txt
            tags:
            - required
            - command_line_tool
            tool: v1.0/cat1-testcli.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test command line with optional input (provided)""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.initial_work_dir
    @pytest.mark.inline_javascript
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_initworkdir_expreng_requirements(self):
        """Test InitialWorkDirRequirement ExpressionEngineRequirement.engineConfig feature

        Generated from::

            id: initworkdir_expreng_requirements
            job: v1.0/cat-job.json
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
            tool: v1.0/template-tool.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test InitialWorkDirRequirement ExpressionEngineRequirement.engineConfig feature""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.docker
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_stdout_redirect_docker(self):
        """Test command execution in Docker with stdout redirection

        Generated from::

            id: stdout_redirect_docker
            job: v1.0/cat-job.json
            output:
              output_file:
                checksum: sha1$47a013e660d408619d894b20806b1d5086aab03b
                class: File
                location: output.txt
                size: 13
            tags:
            - docker
            - command_line_tool
            tool: v1.0/cat3-tool-docker.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test command execution in Docker with stdout redirection""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.docker
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_stdout_redirect_shortcut_docker(self):
        """Test command execution in Docker with shortcut stdout redirection

        Generated from::

            id: stdout_redirect_shortcut_docker
            job: v1.0/cat-job.json
            output:
              output_file:
                checksum: sha1$47a013e660d408619d894b20806b1d5086aab03b
                class: File
                location: Any
                size: 13
            tags:
            - docker
            - command_line_tool
            tool: v1.0/cat3-tool-shortcut.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test command execution in Docker with shortcut stdout redirection""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.docker
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_stdout_redirect_mediumcut_docker(self):
        """Test command execution in Docker with mediumcut stdout redirection

        Generated from::

            id: stdout_redirect_mediumcut_docker
            job: v1.0/cat-job.json
            output:
              output_file:
                checksum: sha1$47a013e660d408619d894b20806b1d5086aab03b
                class: File
                location: cat-out
                size: 13
            tags:
            - docker
            - command_line_tool
            tool: v1.0/cat3-tool-mediumcut.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test command execution in Docker with mediumcut stdout redirection""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.shell_command
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_stderr_redirect(self):
        """Test command line with stderr redirection

        Generated from::

            id: stderr_redirect
            job: v1.0/empty.json
            output:
              output_file:
                checksum: sha1$f1d2d2f924e986ac86fdf7b36c94bcdf32beec15
                class: File
                location: error.txt
                size: 4
            tags:
            - shell_command
            - command_line_tool
            tool: v1.0/stderr.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test command line with stderr redirection""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.shell_command
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_stderr_redirect_shortcut(self):
        """Test command line with stderr redirection, brief syntax

        Generated from::

            id: stderr_redirect_shortcut
            job: v1.0/empty.json
            output:
              output_file:
                checksum: sha1$f1d2d2f924e986ac86fdf7b36c94bcdf32beec15
                class: File
                location: Any
                size: 4
            tags:
            - shell_command
            - command_line_tool
            tool: v1.0/stderr-shortcut.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test command line with stderr redirection, brief syntax""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.shell_command
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_stderr_redirect_mediumcut(self):
        """Test command line with stderr redirection, named brief syntax

        Generated from::

            id: stderr_redirect_mediumcut
            job: v1.0/empty.json
            output:
              output_file:
                checksum: sha1$f1d2d2f924e986ac86fdf7b36c94bcdf32beec15
                class: File
                location: std.err
                size: 4
            tags:
            - shell_command
            - command_line_tool
            tool: v1.0/stderr-mediumcut.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test command line with stderr redirection, named brief syntax""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_stdinout_redirect_docker(self):
        """Test command execution in Docker with stdin and stdout redirection

        Generated from::

            id: stdinout_redirect_docker
            job: v1.0/cat-job.json
            output:
              output_txt:
                checksum: sha1$47a013e660d408619d894b20806b1d5086aab03b
                class: File
                location: output.txt
                size: 13
            tags:
            - required
            - command_line_tool
            tool: v1.0/cat4-tool.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test command execution in Docker with stdin and stdout redirection""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.inline_javascript
    @pytest.mark.expression_tool
    @pytest.mark.green
    def test_conformance_v1_0_expression_any(self):
        """Test default usage of Any in expressions.

        Generated from::

            id: expression_any
            job: v1.0/empty.json
            output:
              output: 1
            tags:
            - inline_javascript
            - expression_tool
            tool: v1.0/null-expression1-tool.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test default usage of Any in expressions.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.inline_javascript
    @pytest.mark.expression_tool
    @pytest.mark.green
    def test_conformance_v1_0_expression_any_null(self):
        """Test explicitly passing null to Any type inputs with default values.

        Generated from::

            id: expression_any_null
            job: v1.0/null-expression1-job.json
            output:
              output: 1
            tags:
            - inline_javascript
            - expression_tool
            tool: v1.0/null-expression1-tool.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test explicitly passing null to Any type inputs with default values.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.inline_javascript
    @pytest.mark.expression_tool
    @pytest.mark.green
    def test_conformance_v1_0_expression_any_string(self):
        """Testing the string 'null' does not trip up an Any with a default value.

        Generated from::

            id: expression_any_string
            job: v1.0/null-expression2-job.json
            output:
              output: 2
            tags:
            - inline_javascript
            - expression_tool
            tool: v1.0/null-expression1-tool.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Testing the string 'null' does not trip up an Any with a default value.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.inline_javascript
    @pytest.mark.expression_tool
    @pytest.mark.green
    def test_conformance_v1_0_expression_any_nodefaultany(self):
        """Test Any without defaults cannot be unspecified.

        Generated from::

            id: expression_any_nodefaultany
            job: v1.0/empty.json
            should_fail: true
            tags:
            - inline_javascript
            - expression_tool
            tool: v1.0/null-expression2-tool.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test Any without defaults cannot be unspecified.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.inline_javascript
    @pytest.mark.expression_tool
    @pytest.mark.green
    def test_conformance_v1_0_expression_any_null_nodefaultany(self):
        """Test explicitly passing null to Any type without a default value.

        Generated from::

            id: expression_any_null_nodefaultany
            job: v1.0/null-expression1-job.json
            should_fail: true
            tags:
            - inline_javascript
            - expression_tool
            tool: v1.0/null-expression2-tool.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test explicitly passing null to Any type without a default value.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.inline_javascript
    @pytest.mark.expression_tool
    @pytest.mark.green
    def test_conformance_v1_0_expression_any_nullstring_nodefaultany(self):
        """Testing the string 'null' does not trip up an Any without a default value.

        Generated from::

            id: expression_any_nullstring_nodefaultany
            job: v1.0/null-expression2-job.json
            output:
              output: 2
            tags:
            - inline_javascript
            - expression_tool
            tool: v1.0/null-expression2-tool.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Testing the string 'null' does not trip up an Any without a default value.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.required
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_0_any_outputSource_compatibility(self):
        """Testing Any type compatibility in outputSource

        Generated from::

            id: any_outputSource_compatibility
            job: v1.0/any-type-job.json
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
            tool: v1.0/any-type-compat.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Testing Any type compatibility in outputSource""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_stdinout_redirect(self):
        """Test command execution in with stdin and stdout redirection

        Generated from::

            id: stdinout_redirect
            job: v1.0/cat-job.json
            output:
              output:
                checksum: sha1$47a013e660d408619d894b20806b1d5086aab03b
                class: File
                location: output
                size: 13
            tags:
            - required
            - command_line_tool
            tool: v1.0/cat-tool.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test command execution in with stdin and stdout redirection""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.inline_javascript
    @pytest.mark.expression_tool
    @pytest.mark.green
    def test_conformance_v1_0_expression_parseint(self):
        """Test ExpressionTool with Javascript engine

        Generated from::

            id: expression_parseint
            job: v1.0/parseInt-job.json
            output:
              output: 42
            tags:
            - inline_javascript
            - expression_tool
            tool: v1.0/parseInt-tool.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test ExpressionTool with Javascript engine""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.inline_javascript
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_expression_outputEval(self):
        """Test outputEval to transform output

        Generated from::

            id: expression_outputEval
            job: v1.0/wc-job.json
            output:
              output: 16
            tags:
            - inline_javascript
            - command_line_tool
            tool: v1.0/wc2-tool.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test outputEval to transform output""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.inline_javascript
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_0_wf_wc_parseInt(self):
        """Test two step workflow with imported tools

        Generated from::

            id: wf_wc_parseInt
            job: v1.0/wc-job.json
            output:
              count_output: 16
            tags:
            - inline_javascript
            - workflow
            tool: v1.0/count-lines1-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test two step workflow with imported tools""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.inline_javascript
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_0_wf_wc_expressiontool(self):
        """Test two step workflow with inline tools

        Generated from::

            id: wf_wc_expressiontool
            job: v1.0/wc-job.json
            output:
              count_output: 16
            tags:
            - inline_javascript
            - workflow
            tool: v1.0/count-lines2-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test two step workflow with inline tools""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.scatter
    @pytest.mark.inline_javascript
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_0_wf_wc_scatter(self):
        """Test single step workflow with Scatter step

        Generated from::

            id: wf_wc_scatter
            job: v1.0/count-lines3-job.json
            output:
              count_output:
              - 16
              - 1
            tags:
            - scatter
            - inline_javascript
            - workflow
            tool: v1.0/count-lines3-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test single step workflow with Scatter step""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.scatter
    @pytest.mark.multiple_input
    @pytest.mark.inline_javascript
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_0_wf_wc_scatter_multiple_merge(self):
        """Test single step workflow with Scatter step and two data links connected to same input, default merge behavior

        Generated from::

            id: wf_wc_scatter_multiple_merge
            job: v1.0/count-lines4-job.json
            output:
              count_output:
              - 16
              - 1
            tags:
            - scatter
            - multiple_input
            - inline_javascript
            - workflow
            tool: v1.0/count-lines4-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test single step workflow with Scatter step and two data links connected to same input, default merge behavior""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.scatter
    @pytest.mark.multiple_input
    @pytest.mark.inline_javascript
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_0_wf_wc_scatter_multiple_nested(self):
        """Test single step workflow with Scatter step and two data links connected to same input, nested merge behavior

        Generated from::

            id: wf_wc_scatter_multiple_nested
            job: v1.0/count-lines6-job.json
            output:
              count_output:
              - 32
              - 2
            tags:
            - scatter
            - multiple_input
            - inline_javascript
            - workflow
            tool: v1.0/count-lines6-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test single step workflow with Scatter step and two data links connected to same input, nested merge behavior""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.multiple_input
    @pytest.mark.inline_javascript
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_0_wf_wc_scatter_multiple_flattened(self):
        """Test single step workflow with Scatter step and two data links connected to same input, flattened merge behavior

        Generated from::

            id: wf_wc_scatter_multiple_flattened
            job: v1.0/count-lines6-job.json
            output:
              count_output: 34
            tags:
            - multiple_input
            - inline_javascript
            - workflow
            tool: v1.0/count-lines7-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test single step workflow with Scatter step and two data links connected to same input, flattened merge behavior""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.inline_javascript
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_0_wf_wc_nomultiple(self):
        """Test that no MultipleInputFeatureRequirement is necessary when workflow step source is a single-item list

        Generated from::

            id: wf_wc_nomultiple
            job: v1.0/count-lines6-job.json
            output:
              count_output: 32
            tags:
            - inline_javascript
            - workflow
            tool: v1.0/count-lines13-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test that no MultipleInputFeatureRequirement is necessary when workflow step source is a single-item list""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.inline_javascript
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_0_wf_input_default_missing(self):
        """Test workflow with default value for input parameter (missing)

        Generated from::

            id: wf_input_default_missing
            job: v1.0/empty.json
            output:
              count_output: 1
            tags:
            - inline_javascript
            - workflow
            tool: v1.0/count-lines5-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test workflow with default value for input parameter (missing)""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.inline_javascript
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_0_wf_input_default_provided(self):
        """Test workflow with default value for input parameter (provided)

        Generated from::

            id: wf_input_default_provided
            job: v1.0/wc-job.json
            output:
              count_output: 16
            tags:
            - inline_javascript
            - workflow
            tool: v1.0/count-lines5-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test workflow with default value for input parameter (provided)""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.required
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_0_wf_default_tool_default(self):
        """Test that workflow defaults override tool defaults

        Generated from::

            id: wf_default_tool_default
            job: v1.0/empty.json
            output:
              default_output: workflow_default
            tags:
            - required
            - workflow
            tool: v1.0/echo-wf-default.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test that workflow defaults override tool defaults""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.env_var
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_envvar_req(self):
        """Test EnvVarRequirement

        Generated from::

            id: envvar_req
            job: v1.0/env-job.json
            output:
              out:
                checksum: sha1$b3ec4ed1749c207e52b3a6d08c59f31d83bff519
                class: File
                location: out
                size: 15
            tags:
            - env_var
            - command_line_tool
            tool: v1.0/env-tool1.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test EnvVarRequirement""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.scatter
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_0_wf_scatter_single_param(self):
        """Test workflow scatter with single scatter parameter

        Generated from::

            id: wf_scatter_single_param
            job: v1.0/scatter-job1.json
            output:
              out:
              - foo one
              - foo two
              - foo three
              - foo four
            tags:
            - scatter
            - workflow
            tool: v1.0/scatter-wf1.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test workflow scatter with single scatter parameter""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.scatter
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_0_wf_scatter_two_nested_crossproduct(self):
        """Test workflow scatter with two scatter parameters and nested_crossproduct join method

        Generated from::

            id: wf_scatter_two_nested_crossproduct
            job: v1.0/scatter-job2.json
            output:
              out:
              - - foo one three
                - foo one four
              - - foo two three
                - foo two four
            tags:
            - scatter
            - workflow
            tool: v1.0/scatter-wf2.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test workflow scatter with two scatter parameters and nested_crossproduct join method""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.scatter
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_0_wf_scatter_two_flat_crossproduct(self):
        """Test workflow scatter with two scatter parameters and flat_crossproduct join method

        Generated from::

            id: wf_scatter_two_flat_crossproduct
            job: v1.0/scatter-job2.json
            output:
              out:
              - foo one three
              - foo one four
              - foo two three
              - foo two four
            tags:
            - scatter
            - workflow
            tool: v1.0/scatter-wf3.cwl#main
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test workflow scatter with two scatter parameters and flat_crossproduct join method""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.scatter
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_0_wf_scatter_two_dotproduct(self):
        """Test workflow scatter with two scatter parameters and dotproduct join method

        Generated from::

            id: wf_scatter_two_dotproduct
            job: v1.0/scatter-job2.json
            output:
              out:
              - foo one three
              - foo two four
            tags:
            - scatter
            - workflow
            tool: v1.0/scatter-wf4.cwl#main
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test workflow scatter with two scatter parameters and dotproduct join method""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.scatter
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_0_wf_scatter_emptylist(self):
        """Test workflow scatter with single empty list parameter

        Generated from::

            id: wf_scatter_emptylist
            job: v1.0/scatter-empty-job1.json
            output:
              out: []
            tags:
            - scatter
            - workflow
            tool: v1.0/scatter-wf1.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test workflow scatter with single empty list parameter""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.scatter
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_0_wf_scatter_nested_crossproduct_secondempty(self):
        """Test workflow scatter with two scatter parameters and nested_crossproduct join method with second list empty

        Generated from::

            id: wf_scatter_nested_crossproduct_secondempty
            job: v1.0/scatter-empty-job2.json
            output:
              out:
              - []
              - []
            tags:
            - scatter
            - workflow
            tool: v1.0/scatter-wf2.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test workflow scatter with two scatter parameters and nested_crossproduct join method with second list empty""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.scatter
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_0_wf_scatter_nested_crossproduct_firstempty(self):
        """Test workflow scatter with two scatter parameters and nested_crossproduct join method with first list empty

        Generated from::

            id: wf_scatter_nested_crossproduct_firstempty
            job: v1.0/scatter-empty-job3.json
            output:
              out: []
            tags:
            - scatter
            - workflow
            tool: v1.0/scatter-wf3.cwl#main
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test workflow scatter with two scatter parameters and nested_crossproduct join method with first list empty""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.scatter
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_0_wf_scatter_flat_crossproduct_oneempty(self):
        """Test workflow scatter with two scatter parameters, one of which is empty and flat_crossproduct join method

        Generated from::

            id: wf_scatter_flat_crossproduct_oneempty
            job: v1.0/scatter-empty-job2.json
            output:
              out: []
            tags:
            - scatter
            - workflow
            tool: v1.0/scatter-wf3.cwl#main
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test workflow scatter with two scatter parameters, one of which is empty and flat_crossproduct join method""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.scatter
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_0_wf_scatter_dotproduct_twoempty(self):
        """Test workflow scatter with two empty scatter parameters and dotproduct join method

        Generated from::

            id: wf_scatter_dotproduct_twoempty
            job: v1.0/scatter-empty-job4.json
            output:
              out: []
            tags:
            - scatter
            - workflow
            tool: v1.0/scatter-wf4.cwl#main
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test workflow scatter with two empty scatter parameters and dotproduct join method""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_any_input_param(self):
        """Test Any type input parameter

        Generated from::

            id: any_input_param
            job: v1.0/env-job.json
            output:
              out: 'hello test env
            
                '
            tags:
            - required
            - command_line_tool
            tool: v1.0/echo-tool.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test Any type input parameter""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.subworkflow
    @pytest.mark.workflow
    @pytest.mark.inline_javascript
    @pytest.mark.green
    def test_conformance_v1_0_nested_workflow(self):
        """Test nested workflow

        Generated from::

            id: nested_workflow
            job: v1.0/wc-job.json
            output:
              count_output: 16
            tags:
            - subworkflow
            - workflow
            - inline_javascript
            tool: v1.0/count-lines8-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test nested workflow""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.env_var
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_0_requirement_priority(self):
        """Test requirement priority

        Generated from::

            id: requirement_priority
            job: v1.0/env-job.json
            output:
              out:
                checksum: sha1$b3ec4ed1749c207e52b3a6d08c59f31d83bff519
                class: File
                location: out
                size: 15
            tags:
            - env_var
            - workflow
            tool: v1.0/env-wf1.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test requirement priority""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.env_var
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_0_requirement_override_hints(self):
        """Test requirements override hints

        Generated from::

            id: requirement_override_hints
            job: v1.0/env-job.json
            output:
              out:
                checksum: sha1$cdc1e84968261d6a7575b5305945471f8be199b6
                class: File
                location: out
                size: 9
            tags:
            - env_var
            - workflow
            tool: v1.0/env-wf2.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test requirements override hints""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.env_var
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_0_requirement_workflow_steps(self):
        """Test requirements on workflow steps

        Generated from::

            id: requirement_workflow_steps
            job: v1.0/env-job.json
            output:
              out:
                checksum: sha1$cdc1e84968261d6a7575b5305945471f8be199b6
                class: File
                location: out
                size: 9
            tags:
            - env_var
            - workflow
            tool: v1.0/env-wf3.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test requirements on workflow steps""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.inline_javascript
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_0_step_input_default_value(self):
        """Test default value on step input parameter

        Generated from::

            id: step_input_default_value
            job: v1.0/empty.json
            output:
              count_output: 16
            tags:
            - inline_javascript
            - workflow
            tool: v1.0/count-lines9-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test default value on step input parameter""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.inline_javascript
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_0_step_input_default_value_nosource(self):
        """Test use default value on step input parameter with empty source

        Generated from::

            id: step_input_default_value_nosource
            job: v1.0/empty.json
            output:
              count_output: 16
            tags:
            - inline_javascript
            - workflow
            tool: v1.0/count-lines11-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test use default value on step input parameter with empty source""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.inline_javascript
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_0_step_input_default_value_nullsource(self):
        """Test use default value on step input parameter with null source

        Generated from::

            id: step_input_default_value_nullsource
            job: v1.0/file1-null.json
            output:
              count_output: 16
            tags:
            - inline_javascript
            - workflow
            tool: v1.0/count-lines11-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test use default value on step input parameter with null source""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.inline_javascript
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_0_step_input_default_value_overriden(self):
        """Test default value on step input parameter overridden by provided source

        Generated from::

            id: step_input_default_value_overriden
            job: v1.0/cat-job.json
            output:
              count_output: 1
            tags:
            - inline_javascript
            - workflow
            tool: v1.0/count-lines11-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test default value on step input parameter overridden by provided source""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.required
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_0_wf_simple(self):
        """Test simple workflow

        Generated from::

            id: wf_simple
            job: v1.0/revsort-job.json
            output:
              output:
                checksum: sha1$b9214658cc453331b62c2282b772a5c063dbd284
                class: File
                location: output.txt
                size: 1111
            tags:
            - required
            - workflow
            tool: v1.0/revsort.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test simple workflow""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_hints_unknown_ignored(self):
        """Test unknown hints are ignored.

        Generated from::

            id: hints_unknown_ignored
            job: v1.0/cat-job.json
            output:
              output_file:
                checksum: sha1$47a013e660d408619d894b20806b1d5086aab03b
                class: File
                location: output.txt
                size: 13
            tags:
            - required
            - command_line_tool
            tool: v1.0/cat5-tool.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test unknown hints are ignored.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.initial_work_dir
    @pytest.mark.inline_javascript
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_0_initial_workdir_secondary_files_expr(self):
        """Test InitialWorkDirRequirement linking input files and capturing secondaryFiles on input and output. Also tests the use of a variety of parameter references and expressions in the secondaryFiles field.

        Generated from::

            id: initial_workdir_secondary_files_expr
            job: v1.0/search-job.json
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
            tool: v1.0/search.cwl#main
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test InitialWorkDirRequirement linking input files and capturing secondaryFiles on input and output. Also tests the use of a variety of parameter references and expressions in the secondaryFiles field.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.initial_work_dir
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_rename(self):
        """Test InitialWorkDirRequirement with expression in filename.

        Generated from::

            id: rename
            job: v1.0/rename-job.json
            output:
              outfile:
                checksum: sha1$327fc7aedf4f6b69a42a7c8b808dc5a7aff61376
                class: File
                location: fish.txt
                size: 1111
            tags:
            - initial_work_dir
            - command_line_tool
            tool: v1.0/rename.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test InitialWorkDirRequirement with expression in filename.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.initial_work_dir
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_initial_workdir_trailingnl(self):
        """Test if trailing newline is present in file entry in InitialWorkDir

        Generated from::

            id: initial_workdir_trailingnl
            job: v1.0/string-job.json
            output:
              out:
                checksum: sha1$6a47aa22b2a9d13a66a24b3ee5eaed95ce4753cf
                class: File
                location: example.conf
                size: 16
            tags:
            - initial_work_dir
            - command_line_tool
            tool: v1.0/iwdr-entry.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test if trailing newline is present in file entry in InitialWorkDir""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.inline_javascript
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_inline_expressions(self):
        """Test inline expressions

        Generated from::

            id: inline_expressions
            job: v1.0/wc-job.json
            output:
              output: 16
            tags:
            - inline_javascript
            - command_line_tool
            tool: v1.0/wc4-tool.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test inline expressions""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.schema_def
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_schemadef_req_tool_param(self):
        """Test SchemaDefRequirement definition used in tool parameter

        Generated from::

            id: schemadef_req_tool_param
            job: v1.0/schemadef-job.json
            output:
              output:
                checksum: sha1$f12e6cfe70f3253f70b0dbde17c692e7fb0f1e5e
                class: File
                location: output.txt
                size: 12
            tags:
            - schema_def
            - command_line_tool
            tool: v1.0/schemadef-tool.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test SchemaDefRequirement definition used in tool parameter""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.schema_def
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_0_schemadef_req_wf_param(self):
        """Test SchemaDefRequirement definition used in workflow parameter

        Generated from::

            id: schemadef_req_wf_param
            job: v1.0/schemadef-job.json
            output:
              output:
                checksum: sha1$f12e6cfe70f3253f70b0dbde17c692e7fb0f1e5e
                class: File
                location: output.txt
                size: 12
            tags:
            - schema_def
            - workflow
            tool: v1.0/schemadef-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test SchemaDefRequirement definition used in workflow parameter""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_param_evaluation_noexpr(self):
        """Test parameter evaluation, no support for JS expressions

        Generated from::

            id: param_evaluation_noexpr
            job: v1.0/empty.json
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
            tool: v1.0/params.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test parameter evaluation, no support for JS expressions""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.inline_javascript
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_param_evaluation_expr(self):
        """Test parameter evaluation, with support for JS expressions

        Generated from::

            id: param_evaluation_expr
            job: v1.0/empty.json
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
            tool: v1.0/params2.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test parameter evaluation, with support for JS expressions""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_metadata(self):
        """Test metadata

        Generated from::

            id: metadata
            job: v1.0/cat-job.json
            output: {}
            tags:
            - required
            - command_line_tool
            tool: v1.0/metadata.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test metadata""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_format_checking(self):
        """Test simple format checking.

        Generated from::

            id: format_checking
            job: v1.0/formattest-job.json
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
            tool: v1.0/formattest.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test simple format checking.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_format_checking_subclass(self):
        """Test format checking against ontology using subclassOf.

        Generated from::

            id: format_checking_subclass
            job: v1.0/formattest2-job.json
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
            tool: v1.0/formattest2.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test format checking against ontology using subclassOf.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_format_checking_equivalentclass(self):
        """Test format checking against ontology using equivalentClass.

        Generated from::

            id: format_checking_equivalentclass
            job: v1.0/formattest2-job.json
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
            tool: v1.0/formattest3.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test format checking against ontology using equivalentClass.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.docker
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_output_secondaryfile_optional(self):
        """Test optional output file and optional secondaryFile on output.

        Generated from::

            id: output_secondaryfile_optional
            job: v1.0/cat-job.json
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
            tool: v1.0/optional-output.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test optional output file and optional secondaryFile on output.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.inline_javascript
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_valuefrom_ignored_null(self):
        """Test that valueFrom is ignored when the parameter is null

        Generated from::

            id: valuefrom_ignored_null
            job: v1.0/empty.json
            output:
              out: '
            
                '
            tags:
            - inline_javascript
            - command_line_tool
            tool: v1.0/vf-concat.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test that valueFrom is ignored when the parameter is null""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.inline_javascript
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_valuefrom_secondexpr_ignored(self):
        """Test that second expression in concatenated valueFrom is not ignored

        Generated from::

            id: valuefrom_secondexpr_ignored
            job: v1.0/cat-job.json
            output:
              out: 'a string
            
                '
            tags:
            - inline_javascript
            - command_line_tool
            tool: v1.0/vf-concat.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test that second expression in concatenated valueFrom is not ignored""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.step_input
    @pytest.mark.inline_javascript
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_0_valuefrom_wf_step(self):
        """Test valueFrom on workflow step.

        Generated from::

            id: valuefrom_wf_step
            job: v1.0/step-valuefrom-wf.json
            output:
              count_output: 16
            tags:
            - step_input
            - inline_javascript
            - workflow
            tool: v1.0/step-valuefrom-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test valueFrom on workflow step.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.step_input
    @pytest.mark.inline_javascript
    @pytest.mark.multiple_input
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_0_valuefrom_wf_step_multiple(self):
        """Test valueFrom on workflow step with multiple sources

        Generated from::

            id: valuefrom_wf_step_multiple
            job: v1.0/step-valuefrom-job.json
            output:
              val: '3
            
                '
            tags:
            - step_input
            - inline_javascript
            - multiple_input
            - workflow
            tool: v1.0/step-valuefrom2-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test valueFrom on workflow step with multiple sources""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.step_input
    @pytest.mark.inline_javascript
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_0_valuefrom_wf_step_other(self):
        """Test valueFrom on workflow step referencing other inputs

        Generated from::

            id: valuefrom_wf_step_other
            job: v1.0/step-valuefrom-job.json
            output:
              val: '3
            
                '
            tags:
            - step_input
            - inline_javascript
            - workflow
            tool: v1.0/step-valuefrom3-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test valueFrom on workflow step referencing other inputs""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.shell_command
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_record_output_binding(self):
        """Test record type output binding.

        Generated from::

            id: record_output_binding
            job: v1.0/record-output-job.json
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
            tool: v1.0/record-output.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test record type output binding.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.shell_command
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_docker_json_output_path(self):
        """Test support for reading cwl.output.json when running in a Docker container and just 'path' is provided.

        Generated from::

            id: docker_json_output_path
            job: v1.0/empty.json
            output:
              foo:
                checksum: sha1$f1d2d2f924e986ac86fdf7b36c94bcdf32beec15
                class: File
                location: foo
                size: 4
            tags:
            - shell_command
            - command_line_tool
            tool: v1.0/test-cwl-out.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test support for reading cwl.output.json when running in a Docker container and just 'path' is provided.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.shell_command
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_docker_json_output_location(self):
        """Test support for reading cwl.output.json when running in a Docker container and just 'location' is provided.

        Generated from::

            id: docker_json_output_location
            job: v1.0/empty.json
            output:
              foo:
                checksum: sha1$f1d2d2f924e986ac86fdf7b36c94bcdf32beec15
                class: File
                location: foo
                size: 4
            tags:
            - shell_command
            - command_line_tool
            tool: v1.0/test-cwl-out2.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test support for reading cwl.output.json when running in a Docker container and just 'location' is provided.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_multiple_glob_expr_list(self):
        """Test support for returning multiple glob patterns from expression

        Generated from::

            id: multiple_glob_expr_list
            job: v1.0/abc.json
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
            tool: v1.0/glob-expr-list.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test support for returning multiple glob patterns from expression""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.scatter
    @pytest.mark.step_input
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_0_wf_scatter_oneparam_valuefrom(self):
        """Test workflow scatter with single scatter parameter and two valueFrom on step input (first and current el)

        Generated from::

            id: wf_scatter_oneparam_valuefrom
            job: v1.0/scatter-valuefrom-job1.json
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
            tool: v1.0/scatter-valuefrom-wf1.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test workflow scatter with single scatter parameter and two valueFrom on step input (first and current el)""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.scatter
    @pytest.mark.step_input
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_0_wf_scatter_twoparam_nested_crossproduct_valuefrom(self):
        """Test workflow scatter with two scatter parameters and nested_crossproduct join method and valueFrom on step input

        Generated from::

            id: wf_scatter_twoparam_nested_crossproduct_valuefrom
            job: v1.0/scatter-valuefrom-job2.json
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
            tool: v1.0/scatter-valuefrom-wf2.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test workflow scatter with two scatter parameters and nested_crossproduct join method and valueFrom on step input""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.scatter
    @pytest.mark.step_input
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_0_wf_scatter_twoparam_flat_crossproduct_valuefrom(self):
        """Test workflow scatter with two scatter parameters and flat_crossproduct join method and valueFrom on step input

        Generated from::

            id: wf_scatter_twoparam_flat_crossproduct_valuefrom
            job: v1.0/scatter-valuefrom-job2.json
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
            tool: v1.0/scatter-valuefrom-wf3.cwl#main
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test workflow scatter with two scatter parameters and flat_crossproduct join method and valueFrom on step input""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.scatter
    @pytest.mark.step_input
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_0_wf_scatter_twoparam_dotproduct_valuefrom(self):
        """Test workflow scatter with two scatter parameters and dotproduct join method and valueFrom on step input

        Generated from::

            id: wf_scatter_twoparam_dotproduct_valuefrom
            job: v1.0/scatter-valuefrom-job2.json
            output:
              out:
              - foo one one three
              - foo one two four
            tags:
            - scatter
            - step_input
            - workflow
            tool: v1.0/scatter-valuefrom-wf4.cwl#main
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test workflow scatter with two scatter parameters and dotproduct join method and valueFrom on step input""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.scatter
    @pytest.mark.step_input
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_0_wf_scatter_oneparam_valuefrom_twice_current_el(self):
        """Test workflow scatter with single scatter parameter and two valueFrom on step input (current el twice)

        Generated from::

            id: wf_scatter_oneparam_valuefrom_twice_current_el
            job: v1.0/scatter-valuefrom-job1.json
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
            tool: v1.0/scatter-valuefrom-wf5.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test workflow scatter with single scatter parameter and two valueFrom on step input (current el twice)""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.scatter
    @pytest.mark.step_input
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_0_wf_scatter_oneparam_valueFrom(self):
        """Test valueFrom eval on scattered input parameter

        Generated from::

            id: wf_scatter_oneparam_valueFrom
            job: v1.0/scatter-valuefrom-job3.json
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
            tool: v1.0/scatter-valuefrom-wf6.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test valueFrom eval on scattered input parameter""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.required
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_0_wf_two_inputfiles_namecollision(self):
        """Test workflow two input files with same name.

        Generated from::

            id: wf_two_inputfiles_namecollision
            job: v1.0/conflict-job.json
            output:
              fileout:
                checksum: sha1$a2d8d6e7b28295dc9977dc3bdb652ddd480995f0
                class: File
                location: out.txt
                size: 25
            tags:
            - required
            - workflow
            tool: v1.0/conflict-wf.cwl#collision
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test workflow two input files with same name.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.shell_command
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_directory_input_param_ref(self):
        """Test directory input with parameter reference

        Generated from::

            id: directory_input_param_ref
            job: v1.0/dir-job.yml
            output:
              outlist:
                checksum: sha1$13cda8661796ae241da3a18668fb552161a72592
                class: File
                location: output.txt
                size: 20
            tags:
            - shell_command
            - command_line_tool
            tool: v1.0/dir.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test directory input with parameter reference""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.command_line_tool
    @pytest.mark.shell_command
    @pytest.mark.green
    def test_conformance_v1_0_directory_input_docker(self):
        """Test directory input in Docker

        Generated from::

            id: directory_input_docker
            job: v1.0/dir-job.yml
            output:
              outlist:
                checksum: sha1$13cda8661796ae241da3a18668fb552161a72592
                class: File
                location: output.txt
                size: 20
            tags:
            - command_line_tool
            - shell_command
            tool: v1.0/dir2.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test directory input in Docker""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_directory_output(self):
        """Test directory output

        Generated from::

            id: directory_output
            job: v1.0/dir3-job.yml
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
            tool: v1.0/dir3.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test directory output""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.shell_command
    @pytest.mark.command_line_tool
    @pytest.mark.red
    def test_conformance_v1_0_directory_secondaryfiles(self):
        """Test directories in secondaryFiles

        Generated from::

            id: directory_secondaryfiles
            job: v1.0/dir4-job.yml
            output:
              outlist:
                checksum: sha1$13cda8661796ae241da3a18668fb552161a72592
                class: File
                location: output.txt
                size: 20
            tags:
            - shell_command
            - command_line_tool
            tool: v1.0/dir4.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test directories in secondaryFiles""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.shell_command
    @pytest.mark.initial_work_dir
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_dynamic_initial_workdir(self):
        """Test dynamic initial work dir

        Generated from::

            id: dynamic_initial_workdir
            job: v1.0/dir-job.yml
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
            tool: v1.0/dir5.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test dynamic initial work dir""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.initial_work_dir
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_writable_stagedfiles(self):
        """Test writable staged files.

        Generated from::

            id: writable_stagedfiles
            job: v1.0/stagefile-job.yml
            output:
              outfile:
                checksum: sha1$b769c7b2e316edd4b5eb2d24799b2c1f9d8c86e6
                class: File
                location: bob.txt
                size: 1111
            tags:
            - initial_work_dir
            - command_line_tool
            tool: v1.0/stagefile.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test writable staged files.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_input_file_literal(self):
        """Test file literal as input

        Generated from::

            id: input_file_literal
            job: v1.0/file-literal.yml
            output:
              output_file:
                checksum: sha1$d0e04ff6c413c7d57f9a0ca0a33cd3ab52e2dd9c
                class: File
                location: output.txt
                size: 18
            tags:
            - required
            - command_line_tool
            tool: v1.0/cat3-tool.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test file literal as input""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.initial_work_dir
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_initial_workdir_expr(self):
        """Test expression in InitialWorkDir listing

        Generated from::

            id: initial_workdir_expr
            job: v1.0/arguments-job.yml
            output:
              classfile:
                checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                class: File
                location: Hello.class
                size: 0
            tags:
            - initial_work_dir
            - command_line_tool
            tool: v1.0/linkfile.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test expression in InitialWorkDir listing""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_nameroot_nameext_stdout_expr(self):
        """Test nameroot/nameext expression in arguments, stdout

        Generated from::

            id: nameroot_nameext_stdout_expr
            job: v1.0/wc-job.json
            output:
              b:
                checksum: sha1$c4cfd130e7578714e3eef91c1d6d90e0e0b9db3e
                class: File
                location: whale.xtx
                size: 21
            tags:
            - required
            - command_line_tool
            tool: v1.0/nameroot.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test nameroot/nameext expression in arguments, stdout""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.shell_command
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_input_dir_inputbinding(self):
        """Test directory input with inputBinding

        Generated from::

            id: input_dir_inputbinding
            job: v1.0/dir-job.yml
            output:
              outlist:
                checksum: sha1$13cda8661796ae241da3a18668fb552161a72592
                class: File
                location: output.txt
                size: 20
            tags:
            - shell_command
            - command_line_tool
            tool: v1.0/dir6.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test directory input with inputBinding""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_cl_gen_arrayofarrays(self):
        """Test command line generation of array-of-arrays

        Generated from::

            id: cl_gen_arrayofarrays
            job: v1.0/nested-array-job.yml
            output:
              echo:
                checksum: sha1$3f786850e387550fdab836ed7e6dc881de23001b
                class: File
                location: echo.txt
                size: 2
            tags:
            - required
            - command_line_tool
            tool: v1.0/nested-array.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test command line generation of array-of-arrays""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.shell_command
    @pytest.mark.command_line_tool
    @pytest.mark.red
    def test_conformance_v1_0_env_home_tmpdir(self):
        """Test $HOME and $TMPDIR are set correctly

        Generated from::

            id: env_home_tmpdir
            job: v1.0/empty.json
            output: {}
            tags:
            - shell_command
            - command_line_tool
            tool: v1.0/envvar.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test $HOME and $TMPDIR are set correctly""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.shell_command
    @pytest.mark.command_line_tool
    @pytest.mark.red
    def test_conformance_v1_0_env_home_tmpdir_docker(self):
        """Test $HOME and $TMPDIR are set correctly in Docker

        Generated from::

            id: env_home_tmpdir_docker
            job: v1.0/empty.json
            output: {}
            tags:
            - shell_command
            - command_line_tool
            tool: v1.0/envvar2.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test $HOME and $TMPDIR are set correctly in Docker""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.inline_javascript
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_0_expressionlib_tool_wf_override(self):
        """Test that expressionLib requirement of individual tool step overrides expressionLib of workflow.

        Generated from::

            id: expressionlib_tool_wf_override
            job: v1.0/empty.json
            output:
              out:
                checksum: sha1$7448d8798a4380162d4b56f9b452e2f6f9e24e7a
                class: File
                location: whatever.txt
                size: 2
            tags:
            - inline_javascript
            - workflow
            tool: v1.0/js-expr-req-wf.cwl#wf
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test that expressionLib requirement of individual tool step overrides expressionLib of workflow.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.docker
    @pytest.mark.initial_work_dir
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_initial_workdir_output(self):
        """Test output of InitialWorkDir

        Generated from::

            id: initial_workdir_output
            job: v1.0/initialworkdirrequirement-docker-out-job.json
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
            tool: v1.0/initialworkdirrequirement-docker-out.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test output of InitialWorkDir""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.subworkflow
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_0_embedded_subworkflow(self):
        """Test embedded subworkflow

        Generated from::

            id: embedded_subworkflow
            job: v1.0/wc-job.json
            output:
              count_output: 16
            tags:
            - subworkflow
            - workflow
            tool: v1.0/count-lines10-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test embedded subworkflow""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.docker
    @pytest.mark.inline_javascript
    @pytest.mark.shell_command
    @pytest.mark.command_line_tool
    @pytest.mark.red
    def test_conformance_v1_0_filesarray_secondaryfiles(self):
        """Test secondaryFiles on array of files.

        Generated from::

            id: filesarray_secondaryfiles
            job: v1.0/docker-array-secondaryfiles-job.json
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
            tool: v1.0/docker-array-secondaryfiles.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test secondaryFiles on array of files.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.inline_javascript
    @pytest.mark.expression_tool
    @pytest.mark.green
    def test_conformance_v1_0_exprtool_directory_literal(self):
        """Test directory literal output created by ExpressionTool

        Generated from::

            id: exprtool_directory_literal
            job: v1.0/dir7.yml
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
            tool: v1.0/dir7.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test directory literal output created by ExpressionTool""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.inline_javascript
    @pytest.mark.expression_tool
    @pytest.mark.green
    def test_conformance_v1_0_exprtool_file_literal(self):
        """Test file literal output created by ExpressionTool

        Generated from::

            id: exprtool_file_literal
            job: v1.0/empty.json
            output:
              lit:
                checksum: sha1$fea23663b9c8ed71968f86415b5ec091bb111448
                class: File
                location: a_file
                size: 19
            tags:
            - inline_javascript
            - expression_tool
            tool: v1.0/file-literal-ex.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test file literal output created by ExpressionTool""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.docker
    @pytest.mark.command_line_tool
    @pytest.mark.red
    def test_conformance_v1_0_dockeroutputdir(self):
        """Test dockerOutputDirectory

        Generated from::

            id: dockeroutputdir
            job: v1.0/empty.json
            output:
              thing:
                checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                class: File
                location: thing
                size: 0
            tags:
            - docker
            - command_line_tool
            tool: v1.0/docker-output-dir.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test dockerOutputDirectory""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_hints_import(self):
        """Test hints with $import

        Generated from::

            id: hints_import
            job: v1.0/empty.json
            output:
              out:
                checksum: sha1$b3ec4ed1749c207e52b3a6d08c59f31d83bff519
                class: File
                location: out
                size: 15
            tags:
            - required
            - command_line_tool
            tool: v1.0/imported-hint.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test hints with $import""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_default_path_notfound_warning(self):
        """Test warning instead of error when default path is not found

        Generated from::

            id: default_path_notfound_warning
            job: v1.0/default_path_job.yml
            output: {}
            tags:
            - required
            - command_line_tool
            tool: v1.0/default_path.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test warning instead of error when default path is not found""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.inline_javascript
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_inlinejs_req_expressions(self):
        """Test InlineJavascriptRequirement with multiple expressions in the same tool

        Generated from::

            id: inlinejs_req_expressions
            job: v1.0/empty.json
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
            tool: v1.0/inline-js.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test InlineJavascriptRequirement with multiple expressions in the same tool""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.initial_work_dir
    @pytest.mark.shell_command
    @pytest.mark.command_line_tool
    @pytest.mark.red
    def test_conformance_v1_0_input_dir_recurs_copy_writable(self):
        """Test if a writable input directory is recursively copied and writable

        Generated from::

            id: input_dir_recurs_copy_writable
            job: v1.0/recursive-input-directory.yml
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
            tool: v1.0/recursive-input-directory.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test if a writable input directory is recursively copied and writable""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.inline_javascript
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_null_missing_params(self):
        """Test that missing parameters are null (not undefined) in expression

        Generated from::

            id: null_missing_params
            job: v1.0/empty.json
            output:
              out: 't
            
                '
            tags:
            - inline_javascript
            - command_line_tool
            tool: v1.0/null-defined.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test that missing parameters are null (not undefined) in expression""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.inline_javascript
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_param_notnull_expr(self):
        """Test that provided parameter is not null in expression

        Generated from::

            id: param_notnull_expr
            job: v1.0/cat-job.json
            output:
              out: 'f
            
                '
            tags:
            - inline_javascript
            - command_line_tool
            tool: v1.0/null-defined.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test that provided parameter is not null in expression""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.required
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_0_wf_compound_doc(self):
        """Test compound workflow document

        Generated from::

            id: wf_compound_doc
            job: v1.0/revsort-job.json
            output:
              output:
                checksum: sha1$b9214658cc453331b62c2282b772a5c063dbd284
                class: File
                location: output.txt
                size: 1111
            tags:
            - required
            - workflow
            tool: v1.0/revsort-packed.cwl#main
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test compound workflow document""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.step_input
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_0_nameroot_nameext_generated(self):
        """Test that nameroot and nameext are generated from basename at execution time by the runner

        Generated from::

            id: nameroot_nameext_generated
            job: v1.0/basename-fields-job.yml
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
            tool: v1.0/basename-fields-test.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test that nameroot and nameext are generated from basename at execution time by the runner""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.initial_work_dir
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_initialworkpath_output(self):
        """Test that file path in $(inputs) for initialworkdir is in $(outdir).

        Generated from::

            id: initialworkpath_output
            job: v1.0/wc-job.json
            output: {}
            tags:
            - initial_work_dir
            - command_line_tool
            tool: v1.0/initialwork-path.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test that file path in $(inputs) for initialworkdir is in $(outdir).""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.multiple_input
    @pytest.mark.inline_javascript
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_0_wf_scatter_twopar_oneinput_flattenedmerge(self):
        """Test single step workflow with Scatter step and two data links connected to same input, flattened merge behavior. Workflow inputs are set as list

        Generated from::

            id: wf_scatter_twopar_oneinput_flattenedmerge
            job: v1.0/count-lines6-job.json
            output:
              count_output: 34
            tags:
            - multiple_input
            - inline_javascript
            - workflow
            tool: v1.0/count-lines12-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test single step workflow with Scatter step and two data links connected to same input, flattened merge behavior. Workflow inputs are set as list""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.step_input
    @pytest.mark.inline_javascript
    @pytest.mark.multiple_input
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_0_wf_multiplesources_multipletypes(self):
        """Test step input with multiple sources with multiple types

        Generated from::

            id: wf_multiplesources_multipletypes
            job: v1.0/sum-job.json
            output:
              result: 12
            tags:
            - step_input
            - inline_javascript
            - multiple_input
            - workflow
            tool: v1.0/sum-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test step input with multiple sources with multiple types""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_shelldir_notinterpreted(self):
        """Test that shell directives are not interpreted.

        Generated from::

            id: shelldir_notinterpreted
            job: v1.0/empty.json
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
            tool: v1.0/shellchar.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test that shell directives are not interpreted.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.shell_command
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_shelldir_quoted(self):
        """Test that shell directives are quoted.

        Generated from::

            id: shelldir_quoted
            job: v1.0/empty.json
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
            tool: v1.0/shellchar2.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test that shell directives are quoted.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.inline_javascript
    @pytest.mark.initial_work_dir
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_initial_workdir_empty_writable(self):
        """Test empty writable dir with InitialWorkDirRequirement

        Generated from::

            id: initial_workdir_empty_writable
            job: v1.0/empty.json
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
            tool: v1.0/writable-dir.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test empty writable dir with InitialWorkDirRequirement""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.inline_javascript
    @pytest.mark.initial_work_dir
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_initial_workdir_empty_writable_docker(self):
        """Test empty writable dir with InitialWorkDirRequirement inside Docker

        Generated from::

            id: initial_workdir_empty_writable_docker
            job: v1.0/empty.json
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
            tool: v1.0/writable-dir-docker.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test empty writable dir with InitialWorkDirRequirement inside Docker""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.resource
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_dynamic_resreq_inputs(self):
        """Test dynamic resource reqs referencing inputs

        Generated from::

            id: dynamic_resreq_inputs
            job: v1.0/dynresreq-job.yaml
            output:
              output:
                checksum: sha1$7448d8798a4380162d4b56f9b452e2f6f9e24e7a
                class: File
                location: cores.txt
                size: 2
            tags:
            - resource
            - command_line_tool
            tool: v1.0/dynresreq.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test dynamic resource reqs referencing inputs""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_fileliteral_input_docker(self):
        """Test file literal as input without Docker

        Generated from::

            id: fileliteral_input_docker
            job: v1.0/file-literal.yml
            output:
              output_file:
                checksum: sha1$d0e04ff6c413c7d57f9a0ca0a33cd3ab52e2dd9c
                class: File
                location: output.txt
                size: 18
            tags:
            - required
            - command_line_tool
            tool: v1.0/cat3-nodocker.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test file literal as input without Docker""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_outputbinding_glob_sorted(self):
        """Test that OutputBinding.glob is sorted as specified by POSIX

        Generated from::

            id: outputbinding_glob_sorted
            job: v1.0/empty.json
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
            tool: v1.0/glob_test.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test that OutputBinding.glob is sorted as specified by POSIX""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.initial_work_dir
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_0_initialworkdir_nesteddir(self):
        """Test InitialWorkDirRequirement with a nested directory structure from another step

        Generated from::

            id: initialworkdir_nesteddir
            job: v1.0/empty.json
            output:
              ya_empty:
                checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                class: File
                location: ya
                size: 0
            tags:
            - initial_work_dir
            - workflow
            tool: v1.0/iwdr_with_nested_dirs.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test InitialWorkDirRequirement with a nested directory structure from another step""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_booleanflags_cl_noinputbinding(self):
        """Test that boolean flags do not appear on command line if inputBinding is empty and not null

        Generated from::

            id: booleanflags_cl_noinputbinding
            job: v1.0/bool-empty-inputbinding-job.json
            output:
              args: []
            tags:
            - required
            - command_line_tool
            tool: v1.0/bool-empty-inputbinding.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test that boolean flags do not appear on command line if inputBinding is empty and not null""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_expr_reference_self_noinput(self):
        """Test that expression engine does not fail to evaluate reference to self with unprovided input

        Generated from::

            id: expr_reference_self_noinput
            job: v1.0/empty.json
            output:
              args: []
            tags:
            - required
            - command_line_tool
            tool: v1.0/stage-unprovided-file.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test that expression engine does not fail to evaluate reference to self with unprovided input""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_success_codes(self):
        """Test successCodes

        Generated from::

            id: success_codes
            job: v1.0/empty.json
            output: {}
            tags:
            - required
            - command_line_tool
            tool: v1.0/exit-success.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test successCodes""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.resource
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_0_dynamic_resreq_wf(self):
        """Test simple workflow with a dynamic resource requirement

        Generated from::

            id: dynamic_resreq_wf
            job: v1.0/dynresreq-job.yaml
            output:
              cores:
                checksum: sha1$7448d8798a4380162d4b56f9b452e2f6f9e24e7a
                class: File
                location: output
                size: 2
            tags:
            - resource
            - workflow
            tool: v1.0/dynresreq-workflow.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test simple workflow with a dynamic resource requirement""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_cl_empty_array_input(self):
        """Test that empty array input does not add anything to command line

        Generated from::

            id: cl_empty_array_input
            job: v1.0/empty-array-job.json
            output:
              args: []
            tags:
            - required
            - command_line_tool
            tool: v1.0/empty-array-input.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test that empty array input does not add anything to command line""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.resource
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_0_resreq_step_overrides_wf(self):
        """Test that ResourceRequirement on a step level redefines requirement on the workflow level

        Generated from::

            id: resreq_step_overrides_wf
            job: v1.0/empty.json
            output:
              out:
                checksum: sha1$e5fa44f2b31c1fb553b6021e7360d07d5d91ff5e
                class: File
                location: cores.txt
                size: 2
            tags:
            - resource
            - workflow
            tool: v1.0/steplevel-resreq.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test that ResourceRequirement on a step level redefines requirement on the workflow level""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.required
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_valuefrom_constant_overrides_inputs(self):
        """Test valueFrom with constant value overriding provided array inputs

        Generated from::

            id: valuefrom_constant_overrides_inputs
            job: v1.0/array-of-strings-job.yml
            output:
              args:
              - replacementValue
            tags:
            - required
            - command_line_tool
            tool: v1.0/valueFrom-constant.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test valueFrom with constant value overriding provided array inputs""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.resource
    @pytest.mark.command_line_tool
    @pytest.mark.green
    def test_conformance_v1_0_dynamic_resreq_filesizes(self):
        """Test dynamic resource reqs referencing the size of Files inside a Directory

        Generated from::

            id: dynamic_resreq_filesizes
            job: v1.0/dynresreq-dir-job.yaml
            output:
              output:
                checksum: sha1$7448d8798a4380162d4b56f9b452e2f6f9e24e7a
                class: File
                location: cores.txt
                size: 2
            tags:
            - resource
            - command_line_tool
            tool: v1.0/dynresreq-dir.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test dynamic resource reqs referencing the size of Files inside a Directory""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.required
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_0_wf_step_connect_undeclared_param(self):
        """Test that it is not an error to connect a parameter to a workflow step, even if the parameter doesn't appear in the `run` process inputs.

        Generated from::

            id: wf_step_connect_undeclared_param
            job: v1.0/empty.json
            output:
              out: 'hello inp1
            
                '
            tags:
            - required
            - workflow
            tool: v1.0/pass-unconnected.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test that it is not an error to connect a parameter to a workflow step, even if the parameter doesn't appear in the `run` process inputs.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.required
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_0_wf_step_access_undeclared_param(self):
        """Test that parameters that don't appear in the `run` process inputs are not present in the input object used to run the tool.

        Generated from::

            id: wf_step_access_undeclared_param
            job: v1.0/empty.json
            should_fail: true
            tags:
            - required
            - workflow
            tool: v1.0/fail-unconnected.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test that parameters that don't appear in the `run` process inputs are not present in the input object used to run the tool.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.shell_command
    @pytest.mark.command_line_tool
    @pytest.mark.red
    def test_conformance_v1_0_env_home_tmpdir_docker_complex(self):
        """Test $HOME and $TMPDIR are set correctly in Docker without using return code

        Generated from::

            id: env_home_tmpdir_docker_complex
            job: v1.0/empty.json
            output:
              results:
                basename: results
                checksum: sha1$7d5ca8c0c03e883c56c4eb1ef6f6bb9bccad4d86
                class: File
                size: 8
            tags:
            - shell_command
            - command_line_tool
            tool: v1.0/envvar3.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test $HOME and $TMPDIR are set correctly in Docker without using return code""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.scatter
    @pytest.mark.step_input
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_0_wf_scatter_oneparam_valuefrom_inputs(self):
        """Test workflow scatter with single scatter parameter and two valueFrom using $inputs (first and current el)

        Generated from::

            id: wf_scatter_oneparam_valuefrom_inputs
            job: v1.0/scatter-valuefrom-job1.json
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
            tool: v1.0/scatter-valuefrom-inputs-wf1.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test workflow scatter with single scatter parameter and two valueFrom using $inputs (first and current el)""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.schema_def
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_0_packed_import_schema(self):
        """SchemaDefRequirement with $import, and packed

        Generated from::

            id: packed_import_schema
            job: v1.0/import_schema-def_job.yml
            output:
              output_bam:
                basename: a.bam
                checksum: sha1$da39a3ee5e6b4b0d3255bfef95601890afd80709
                class: File
                size: 0
            tags:
            - schema_def
            - workflow
            tool: v1.0/import_schema-def_packed.cwl#main
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """SchemaDefRequirement with $import, and packed""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.shell_command
    @pytest.mark.command_line_tool
    @pytest.mark.red
    def test_conformance_v1_0_job_input_secondary_subdirs(self):
        """Test specifying secondaryFiles in subdirectories of the job input document.

        Generated from::

            id: job_input_secondary_subdirs
            job: v1.0/dir4-subdir-1-job.yml
            output:
              outlist:
                checksum: sha1$9d9bc8f5252d39274b5dfbac64216c6e888f5dfc
                class: File
                location: output.txt
                size: 14
            tags:
            - shell_command
            - command_line_tool
            tool: v1.0/dir4.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test specifying secondaryFiles in subdirectories of the job input document.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.shell_command
    @pytest.mark.command_line_tool
    @pytest.mark.red
    def test_conformance_v1_0_job_input_subdir_primary_and_secondary_subdirs(self):
        """Test specifying secondaryFiles in same subdirectory of the job input as the primary input file.

        Generated from::

            id: job_input_subdir_primary_and_secondary_subdirs
            job: v1.0/dir4-subdir-2-job.yml
            output:
              outlist:
                checksum: sha1$9d9bc8f5252d39274b5dfbac64216c6e888f5dfc
                class: File
                location: output.txt
                size: 14
            tags:
            - shell_command
            - command_line_tool
            tool: v1.0/dir4.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test specifying secondaryFiles in same subdirectory of the job input as the primary input file.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.workflow
    @pytest.mark.inline_javascript
    @pytest.mark.green
    def test_conformance_v1_0_scatter_embedded_subworkflow(self):
        """Test simple scatter over an embedded subworkflow

        Generated from::

            id: scatter_embedded_subworkflow
            job: v1.0/count-lines3-job.json
            output:
              count_output:
              - 16
              - 1
            tags:
            - workflow
            - inline_javascript
            tool: v1.0/count-lines18-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test simple scatter over an embedded subworkflow""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.workflow
    @pytest.mark.scatter
    @pytest.mark.subworkflow
    @pytest.mark.multiple_input
    @pytest.mark.inline_javascript
    @pytest.mark.green
    def test_conformance_v1_0_scatter_multi_input_embedded_subworkflow(self):
        """Test simple multiple input scatter over an embedded subworkflow

        Generated from::

            id: scatter_multi_input_embedded_subworkflow
            job: v1.0/count-lines4-job.json
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
            tool: v1.0/count-lines14-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test simple multiple input scatter over an embedded subworkflow""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.workflow
    @pytest.mark.subworkflow
    @pytest.mark.inline_javascript
    @pytest.mark.red
    def test_conformance_v1_0_workflow_embedded_subworkflow_embedded_subsubworkflow(self):
        """Test twice nested subworkflow

        Generated from::

            id: workflow_embedded_subworkflow_embedded_subsubworkflow
            job: v1.0/wc-job.json
            output:
              count_output: 16
            tags:
            - workflow
            - subworkflow
            - inline_javascript
            tool: v1.0/count-lines15-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test twice nested subworkflow""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.workflow
    @pytest.mark.subworkflow
    @pytest.mark.inline_javascript
    @pytest.mark.red
    def test_conformance_v1_0_workflow_embedded_subworkflow_with_tool_and_subsubworkflow(self):
        """Test subworkflow of mixed depth with tool first

        Generated from::

            id: workflow_embedded_subworkflow_with_tool_and_subsubworkflow
            job: v1.0/wc-job.json
            output:
              count_output: 16
            tags:
            - workflow
            - subworkflow
            - inline_javascript
            tool: v1.0/count-lines16-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test subworkflow of mixed depth with tool first""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.workflow
    @pytest.mark.subworkflow
    @pytest.mark.inline_javascript
    @pytest.mark.red
    def test_conformance_v1_0_workflow_embedded_subworkflow_with_subsubworkflow_and_tool(self):
        """Test subworkflow of mixed depth with tool after

        Generated from::

            id: workflow_embedded_subworkflow_with_subsubworkflow_and_tool
            job: v1.0/wc-job.json
            output:
              count_output: 16
            tags:
            - workflow
            - subworkflow
            - inline_javascript
            tool: v1.0/count-lines17-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test subworkflow of mixed depth with tool after""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.workflow
    @pytest.mark.shell_command
    @pytest.mark.green
    def test_conformance_v1_0_workflow_records_inputs_and_outputs(self):
        """Test record type inputs to and outputs from workflows.

        Generated from::

            id: workflow_records_inputs_and_outputs
            job: v1.0/record-output-job.json
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
            tool: v1.0/record-output-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test record type inputs to and outputs from workflows.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.workflow
    @pytest.mark.inline_javascript
    @pytest.mark.expression_tool
    @pytest.mark.green
    def test_conformance_v1_0_workflow_integer_input(self):
        """Test integer workflow input and outputs

        Generated from::

            id: workflow_integer_input
            job: v1.0/io-int.json
            output:
              o: 10
            tags:
            - workflow
            - inline_javascript
            - expression_tool
            tool: v1.0/io-int-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test integer workflow input and outputs""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.workflow
    @pytest.mark.inline_javascript
    @pytest.mark.expression_tool
    @pytest.mark.green
    def test_conformance_v1_0_workflow_integer_input_optional_specified(self):
        """Test optional integer workflow inputs (specified)

        Generated from::

            id: workflow_integer_input_optional_specified
            job: v1.0/io-int.json
            output:
              o: 10
            tags:
            - workflow
            - inline_javascript
            - expression_tool
            tool: v1.0/io-int-optional-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test optional integer workflow inputs (specified)""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.workflow
    @pytest.mark.inline_javascript
    @pytest.mark.expression_tool
    @pytest.mark.red
    def test_conformance_v1_0_workflow_integer_input_optional_unspecified(self):
        """Test optional integer workflow inputs (unspecified)

        Generated from::

            id: workflow_integer_input_optional_unspecified
            job: v1.0/empty.json
            output:
              o: 4
            tags:
            - workflow
            - inline_javascript
            - expression_tool
            tool: v1.0/io-int-optional-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test optional integer workflow inputs (unspecified)""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.workflow
    @pytest.mark.inline_javascript
    @pytest.mark.expression_tool
    @pytest.mark.green
    def test_conformance_v1_0_workflow_integer_input_default_specified(self):
        """Test default integer workflow inputs (specified)

        Generated from::

            id: workflow_integer_input_default_specified
            job: v1.0/io-int.json
            output:
              o: 10
            tags:
            - workflow
            - inline_javascript
            - expression_tool
            tool: v1.0/io-int-default-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test default integer workflow inputs (specified)""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.workflow
    @pytest.mark.inline_javascript
    @pytest.mark.expression_tool
    @pytest.mark.green
    def test_conformance_v1_0_workflow_integer_input_default_unspecified(self):
        """Test default integer workflow inputs (unspecified)

        Generated from::

            id: workflow_integer_input_default_unspecified
            job: v1.0/empty.json
            output:
              o: 8
            tags:
            - workflow
            - inline_javascript
            - expression_tool
            tool: v1.0/io-int-default-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test default integer workflow inputs (unspecified)""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.workflow
    @pytest.mark.inline_javascript
    @pytest.mark.expression_tool
    @pytest.mark.green
    def test_conformance_v1_0_workflow_integer_input_default_and_tool_integer_input_default(self):
        """Test default integer tool and workflow inputs (unspecified)

        Generated from::

            id: workflow_integer_input_default_and_tool_integer_input_default
            job: v1.0/empty.json
            output:
              o: 13
            tags:
            - workflow
            - inline_javascript
            - expression_tool
            tool: v1.0/io-int-default-tool-and-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test default integer tool and workflow inputs (unspecified)""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.workflow
    @pytest.mark.red
    def test_conformance_v1_0_workflow_file_input_default_unspecified(self):
        """Test File input with default unspecified to workflow

        Generated from::

            id: workflow_file_input_default_unspecified
            job: v1.0/empty.json
            output:
              o:
                basename: output
                checksum: sha1$327fc7aedf4f6b69a42a7c8b808dc5a7aff61376
                class: File
                location: Any
                size: 1111
            tags:
            - workflow
            tool: v1.0/io-file-default-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test File input with default unspecified to workflow""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.workflow
    @pytest.mark.green
    def test_conformance_v1_0_workflow_file_input_default_specified(self):
        """Test File input with default specified to workflow

        Generated from::

            id: workflow_file_input_default_specified
            job: v1.0/default_path_job.yml
            output:
              o:
                basename: output
                checksum: sha1$47a013e660d408619d894b20806b1d5086aab03b
                class: File
                location: Any
                size: 13
            tags:
            - workflow
            tool: v1.0/io-file-default-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test File input with default specified to workflow""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.command_line_tool
    @pytest.mark.inline_javascript
    @pytest.mark.green
    def test_conformance_v1_0_clt_optional_union_input_file_or_files_with_array_of_one_file_provided(self):
        """Test input union type or File or File array to a tool with one file in array specified.

        Generated from::

            id: clt_optional_union_input_file_or_files_with_array_of_one_file_provided
            job: v1.0/job-input-array-one-empty-file.json
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
            tool: v1.0/io-file-or-files.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test input union type or File or File array to a tool with one file in array specified.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.command_line_tool
    @pytest.mark.inline_javascript
    @pytest.mark.green
    def test_conformance_v1_0_clt_optional_union_input_file_or_files_with_many_files_provided(self):
        """Test input union type or File or File array to a tool with a few files in array specified.

        Generated from::

            id: clt_optional_union_input_file_or_files_with_many_files_provided
            job: v1.0/job-input-array-few-files.json
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
            tool: v1.0/io-file-or-files.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test input union type or File or File array to a tool with a few files in array specified.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.command_line_tool
    @pytest.mark.inline_javascript
    @pytest.mark.green
    def test_conformance_v1_0_clt_optional_union_input_file_or_files_with_single_file_provided(self):
        """Test input union type or File or File array to a tool with one file specified.

        Generated from::

            id: clt_optional_union_input_file_or_files_with_single_file_provided
            job: v1.0/job-input-one-file.json
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
            tool: v1.0/io-file-or-files.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test input union type or File or File array to a tool with one file specified.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.command_line_tool
    @pytest.mark.inline_javascript
    @pytest.mark.green
    def test_conformance_v1_0_clt_optional_union_input_file_or_files_with_nothing_provided(self):
        """Test input union type or File or File array to a tool with null specified.

        Generated from::

            id: clt_optional_union_input_file_or_files_with_nothing_provided
            job: v1.0/job-input-null.json
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
            tool: v1.0/io-file-or-files.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test input union type or File or File array to a tool with null specified.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.command_line_tool
    @pytest.mark.inline_javascript
    @pytest.mark.green
    def test_conformance_v1_0_clt_any_input_with_integer_provided(self):
        """Test Any parameter with integer input to a tool

        Generated from::

            id: clt_any_input_with_integer_provided
            job: v1.0/io-any-int.json
            output:
              t1: 7
            tags:
            - command_line_tool
            - inline_javascript
            tool: v1.0/io-any-1.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test Any parameter with integer input to a tool""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.command_line_tool
    @pytest.mark.inline_javascript
    @pytest.mark.green
    def test_conformance_v1_0_clt_any_input_with_string_provided(self):
        """Test Any parameter with string input to a tool

        Generated from::

            id: clt_any_input_with_string_provided
            job: v1.0/io-any-string.json
            output:
              t1: '7'
            tags:
            - command_line_tool
            - inline_javascript
            tool: v1.0/io-any-1.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test Any parameter with string input to a tool""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.command_line_tool
    @pytest.mark.inline_javascript
    @pytest.mark.green
    def test_conformance_v1_0_clt_any_input_with_file_provided(self):
        """Test Any parameter with file input to a tool

        Generated from::

            id: clt_any_input_with_file_provided
            job: v1.0/io-any-file.json
            output:
              t1: File
            tags:
            - command_line_tool
            - inline_javascript
            tool: v1.0/io-any-1.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test Any parameter with file input to a tool""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.command_line_tool
    @pytest.mark.inline_javascript
    @pytest.mark.red
    def test_conformance_v1_0_clt_any_input_with_mixed_array_provided(self):
        """Test Any parameter with array input to a tool

        Generated from::

            id: clt_any_input_with_mixed_array_provided
            job: v1.0/io-any-array.json
            output:
              t1:
              - 1
              - moocow
            tags:
            - command_line_tool
            - inline_javascript
            tool: v1.0/io-any-1.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test Any parameter with array input to a tool""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.command_line_tool
    @pytest.mark.inline_javascript
    @pytest.mark.green
    def test_conformance_v1_0_clt_any_input_with_record_provided(self):
        """Test Any parameter with record input to a tool

        Generated from::

            id: clt_any_input_with_record_provided
            job: v1.0/io-any-record.json
            output:
              t1:
                cow: 5
                moo: 1
            tags:
            - command_line_tool
            - inline_javascript
            tool: v1.0/io-any-1.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test Any parameter with record input to a tool""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.workflow
    @pytest.mark.inline_javascript
    @pytest.mark.green
    def test_conformance_v1_0_workflow_any_input_with_integer_provided(self):
        """Test Any parameter with integer input to a workflow

        Generated from::

            id: workflow_any_input_with_integer_provided
            job: v1.0/io-any-int.json
            output:
              t1: 7
            tags:
            - workflow
            - inline_javascript
            tool: v1.0/io-any-wf-1.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test Any parameter with integer input to a workflow""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.workflow
    @pytest.mark.inline_javascript
    @pytest.mark.green
    def test_conformance_v1_0_workflow_any_input_with_string_provided(self):
        """Test Any parameter with string input to a workflow

        Generated from::

            id: workflow_any_input_with_string_provided
            job: v1.0/io-any-string.json
            output:
              t1: '7'
            tags:
            - workflow
            - inline_javascript
            tool: v1.0/io-any-wf-1.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test Any parameter with string input to a workflow""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.workflow
    @pytest.mark.inline_javascript
    @pytest.mark.green
    def test_conformance_v1_0_workflow_any_input_with_file_provided(self):
        """Test Any parameter with file input to a workflow

        Generated from::

            id: workflow_any_input_with_file_provided
            job: v1.0/io-any-file.json
            output:
              t1: File
            tags:
            - workflow
            - inline_javascript
            tool: v1.0/io-any-wf-1.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test Any parameter with file input to a workflow""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.workflow
    @pytest.mark.inline_javascript
    @pytest.mark.green
    def test_conformance_v1_0_workflow_any_input_with_mixed_array_provided(self):
        """Test Any parameter with array input to a workflow

        Generated from::

            id: workflow_any_input_with_mixed_array_provided
            job: v1.0/io-any-array.json
            output:
              t1:
              - 1
              - moocow
            tags:
            - workflow
            - inline_javascript
            tool: v1.0/io-any-wf-1.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test Any parameter with array input to a workflow""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.workflow
    @pytest.mark.inline_javascript
    @pytest.mark.green
    def test_conformance_v1_0_workflow_any_input_with_record_provided(self):
        """Test Any parameter with record input to a tool in a workflow

        Generated from::

            id: workflow_any_input_with_record_provided
            job: v1.0/io-any-record.json
            output:
              t1:
                cow: 5
                moo: 1
            tags:
            - workflow
            - inline_javascript
            tool: v1.0/io-any-wf-1.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test Any parameter with record input to a tool in a workflow""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.workflow
    @pytest.mark.inline_javascript
    @pytest.mark.expression_tool
    @pytest.mark.green
    def test_conformance_v1_0_workflow_union_default_input_unspecified(self):
        """Test union type input to workflow with default unspecified

        Generated from::

            id: workflow_union_default_input_unspecified
            job: v1.0/empty.json
            output:
              o: the default value
            tags:
            - workflow
            - inline_javascript
            - expression_tool
            tool: v1.0/io-union-input-default-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test union type input to workflow with default unspecified""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.workflow
    @pytest.mark.inline_javascript
    @pytest.mark.expression_tool
    @pytest.mark.green
    def test_conformance_v1_0_workflow_union_default_input_with_file_provided(self):
        """Test union type input to workflow with default specified as file

        Generated from::

            id: workflow_union_default_input_with_file_provided
            job: v1.0/io-any-file.json
            output:
              o: File
            tags:
            - workflow
            - inline_javascript
            - expression_tool
            tool: v1.0/io-union-input-default-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test union type input to workflow with default specified as file""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.workflow
    @pytest.mark.step_input
    @pytest.mark.green
    def test_conformance_v1_0_workflowstep_valuefrom_string(self):
        """Test valueFrom on workflow step from literal (string).

        Generated from::

            id: workflowstep_valuefrom_string
            job: v1.0/empty.json
            output:
              val: 'moocow
            
                '
            tags:
            - workflow
            - step_input
            tool: v1.0/step-valuefrom4-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test valueFrom on workflow step from literal (string).""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.workflow
    @pytest.mark.step_input
    @pytest.mark.green
    def test_conformance_v1_0_workflowstep_valuefrom_file_basename(self):
        """Test valueFrom on workflow step using basename.

        Generated from::

            id: workflowstep_valuefrom_file_basename
            job: v1.0/wc-job.json
            output:
              val1: 'whale.txt
            
                '
              val2: 'step1_out
            
                '
            tags:
            - workflow
            - step_input
            tool: v1.0/step-valuefrom5-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test valueFrom on workflow step using basename.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.expression_tool
    @pytest.mark.inline_javascript
    @pytest.mark.green
    def test_conformance_v1_0_expression_tool_int_array_output(self):
        """Test output arrays in a tool (with ints).

        Generated from::

            id: expression_tool_int_array_output
            job: v1.0/output-arrays-int-job.json
            output:
              o:
              - 0
              - 1
              - 2
            tags:
            - expression_tool
            - inline_javascript
            tool: v1.0/output-arrays-int.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test output arrays in a tool (with ints).""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.workflow
    @pytest.mark.expression_tool
    @pytest.mark.inline_javascript
    @pytest.mark.green
    def test_conformance_v1_0_workflowstep_int_array_input_output(self):
        """Test output arrays in a workflow (with ints).

        Generated from::

            id: workflowstep_int_array_input_output
            job: v1.0/output-arrays-int-job.json
            output:
              o: 12
            tags:
            - workflow
            - expression_tool
            - inline_javascript
            tool: v1.0/output-arrays-int-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test output arrays in a workflow (with ints).""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.workflow
    @pytest.mark.expression_tool
    @pytest.mark.inline_javascript
    @pytest.mark.red
    def test_conformance_v1_0_workflow_file_array_output(self):
        """Test output arrays in a workflow (with Files).

        Generated from::

            id: workflow_file_array_output
            job: v1.0/output-arrays-file-job.json
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
            tool: v1.0/output-arrays-file-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test output arrays in a workflow (with Files).""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.command_line_tool
    @pytest.mark.docker
    @pytest.mark.red
    def test_conformance_v1_0_docker_entrypoint(self):
        """Test Docker ENTRYPOINT usage

        Generated from::

            id: docker_entrypoint
            job: v1.0/empty.json
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
            tool: v1.0/docker-run-cmd.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test Docker ENTRYPOINT usage""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.command_line_tool
    @pytest.mark.inline_javascript
    @pytest.mark.green
    def test_conformance_v1_0_clt_file_size_property_with_empty_file(self):
        """Test use of size in expressions for an empty file

        Generated from::

            id: clt_file_size_property_with_empty_file
            job: v1.0/job-input-array-one-empty-file.json
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
            tool: v1.0/size-expression-tool.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test use of size in expressions for an empty file""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.command_line_tool
    @pytest.mark.inline_javascript
    @pytest.mark.green
    def test_conformance_v1_0_clt_file_size_property_with_multi_file(self):
        """Test use of size in expressions for a few files

        Generated from::

            id: clt_file_size_property_with_multi_file
            job: v1.0/job-input-array-few-files.json
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
            tool: v1.0/size-expression-tool.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test use of size in expressions for a few files""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.command_line_tool
    @pytest.mark.required
    @pytest.mark.green
    def test_conformance_v1_0_any_without_defaults_unspecified_fails(self):
        """Test Any without defaults, unspecified, should fail.

        Generated from::

            id: any_without_defaults_unspecified_fails
            job: v1.0/null-expression-echo-job.json
            should_fail: true
            tags:
            - command_line_tool
            - required
            tool: v1.0/echo-tool.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test Any without defaults, unspecified, should fail.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.command_line_tool
    @pytest.mark.required
    @pytest.mark.green
    def test_conformance_v1_0_any_without_defaults_specified_fails(self):
        """Test Any without defaults, specified, should fail.

        Generated from::

            id: any_without_defaults_specified_fails
            job: v1.0/null-expression1-job.json
            should_fail: true
            tags:
            - command_line_tool
            - required
            tool: v1.0/echo-tool.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test Any without defaults, specified, should fail.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.workflow
    @pytest.mark.required
    @pytest.mark.green
    def test_conformance_v1_0_step_input_default_value_noexp(self):
        """Test default value on step input parameter, no ExpressionTool

        Generated from::

            id: step_input_default_value_noexp
            job: v1.0/empty.json
            output:
              wc_output:
                checksum: sha1$3596ea087bfdaf52380eae441077572ed289d657
                class: File
                size: 3
            tags:
            - workflow
            - required
            tool: v1.0/count-lines9-wf-noET.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test default value on step input parameter, no ExpressionTool""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.workflow
    @pytest.mark.required
    @pytest.mark.red
    def test_conformance_v1_0_step_input_default_value_overriden_noexp(self):
        """Test default value on step input parameter overridden by provided source, no ExpressionTool

        Generated from::

            id: step_input_default_value_overriden_noexp
            job: v1.0/cat-job.json
            output:
              wc_output:
                checksum: sha1$e5fa44f2b31c1fb553b6021e7360d07d5d91ff5e
                class: File
                size: 2
            tags:
            - workflow
            - required
            tool: v1.0/count-lines11-wf-noET.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test default value on step input parameter overridden by provided source, no ExpressionTool""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.workflow
    @pytest.mark.subworkflow
    @pytest.mark.green
    def test_conformance_v1_0_nested_workflow_noexp(self):
        """Test nested workflow, without ExpressionTool

        Generated from::

            id: nested_workflow_noexp
            job: v1.0/wc-job.json
            output:
              wc_output:
                checksum: sha1$3596ea087bfdaf52380eae441077572ed289d657
                class: File
                size: 3
            tags:
            - workflow
            - subworkflow
            tool: v1.0/count-lines8-wf-noET.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test nested workflow, without ExpressionTool""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.workflow
    @pytest.mark.step_input
    @pytest.mark.inline_javascript
    @pytest.mark.multiple_input
    @pytest.mark.red
    def test_conformance_v1_0_wf_multiplesources_multipletypes_noexp(self):
        """Test step input with multiple sources with multiple types, without ExpressionTool

        Generated from::

            id: wf_multiplesources_multipletypes_noexp
            job: v1.0/sum-job.json
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
            tool: v1.0/sum-wf-noET.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test step input with multiple sources with multiple types, without ExpressionTool""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.workflow
    @pytest.mark.resource
    @pytest.mark.red
    def test_conformance_v1_0_dynamic_resreq_wf_optional_file_default(self):
        """Within a workflow, test accessing the size attribute of an optional input File as part of a CommandLineTool's ResourceRequirement calculation. The CommandLineTool input has a default value (a local file) and the workflow nor the workflow step does not provide any value for this input.

        Generated from::

            id: dynamic_resreq_wf_optional_file_default
            job: v1.0/empty.json
            output:
              cores:
                checksum: sha1$7448d8798a4380162d4b56f9b452e2f6f9e24e7a
                class: File
                location: output
                size: 2
            tags:
            - workflow
            - resource
            tool: v1.0/dynresreq-workflow-tooldefault.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Within a workflow, test accessing the size attribute of an optional input File as part of a CommandLineTool's ResourceRequirement calculation. The CommandLineTool input has a default value (a local file) and the workflow nor the workflow step does not provide any value for this input.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.workflow
    @pytest.mark.resource
    @pytest.mark.green
    def test_conformance_v1_0_dynamic_resreq_wf_optional_file_step_default(self):
        """Within a workflow, test accessing the size attribute of an optional input File as part of a CommandLineTool's ResourceRequirement calculation. The workflow step provides a default value (a local file) for this input and the workflow itself does not provide any value for this input.

        Generated from::

            id: dynamic_resreq_wf_optional_file_step_default
            job: v1.0/empty.json
            output:
              cores:
                checksum: sha1$7448d8798a4380162d4b56f9b452e2f6f9e24e7a
                class: File
                location: output
                size: 2
            tags:
            - workflow
            - resource
            tool: v1.0/dynresreq-workflow-stepdefault.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Within a workflow, test accessing the size attribute of an optional input File as part of a CommandLineTool's ResourceRequirement calculation. The workflow step provides a default value (a local file) for this input and the workflow itself does not provide any value for this input.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.workflow
    @pytest.mark.resource
    @pytest.mark.red
    def test_conformance_v1_0_dynamic_resreq_wf_optional_file_wf_default(self):
        """Within a workflow, test accessing the size attribute of an optional input File as part of a CommandLineTool's ResourceRequirement calculation. The workflow itself provides a default value (a local file) for this input.

        Generated from::

            id: dynamic_resreq_wf_optional_file_wf_default
            job: v1.0/empty.json
            output:
              cores:
                checksum: sha1$7448d8798a4380162d4b56f9b452e2f6f9e24e7a
                class: File
                location: output
                size: 2
            tags:
            - workflow
            - resource
            tool: v1.0/dynresreq-workflow-inputdefault.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Within a workflow, test accessing the size attribute of an optional input File as part of a CommandLineTool's ResourceRequirement calculation. The workflow itself provides a default value (a local file) for this input.""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.workflow
    @pytest.mark.inline_javascript
    @pytest.mark.red
    def test_conformance_v1_0_step_input_default_value_overriden_2nd_step(self):
        """Test default value on step input parameter overridden by provided source. With passthrough first step

        Generated from::

            id: step_input_default_value_overriden_2nd_step
            job: v1.0/cat-job.json
            output:
              count_output: 1
            tags:
            - workflow
            - inline_javascript
            tool: v1.0/count-lines11-extra-step-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test default value on step input parameter overridden by provided source. With passthrough first step""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.workflow
    @pytest.mark.required
    @pytest.mark.red
    def test_conformance_v1_0_step_input_default_value_overriden_2nd_step_noexp(self):
        """Test default value on step input parameter overridden by provided source. With passthrough first step and no ExpressionTool

        Generated from::

            id: step_input_default_value_overriden_2nd_step_noexp
            job: v1.0/cat-job.json
            output:
              wc_output:
                checksum: sha1$e5fa44f2b31c1fb553b6021e7360d07d5d91ff5e
                class: File
                size: 2
            tags:
            - workflow
            - required
            tool: v1.0/count-lines11-extra-step-wf-noET.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test default value on step input parameter overridden by provided source. With passthrough first step and no ExpressionTool""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.workflow
    @pytest.mark.inline_javascript
    @pytest.mark.green
    def test_conformance_v1_0_step_input_default_value_overriden_2nd_step_null(self):
        """Test default value on step input parameter overridden by provided source. With null producing first step

        Generated from::

            id: step_input_default_value_overriden_2nd_step_null
            job: v1.0/empty.json
            output:
              count_output: 16
            tags:
            - workflow
            - inline_javascript
            tool: v1.0/count-lines11-null-step-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test default value on step input parameter overridden by provided source. With null producing first step""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.workflow
    @pytest.mark.required
    @pytest.mark.green
    def test_conformance_v1_0_step_input_default_value_overriden_2nd_step_null_noexp(self):
        """Test default value on step input parameter overridden by provided source. With null producing first step and no ExpressionTool

        Generated from::

            id: step_input_default_value_overriden_2nd_step_null_noexp
            job: v1.0/empty.json
            output:
              wc_output:
                checksum: sha1$3596ea087bfdaf52380eae441077572ed289d657
                class: File
                size: 3
            tags:
            - workflow
            - required
            tool: v1.0/count-lines11-null-step-wf-noET.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test default value on step input parameter overridden by provided source. With null producing first step and no ExpressionTool""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.command_line_tool
    @pytest.mark.required
    @pytest.mark.green
    def test_conformance_v1_0_stdin_from_directory_literal_with_local_file(self):
        """Pipe to stdin from user provided local File via a Directory literal

        Generated from::

            id: stdin_from_directory_literal_with_local_file
            job: v1.0/cat-from-dir-job.yaml
            output:
              output:
                checksum: sha1$47a013e660d408619d894b20806b1d5086aab03b
                class: File
                size: 13
            tags:
            - command_line_tool
            - required
            tool: v1.0/cat-from-dir.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Pipe to stdin from user provided local File via a Directory literal""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.command_line_tool
    @pytest.mark.required
    @pytest.mark.green
    def test_conformance_v1_0_stdin_from_directory_literal_with_literal_file(self):
        """Pipe to stdin from literal File via a Directory literal

        Generated from::

            id: stdin_from_directory_literal_with_literal_file
            job: v1.0/cat-from-dir-with-literal-file.yaml
            output:
              output:
                checksum: sha1$ef88e689559565999700d6fea7cf7ba306d04360
                class: File
                size: 26
            tags:
            - command_line_tool
            - required
            tool: v1.0/cat-from-dir.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Pipe to stdin from literal File via a Directory literal""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.command_line_tool
    @pytest.mark.required
    @pytest.mark.green
    def test_conformance_v1_0_directory_literal_with_literal_file_nostdin(self):
        """Test non-stdin reference to literal File via a Directory literal

        Generated from::

            id: directory_literal_with_literal_file_nostdin
            job: v1.0/cat-from-dir-with-literal-file.yaml
            output:
              output_file:
                checksum: sha1$ef88e689559565999700d6fea7cf7ba306d04360
                class: File
                size: 26
            tags:
            - command_line_tool
            - required
            tool: v1.0/cat3-from-dir.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test non-stdin reference to literal File via a Directory literal""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.command_line_tool
    @pytest.mark.required
    @pytest.mark.green
    def test_conformance_v1_0_no_inputs_commandlinetool(self):
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
            tool: v1.0/no-inputs-tool.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test CommandLineTool without inputs""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.command_line_tool
    @pytest.mark.required
    @pytest.mark.green
    def test_conformance_v1_0_no_outputs_commandlinetool(self):
        """Test CommandLineTool without outputs

        Generated from::

            id: no_outputs_commandlinetool
            job: v1.0/cat-job.json
            output: {}
            tags:
            - command_line_tool
            - required
            tool: v1.0/no-outputs-tool.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test CommandLineTool without outputs""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.workflow
    @pytest.mark.required
    @pytest.mark.green
    def test_conformance_v1_0_no_inputs_workflow(self):
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
            tool: v1.0/no-inputs-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test Workflow without inputs""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.workflow
    @pytest.mark.required
    @pytest.mark.green
    def test_conformance_v1_0_no_outputs_workflow(self):
        """Test Workflow without outputs

        Generated from::

            id: no_outputs_workflow
            job: v1.0/cat-job.json
            output: {}
            tags:
            - workflow
            - required
            tool: v1.0/no-outputs-wf.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test Workflow without outputs""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.command_line_tool
    @pytest.mark.required
    @pytest.mark.green
    def test_conformance_v1_0_anonymous_enum_in_array(self):
        """Test an anonymous enum inside an array inside a record

        Generated from::

            id: anonymous_enum_in_array
            job: v1.0/anon_enum_inside_array.yml
            output:
              result:
                checksum: sha1$2132943d72c39423e0b9425cbc40dfd5bf3e9cb2
                class: File
                size: 39
            tags:
            - command_line_tool
            - required
            tool: v1.0/anon_enum_inside_array.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test an anonymous enum inside an array inside a record""")

    @pytest.mark.cwl_conformance
    @pytest.mark.cwl_conformance_v1_0
    @pytest.mark.command_line_tool
    @pytest.mark.schema_def
    @pytest.mark.green
    def test_conformance_v1_0_schema_def_anonymous_enum_in_array(self):
        """Test an anonymous enum inside an array inside a record, SchemaDefRequirement

        Generated from::

            id: schema-def_anonymous_enum_in_array
            job: v1.0/anon_enum_inside_array_inside_schemadef.yml
            output:
              result:
                checksum: sha1$f17c7d81f66e1520fca25b96b90eeeae5bbf08b0
                class: File
                size: 39
            tags:
            - command_line_tool
            - schema_def
            tool: v1.0/anon_enum_inside_array_inside_schemadef.cwl
        """  # noqa: W293
        self.cwl_populator.run_conformance_test("""v1.0""", """Test an anonymous enum inside an array inside a record, SchemaDefRequirement""")
