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
                        {{ section.title }}
                        <div class="toolSectionBody">
                            <div v-for="(item, itemIndex) in section.items" :key="itemIndex" class="toolTitle">
                                <a class="title-link" :id="item.id">
                                    <span class="name">{{ item.title }}</span>
                                </a>
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
        isRepoInstalled: {
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
                            url: "admin/data_types",
                        },
                        {
                            id: "admin-link-data-tables",
                            title: "Data Tables",
                            url: "admin/data_tables",
                        },
                        {
                            id: "admin-link-display-applications",
                            title: "Display Applications",
                            url: "admin/display_applications",
                        },
                        {
                            id: "admin-link-jobs",
                            title: "Jobs",
                            url: "admin/jobs",
                        },
                        {
                            id: "admin-link-invocations",
                            title: "Workflow Invocations",
                            url: "admin/invocations",
                        },
                        {
                            id: "admin-link-local-data",
                            title: "Local Data",
                            url: "admin/data_manager",
                        },
                    ],
                },
                {
                    title: "User Management",
                    items: [
                        {
                            id: "admin-link-users",
                            title: "Users",
                            url: "admin/users",
                        },
                        {
                            id: "admin-link-quotas",
                            title: "Quotas",
                            url: "admin/quotas",
                            enabled: this.enableQuotas,
                        },
                        {
                            id: "admin-link-groups",
                            title: "Groups",
                            url: "admin/groups",
                        },
                        {
                            id: "admin-link-roles",
                            title: "Roles",
                            url: "admin/roles",
                        },
                        {
                            id: "admin-link-forms",
                            title: "Forms",
                            url: "admin/forms",
                        },
                    ],
                },
                {
                    title: "Tool Management",
                    items: [
                        {
                            id: "admin-link-toolshed",
                            title: "Install and Uninstall",
                            url: "admin/toolshed",
                            enabled: this.isToolshedInstalled,
                        },
                        {
                            id: "admin-link-metadata",
                            title: "Manage Metadata",
                            url: "admin/reset_metadata",
                            enabled: this.isRepoInstalled,
                        },
                        {
                            id: "admin-link-allowlist",
                            title: "Manage Allowlist",
                            url: "admin/sanitize_allow",
                        },
                        {
                            id: "admin-link-manage-dependencies",
                            title: "Manage Dependencies",
                            url: "admin/toolbox_dependencies",
                        },
                        {
                            id: "admin-link-manage-dependencies-legacy",
                            title: "Manage Dependencies (legacy)",
                            url: "admin/manage_tool_dependencies",
                        },
                        {
                            id: "admin-link-tool-versions",
                            title: "View Lineage",
                            url: "admin/tool_versions",
                        },
                        {
                            id: "admin-link-error-stack",
                            title: "View Error Logs",
                            url: "admin/error_stack",
                        },
                    ],
                },
            ],
        };
    },
};
</script>
