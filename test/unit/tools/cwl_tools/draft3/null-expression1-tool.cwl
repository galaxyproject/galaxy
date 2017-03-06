#!/usr/bin/env cwl-runner

class: ExpressionTool
requirements:
  - class: InlineJavascriptRequirement
cwlVersion: cwl:draft-3

inputs:
  - { id: i1, type: Any, default: "the-default" }

outputs:
  - { id: output, type: int }

expression: "$({'output': (inputs.i1 == 'the-default' ? 1 : 2)})"