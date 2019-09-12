<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<%def name="title()">Administration</%def>

<h2>Administration</h2>
Please visit <a href="https://galaxyproject.org/admin" target="_blank">the Galaxy administration hub</a> to learn how to keep your Galaxy in best shape.
%if message:
    ${render_msg( message, status )}
%else:
        <h4>Server</h4>
            <ul>
                <li>
                    <strong><a href="/admin/data_types" target="_parent">Data types</a></strong> - See all datatypes available in this Galaxy.
                </li>
                <li>
                    <strong><a href="/admin/data_tables" target="_parent">Data tables</a></strong> - See all data tables available in this Galaxy.
                </li>
                <li>
                    <strong><a href="/admin/display_applications" target="_parent">Display applications</a></strong> - See all display applications configured in this Galaxy.
                </li>
                <li>
                    <strong><a href="/admin/jobs" target="_parent">Manage jobs</a></strong> - Display all jobs that are currently not finished (i.e., their state is new, waiting, queued, or running).  Administrators are able to cleanly stop long-running jobs.
                </li>
                <li>
                    <strong><a href="/admin/data_manager" target="_parent">Local data</a></strong> - Manage the reference (and other) data that is stored within Tool Data Tables. See <a href="https://galaxyproject.org/admin/tools/data-managers" target="_blank">wiki</a> for details.
                </li>
            </ul>

        <h4>User Management</h4>
            <ul>
                <li>
                    <strong><a href="/admin/users" target="_parent">Users</a></strong> - The primary user management interface, displaying information associated with each user and providing operations for resetting passwords, updating user information, impersonating a user, and more.
                </li>
            %if trans.app.config.enable_quotas:
                <li>
                    <strong><a href="/admin/quotas" target="_parent">Quotas</a></strong> - Manage user space quotas. See <a href="https://galaxyproject.org/admin/disk-quotas" target="_blank">wiki</a> for details.
                </li>
            %endif
                <li>
                    <strong><a href="/admin/groups" target="_parent">Groups</a></strong> - A view of all groups along with the members of the group and the roles associated with each group.
                </li>
                <li>
                    <strong><a href="/admin/roles" target="_parent">Roles</a></strong> - A view of all non-private roles along with the role type, and the users and groups that are associated with the role.
                    Also includes a view of the data library datasets that are associated with the role and the permissions applied to each dataset.
                </li>
                <li>
                    <strong><a href="/admin/forms" target="_parent">Forms</a></strong> - Manage local form definitions.
                </li>
            </ul>

        <h4>Tool Management</h4>
            <ul>
            %if trans.app.tool_shed_registry and trans.app.tool_shed_registry.tool_sheds:
                <li>
                    <strong><a href="/admin/toolshed" target="_parent">Install new tools</a></strong> - Search and install new tools and other Galaxy utilities from the Tool Shed. See <a href="https://galaxyproject.org/admin/tools/add-tool-from-toolshed-tutorial" target="_blank">the tutorial</a>.
                </li>
            %endif
            %if tool_shed_repository_ids:
                <li>
                    <strong>Monitor installation</strong> - View the status of tools that are being currently installed.
                </li>
            %endif
            %if is_repo_installed:
                <li>
                    <strong>Manage tools</strong> - View and administer installed tools and utilities on this Galaxy.
                </li>
                <li>
                    <strong>Manage metadata</strong> - Select on which repositories you want to reset metadata.
                </li>
            %endif
                <li>
                    <strong><a href="/admin/tool_versions" target="_parent">View lineage</a></strong> - A view of a version lineages for all installed tools. Useful for debugging.
                </li>
                <li>
                    <strong><a href="/admin/review_tool_migration_stages" target="_parent">View migration stages</a></strong> - See the list of migration stages that moved sets of tools from the distribution to the Tool Shed.
                </li>
            </ul>
%endif
