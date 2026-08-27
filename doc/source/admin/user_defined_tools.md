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

## Limitations

The user-defined tool language is still evolving, and additional safety audits are ongoing.

Current limitations include:

- Access to reference data is not supported
- Access to metadata and metadata files (such as BAM indexes) is not supported
- Access to the `extra_files` directory is not supported
