#!/usr/bin/env cwl-runner
cwlVersion: "v1.0"
class: CommandLineTool
doc: "Print the contents of a file to stdout using 'cat' running in a docker container."
hints:
  DockerRequirement:
    dockerPull: docker.io/python:3-slim
inputs:
  optionaloutput.py:
    type: File
    default:
      class: File
      path: optionaloutput.py
    inputBinding:
      position: 0
  produce:
    type: string
    inputBinding:
      position: 1
baseCommand: python3
outputs:
  optional_file:
    type: File?
    outputBinding:
      glob: bumble.txt
