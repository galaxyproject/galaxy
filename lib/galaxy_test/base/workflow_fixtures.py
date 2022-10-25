WORKFLOW_SIMPLE_CAT_AND_RANDOM_LINES = """
class: GalaxyWorkflow
doc: |
  Simple workflow that no-op cats a file and then selects 10 random lines.
creator:
  - class: Person
    name: John Chilton
    email: jmchilton@gmail.com
    identifier: https://orcid.org/0000-0002-6794-0756
inputs:
  the_input:
    type: data
    doc: input doc
steps:
  - tool_id: cat1
    doc: cat doc
    in:
      input1: the_input
  - tool_id: cat1
    in:
      input1: 1/out_file1
  - tool_id: random_lines1
    label: random_line_label
    state:
      num_lines: 10
      seed_source:
        seed_source_selector: set_seed
        seed: asdf
    in:
      input: 2/out_file1
"""


WORKFLOW_SIMPLE_CAT_TWICE = """
class: GalaxyWorkflow
inputs:
  input1: data
steps:
  first_cat:
    tool_id: cat
    in:
      input1: input1
      queries_0|input2: input1
"""


WORKFLOW_WITH_OLD_TOOL_VERSION = """
class: GalaxyWorkflow
inputs:
  input1: data
steps:
  mul_versions:
    tool_id: multiple_versions
    tool_version: "0.0.1"
    state:
      inttest: 8
"""


WORKFLOW_SELECT_FROM_OPTIONAL_DATASET = """
class: GalaxyWorkflow
steps:
  select_from_dataset_optional:
    tool_id: select_from_dataset_optional
    state:
      select_single: null
"""


# Throwing a bunch of broken steps in to get a really long modal and sure it
# is scrollable.
WORKFLOW_WITH_INVALID_STATE = """
class: GalaxyWorkflow
inputs:
  input1: data
steps:
  mul_versions_1:
    tool_id: multiple_versions
    tool_version: "0.0.1"
    state:
      inttest: "moocow"
  'another bad step':
    tool_id: multiple_versions
    tool_version: "0.0.3c"
    state:
      inttest: "moocow"
  'another bad step':
    tool_id: multiple_versions
    tool_version: "0.0.3c"
    state:
      inttest: "moocow"
  'another bad step2':
    tool_id: multiple_versions
    tool_version: "0.0.3c"
    state:
      inttest: "moocow"
  'another bad step3':
    tool_id: multiple_versions
    tool_version: "0.0.3c"
    state:
      inttest: "moocow"
  'another bad step4':
    tool_id: multiple_versions
    tool_version: "0.0.3c"
    state:
      inttest: "moocow"
  'another bad step5':
    tool_id: multiple_versions
    tool_version: "0.0.3c"
    state:
      inttest: "moocow"
  'another bad step6':
    tool_id: multiple_versions
    tool_version: "0.0.3c"
    state:
      inttest: "moocow"
  'another bad step7':
    tool_id: multiple_versions
    tool_version: "0.0.3c"
    state:
      inttest: "moocow"
  'another bad step8':
    tool_id: multiple_versions
    tool_version: "0.0.3c"
    state:
      inttest: "moocow"
  'another bad step9':
    tool_id: multiple_versions
    tool_version: "0.0.3c"
    state:
      inttest: "moocow"
  'another bad step10':
    tool_id: multiple_versions
    tool_version: "0.0.3c"
    state:
      inttest: "moocow"
  'another bad step11':
    tool_id: multiple_versions
    tool_version: "0.0.3c"
    state:
      inttest: "moocow"
  'another bad step12':
    tool_id: multiple_versions
    tool_version: "0.0.3c"
    state:
      inttest: "moocow"
  'another bad step13':
    tool_id: multiple_versions
    tool_version: "0.0.3c"
    state:
      inttest: "moocow"
  'another bad step14':
    tool_id: multiple_versions
    tool_version: "0.0.3c"
    state:
      inttest: "moocow"
"""


WORKFLOW_WITH_OUTPUT_COLLECTION = """
class: GalaxyWorkflow
inputs:
  text_input: data
steps:
  split_up:
    tool_id: collection_creates_pair
    in:
      input1: text_input
  paired:
    tool_id: collection_paired_test
    in:
      f1: split_up/paired_output
test_data:
  text_input: |
    a
    b
    c
    d
"""

