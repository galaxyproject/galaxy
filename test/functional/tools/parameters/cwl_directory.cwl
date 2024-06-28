#!/usr/bin/env cwl-runner

class: ExpressionTool
requirements:
  - class: InlineJavascriptRequirement
cwlVersion: v1.2

inputs:
  parameter:
    type: Directory

outputs:
  output: Directory

expression: "$({'output': inputs.parameter})"
