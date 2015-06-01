<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<%def name="title()">Galaxy Administration</%def>

<h2>Administration</h2>

%if message:
    ${render_msg( message, status )}
%else:
        <h4>Repositories</h4>
            <ul>
                <li>
                    <strong>Search Tool Shed</strong> - Search and install new tools and other Galaxy utilities from the Tool Shed. See <a href="https://wiki.galaxyproject.org/Admin/Tools/AddToolFromToolShedTutorial">the tutorial</a>.
                </li>
                <li>
                    <strong>Monitor installing repositories</strong> - View the status of tools that are being currently installed <i>(Appears only if something from Tool Shed is installed.)</i>
                </li>
                <li>
                    <strong>Manage installed</strong> - View and administer installed tools and utilities on this Galaxy. <i>(Appears only if something from Tool Shed is installed.)</i>
                </li>
                <li>
                    <strong>Reset metadata</strong> - Select on which repositories you want to reset metadata. <i>(Appears only if something from Tool Shed is installed.)</i>
                </li>
                <li>
                    <strong>Download local tool</strong> - Download a tarball with a tool from this Galaxy.
                </li>
            </ul>

        <h4>Security</h4>
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
                <li>
                    <strong>Impersonate a user</strong> - Allows to view Galaxy as another user in order to help troubleshoot issues. <i>(Appears only if allowed in the config.)</i>
                </li>
            </ul>

        <h4>Data</h4>
            <ul>
                <li>
                    <strong>Data libraries</strong> - Data libraries enable authorized Galaxy users to share datasets through with other groups or users. Only administrators can create data libraries. See <a href="https://wiki.galaxyproject.org/DataLibraries">wiki</a> for details and <a href="https://wiki.galaxyproject.org/Admin/DataLibraries/LibrarySecurity">this page</a> for security description.
                </li>
                <li>
                    <strong>Local data</strong> - Manage the reference (and other) data that is stored within Tool Data Tables. See <a href="https://wiki.galaxyproject.org/Admin/Tools/DataManagers">wiki</a> for details.
                </li>
            </ul>

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

        <h4>Form definitions</h4>
            <ul>
                <li>
                    <strong>Form definitions</strong> - Manage local form definitions.
                </li>
            </ul>
%endif
