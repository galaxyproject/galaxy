#!/usr/bin/env cwl-runner

class: ExpressionTool
requirements:
  - class: InlineJavascriptRequirement
cwlVersion: v1.2

inputs:
  parameter:
    type: float?

outputs:
  output: float?

expression: "$({'output': inputs.parameter})"
