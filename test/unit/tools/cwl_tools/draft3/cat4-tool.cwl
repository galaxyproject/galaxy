#!/usr/bin/env cwl-runner
class: CommandLineTool
cwlVersion: cwl:draft-3
description: "Print the contents of a file to stdout using 'cat' running in a docker container."
hints:
  - class: DockerRequirement
    dockerPull: debian:wheezy
inputs:
  - id: file1
    type: File
outputs:
  - id: output_txt
    type: File
    outputBinding:
      glob: output.txt
baseCommand: cat
stdout: output.txt
stdin: $(inputs.file1.path)
