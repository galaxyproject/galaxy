#!/usr/bin/env cwl-runner
cwlVersion: "v1.0"
class: CommandLineTool
doc: "Print the contents of a file to stdout using 'cat' running in a docker container."
hints:
  DockerRequirement:
    dockerPull: debian:wheezy
inputs:
  file1:
    label: Input File
    doc: "The file that will be copied using 'cat'"
    type: File
    default:
      class: File
      path: hello.txt
    inputBinding: {position: 1}
baseCommand: cat
stdout: output.txt
outputs:
  output_file:
    type: File
    outputBinding: {glob: output.txt}
