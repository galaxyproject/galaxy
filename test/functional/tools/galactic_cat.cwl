#!/usr/bin/env cwl-runner
$namespaces:
  gx: "http://galaxyproject.org/cwl#"
cwlVersion: v1.0
class: CommandLineTool
id: "galactic_cat"
gx:version: '1.2'
doc: |
  Galactic Cat.
inputs:
  - id: input1
    type: File
    inputBinding:
      position: 1
outputs:
  - id: output1
    type: File
    outputBinding:
      glob: out
baseCommand: ["cat"]
arguments: []
stdout: out
hints:
  gx:interface:
    gx:inputs:
      - gx:name: input1
        gx:type: data
        gx:format: 'txt'
    gx:outputs:
      output1:
        gx:format: 'txt'
