
WORKFLOW_SIMPLE_CAT_TWICE = """
class: GalaxyWorkflow
inputs:
  - id: input1
steps:
  - tool_id: cat
    label: first_cat
    state:
      input1:
        $link: input1
      queries:
        - input2:
            $link: input1
"""


WORKFLOW_WITH_OLD_TOOL_VERSION = """
class: GalaxyWorkflow
inputs:
  - id: input1
steps:
  - tool_id: multiple_versions
    tool_version: "0.0.1"
    state:
      inttest: 8
"""


WORKFLOW_WITH_INVALID_STATE = """
class: GalaxyWorkflow
inputs:
  - id: input1
steps:
  - tool_id: multiple_versions
    tool_version: "0.0.1"
    state:
      inttest: "moocow"
"""


WORKFLOW_WITH_OUTPUT_COLLECTION = """
class: GalaxyWorkflow
steps:
  - label: text_input
    type: input
  - label: split_up
    tool_id: collection_creates_pair
    state:
      input1:
        $link: text_input
  - tool_id: collection_paired_test
    state:
      f1:
        $link: split_up#paired_output
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
    state:
      input1:
        $link: split_up#split_output
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
  - id: input1
    type: data_collection_input
    collection_type: list
steps:
  - tool_id: cat
    label: cat
    state:
      input1:
        $link: input1
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
  - type: collection
    label: input_c
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
  - type: collection
    label: input_c
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
    state:
      input1:
        $link: apply#output
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
  - id: outer_input
outputs:
  - id: outer_output
    source: second_cat#out_file1
steps:
  - tool_id: cat1
    label: first_cat
    state:
      input1:
        $link: outer_input
  - run:
      class: GalaxyWorkflow
      inputs:
        - id: inner_input
      outputs:
        - id: workflow_output
          source: random_lines#out_file1
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
    connect:
      inner_input: first_cat#out_file1
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
  - id: outer_input
outputs:
  - id: outer_output
    source: nested_workflow#workflow_output
steps:
  - run:
      class: GalaxyWorkflow
      inputs:
        - id: inner_input
      outputs:
        - id: workflow_output
          source: random_lines#out_file1
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
    connect:
      inner_input: outer_input
"""


WORKFLOW_RUNTIME_PARAMETER_SIMPLE = """
class: GalaxyWorkflow
inputs:
  - id: input1
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
