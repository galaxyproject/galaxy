# Workflow CLI Tooling

```{note}
**New to Galaxy workflows?** Start with the [Planemo workflow documentation](https://planemo.readthedocs.io/en/latest/best_practices_workflows.html) — it covers best practices, testing, running, and publishing workflows with a beginner-friendly walkthrough.
```

Galaxy's workflow CLI tooling spans three packages at different abstraction levels. This document covers the **schema-aware** tools in `galaxy-tool-util` and how they relate to both the higher-level Planemo commands and the lower-level gxformat2 utilities.

## Quick Reference

| Command                      | Package          | What It Does                                                 |
| ---------------------------- | ---------------- | ------------------------------------------------------------ |
| `planemo workflow_lint`      | planemo          | Best-practice checks (labels, annotations, outputs, tests)   |
| `planemo run`                | planemo          | Execute workflow via CLI with full Galaxy orchestration      |
| `planemo workflow_test_init` | planemo          | Stub out test YAML from scratch or from an invocation        |
| `planemo autoupdate`         | planemo          | Update tool versions in a workflow                           |
| `gxwf validate`              | galaxy-tool-util | Validate tool_state against tool definitions                 |
| `gxwf clean`                 | galaxy-tool-util | Strip stale/obsolete tool_state keys                         |
| `gxwf roundtrip`             | galaxy-tool-util | Prove native↔Format2 round-trip equivalence                 |
| `gxwf lint`                  | galaxy-tool-util | Structural lint + tool state validation                      |
| `gxwf convert`               | galaxy-tool-util | Convert between .ga and .gxwf.yml (auto-detects direction)   |
| `gxwf validate-tree`         | galaxy-tool-util | Validate all workflows under a directory tree                |
| `gxwf validate-tests`        | galaxy-tool-util | Validate a workflow-tests YAML file against the Tests schema |
| `gxwf validate-tests-tree`   | galaxy-tool-util | Validate all workflow-tests YAML files in a directory tree   |
| `gxwf clean-tree`            | galaxy-tool-util | Strip stale state from all workflows in a directory tree     |
| `gxwf roundtrip-tree`        | galaxy-tool-util | Round-trip validate all workflows in a directory             |
| `gxwf lint-tree`             | galaxy-tool-util | Lint all workflows in a directory                            |
| `gxwf convert-tree`          | galaxy-tool-util | Batch convert workflows in a directory                       |
| `gxwf viz`                   | galaxy-tool-util | Interactive Cytoscape graph (requires gxformat2)             |
| `gxwf abstract-export`       | galaxy-tool-util | Abstract CWL export (requires gxformat2)                     |
| `gxwf mermaid`               | galaxy-tool-util | Mermaid diagram (requires gxformat2)                         |
| `galaxy-tool-cache`          | galaxy-tool-util | Manage local ToolShed tool metadata cache                    |
| `gxwf-lint`                  | gxformat2        | Structural/syntax validation (no tool defs)                  |
| `gxwf-to-native`             | gxformat2        | Format2→native conversion (no schema awareness)              |
| `gxwf-to-format2`            | gxformat2        | Native→Format2 conversion (no schema awareness)              |
| `gxwf-viz`                   | gxformat2        | Cytoscape graph visualization                                |
| `gxwf-abstract-export`       | gxformat2        | Abstract CWL export                                          |

Each `gxwf` subcommand is also available as a standalone binary (`gxwf-state-validate`, `gxwf-state-clean`, `gxwf-roundtrip-validate`, `gxwf-lint-stateful`, `gxwf-to-format2-stateful`, `gxwf-to-native-stateful`). The `gxwf` unified interface is preferred.

## Part 1: Using the Tools

### Tool Cache Setup

All schema-aware operations need tool definitions. The `galaxy-tool-cache` command fetches `ParsedTool` metadata from ToolShed 2.0 and caches it locally.

```bash
# Cache all tools referenced by a workflow
galaxy-tool-cache populate-workflow my-workflow.ga

# Cache all tools from every workflow in a directory
galaxy-tool-cache populate-workflow ./iwc/workflows/

# Cache a single tool by ToolShed ID
galaxy-tool-cache add toolshed.g2.bx.psu.edu/repos/devteam/fastqc/fastqc/0.74+galaxy0

# Cache from a local tool XML
galaxy-tool-cache add-local path/to/tool.xml

# Inspect the cache
galaxy-tool-cache list
galaxy-tool-cache list --json
galaxy-tool-cache info fastqc              # TRS ID or substring match

# Clear cache
galaxy-tool-cache clear                    # everything
galaxy-tool-cache clear toolshed.g2.bx.psu  # by prefix
```

