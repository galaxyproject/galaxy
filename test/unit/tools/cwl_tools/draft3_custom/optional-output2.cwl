#!/usr/bin/env cwl-runner
class: CommandLineTool
cwlVersion: "cwl:draft-3"
description: "Print the contents of a file to stdout using 'cat' running in a docker container."
hints:
  - class: DockerRequirement
    dockerPull: debian:wheezy
inputs:
  - id: optionaloutput.py
    type: File
    default:
      class: File
      path: optionaloutput.py
    inputBinding:
      position: 0
  - id: produce
    type: string
    inputBinding:
      position: 1
outputs:
  - id: optional_file
    type: ["null", File]
    outputBinding:
      glob: bumble.txt
baseCommand: python
