#!/usr/bin/env cwl-runner
class: CommandLineTool
cwlVersion: "cwl:draft-3"
requirements:
 - class: SubworkflowFeatureRequirement

inputs:
  - id: bar
    type: Any

outputs:
  - id: t1
    type: Any
    outputBinding:
      outputEval: $(inputs.bar)

baseCommand: "true"
