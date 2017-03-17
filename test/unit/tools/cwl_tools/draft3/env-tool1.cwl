class: CommandLineTool
cwlVersion: cwl:draft-3
inputs:
  - { id: in, type: string }
outputs:
  - id: out
    type: File
    outputBinding:
      glob: out

requirements:
  - class: EnvVarRequirement
    envDef:
      - envName: TEST_ENV
        envValue: $(inputs.in)

baseCommand: ["/bin/bash", "-c", "echo $TEST_ENV"]

stdout: out