WORKFLOW_WITH_MAPPED_OUTPUT_COLLECTION = """
class: GalaxyWorkflow
inputs:
  input1:
    type: data_collection_input
    collection_type: list
outputs:
  wf_output_1:
    outputSource: first_cat/out_file1
steps:
  first_cat:
    tool_id: cat
    in:
      input1: input1
"""

WORKFLOW_WITH_DYNAMIC_OUTPUT_COLLECTION = """
class: GalaxyWorkflow
inputs:
  text_input1: data
  text_input2: data
steps:
  cat_inputs:
    tool_id: cat1
    in:
      input1: text_input1
      queries_0|input2: text_input2
  split_up:
    tool_id: collection_split_on_column
    in:
      input1: cat_inputs/out_file1
  cat_list:
    tool_id: cat_list
    in:
      input1: split_up/split_output
test_data:
  text_input1: |
    samp1\t10.0
    samp2\t20.0
  text_input2: |
    samp1\t30.0
    samp2\t40.0
"""


WORKFLOW_SIMPLE_MAPPING = """
class: GalaxyWorkflow
inputs:
  input1:
    type: collection
    collection_type: list
steps:
  cat:
    tool_id: cat
    in:
      input1: input1
"""


WORKFLOW_WITH_OUTPUT_COLLECTION_MAPPING = """
class: GalaxyWorkflow
steps:
  - type: input_collection
  - tool_id: collection_creates_pair
    state:
      input1:
        $link: 0
  - tool_id: collection_paired_test
    state:
      f1:
        $link: 1/paired_output
  - tool_id: cat_list
    state:
      input1:
        $link: 2/out1
"""


WORKFLOW_WITH_RULES_1 = """
class: GalaxyWorkflow
inputs:
  input_c: collection
steps:
  apply:
    tool_id: __APPLY_RULES__
    state:
      input:
        $link: input_c
      rules:
        rules:
          - type: add_column_metadata
            value: identifier0
          - type: add_column_metadata
            value: identifier0
        mapping:
          - type: list_identifiers
            columns: [0, 1]
  random_lines:
    tool_id: random_lines1
    state:
      num_lines: 1
      input:
        $link: apply/output
      seed_source:
        seed_source_selector: set_seed
        seed: asdf
test_data:
  input_c:
    collection_type: list
    elements:
      - identifier: i1
        content: "0"
      - identifier: i2
        content: "1"
"""


WORKFLOW_WITH_RULES_2 = """
class: GalaxyWorkflow
inputs:
  input_c: collection
steps:
  apply:
    tool_id: __APPLY_RULES__
    state:
      input:
        $link: input_c
      rules:
        rules:
          - type: add_column_metadata
            value: identifier0
          - type: add_column_metadata
            value: identifier0
        mapping:
          - type: list_identifiers
            columns: [0, 1]
  copy_list:
    tool_id: collection_creates_list
    in:
      input1: apply/output
test_data:
  input_c:
    type: list
    elements:
      - identifier: i1
        content: "0"
      - identifier: i2
        content: "1"
"""


WORKFLOW_NESTED_SIMPLE = """
class: GalaxyWorkflow
inputs:
  outer_input: data
outputs:
  outer_output:
    outputSource: second_cat/out_file1
steps:
  first_cat:
    tool_id: cat1
    in:
      input1: outer_input
  nested_workflow:
    run:
      class: GalaxyWorkflow
      inputs:
        inner_input: data
      outputs:
        workflow_output:
          outputSource: random_lines/out_file1
      steps:
        random_lines:
          tool_id: random_lines1
          state:
            num_lines: 1
            input:
              $link: inner_input
            seed_source:
              seed_source_selector: set_seed
              seed: asdf
    in:
      inner_input: first_cat/out_file1
  second_cat:
    tool_id: cat1
    in:
      input1: nested_workflow/workflow_output
      queries_0|input2: nested_workflow/workflow_output
"""


WORKFLOW_NESTED_RUNTIME_PARAMETER = """
class: GalaxyWorkflow
inputs:
  outer_input: data
outputs:
  outer_output:
    outputSource: nested_workflow/workflow_output
steps:
  nested_workflow:
    run:
      class: GalaxyWorkflow
      inputs:
        inner_input: data
      outputs:
        workflow_output:
          outputSource: random_lines/out_file1
      steps:
        - tool_id: random_lines1
          label: random_lines
          runtime_inputs:
            - num_lines
          state:
            input:
              $link: inner_input
            seed_source:
              seed_source_selector: set_seed
              seed: asdf
    in:
      inner_input: outer_input
"""

