<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<%def name="title()">Galaxy Administration</%def>

<h2>Administration</h2>
Please visit <a href="https://wiki.galaxyproject.org/Admin" target="_blank">the Galaxy administration hub</a> to learn how to keep your Galaxy in best shape.
%if message:
    ${render_msg( message, status )}
%else:
        <h4>Server</h4>
            <ul>
                <li>
                    <strong>Data types registry</strong> - See all datatypes available in this Galaxy.
                </li>
                <li>
                    <strong>Data tables registry</strong> - See all data tables available in this Galaxy.
                </li>
                <li>
                    <strong>Display applications</strong> - See all display applications configured in this Galaxy.
                </li>
                <li>
                    <strong>Manage jobs</strong> - Display all jobs that are currently not finished (i.e., their state is new, waiting, queued, or running).  Administrators are able to cleanly stop long-running jobs. 
                </li>
            </ul>

        <h4>Tools and Tool Shed</h4>
            <ul>
            %if trans.app.tool_shed_registry and trans.app.tool_shed_registry.tool_sheds:
                <li>
                    <strong>Search Tool Shed</strong> - Search and install new tools and other Galaxy utilities from the Tool Shed. See <a href="https://wiki.galaxyproject.org/Admin/Tools/AddToolFromToolShedTutorial" target="_blank">the tutorial</a>.
                </li>
            %endif
            %if tool_shed_repository_ids:
                <li>
                    <strong>Monitor installing repositories</strong> - View the status of tools that are being currently installed.
                </li>
            %endif
            %if is_repo_installed:
                <li>
                    <strong>Manage installed tools</strong> - View and administer installed tools and utilities on this Galaxy.
                </li>
                <li>
                    <strong>Reset metadata</strong> - Select on which repositories you want to reset metadata.
                </li>
            %endif
                <li>
                    <strong>Download local tool</strong> - Download a tarball with a tool from this Galaxy.
                </li>
                <li>
                    <strong>Reload a tool's configuration</strong> - Allows a new version of a tool to be loaded while the server is running.
                </li>
                <li>
                    <strong>Tool lineage</strong> - A view of a version lineages for all installed tools. Useful for debugging.
                </li>
                <li>
                    <strong>Review tool migration stages</strong> - See the list of migration stages that moved sets of tools from the distribution to the Tool Shed.
                </li>
            </ul>

        <h4>User Management</h4>
            <ul>
                <li>
                    <strong>Users</strong> - A view of all users and all groups and non-private roles associated with each user.  
                </li>
                <li>
                    <strong>Groups</strong> - A view of all groups along with the members of the group and the roles associated with each group.
                </li>
                <li>
                    <strong>Roles</strong> - A view of all non-private roles along with the role type, and the users and groups that are associated with the role.
                    Also includes a view of the data library datasets that are associated with the role and the permissions applied to each dataset.
                </li>
                <li>
                    <strong>API keys</strong> - A view of all generated API keys with an option to re-generate.
                </li>
            %if trans.app.config.allow_user_impersonation:
                <li>
                    <strong>Impersonate a user</strong> - Allows to view Galaxy as another user in order to help troubleshoot issues.
                </li>
            %endif
            </ul>

        <h4>Data</h4>
            <ul>
            %if trans.app.config.enable_quotas:
                <li>
                    <strong>Quotas</strong> - Manage user space quotas. See <a href="https://wiki.galaxyproject.org/Admin/DiskQuotas" target="_blank">wiki</a> for details.
                </li>
            %endif
                <li>
                    <strong>Data libraries</strong> - Data libraries enable authorized Galaxy users to share datasets with other groups or users. Only administrators can create data libraries. See <a href="https://wiki.galaxyproject.org/DataLibraries" target="_blank">wiki</a> for details and <a href="https://wiki.galaxyproject.org/Admin/DataLibraries/LibrarySecurity" target="_blank">this page</a> for security description.
                </li>
                <li>
                    <strong>Local data</strong> - Manage the reference (and other) data that is stored within Tool Data Tables. See <a href="https://wiki.galaxyproject.org/Admin/Tools/DataManagers" target="_blank">wiki</a> for details.
                </li>
            </ul>
        <h4>Form definitions</h4>
            <ul>
                <li>
                    <strong>Form definitions</strong> - Manage local form definitions.
                </li>
            </ul>

        <h4>Sample tracking</h4>
            <ul>
                <li>
                    Please see the <a href="https://wiki.galaxyproject.org/Admin/DataLibraries/LibrarySampleTracking" target="_blank">sample tracking tutorial</a>.
                </li>
            </ul>
%endif
