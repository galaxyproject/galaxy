# User-Defined Tools (Beta)

Starting with Galaxy 25.0, users can create their own tools without requiring administrator privileges to install them. These tools are written in YAML, defined through the Galaxy user interface, and stored in the database.

## Differences from Standard Galaxy Tools

Standard Galaxy tools are written in XML and have broad access to the Galaxy database and filesystem during the command and configuration file templating phase, which uses the Cheetah templating language.

For example, the following XML tool command section queries the Galaxy database and writes a file to the home directory of the system user running the Galaxy process:

```xml
<command><![CDATA[
    #from pathlib import Path
    #user_id = $__app__.model.session().query($__app__.model.User.id).one()
    #open(f"{Path.home()}/a_file", "w").write("Hello!")
]]></command>
```

This level of access is acceptable when only administrators install tools. However, allowing regular users to define and execute arbitrary tools requires stricter controls.

To address this, Galaxy now supports a restricted tool language for user-defined tools. This format is modeled after the XML tool definition but replaces Cheetah templating with sandboxed JavaScript expressions that do not have access to the database or filesystem.

Example: Concatenate Files Tool (YAML)

```yaml
class: GalaxyUserTool
id: cat_user_defined
version: "0.1"
name: Concatenate Files
description: tail-to-head
container: busybox
shell_command: |
  cat $(inputs.datasets.map((input) => input.path).join(' ')) > output.txt
inputs:
  - name: datasets
    multiple: true
    type: data
outputs:
  - name: output1
    type: data
    format_source: datasets
    from_work_dir: output.txt
```

Equivalent Tool in XML:

```xml
<tool id="cat" version="0.1">
    <description>tail-to-head</description>
    <requirements>
        <requirement type="container">busybox</requirement>
    </requirements>
    <command><![CDATA[
cat
#for dataset in datasets:
    '$dataset'
#end for
> '$output1'
    ]]></command>
    <inputs>
        <input name="datasets" format="data" type="data" multiple="true"/>
    </inputs>
    <outputs>
        <output name="output1" format_source="datasets" />
    </outputs>
</tool>
```

While the structure is similar, several key differences exist:

- The YAML version includes a required `class: GalaxyUserTool` line to signal the use of the restricted `UserToolSource` schema.
- All user-defined tools must be executed inside a container, specified using the `container` key.
- The command to be executed is defined under the `shell_command` key, using a string with embedded JavaScript expressions inside `$()`. In the example above, the expression iterates over the input dataset paths and joins them into a single command string.

## Enabling User-Defined Tools

To enable this feature:

1. Set `enable_beta_tool_formats: true` in your Galaxy configuration.
2. Create a role of type `Custom Tool Execution` in the admin user interface.
3. Assign users or groups to this role.

## Sharing User-Defined Tools

User-defined tools are private to their creators. However, if a tool is embedded in a workflow, any user who imports that workflow will automatically have the tool created in their account.

These tools can also be exported to disk and loaded like regular tools, enabling instance-wide availability if needed.

## Security considerations

User-defined tools share the same security risks as interactive tools.
See https://training.galaxyproject.org/training-material/topics/admin/tutorials/interactive-tools/tutorial.html#securing-interactive-tools for an extended discussion,
and see https://github.com/galaxyproject/galaxy/blob/dev/test/integration/embedded_pulsar_job_conf.yml#L29 for a simple example that uses embedded pulsar to isolate mounts and disables network access.
While the feature is in beta we recommend that only trusted users are allowed to use this feature.

## Supported input parameter types

The YAML authoring layer exposes a deliberately narrow subset of Galaxy's
parameter model. The JSON schema published to the editor (`ToolSourceSchema.json`)
is generated from this subset and rejects any unknown fields via
`extra="forbid"`, so unsupported attributes fail fast at parse time.

Supported leaf parameter types:

| Type              | Supported fields (beyond `name`, `label`, `help`, `optional`)          |
| ----------------- | ---------------------------------------------------------------------- |
| `boolean`         | `value`                                                                |
| `integer`         | `value`, `min`, `max`, `validators` (`in_range` only)                  |
| `float`           | `value`, `min`, `max`, `validators` (`in_range` only)                  |
| `text`            | `value`, `area`, `validators` (`length`, `regex`, `empty_field`)       |
| `select`          | `options` (static, non-empty), `multiple`, `validators` (`no_options`) |
| `color`           | `value`                                                                |
| `data`            | `format`, `multiple`, `min`, `max`                                     |
| `data_collection` | `collection_type`, `format`                                            |