WORKFLOW_NESTED_WITH_MULTIPLE_VERSIONS_TOOL = """
class: GalaxyWorkflow
inputs:
  outer_input: data
outputs:
  outer_output:
    outputSource: cat/out_file1
steps:
  tool_update_step:
    tool_id: multiple_versions
    tool_version: '0.1'
    in:
      input1: outer_input
  nested_workflow:
    run:
      class: GalaxyWorkflow
      inputs:
        inner_input: data
      outputs:
        workflow_output:
          outputSource: random_lines/out_file1
      steps:
        random_lines:
          tool_id: random_lines1
          state:
            num_lines: 1
            input:
              $link: inner_input
            seed_source:
              seed_source_selector: set_seed
              seed: asdf
    in:
      inner_input: tool_update_step/out_file1
  cat:
    tool_id: cat1
    in:
      input1: nested_workflow/workflow_output
      queries_0|input2: nested_workflow/workflow_output
  compose_text_param:
    tool_id: compose_text_param
    tool_version: 0.1.0
    label: compose_text_param
"""

WORKFLOW_WITH_OUTPUT_ACTIONS = """
class: GalaxyWorkflow
inputs:
  input1: data
steps:
  first_cat:
    tool_id: cat1
    outputs:
       out_file1:
         hide: true
         rename: "the new value"
    in:
      input1: input1
  second_cat:
    tool_id: cat1
    in:
      input1: first_cat/out_file1
"""

WORKFLOW_INPUTS_AS_OUTPUTS = """
class: GalaxyWorkflow
inputs:
  input1: data
  text_input: text
outputs:
  wf_output_1:
    outputSource: input1
  wf_output_param:
    outputSource: text_input
steps: []
"""

WORKFLOW_PARAMETER_INPUT_INTEGER_REQUIRED = """
class: GalaxyWorkflow
inputs:
  data_input: data
  int_input: integer
steps:
  random:
    tool_id: random_lines1
    in:
      input: data_input
      num_lines: int_input
    state:
      seed_source:
        seed_source_selector: set_seed
        seed: asdf
"""


WORKFLOW_PARAMETER_INPUT_INTEGER_OPTIONAL = """
class: GalaxyWorkflow
inputs:
  data_input: data
  int_input:
    type: integer
    optional: true
steps:
  random:
    tool_id: random_lines1
    in:
      input: data_input
      num_lines: int_input
    state:
      seed_source:
        seed_source_selector: set_seed
        seed: asdf
"""


WORKFLOW_PARAMETER_INPUT_INTEGER_DEFAULT = """
class: GalaxyWorkflow
inputs:
  data_input: data
  int_input:
    type: integer
    default: 3
steps:
  random:
    tool_id: random_lines1
    in:
      input: data_input
      num_lines: int_input
    state:
      seed_source:
        seed_source_selector: set_seed
        seed: asdf
"""


WORKFLOW_OPTIONAL_TRUE_INPUT_DATA = """
class: GalaxyWorkflow
inputs:
  input1:
    type: data
    optional: true
outputs:
  out1:
    outputSource: the_tool/out1
steps:
  the_tool:
    tool_id: multi_data_optional
    in:
      input1: input1
    out:
      out1: out1
"""


# Same workflow but non-optional input
WORKFLOW_OPTIONAL_FALSE_INPUT_DATA = """
class: GalaxyWorkflow
inputs:
  input1:
    type: data
    optional: false
outputs:
  out1:
    outputSource: the_tool/out1
steps:
  the_tool:
    tool_id: multi_data_optional
    in:
      input1: input1
    out:
      out1: out1
"""


WORKFLOW_OPTIONAL_TRUE_INPUT_COLLECTION = """
class: GalaxyWorkflow
inputs:
  input1:
    type: collection
    collection_type: paired
    optional: true
outputs:
  out1:
    outputSource: the_tool/out1
steps:
  the_tool:
    tool_id: collection_optional_param
    in:
      f1: input1
    out:
      out1: out1
"""


