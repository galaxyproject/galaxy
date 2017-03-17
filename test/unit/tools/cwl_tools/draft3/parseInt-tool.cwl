#!/usr/bin/env cwl-runner

class: ExpressionTool
requirements:
  - class: InlineJavascriptRequirement
cwlVersion: cwl:draft-3

inputs:
  - { id: file1, type: File, inputBinding: { loadContents: true } }

outputs:
  - { id: output, type: int }

expression: "$({'output': parseInt(inputs.file1.contents)})"