Supported structural groups: `conditional`, `repeat`, `section`. These recurse
into the supported leaf set.

Example using several supported types:

```yaml
class: GalaxyUserTool
id: example_tool
version: "0.1"
name: Example
container: busybox
shell_command: echo "$(inputs.greeting) $(inputs.count)"
inputs:
  - name: greeting
    type: select
    options:
      - { label: Hi, value: hi, selected: true }
      - { label: Hello, value: hello, selected: false }
  - name: count
    type: integer
    value: 1
    min: 1
    max: 10
  - name: extras
    type: repeat
    min: 0
    parameters:
      - name: input_file
        type: data
        format: txt
outputs: []
```

Types that exist in the XML tool vocabulary but are **not** supported in YAML
user-defined tools and will be rejected at parse time: `hidden`, `drill_down`,
`data_column`, `genomebuild`, `group_tag`, `baseurl`, `rules`, `directory`.
XML-only fields such as `truevalue`, `falsevalue`, `argument`, `is_dynamic`,
`hidden` (as a field), and `parameter_type` are likewise rejected on any
parameter.

## Expression syntax and its collision with shell syntax

`shell_command` is not handed to the shell unchanged. Galaxy first evaluates it with a
sandboxed ECMAScript 5.1 engine, using the same parameter-reference syntax CWL uses, and
only the evaluated result is written into the job script.

Two forms are recognized:

- `$( ... )` — a parameter reference or a single expression, for example
  `$(inputs.threads)`, `$(inputs.query.path)`, or
  `$(inputs.datasets.map((d) => d.path).join(' '))`.
- `${ ... }` — a function body, which must `return` a value, for example
  `${ return inputs.threads * 2 }`.

Substituted values are inserted literally; Galaxy does **not** shell-quote them. Quote any
substitution that can contain spaces yourself: `'$(inputs.query.path)'`.

Reusable helper functions can be declared with a `javascript` requirement, and are then
available to every expression in the tool:

```yaml
requirements:
  - type: javascript
    expression_lib:
      - |
        function basename(path) { return path.split('/').pop(); }
```

### Shell constructs that do not survive evaluation

Because `$(` and `${` are consumed during evaluation, the shell constructs built on them
never reach the shell:

| Written in `shell_command`                | Result                                                                       |
| ----------------------------------------- | ---------------------------------------------------------------------------- |
| `$(date +%s)`                             | Evaluated as JavaScript; the job fails with an expression evaluation error.  |
| `${HOME}`, `${f%.txt}`, `${VAR:-default}` | Evaluated as JavaScript; normally a syntax error.                            |
| `$(( 1 + 2 ))`                            | Silently evaluated as JavaScript and replaced by `3` — no error, wrong meaning. |
| `$GALAXY_SLOTS`, `$HOME`, `$1`            | Passed through untouched. A `$` not followed by `(` or `{` is ignored.       |

An unbraced shell variable is therefore the safe form, and `$GALAXY_SLOTS` in particular
works as it does in XML tools.

To emit a literal `$(` or `${`, escape the dollar with a backslash — `\$(date +%s)` reaches
the shell as `$(date +%s)`.

Backslash handling has one more consequence worth knowing. Escape processing only runs when
the command contains `$(` or `${` somewhere; a command with no expression at all is passed
through byte for byte. In a command that *does* contain an expression, `\\` collapses to a
single `\` everywhere in that command, so a literal backslash pair has to be written as
`\\\\`. Lone backslashes (`\;`, `\.`, `\t`) are left alone.

### Recommended pattern

Evaluate each input once into a shell variable at the top of the command, then use plain,
unbraced shell variables below. Note `"$threads"` rather than `"${threads}"` — the braced
form would be eaten by the expression engine.

```yaml
shell_command: |
  threads="$(inputs.threads)"
  query='$(inputs.query.path)'
  db='$(inputs.database.path)'

  foldseek easy-search "$query" "$db" result.m8 tmp --threads "$threads"
