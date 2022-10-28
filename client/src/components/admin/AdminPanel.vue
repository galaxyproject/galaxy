<template>
    <div class="unified-panel">
        <div class="unified-panel-header" unselectable="on">
            <div class="unified-panel-header-inner">
                <div class="panel-header-text">Galaxy Version {{ versionMajor }}</div>
            </div>
        </div>
        <div class="unified-panel-body">
            <div class="toolMenuContainer">
                <div class="toolSectionWrapper">
                    <div
                        v-for="(section, sectionIndex) in sections"
                        :key="sectionIndex"
                        class="toolSectionTitle pt-1 px-3">
                        <h2 class="font-weight-bold h-text mb-0">{{ section.title }}</h2>
                        <div class="toolSectionBody">
                            <div v-for="(item, itemIndex) in section.items" :key="itemIndex" class="toolTitle">
                                <router-link v-if="!item.disabled" :id="item.id" class="title-link" :to="item.route">
                                    <small class="name">{{ item.title }}</small>
                                </router-link>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
export default {
    props: {
        enableQuotas: {
            type: Boolean,
            default: false,
        },
        isToolshedInstalled: {
            type: Boolean,
            default: false,
        },
        versionMajor: {
            type: String,
            default: "",
        },
    },
    data() {
        return {
            sections: [
                {
                    title: "Server",
                    items: [
                        {
                            id: "admin-link-datatypes",
                            title: "Data Types",
                            route: "/admin/data_types",
                        },
                        {
                            id: "admin-link-data-tables",
                            title: "Data Tables",
                            route: "/admin/data_tables",
                        },
                        {
                            id: "admin-link-display-applications",
                            title: "Display Applications",
                            route: "/admin/display_applications",
                        },
                        {
                            id: "admin-link-jobs",
                            title: "Jobs",
                            route: "/admin/jobs",
                        },
                        {
                            id: "admin-link-invocations",
                            title: "Workflow Invocations",
                            route: "/admin/invocations",
                        },
                        {
                            id: "admin-link-local-data",
                            title: "Local Data",
                            route: "/admin/data_manager",
                        },
                    ],
                },
                {
                    title: "User Management",
                    items: [
                        {
                            id: "admin-link-users",
                            title: "Users",
                            route: "/admin/users",
                        },
                        {
                            id: "admin-link-quotas",
                            title: "Quotas",
                            route: "/admin/quotas",
                            disabled: !this.enableQuotas,
                        },
                        {
                            id: "admin-link-groups",
                            title: "Groups",
                            route: "/admin/groups",
                        },
                        {
                            id: "admin-link-roles",
                            title: "Roles",
                            route: "/admin/roles",
                        },
                        {
                            id: "admin-link-forms",
                            title: "Forms",
                            route: "/admin/forms",
                        },
                    ],
                },
                {
                    title: "Tool Management",
                    items: [
                        {
                            id: "admin-link-toolshed",
                            title: "Install and Uninstall",
                            route: "/admin/toolshed",
                            disabled: !this.isToolshedInstalled,
                        },
                        {
                            id: "admin-link-metadata",
                            title: "Manage Metadata",
                            route: "/admin/reset_metadata",
                        },
                        {
                            id: "admin-link-allowlist",
                            title: "Manage Allowlist",
                            route: "/admin/sanitize_allow",
                        },
                        {
                            id: "admin-link-manage-dependencies",
                            title: "Manage Dependencies",
                            route: "/admin/toolbox_dependencies",
                        },
                        {
                            id: "admin-link-tool-versions",
                            title: "View Lineage",
                            route: "/admin/tool_versions",
                        },
                        {
                            id: "admin-link-error-stack",
                            title: "View Error Logs",
                            route: "/admin/error_stack",
                        },
                    ],
                },
            ],
        };
    },
};
</script>
