class: CommandLineTool
cwlVersion: "cwl:draft-3"
baseCommand: python
stdout: output.txt
inputs:
  - id: file
    type: File
    inputBinding:
      position: 1
    secondaryFiles:
      - ".idx1"
  - id: showindex.py
    type: File
    default:
      class: File
      path: showindex.py
    inputBinding:
      position: 0
outputs:
  - id: output_txt
    type: File
    outputBinding:
      glob: output.txt
