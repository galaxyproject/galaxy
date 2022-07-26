<template>
    <div>
        <h2>Administration</h2>
        Please visit

        <a href="https://galaxyproject.org/admin" target="_blank">the Galaxy administration hub</a> to learn how to keep
        your Galaxy in best shape.

        <h4>Server</h4>
        <ul>
            <li>
                <strong>
                    <a :href="adminDataTypesUrl" @click.prevent="useRouter">Data Types</a>
                </strong>
                - See all datatypes available in this Galaxy.
            </li>
            <li>
                <strong>
                    <a :href="adminDataTablesUrl" @click.prevent="useRouter">Data Tables</a>
                </strong>
                - See all data tables available in this Galaxy.
            </li>
            <li>
                <strong>
                    <a :href="adminDisplayApplicationsUrl" @click.prevent="useRouter">Display Applications</a>
                </strong>
                - See all display applications configured in this Galaxy.
            </li>
            <li>
                <strong>
                    <a :href="adminJobsUrl" @click.prevent="useRouter">Jobs</a>
                </strong>
                - Display all jobs that are currently not finished (i.e., their state is new, waiting, queued, or
                running). Administrators are able to cleanly stop long-running jobs.
            </li>
            <li>
                <strong>
                    <a :href="adminDMUrl" @click.prevent="useRouter">Local Data</a>
                </strong>
                - Manage the reference (and other) data that is stored within Tool Data Tables. See
                <a href="https://galaxyproject.org/admin/tools/data-managers" target="_blank">wiki</a> for details.
            </li>
        </ul>

        <h4>User Management</h4>
        <ul>
            <li>
                <strong>
                    <a :href="adminUsersUrl" @click.prevent="useRouter">Users</a>
                </strong>
                - The primary user management interface, displaying information associated with each user and providing
                operations for resetting passwords, updating user information, impersonating a user, and more.
            </li>
            <!-- %if trans.app.config.enable_quotas: -->
            <li>
                <strong>
                    <a :href="adminQuotasUrl" @click.prevent="useRouter">Quotas</a>
                </strong>
                - Manage user space quotas. See
                <a href="https://galaxyproject.org/admin/disk-quotas" target="_blank">wiki</a> for details.
            </li>
            <!-- %endif -->
            <li>
                <strong>
                    <a :href="adminGroupsUrl" @click.prevent="useRouter">Groups</a>
                </strong>
                - A view of all groups along with the members of the group and the roles associated with each group.
            </li>
            <li>
                <strong>
                    <a :href="adminRolesUrl" @click.prevent="useRouter">Roles</a>
                </strong>
                - A view of all non-private roles along with the role type, and the users and groups that are
                associated, with the role. Also includes a view of the data library datasets that are associated with
                the role and the permissions applied to each dataset.
            </li>
            <li>
                <strong>
                    <a :href="adminFormsUrl" @click.prevent="useRouter">Forms</a>
                </strong>
                - Manage local form definitions.
            </li>
        </ul>

        <h4>Tool Management</h4>
        <ul>
            <li>
                <strong>
                    <a :href="adminSanitizeAllowUrl" @click.prevent="useRouter">Manage Allowlist</a>
                </strong>
                - Manage HTML rendering for installed tools' output datasets.
            </li>
            <li v-if="isToolShedInstalled">
                <strong>
                    <a :href="adminToolshedUrl" @click.prevent="useRouter">Install and Uninstall</a>
                </strong>
                - Search and install new tools and other Galaxy utilities from the Tool Shed. See
                <a href="https://galaxyproject.org/admin/tools/add-tool-from-toolshed-tutorial" target="_blank"
                    >the tutorial</a
                >.
            </li>
            <li v-if="isRepoInstalled">
                <strong>
                    <a :href="adminManageMetadata" @click.prevent="useRouter">Manage Metadata</a>
                </strong>
                - Select on which repositories you want to reset metadata.
            </li>
            <li>
                <strong>
                    <a :href="adminToolVersionsUrl" @click.prevent="useRouter">View Lineage</a>
                </strong>
                - A view of a version lineages for all installed tools. Useful for debugging.
            </li>
        </ul>
    </div>
</template>

<script>
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";

const root = getAppRoot();

export default {
    props: {
        isRepoInstalled: {
            type: Boolean,
            required: true,
        },
        isToolShedInstalled: {
            type: Boolean,
            required: true,
        },
    },
    computed: {
        adminDataTypesUrl: () => `${root}admin/data_types`,
        adminDataTablesUrl: () => `${root}admin/data_tables`,
        adminDisplayApplicationsUrl: () => `${root}admin/display_applications`,
        adminJobsUrl: () => `${root}admin/jobs`,
        adminManageMetadata: () => `${root}admin/reset_metadata`,
        adminDMUrl: () => `${root}admin/data_manager`,
        adminUsersUrl: () => `${root}admin/users`,
        adminQuotasUrl: () => `${root}admin/quotas`,
        adminGroupsUrl: () => `${root}admin/groups`,
        adminRolesUrl: () => `${root}admin/roles`,
        adminSanitizeAllowUrl: () => `${root}admin/sanitize_allow`,
        adminFormsUrl: () => `${root}admin/forms`,
        adminToolshedUrl: () => `${root}admin/toolshed`,
        adminToolVersionsUrl: () => `${root}admin/tool_versions`,
    },
    methods: {
        useRouter: function (ev) {
            const Galaxy = getGalaxyInstance();
            Galaxy.page.router.push(ev.target.pathname.slice(root.length));
        },
    },
};
</script>