Cache defaults to `$GALAXY_TOOL_CACHE_DIR` or `~/.galaxy/tool_info_cache/`.

All schema-aware commands share these common flags:

- `--populate-cache` — auto-populate tool cache from the target workflow before running
- `--tool-source {shed,galaxy,auto}` — where to fetch tool definitions (default: `shed` for ToolShed 2.0 API, `galaxy` for a Galaxy instance, `auto` to try both)
- `--galaxy-url URL` — Galaxy instance URL when using `--tool-source galaxy` (default: `$GALAXY_URL` or `https://usegalaxy.org`)
- `--tool-source-cache-dir DIR` — override cache directory
- `-v, --verbose` — enable debug logging

### Validating Workflows

Validation operates at three levels of depth:

**Structural lint** — checks metadata completeness, no tool definitions needed:

```bash
planemo workflow_lint my-workflow.ga          # best-practice checks
gxwf-lint my-workflow.ga                     # structural syntax check
```

See the [Planemo best practices docs](https://planemo.readthedocs.io/en/latest/best_practices_workflows.html) for what `workflow_lint` checks: annotations, creators, licenses, labeled inputs/outputs, connected steps, test file validity.

**Combined lint** — structural lint plus tool state validation in one pass:

```bash
# Full lint: structural checks + tool state validation
gxwf lint --populate-cache my-workflow.ga

# Skip best practice checks (annotation, creator, license)
gxwf lint --skip-best-practices my-workflow.ga

# With connection type validation
gxwf lint --connections my-workflow.ga

# Strict: treat missing tool defs as failures
gxwf lint --strict my-workflow.ga

# Structured output
gxwf lint --report-json report.json my-workflow.ga
gxwf lint --report-markdown report.md my-workflow.ga
```

Runs gxformat2's full structural lint pipeline (format validation, pydantic schema checks, best practices) followed by per-step tool state validation. Output groups results under "Structural Lint" and "State Validation" headers. Exit codes: 0 = clean, 1 = errors/failures, 2 = skips (with `--strict`).

**Schema-aware validation** — type-checks every parameter against the tool definition:

```bash
# Single file (auto-detects native vs Format2)
gxwf validate my-workflow.ga
gxwf validate my-workflow.gxwf.yml

# Entire directory tree
gxwf validate-tree ./workflows/

# Auto-fetch tool defs, strict mode (skips = failures)
gxwf validate-tree --populate-cache --strict ./workflows/

# Structured output
gxwf validate --report-json report.json my-workflow.ga
gxwf validate --report-markdown report.md my-workflow.ga
gxwf validate-tree --summary ./workflows/
```

Validates parameter names, types (integers, floats, selects against declared options, booleans, data columns), conditional branch consistency, and connection completeness. Recurses into subworkflows. Use `--connections` to also validate inter-step connection type compatibility. Exit codes: 0 = pass, 1 = failures, 2 = skips (with `--strict`).

**Validating workflow-test files** — schema-checks `*-tests.yml` / `*.gxwf-tests.yml` against `galaxy.tool_util_models.Tests` (job block, File/Collection discriminators, assertions). Schema-only; no tool cache required.

```bash
gxwf validate-tests my-workflow-tests.yml
gxwf validate-tests-tree ./workflows/
gxwf validate-tests --report-json report.json my-workflow-tests.yml
```

Exit codes: 0 = valid, 1 = schema errors, 2 = load/parse error.

**Round-trip equivalence** — proves a workflow survives native→Format2→native without data loss:

```bash
gxwf roundtrip my-workflow.ga

# Write intermediate artifacts for inspection
gxwf roundtrip \
  --output-format2 intermediate.gxwf.yml \
  --output-native roundtripped.ga \
  my-workflow.ga

# Strip bookkeeping keys before comparison
gxwf roundtrip --strip-bookkeeping my-workflow.ga

# Strict: treat benign diffs (dropped empty repeats, all-None sections) as errors
gxwf roundtrip --strict my-workflow.ga

# Sweep a directory
gxwf roundtrip-tree --populate-cache ./workflows/
```

Diffs are classified by severity — **error** (real data loss) vs **benign** (known representation artifacts like empty repeats dropped by Format2, all-None sections omitted, multiple-select scalar→list normalization).

### Cleaning Workflows

**Stale state removal** — strips tool_state keys left behind by tool upgrades:

```bash
# Dry run (default) — shows what would be removed
gxwf clean --populate-cache my-workflow.ga

# Show unified diff
gxwf clean --diff my-workflow.ga

# Write cleaned file in-place
gxwf clean --output-template "{path}" my-workflow.ga

# Write adjacent file
gxwf clean \
  --output-template "{dir}/{stem}.cleaned{ext}" \
  my-workflow.ga

# Sweep a directory in-place
gxwf clean-tree \
  --populate-cache --output-template "{path}" \
  ./workflows/

# Structured output
gxwf clean --report-json report.json my-workflow.ga
gxwf clean --report-markdown report.md my-workflow.ga
```

Stale keys are classified into categories that can be individually controlled:

| Category            | Meaning                               | Example                                  |
| ------------------- | ------------------------------------- | ---------------------------------------- |
| `bookkeeping`       | Framework-managed keys                | `__current_case__`, `__page__`           |
| `stale-root-keys`   | Conditional params leaked to parent   | Parameter from old conditional structure |
| `stale-branch-data` | Data from inactive conditional branch | Values from a branch no longer selected  |
| `runtime-leak`      | Execution artifacts                   | `__workflow_invocation_uuid__`           |
| `unknown`           | Catch-all                             | Tool upgrade residue                     |

Use `--preserve`/`--strip` (cleaning) or `--allow`/`--deny` (validation/export) to control policy per category.

**Tool version updates** — Planemo handles this:

```bash
planemo autoupdate my-workflow.ga
```

See [Planemo automating workflows](https://planemo.readthedocs.io/en/latest/automating_workflows.html) for full details.

### Converting and Exporting Workflows

**Schema-aware conversion** — `gxwf convert` auto-detects direction from the input file extension (`.ga` → format2, `.gxwf.yml` → native) and uses tool definitions for correct type encoding:

```bash
# .ga → format2 (auto-detected), output to stdout
gxwf convert --populate-cache my-workflow.ga

# .gxwf.yml → native (auto-detected), output to file
gxwf convert -o my-workflow.ga my-workflow.gxwf.yml

# Override direction explicitly
gxwf convert --to format2 my-workflow.ga
gxwf convert --to native my-workflow.gxwf.yml

# format2 output options (ignored when converting to native)
gxwf convert --compact my-workflow.ga      # strip positions
gxwf convert --json my-workflow.ga        # JSON instead of YAML

# Strict: fail if any step can't be converted
gxwf convert --strict my-workflow.ga

# Batch convert a directory (--to required)
gxwf convert-tree --to format2 --output-dir ./format2/ ./workflows/
gxwf convert-tree --to native  --output-dir ./native/  ./workflows/
```

Stale key policy (`--allow`/`--deny`) applies during format2 export — same categories as validation.

**Structural format conversion** — no tool definitions, no state decoding:

```bash
gxwf-to-native my-workflow.gxwf.yml output.ga     # Format2 → native
gxwf-to-format2 my-workflow.ga output.gxwf.yml     # native → Format2 (emits tool_state, not state)
gxwf-to-format2 my-workflow.ga -o out.gxwf.yml     # -o is equivalent to positional output
gxwf-to-format2 my-workflow.ga --json              # JSON output to stdout
gxwf-to-format2 --compact my-workflow.ga            # strip positions
```

Both commands share `--compact`, `--json`, and `-o` flags. The key difference: `gxwf convert` (schema-aware) produces proper `state` dicts by consulting tool definitions to decode double-encoded JSON strings. `gxwf-to-format2` copies the raw `tool_state` strings as-is since it has no tool schema.

### Visualization and Abstract Export

These subcommands are pass-throughs to the corresponding gxformat2 binaries (require gxformat2 installed):

```bash
gxwf viz my-workflow.ga graph.html          # interactive Cytoscape HTML
gxwf viz my-workflow.ga graph.json          # Cytoscape JSON for desktop
gxwf abstract-export my-workflow.ga out.cwl # abstract CWL (non-executable)
gxwf mermaid my-workflow.ga                 # Mermaid diagram
```

All arguments after the subcommand are forwarded verbatim to the underlying gxformat2 binary. See the [gxformat2 CLI docs](https://gxformat2.readthedocs.io/en/latest/cli.html) for details.

### Running and Testing Workflows

Execution and testing are Planemo's domain:

```bash
planemo run my-workflow.ga job.yml                      # run workflow
planemo workflow_job_init my-workflow.ga                 # create job template
planemo workflow_test_init my-workflow.ga                # stub out tests
planemo workflow_test_init --from_invocation <ID> \
  --galaxy_url <URL> --galaxy_user_key <KEY>            # tests from invocation
planemo test my-workflow.ga                              # run tests
```

See [Running Galaxy workflows](https://planemo.readthedocs.io/en/latest/running.html) and [Automating Galaxy workflows](https://planemo.readthedocs.io/en/latest/automating_workflows.html).

### Common Pipelines

**Validate and clean an IWC-style repository:**

```bash
# 1. Cache all tools
galaxy-tool-cache populate-workflow ./workflows/

# 2. Validate everything
gxwf validate-tree --summary ./workflows/

# 3. Clean stale state in-place
gxwf clean-tree --output-template "{path}" ./workflows/

# 4. Verify round-trip safety
gxwf roundtrip-tree ./workflows/
```

**Export a workflow to Format2 with full verification:**

```bash
# 1. Validate the source
gxwf validate --populate-cache my-workflow.ga

# 2. Export with schema-aware conversion
gxwf convert -o my-workflow.gxwf.yml my-workflow.ga

# 3. Validate the exported Format2
gxwf validate my-workflow.gxwf.yml

# 4. Prove round-trip equivalence
gxwf roundtrip \
  --output-format2 /dev/null \
  my-workflow.ga
```

## Part 2: Developing Workflow CLI Tools

### Architecture

Workflow CLI tooling is split across three packages, each with a distinct scope. New functionality should go in the package whose scope it fits — if it needs tool definitions, it belongs in `galaxy-tool-util`; if it's structural, it belongs in `gxformat2`; if it's user-facing orchestration, it belongs in `planemo`.

```
┌─────────────────────────────────────────────────────────────────────┐
│                          planemo                                    │
│  Polished UX · Galaxy server orchestration · opinionated defaults   │
│                                                                     │
│  workflow_lint  run  test  autoupdate  workflow_test_init           │
│  workflow_job_init  dockstore_init                                  │
├─────────────────────────────────────────────────────────────────────┤
│                      galaxy-tool-util                               │
│  Schema-aware · uses ParsedTool from ToolShed 2.0 · no runtime     │
│                                                                     │
│  gxwf <subcommand>                                                    │
│    validate · clean · lint · roundtrip · convert                    │
│    validate-tree · clean-tree · lint-tree · roundtrip-tree          │
│    convert-tree · viz · abstract-export · mermaid                   │
│  galaxy-tool-cache                                                   │
│                                                                     │
│  Protocols: GetToolInfo · ToolInputs                               │
│  Infrastructure: _walker.py · Pydantic parameter models             │
├─────────────────────────────────────────────────────────────────────┤
│                        gxformat2                                    │
│  Structural · no tool definitions · format conversion               │
│                                                                     │
│  gxwf-lint  gxwf-to-native  gxwf-to-format2  gxwf-viz             │
│  gxwf-abstract-export  gxwf-mermaid                                 │
│                                                                     │
│  ConversionOptions callbacks:                                       │
│    state_encode_to_format2 · state_encode_to_native                 │
└─────────────────────────────────────────────────────────────────────┘
```

The key architectural insight: **gxformat2's `ConversionOptions` defines callback slots** (`state_encode_to_format2`, `state_encode_to_native`) that `galaxy-tool-util` fills with schema-aware implementations. This lets gxformat2 remain dependency-free while gaining schema awareness when tool definitions are available.

### Where to Put New Functionality

| If the feature...                                                | Put it in...                                         | Why                                      |
| ---------------------------------------------------------------- | ---------------------------------------------------- | ---------------------------------------- |
| Needs tool definitions (ParsedTool)                              | `galaxy-tool-util`                                   | Only package with ToolShed API access    |
| Is structural/syntactic (format conversion, graph topology)      | `gxformat2`                                          | No runtime or ToolShed dependency needed |
| Orchestrates Galaxy (launches server, installs tools, runs jobs) | `planemo`                                            | Needs Galaxy runtime interaction         |
| Validates parameter values or types                              | `galaxy-tool-util`                                   | Requires Pydantic parameter models       |
| Lints metadata (labels, annotations, creators)                   | `gxformat2` or `planemo`                             | Structural — no tool defs needed         |
| Needs both structural conversion AND schema awareness            | gxformat2 (structural) + galaxy-tool-util (callback) | Use the callback protocol pattern        |

### Shared CLI Infrastructure

All `galaxy-tool-util` workflow CLIs share infrastructure in `_cli_common.py`:

- **`build_base_parser(prog, description)`** — creates a top-level `argparse.ArgumentParser` with common args (`--tool-source-cache-dir`, `-v`, `--populate-cache`, `--tool-source`, `--galaxy-url`, `workflow_path` positional)
- **`build_base_subparser_args(parser, stale_key_mode)`** — same as above but mutates an existing subparser (no `prog`/`description`); used by `register()` functions
- **`add_populate_args(parser)`** — adds `--populate-cache`, `--tool-source`, `--galaxy-url`
- **`add_stale_key_args(parser, mode)`** — adds category policy flags (`--allow`/`--deny` for validate mode, `--preserve`/`--strip` for clean mode)
- **`cli_main(parser, options_cls, run_fn)`** — top-level entry-point: parse → `options_cls.from_namespace(args)` → `run_fn(options)` → `sys.exit`
- **`cli_main_from_args(options_cls, run_fn, args)`** — subcommand variant: takes pre-parsed `Namespace`, returns int exit code
- **`setup_tool_info(options)`** — configures logging, builds `GetToolInfo` from options, optionally populates cache

Each script exposes a `register(subparsers)` function called by `gxwf.py` and a `main()` for the standalone binary:

```python
# scripts/my_new_command.py
from .._cli_common import build_base_parser, build_base_subparser_args, cli_main, cli_main_from_args
from ..my_module import MyOptions, run_my_command

SUBCOMMAND = "my-command"

def _add_args(parser):
    parser.add_argument("--strict", action="store_true")

def build_parser():
    parser = build_base_parser("gxwf-my-command", "Description here.")
    _add_args(parser)
    return parser

def main(argv=None):
    cli_main(build_parser(), MyOptions, run_my_command, argv)

def register(subparsers):
    p = subparsers.add_parser(SUBCOMMAND, help="Short help for gxwf my-command")
    build_base_subparser_args(p)
    _add_args(p)
    p.set_defaults(func=lambda args: cli_main_from_args(MyOptions, run_my_command, args))
```

`MyOptions` must extend `ToolCacheOptions` and implement `from_namespace(args)` (inherited from `ToolCacheOptions`).

Register the standalone binary in `packages/tool_util/setup.cfg`:

```ini
[options.entry_points]
console_scripts =
    gxwf-my-command = galaxy.tool_util.workflow_state.scripts.my_command:main
```

The `gxwf` entry point is registered once; adding a subcommand only requires implementing `register()` and importing the module in `gxwf.py`.

### Report Models

Validation, cleaning, and round-trip commands share structured report infrastructure via `_report_models.py`. Reports support three output formats:

- **Text** — human-readable terminal output (default)
- **JSON** — machine-readable (`--report-json`)
- **Markdown** — documentation-friendly (`--report-markdown`)

New commands that produce structured results should use this infrastructure for consistency.

### The gxformat2 Callback Protocol

When `galaxy-tool-util` needs schema-aware behavior inside gxformat2's conversion pipeline, it injects callbacks via `ConversionOptions` rather than adding a dependency:

- **`state_encode_to_format2`** (`StateEncodeToFormat2Fn`) — converts a native step's `tool_state` to a Format2 `state` dict. Accepts a native step dict, returns a state dict or `None` to fall back to default passthrough. Factory: `make_convert_tool_state(get_tool_info)`.
- **`state_encode_to_native`** (`StateEncodeToNativeFn`) — encodes Format2 `state` back to native with correct types (multiple-select lists → comma strings, etc.). Accepts `(step, state)`, returns encoded dict or `None` for default `json.dumps` encoding. Factory: `make_encode_tool_state(get_tool_info)`.

Wiring example (from `roundtrip.py`):

```python
from gxformat2.options import ConversionOptions
from .convert import make_convert_tool_state, make_encode_tool_state

forward_options = ConversionOptions(
    state_encode_to_format2=make_convert_tool_state(get_tool_info)
)
reverse_options = ConversionOptions(
    state_encode_to_native=make_encode_tool_state(get_tool_info)
)
```

To add a new schema-aware transformation: add a callback slot on `ConversionOptions` in gxformat2, then implement and wire it from `galaxy-tool-util`.

### Adding a New CLI Command — Checklist

1. Implement domain logic in a module under `workflow_state/` (e.g. `my_feature.py`)
2. Define a typed options model (Pydantic `BaseModel` extending `ToolCacheOptions`)
3. Define a `run_my_feature(options) -> int` entry point returning an exit code
4. Create `scripts/my_command.py` with `main()` and `register(subparsers)` following the pattern above
5. Register the standalone binary in `packages/tool_util/setup.cfg` as a `console_scripts` entry
6. Import the module in `scripts/gxwf.py` and add it to `_SINGLE_FILE` or `_TREE`
7. Add tests — unit tests for domain logic and integration tests in `test_gxwf_cli.py`
8. Update this document
