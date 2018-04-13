
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
