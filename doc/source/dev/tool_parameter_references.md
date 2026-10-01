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

<!-- TODO: one summary table across tool syntax and APIs -->

## Tool Syntax

### XML

<!-- TODO -->

### YAML

<!-- TODO -->

### Differences Between XML and YAML Tools

<!-- TODO -->

## API

### Legacy Tool API

<!-- TODO -->

### Tool Request API

<!-- TODO -->

### Forms of the Legacy API

<!-- TODO -->

## Workflows

<!-- TODO: step input connections, stored tool_state, `when` expressions -->
