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
outputs: []
baseCommand: cat
stdin: $(inputs.file1.path)
