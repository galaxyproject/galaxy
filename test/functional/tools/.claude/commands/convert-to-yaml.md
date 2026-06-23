# Convert XML Tool to YAML

Convert an XML test tool to YAML format (GalaxyUserTool).

## Arguments

The command accepts either:
- A filename (e.g., `collection_creates_pair.xml`)
- A tool ID (e.g., `collection_creates_pair`)

## Task Steps

### 1. Find and Read the XML Tool

- If given a filename, read that file
- If given a tool ID, search for `<tool id="{tool_id}"` in XML files in this directory and subdirectories
- Read the XML tool file completely

### 2. Create YAML Tool File

- Parse the XML tool to extract:
  - Tool ID, name, version, description
  - Command section (needs Cheetah to JavaScript conversion)
  - Inputs
  - Outputs
  - Tests (if present)
  - Container/requirements (if present)

- Create new YAML file with:
  - Filename: `{original_id}_user.yml` (e.g., `collection_creates_pair_user.yml`)
  - `class: GalaxyUserTool`
  - `id: {original_id}_user` (e.g., `collection_creates_pair_user`)
  - Convert other fields to YAML format

### 3. Convert Cheetah Command to JavaScript Shell Command

The XML `<command>` section uses Cheetah templating. Convert to JavaScript for `shell_command:`:

**Common Cheetah to JavaScript conversions:**

| Cheetah (XML) | JavaScript (YAML) |
|---------------|-------------------|
| `$input1` | `$(inputs.input1.path)` |
| `${input1}` | `$(inputs.input1.path)` |
| `$output1` | Hard-code output filename (e.g., `output.txt`) and use `from_work_dir` in outputs |
| `#for $item in $repeat#...#end for#` | `$(inputs.repeat.map((item) => ...).join(' '))` |
| `#if $condition#...#end if#` | `$(inputs.condition ? ... : ...)` |
| String concatenation | Use JavaScript template literals |
| `str($param)` | `$(inputs.param)` |
| `$param.value` | `$(inputs.param)` (in YAML, just reference the value directly) |

**Example conversions:**

XML:
```xml
<command>cat '$input1' > '$output1'</command>
```

YAML:
```yaml
shell_command: cat '$(inputs.input1.path)' > output.txt
```

XML:
```xml
<command>
#for $q in $queries#
  cat '${q.input2}' >> output.txt
#end for#
</command>
```

YAML:
```yaml
shell_command: |
  $(inputs.queries.map((q) => `cat '${q.input2.path}'`).join(' && '))
```

### 4. Convert Inputs

Map XML input parameters to YAML format:

**Data inputs:**
```xml
<param name="input1" type="data" format="txt" label="Input" />
```
→
```yaml
- name: input1
  type: data
  format: txt
```

**Other parameter types:**
```xml
<param name="param1" type="integer" value="5" />
```
→
```yaml
- name: param1
  type: integer
  value: 5
```

**Multiple/optional:**
```xml
<param name="input1" type="data" multiple="true" optional="true" />
```
→
```yaml
- name: input1
  type: data
  multiple: true
  optional: true
```

### 5. Convert Outputs

Map XML outputs to YAML:

**Simple output:**
```xml
<data name="output1" format="txt" />
```
→
```yaml
- name: output1
  type: data
  format: txt
  from_work_dir: output.txt
```

**Output with format_source:**
```xml
<data name="output1" format_source="input1" />
```
→
```yaml
- name: output1
  type: data
  format_source: input1
  from_work_dir: output.txt
```

**Collections:**
```xml
<collection name="paired_output" type="paired">
  <data name="forward" format="txt" />
  <data name="reverse" format_source="input1" from_work_dir="reverse.txt" />
</collection>
```
→
```yaml
- name: paired_output
  type: collection
  collection_type: paired
  outputs:
    - name: forward
      type: data
      format: txt
      from_work_dir: forward.txt
    - name: reverse
      type: data
      format_source: input1
      from_work_dir: reverse.txt
```

### 6. Convert Tests

Map XML test cases to YAML:

**XML:**
```xml
<test>
  <param name="input1" value="simple_line.txt" />
  <output name="output1" file="expected_output.txt" />
</test>
```

