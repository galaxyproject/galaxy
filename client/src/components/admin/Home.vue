<template>
    <div>
        <h1>Administration</h1>

        <p>
            Please visit

            <a href="https://galaxyproject.org/admin" target="_blank">the Galaxy administration hub</a> to learn how to
            keep your Galaxy in best shape.
        </p>

        <Heading h2 icon="fa-server" size="md">Server</Heading>
        <ul>
            <li>
                <strong>
                    <router-link to="/admin/data_types">Data Types</router-link>
                </strong>
                - See all datatypes available in this Galaxy.
            </li>
            <li>
                <strong>
                    <router-link to="/admin/data_tables">Data Tables</router-link>
                </strong>
                - See all data tables available in this Galaxy.
            </li>
            <li>
                <strong>
                    <router-link to="/admin/display_applications">Display Applications</router-link>
                </strong>
                - See all display applications configured in this Galaxy.
            </li>
            <li>
                <strong>
                    <router-link to="/admin/jobs">Jobs</router-link>
                </strong>
                - Display all jobs that are currently not finished (i.e., their state is new, waiting, queued, or
                running). Administrators are able to cleanly stop long-running jobs.
            </li>
            <li>
                <strong>
                    <router-link to="/admin/data_manager">Local Data</router-link>
                </strong>
                - Manage the reference (and other) data that is stored within Tool Data Tables. See
                <a href="https://galaxyproject.org/admin/tools/data-managers" target="_blank">wiki</a> for details.
            </li>
        </ul>

        <Heading h2 icon="fa-user" size="md">User Management</Heading>
        <ul>
            <li>
                <strong>
                    <router-link to="/admin/users">Users</router-link>
                </strong>
                - The primary user management interface, displaying information associated with each user and providing
                operations for resetting passwords, updating user information, impersonating a user, and more.
            </li>
            <!-- %if trans.app.config.enable_quotas: -->
            <li>
                <strong>
                    <router-link to="/admin/quotas">Quotas</router-link>
                </strong>
                - Manage user space quotas. See
                <a href="https://galaxyproject.org/admin/disk-quotas" target="_blank">wiki</a> for details.
            </li>
            <!-- %endif -->
            <li>
                <strong>
                    <router-link to="/admin/groups">Groups</router-link>
                </strong>
                - A view of all groups along with the members of the group and the roles associated with each group.
            </li>
            <li>
                <strong>
                    <router-link to="/admin/roles">Roles</router-link>
                </strong>
                - A view of all non-private roles along with the role type, and the users and groups that are
                associated, with the role. Also includes a view of the data library datasets that are associated with
                the role and the permissions applied to each dataset.
            </li>
            <li>
                <strong>
                    <router-link to="/admin/forms">Forms</router-link>
                </strong>
                - Manage local form definitions.
            </li>
        </ul>

        <Heading h2 icon="fa-wrench" size="md">Tool Management</Heading>
        <ul>
            <li>
                <strong>
                    <router-link to="/admin/sanitize_allow">Manage Allowlist</router-link>
                </strong>
                - Manage HTML rendering for installed tools' output datasets.
            </li>
            <li v-if="isToolshedInstalled">
                <strong>
                    <router-link to="/admin/toolshed">Install and Uninstall</router-link>
                </strong>
                - Search and install new tools and other Galaxy utilities from the Tool Shed. See
                <a href="https://galaxyproject.org/admin/tools/add-tool-from-toolshed-tutorial" target="_blank"
                    >the tutorial</a
                >.
            </li>
            <li>
                <strong>
                    <router-link to="/admin/reset_metadata">Manage Metadata</router-link>
                </strong>
                - Select on which repositories you want to reset metadata.
            </li>
            <li>
                <strong>
                    <router-link to="/admin/tool_versions">View Lineage</router-link>
                </strong>
                - A view of a version lineages for all installed tools. Useful for debugging.
            </li>
        </ul>
    </div>
</template>

<script>
import Heading from "components/Common/Heading.vue";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faServer, faUser, faWrench } from "@fortawesome/free-solid-svg-icons";

library.add(faServer, faUser, faWrench);

export default {
    components: { Heading },
    props: {
        isToolshedInstalled: {
            type: Boolean,
            default: false,
        },
    },
};
</script>
