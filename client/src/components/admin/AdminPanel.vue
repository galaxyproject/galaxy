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
                                <a class="title-link">
                                    {{ item.title }}
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
                            title: "Data Types",
                            url: "admin/data_types",
                            target: "__use_router__",
                            id: "admin-link-datatypes",
                        },
                        {
                            title: "Data Tables",
                            url: "admin/data_tables",
                            target: "__use_router__",
                            id: "admin-link-data-tables",
                        },
                        {
                            title: "Display Applications",
                            url: "admin/display_applications",
                            target: "__use_router__",
                            id: "admin-link-display-applications",
                        },
                        {
                            title: "Jobs",
                            url: "admin/jobs",
                            target: "__use_router__",
                            id: "admin-link-jobs",
                        },
                        {
                            title: "Workflow Invocations",
                            url: "admin/invocations",
                            target: "__use_router__",
                            id: "admin-link-invocations",
                        },
                        {
                            title: "Local Data",
                            url: "admin/data_manager",
                            target: "__use_router__",
                            id: "admin-link-local-data",
                        },
                    ],
                },
                {
                    title: "User Management",
                    items: [
                        {
                            title: "Users",
                            url: "admin/users",
                            target: "__use_router__",
                            id: "admin-link-users",
                        },
                        {
                            title: "Quotas",
                            url: "admin/quotas",
                            target: "__use_router__",
                            enabled: this.enableQuotas,
                            id: "admin-link-quotas",
                        },
                        {
                            title: "Groups",
                            url: "admin/groups",
                            target: "__use_router__",
                            id: "admin-link-groups",
                        },
                        {
                            title: "Roles",
                            url: "admin/roles",
                            target: "__use_router__",
                            id: "admin-link-roles",
                        },
                        {
                            title: "Forms",
                            url: "admin/forms",
                            target: "__use_router__",
                            id: "admin-link-forms",
                        },
                    ],
                },
                {
                    title: "Tool Management",
                    items: [
                        {
                            title: "Install and Uninstall",
                            url: "admin/toolshed",
                            target: "__use_router__",
                            id: "admin-link-toolshed",
                            enabled: this.isToolshedInstalled,
                        },
                        {
                            title: "Manage Metadata",
                            url: "admin/reset_metadata",
                            id: "admin-link-metadata",
                            enabled: this.isRepoInstalled,
                            target: "__use_router__",
                        },
                        {
                            title: "Manage Allowlist",
                            url: "admin/sanitize_allow",
                            id: "admin-link-allowlist",
                            target: "__use_router__",
                        },
                        {
                            title: "Manage Dependencies",
                            url: "admin/toolbox_dependencies",
                            target: "__use_router__",
                            id: "admin-link-manage-dependencies",
                        },
                        {
                            title: "Manage Dependencies (legacy)",
                            url: "admin/manage_tool_dependencies",
                        },
                        {
                            title: "View Lineage",
                            url: "admin/tool_versions",
                            target: "__use_router__",
                            id: "admin-link-tool-versions",
                        },
                        {
                            title: "View Error Logs",
                            url: "admin/error_stack",
                            id: "admin-link-error-stack",
                            target: "__use_router__",
                        },
                    ],
                },
            ],
        };
    },
};
</script>
