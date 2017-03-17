#!/usr/bin/env cwl-runner
class: CommandLineTool
cwlVersion: "cwl:draft-345"

inputs:
  - id: bar
    type: Any

outputs:
  - id: t1
    type: Any
    outputBinding:
      outputEval: $(inputs.bar)

baseCommand: "true"
