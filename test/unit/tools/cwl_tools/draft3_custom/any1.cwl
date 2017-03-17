#!/usr/bin/env cwl-runner
class: CommandLineTool

inputs:
  - id: bar
    type: Any

outputs:
  - id: t1
    type: Any
    outputBinding:
      outputEval: $(inputs.bar)

baseCommand: "true"
