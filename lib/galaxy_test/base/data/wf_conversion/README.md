# Workflow Conversion Artifact Test Data

This directory contains native .ga workflows whose tool_state has representation
artifacts from schema-unaware gxformat2 format2→native conversion. The API tests
in `test/api/test_wf_conversion_artifacts.py` verify Galaxy executes these
workflows correctly despite the non-standard encoding.

## What's being tested

When gxformat2's `python_to_workflow()` converts a format2 workflow to native
.ga format without access to tool definitions, certain parameter values get
encoded differently than Galaxy's own serialization would produce:

| Artifact                | Native (Galaxy)                           | After gxformat2 conversion              |
| ----------------------- | ----------------------------------------- | --------------------------------------- |
| Multiple select         | `"--ex1"` (comma-delimited string)        | `["--ex1"]` (JSON list)                 |
| All-None section        | `{"param": null, ...}` (section present)  | absent (section omitted)                |
| Empty repeat            | `[]` (empty list)                         | absent (key omitted)                    |
| Boolean                 | `"True"` / `"False"` (capitalized string) | `true` / `false` (JSON boolean)         |
| Connection-only section | section state for connected data param    | absent section plus `input_connections` |

## How the .ga files were generated

1. Human-authored format2 workflows live in `format2/`
2. Each was converted to native format using:
   ```python
   from gxformat2.converter import python_to_workflow
   from gxformat2.yaml import ordered_load
   native = python_to_workflow(ordered_load(open(f2_path)), galaxy_interface=None)
   ```
3. The resulting .ga files were inspected to verify artifacts are present
4. Both the format2 source and .ga output are committed when a format2 source exists

The `empty_repeat_optional.ga` fixture currently has no companion format2 source.
It is kept as a native snapshot for the `gx_repeat_optional` safe-template coverage.

## How to add a new test workflow

1. Write a minimal format2 workflow in `format2/` exercising the artifact
2. Convert it:
   ```python
   from gxformat2.converter import python_to_workflow
   from gxformat2.yaml import ordered_load
   import json
   with open("format2/your_workflow.gxwf.yml") as f:
       f2 = ordered_load(f)
   native = python_to_workflow(f2, galaxy_interface=None)
   with open("your_workflow.ga", "w") as f:
       json.dump(native, f, indent=4)
   ```
3. Inspect the .ga to confirm the expected artifact is present in tool_state
4. Add a test method in `test/api/test_wf_conversion_artifacts.py`
5. Commit both the format2 source and .ga file unless documenting a native-only fixture

## Important

The .ga files are frozen snapshots — do not regenerate them automatically.
They represent what the old schema-unaware conversion produces. Even as the
converter improves, these tests continue to verify Galaxy handles legacy
artifacts.
