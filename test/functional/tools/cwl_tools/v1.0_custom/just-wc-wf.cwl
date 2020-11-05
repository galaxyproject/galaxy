#!/usr/bin/env cwl-runner
class: Workflow
cwlVersion: v1.0

inputs:
  file1:
    type: File

outputs:
  count_output:
    type: File
    outputSource: step1/wc_output

steps:
  step1:
    in:
      wc_file1: file1
    out: [wc_output]
    run:
      id: wc
      class: CommandLineTool
      inputs:
        wc_file1:
          type: File
          inputBinding: {}
      outputs:
        wc_output:
          type: File
          outputBinding:
            glob: output.txt
      stdout: output.txt
      baseCommand: wc