```

User-defined tool commands run under `set -e`, so the first failing command ends the job.

## The container is the whole execution environment

`container` is required, and the image it names is the only environment the command gets.
Every binary, interpreter and library referenced by `shell_command` — including the ones
used for glue work such as sorting, reformatting or renaming outputs — has to already exist
in that image. A single-tool BioContainer is built to be small; many do ship a Python
interpreter, since they are conda environments, but a given image may not, and may equally
lack utilities like `jq` or `bc`. Check before relying on one:

```console
$ docker run --rm quay.io/biocontainers/foldseek:10.941cd33 sh -c 'command -v python3 awk sort'
```

If a command needs several packages, use a multi-package (mulled) image or an image you
build and publish yourself, rather than assuming a single-tool image also carries the others.

### Writing the image reference

Use a fully qualified `registry/repository:tag` reference:

```yaml
container: quay.io/biocontainers/foldseek:10.941cd33
```

A bare `foldseek:10.941cd33` is not resolved by Galaxy against BioContainers; the identifier
is passed to the container runtime as written, and the runtime applies its own default
registry — for Docker that is `docker.io/library`, where the image almost certainly does not
exist. The failure surfaces at job runtime as an image pull error, not at tool creation.

Do **not** prefix the value with `docker://`. Galaxy stores a `container` string as a Docker
container description and adds the `docker://` prefix itself when the destination executes
through Singularity or Apptainer; writing the prefix yourself produces a doubled
`docker://docker://…` identifier.

Container requirements written as `requirements: [{type: container, …}]` are accepted by the
schema but are not read by the YAML tool parser. The top-level `container` key is the only
way a user-defined tool selects its image.

Which container types are usable, and whether images are converted and cached ahead of time,
is a per-destination deployment decision — see
[Container Resolvers in Galaxy](./container_resolvers.rst). Administrators are strongly
encouraged to set `require_container: true` on any destination that accepts user-defined
tools, so a tool whose image cannot be resolved fails instead of running on the host.

## Requesting compute resources

A user-defined tool declares its resource needs with a `resource` entry under `requirements`:

```yaml
requirements:
  - type: resource
    cores_min: 32
    ram_min: 8192
    cuda_device_count_min: 1
    cuda_device_count_max: 1
    gpu_memory_min: 40960
```

The supported fields. The defaults apply when a `resource` entry is present and omits the
field; a tool with no `resource` entry at all declares nothing.

| Field                                            | Meaning                                                  | Default |
| ------------------------------------------------ | -------------------------------------------------------- | ------- |
| `cores_min` / `cores_max`                        | Reserved CPU cores. May be fractional; the reported count is rounded up to the next whole number. | `1` / unset |
| `ram_min` / `ram_max`                            | Reserved RAM in mebibytes (2\*\*20).                     | `256` / unset |
| `tmpdir_min` / `tmpdir_max`                      | Temporary directory space.                               | unset   |
| `cuda_version_min`, `cuda_compute_capability`    | Minimum CUDA version and compute capability.             | unset   |
| `cuda_device_count_min` / `cuda_device_count_max`| Number of GPUs.                                          | unset   |
| `gpu_memory_min`                                 | Minimum GPU memory.                                      | unset   |
| `shm_size`                                       | Shared memory size.                                      | unset   |
| `timelimit`                                      | Maximum runtime in seconds; the job is terminated if exceeded. | unset |

Only `ram_min`/`ram_max` (mebibytes) and `timelimit` (seconds) have a unit declared in the
schema. `tmpdir_*`, `gpu_memory_min` and `shm_size` do not, and nothing in Galaxy reads them,
so their unit is whatever the site-specific rule that consumes them decides — in practice
they are written on the same mebibyte scale as `ram_min`.

Two points about how these values are used are easy to get wrong:

- **Galaxy itself enforces only `timelimit`.** Every other field is metadata attached to the
  tool for the deployment's job-destination logic to act on. Whether a request has any effect
  depends entirely on how the instance's job configuration is set up, and an instance with no
  GPU destination cannot satisfy a GPU request no matter how it is written.
- **`cores_min` does not by itself set `$GALAXY_SLOTS`.** `$GALAXY_SLOTS` is set in the job
  script from the resource manager's actual allocation, or from the destination's
  configuration. It tracks `cores_min` only when the destination is configured to derive its
  core count from the tool's request, which is what the TPV configuration in the next section
  does.

Write literal numbers. The schema also accepts strings, intended for expressions evaluated at
runtime, but expression evaluation for resource requirements is not implemented yet and such
a value is currently ignored rather than rejected.

## Routing user-defined tool jobs

