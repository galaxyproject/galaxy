#!/usr/bin/env cwl-runner

class: ExpressionTool
requirements:
  - class: InlineJavascriptRequirement
cwlVersion: v1.2

inputs:
  parameter:
    type: boolean?

outputs:
  output: boolean?

expression: "$({'output': inputs.parameter})"
