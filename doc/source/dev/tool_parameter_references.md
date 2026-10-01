# Tool Parameter References

Galaxy has grown organically over decades and has used conflicting syntaxes for referencing nested
tool parameters. Legacy tool syntaxes and APIs will continue to be supported, but they are inherently
inconsistent. This document is a concise, quick look at how these references differ, aimed at Galaxy
developers evaluating new features and changes to existing features.

For how parameter _values_ are represented and validated, see [Tool State](tool_state.md).

## Running Example

Every example below references parameters of this tool, which has a top-level input and one
input inside each kind of grouping: a section, a conditional, and a repeat.

```xml
<inputs>
    <param name="input" type="data" format="tabular" />
    <section name="adv" title="Advanced">
        <param name="size" type="integer" value="1" />
    </section>
    <conditional name="cond">
        <param name="sel" type="select">
            <option value="a">A</option>
            <option value="b">B</option>
        </param>
        <when value="a">
            <param name="input1" type="data" format="txt" />
        </when>
        <when value="b" />
    </conditional>
    <repeat name="queries" title="Query">
        <param name="input2" type="data" format="txt" />
    </repeat>
</inputs>
```

## At a Glance

Galaxy names a nested parameter in five basic styles. Every feature in this document uses one of
them, and several features use more than one.

| Style                | Running example                                                                       | Used by                                                                                                                                                                                                                                                                                  |
| -------------------- | ------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Pipe path** (flat) | `adv\|size`, `cond\|input1`, `queries_0\|input2`                                      | XML and YAML output attributes (`format_source`, `metadata_source`, `structured_like`, ...); XML tool tests; the legacy tool API; `/build` responses and legacy errors; `.ga` `input_connections`; gxformat2 `in:`; invocation `parameters`; the refactor API; workflow editor terminals |
| **Nested state**     | `{"adv": {"size": 3}, "cond": {"sel": "a", "input1": …}, "queries": [{"input2": …}]}` | The legacy API with `input_format: "21.01"`; the tool request API; stored `tool_state`; gxformat2 `state:`; YAML tool tests                                                                                                                                                              |
| **Dotted path**      | `$cond.input1`, `inputs.cond.input1`, `cond.sel`, `#{cond.input1}`                    | Cheetah templates; JavaScript expressions in YAML tools and workflow `when`; XML `<actions>` and `change_format`; rename post-job actions; tool request API error locations (`cond.a.input1`)                                                                                            |
| **Python subscript** | `cond['sel']`                                                                         | XML output `<filter>`                                                                                                                                                                                                                                                                    |
| **Bare leaf name**   | `input1`                                                                              | XML dependent parameters (`data_ref`, `<options>` filter `ref`); legacy fallbacks: Cheetah's name search, the `format_source` alias, `structured_like` below profile 26.0, XML tests up to profile 24.1, the rename action's suffix match                                                |

Repeats are where the styles diverge the most:

| Style                | Repeat instance                                  | Not reachable from                 |
| -------------------- | ------------------------------------------------ | ---------------------------------- |
| Pipe path            | `queries_0\|input2` (index is part of the name)  | `structured_like` when mapped over |
| Nested state         | list position                                    | —                                  |
| Cheetah / JavaScript | `$queries[0].input2`, `inputs.queries[0].input2` | Cheetah's bare-name fallback       |
| XML `<actions>`      | only `param_attribute="first.…"`                 | everything else in `<actions>`     |
| Request API errors   | `queries.0.input2`                               | —                                  |

Traps that fail **silently** rather than with an error, each described in detail below:

- The legacy tool API ignores nested dicts unless `input_format` is `21.01`, and ignores pipe keys
  when it is. The parameters take their defaults ([Forms of the Legacy API](#forms-of-the-legacy-api)).
- A gxformat2 `in:` key written `adv/size` connects to nothing ([Format2](#format2-gxformat2)).
- An XML `change_format` `<when input="cond|sel">` never matches ([Cheetah](#cheetah-templates)).
- An XML output `<filter>` that raises keeps the output.
- The `format_source` legacy alias works when the job is created, but not during later dataset
  discovery ([Pipe paths](#pipe-paths)).
- YAML output attributes such as `format_source` are not checked against the declared inputs.

## Tool Syntax

XML and YAML tools mostly share one set of resolvers: the YAML parser hands output attributes such
as `format_source` to the same code as XML, unchanged. The table summarizes every feature that
references a parameter. The scope columns describe the resolver; YAML tools are further limited by
which groupings they can declare (see [YAML](#yaml)).

| Feature                            | XML                                                                                             | YAML                                                                                   | Section                | Conditional                        | Repeat                                       | Notes                                                                          |
| ---------------------------------- | ----------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- | ---------------------- | ---------------------------------- | -------------------------------------------- | ------------------------------------------------------------------------------ |
| Command and config templates       | Cheetah `$cond.input1` in `<command>`, `<configfile>`, `<environment_variable>`, output `label` | JavaScript `$(inputs.cond.input1.path)` in `shell_command`, `configfiles`, `arguments` | ✓                      | ✓                                  | ✓ `$queries[0].input2` / `inputs.queries[0]` | Cheetah also resolves a bare `$input1` by searching every level except repeats |
| `format_source`, `metadata_source` | `cond\|input1`                                                                                  | same                                                                                   | ✓                      | ✓                                  | ✓ `queries_0\|input2`                        | Legacy alias drops only the innermost grouping, and only at job creation       |
| `structured_like`                  | `cond\|input1`                                                                                  | same                                                                                   | ✓                      | ✓                                  | unmapped only                                | When mapped over below profile 26.0, a bare name is searched recursively       |
| `type_source`                      | `adv\|…`                                                                                        | `collection_type_source`, same                                                         | ✓                      | ✗                                  | ✓                                            | A path into a conditional raises `AttributeError`                              |
| `default_identifier_source`        | `cond\|input1`                                                                                  | same, file flavor only                                                                 | ✓                      | ✓                                  | `?`                                          | Exact match, no alias                                                          |
| `change_format`                    | `input="cond.sel"` (Cheetah), `input_dataset="cond\|input1"`                                    | not supported                                                                          | ✓                      | ✓                                  | ✓                                            | Errors are swallowed                                                           |
| Output `<filter>`                  | `cond['sel']`                                                                                   | not supported                                                                          | ✓                      | ✓                                  | ✓                                            | Python `eval`; an exception keeps the output                                   |
| Output `<actions>`                 | `cond.sel`                                                                                      | not supported                                                                          | ✓                      | ✓                                  | ✗                                            | Dotted walk from the root                                                      |
| Dependent parameters               | `data_ref="input1"`, `<options>` `<filter ref>`                                                 | `data_ref` only, file flavor only                                                      | own or enclosing level | own or enclosing level (not `sel`) | own or enclosing level                       | Leaf name in lexical scope, declared earlier                                   |
| Tool tests                         | nested elements, or `cond\|input1`                                                              | nested dicts only                                                                      | ✓                      | ✓                                  | ✓                                            | XML bare names allowed up to profile 24.1                                      |
| Validators, sanitizers             | —                                                                                               | —                                                                                      | n/a                    | n/a                                | n/a                                          | See only their own parameter's value                                           |

### XML

The [Tool Syntax](#tool-syntax) table summarizes XML references.

**Patterns.** XML tools name nested parameters in six different ways:

- **Cheetah dotted access** (`$cond.input1`), with a hidden bare-name fallback. Used by command, configfiles, environment variables, labels and `change_format input`.
- **Python subscripts** (`cond['sel']`). Used by `<filter>`.
- **Dotted dictionary walk from the root** (`cond.sel`). Used by output `<actions>`.
- **Pipe paths with `_N` repeat indexes** (`cond|input1`, `queries_0|input2`). This is the `prefixed_name` produced by `visit_input_values`. Used by `format_source`, `metadata_source`, `structured_like`, `type_source`, `default_identifier_source`, `input_dataset` and tool tests.
- **Leaf names resolved through lexical scope** (`input1`). Used by `data_ref`, `from_dataset` and `<options>` filter `ref`s.
- **Legacy bare-name searches.** These come in three incompatible variants: the Cheetah fallback, the one-level alias for pipe paths, and `structured_like`'s recursive search.

The same attribute name can mean different syntaxes. An `<options>` `<filter ref="input1">` is a lexical leaf name, while an `<actions>` `<filter ref="cond.input1">` is a dotted path.

#### Cheetah Templates

```xml
<command>
cat '$input' '$cond.input1' > '$out' &&
echo $adv.size $cond.sel
#for $q in $queries
  && cat '$q.input2'
#end for
</command>
<data name="out" format="txt" label="${tool.name} on ${on_string} (${cond.sel})">
    <change_format>
        <when input="cond.sel" value="b" format="tabular" />
    </change_format>
</data>
```

- Every template is rendered by `fill_template` against nested wrappers. Sections and conditionals become attributes (`$adv.size`). Repeats become lists, so use `$queries[0].input2` or `#for`. Nested repeats work too (`$queries[0].inner[0].input4`).
- When a name is not found, `fill_template` retries with a `TreeDict`. That copy injects every key from nested section and conditional dicts into the top level, so `$input1`, `$size` and `$sel` all resolve.
  - The fallback reaches any depth, but never into repeats (`$input2` fails).
  - On a name collision, the first match in input order wins, and a top-level parameter beats a nested one.
- `change_format` `input` is plain Cheetah with `$` prepended. Any exception skips that `<when>` silently.
  - A pipe path does not raise. `input="cond|sel"` renders as `"{'sel': 'a'}|sel"` and simply never matches.
- `<configfile><inputs name="…"/>` is not a reference. It dumps the whole nested state as JSON.
- A `<configfile name="…">` defines a new template variable. It is not a reference either.

#### Pipe Paths

```xml
<data name="out1" format_source="cond|input1" metadata_source="cond|input1" />
<data name="out2" format_source="queries_0|input2" />
<collection name="c" type="list" format_source="cond|input_collection['forward']" />
```

- The reference is a key of the input dataset map, which is the pipe-joined `prefixed_name`. Repeats need a concrete instance index, as in `queries_0|input2`. For collections, `name[0]` or `name['forward']` picks a specific element.
- **Legacy alias.** Since 23.1, inputs are keyed by full path. A `LegacyUnprefixedDict` keeps the old key working as an alias. The old key is the visitor's `prefix + name`, which drops **only the innermost section or conditional**:

  | Parameter path       | Alias                        |
  | -------------------- | ---------------------------- |
  | `cond\|input1`       | `input1`                     |
  | `adv\|deep\|input3`  | `adv\|input3` (not `input3`) |
  | anything in a repeat | none                         |

  A real key always beats an alias. If `input` were `multiple="true"`, it would create the keys `input1`, `input2` and so on, and `format_source="input1"` would then resolve to `input`'s first dataset.

- **The alias works only when the job is created** (`DefaultToolAction`). Several paths run later and look names up in a plain dict built from the job's input associations, which are recorded under full paths. Those paths accept only full paths:
  - collection `format_source` and `metadata_source` during dataset discovery
  - the late `format_source` evaluation for `expression.json` outputs
  - `MetadataSourceProvider`
- `default_identifier_source` is looked up in the mapped-over collections by exact flattened key, with no alias.
- The `OutputsFormatSourceReference` linter warns when an unqualified name matches a nested parameter. It does not model repeats, so a name inside a repeat counts as top level and passes.

#### `structured_like`

```xml
<collection name="c" type="list" structured_like="cond|input1" inherit_format="true" />
```

`structured_like` is resolved in two places:

- **Without mapping**, `collection_prototype` looks the name up in the alias dict described above, at any profile.
- **When mapped over**, `sliced_input_collection_structure` resolves it in one of three ways:
  - A `|` path is walked key by key. Repeats are unreachable, because the state holds `queries`, not `queries_0`.
  - A bare name with profile < 26.0 triggers a recursive search through section and conditional dicts. The first match wins, at any depth.
  - A bare name with profile ≥ 26.0 must be top level.

So `structured_like="input3"` (deep inside `adv|deep`) works only when mapped over with an old profile, and `queries_0|input2` works only without mapping. The `OutputsStructuredLikeReference` linter warns on unqualified nested names. The upgrade advice `18_01_consider_structured_like` still claims that 18.01+ tools must qualify, which contradicts the 26.0 gate in the code.

#### `type_source`

```xml
<collection name="c" type_source="adv|input_collect" />
```

Without mapping, the reference must first be a key in the alias dict. Then `|` segments are walked down `tool.inputs`, with any trailing `_N` stripped as a repeat index. As a result:

- Sections and repeats work.
- A path into a conditional raises `AttributeError`, because `Conditional` has no `inputs`.
- A bare alias such as `input1` passes the key check but then walks to `None`.
- A real parameter name ending in `_<digit>` gets mangled by the stripping.

When mapped over, it is resolved like `structured_like`.

#### Output Filters

```xml
<data name="out" format="txt">
    <filter>cond['sel'] == 'a' and adv['size'] &gt; 1 and len(queries) &gt; 0</filter>
</data>
```

- The filter is `eval`'d with the raw nested state as locals. Use Python subscripts. There is no dotted access and no bare-name fallback.
- A `KeyError` is common, for example when a parameter belongs to an inactive conditional case. Any exception is logged and **the output is still created**.

#### Output Actions

```xml
<actions>
    <conditional name="cond.sel">
        <when value="a">
            <action type="metadata" name="dbkey">
                <option type="from_param" name="cond.input1" param_attribute="dbkey" />
            </action>
        </when>
    </conditional>
</actions>
```

- `<conditional name>`, `<option type="from_param" name>` and `<filter type="param_value|insert_column|metadata_value" ref>` all split on `.` and walk dictionaries from the root of the parameters.
  - Sections and conditionals work (`asection.abool`, `input_cond.input`).
  - Repeats cannot be indexed. The one exception is `from_param`'s `param_attribute`, where `first` selects the first element of a list (`param_attribute="first.input2.ext"`).
- `param_attribute` and `ref_attribute` are attribute chains on the resolved value, not parameter paths.

#### Dependent Parameters

```xml
<param name="input" type="data" format="tabular" />
<param name="col" type="data_column" data_ref="input" />
<when value="a">
    <param name="input1" type="data" format="txt" />
    <param name="col1" type="data_column" data_ref="input1" />
    <param name="build" type="select">
        <options><filter type="data_meta" ref="input" key="dbkey" /></options>
    </param>
</when>
```

- References are **leaf names only**, resolved through `ExpressionContext` chains. The lookup checks the parameter's own level first, then each enclosing level outward.
- At parse time, `parse_param_elem` asserts that each dependency was **already declared**.
  - You cannot reach into a sibling or child group: `data_ref="input1"` fails from the top level, and `cond.input1` and `cond|input1` fail too.
  - Forward references fail.
  - A `<when>` cannot reference its own conditional's test parameter (`sel`).
- These attributes are covered by the parse-time check: `data_ref` on `data_column` and `group_tag`, `from_dataset`, and the `ref` of `data_meta` and `param_value` filters.
- These are not checked at parse time and resolve leniently at runtime: `remove_value` `ref` and `meta_ref`, and `rules` `data_ref`.
- `<options from_parameter>` (deprecated) is an attribute path on the parameter object itself, not a parameter reference.

#### Tool Tests

```xml
<test>
    <param name="input" value="1.tabular" />
    <section name="adv"><param name="size" value="3" /></section>
    <conditional name="cond">
        <param name="sel" value="a" />
        <param name="input1" value="1.txt" />
    </conditional>
    <repeat name="queries"><param name="input2" value="a.txt" /></repeat>
    <repeat name="queries"><param name="input2" value="b.txt" /></repeat>
</test>
```

- Nested `<section>`, `<conditional>` and `<repeat>` elements are flattened to pipe paths. Repeated `<repeat>` elements are numbered `queries_0`, `queries_1`, and so on.
- The equivalent flat form `<param name="cond|input1">` / `<param name="queries_1|input2">` is accepted at every profile.
- Up to profile 24.1, bare leaf names (`input1`, `size`, `sel`) are also matched, by trying each suffix of the qualified path.
  - **Gotcha:** a bare `input2` given twice fills the repeat in reverse order (`queries_0` gets the second value), because the matcher takes the last match.
- From profile 24.2, bare names are rejected ("Invalid parameter name found") and test cases are validated as `test_case_xml` [tool state](tool_state.md).
- Test `<output>` and `<output_collection>` names refer to outputs, not parameters.

#### Not References

- `<validator>`s and `<sanitizer>`s only see their own parameter's value.
- `<expand>` and macro tokens are textual and resolved before parsing.
- `<discover_datasets>` attributes are not parameter references.
- `<edam_*>` and `<xrefs>` are not parameter references.
- The legacy conditional `value_ref` / `value_from` (used by `upload.xml`) names a sibling parameter on the same level by bare name.

### YAML

Galaxy has two YAML tool flavors. Both end up in the same parser, `YamlToolSource` in
`galaxy.tool_util.parser.yaml`, but they accept different input shapes:

- **File** (`file` in the table below): a `.yml` tool on disk, loaded by `get_tool_source` when
  beta tool formats are enabled. `class` is optional (`GalaxyTool` or absent). The raw dict goes
  straight to the parser and nothing validates it first. This is the shape
  `test/functional/tools/simple_constructs.yml` uses: repeats nest under `blocks:`, a conditional
  can use a `when:` mapping, and the command can be a Cheetah `command:` or a JavaScript
  `shell_command:`.
- **Modelled** (`model`): `class: GalaxyTool` posted to `/api/dynamic_tools` (admin), or
  `class: GalaxyUserTool` posted to `/api/unprivileged_tools`. Both are validated first by the
  pydantic models in `galaxy.tool_util_models` (`YamlToolSource` and `UserToolSource` in
  `_models.py`, inputs from `yaml_parameters.py`), then dumped and handed to the same parser.
  `shell_command` (JavaScript) is required. Groupings nest under `parameters:`, and a
  conditional's branches go in a `whens:` list. Unknown keys are rejected for `GalaxyUserTool`;
  on `GalaxyTool` outputs they are accepted and then dropped.

The syntax is documented in [Authoring User-Defined Tools](user_defined_tools_authoring.md).
This section covers only how a YAML tool refers to its parameters by name.

Here is the running example in the modelled shape, the one the tool editor and the authoring docs
describe:

```yaml
class: GalaxyUserTool
id: running_example
name: Running example
version: "0.1.0"
container: busybox
shell_command: |
  cat '$(inputs.input.path)' > out.txt
  echo '$(inputs.adv.size)' >> out.txt
  echo '$(inputs.cond.sel)' >> out.txt
  $(inputs.cond.sel == "a" ? `cat '${inputs.cond.input1.path}' >> out.txt` : "")
  cat $(inputs.queries.map((q) => `'${q.input2.path}'`).join(" ")) >> out.txt
inputs:
  - name: input
    type: data
    format: tabular
  - name: adv
    type: section
    parameters:
      - name: size
        type: integer
        value: 1
  - name: cond
    type: conditional
    test_parameter:
      name: sel
      type: select
      options:
        - { label: A, value: a }
        - { label: B, value: b }
    whens:
      - discriminator: a
        parameters:
          - name: input1
            type: data
            format: txt
      - discriminator: b
        parameters: []
  - name: queries
    type: repeat
    parameters:
      - name: input2
        type: data
        format: txt
outputs:
  - name: out
    type: data
    format_source: input
    from_work_dir: out.txt
```

```{warning}
This tool passes pydantic validation but does not load. The parser has no `section` input type:
it reports `Unknown Galaxy parameter type section`. It also reads a repeat's children from
`blocks:`, which the model forbids, so a modelled repeat fails with `KeyError: 'blocks'`. In
practice, **modelled YAML tools support only conditionals among the groupings**. File-flavor
tools support conditionals and repeats (`blocks:`). Neither flavor supports sections. Unit tests
only round-trip the models through `to_internal()`, never through the parser, which is why the
mismatch goes unnoticed. The [Tool Syntax](#tool-syntax) table describes what the resolvers support.
```

As a file-flavor tool, the example has to drop `adv`. Its repeat looks like this:

```yaml
- name: queries
  type: repeat
  blocks:
    - name: input2
      type: data
      format: txt
```

#### Patterns

YAML tools use four reference styles.

1. **JavaScript object paths over the runtime state**: `inputs.cond.input1`,
   `inputs.queries[0].input2`. This style covers `shell_command`, `configfiles`, `arguments` and
   editor typing. It is the only style the authoring docs teach.
2. **Pipe-qualified strings passed to the XML resolution code unchanged**: `cond|input1`, or
   `queries_0|input2` with a repeat index. This style covers `format_source`, `metadata_source`,
   `structured_like`, `collection_type_source` and `default_identifier_source`. The YAML parser
   copies these strings without interpreting them, so every XML rule applies, including the
   unqualified fallbacks.
3. **Cheetah**: `command` in file-flavor tools, using the same wrapped parameter namespace as XML.
4. **Nested values with no name syntax**: test `inputs` mirror the state tree. The parser then
   flattens them to style 2 (`cond|sel`, `cond|input1`, `queries_0|input2`) for the shared
   test-case code.

`data_ref` is the one outlier. It is a bare name looked up in the enclosing scope, as in XML.

#### JavaScript Expressions

`shell_command`, the `content` of each `configfiles` entry, and the `arguments` that follow
`base_command` are evaluated as CWL-style expressions. `$(…)` holds a parameter reference or a
single expression, and `${…}` holds a function body that must return a value. When the job has a
stored tool state, `inputs` is that state converted for runtime by `runtimeify` (see
[Tool State](tool_state.md)). In that object:

- A conditional is an object holding its test parameter and the active branch's parameters:
  `inputs.cond.sel` and `inputs.cond.input1`. Parameters in inactive branches are absent.
- A repeat is an array of objects: `inputs.queries[1].input2.path`, or
  `inputs.queries.map((q) => q.input2.path)`. Nested repeats are nested arrays:
  `inputs.outer[0].inner[1].x`.
- A section would be an object (`inputs.adv.size`, the form the model's own examples use), but
  sections do not load today.
- A data input is a CWL `File`-like object, so `.path` is required to get a path. A collection
  input exposes its elements as `.elements`, for example `inputs.f1.elements.forward.path`.
- Dotted and bracketed property access (`inputs.cond['input1'].path`) both work. Pipe paths are
  not JavaScript and do not resolve.

```yaml
shell_command: |
  cat '$(inputs.cond.input1.path)' $(inputs.queries.map((q) => `'${q.input2.path}'`).join(" ")) > out.txt
```

Gotchas:

- At validation time, modelled tools check only the identifier directly after `inputs.` against
  the top-level input names. `inputs.cond.input1` and `inputs.cond.nope` both pass. Aliased
  access such as `var x = inputs` is not checked.
- The tool editor types `inputs` from `/api/unprivileged_tools/runtime_model`. There a
  conditional is a `oneOf` of one object per branch, keyed on the test parameter's value.
- Jobs without a stored tool state, for example jobs from the legacy run API, fall back to the
  deprecated `to_cwl` conversion. Whether that produces the same shape was not checked.
- `configfiles` always use JavaScript. A file-flavor tool that pairs Cheetah `command:` with
  `configfiles` evaluates them against a Cheetah `param_dict` that has no `inputs` key. This
  combination is untested.

#### Output Source Attributes

`format_source`, `metadata_source`, `structured_like`, `collection_type_source` (also accepted
as `type_source`) and `default_identifier_source` reach the same `ToolOutput` and
`ToolOutputCollection` objects as their XML counterparts, and resolve the same way. See
[XML](#xml) for the full rules. In short:

```yaml
outputs:
  - name: out
    type: data
    format_source: cond|input1 # `input1` also resolves, through the legacy alias
    metadata_source: cond|input1
  - name: per_query
    type: data
    format_source: queries_0|input2
```

- Data inputs are keyed by prefixed name: `cond|input1`, `queries_0|input2`. Each also gets a
  legacy alias in which the conditional name is dropped (`input1`) but the repeat prefix is kept.
- `structured_like` accepts unqualified names when the profile is below 26.0. YAML tools default
  to profile `24.2`, so `structured_like: input1` currently works.
- `structured_like` does not descend into repeats.
- None of these names are checked against the declared inputs, whether by the pydantic models or
  by the linters (the output linters are XML-only). A typo shows up only when the job runs.
- The YAML style is JavaScript, but these attributes use pipe syntax: write
  `format_source: cond|input1`, not `cond.input1`.

#### Test Inputs

YAML tests write their values as a nested tree in the
[`test_case_json`](tool_state.md#state-representations) representation, which is validated
against the tool's parameter model:

```yaml
tests:
  - inputs:
      input: { class: File, path: a.tsv }
      cond:
        sel: a
        input1: { class: File, path: b.txt }
      queries:
        - input2: { class: File, path: c.txt }
        - input2: { class: File, path: d.txt }
```

- Flat `cond|input1` keys, and unqualified `input1` or `sel`, fail validation with
  `extra_forbidden`. The only exception is `expect_failure: true`, which skips validation; any
  stray keys are then silently ignored.
- The parser then flattens the tree to `input`, `cond|sel`, `cond|input1`, `queries_0|input2`
  and `queries_1|input2`. Nested repeats flatten to keys like `outer_0|inner_1|x`. The flat keys
  feed the same test-expansion code as XML tests. These tests are submitted through the tool
  request API, except tests with credentials, which use the legacy API.
- If the test parameter is omitted (`cond: {input1: …}`), the conditional's default branch is
  used.

#### Unsupported or File-Flavor-Only Features

- **Output `filter`, `change_format` and `actions`.** `ToolOutput.from_dict` and
  `_parse_output_collection` always set these to empty, so YAML tools cannot filter outputs or
  switch formats based on parameter values.
- **`environment_variables`.** `parse_environment_variables` returns `[]`.
- **Dynamic select options**, and with them the `<filter ref="…">` style of reference, have no
  YAML form.
- **`data_column` with `data_ref`.** File flavor only, where it works through
  `YamlInputSource.get`, as in XML. `data_ref` is a bare name looked up in the enclosing scope.
  The models have no `data_column` type.
- **Validators** never name another parameter. File-flavor tools accept every validator type.
  The models accept only `regex`, `length`, `empty_field`, `in_range` and `no_options`.
- **Other YAML.** Workflow parameter inputs are also parsed with `YamlInputSource`, and gxformat2
  workflows can embed a `GalaxyUserTool`. Both are covered under [Workflows](#workflows).

### Differences Between XML and YAML Tools

YAML tools are not a different reference model. Where a feature exists in both, the YAML parser
passes the reference string to the XML resolver unchanged, so the XML rules, including its legacy
fallbacks, apply. The differences come from which features and groupings YAML supports, and from
the expression language.

| Topic                                                                            | XML                                                                                    | YAML                                                                                              |
| -------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| Groupings                                                                        | sections, conditionals, repeats                                                        | file flavor: conditionals and repeats (`blocks:`); modelled: conditionals only; sections: neither |
| Command language                                                                 | Cheetah, dotted access with a bare-name fallback                                       | JavaScript over `inputs` (modelled tools require it); Cheetah `command:` in file flavor only      |
| Output attributes (`format_source`, ...)                                         | pipe paths, checked by linters                                                         | the same pipe paths, inside a JavaScript-style tool, checked by nothing                           |
| `change_format`, `<filter>`, `<actions>`, environment variables, dynamic options | supported                                                                              | not supported                                                                                     |
| `data_ref`, `default_identifier_source`                                          | supported                                                                              | file flavor only                                                                                  |
| Test inputs                                                                      | nested elements or flat `cond\|input1`; bare names up to profile 24.1                  | nested dicts only; flat and bare keys rejected (unless `expect_failure`)                          |
| Default profile                                                                  | none, so legacy behaviour applies                                                      | `24.2`, so `structured_like: input1` still resolves                                               |
| Linting of references                                                            | `OutputsFormatSourceReference`, `OutputsStructuredLikeReference` (no repeat awareness) | none for output attributes; modelled tools check only the first name after `inputs.`              |

When adding a feature that references parameters, the YAML side is where the inconsistency shows:
one tool mixes `inputs.cond.input1` in its command with `cond|input1` in its outputs.

## API

Galaxy has two job-submission APIs. The legacy tool API (`POST /api/tools`) accepts two input
shapes, chosen by the `input_format` field: flat pipe-delimited keys (`legacy`, the default) and
nested dictionaries (`21.01`). The tool request API (`POST /api/jobs`) accepts only nested
dictionaries, validated against the tool's pydantic request model. All three shapes are checked
by the same parametrized API tests (`tool_input_format` in `lib/galaxy_test/api/test_tool_execute.py`).

| API / form            | Endpoint                                                 | Nested syntax                                  | Section         | Conditional                                              | Repeat                  | Data refs                                                              | Batch                                                                               | Notes                                                                                                      |
| --------------------- | -------------------------------------------------------- | ---------------------------------------------- | --------------- | -------------------------------------------------------- | ----------------------- | ---------------------------------------------------------------------- | ----------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| Legacy, flat          | `POST /api/tools` (`input_format` omitted or `"legacy"`) | `\|` between levels, `_N` for repeat index     | ✓ `adv\|size`   | ✓ `cond\|sel`, `cond\|input1`                            | ✓ `queries_0\|input2`   | `{"src","id"}`, bare id, `{"values": [...]}`, string encodings         | ✓ `{"batch": true, "values", "linked"}`, any parameter type                         | Nested dicts are ignored without an error; the tool form's fallback path uses this                         |
| Legacy, nested        | `POST /api/tools` with `"input_format": "21.01"`         | dicts and lists                                | ✓ `adv: {size}` | ✓ `cond: {sel, input1}`                                  | ✓ `queries: [{input2}]` | same as flat                                                           | ✓ same wrapper, placed in the nested position                                       | Flat `\|` keys are ignored without an error; `__current_case__` and `__index__` are overwritten or dropped |
| Tool request          | `POST /api/jobs` (`strict` defaults to true)             | dicts and lists only                           | ✓               | ✓ `sel` optional; when omitted, the default case is used | ✓ list                  | `{"src": "hda"\|"ldda"\|"dce"\|"url", ...}`; plain list for `multiple` | ✓ `{"__class__": "Batch", "values", "linked"}`, data and collection parameters only | Rejects flat keys, `__current_case__`, `__index__`, inactive-case parameters, and `"3"` for an integer     |
| Tool request, relaxed | `POST /api/jobs` with `"strict": false`                  | same as strict                                 | ✓               | ✓                                                        | ✓                       | same                                                                   | same                                                                                | Addressing is the same as strict; only null and default handling for text differs                          |
| Form build            | `GET`/`POST /api/tools/{id}/build`                       | flat in; nested `state_inputs` out             | ✓               | ✓                                                        | ✓                       | same as legacy                                                         | n/a                                                                                 | Input is parsed like legacy flat; errors are keyed by flat names                                           |
| Rerun build           | `GET /api/jobs/{id}/build_for_rerun`                     | stored job state flattened back into pipe keys | ✓               | ✓                                                        | ✓                       | remapped to current history                                            | n/a                                                                                 | Same response model as `/build`                                                                            |

**Patterns.** Each legacy shape ignores the other shape's syntax without reporting an error. A
nested dict sent without `input_format` is dropped, and its parameters take their default values.
A flat key sent with `21.01` is dropped the same way. Usually the only symptom is a later "required
parameter missing" error, keyed by the flat name (`cond|input1`). The request API never drops input
silently, because its models forbid extra fields. A key in the wrong syntax fails with a 400.
Batching uses a different wrapper in each API: `{"batch": true}` in the legacy API and
`{"__class__": "Batch"}` in the request API. Neither API accepts the other's wrapper. Each API also
names parameters differently in its validation errors (see
[Parameter Names in Responses](#parameter-names-in-responses)). Parameter _values_ and their
validation are covered in [Tool State](tool_state.md). This section covers only how parameters
are addressed.

### Legacy Tool API

`POST /api/tools` takes `tool_id`, `history_id` and `inputs`. With the default
`input_format: "legacy"`, every parameter is a single top-level key. The key is its path through
the tool's groups, with `|` between levels and `_N` after a repeat name:

```json
{
  "tool_id": "running_example",
  "history_id": "f2db41e1fa331b3e",
  "inputs": {
    "input": { "src": "hda", "id": "a799d38679e985db" },
    "adv|size": 3,
    "cond|sel": "a",
    "cond|input1": { "src": "hda", "id": "33b43b4e7093c91f" },
    "queries_0|input2": { "src": "hda", "id": "5969b1f7201f12ae" },
    "queries_1|input2": { "src": "hda", "id": "df7a1f0c02a5b08e" }
  }
}
```

With `"input_format": "21.01"`, the same request is nested:

```json
{
  "input_format": "21.01",
  "inputs": {
    "input": { "src": "hda", "id": "a799d38679e985db" },
    "adv": { "size": 3 },
    "cond": {
      "sel": "a",
      "input1": { "src": "hda", "id": "33b43b4e7093c91f" }
    },
    "queries": [
      { "input2": { "src": "hda", "id": "5969b1f7201f12ae" } },
      { "input2": { "src": "hda", "id": "df7a1f0c02a5b08e" } }
    ]
  }
}
```

**Groups**

- _Section._ Flat key `adv|size`, or nested `adv: {size}`. If the section is omitted, its
  parameters take their defaults.
- _Conditional._ The test parameter is addressed like any other parameter: `cond|sel` flat, or
  `cond: {sel}` nested. If it is omitted, the default case is used. Parameters of an inactive case
  (`cond|input1` when `sel` is `b`) are ignored.
- _Repeat (flat)._ The index is part of the key (`queries_0|...`, `queries_1|...`). Indices must
  start at 0 and be contiguous: the server stops at the first missing index, so a lone
  `queries_1|input2` is dropped.
- _Repeat (nested)._ A list.
- _Repeat bounds._ The two shapes handle a repeat's `min`/`max` differently. Flat input is padded
  with default instances up to `min` and silently truncated at `max`. Nested input with too few or
  too many instances is an error.
- _Names that look like indices._ Any group name ending in `_<digits>` is read as a repeat index
  when keys are flattened. A conditional named `inner_options_1` needed a regression fix
  (`test_create_job_with_conditional_name_digit_suffix`), and the heuristic still treats `_0` as a
  repeat index.

**Bookkeeping keys**

- _`__current_case__` and `__index__`_ appear in the server's _output_ state. The API ignores them
  on input. In `21.01`, a submitted `__current_case__` is recomputed and a submitted `__index__`
  is dropped.

**Data references**

- _Canonical form._ `{"src": "hda"|"ldda"|"hdca"|"dce", "id": <encoded>}`. A `values` list wraps
  several (`{"batch": false, "values": [hda1, hda2]}` for a `multiple="true"` parameter,
  `test_multidata_param`).
- _Older forms_ that are also accepted:
  - a bare encoded id, or an unencoded integer id (treated as an HDA)
  - comma-joined unencoded ids (`"12,13"`)
  - `"__collection_reduce__|<hdca id>"`
- _Collections on single-dataset parameters._ A bare `hdca` on a non-`multiple` `data`
  parameter is rejected; it must be wrapped in a batch
  (`test_hdca_rejected_for_single_data_param_in_conditional`).

**Batch (multirun)**

- _The wrapper_ is `{"batch": true, "values": [...]}`, and it can sit at any parameter's address:
  `"queries_0|input2": {...}` flat, or inside `queries: [{input2: {...}}]` nested
  (`test_multi_run_in_repeat`).
- _Linking._ Batched inputs are linked (zipped) by default. `"linked": false` makes them a
  cartesian product (`test_multirun_on_multiple_inputs_unlinked`).
- _Mapping over a collection._ A single `{"src": "hdca"|"dce", "id": ...}` in `values` maps over
  the collection. An optional `map_over_type` (for example `"paired"`) maps over subcollections.
- _Non-data parameters_ can be batched as well:
  `"num_lines": {"batch": true, "values": [1, 2, 3]}` (`test_multirun_non_data_parameter`).
- _Unwrapped values._ A wrapper-less value next to a batched one is shared by every job
  (`test_multi_run_in_repeat_mismatch`).

### Tool Request API

`POST /api/jobs` validates `inputs` against `RequestToolState` (strict) or
`RelaxedRequestToolState` (`"strict": false`). Validation happens before anything is queued, and
the response is a `tool_request_id`, not jobs. Inputs must be nested. Every model forbids extra
fields, so a key in the wrong syntax fails with a 400 instead of being ignored:

```json
{
  "tool_id": "running_example",
  "history_id": "f2db41e1fa331b3e",
  "inputs": {
    "input": { "src": "hda", "id": "a799d38679e985db" },
    "adv": { "size": 3 },
    "cond": {
      "sel": "a",
      "input1": { "src": "hda", "id": "33b43b4e7093c91f" }
    },
    "queries": [
      {
        "input2": {
          "__class__": "Batch",
          "values": [{ "src": "hdca", "id": "1cd8e2f6b131e891" }]
        }
      }
    ]
  }
}
```

**Groups.** The nesting matches `21.01`, with these differences:

- _Section._ `adv` can be omitted.
- _Conditional._ The conditional is a tagged union on the test parameter. Omitting `sel` selects
  the default case, but `"sel": null` is rejected.
- _Repeat._ A list of instance dicts.

**Rejected inputs**, each as an extra field or a type error:

- flat keys (`adv|size`, `cond|sel`)
- `__current_case__` and `__index__`
- a parameter from the inactive case (`cond: {sel: "b", input1: ...}`)
- `"3"` for an integer (`test_validation` on `gx_int`)
- the legacy `{"values": [...]}` and `{"batch": true, ...}` wrappers

**Data references**

- _Data parameters_ accept `{"src": "hda"|"ldda"|"dce", "id"}` and `{"src": "url", "url", "ext", ...}`.
- _`hdca`_ is accepted only by collection parameters or inside a `Batch`.
- _A `multiple` data parameter_ takes a plain list (`"f1": [hda1, hda2]`, `test_multidata_param`).

**Batch.** The wrapper is `{"__class__": "Batch", "values": [...], "linked": false?}`. It is
accepted only on `data` and `data_collection` parameters, so a batched integer is rejected. It may
appear at any depth (`test_multi_run_in_repeat`). Mapping over subcollections uses the same
`map_over_type` key as the legacy API.

**Unsupported tools.** Tools without a parameter model are rejected with "has no parameters
defined". These include the upload tools. Data-source tools (those with an `input_translator`)
are rejected when the request is processed, with a pointer to `/api/tools`.

### Forms of the Legacy API

Every shape below is accepted by `/api/tools`, or produced by Galaxy and fed back into it.

- **Fully flat.** The default, shown above. This is what the tool form's `formData` holds, keyed
  by `cond|sel` and `queries_0|input2`.
- **Fully nested (`"input_format": "21.01"`).** Shown above. Any other `input_format` value is a 400. The `"request"` label in `galaxy_test.base.populators` is a test-harness name that routes to
  `/api/jobs`; the server does not accept it.
- **Mixed.** Without `input_format`, only the flat keys are read: `{"adv": {"size": 3}, "cond|sel": "a"}`
  reads `cond|sel` and leaves `size` at its default. With `21.01`, the reverse applies. Neither
  combination is an error.
- **String-encoded.** Form-encoded posts may send `inputs` (and any other field) as a JSON string,
  which the API decorator parses. The test populators do this
  (`"inputs": "{\"cond|sel\": \"a\", ...}"`). Scalar strings such as `"adv|size": "3"` are
  converted by the parameter type.
- **Pseudo-parameters inside `inputs`.** These keys can be sent inside `inputs` as well as at the
  top level: `use_cached_job`, `rerun_remap_job_id` and `send_email_notification`. The client's
  legacy fallback sends them inside `inputs`.
- **Uploads.** `files_0|file_data` keys (sent as multipart form fields, or under `__files`) are
  merged into `inputs`.
- **Identifier helpers.** `<param>|__identifier__` keys are discarded by the server.
- **Job resources.** When job resource parameters are configured, each XML tool gets an injected
  `__job_resource` conditional. In the legacy API it is addressed flat, like any conditional:
  `"__job_resource|__job_resource__select": "yes"`, `"__job_resource|cores": 2`. Workflow and
  request state use the nested form `__job_resource: {__job_resource__select: "yes"}`. The tool
  test runner appends the flat keys even when submitting through `/api/jobs`. Whether that works
  is unverified (`?`).
- **Tool form submission.** The tool form posts to `/api/jobs` when `enable_tool_requests` (default
  on) and Celery are both enabled and the tool has a parameter model. In that case it nests the
  flat `formData` (`buildNestedState`), rewrites `{batch: true}` as `{__class__: "Batch"}`, and
  sends `strict: true`. Otherwise it posts the flat `formData` to `/api/tools` with no
  `input_format`. The API tests run the request API with `strict: false`.
- **Form build.** `GET`/`POST /api/tools/{id}/build` reads `inputs` (or the query string) as legacy
  flat state. The response contains:
  - `inputs`: the form tree, with repeat instances under `cache[i]` and case inputs under
    `cases[i].inputs`
  - `state_inputs`: nested JSON carrying `__current_case__` and `__index__`
  - `errors`: keyed by flat names

  `options_pagination` is also keyed by flat names (`cond|input1`, `queries_0|input2`).

- **Rerun.** `GET /api/jobs/{id}/build_for_rerun` loads the job's stored nested state, flattens it
  back to pipe keys (`queries_<__index__>|input2`), and returns the same model as `/build`.

#### Parameter Names in Responses

| Source                                       | Example key for a bad `size` / bad `sel`        | Format                                                                                                                                                                          |
| -------------------------------------------- | ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Legacy, flat (`err_data`, `param_errors`)    | `adv\|size`, `cond\|sel`                        | Flat path, matching the input key                                                                                                                                               |
| Legacy, `21.01` (`err_data`)                 | `adv` → stringified `{'size': ...}`; `sel`      | Errors are nested under the group name, but conditional test parameter errors are keyed by the bare name at the parent level (not `cond`), and the nested dicts are stringified |
| `/build` (`errors`)                          | `adv\|size`, `cond\|sel`                        | Flat (always parsed as legacy)                                                                                                                                                  |
| Tool request (`err_msg` only, no `err_data`) | `adv.size`, `cond.a.input1`, `queries.0.input2` | Pydantic location, dotted, with the conditional's _case value_ inserted as a path segment                                                                                       |

## Workflows

Workflows reference a tool step's parameters in two ways. Connections and every API keyed by
input name use the **flat** form (`cond|input1`, `queries_0|input2`). Stored and authored tool
state, and `when` expressions, use the **nested** form. Two outliers use other separators: rename
post-job actions use `.` because `|` is already taken there, and gxformat2 keeps `/` for
`step/output` sources, never for parameter paths.

| Feature                       | Where                                     | Nested syntax                                                           | Section                | Conditional                             | Repeat                           | Notes                                                                             |
| ----------------------------- | ----------------------------------------- | ----------------------------------------------------------------------- | ---------------------- | --------------------------------------- | -------------------------------- | --------------------------------------------------------------------------------- |
| Step connections              | `.ga` `input_connections` keys            | flat `\|`, `_N`                                                         | `adv\|size`            | `cond\|input1`                          | `queries_0\|input2`              | nested repeat `a_0\|b_1\|x` (augmentation untested)                               |
| Step input defaults           | `.ga` / format2 step `in`                 | flat                                                                    | `adv\|size`            | `cond\|input1`                          | `queries_0\|input2`              | `{"default": ...}` per flat name                                                  |
| Stored tool state             | `.ga` `tool_state`, DB                    | nested JSON                                                             | `adv: {size}`          | `cond: {sel, __current_case__, input1}` | `queries: [{__index__, input2}]` | `.ga` holds a JSON string; the editor API JSON-encodes each top-level value again |
| Connected / runtime markers   | inside `tool_state`                       | `{"__class__": "ConnectedValue"}` / `"RuntimeValue"` at the nested spot | ✓                      | ✓                                       | ✓                                | `RuntimeValue` isn't accepted by the `workflow_step*` pydantic models             |
| Legacy step `inputs` list     | `.ga` tool step                           | top-level name only                                                     | `adv`                  | `cond`                                  | ✗                                | lists runtime params only; core code doesn't use it                               |
| Format2 `in:`                 | gxformat2 step                            | flat `\|` copied verbatim                                               | `adv\|size`            | `cond\|input1`                          | `queries_0\|input2`              | `adv/size` isn't translated and silently matches nothing                          |
| Format2 `state:` + `$link`    | gxformat2 step                            | nested YAML, no markers                                                 | ✓                      | ✓ (`__current_case__` optional)         | list, no `__index__`             | `$link` becomes `ConnectedValue` plus a flat connection key                       |
| Format2 `tool_state:`         | gxformat2 step / export                   | native nested state, markers kept                                       | ✓                      | ✓                                       | ✓                                | export default when no state encoder is configured                                |
| Format2 `runtime_inputs:`     | gxformat2 step                            | top-level only                                                          | ✗                      | ✗                                       | ✗                                | `cond\|sel` becomes a bogus literal top-level key                                 |
| `when` expression             | step `when` (CWL JS)                      | nested, dot or bracket                                                  | `inputs.adv.size`      | `inputs.cond.input1`                    | `inputs.queries[0].input2`       | extra inputs stay flat (`inputs.when`); flat tool names are hidden since 26.2     |
| Editor terminals              | `get_all_inputs` → step `inputs[].name`   | flat                                                                    | ✓                      | ✓                                       | ✓                                | labels add only `Query 1 > `; sections and conditionals add nothing               |
| Editor tool form              | `build_module` `inputs`                   | flat form keys                                                          | ✓                      | ✓                                       | ✓                                | the server nests them with `populate_state`                                       |
| Invocation `parameters`       | `POST /api/workflows/{id}/invocations`    | step key → nested dict or flat                                          | ✓                      | ✓                                       | flat only                        | the run form sends flat with `parameters_normalized: true`                        |
| Subworkflow `parameters`      | same, on a subworkflow step               | `"<inner order_index>\|<flat name>"`                                    | ✓                      | ✓                                       | ✓                                | needs `parameters_normalized`; one level deep                                     |
| Subworkflow connections       | `input_connections` on a subworkflow step | inner input step **label**                                              | –                      | –                                       | –                                | unlabelled: `"<order_index>:<name>"`; no character checks on labels               |
| `replacement_params` / `${x}` | run request; PJA args; text values        | free name, not a path                                                   | –                      | –                                       | –                                | server substitutes only into rename `newname`                                     |
| Rename PJA `#{...}`           | `RenameDatasetAction` `newname`           | `.` → `\|`                                                              | `#{adv.x}` (data only) | `#{cond.input1}`                        | `#{queries_0.input2}`            | `\|` starts filters (`#{x \| basename}`); bare `#{input1}` matches by suffix      |
| Refactor API                  | `input_name` in actions and messages      | flat                                                                    | ✓                      | `cond\|input1`                          | `queries_0\|input2`              | documented in the schema as `'cond\|repeat_0\|input'`                             |

**Patterns.** The flat name is what `visit_input_values` produces as `prefixed_name`. It is the
real key for connections, step inputs, editor terminals, runtime overrides and refactoring. The
nested shape matches the tool's own state. Native state carries `__current_case__` and
`__index__`. Format2 `state:` and the `workflow_step*` models in `galaxy.tool_util.parameters`
leave them out, and those models reject both markers and flat keys. Conversion from nested to
flat happens in three places (gxformat2 `$link`, `_flatten_step_params`, `populate_state`).
Conversion from flat to nested happens only through `visit_input_values` over existing state, plus
a one-off repeat-growing hack. No shared path helper exists. See [Tool State](tool_state.md) for
the `workflow_step` and `workflow_step_linked` representations.

### Native `.ga`

```json
"input_connections": {
  "input": {"id": 0, "output_name": "output"},
  "cond|input1": {"id": 1, "output_name": "output"},
  "queries_0|input2": [{"id": 2, "output_name": "output"}]
},
"tool_state": "{\"cond\": {\"sel\": \"a\", \"__current_case__\": 0, \"input1\": {\"__class__\": \"ConnectedValue\"}}, \"queries\": [{\"__index__\": 0, \"input2\": {\"__class__\": \"ConnectedValue\"}}], ...}",
"post_job_actions": {"RenameDatasetActionout": {"action_type": "RenameDatasetAction", "output_name": "out",
    "action_arguments": {"newname": "#{cond.input1 | basename} ${suffix}"}}}
```

- A single connection is written as a dict and several as a list. Import accepts both.
- A connection key ending in `_N|...` makes Galaxy grow the repeat to N+1 instances on load
  (`augment_tool_state_for_input_connections`). Connections to nested repeats are untested.
- A connection that matches no input is ignored with only a logged warning
  ("Failed to use input connections").
- `tool_state` encodings differ by consumer. The DB and `.ga` export hold one JSON string of the
  nested dict. The editor payload (`_workflow_to_dict_editor`) uses `params_to_strings(nested=False)`,
  so each top-level value is itself a JSON string. Older `.ga` files are double-encoded the same
  way, and `safe_loads` on import accepts either.
- `post_job_actions` keys are `action_type + output_name`. Arguments name outputs, never
  parameters, except for the rename syntax below.

### Format2 (gxformat2)

```yaml
steps:
  example:
    tool_id: example
    in:
      input: i # flat names; values are "step_label/output"
      cond|input1: j
      adv|size: n
    state:
      cond: { sel: a }
      queries:
        - input2: { $link: k } # becomes input_connections["queries_0|input2"]
```

- Use `|` in `in:` keys. A `/` there is never converted, so `adv/size` produces a connection named
  `adv/size` that matches nothing. In _values_, `/` separates step label from output.
- A `$link` path is built with `|` for dicts and `_i` for list items. An item that is itself a
  `$link` collapses onto the parent key, which is how `multiple="true"` inputs are linked.
- `runtime_inputs: [num_lines]` works only for top-level parameters.
- Galaxy imports through `gxformat2.python_to_workflow` (`managers/workflows.py`). There is no
  `lib/galaxy/workflow/format2.py`. Export without a state encoder writes `tool_state:` verbatim,
  markers included.

### `when` Expressions

```yaml
in:
  cond|input1: j
  when: should_run # not a tool parameter
when: $(inputs.when && inputs.cond.input1 !== null && inputs.queries[0].input2 !== null)
```

- `inputs` is the step's execution state passed through `to_cwl`. Nesting follows tool state,
  `__current_case__` and `__index__` included. Data becomes CWL `File` objects.
- Connections that are not tool parameters go into `extra_step_state` under their **flat**
  connection name (`inputs.when`, or `inputs["cond|bogus"]` when a pipe name matches no active
  parameter).
- Since 26.2, connected nested tool parameters are no longer _also_ exposed under the flat name
  (`!("cond|more_text" in inputs)`). `${inputs.when}` is rewritten to `$(inputs.when)` for
  workflows from 23.0.
- When the editor and the tool-upgrade refactor decide whether a non-tool connection is a `when`
  input, they use a plain substring test on the expression text (`when.includes(name)` /
  `"inputs.<name>" in when`).

### Workflow Editor

- Terminal names are the server-provided `step.inputs[].name`, which are flat `prefixed_name`s.
  The client never parses them. `stepToConnections` pairs `input_connections` keys with those names.
- Non-data parameters get terminals only when their state value is `ConnectedValue`.
  `FormElement.vue` sets that value under the flat form key, and `build_module` turns the flat
  form into nested state.
- Untyped `${x}` parameters are found by scanning `config_form` values and PJA arguments
  (`modules/parameters.ts`). Lint messages refer to inputs by the flat name.

### Invocation API and Run Form

```json
{
  "inputs": {"0": {"src": "hda", "id": "..."}},
  "inputs_by": "step_index|step_uuid",
  "parameters": {"3": {"adv": {"size": 5}, "cond|sel": "a", "queries_0|input2": {"values": [...]}}},
  "replacement_params": {"suffix": "final"}
}
```

- `inputs` and `inputs_by` address workflow _input steps_ (`step_id`, `step_index`,
  `step_uuid` or `name`, meaning the label). They never address tool parameters.
- `parameters` keys can be an order index, a uuid, a tool id (legacy) or the DB step id with
  `legacy`. Nested dicts are flattened to `|`. Lists are not flattened, so repeats must be flat
  `queries_0|...`, and only instances already in the step state are visited. Legacy
  `{"param": NAME, "value": V}` is still accepted.
- For a subworkflow step, use `parameters_normalized: true` and keys like `"1|num_lines"` or
  `"1|cond|sel"`, where `1` is the inner order index. The split is on the first `|` only.
- `${x}` in tool _text values_ is substituted by the client run form (`getReplacements`). On the
  server, `replacement_params` reach only the rename `newname` (`${x}`). API callers submitting
  tool state must substitute it themselves.

### Rename Post-Job Action

`#{name | op | op}` takes the name of a data input. Because `|` separates the filter operations
(`basename`, `upper`, `lower`), nesting is written with `.` (`#{cond.input1}`,
`#{queries_0.input2}`) and converted to `|` before matching job input names. If nothing matches
exactly, the first `|`-qualified input name ending in the bare name is used (`#{input1}`).

### Refactor API

`connect`, `disconnect` and `extract_input` take `input: {label | order_index, input_name}` with
a flat `input_name`. Upgrade and fill-defaults messages report `input_name` the same way. The
schema documents the format as `'cond|repeat_0|input'`. `extract_untyped_parameter` rewrites
`${name}` in rename PJAs and connects, by its flat name, every tool input whose value is exactly `${name}`.