Because a user-defined tool runs an arbitrary command in an arbitrary image, it should be
routed to an isolated destination rather than to wherever ordinary tools run. Galaxy exposes
user-defined tools to the job configuration in two ways. Both are general mechanisms; what a
particular server does with them is that server's own policy.

### With `job_conf.yml`

Every user-defined tool matches the `user_defined` tool class, so a static mapping is enough
to send all of them to one environment:

```yaml
execution:
  environments:
    user_defined:
      runner: pulsar_embed
      remote_metadata: true
      docker_enabled: true
      require_container: true
      docker_net: "none"

tools:
  - class: user_defined
    environment: user_defined
```

See [Galaxy Job Configuration](./jobs.md) for the full syntax, including dynamic destination
mapping if the decision needs to be made per job.

### With Total Perspective Vortex

[Total Perspective Vortex](https://total-perspective-vortex.readthedocs.io/) (TPV), which
Galaxy requires at version 3.2.1 or newer, understands user-defined tools natively:

- Each user-defined tool job is tagged `tool_type_user_defined`, and destinations that do not
  explicitly `accept` that tag reject the job. This is a secure default: a new destination
  will not silently start receiving user-defined tools.
- The tool's resource requirements are mapped onto TPV entity fields —
  `cores_min` → `cores`, `cores_max` → `max_cores`, `ram_min` → `mem`, `ram_max` → `max_mem`,
  `cuda_device_count_min` → `gpus`, `cuda_device_count_max` → `max_gpus`. The remaining
  fields have no TPV equivalent and need a custom rule if a site wants to act on them.

A destination can then turn TPV's resolved `cores` into `$GALAXY_SLOTS`:

```yaml
execution:
  default: tpv
  environments:
    tpv:
      runner: dynamic_tpv
      tpv_configs:
        - destinations:
            user_defined:
              runner: pulsar_embed
              env:
                GALAXY_SLOTS: '{cores}'
              scheduling:
                accept:
                  - tool_type_user_defined
              params:
                require_container: true
                docker_enabled: true
                docker_net: "none"
```

Galaxy's own integration tests exercise both of these configurations; see
[`test/integration/embedded_pulsar_job_conf.yml`](https://github.com/galaxyproject/galaxy/blob/dev/test/integration/embedded_pulsar_job_conf.yml)
and
[`test/integration/embedded_pulsar_tpv_job_conf.yml`](https://github.com/galaxyproject/galaxy/blob/dev/test/integration/embedded_pulsar_tpv_job_conf.yml).

### A note for tool authors on instance-specific routing

Some public servers publish a convention that lets authors pick a resource profile, for
example by using a particular prefix in the tool `id`. A user-defined tool's `id` is chosen
by its author and does reach the job configuration, so an instance can legitimately write
rules against it — but such a convention is that instance's policy rather than part of the
tool format, and it does not transfer to another server. TPV, for instance, matches
user-defined tools by the entity id `user_defined-<uuid>` rather than by the author-supplied
`id`, so a rule keyed on an `id` prefix is one that site wrote deliberately.

If a tool needs a particular amount of CPU, memory or a GPU, declare it in `requirements` as
described above, and check your instance's documentation or support channel for what it
supports. Do not assume another server's naming convention does anything here.

## Validating a tool

Galaxy checks a user-defined tool at several points before it ever runs:

- **Schema validation.** Unknown keys are rejected anywhere in the document
  (`extra="forbid"`), so a misspelled or XML-only field fails immediately rather than being
  ignored.
- **Cross-field validation.** Every `$(inputs.NAME)` referenced from `shell_command` or a
  config file must correspond to a declared input; every `data` output must set
  `from_work_dir` or `discover_datasets`, and every collection output must set
  `discover_datasets`, so an output whose bytes could never be claimed is rejected.
- **Linting.** Creating or editing a tool runs Galaxy's tool linters and refuses the tool if
  any of them reports a problem. This includes a check that the container reference has a
  recognizable shape. Linters that call external services (bio.tools, EDAM) are skipped so
  that authoring does not depend on third-party availability.

Two endpoints are useful for checking a draft without saving it:

- `POST /api/unprivileged_tools/build` renders the tool form for a history, which is the
  quickest way to confirm the input interface is what you intended.
- `POST /api/unprivileged_tools/runtime_model` returns an OpenAPI model of the tool's inputs.

None of this checks that the tool produces *correct results*. A tool that validates, lints
and runs to completion can still be wrong — a misquoted path, a flag that silently changes
meaning between tool versions, or a container whose tool version differs from the one the
command was written against.

### Testing

A user-defined tool may declare a `tests` block, using the same test syntax as other
YAML-format Galaxy tools:

```yaml
tests:
  - inputs:
      input1:
        class: File
        path: simple_line.txt
    outputs:
      output1: simple_line.txt
```

Galaxy stores and returns these tests, but does not currently run them for a tool held in
the database. There is no in-application "run this tool's tests" action, and a
database-stored tool has no tool directory, so file-based test inputs such as the
`simple_line.txt` above cannot be resolved. Declared tests become executable once the tool
is exported to disk and loaded like a regular tool, at which point the usual tool-test
tooling applies; Galaxy's own framework test suite does exactly this for
[`test/functional/tools/cat_user_defined.yml`](https://github.com/galaxyproject/galaxy/blob/dev/test/functional/tools/cat_user_defined.yml).

Until in-platform testing exists, validate correctness by running the tool on inputs whose
answer you already know, and comparing the outputs against a run of the same command outside
Galaxy. This is worth doing once per registered version, since a version bump usually means
a new container image as well.

## Authoring through the API

The tool editor in the Galaxy interface is a client of a small API, so tools can also be
created and managed programmatically — useful when registering many tools, or many versions
of one tool. All of these endpoints require the `Custom Tool Execution` role and operate only
on the calling user's own tools.

| Endpoint                                             | Purpose                                          |
| ---------------------------------------------------- | ------------------------------------------------ |
| `POST /api/unprivileged_tools`                       | Create a tool; returns its `uuid`.               |
| `GET /api/unprivileged_tools`                        | List the calling user's tools.                   |
| `GET /api/unprivileged_tools/{uuid}`                 | Show one tool and its representation.            |
| `DELETE /api/unprivileged_tools/{uuid}`              | Deactivate a tool.                               |
| `POST /api/unprivileged_tools/build?history_id=…`    | Render the tool form without saving the tool.    |
| `POST /api/unprivileged_tools/runtime_model`         | Return an OpenAPI model of the tool's inputs.    |

The create payload wraps the YAML document, converted to JSON, in a `representation` key.
Keeping it in a file avoids fighting the shell over the quoting inside `shell_command`:

```json
{
  "representation": {
    "class": "GalaxyUserTool",
    "id": "my-cool-tool",
    "name": "My Cool Tool",
    "version": "0.1.0",
    "container": "quay.io/biocontainers/python:3.13",
    "shell_command": "head -n '$(inputs.n_lines)' '$(inputs.data_input.path)' > out.txt",
    "inputs": [
      {"type": "integer", "name": "n_lines"},
      {"type": "data", "name": "data_input"}
    ],
    "outputs": [
      {"type": "data", "name": "out", "from_work_dir": "out.txt"}
    ]
  }
}
```

```console
$ curl -X POST "$GALAXY_URL/api/unprivileged_tools" \
    -H "x-api-key: $GALAXY_API_KEY" \
    -H 'Content-Type: application/json' \
    -d @tool.json
```

Run the resulting tool by passing its `uuid` to the normal tool execution endpoint —
`POST /api/tools` with `tool_uuid` instead of `tool_id`.

Rather than reproducing the request and response schemas here, consult the interactive
OpenAPI documentation your server publishes at `<galaxy_url>/api/docs`, under the
`dynamic_tools` tag; it is generated from the same `UserToolSource` model the tool editor
validates against. The generated JSON schema is also checked into the client as
[`ToolSourceSchema.json`](https://github.com/galaxyproject/galaxy/blob/dev/client/src/components/Tool/ToolSourceSchema.json).
For worked examples of every endpoint, see
[`lib/galaxy_test/api/test_unprivileged_tools.py`](https://github.com/galaxyproject/galaxy/blob/dev/lib/galaxy_test/api/test_unprivileged_tools.py).

## Limitations

The user-defined tool language is still evolving, and additional safety audits are ongoing.

Current limitations include:

- Access to reference data is not supported
- Access to metadata and metadata files (such as BAM indexes) is not supported
- Access to the `extra_files` directory is not supported
- Declared `tests` are stored but are not executed for a tool held in the database
- Expressions in resource requirement values are not evaluated