**YAML:**
```yaml
- inputs:
    input1:
      class: File
      path: simple_line.txt
  outputs:
    output1: expected_output.txt
```

**With assertions:**
```xml
<test>
  <param name="input1" value="simple_line.txt" />
  <output name="output1">
    <assert_contents>
      <has_line line="expected text" />
      <has_text_matching expression="pattern" />
    </assert_contents>
  </output>
</test>
```

**YAML:**
```yaml
- inputs:
    input1:
      class: File
      path: simple_line.txt
  outputs:
    output1:
      asserts:
        - has_line:
            line: expected text
        - has_text_matching:
            expression: pattern
```

### 7. Update parameter_specification.yml

Read `test/unit/tool_util/parameter_specification.yml`:

- Search for the original tool ID (e.g., `gx_boolean:`)
- If found, clone that entire section
- Create a new section with the new tool ID (e.g., `gx_boolean_user:`)
- Keep all the test specifications the same (they should work for both XML and YAML versions)

**Example:**
If the file has:
```yaml
gx_boolean:
  request_valid:
    - parameter: True
    - parameter: False
```

Add:
```yaml
gx_boolean_user:
  request_valid:
    - parameter: True
    - parameter: False
```

**Run parameter specification tests:**
After updating parameter_specification.yml, run the tests to verify the new tool ID works correctly:

```bash
cd /path/to/galaxy
source .venv/bin/activate
pytest test/unit/tool_util/test_parameter_specification.py
```

This will run all parameter specification tests, including the new tool ID (e.g., `gx_boolean_user`). If successful, the YAML tool properly implements the same parameter validation as the XML version.

### 8. Check and Update test_tool_execute.py

Read `lib/galaxy_test/api/test_tool_execute.py`:

- Search for references to the original tool ID using `@requires_tool_id("{original_id}")`
- If found, create corresponding test functions for the new tool ID
- Clone each test function that references the original tool
- Update the decorator to `@requires_tool_id("{original_id}_user")`
- Update the function name to include `_user` suffix
- Keep the test logic identical

**Example:**
```python
@requires_tool_id("collection_creates_pair")
def test_collection_creates_pair(required_tool: RequiredTool):
    # test implementation
```

Add:
```python
@requires_tool_id("collection_creates_pair_user")
def test_collection_creates_pair_user(required_tool: RequiredTool):
    # same test implementation
```

### 9. Add to sample_tool_conf.xml

Read `test/functional/tools/sample_tool_conf.xml`:

- Find the entry for the original XML tool
- Add a new entry immediately after it for the YAML tool
- Format: `<tool file="{path_to_yaml_tool}" />`
- Path is relative to `test/functional/tools/`

**Example:**
If the file has:
```xml
<tool file="collection_creates_pair.xml" />
```

Add after it:
```xml
<tool file="collection_creates_pair.xml" />
<tool file="collection_creates_pair_user.yml" />
```

For tools in subdirectories (e.g., `parameters/gx_boolean.xml`):
```xml
<tool file="parameters/gx_boolean.xml" />
<tool file="parameters/gx_boolean_user.yml" />
```

## Output

After completion, report:
1. Path to the new YAML file created
2. Whether parameter_specification.yml was updated (and what section)
3. Whether test_tool_execute.py had tests (and how many were added)
4. Confirmation that sample_tool_conf.xml was updated
5. Any conversion challenges or notes about the Cheetah → JavaScript conversion

## Validation

After creating the YAML tool, validate it:
```bash
sh scripts/validate_tools.sh test/functional/tools/{new_yaml_file}
```

Note: XML validation works with validate_tools.sh, but YAML validation uses the YAML parser. Check for parsing errors.

## Edge Cases

- **No tests in XML**: Don't create a tests section in YAML
- **Complex Cheetah logic**: Document if the conversion requires manual review
- **Collections in outputs**: Carefully map collection structure
- **Conditional parameters**: May need special handling in shell_command
- **Multiple outputs**: Ensure all outputs have unique from_work_dir values
- **Requirements/containers**: Convert `<requirements>` to `container:` or `requirements:` in YAML
