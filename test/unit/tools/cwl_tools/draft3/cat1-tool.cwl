#!/usr/bin/env cwl-runner
cwlVersion: cwl:draft-3
class: CommandLineTool
description: "Print the contents of a file to stdout using 'cat' running in a docker container."
hints:
  - class: DockerRequirement
    dockerPull: debian:wheezy
inputs:
  - id: file1
    type: File
    inputBinding: {position: 1}
  - id: numbering
    type: ["null", boolean]
    inputBinding:
      position: 0
      prefix: -n
outputs: []
baseCommand: cat
