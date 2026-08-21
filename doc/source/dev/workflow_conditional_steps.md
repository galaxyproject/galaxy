# Conditional Workflow Steps

A workflow step may carry a `when` expression. Galaxy evaluates it before the step runs;
if it evaluates false, the step is skipped and produces no outputs. This document covers
what the expression can read, the two ways to decide whether a step should run, and what
to do with the outputs of a step that might not run.

## What a `when` expression can read

The `when` condition is a `$(...)` expression evaluated with an `inputs` object in scope.
`inputs` carries the step's tool state together with anything else connected to the step,
so an expression can read:

- **Tool parameters**, connected or not, in their tool-state shape. A parameter nested
  inside a `<conditional>` is addressed as `inputs.cond.param` or
  `inputs["cond"]["param"]`. Galaxy names the _connection_ with a flat, pipe-prefixed
  name (`cond|param`), but that spelling is not exposed to the expression.
- **Data inputs.** A connected dataset appears as an object with its metadata, so
  `$(inputs.reference.format != "bwa_mem2_index")` is a valid condition.
- **Extra connections** that are not tool parameters at all. Connecting an output to a
  name the tool does not define makes that value available to the expression and nothing
  else. This is how the `when` boolean convention works, and it generalizes.

## Running based on a boolean parameter

The common form, and the one the workflow editor writes when you pick _Run when a
boolean parameter is true_:

```yaml
steps:
  trim:
    tool_id: trimmomatic
    in:
      input: reads
      when: run_trimming
    when: $(inputs.when)
```

`run_trimming` is a boolean workflow input. `when` is not a Trimmomatic parameter — it is
an extra connection that exists only to be read by the expression.

## Running when an input is provided

A workflow input declared `optional: true` may be connected to a _required_ tool data
parameter, as long as the step runs only when that input is present:

```yaml
inputs:
  mapped: data
  primer_scheme:
    type: data
    optional: true
steps:
  trim:
    tool_id: ivar_trim
    in:
      input_bam: mapped
      primer|input_bed: primer_scheme
    when: $(inputs.primer.input_bed !== null)
```

When the dataset is supplied the step runs normally. When it is omitted the condition
evaluates false and the step is skipped, so the tool never sees a missing required
parameter.

Without this condition the workflow fails: an omitted optional input is not implicitly
skipped, it reaches parameter validation as null and the job errors. The skip comes from
the expression and nothing else.

The workflow editor writes this expression for you. Choose _Run when an input is
provided_ on the step, or drop an optional output onto a required input and accept the
offer to run the step only when the input is provided.

For a parameter inside a `<repeat>`, the expression follows the list structure of the
step's state. For example, the connection `queries_0|input2` is addressed as
`inputs.queries[0].input2`. The workflow editor resolves this structure and writes the
indexed expression for you.

## Continue after a conditional step

A conditional step's outputs are optional because the step might be skipped. Galaxy
cannot connect such an output directly to a required downstream input: when the condition
is false, there is no value for the downstream step to consume.

Place a Pick Value step immediately after the conditional step to select its output when
present and a fallback otherwise:

```yaml
merge:
  type: pick_value
  in:
    input_0: trim/output_bam
    input_1: mapped
  state:
    mode: first_non_null
```

`pick_value` takes the first input that is not null, so the workflow continues with the
trimmed data when trimming ran and with the untrimmed data when it did not. Everything
downstream of `merge` sees an ordinary required dataset.

Two spellings exist. `type: pick_value` is the native workflow module described here; it
has an editor palette entry and a step form. Many published workflows instead use the
tool shed tool `iuc/pick_value`, which does the same job and reads the same way in a
workflow file. Prefer the module for new work.

## Running a tool in two different shapes

Tool state is fixed per step, so a tool that must run with a reference in one case and
without it in the other needs two steps with complementary conditions. An extra connection
carries the dataset into both expressions, including the branch that does not consume it:

```yaml
with_ref:
  tool_id: some_tool
  in:
    ref: maybe_reference
    probe: maybe_reference
  when: $(inputs.probe !== null)
without_ref:
  tool_id: some_tool
  in:
    probe: maybe_reference
  when: $(inputs.probe === null)
merged:
  type: pick_value
  in:
    input_0: with_ref/out
    input_1: without_ref/out
  state:
    mode: first_non_null
```

Exactly one of the two runs, and `pick_value` picks up whichever did.

## Deleting an input used by a condition

An expression that reads a connection which no longer exists fails quietly: on a tool
parameter the state key survives as null, so the step is skipped on every run, and on an
extra connection the evaluation raises. The workflow editor's best-practices panel
reports it, so a condition that refers to a deleted connection does not go unnoticed.
