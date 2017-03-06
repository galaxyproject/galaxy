class: CommandLineTool
cwlVersion: "cwl:draft-3"
baseCommand: python
arguments:
  - valueFrom: input.txt
    position: 1
requirements:
  - class: CreateFileRequirement
    fileDef:
      - filename: input.txt
        fileContent: $(inputs.file)
inputs:
  - id: file
    type: File
  - id: index.py
    type: File
    default:
      class: File
      path: index.py
    inputBinding:
      position: 0
outputs:
  - id: result
    type: File
    outputBinding:
      glob: input.txt
    secondaryFiles:
      - ".idx1"
