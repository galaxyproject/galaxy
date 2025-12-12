# Galaxy Test Tools Directory

This directory contains test tools for the Galaxy project. These tools are installed into dev and test environments to test features of the workflow and tool subsystems of the Galaxy backend.

## Overview

Test tools in this directory are used to validate:
- Tool parsing and loading
- Input parameter specifications and validation
- Output handling and collections
- Workflow integration
- Tool state modeling
- Test definition parsing

## Directory Structure

```
test/functional/tools/
├── parameters/          # Tools for testing input parameter patterns
├── for_workflows/       # Simple building blocks for workflow testing (not tool testing)
├── cwl_tools/          # CWL (Common Workflow Language) related tools
├── data/               # Test data files
├── deprecated/         # Deprecated test tools
├── for_tours/          # Tools for Galaxy tour testing
└── realtime/           # Real-time/interactive tool tests
```

### Directory Conventions

- **parameters/**: Contains tools specifically designed to test various input parameter types and patterns (e.g., `gx_boolean.xml`, `gx_conditional_boolean_checked.xml`)
- **for_workflows/**: Contains simple building block tools for workflow testing (e.g., `cat.xml`, `head.xml`). These are NOT for tool subsystem testing.
- **Root directory**: General tool testing tools for various features

## File Formats

### XML Format (Legacy)

Most test tools are Galaxy Tool XML files with a root `<tool>` tag.

**Example structure:**
```xml
<tool id="collection_creates_pair" name="collection_creates_pair" version="0.1.0">
  <command>
    sed 'n;d' $input1 > $forward ;
    sed -n 'g;n;p' $input1 > "reverse.txt";
  </command>
  <inputs>
    <param name="input1" type="data" label="Input" />
  </inputs>
  <outputs>
    <collection name="paired_output" type="paired">
      <data name="forward" format="txt" />
      <data name="reverse" format_source="input1" from_work_dir="reverse.txt" />
    </collection>
  </outputs>
  <tests>
    <test>
      <param name="input1" value="simple_lines_interleaved.txt" />
      <output_collection name="paired_output" type="paired">
        <element name="forward">
          <assert_contents>
            <has_text_matching expression="^This is a line of text.\n$" />
          </assert_contents>
        </element>
      </output_collection>
    </test>
  </tests>
</tool>
```

**Key documentation:**
- XML Schema: `lib/galaxy/tool_util/xsd/galaxy.xsd`
- Parser: `lib/galaxy/tool_util/parser/xml.py` (produces ToolSource objects)

### YAML Format (Newer)

YAML tools have `.yml` extension and contain `class: GalaxyUserTool` or `class: GalaxyTool` as root attributes.

**Example structure:**
```yaml
class: GalaxyUserTool
id: cat_user_defined
version: "0.1"
name: cat_user_defined
description: concatenates a file
container: busybox
shell_command: cat '$(inputs.input1.path)' > output.txt
inputs:
  - name: input1
    type: data
    format: txt
outputs:
  - name: output1
    type: data
    format: txt
    from_work_dir: output.txt
tests:
  - inputs:
      input1:
        class: File
        path: simple_line.txt
    outputs:
      output1: simple_line.txt
```

**Key documentation:**
- Parser: `lib/galaxy/tool_util/parser/yaml.py`

## Test Tool Conventions

1. **No help sections**: Test tools typically don't contain help documentation
2. **Filename matches tool ID**: The filename should match the tool ID defined in the tool
3. **Test cases are optional**: Not all test tools need test cases defined within them
   - Some tools are used for lower-level API testing in `lib/galaxy_test/api/test_tool_execute.py`
   - Parameter specification tools may only be used for model validation tests
   - Tests are expensive to run - only include when testing something specific

## Available Slash Commands

This directory includes custom Claude Code slash commands to help with common tasks:

- **`/convert-to-yaml <tool_id_or_filename>`**: Convert an XML test tool to YAML format with automatic updates to all related test files

## Common Tasks

### Creating a New Test Tool

1. Determine the appropriate directory:
   - Use root directory for general tool feature testing
   - Use `parameters/` for input parameter pattern testing
   - Use `for_workflows/` only for workflow building blocks

2. Choose format (XML or YAML) - either is acceptable

3. Follow naming conventions:
   - Filename should match tool ID
   - Use descriptive, snake_case names

4. Decide if test cases are needed:
   - Include tests if validating tool execution behavior
   - Omit tests if only testing parsing, API structure, or parameter modeling

5. Add the tool to `sample_tool_conf.xml`:
   - Add an entry: `<tool file="path/to/your_tool.xml" />`
   - Path is relative to `test/functional/tools/`
   - For subdirectories: `<tool file="parameters/your_tool.xml" />`

6. Validate the tool (see Validation section)

### Converting XML Tool to YAML

Use the `/convert-to-yaml` slash command to convert an existing XML test tool to YAML format:

```
/convert-to-yaml collection_creates_pair
```

or

```
/convert-to-yaml collection_creates_pair.xml
```

**What this does:**
- Creates a new YAML tool file with `_user` suffix (e.g., `collection_creates_pair_user.yml`)
- Converts Cheetah templating to JavaScript shell_command syntax
- Converts inputs, outputs, and tests to YAML format
- Updates `parameter_specification.yml` if the original tool has test specifications
- Updates `test_tool_execute.py` if the original tool has API tests
- Adds the new tool to `sample_tool_conf.xml`

This is useful for creating parallel YAML versions of XML tools to ensure both formats work correctly.

### Running Tool Tests

To run tests for a specific tool:

```bash
GALAXY_SKIP_CLIENT_BUILD=1 GALAXY_CONFIG_OVERRIDE_CONDA_AUTO_INIT=false ./run_tests.sh -framework -id <tool_id>
```

Where `<tool_id>` is the ID defined in the tool file.

**Note**: This runs the tests defined within the tool file itself.

## Testing Approaches

### 1. Tool Execution Tests (Framework Tests)

Tests defined within tool files are run via the framework test system. These validate:
- Correct tool execution
- Output generation and validation
- Collection handling
- Test assertions

### 2. Unit Tests

Located in `test/unit/tool_util/`, these test various parsing and modeling aspects:

#### Key Unit Test Files

- **`test_parsing.py`**: Tests basic tool parsing from XML/YAML
- **`test_test_definition_parsing.py`**: Tests how Galaxy generates test descriptions for the API to run tests defined in tool files
- **`test_parameter_specification.py`**: Tests dynamic Pydantic models for reasoning about tool state
- **`test_parameter_test_cases.py`**: Additional parameter test case validation

#### When to Use Each Approach

| Test Type | Use Case | Location |
|-----------|----------|----------|
| In-tool tests | Validate tool execution, outputs, collections | Tool file's `<tests>` section |
| API tests | Test exact JSON syntax for Galaxy API tool execution | `lib/galaxy_test/api/test_tool_execute.py` |
| Unit tests | Test parsing, parameter modeling, test definition generation | `test/unit/tool_util/` |

**Cost consideration**: Framework tests are expensive to run. For parsing, API structure, or model validation, use unit tests or API tests instead.

## Validation

### Linting All Test Tools

Run in CI with tox:

```bash
tox -e validate_test_tools
```

**Note**: This validation is expensive as it checks all test tools in the directory.

### Validating a Single Tool

To validate an individual tool (much faster than validating all tools), run from the Galaxy root directory:

```bash
sh scripts/validate_tools.sh test/functional/tools/your_tool.xml
```

Or for multiple specific tools:

```bash
sh scripts/validate_tools.sh test/functional/tools/tool1.xml test/functional/tools/tool2.xml
```

**What this does:**
- Loads the tool using the Galaxy tool loader
- Validates the XML structure against the Galaxy XSD schema (`lib/galaxy/tool_util/xsd/galaxy.xsd`)
- Reports any schema validation errors

**Example output:**
```
test/functional/tools/your_tool.xml
ok 1
```

Or if there are validation errors:
```
test/functional/tools/your_tool.xml
not ok 1 test/functional/tools/your_tool.xml
    [error details from xmllint]
```

**Note**: This validation currently works for XML tools. YAML tools use a different validation approach through the YAML parser.

### Validating YAML Tools with Galaxy Parser

To validate YAML tools programmatically using the Galaxy parser (useful for confirming tools are properly structured):

```bash
cd /path/to/galaxy
source .venv/bin/activate
PYTHONPATH=lib:$PYTHONPATH python -c "
from galaxy.tool_util.parser.factory import get_tool_source

tool_path = 'test/functional/tools/parameters/your_tool.yml'
tool_source = get_tool_source(tool_path)
print(f'Tool ID: {tool_source.parse_id()}')
print(f'Name: {tool_source.parse_name()}')
print(f'Version: {tool_source.parse_version()}')
"
```

**Important**: When running Galaxy Python code:
1. **Activate the virtual environment**: `source .venv/bin/activate` (from Galaxy root)
2. **Set PYTHONPATH**: `PYTHONPATH=lib:$PYTHONPATH` to ensure Galaxy modules can be imported
3. Run from the Galaxy root directory

This approach works for both XML and YAML tools and validates that the tool can be successfully parsed by Galaxy's tool loading system.

## Key Reference Files

### Parsing and Schema

- **`lib/galaxy/tool_util/xsd/galaxy.xsd`**: XML Schema Definition for Galaxy tools
- **`lib/galaxy/tool_util/parser/xml.py`**: XML parser producing ToolSource objects
- **`lib/galaxy/tool_util/parser/yaml.py`**: YAML parser producing ToolSource objects
- **`lib/galaxy/tool_util/parser/interface.py`**: ToolSource interface definition

### Unit Tests

- **`test/unit/tool_util/test_parsing.py`**: Basic parsing tests
- **`test/unit/tool_util/test_test_definition_parsing.py`**: Test definition parsing
- **`test/unit/tool_util/test_parameter_specification.py`**: Parameter specification modeling (uses specifications from `test/unit/tool_util/parameter_specification.yml`)
- **`test/unit/tool_util/parameter_specification.yml`**: YAML file containing parameter validation test specifications for various tools (e.g., `gx_boolean`, `gx_int`, etc.)
- **`test/unit/tool_util/test_parameter_test_cases.py`**: Parameter test cases

### API Tests

- **`lib/galaxy_test/api/test_tool_execute.py`**: Lower-level API testing for exact JSON syntax validation

### Tool Configuration

- **`test/functional/tools/sample_tool_conf.xml`**: Tool configuration file that registers all functional test tools with Galaxy. This file is essential - **every test tool must be listed here to be loaded during testing**.
  - Format: `<tool file="path/to/tool.xml" />` or `<tool file="path/to/tool.yml" />`
  - Paths are relative to `test/functional/tools/`
  - Tools can be organized in `<section>` tags for grouping
  - Both XML and YAML tools are supported
  - When adding a new tool, insert it in a logical location (often near related tools)

  **Example structure:**
  ```xml
  <?xml version="1.0"?>
  <toolbox tool_path="${tool_conf_dir}">
    <tool file="simple_constructs.xml" />
    <tool file="collection_creates_pair.xml" />
    <tool file="collection_creates_pair_user.yml" />
    <section id="test" name="Test Section">
      <tool file="parameters/gx_boolean.xml" />
      <tool file="parameters/gx_boolean_user.yml" />
    </section>
  </toolbox>
  ```

## Tool Profiles

Galaxy tools use profile versions to control behavior changes. Common profiles include:

- **16.04**: Disables implicit extra file collection, `format="input"`, interpreter use
- **18.01**: Separate home directory per job
- **20.05**: JSON config file behavior changes for optional parameters
- **23.0**: Text parameter optional inference changes
- **24.0**: Data source tool environment changes

See `lib/galaxy/tool_util/xsd/galaxy.xsd` for complete profile documentation.

## Examples by Category

### Parameter Testing Tools
- `parameters/gx_boolean.xml` - Boolean parameter
- `parameters/gx_conditional_boolean_checked.xml` - Conditional with boolean
- `parameters/gx_color.xml` - Color parameter
- `parameters/gx_select_dynamic.xml` - Dynamic select parameter

### Collection Tools
- `collection_creates_pair.xml` - Creates paired collection
- `collection_creates_list.xml` - Creates list collection
- `collection_creates_dynamic_nested.xml` - Dynamic nested collections

### Workflow Building Blocks
- `for_workflows/cat.xml` - Simple concatenation
- `for_workflows/head.xml` - Take first N lines
- `for_workflows/count_list.xml` - Count list elements

### YAML Format Examples
- `cat_user_defined.yml` - Simple user-defined tool
- `collection_creates_pair_y.yml` - Collection creation in YAML

## Troubleshooting

### Common Issues

1. **Tool doesn't load**:
   - Check XML/YAML syntax, verify tool ID and version are present
   - **Ensure the tool is registered in `sample_tool_conf.xml`** - this is the most common issue
   - Verify the path in `sample_tool_conf.xml` is correct and relative to `test/functional/tools/`
2. **Tests fail**: Verify test data files exist in `data/` directory
3. **Parser errors**: Validate against XSD schema for XML tools
4. **Unit test failures**: Run specific unit test file to see detailed error messages
5. **YAML tool not recognized**: Check that `class: GalaxyUserTool` or `class: GalaxyTool` is at the root level

### Getting Help

- Check the Galaxy Tool XSD for XML attribute documentation
- Look at similar existing test tools for examples
- Run unit tests to validate parsing before running framework tests
- Use API tests when testing exact JSON structure requirements

## Future Improvements

- [x] Document process for validating single tools (not entire directory)
- [ ] Add more examples of common test patterns
- [ ] Document CWL tool testing approach
- [ ] Create templates for common test tool types
