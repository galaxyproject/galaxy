

WORKFLOW_SIMPLE_CAT_AND_RANDOM_LINES = """
class: GalaxyWorkflow
doc: |
  Simple workflow that no-op cats a file and then selects 10 random lines.
inputs:
  - id: the_input
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
  - tool_id: cat
    label: first_cat
    in:
      input1: input1
      queries_0|input2: input1
"""


WORKFLOW_WITH_OLD_TOOL_VERSION = """
class: GalaxyWorkflow
inputs:
  input1: data
steps:
  - tool_id: multiple_versions
    tool_version: "0.0.1"
    state:
      inttest: 8
"""


WORKFLOW_WITH_INVALID_STATE = """
class: GalaxyWorkflow
inputs:
  input1: data
steps:
  - tool_id: multiple_versions
    tool_version: "0.0.1"
    state:
      inttest: "moocow"
"""


WORKFLOW_WITH_OUTPUT_COLLECTION = """
class: GalaxyWorkflow
inputs:
  text_input: data
steps:
  - label: split_up
    tool_id: collection_creates_pair
    in:
      input1: text_input
  - tool_id: collection_paired_test
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
steps:
  - label: text_input1
    type: input
  - label: text_input2
    type: input
  - label: cat_inputs
    tool_id: cat1
    state:
      input1:
        $link: text_input1
      queries:
        - input2:
            $link: text_input2
  - label: split_up
    tool_id: collection_split_on_column
    state:
      input1:
        $link: cat_inputs#out_file1
  - tool_id: cat_list
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
  - tool_id: cat
    label: cat
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
  - label: apply
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
  - tool_id: random_lines1
    label: random_lines
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
  - label: apply
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
  - tool_id: collection_creates_list
    label: copy_list
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
  - tool_id: cat1
    label: first_cat
    in:
      input1: outer_input
  - run:
      class: GalaxyWorkflow
      inputs:
        inner_input: data
      outputs:
        workflow_output:
          outputSource: random_lines/out_file1
      steps:
        - tool_id: random_lines1
          label: random_lines
          state:
            num_lines: 1
            input:
              $link: inner_input
            seed_source:
              seed_source_selector: set_seed
              seed: asdf
    label: nested_workflow
    in:
      inner_input: first_cat/out_file1
  - tool_id: cat1
    label: second_cat
    state:
      input1:
        $link: nested_workflow#workflow_output
      queries:
        - input2:
            $link: nested_workflow#workflow_output
"""


WORKFLOW_NESTED_RUNTIME_PARAMETER = """
class: GalaxyWorkflow
inputs:
  outer_input: data
outputs:
  outer_output:
    outputSource: nested_workflow/workflow_output
steps:
  - run:
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
    label: nested_workflow
    in:
      inner_input: outer_input
"""


WORKFLOW_WITH_OUTPUT_ACTIONS = """
class: GalaxyWorkflow
inputs:
  input1: data
steps:
  - tool_id: cat1
    label: first_cat
    outputs:
       out_file1:
         hide: true
         rename: "the new value"
    in:
      input1: input1
  - tool_id: cat1
    in:
      input1: first_cat/out_file1
"""


WORKFLOW_RUNTIME_PARAMETER_SIMPLE = """
class: GalaxyWorkflow
inputs:
  input1: data
steps:
  - tool_id: random_lines1
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
  - label: the_pause
    type: pause
    in:
      input: input1
  - tool_id: random_lines1
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
  - tool_id: cat
    label: first_cat
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
  - tool_id: cat
    label: first_cat
    state:
      input1:
        $link: input1
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
  - run:
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
    label: nested_workflow
    in:
      inner_input: outer_input
"""

WORKFLOW_WITH_OUTPUTS = """
class: GalaxyWorkflow
inputs:
  input1: data
outputs:
  wf_output_1:
    outputSource: first_cat/out_file1
steps:
  - tool_id: cat1
    label: first_cat
    state:
      input1:
        $link: input1
      queries:
        - input2:
            $link: input1
"""
