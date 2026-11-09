# User-Defined Tools (Beta)

Starting with Galaxy 25.0, users can create their own tools without requiring administrator privileges to install them. These tools are written in YAML, defined through the Galaxy user interface, and stored in the database.

This page covers the administration of the feature: enabling it, containing what it runs, and routing its jobs. For the tool format itself — expression syntax, container references, resource requests, validation and the authoring API — see [Authoring User-Defined Tools](../dev/user_defined_tools_authoring.md), which is the same reference the tool editor's help panel shows.

## Why user-defined tools use a restricted language

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

To address this, Galaxy supports a restricted tool language for user-defined tools. This format is modeled after the XML tool definition but replaces Cheetah templating with sandboxed JavaScript expressions that have no access to the database or filesystem, and it requires every tool to declare the container it runs in.

User-defined tool help must be written in Markdown, which Galaxy renders without raw HTML.

The sandbox constrains what a tool definition can *template*. It does not constrain what the resulting command can *do* inside its container, so the isolation of the job's execution environment is still the deployment's responsibility.

## Enabling User-Defined Tools

To enable this feature:

1. Set `enable_beta_tool_formats: true` in your Galaxy configuration.
2. Create a role of type `Custom Tool Execution` in the admin user interface.
3. Assign users or groups to this role.
4. Review `user_defined_tool_allowed_containers`, which by default only allows BioContainers images (see [Allowed container images](#allowed-container-images)).

Galaxy checks the role again when a job is prepared, so removing a user from the role, or deleting the role, also fails that user's queued user-defined tool jobs.

## Sharing User-Defined Tools

User-defined tools are private to their creators. However, if a tool is embedded in a workflow, any user who imports that workflow will automatically have the tool created in their account.

These tools can also be exported to disk and loaded like regular tools, enabling instance-wide availability if needed.

## Stored tools and schema changes

A tool is stored as it was saved, and the schema for user-defined tools can become stricter between Galaxy versions. Galaxy validates each stored tool against the current schema when it loads it:

- If the definition contains fields the schema no longer accepts, or input validators of a type the parameter no longer accepts, those parts are dropped and the tool loads without them. The tool form shows a message listing what was ignored. The unprivileged tools API reports the tool with `representation_status: lifted` and lists the dropped parts in `representation_errors`. Requests for a single tool, including its raw source, also add a shortened summary in the `X-Galaxy-Deprecated-Fields` response header (at most 20 entries or 1 KB, ending in `+N more` when cut); the list endpoint sends no such header. Saving the tool from the tool editor stores it as a new tool without them.
- If the definition cannot be made valid by dropping parts, for example because a required field such as `shell_command` is missing, the tool is refused. Opening or running it returns an error that lists the problems and asks the user to correct them in the tool editor and save the tool as a new tool. The unprivileged tools API still returns the stored definition, with `representation_status: invalid`, so that it can be repaired.

## Security considerations

User-defined tools share the same security risks as interactive tools.
See https://training.galaxyproject.org/training-material/topics/admin/tutorials/interactive-tools/tutorial.html#securing-interactive-tools for an extended discussion,
and see https://github.com/galaxyproject/galaxy/blob/dev/test/integration/embedded_pulsar_job_conf.yml#L29 for a simple example that uses embedded pulsar to isolate mounts and disables network access.
While the feature is in beta we recommend that only trusted users are allowed to use this feature.

## Routing user-defined tool jobs

Because a user-defined tool runs an arbitrary command in an arbitrary image, it should be routed to an isolated destination rather than to wherever ordinary tools run. Galaxy exposes user-defined tools to the job configuration in two ways.

### With `job_conf.yml`

Every user-defined tool matches the `user_defined` tool class, so a static mapping is enough to send all of them to one environment:

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

See [Galaxy Job Configuration](./jobs.md) for the full syntax, including dynamic destination mapping if the decision needs to be made per job.

### With Total Perspective Vortex

[Total Perspective Vortex](https://total-perspective-vortex.readthedocs.io/) (TPV), which Galaxy requires at version 3.2.1 or newer, understands user-defined tools natively:

- Each user-defined tool job is tagged `tool_type_user_defined`, and destinations that do not explicitly `accept` that tag reject the job. This is a secure default: a new destination will not silently start receiving user-defined tools.
- The resource requirements declared by the tool author are mapped onto TPV entity fields — `cores_min` → `cores`, `cores_max` → `max_cores`, `ram_min` → `mem`, `ram_max` → `max_mem`, `cuda_device_count_min` → `gpus`, `cuda_device_count_max` → `max_gpus`. The remaining fields have no TPV equivalent and need a custom rule if a site wants to act on them.

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
[`test/integration/embedded_pulsar_job_conf.yml`](https://github.com/galaxyproject/galaxy/blob/release_26.1/test/integration/embedded_pulsar_job_conf.yml)
and
[`test/integration/embedded_pulsar_tpv_job_conf.yml`](https://github.com/galaxyproject/galaxy/blob/release_26.1/test/integration/embedded_pulsar_tpv_job_conf.yml).

### Resource requests are advisory

A tool author declares CPU, memory and GPU needs with a `resource` requirement. Galaxy core enforces only `timelimit`; every other field is metadata attached to the tool for the destination logic above to act on. Nothing happens automatically, and `cores_min` in particular does not set `$GALAXY_SLOTS` unless a destination is configured to derive its core count from the request, as the TPV example does.

If your site publishes a convention for selecting a resource profile — a tool `id` prefix, a naming scheme, a dedicated destination — document it for your users. TPV's own entity matching identifies a user-defined tool as `user_defined-<uuid>` rather than by the author-supplied `id`, so a rule keyed on an `id` prefix is one you have to write deliberately.

## Container execution

Every user-defined tool names the image it runs in, and that reference is resolved by the `explicit` family of container resolvers: the identifier is handed to the container runtime as written rather than being resolved from package requirements. Which container types are usable, and whether images are converted and cached ahead of time, is a per-destination decision — see [Container Resolvers in Galaxy](./container_resolvers.rst).

Set `require_container: true` on any destination that accepts user-defined tools. Without it, a tool whose image cannot be resolved runs directly on the host instead of failing.

### Allowed container images

The `user_defined_tool_allowed_containers` option lists the images user-defined tools may name. The default allows only BioContainers:

```yaml
user_defined_tool_allowed_containers:
  - quay.io/biocontainers/*
```

BioContainers images are built by the Bioconda build system from reviewed recipes, so the whole namespace can be trusted at once. Add other images one at a time:

```yaml
user_defined_tool_allowed_containers:
  - quay.io/biocontainers/*     # any image below the namespace, at any depth, any tag or digest
  - docker.io/library/python    # this image, any tag or digest
  - ghcr.io/someorg/tool:1.2    # this image, only tag 1.2 (and no digest)
  - ghcr.io/someorg/tool@sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef  # only this digest
```

Each entry and each tool's `container` are parsed into registry, repository, tag and digest and compared part by part, never as string prefixes:

- An unqualified name is on Docker Hub, and a single-component Docker Hub name is in `library/`: `python:3.13` is `docker.io/library/python:3.13`. A `docker://` prefix is ignored, and registry host names are compared case-insensitively.
- `<registry>/<path>/*` allows any repository strictly below `<path>` on that registry. `quay.io/biocontainers/*` does not allow `quay.io/biocontainers-evil/x`, `quay.io.evil.com/biocontainers/x`, or `quay.io/biocontainers` itself. `<registry>/*` allows a whole registry, and `<path>/*` without a registry a Docker Hub namespace.
- An entry with a tag allows only references with that tag and without a digest. An entry with a digest allows only references with that digest, whatever tag they also carry. Container runtimes pull the digest of a reference that has both and ignore its tag, so a tag entry cannot allow `image:<tag>@<any digest>`.
- References with any other scheme, such as `oras://`, never match: user-defined tool images are Docker image references, which the explicit Singularity resolvers pull with a `docker://` prefix.
- A lone `*` allows any image. An empty list allows none, so no user-defined tool can be created or run. Leaving the option unset uses the default.

To exclude images from what the allowed list permits, list them in `user_defined_tool_denied_containers`, which is empty by default. A denied entry takes precedence over an allowed one:

```yaml
user_defined_tool_allowed_containers:
  - quay.io/biocontainers/*
user_defined_tool_denied_containers:
  - quay.io/biocontainers/some-tool   # this image, every tag and digest
  - ghcr.io/someorg/experimental/*    # any image below the path
```

Denied entries are parsed and compared like allowed ones, with these differences:

- An entry must name a repository or a namespace. Entries with a tag or digest are refused, because the same image can be named by another tag or digest. A lone `*` is refused too; use an empty allowed list to allow no images.
- When the list is not empty, a reference Galaxy cannot parse, such as an `oras://` one, is refused even if `user_defined_tool_allowed_containers` is `*`, because it cannot be compared against the denied entries.
- `<path>/*` does not include `<path>` itself. To deny both, list both.

Galaxy resolves an unqualified name against Docker Hub, as Docker does. Podman may instead search the registries listed in its `unqualified-search-registries` setting, so a tool allowed to use `python:3.13` because `docker.io/library/python` is listed could pull `python` from another registry. On destinations that run Podman, either set `unqualified-search-registries = ["docker.io"]` or do not list Docker Hub images. The default list is not affected: an unqualified name never matches `quay.io/biocontainers/*`.

Galaxy checks the image when a tool is created, through the API, the tool editor, a workflow import or the tool-authoring assistant, and refuses the tool with a message listing the allowed entries. It checks again before each job of a user-defined tool runs, against the image the tool declares rather than whatever a container resolver maps it to, so tools created before an image was removed from the list fail with a message instead of running. The check also applies to `GalaxyUserTool` tools an administrator loads from disk. Galaxy refuses to start if an entry is malformed.

This check gives users an early, clear error and protects servers whose compute nodes can reach any registry. It cannot stop a compromised compute node from pulling other images; to enforce the list at the network level, route the compute nodes' registry traffic through a proxy that only serves the allowed upstreams.

## Limitations

The user-defined tool language is still evolving, and additional safety audits are ongoing.

Current limitations include:

- Access to reference data is not supported
- Access to metadata and metadata files (such as BAM indexes) is not supported
- Access to the `extra_files` directory is not supported
- Declared `tests` are stored but are not executed for a tool held in the database
- Nonnumeric expressions in resource requirement values are not supported
