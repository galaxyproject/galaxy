#!/usr/bin/env cwl-runner
cwlVersion: "v1.0"
class: CommandLineTool
requirements:
  InitialWorkDirRequirement:
    listing:
    - entryname: input.txt
      entry: $(inputs.file)
inputs:
  file: File
  index.py:
    type: File
    default:
      class: File
      path: index.py
    inputBinding:
      position: 0
baseCommand: python
arguments:
- valueFrom: input.txt
  position: 1
outputs:
  result:
    type: File
    secondaryFiles:
    - ".idx1"
    outputBinding:
      glob: input.txt
