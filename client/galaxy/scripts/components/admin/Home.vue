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
                    <a @click.prevent="useRouter" :href="adminDataTypesUrl">Data types</a>
                </strong>
                - See all datatypes available in this Galaxy.
            </li>
            <li>
                <strong>
                    <a @click.prevent="useRouter" :href="adminDataTablesUrl">Data tables</a>
                </strong>
                - See all data tables available in this Galaxy.
            </li>
            <li>
                <strong>
                    <a @click.prevent="useRouter" :href="adminDisplayApplicationsUrl">Display applications</a>
                </strong>
                - See all display applications configured in this Galaxy.
            </li>
            <li>
                <strong>
                    <a @click.prevent="useRouter" :href="adminJobsUrl">Manage jobs</a>
                </strong>
                - Display all jobs that are currently not finished (i.e., their state is new, waiting, queued, or
                running). Administrators are able to cleanly stop long-running jobs.
            </li>
            <li>
                <strong>
                    <a @click.prevent="useRouter" :href="adminDMUrl">Local data</a>
                </strong>
                - Manage the reference (and other) data that is stored within Tool Data Tables. See
                <a href="https://galaxyproject.org/admin/tools/data-managers" target="_blank">wiki</a> for details.
            </li>
        </ul>

        <h4>User Management</h4>
        <ul>
            <li>
                <strong>
                    <a @click.prevent="useRouter" :href="adminUsersUrl">Users</a>
                </strong>
                - The primary user management interface, displaying information associated with each user and providing
                operations for resetting passwords, updating user information, impersonating a user, and more.
            </li>
            <!-- %if trans.app.config.enable_quotas: -->
            <li>
                <strong>
                    <a @click.prevent="useRouter" :href="adminQuotasUrl">Quotas</a>
                </strong>
                - Manage user space quotas. See
                <a href="https://galaxyproject.org/admin/disk-quotas" target="_blank">wiki</a> for details.
            </li>
            <!-- %endif -->
            <li>
                <strong>
                    <a @click.prevent="useRouter" :href="adminGroupsUrl">Groups</a>
                </strong>
                - A view of all groups along with the members of the group and the roles associated with each group.
            </li>
            <li>
                <strong>
                    <a @click.prevent="useRouter" :href="adminRolesUrl">Roles</a>
                </strong>
                - A view of all non-private roles along with the role type, and the users and groups that are
                associated, with the role. Also includes a view of the data library datasets that are associated with
                the role and the permissions applied to each dataset.
            </li>
            <li>
                <strong>
                    <a @click.prevent="useRouter" :href="adminFormsUrl">Forms</a>
                </strong>
                - Manage local form definitions.
            </li>
        </ul>

        <h4>Tool Management</h4>
        <ul>
            <li v-if="isToolShedInstalled">
                <strong>
                    <a @click.prevent="useRouter" :href="adminToolshedUrl">Install new tools</a>
                </strong>
                - Search and install new tools and other Galaxy utilities from the Tool Shed. See
                <a href="https://galaxyproject.org/admin/tools/add-tool-from-toolshed-tutorial" target="_blank"
                    >the tutorial</a
                >.
            </li>
            <li v-if="installingRepositoryIds">
                <strong>Monitor installation</strong> - View the status of tools that are being currently installed.
            </li>
            <template v-if="isRepoInstalled">
                <li>
                    <strong>Manage tools</strong> - View and administer installed tools and utilities on this Galaxy.
                </li>
                <li><strong>Manage metadata</strong> - Select on which repositories you want to reset metadata.</li>
            </template>
            <li>
                <strong>
                    <a @click.prevent="useRouter" :href="adminToolVersionsUrl">View lineage</a>
                </strong>
                - A view of a version lineages for all installed tools. Useful for debugging.
            </li>
            <li>
                <strong>
                    <a :href="migrationStagesUrl">View migration stages</a>
                </strong>
                - See the list of migration stages that moved sets of tools from the distribution to the Tool Shed.
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
        installingRepositoryIds: {
            type: String,
            required: true
        },
        isRepoInstalled: {
            type: Boolean,
            required: true
        },
        isToolShedInstalled: {
            type: Boolean,
            required: true
        }
    },
    methods: {
        useRouter: function(ev) {
            const Galaxy = getGalaxyInstance();
            Galaxy.page.router.push(ev.target.pathname.slice(root.length));
        }
    },
    computed: {
        migrationStagesUrl: () => `${root}admin/review_tool_migration_stages`, // NOT ROUTER
        adminDataTypesUrl: () => `${root}admin/data_types`,
        adminDataTablesUrl: () => `${root}admin/data_tables`,
        adminDisplayApplicationsUrl: () => `${root}admin/display_applications`,
        adminJobsUrl: () => `${root}admin/jobs`,
        adminDMUrl: () => `${root}admin/data_manager`,
        adminUsersUrl: () => `${root}admin/users`,
        adminQuotasUrl: () => `${root}admin/quotas`,
        adminGroupsUrl: () => `${root}admin/groups`,
        adminRolesUrl: () => `${root}admin/roles`,
        adminFormsUrl: () => `${root}admin/forms`,
        adminToolshedUrl: () => `${root}admin/toolshed`,
        adminToolVersionsUrl: () => `${root}admin/tool_versions`
    }
};
</script>
