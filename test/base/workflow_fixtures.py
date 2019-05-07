

WORKFLOW_SIMPLE_CAT_AND_RANDOM_LINES = """
class: GalaxyWorkflow
doc: |
  Simple workflow that no-op cats a file and then selects 10 random lines.
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


WORKFLOW_WITH_INVALID_STATE = """
class: GalaxyWorkflow
inputs:
  input1: data
steps:
  mul_versions:
    tool_id: multiple_versions
    tool_version: "0.0.1"
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
        $link: 1#paired_output
  - tool_id: cat_list
    state:
      input1:
        $link: 2#out1
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
        $link: apply#output
      seed_source:
        seed_source_selector: set_seed
        seed: asdf
test_data:
  input_c:
    type: list
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
          outputSource: random_lines#out_file1
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
  sections:
    - type: free_markdown
      content: |
        The next three sections (inputs, outputs, and workflow) are auto generated sections
        of the 'core' invocation report generator plugin. That plugin automatically
        produces Galaxy Workflow Flavored Markdown from an invocation run.

        This section and the last one are custom markdown (``free_markdown``) sections. The
        auto-generated sections could easily hand-crafted from free markdown also - the auto
        generated sections are for convenience and for supplying a default report for workflows
        that don't define one.

        As you'll see below in the last section, "Galaxy Workflow Flavored Markdown" is an
        extension to markdown that allow referencing and embedding Galaxy objects. In particular
        "Galaxy Workflow Flavored Markdown" contains workflow-relative references. The report generator
        plugin translates this to "Galaxy Flavored Markdown" where the references are stored
        by actual object ids.

        The upshot of translating this to a neutral format that has no
        concept of the workflow invocation is that client side rendering (and much of the backend
        processing) is completely general and not tied to workflows or workflow invocations.
        The same markdown component could potentially be used to render pages, history annotations,
        libraries, etc..
    - type: inputs
    - type: outputs
    - type: workflow
    - type: free_markdown
      title: Custom Section Example
      content: |
        This is a my **custom** content, I defined this section with free Markdown.

        If I want to reference an output and embed, I can do it as follows:

        ```
        ::: history_dataset_display output=output_1
        :::
        ```

        ::: history_dataset_display output=output_1
        :::

        If I want to reference an input, I can do that *also* as follows:

        ```
        ::: history_dataset_display input=input_1
        :::
        ```

        ::: history_dataset_display input=input_1
        :::

        I can embed an output (or input) directly into the report as an image as follows:

        ```
        ::: history_dataset_as_image output=output_image
        :::
        ```

        ::: history_dataset_as_image output=output_image
        :::

        ---

        I can also embed just a dataset peek:

        ```
        ::: history_dataset_peek output=output_1
        :::
        ```

        ::: history_dataset_peek output=output_1
        :::

        ---

        Or a dataset "info" content:

        ```
        ::: history_dataset_info input=input_1
        :::
        ```

        ::: history_dataset_info input=input_1
        :::

        ---

        Collections can also be displayed:

        ```
        ::: history_dataset_collection_display input=input_list
        :::
        ```

        ::: history_dataset_collection_display input=input_list
        :::

        ---

        I can actually embed the whole workflow, which looks like this:

        ```
        ::: workflow_display
        :::
        ```

        ::: workflow_display
        :::

        ---

        Job parameters can be summarized:

        ```
        ::: job_parameters step=qc_step
        :::
        ```

        ::: job_parameters step=qc_step
        :::

        ---

        Job metrics can be summarized as well:

        ```
        ::: job_metrics step=image_cat
        :::
        ```

        ::: job_metrics step=image_cat
        :::

        ---

        Tool standard out and error are also available for steps.

        ```
        ::: tool_stdout step=qc_step
        :::
        ```

        ::: tool_stdout step=qc_step
        :::

        ```
        ::: tool_stderr step=qc_step
        :::
        ```

        ::: tool_stderr step=qc_step
        :::

        ---

        There is some content down here. *fin*

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
  type: list
  elements:
    - identifier: i1
      content: "0"
  name: example list
"""
