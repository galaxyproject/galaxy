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

The sandbox constrains what a tool definition can *template*. It does not constrain what the resulting command can *do* inside its container, so the isolation of the job's execution environment is still the deployment's responsibility.

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
[`test/integration/embedded_pulsar_job_conf.yml`](https://github.com/galaxyproject/galaxy/blob/dev/test/integration/embedded_pulsar_job_conf.yml)
and
[`test/integration/embedded_pulsar_tpv_job_conf.yml`](https://github.com/galaxyproject/galaxy/blob/dev/test/integration/embedded_pulsar_tpv_job_conf.yml).

### Resource requests are advisory

A tool author declares CPU, memory and GPU needs with a `resource` requirement. Galaxy core enforces only `timelimit`; every other field is metadata attached to the tool for the destination logic above to act on. Nothing happens automatically, and `cores_min` in particular does not set `$GALAXY_SLOTS` unless a destination is configured to derive its core count from the request, as the TPV example does.

If your site publishes a convention for selecting a resource profile — a tool `id` prefix, a naming scheme, a dedicated destination — document it for your users. TPV's own entity matching identifies a user-defined tool as `user_defined-<uuid>` rather than by the author-supplied `id`, so a rule keyed on an `id` prefix is one you have to write deliberately.

## Container execution

Every user-defined tool names the image it runs in, and that reference is resolved by the `explicit` family of container resolvers: the identifier is handed to the container runtime as written rather than being resolved from package requirements. Which container types are usable, and whether images are converted and cached ahead of time, is a per-destination decision — see [Container Resolvers in Galaxy](./container_resolvers.rst).

Set `require_container: true` on any destination that accepts user-defined tools. Without it, a tool whose image cannot be resolved runs directly on the host instead of failing.

## Limitations

The user-defined tool language is still evolving, and additional safety audits are ongoing.

Current limitations include:

- Access to reference data is not supported
- Access to metadata and metadata files (such as BAM indexes) is not supported
- Access to the `extra_files` directory is not supported
- Declared `tests` are stored but are not executed for a tool held in the database
- Expressions in resource requirement values are not evaluated