# Same workflow but non-optional input
WORKFLOW_OPTIONAL_FALSE_INPUT_COLLECTION = """
class: GalaxyWorkflow
inputs:
  input1:
    type: collection
    collection_type: paired
    optional: false
outputs:
  out1:
    outputSource: the_tool/out1
steps:
  the_tool:
    tool_id: collection_optional_param
    in:
      f1: input1
    out:
      out1: out1
"""


WORKFLOW_OPTIONAL_INPUT_DELAYED_SCHEDULING = """
class: GalaxyWorkflow
inputs:
  required:
    type: data
  optional:
    type: data
    optional: true
outputs:
  out1:
    outputSource: count_multi_file/out_file1
steps:
  expression:
    tool_id: expression_parse_int
    state:
      input1: 1
  head:
    tool_id: head
    in:
      input: required
    state:
      lineNum:
        $link:  expression/out1
  count_multi_file:
    tool_id: count_multi_file
    in:
      input1:
      - optional
      - head/out_file1
    out:
      out_file1: out_file1
test_data:
  required:
    value: 1.bed
    type: File
"""


WORKFLOW_RUNTIME_PARAMETER_SIMPLE = """
class: GalaxyWorkflow
inputs:
  input1: data
steps:
  random:
    tool_id: random_lines1
    runtime_inputs:
      - num_lines
    state:
      input:
        $link: input1
      seed_source:
        seed_source_selector: set_seed
        seed: asdf
"""


WORKFLOW_RUNTIME_PARAMETER_AFTER_PAUSE = """
class: GalaxyWorkflow
inputs:
  input1: data
steps:
  the_pause:
    type: pause
    in:
      input: input1
  random:
    tool_id: random_lines1
    runtime_inputs:
      - num_lines
    state:
      input:
        $link: the_pause
      seed_source:
        seed_source_selector: set_seed
        seed: asdf
"""

WORKFLOW_RENAME_ON_INPUT = """
class: GalaxyWorkflow
inputs:
  input1: data
steps:
  first_cat:
    tool_id: cat
    state:
      input1:
        $link: input1
    outputs:
      out_file1:
        rename: "#{input1 | basename} suffix"
test_data:
  input1:
    value: 1.fasta
    type: File
    name: fasta1
"""

WORKFLOW_RENAME_ON_REPLACEMENT_PARAM = """
class: GalaxyWorkflow
inputs:
  input1: data
steps:
  first_cat:
    tool_id: cat
    in:
      input1: input1
    outputs:
      out_file1:
        rename: "${replaceme} suffix"
"""

WORKFLOW_NESTED_REPLACEMENT_PARAMETER = """
class: GalaxyWorkflow
inputs:
  outer_input: data
outputs:
  outer_output:
    outputSource: nested_workflow/workflow_output
steps:
  nested_workflow:
    run:
      class: GalaxyWorkflow
      inputs:
        inner_input: data
      outputs:
        workflow_output:
          outputSource: first_cat/out_file1
      steps:
        - tool_id: cat
          label: first_cat
          in:
            input1: inner_input
          outputs:
            out_file1:
              rename: "${replaceme} suffix"
    in:
      inner_input: outer_input
"""

WORKFLOW_ONE_STEP_DEFAULT = """
class: GalaxyWorkflow
inputs:
  input: data
steps:
  randomlines:
    tool_id: random_lines1
    in:
      input: input
      num_lines:
        default: 6
"""

WORKFLOW_WITH_OUTPUTS = """
class: GalaxyWorkflow
inputs:
  input1: data
outputs:
  wf_output_1:
    outputSource: first_cat/out_file1
steps:
  first_cat:
    tool_id: cat1
    in:
      input1: input1
      queries_0|input2: input1
"""

