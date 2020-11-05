#!/usr/bin/env cwl-runner
cwlVersion: "v1.0"
class: CommandLineTool
inputs:
  file:
    type: File
    secondaryFiles:
    - ".idx1"
    inputBinding:
      position: 1
  showindex.py:
    type: File
    default:
      class: File
      path: showindex.py
    inputBinding:
      position: 0
baseCommand: python
stdout: output.txt
outputs:
  output_txt:
    type: File
    outputBinding:
      glob: output.txt
