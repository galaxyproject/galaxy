class: CommandLineTool
cwlVersion: cwl:draft-3
baseCommand: "true"
requirements:
  - class: CreateFileRequirement
    fileDef:
      - filename: $(inputs.newname)
        fileContent: $(inputs.srcfile)
inputs:
  - id: srcfile
    type: File
  - id: newname
    type: string
outputs:
  - id: outfile
    type: File
    outputBinding:
      glob: $(inputs.newname)