WORKFLOW_WITH_CUSTOM_REPORT_1 = """
class: GalaxyWorkflow
name: My Cool Workflow
inputs:
  input_1: data
  image_input: data
  input_list: collection
outputs:
  output_1:
    outputSource: first_cat/out_file1
  output_image:
    outputSource: image_cat/out_file1
steps:
  first_cat:
    tool_id: cat
    in:
      input1: input_1
  image_cat:
    tool_id: cat
    in:
      input1: image_input
  qc_step:
    tool_id: qc_stdout
    state:
      quality: 9
    in:
      input: input_1
report:
  markdown: |
    ## About This Report

    This report is generated from markdown content in the workflow YAML/JSON.
    Workflow invocation reports provide a customizable way for workflow authors
    to summarize the results of a workflow execution. There is a default markdown
    template if a workflow does not define one (right now it just shows the inputs,
    outputs, and workflow - but this will evolve).

    This report is written in "Galaxy Workflow Flavored Markdown". This workflow
    variant of "Galaxy Flavored Markdown" contains workflow-relative references.
    Dataset, collections, and jobs are referenced by step labels, input labels, and output
    labels - rather than by object IDs. The Galaxy invocation report generator plugin
    translates this to "Galaxy Flavored Markdown" at the time the report is viewed and
    that format references actual object IDs (by database ID internally, and encoded ID
    when exported to the client via the API).

    An upshot of translating the workflow markdown to this second neutral format that
    has no concept of the workflow invocation is that client side rendering (and much
    of the backend processing) is completely general and not tied to workflows or
    invocations. The same markdown components could potentially be used to render pages,
    history annotations, describe library folders, etc..

    The next two sections demonstrate the auto generated inputs and outputs sections
    in the default workflow invocation report template.

    ## Workflow Inputs
    ```galaxy
    invocation_inputs()
    ```

    ## Workflow Outputs
    ```galaxy
    invocation_outputs()
    ```

    The auto-generated sections could be hand-crafted from workflow markdown also,
    listing out each input and output explicitly. The auto generated sections are merely
    a convenience to avoid needing to that by hand and for supplying a default report
    for workflows that don't define a custom one report.

    ## More Custom Content

    The rest of this report demonstrates more the directives allowed in the report
    markdown. ``invocation_outputs`` and ``invocation_inputs`` are not allow in
    "Galaxy Flavored Markdown" (the non-workflow invocation specific format), but
    the remainder of these are allowed - they would just need to reference object
    IDs instead of inputs, outputs, and steps.

    Once can reference an output and embed a display of it as follows:

    ```galaxy
    history_dataset_display(output=output_1)
    ```

    Inputs can be referenced and displayed the same way:

    ```galaxy
    history_dataset_display(input=input_1)
    ```

    ---

    Images can be embedded directly into the report as follows:

    ```galaxy
    history_dataset_as_image(output=output_image)
    ```

    ---

    Dataset peek content can be displayed to quickly provided an embedded
    summary of an input or output:

    ```galaxy
    history_dataset_peek(output=output_1)
    ```

    ---

    Dataset "info" content can be displayed as well:

    ```galaxy
    history_dataset_info(input=input_1)
    ```

    ---

    Collections can be displayed:

    ```galaxy
    history_dataset_collection_display(input=input_list)
    ```

    ---

    The whole workflow can be embedded to provide some context and display
    annotations and steps.

    ```galaxy
    workflow_display()
    ```

    ---

    Job parameters can be summarized:

    ```galaxy
    job_parameters(step=qc_step)
    ```

    ---

    Job metrics can be summarized as well:

    ```galaxy
    job_metrics(step=image_cat)
    ```

    ---

    Tool standard out and error are also available for steps.

    ```galaxy
    tool_stdout(step=qc_step)
    ```

    ```galaxy
    tool_stderr(step=qc_step)
    ```

    ---

    *fin*

"""

WORKFLOW_WITH_CUSTOM_REPORT_1_TEST_DATA = """
input_1:
  value: 1.bed
  type: File
  name: my bed file
image_input:
  value: 454Score.png
  type: File
  file_type: png
  name: my input image
input_list:
  collection_type: list
  elements:
    - identifier: i1
      content: "0"
  name: example list
"""


WORKFLOW_WITH_BAD_COLUMN_PARAMETER = """
class: GalaxyWorkflow
inputs:
    bed_input: data
steps:
  cat1:
    tool_id: cat1
    in:
      input1: bed_input
  column_param_list:
    tool_id: column_param
    in:
      input1: cat1/out_file1
    state:
      col: 9
      col_names: notacolumn
"""


WORKFLOW_WITH_BAD_COLUMN_PARAMETER_GOOD_TEST_DATA = """
step_parameters:
  '2':
    'col': 1
    'col_names': 'c1: chr1'
bed_input:
  value: 1.bed
  file_type: bed
  type: File
"""
