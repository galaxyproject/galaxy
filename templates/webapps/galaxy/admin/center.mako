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
                    <strong>Data types</strong> - See all datatypes available in this Galaxy.
                </li>
                <li>
                    <strong>Data tables</strong> - See all data tables available in this Galaxy.
                </li>
                <li>
                    <strong>Display applications</strong> - See all display applications configured in this Galaxy.
                </li>
                <li>
                    <strong>Manage jobs</strong> - Display all jobs that are currently not finished (i.e., their state is new, waiting, queued, or running).  Administrators are able to cleanly stop long-running jobs.
                </li>
                <li>
                    <strong>Local data</strong> - Manage the reference (and other) data that is stored within Tool Data Tables. See <a href="https://galaxyproject.org/admin/tools/data-managers" target="_blank">wiki</a> for details.
                </li>
            </ul>

        <h4>User Management</h4>
            <ul>
                <li>
                    <strong>Users</strong> - The primary user management interface, displaying information associated with each user and providing operations for resetting passwords, updating user information, impersonating a user, and more.
                </li>
            %if trans.app.config.enable_quotas:
                <li>
                    <strong>Quotas</strong> - Manage user space quotas. See <a href="https://galaxyproject.org/admin/disk-quotas" target="_blank">wiki</a> for details.
                </li>
            %endif
                <li>
                    <strong>Groups</strong> - A view of all groups along with the members of the group and the roles associated with each group.
                </li>
                <li>
                    <strong>Roles</strong> - A view of all non-private roles along with the role type, and the users and groups that are associated with the role.
                    Also includes a view of the data library datasets that are associated with the role and the permissions applied to each dataset.
                </li>
                <li>
                    <strong>Forms</strong> - Manage local form definitions.
                </li>
            </ul>

        <h4>Tool Management</h4>
            <ul>
            %if trans.app.tool_shed_registry and trans.app.tool_shed_registry.tool_sheds:
                <li>
                    <strong>Install new tools</strong> - Search and install new tools and other Galaxy utilities from the Tool Shed. See <a href="https://galaxyproject.org/admin/tools/add-tool-from-toolshed-tutorial" target="_blank">the tutorial</a>.
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
                    <strong>View lineage</strong> - A view of a version lineages for all installed tools. Useful for debugging.
                </li>
                <li>
                    <strong>View migration stages</strong> - See the list of migration stages that moved sets of tools from the distribution to the Tool Shed.
                </li>
            </ul>
%endif
