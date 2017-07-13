
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
