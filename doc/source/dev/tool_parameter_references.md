# Tool Parameter References

Galaxy uses several syntaxes to reference nested tool parameters. This reference compares the
syntax, supported groupings and legacy behavior of tool definitions, APIs and workflows. It is
intended for Galaxy developers evaluating new features or changes to existing features.

Start with [At a Glance](#at-a-glance), then use [Tool Syntax](#tool-syntax), [API](#api) or
[Workflows](#workflows) for the relevant interface. For how parameter _values_ are represented and
validated, see [Tool State](tool_state.md). Collapsed verification notes identify supporting tests
and source inspection for selected behaviors; [Verification Gaps](#verification-gaps) lists the
remaining checks.

## Running Example

Most examples use the following parameter names: a top-level input and inputs inside a section,
a conditional and a repeat. Some examples introduce additional parameters to illustrate specific
features.

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

| Style                | Example                                                                               | Used by                                                                                                                                                                   |
| -------------------- | ------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Pipe path** (flat) | `adv\|size`, `cond\|input1`, `queries_0\|input2`                                      | [Output attributes](#pipe-paths); [XML tests](#tool-tests); [legacy API](#legacy-tool-api); [workflow connections](#workflows)                                            |
| **Nested state**     | `{"adv": {"size": 3}, "cond": {"sel": "a", "input1": …}, "queries": [{"input2": …}]}` | [Request API](#tool-request-api); [legacy API (`21.01`)](#legacy-tool-api); stored tool state; [gxformat2 state](#format2-gxformat2); [YAML tests](#test-inputs)          |
| **Dotted path**      | `$cond.input1`, `inputs.cond.input1`, `cond.sel`, `#{cond.input1}`                    | [Templates](#cheetah-templates); [JavaScript](#javascript-expressions); [output actions](#output-actions); [rename actions](#rename-post-job-action); API error locations |
| **Python subscript** | `cond['sel']`                                                                         | [XML output filters](#output-filters)                                                                                                                                     |
| **Bare leaf name**   | `input1`                                                                              | [Dependent parameters](#dependent-parameters) and legacy lookup fallbacks                                                                                                 |

Terms used throughout:

- **Grouping**: a section, conditional or repeat. A **test parameter** is a conditional's selector
  (`sel`); its **case** (or branch) is the `<when>` it selects.
- **Profile**: the tool's `profile` attribute, which gates legacy behavior. XML tools without one
  default to `16.01`; YAML tools default to `24.2`.
- **Legacy alias**: a second, shorter key for a pipe path, kept so references written against
  Galaxy's pre-23.1 keys still resolve (see [Pipe Paths](#pipe-paths)).
- **Mapped over**: a collection was supplied to a single-dataset input, so Galaxy runs one job per
  element. Some references resolve differently in that case.
- **Lexical scope**: a parameter's own grouping level plus the levels enclosing it, as written in
  the tool.
- **File flavor** and **modelled** YAML tools: a `.yml` file loaded from disk unvalidated, versus a
  tool posted through the API and validated by pydantic models (see [YAML](#yaml)).

Repeats are where the styles diverge the most:

| Interface            | Repeat reference                                 | Restriction                                                                  |
| -------------------- | ------------------------------------------------ | ---------------------------------------------------------------------------- |
| Pipe path            | `queries_0\|input2`                              | Mapped-over `structured_like` cannot traverse repeats                        |
| Nested state         | `queries: [{input2: …}]`                         | List position identifies the instance                                        |
| Cheetah / JavaScript | `$queries[0].input2`, `inputs.queries[0].input2` | Cheetah’s bare-name fallback does not search repeats                         |
| XML `<actions>`      | `param_attribute="first.input2.ext"`             | Only `first` traversal through the resolved value; no indexed parameter path |
| Request API errors   | `queries.0.input2`                               | Validation location, not submission syntax                                   |

Traps that fail **silently** rather than with an error, each described in detail below:

- The legacy tool API ignores nested dicts unless `input_format` is `21.01`, and ignores pipe keys
  when it is. The parameters take their defaults ([Other Accepted Forms](#other-accepted-forms)).
- A gxformat2 `in:` key written `adv/size` connects to nothing ([Format2](#format2-gxformat2)).
- An XML `change_format` `<when input="cond|sel">` never matches ([Cheetah](#cheetah-templates)).
- An XML output `<filter>` that raises still creates the output ([Output Filters](#output-filters)).
- The `format_source` legacy alias works when the job is created, but not during later dataset
  discovery ([Pipe Paths](#pipe-paths)).
- YAML output attributes such as `format_source` are not checked against the declared inputs
  ([Output Source Attributes](#output-source-attributes)).

## Tool Syntax

XML and YAML tools mostly share one set of resolvers: the YAML parser hands output attributes such
as `format_source` to the same code as XML, unchanged. The tables summarize tool features that
reference parameters. The grouping-support table describes the resolver; YAML tools are further
limited by which groupings they can declare (see [YAML](#yaml)).

In this and later tables, ✓ means the grouping is reachable, ✗ means it is not, `?` means
unverified, and n/a means not applicable.

| Feature                            | XML syntax                                                                                      | YAML syntax                                                                                                                    |
| ---------------------------------- | ----------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| Command and config templates       | Cheetah `$cond.input1` in `<command>`, `<configfile>`, `<environment_variable>`, output `label` | JavaScript `$(inputs.cond.input1.path)` in `shell_command`, `configfiles`, `arguments`; Cheetah `command:` in file flavor only |
| `format_source`, `metadata_source` | `cond\|input1`                                                                                  | same                                                                                                                           |
| `structured_like`                  | `cond\|input1`                                                                                  | same                                                                                                                           |
| `type_source`                      | `adv\|…`                                                                                        | `collection_type_source`, same                                                                                                 |
| `default_identifier_source`        | `cond\|input1`                                                                                  | same, file flavor only                                                                                                         |
| `change_format`                    | `input="cond.sel"` (Cheetah), `input_dataset="cond\|input1"`                                    | not supported                                                                                                                  |
| Output `<filter>`                  | `cond['sel']`                                                                                   | not supported                                                                                                                  |
| Output `<actions>`                 | `cond.sel`                                                                                      | not supported                                                                                                                  |
| Dependent parameters               | `data_ref="input1"`, `<options>` `<filter ref>`                                                 | `data_ref` only, file flavor only                                                                                              |
| Tool tests                         | nested elements, or `cond\|input1`                                                              | nested dicts only                                                                                                              |
| Validators, sanitizers             | none                                                                                            | none                                                                                                                           |

Grouping support and resolver restrictions:

| Feature                            | Sections               | Conditionals                       | Repeats                                      | Restrictions                                                                   |
| ---------------------------------- | ---------------------- | ---------------------------------- | -------------------------------------------- | ------------------------------------------------------------------------------ |
| Command and config templates       | ✓                      | ✓                                  | ✓ `$queries[0].input2` / `inputs.queries[0]` | Cheetah also resolves a bare `$input1` by searching every level except repeats |
| `format_source`, `metadata_source` | ✓                      | ✓                                  | ✓ `queries_0\|input2`                        | Legacy alias works only at job creation                                        |
| `structured_like`                  | ✓                      | ✓                                  | unmapped only                                | When mapped over below profile 26.0, a bare name is searched recursively       |
| `type_source`                      | ✓                      | mapped only                        | unmapped only                                | Unmapped, a path into a conditional raises `AttributeError`                    |
| `default_identifier_source`        | ✓                      | ✓                                  | `?`                                          | Exact match, no alias                                                          |
| `change_format`                    | ✓                      | ✓                                  | ✓                                            | Errors are swallowed                                                           |
| Output `<filter>`                  | ✓                      | ✓                                  | ✓                                            | Python `eval`; on error, the output is still created                           |
| Output `<actions>`                 | ✓                      | ✓                                  | ✗                                            | Dotted walk from the root                                                      |
| Dependent parameters               | own or enclosing level | own or enclosing level (not `sel`) | own or enclosing level                       | Bare leaf name in lexical scope, declared earlier                              |
| Tool tests                         | ✓                      | ✓                                  | ✓                                            | XML bare names allowed up to profile 24.1                                      |
| Validators, sanitizers             | n/a                    | n/a                                | n/a                                          | See only their own parameter's value                                           |

### Differences Between XML and YAML Tools

YAML tools are not a different reference model. Where a feature exists in both, the YAML parser
passes the reference string to the XML resolver unchanged, so the XML rules, including its legacy
fallbacks, apply. The differences come from which features and groupings YAML supports, and from
the expression language.

| Topic                                    | XML                                                                                    | YAML                                                                                                             |
| ---------------------------------------- | -------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| Groupings                                | sections, conditionals, repeats                                                        | file flavor: conditionals and repeats (`blocks:`); modelled: conditionals only; sections: neither                |
| Command language                         | Cheetah, dotted path with a bare-name fallback                                         | JavaScript dotted path over `inputs` (modelled tools require it); Cheetah `command:` in file flavor only         |
| Output attributes (`format_source`, ...) | pipe paths, checked by linters                                                         | the same pipe paths, inside a JavaScript-style tool, not validated against declared inputs                       |
| Features absent from YAML                | n/a                                                                                    | `change_format`, `<filter>`, `<actions>`, environment variables, dynamic options; `data_ref` in file flavor only |
| Test inputs                              | nested elements or flat `cond\|input1`; bare names up to profile 24.1                  | nested dicts only; flat and bare keys rejected (unless `expect_failure`)                                         |
| Default profile                          | `16.01`, so legacy behavior applies                                                    | `24.2`, so `structured_like: input1` still resolves                                                              |
| Linting of references                    | `OutputsFormatSourceReference`, `OutputsStructuredLikeReference` (no repeat awareness) | none for output attributes; modelled tools check only the first name after `inputs.`                             |

When adding a feature that references parameters, the YAML side is where the inconsistency shows:
one tool mixes `inputs.cond.input1` in its command with `cond|input1` in its outputs.

### XML

XML tools use all five styles, and the dotted path and bare leaf name styles each come in
incompatible variants:

- **Dotted path**, two variants:
  - Cheetah attribute access (`$cond.input1`), with a hidden bare-name fallback.
  - A dictionary walk from the root of the parameters (`cond.sel`), in output `<actions>`.
- **Python subscript** (`cond['sel']`), in `<filter>`.
- **Pipe path**, with `_N` repeat indexes (`cond|input1`, `queries_0|input2`). This is the
  `prefixed_name` produced by `visit_input_values`.
- **Bare leaf name**, four variants:
  - Lexical-scope lookup (`input1`), for `data_ref`, `from_dataset` and `<options>` filter `ref`s.
  - Three incompatible legacy searches: the Cheetah fallback, the one-level legacy alias for pipe
    paths, and `structured_like`'s recursive search.

The same attribute name can mean different styles. An `<options>` `<filter ref="input1">` is a bare
leaf name, while an `<actions>` `<filter ref="cond.input1">` is a dotted path.

#### Cheetah Templates

```xml
<command><![CDATA[
cat '$input' '$cond.input1' > '$out' &&
echo $adv.size $cond.sel
#for $q in $queries
  && cat '$q.input2'
#end for
]]></command>
<data name="out" format="txt" label="${tool.name} on ${on_string} (${cond.sel})">
    <change_format>
        <when input="cond.sel" value="b" format="tabular" />
    </change_format>
</data>
```

- Every template is rendered by `fill_template` against nested wrappers. Sections and conditionals
  become attributes (`$adv.size`). Repeats become lists, so use `$queries[0].input2` or `#for`.
  Nested repeats work too (`$queries[0].inner[0].input4`).
- **Bare-name fallback.** When a name is not found, `fill_template` retries with a `TreeDict`. That
  copy injects every key from nested section and conditional dicts into the top level, so `$input1`,
  `$size` and `$sel` all resolve.
  - The fallback reaches any depth, but never into repeats (`$input2` fails).
  - On a name collision, the first match in input order wins, and a top-level parameter beats a
    nested one.
- `change_format` `input` is plain Cheetah with `$` prepended. Any exception skips that `<when>`
  silently.
  - A pipe path is not interpreted as nesting: `input="cond|sel"` evaluates `$cond` followed
    by literal `|sel`, rather than the selector.
- `<configfile><inputs name="…"/>` is not a reference. It dumps the whole nested state as JSON.
- A `<configfile name="…">` defines a new template variable. It is not a reference either.

#### Pipe Paths

```xml
<data name="out1" format_source="cond|input1" metadata_source="cond|input1" />
<data name="out2" format_source="queries_0|input2" />
<collection name="c" type="list" format_source="cond|input_collection['forward']" />
```

- The reference is a key of the input dataset map, which is the pipe-joined `prefixed_name`. Repeats
  need a concrete instance index, as in `queries_0|input2`. For collections, `name[0]` or
  `name['forward']` picks a specific element.
- **Legacy alias.** Since 23.1, inputs are keyed by full path. A `LegacyUnprefixedDict` keeps the
  pre-23.1 key working as an alias. That key is the visitor's `prefix + name`, which drops **only the
  innermost section or conditional**:

  | Parameter path            | Alias                        |
  | ------------------------- | ---------------------------- |
  | `cond\|input1`            | `input1`                     |
  | `adv\|deep\|input3`       | `adv\|input3` (not `input3`) |
  | direct child of a repeat  | no shorter alias             |
  | `queries_0\|cond\|input1` | `queries_0\|input1`          |

  A real key always beats an alias. A `multiple="true"` data parameter creates numbered keys: if
  `input` were multiple, it would create `input`, `input1`, `input2` and so on, and
  `format_source="input1"` would then resolve to `input`'s first dataset instead of `cond|input1`.

- **The alias works only when the job is created** (`DefaultToolAction`). Several paths run later
  and look names up in a plain dict built from the job's input associations, which are recorded
  under full paths. Those paths accept only full paths:
  - collection `format_source` and `metadata_source` during dataset discovery
  - the late `format_source` evaluation for `expression.json` outputs
  - `MetadataSourceProvider`
- `default_identifier_source` is looked up in the mapped-over collections by exact pipe path, with
  no alias.
- The `OutputsFormatSourceReference` linter warns when an unqualified name matches a nested
  parameter. It does not model repeats, so a name inside a repeat counts as top level and passes.

<details><summary>Verification</summary>

- **Tested:** [`test_default_identifier_source_map_over`](https://github.com/galaxyproject/galaxy/blob/dev/lib/galaxy_test/api/test_tools.py) uses
  [`identifier_source.xml`](https://github.com/galaxyproject/galaxy/blob/dev/test/functional/tools/identifier_source.xml) to assert that each
  output inherits identifiers from the selected mapped-over input. Its inputs are top level;
  it does not establish repeat-path support.
- **Source-inspected:** [`_structure_for_output`](https://github.com/galaxyproject/galaxy/blob/dev/lib/galaxy/tools/execute.py) looks up
  `default_identifier_source` in `collection_info.collections` by exact key.
- **Unverified:** repeat-indexed identifier sources need the mapped execution check listed below.

</details>

#### `structured_like`

```xml
<collection name="c" type="list" structured_like="cond|input1" inherit_format="true" />
```

`structured_like` is resolved by different code depending on whether the tool is mapped over:

- **Without mapping**, `collection_prototype` looks the name up in the legacy alias dict described
  above, at any profile.
- **When mapped over**, `sliced_input_collection_structure` resolves it in one of three ways:
  - A pipe path is walked key by key through the nested state. Repeats are unreachable, because the
    state holds `queries`, not `queries_0`.
  - A bare name with profile < 26.0 triggers a recursive search through section and conditional
    dicts. The first match wins, at any depth.
  - A bare name with profile ≥ 26.0 must be top level.

So `structured_like="input3"` (deep inside `adv|deep`) works only when mapped over with an old
profile, and `queries_0|input2` works only without mapping. The `OutputsStructuredLikeReference`
linter warns on unqualified nested names. The upgrade advice `18_01_consider_structured_like` still
claims that 18.01+ tools must qualify, which contradicts the 26.0 gate in the code.

#### `type_source`

```xml
<collection name="c" type_source="adv|input_collect" />
```

Without mapping, the reference must first be a key in the legacy alias dict. Then the `|` segments
are walked down `tool.inputs`, with any trailing `_N` stripped as a repeat index. As a result:

- Sections and repeats work.
- A path into a conditional raises `AttributeError`, because `Conditional` has no `inputs`.
- A bare alias such as `input1` passes the key check but then walks to `None`.
- A real parameter name ending in `_<digit>` gets mangled by the stripping.

When mapped over, it is resolved like `structured_like`, so conditionals work and repeats do not.

#### Output Filters

```xml
<data name="out" format="txt">
    <filter>cond['sel'] == 'a' and adv['size'] &gt; 1 and len(queries) &gt; 0</filter>
</data>
```

- The filter is `eval`'d with the raw nested state as locals. Use Python subscripts. There is no
  dotted access and no bare-name fallback.
- A `KeyError` is common, for example when a parameter belongs to an inactive case. Any exception is
  logged and **the output is still created**.

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

- `<conditional name>`, `<option type="from_param" name>` and
  `<filter type="param_value|insert_column|metadata_value" ref>` all split on `.` and walk
  dictionaries from the root of the parameters.
  - Sections and conditionals work (`asection.abool`, `input_cond.input`).
  - Repeats cannot be indexed. The one exception is `from_param`'s `param_attribute`, where `first`
    selects the first element of a list (`param_attribute="first.input2.ext"`).
- `param_attribute` and `ref_attribute` are attribute chains on the resolved value, not parameter
  paths.

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

- References are **bare leaf names in lexical scope**, resolved through `ExpressionContext` chains.
  The lookup checks the parameter's own level first, then each enclosing level outward.
- At parse time, `Tool.parse_param_elem` asserts that each dependency was **already declared**.
  - You cannot reach into a sibling or child grouping: `data_ref="input1"` fails from the top level,
    and `cond.input1` and `cond|input1` fail too.
  - Forward references fail.
  - A `<when>` cannot reference its own conditional's test parameter (`sel`).
- These attributes are covered by the parse-time check: `data_ref` on `data_column` and `group_tag`,
  `from_dataset`, and the `ref` of `data_meta` and `param_value` filters.
- These are not checked at parse time and resolve leniently at runtime: `remove_value` `ref` and
  `meta_ref`, and `rules` `data_ref`.
- `<options from_parameter>` (deprecated) is an attribute path on the parameter object itself, not a
  parameter reference.

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

- Nested `<section>`, `<conditional>` and `<repeat>` elements are flattened to pipe paths. Repeated
  `<repeat>` elements are numbered `queries_0`, `queries_1`, and so on.
- The equivalent flat form `<param name="cond|input1">` / `<param name="queries_1|input2">` is
  accepted at every profile.
- Up to profile 24.1, bare leaf names (`input1`, `size`, `sel`) are also matched, by trying each
  suffix of the pipe path.
  - **Legacy behavior:** a bare `input2` given twice fills the repeat in reverse order (`queries_0` gets the
    second value), because the matcher takes the last match.
- From profile 24.2, bare names are rejected ("Invalid parameter name found") and test cases are
  validated as `test_case_xml` [tool state](tool_state.md).
  - **Profile edge case:** a profile between the two, such as `24.1.1`, gets neither: bare names are no
    longer matched, and the validation that would report them is skipped.
- Test `<output>` and `<output_collection>` names refer to outputs, not parameters.

<details><summary>Verification</summary>

- **Tested:** [`test_parameter_test_cases.py`](https://github.com/galaxyproject/galaxy/blob/dev/test/unit/tool_util/test_parameter_test_cases.py)
  includes `test_legacy_features_fail_validation_with_24_2` for the profile gate and
  `test_nested_conditional_duplicate_short_names_are_distinct_when_qualified` for qualified paths.
  These are parsing/state-conversion checks, not job executions.
- **Test tool fixtures:** the XML definitions under `test/functional/tools` supply the declared
  inputs and test cases used by these checks. An embedded test is evidence for its assertions,
  not for every reference style the tool contains.

</details>

#### Not References

- `<validator>`s and `<sanitizer>`s only see their own parameter's value.
- `<expand>` and macro tokens are textual and resolved before parsing.
- `<discover_datasets>` attributes are not parameter references.
- `<edam_*>` and `<xrefs>` are not parameter references.
- The legacy conditional `value_ref` / `value_from` (used by `upload.xml`) names a sibling parameter
  on the same level by bare name.

### YAML

YAML tools write their command in JavaScript dotted paths, but their output attributes are pipe
paths resolved by the XML code, and their tests use nested state. They also support fewer groupings
than XML: **modelled tools can load only conditionals, file-flavor tools conditionals and repeats,
and neither can load sections** (see the warning below).

Both flavors end up in the same parser, `YamlToolSource` in `galaxy.tool_util.parser.yaml`, but
they accept different input shapes:

- **File flavor**: a `.yml` tool on disk, loaded by `get_tool_source` when beta tool formats are
  enabled. `class` is optional (`GalaxyTool` or absent). The raw dict goes straight to the parser
  and nothing validates it first. This is the shape `test/functional/tools/simple_constructs.yml`
  uses: repeats nest under `blocks:`, a conditional can use a `when:` mapping, and the command can
  be a Cheetah `command:` or a JavaScript `shell_command:`.
- **Modelled**: `class: GalaxyTool` posted to `/api/dynamic_tools` (admin), or
  `class: GalaxyUserTool` posted to `/api/unprivileged_tools`. Both are validated first by the
  pydantic models in `galaxy.tool_util_models` (`YamlToolSource` and `UserToolSource` in
  `_models.py`, inputs from `yaml_parameters.py`), then dumped and handed to the same parser.
  `shell_command` (JavaScript) is required. Groupings nest under `parameters:`, and a conditional's
  cases go in a `whens:` list. Unknown keys are rejected for `GalaxyUserTool`; on `GalaxyTool`
  outputs they are accepted and then dropped.

The syntax is documented in [Authoring User-Defined Tools](user_defined_tools_authoring.md). This
section covers only how a YAML tool refers to its parameters by name.

#### Patterns

YAML tools use four of the five styles:

- **Dotted paths:** JavaScript over the runtime state (`inputs.cond.input1`,
  `inputs.queries[0].input2`) in `shell_command`, `configfiles`, `arguments` and the tool editor's
  type hints. File-flavor Cheetah `command:` uses the same wrapped namespace as XML.
- **Pipe paths:** output attributes (`format_source`, `metadata_source`, `structured_like`,
  `collection_type_source` and `default_identifier_source`) use `cond|input1` or
  `queries_0|input2`. The shared XML resolvers apply, including legacy aliases and bare-name
  fallbacks.
- **Nested state:** test `inputs`, subsequently flattened to pipe paths for the shared test-case
  code.
- **Bare leaf names:** file-flavor dependencies such as `data_ref`, resolved in lexical scope as
  in XML.

#### Running Example in YAML

The following example shows how the models represent the running example. It is illustrative
and cannot currently be loaded:

```{warning}
The parser has no `section` input type (`Unknown Galaxy parameter type section`). It also reads
repeat children from `blocks:`, which the models forbid, so a modelled repeat fails with
`KeyError: 'blocks'`. Modelled YAML tools currently support only conditionals among the groupings;
file-flavor tools support conditionals and repeats (`blocks:`). Neither supports sections.
```

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

As a file-flavor tool, the example has to drop `adv`. Its repeat looks like this:

```yaml
- name: queries
  type: repeat
  blocks:
    - name: input2
      type: data
      format: txt
```

<details><summary>Verification</summary>

- **Tested:** [`test_repeat_of_data` and `test_section_recurses`](https://github.com/galaxyproject/galaxy/blob/dev/test/unit/tool_util/test_yaml_parameters.py)
  validate authoring models and call `to_internal()`. They establish model conversion, not loading
  through `YamlToolSource`.
- **Source-inspected:** [`YamlInputSource`](https://github.com/galaxyproject/galaxy/blob/dev/lib/galaxy/tool_util/parser/yaml.py) reads repeat
  children from `blocks:`; [`_from_input_source_galaxy`](https://github.com/galaxyproject/galaxy/blob/dev/lib/galaxy/tool_util/parameters/factory.py)
  rejects an unknown leaf type such as `section`.
- **Unverified:** add a parser/loading regression test that crosses this model/parser boundary.

</details>

#### JavaScript Expressions

`shell_command`, the `content` of each `configfiles` entry, and the `arguments` that follow
`base_command` are evaluated as CWL-style expressions over an `inputs` object that mirrors the
nested state. `$(…)` holds a parameter reference or a single expression, and `${…}` holds a
function body that must return a value. When the job has a stored tool state, `inputs` is that state
converted for runtime by `runtimeify` (see [Tool State](tool_state.md)). In that object:

- A conditional is an object holding its test parameter and the active case's parameters:
  `inputs.cond.sel` and `inputs.cond.input1`. Parameters in inactive cases are absent.
- A repeat is an array of objects: `inputs.queries[1].input2.path`, or
  `inputs.queries.map((q) => q.input2.path)`. Nested repeats are nested arrays:
  `inputs.outer[0].inner[1].x`.
- A section would be an object (`inputs.adv.size`, the form the model's own examples use), but
  sections do not load today.
- A data input is a CWL `File`-like object, so `.path` is required to get a path. A collection input
  exposes its elements as `.elements`, for example `inputs.f1.elements.forward.path`.
- Dotted and bracketed property access (`inputs.cond['input1'].path`) both work. Pipe paths are not
  JavaScript and do not resolve.

```yaml
shell_command: |
  cat '$(inputs.cond.input1.path)' $(inputs.queries.map((q) => `'${q.input2.path}'`).join(" ")) > out.txt
```

Validation and runtime caveats:

- At validation time, modelled tools check only the identifier directly after `inputs.` against the
  top-level input names. `inputs.cond.input1` and `inputs.cond.nope` both pass. Aliased access such
  as `var x = inputs` is not checked.
- The tool editor types `inputs` from `/api/unprivileged_tools/runtime_model`. There a conditional
  is a `oneOf` of one object per case, keyed on the test parameter's value.
- Jobs without a stored tool state, for example jobs from the legacy run API, fall back to the
  deprecated `to_cwl` conversion. Whether that produces the same shape is unverified.
- `configfiles` always use JavaScript. A file-flavor tool that pairs Cheetah `command:` with
  `configfiles` evaluates them against a Cheetah `param_dict` that has no `inputs` key. This
  combination is untested.

<details><summary>Verification</summary>

- **Test tool fixtures:** [`simple_constructs.yml`](https://github.com/galaxyproject/galaxy/blob/dev/test/functional/tools/simple_constructs.yml)
  exercises conditional and repeat references in a JavaScript command;
  [`configfile_user_defined.yml`](https://github.com/galaxyproject/galaxy/blob/dev/test/functional/tools/configfile_user_defined.yml)
  asserts the contents produced by a JavaScript configfile paired with `shell_command`.
  Neither establishes that Cheetah `command:` works with JavaScript configfiles.
- **Source-inspected:** [`UserToolEvaluator.build_param_dict`](https://github.com/galaxyproject/galaxy/blob/dev/lib/galaxy/tools/evaluation.py)
  selects `runtimeify` when validated job state exists, otherwise `to_cwl`.
- **Unverified:** runtime-shape parity between those paths and the mixed-language configfile case
  need execution checks.

</details>

#### Output Source Attributes

`format_source`, `metadata_source`, `structured_like`, `collection_type_source` (also accepted as
`type_source`) and `default_identifier_source` reach the same `ToolOutput` and
`ToolOutputCollection` objects as their XML counterparts, and resolve the same way, legacy alias
included. See [XML](#xml) for the full rules.

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

What differs for YAML tools:

- The tool is otherwise JavaScript, but these attributes use pipe paths: write
  `format_source: cond|input1`, not `cond.input1`.
- YAML tools default to profile `24.2`, below the 26.0 gate, so a bare `structured_like: input1`
  currently works even when mapped over.
- None of these names are checked against the declared inputs, whether by the pydantic models or by
  the linters (the output linters are XML-only). A typo shows up only when the job runs.

#### Test Inputs

YAML tests write their values as nested state in the
[`test_case_json`](tool_state.md#state-representations) representation, which is validated against
the tool's parameter model:

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

- Flat `cond|input1` keys, and bare `input1` or `sel`, fail validation with `extra_forbidden`.
  - The only exception is `expect_failure: true`, which skips validation; any stray keys are then
    silently ignored.
- If the test parameter is omitted (`cond: {input1: …}`), the conditional's default case is used.
- The parser then flattens the tree to `input`, `cond|sel`, `cond|input1`, `queries_0|input2` and
  `queries_1|input2`. Nested repeats flatten to keys like `outer_0|inner_1|x`. The flat keys feed
  the same test-expansion code as XML tests.
- These tests are submitted through the tool request API, except tests with credentials, which use
  the legacy API.

#### Unsupported or File-Flavor-Only Features

- **Output `filter`, `change_format` and `actions`.** `ToolOutput.from_dict` and
  `_parse_output_collection` always set these to empty, so YAML tools cannot filter outputs or
  switch formats based on parameter values.
- **`environment_variables`.** `parse_environment_variables` returns `[]`.
- **Dynamic select options**, and with them the `<filter ref="…">` style of reference, have no YAML
  form.
- **`data_column` with `data_ref`.** File flavor only, where it works through `YamlInputSource.get`
  as in XML. The models have no `data_column` type.
- **`default_identifier_source`.** File flavor only. `GalaxyUserTool` rejects it and `GalaxyTool`
  drops it.
- **Validators** never name another parameter. File-flavor tools accept every validator type. The
  models accept only `regex`, `length`, `empty_field`, `in_range` and `no_options`.
- **Other YAML.** Workflow parameter inputs are also parsed with `YamlInputSource`, and gxformat2
  workflows can embed a `GalaxyUserTool`. Both are covered under [Workflows](#workflows).

## API

Galaxy has two job-submission APIs. The legacy tool API (`POST /api/tools`) accepts two input
shapes, chosen by the `input_format` field: pipe paths (`legacy`, the default) and nested state
(`21.01`). Each shape silently ignores the other's syntax. The tool request API (`POST /api/jobs`)
accepts only nested state, validated against the tool's pydantic request model, and rejects
anything else with a 400. Tests using the `tool_input_format` fixture exercise all three shapes
(`lib/galaxy_test/api/conftest.py`).

| Interface             | Endpoint                                                 | Parameter addressing                                                |
| --------------------- | -------------------------------------------------------- | ------------------------------------------------------------------- |
| Legacy, flat          | `POST /api/tools` (`input_format` omitted or `"legacy"`) | Pipe paths: `adv\|size`, `cond\|sel`, `queries_0\|input2`           |
| Legacy, nested        | `POST /api/tools` with `"input_format": "21.01"`         | Nested dicts and lists: `adv: {size}`, `queries: [{input2}]`        |
| Tool request          | `POST /api/jobs` (`strict` defaults to true)             | Nested dicts and lists only                                         |
| Tool request, relaxed | `POST /api/jobs` with `"strict": false`                  | Same addressing as strict requests                                  |
| Form build            | `GET`/`POST /api/tools/{id}/build`                       | Flat inputs; nested `state_inputs` and pipe-path errors in response |
| Rerun build           | `GET /api/jobs/{id}/build_for_rerun`                     | Stored state flattened to pipe paths; same response as `/build`     |

Submission values and validation:

| Submission format     | Data references                                                        | Batch wrapper                                                                       | Validation                                                                                                 |
| --------------------- | ---------------------------------------------------------------------- | ----------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| Legacy, flat          | `{"src","id"}`, bare id, `{"values": [...]}`, string encodings         | ✓ `{"batch": true, "values", "linked"}`, any parameter type                         | Nested dicts are ignored without an error; the tool form's fallback path uses this                         |
| Legacy, nested        | same as flat                                                           | ✓ same wrapper, placed in the nested position                                       | Flat `\|` keys are ignored without an error; `__current_case__` and `__index__` are overwritten or dropped |
| Tool request          | `{"src": "hda"\|"ldda"\|"dce"\|"url", ...}`; plain list for `multiple` | ✓ `{"__class__": "Batch", "values", "linked"}`, data and collection parameters only | Rejects flat keys, `__current_case__`, `__index__`, inactive-case parameters, and `"3"` for an integer     |
| Tool request, relaxed | same                                                                   | same                                                                                | Addressing is the same as strict; only null and default handling for text differs                          |

**Patterns.** In the legacy API, a key in the other shape's syntax is dropped and its parameters
take their default values. Usually the only symptom is a later "required parameter missing" error,
keyed by the pipe path (`cond|input1`). The request API never drops input silently, because its
models forbid extra fields. Batching uses a different wrapper in each API (`{"batch": true}` versus
`{"__class__": "Batch"}`), and neither API accepts the other's wrapper. Each API also names
parameters differently in its validation errors (see
[Parameter Names in Responses](#parameter-names-in-responses)). Parameter _values_ and their
validation are covered in [Tool State](tool_state.md); this section covers only how parameters are
addressed.

<details><summary>Verification</summary>

- **Tested:** [`test_multi_run_in_repeat`](https://github.com/galaxyproject/galaxy/blob/dev/lib/galaxy_test/api/test_tool_execute.py)
  submits a batch inside a repeat and asserts job/output results. Tests requesting
  [`tool_input_format`](https://github.com/galaxyproject/galaxy/blob/dev/lib/galaxy_test/api/conftest.py) are parametrized over legacy flat,
  legacy nested and request inputs; this does not extend to tests that omit the fixture.
- **Source-inspected:** [`GalaxyInteractorApi.run_tool`](https://github.com/galaxyproject/galaxy/blob/dev/lib/galaxy/tool_util/verify/interactor.py)
  appends flat job-resource keys after preparing test inputs. Request-API execution with these
  injected keys remains a verification gap.

</details>

### Legacy Tool API

`POST /api/tools` takes `tool_id`, `history_id` and `inputs`. With the default
`input_format: "legacy"`, every parameter is a single top-level key: its pipe path.

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

With `"input_format": "21.01"`, the same request is nested state. Any other `input_format` value is
a 400. (The `"request"` format in `galaxy_test.base.populators` is a test-harness name that routes
to `/api/jobs`; the server does not accept it.)

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

**Groupings**

- _Section._ Flat key `adv|size`, or nested `adv: {size}`. If the section is omitted, its
  parameters take their defaults.
- _Conditional._ The test parameter is addressed like any other parameter: `cond|sel` flat, or
  `cond: {sel}` nested. If it is omitted, the default case is used. Parameters of an inactive case
  (`cond|input1` when `sel` is `b`) are ignored.
- _Repeat, flat._ The index is part of the key (`queries_0|...`, `queries_1|...`). Indices must
  start at 0 and be contiguous: the server stops at the first missing index, so a lone
  `queries_1|input2` is dropped.
- _Repeat, nested._ A list.
- _Repeat bounds._ The two shapes handle a repeat's `min`/`max` differently. Flat input is padded
  with default instances up to the larger of `default` and `min`, and silently truncated at `max`.
  Nested input with too few or too many instances is an error.
- _Names that look like indices._ When flat keys are converted to nested state, a grouping name
  ending in `_<digits>` can be misread as a repeat index. A name ending in `_0` is always treated as
  a repeat; other digits only when the repeat list already exists. A conditional named
  `inner_options_1` needed a regression fix (`test_create_job_with_conditional_name_digit_suffix`).

**Bookkeeping keys**

- `__current_case__` and `__index__` appear in the server's _output_ state. The API ignores them on
  input. In `21.01`, a submitted `__current_case__` is recomputed and a submitted `__index__` is
  dropped.

**Data references**

- _Canonical form._ `{"src": "hda"|"ldda"|"hdca"|"dce", "id": <encoded>}`. A `values` list wraps
  several (`{"batch": false, "values": [hda1, hda2]}` for a `multiple="true"` parameter,
  `test_multidata_param`).
- _Older forms_ that are also accepted:
  - a bare encoded id, or an unencoded integer id (treated as an HDA)
  - comma-joined unencoded ids (`"12,13"`)
  - `"__collection_reduce__|<hdca id>"`
- _Collections on single-dataset parameters._ A bare `hdca` on a non-`multiple` `data` parameter is
  rejected; it must be wrapped in a batch
  (`test_hdca_rejected_for_single_data_param_in_conditional`).

**Batch (multirun)**

- _The wrapper_ is `{"batch": true, "values": [...]}`, and it can sit at any parameter's address:
  `"queries_0|input2": {...}` flat, or inside `queries: [{input2: {...}}]` nested
  (`test_multi_run_in_repeat`).
- _Linking._ Batched inputs are linked (zipped) by default. `"linked": false` makes them a cartesian
  product (`test_multirun_on_multiple_inputs_unlinked`).
- _Mapping over a collection._ A single `{"src": "hdca"|"dce", "id": ...}` in `values` maps over the
  collection. An optional `map_over_type` (for example `"paired"`) maps over subcollections.
- _Non-data parameters_ can be batched as well:
  `"num_lines": {"batch": true, "values": [1, 2, 3]}` (`test_multirun_non_data_parameter`).
- _Unwrapped values._ A wrapper-less value next to a batched one is shared by every job
  (`test_multi_run_in_repeat_mismatch`).

#### Other Accepted Forms

Beyond the two documented shapes, `/api/tools` also accepts:

- **Mixed shapes.** Without `input_format`, only the flat keys are read:
  `{"adv": {"size": 3}, "cond|sel": "a"}` reads `cond|sel` and leaves `size` at its default. With
  `21.01`, the reverse applies. Neither combination is an error.
- **String encoding.** Form-encoded posts may send `inputs` (and any other field) as a JSON string,
  which the API decorator parses. The test populators do this
  (`"inputs": "{\"cond|sel\": \"a\", ...}"`). Scalar strings such as `"adv|size": "3"` are converted
  by the parameter type.
- **Pseudo-parameters inside `inputs`.** `use_cached_job`, `rerun_remap_job_id` and
  `send_email_notification` can be sent inside `inputs` as well as at the top level. The client's
  legacy fallback sends them inside `inputs`.
- **Uploads.** `files_0|file_data` keys (sent as multipart form fields, or under `__files`) are
  merged into `inputs`.
- **Identifier helpers.** `<param>|__identifier__` keys are discarded by the server.
- **Job resources.** When job resource parameters are configured, each XML tool gets an injected
  `__job_resource` conditional. In the legacy API it is addressed flat, like any conditional:
  `"__job_resource|__job_resource__select": "yes"`, `"__job_resource|cores": 2`. Workflow and
  request state use the nested form `__job_resource: {__job_resource__select: "yes"}`. The tool test
  runner appends the flat keys even when submitting through `/api/jobs`. Whether that works is
  unverified (`?`).

### Tool Request API

`POST /api/jobs` accepts only nested state and rejects every other syntax with a 400. It validates
`inputs` against `RequestToolState` (strict) or `RelaxedRequestToolState` (`"strict": false`).
Validation happens before anything is queued, and the response is a `tool_request_id`, not jobs.

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

**Groupings.** The nesting matches `21.01`, with these differences:

- _Section._ `adv` can be omitted.
- _Conditional._ The conditional is a tagged union on the test parameter. Omitting `sel` selects the
  default case, but `"sel": null` is rejected.
- _Repeat._ A list of instance dicts.

**Rejected inputs**, each as an extra field or a type error:

- flat keys (`adv|size`, `cond|sel`)
- `__current_case__` and `__index__`
- a parameter from the inactive case (`cond: {sel: "b", input1: ...}`)
- `"3"` for an integer (`test_validation` on `gx_int`)
- the legacy `{"values": [...]}` and `{"batch": true, ...}` wrappers

**Data references**

- _Data parameters_ accept `{"src": "hda"|"ldda"|"dce", "id"}` and
  `{"src": "url", "url", "ext", ...}`.
- _`hdca`_ is accepted only by collection parameters or inside a `Batch`.
- _A `multiple` data parameter_ takes a plain list (`"f1": [hda1, hda2]`, `test_multidata_param`).

**Batch.** The wrapper is `{"__class__": "Batch", "values": [...], "linked": false?}`. It is accepted
only on `data` and `data_collection` parameters, so a batched integer is rejected. It may appear at
any depth (`test_multi_run_in_repeat`). Mapping over subcollections uses the same `map_over_type`
key as the legacy API.

**Unsupported tools.** Tools without a parameter model are rejected with "has no parameters
defined". These include the upload tools. Data-source tools (those with an `input_translator`) are
rejected when the request is processed, with a pointer to `/api/tools`.

### Tool Form, Build and Rerun

The tool form works in pipe paths and converts to nested state only when it submits through the
request API.

- **Submission.** The tool form posts to `/api/jobs` when `enable_tool_requests` (default on) and
  Celery are both enabled and the tool has a parameter model. In that case it nests the flat
  `formData` (`buildNestedState`), rewrites `{batch: true}` as `{__class__: "Batch"}`, and sends
  `strict: true`. Otherwise it posts the flat `formData` (keyed by `cond|sel`, `queries_0|input2`)
  to `/api/tools` with no `input_format`. The API tests, by contrast, run the request API with
  `strict: false`.
- **Form build.** `GET`/`POST /api/tools/{id}/build` reads `inputs` (or the query string) as legacy
  flat state. The response contains:
  - `inputs`: the form tree, with repeat instances under `cache[i]` and case inputs under
    `cases[i].inputs`
  - `state_inputs`: nested state carrying `__current_case__` and `__index__`
  - `errors`: keyed by pipe paths

  `options_pagination` is also keyed by pipe paths (`cond|input1`, `queries_0|input2`).

- **Rerun.** `GET /api/jobs/{id}/build_for_rerun` loads the job's stored nested state, flattens it
  back to pipe paths (`queries_<__index__>|input2`), and returns the same model as `/build`.

### Parameter Names in Responses

Each API reports a bad parameter under a different name:

| Source                                       | Example key for a bad `size` / bad `sel`        | Format                                                                                                                                                                          |
| -------------------------------------------- | ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Legacy, flat (`err_data`, `param_errors`)    | `adv\|size`, `cond\|sel`                        | Pipe path, matching the input key                                                                                                                                               |
| Legacy, `21.01` (`err_data`)                 | `adv` → stringified `{'size': ...}`; `sel`      | Errors are nested under the group name, but conditional test parameter errors are keyed by the bare name at the parent level (not `cond`), and the nested dicts are stringified |
| `/build` (`errors`)                          | `adv\|size`, `cond\|sel`                        | Pipe path (always parsed as legacy)                                                                                                                                             |
| Tool request (`err_msg` only, no `err_data`) | `adv.size`, `cond.a.input1`, `queries.0.input2` | Pydantic location as a dotted path, with the conditional's _case value_ inserted as a path segment                                                                              |

## Workflows

Workflows reference a tool step's parameters in two styles. Connections and every API keyed by input
name use **pipe paths** (`cond|input1`, `queries_0|input2`). Stored and authored tool state, and
`when` expressions, use **nested state**. Two outliers use other separators: rename post-job
actions use a dotted path because `|` is already taken there, and gxformat2 keeps `/` for
`step/output` sources, never for parameter paths.

**Connections and state**

| Feature                     | Parameter syntax                                            | Restrictions                                                                                                      |
| --------------------------- | ----------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| Step connections            | Pipe path (`cond\|input1`, `queries_0\|input2`)             | Repeat indexes are part of the key: `a_0\|b_1\|x`; nested-repeat augmentation is untested                         |
| Step input defaults         | Pipe path (`cond\|input1`, `queries_0\|input2`)             | `{"default": ...}` per pipe path                                                                                  |
| Stored tool state           | nested JSON                                                 | Carries `__current_case__` and `__index__`; `.ga` stores a JSON string, editor encodes each top-level value again |
| Connected / runtime markers | Nested `{"__class__": "ConnectedValue"}` / `"RuntimeValue"` | `RuntimeValue` is rejected by the `workflow_step*` models                                                         |
| Legacy step `inputs` list   | top-level name only                                         | Top-level runtime parameters only; repeats unsupported; core code does not use this list                          |
| Format2 `in:`               | Pipe path (`cond\|input1`, `queries_0\|input2`)             | `adv/size` isn't translated and silently matches nothing                                                          |
| Format2 `state:` + `$link`  | nested YAML, no markers                                     | `$link` creates a `ConnectedValue` and a pipe-path connection; no bookkeeping markers required                    |
| Format2 `tool_state:`       | native nested state, markers kept                           | export default when no state encoder is configured                                                                |
| Format2 `runtime_inputs:`   | top-level only                                              | Top-level only; `cond\|sel` becomes a literal top-level key                                                       |

**Execution and invocation**

| Feature                       | Parameter syntax                           | Restrictions                                                                                |
| ----------------------------- | ------------------------------------------ | ------------------------------------------------------------------------------------------- |
| `when` expression             | dotted path over nested state, or brackets | Extra inputs remain flat (`inputs.when`); pipe-path aliases for tool inputs removed in 26.2 |
| Invocation `parameters`       | step key → nested dict or pipe paths       | Repeats require pipe paths; run form uses `parameters_normalized: true`                     |
| Subworkflow `parameters`      | `"<inner order_index>\|<pipe path>"`       | Requires `parameters_normalized`; one subworkflow level deep                                |
| Subworkflow connections       | inner input step **label**                 | unlabelled: `"<order_index>:<name>"`; no character checks on labels                         |
| `replacement_params` / `${x}` | free name, not a path                      | server substitutes only into rename `newname`                                               |
| Rename PJA `#{...}`           | dotted path, `.` → `\|`                    | Data inputs only; repeat syntax `#{queries_0.input2}`; bare names match by suffix           |

**Editor and refactor**

| Feature          | Parameter syntax                                | Restrictions                                                        |
| ---------------- | ----------------------------------------------- | ------------------------------------------------------------------- |
| Editor terminals | Pipe path (`cond\|input1`, `queries_0\|input2`) | labels add only `Query 1 > `; sections and conditionals add nothing |
| Editor tool form | Pipe path (`cond\|input1`, `queries_0\|input2`) | the server nests them with `populate_state`                         |
| Refactor API     | Pipe path (`cond\|input1`, `queries_0\|input2`) | documented in the schema as `'cond\|repeat_0\|input'`               |

**Patterns.** The pipe path is what `visit_input_values` produces as `prefixed_name`. The nested
shape matches the tool's own state. Native state carries `__current_case__` and `__index__`.
Format2 `state:` and the `workflow_step*` models in `galaxy.tool_util.parameters` leave them out,
and those models reject both markers and pipe-path keys. Conversions are spread across several
helpers and call sites:

- Nested to flat: gxformat2 `$link` and `_flatten_step_params` (invocation `parameters`).
- Flat to nested: `populate_state` (the editor tool form), `visit_input_values` matching pipe paths
  against existing state (runtime overrides), and a one-off repeat-growing hack for connections.

See [Tool State](tool_state.md) for the `workflow_step` and `workflow_step_linked` representations.

### Native `.ga`

A native workflow keys connections by pipe path and stores state as nested JSON:

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
- A connection key starting with `<repeat>_N|...` makes Galaxy grow the repeat to N+1 instances on load
  (`augment_tool_state_for_input_connections`). Connections to nested repeats are untested.
- A connection that matches no input is ignored with only a logged warning ("Failed to use input
  connections").
- `tool_state` encodings differ by consumer. The DB and `.ga` export hold one JSON string of the
  nested dict. The editor payload (`_workflow_to_dict_editor`) uses
  `params_to_strings(nested=False)`, so each top-level value is itself a JSON string. Older `.ga`
  files are double-encoded the same way, and `safe_loads` on import accepts either.
- `post_job_actions` keys are `action_type + output_name`. Arguments name outputs, never parameters,
  except for the [rename syntax](#rename-post-job-action).

<details><summary>Verification</summary>

- **Tested:** [`test_nested_key_to_path`](https://github.com/galaxyproject/galaxy/blob/dev/test/unit/app/tools/test_parameter_parsing.py)
  checks conversion of a nested-repeat pipe path into dictionary keys and list indexes. It does
  not test creating repeat instances or connecting a workflow.
- **Tested:** [`test_inputs_to_steps`](https://github.com/galaxyproject/galaxy/blob/dev/lib/galaxy_test/api/test_workflows_from_yaml.py)
  invokes a workflow with a top-level repeat connection. It does not cover nested-repeat
  augmentation.
- **Source-inspected:** [`augment_tool_state_for_input_connections`](https://github.com/galaxyproject/galaxy/blob/dev/lib/galaxy/workflow/modules.py)
  begins with a repeat prefix and looks up that repeat in root tool inputs. Its nested-repeat
  branch is explicitly marked untested.

</details>

### Format2 (gxformat2)

gxformat2 uses pipe paths in `in:` and nested state in `state:`:

```yaml
steps:
  example:
    tool_id: example
    in:
      input: i # pipe paths; values are "step_label/output"
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
- Galaxy imports through `gxformat2.python_to_workflow` (`managers/workflows.py`). Export without
  a state encoder writes `tool_state:` verbatim, markers included.

### `when` Expressions

A `when` expression reads tool parameters as dotted paths over nested state, but non-tool
connections by their flat connection name:

```yaml
in:
  cond|input1: j
  when: should_run # not a tool parameter
when: $(inputs.when && inputs.cond.input1 !== null && inputs.queries[0].input2 !== null)
```

- `inputs` is the step's execution state passed through `to_cwl`. Nesting follows tool state,
  `__current_case__` and `__index__` included (unlike `runtimeify` for YAML tools). Data becomes
  CWL `File` objects.
- Connections that are not tool parameters go into `extra_step_state` under their **flat**
  connection name (`inputs.when`, or `inputs["cond|bogus"]` when a pipe path matches no active
  parameter).
- Since 26.2, connected nested tool parameters are no longer _also_ exposed under their pipe path
  (`!("cond|more_text" in inputs)`).
- `${inputs.when}` is rewritten to `$(inputs.when)`, as a fallback for workflows defined on 23.0.
- When the editor and the tool-upgrade refactor decide whether a non-tool connection is a `when`
  input, they use a plain substring test on the expression text (`when.includes(name)` /
  `"inputs.<name>" in when`).

### Workflow Editor

The editor never parses parameter names; it uses the server's pipe paths as opaque terminal names.

- Terminal names are the server-provided `step.inputs[].name`, which are `prefixed_name`s.
  `stepToConnections` pairs `input_connections` keys with those names.
- Non-data parameters get terminals only when their state value is `ConnectedValue`.
  `FormElement.vue` sets that value under the pipe-path form key, and `build_module` turns the flat
  form into nested state.
- Untyped `${x}` parameters are found by scanning `config_form` values and PJA arguments
  (`modules/parameters.ts`). Lint messages refer to inputs by pipe path.

### Invocation API and Run Form

The invocation API addresses input steps by step key and tool parameters by pipe path, with nested
dicts flattened on the way in:

```json
{
  "inputs": { "0": { "src": "hda", "id": "..." } },
  "inputs_by": "step_index|step_uuid",
  "parameters": {
    "3": {
      "adv": { "size": 5 },
      "cond|sel": "a",
      "queries_0|input2": { "src": "hda", "id": "..." }
    }
  },
  "replacement_params": { "suffix": "final" }
}
```

- `inputs` and `inputs_by` address workflow _input steps_ (`step_id`, `step_index`, `step_uuid` or
  `name`, meaning the label). They never address tool parameters.
- `parameters` keys can be an order index, a uuid, a tool id (legacy) or the DB step id with
  `legacy`. Legacy `{"param": NAME, "value": V}` is still accepted.
- Nested dicts in `parameters` are flattened to pipe paths. Lists are not flattened, so repeats must
  be written as pipe paths (`queries_0|...`), and only instances already in the step state are
  visited.
- For a subworkflow step, use `parameters_normalized: true` and keys like `"1|num_lines"` or
  `"1|cond|sel"`, where `1` is the inner order index. The split is on the first `|` only.
- `${x}` in tool _text values_ is substituted by the client run form (`getReplacements`). On the
  server, `replacement_params` reach only the rename `newname` (`${x}`). API callers submitting tool
  state must substitute it themselves.

### Rename Post-Job Action

`#{name | op | op}` takes the name of a data input. Because `|` separates the filter operations
(`basename`, `upper`, `lower`), nesting is written as a dotted path (`#{cond.input1}`,
`#{queries_0.input2}`) and converted to a pipe path before matching job input names. If nothing
matches exactly, the first pipe path whose text ends with the bare name is used (`#{input1}`). This
is a raw string suffix match, so `#{input1}` can also match `cond|xinput1`.

### Refactor API

`connect`, `disconnect` and `extract_input` take `input: {label | order_index, input_name}` with a
pipe-path `input_name`. Upgrade and fill-defaults messages report `input_name` the same way. The
schema documents the format as `'cond|repeat_0|input'`. `extract_untyped_parameter` rewrites
`${name}` in rename PJAs and connects, by its pipe path, every tool input whose value is exactly
`${name}`.

## Verification Gaps

Verification notes use **Tested** for behavior asserted by a named regression test,
**Source-inspected** for behavior inferred from the implementation, and **Unverified** for an
unsettled outcome. They describe the evidence available in the repository, not a claim that every
listed test was run for this documentation change. Test-tool fixtures provide executable examples;
model validation, parser/loading checks and job execution establish different things.

These are focused checks within this reference's existing scope. Close a gap by adding or locating
a test that asserts the outcome, then update the relevant claim and verification note.

| Behavior                                    | Check needed to close the gap                                                                                                                                                      | Test level                          |
| ------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------- |
| Repeat-indexed `default_identifier_source`  | Map over `queries_0\|input2` and assert output element identifiers; also assert the behavior for an unmatched source                                                               | API execution with an XML test tool |
| Modelled YAML groupings                     | Pass section and repeat definitions through model validation and actual tool loading; assert the parser/model mismatch, then update the compatibility warning if support changes   | Parser/loading regression           |
| Legacy YAML runtime state                   | Execute the same conditional/repeat file-flavor tool through legacy and request submission; assert the values and paths exposed to JavaScript                                      | API execution with a YAML test tool |
| Cheetah command with JavaScript configfiles | Load a file-flavor tool combining `command:` and a configfile that reads `inputs`; assert the resulting content or explicit failure                                                | Tool execution                      |
| Job resources through `/api/jobs`           | Configure injected resource inputs and submit a tool test with resource overrides through the request API; assert both acceptance and the applied values                           | Integration/API execution           |
| Workflow repeat augmentation                | Import and invoke connections to nested repeats and repeats beneath sections/conditionals, starting without the required instances; distinguish path lookup from instance creation | Workflow API execution              |
