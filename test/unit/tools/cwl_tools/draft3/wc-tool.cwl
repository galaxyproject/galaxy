#!/usr/bin/env cwl-runner

class: CommandLineTool
cwlVersion: cwl:draft-3

inputs:
  - { id: file1, type: File }

"outputs":
  - { id: output, type: File,  outputBinding: { glob: output } }

baseCommand: [wc]

stdin: $(inputs.file1.path)
stdout: output
