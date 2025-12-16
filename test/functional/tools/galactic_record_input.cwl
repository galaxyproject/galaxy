#!/usr/bin/env cwl-runner
$namespaces:
  gx: "http://galaxyproject.org/cwl#"
class: CommandLineTool
cwlVersion: v1.0
requirements:
  - class: ShellCommandRequirement
id: galactic_record_input
gx:version: '1.2'
inputs:
  irec:
    type:
      name: irec
      type: record
      fields:
      - name: ifoo
        type: File
        inputBinding:
          position: 2
      - name: ibar
        type: File
        inputBinding:
          position: 6

outputs:
  - id: ofoo
    type: File
    outputBinding:
      glob: foo
  - id: obar
    type: File
    outputBinding:
      glob: bar

arguments:
  - {valueFrom: "cat", position: 1}
  - {valueFrom: "> foo", position: 3, shellQuote: false}
  - {valueFrom: "&&", position: 4, shellQuote: false}
  - {valueFrom: "cat", position: 5}
  - {valueFrom: "> bar", position: 7, shellQuote: false}

hints:
  gx:interface:
    gx:inputs:
      - gx:name: input1
        gx:type: data
        gx:format: 'txt'
        gx:mapTo: 'irec/ifoo'
      - gx:name: input2
        gx:type: data
        gx:format: 'txt'
        gx:mapTo: 'irec/ibar'
    gx:outputs:
      ofoo:
        gx:format: 'txt'
      obar:
        gx:format: 'txt'
