#!/usr/bin/env cwl-runner
cwlVersion: v1.0
class: CommandLineTool
doc: "Print the contents of a file to stdout using 'cat' running in a docker container."
hints:
  DockerRequirement:
    dockerPull: debian:wheezy
inputs:
  file1:
    type: File
    inputBinding: {position: 1}
  numbering:
    type: boolean?
    inputBinding:
      position: 0
      prefix: -n
baseCommand: cat
outputs: {}
