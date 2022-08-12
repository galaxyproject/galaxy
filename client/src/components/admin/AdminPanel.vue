<template>
    <div class="unified-panel">
        <div unselectable="on">
            <div class="unified-panel-header-inner">
                <nav class="d-flex justify-content-between mx-3 my-2">
                    <h4 v-localize class="m-1">Tools</h4>
                    <div class="panel-header-buttons">
                        <b-button-group>
                            <favorites-button :query="query" @onFavorites="onQuery" />
                            <panel-view-button
                                v-if="panelViews && Object.keys(panelViews).length > 1"
                                :panel-views="panelViews"
                                :current-panel-view="currentPanelView"
                                @updatePanelView="updatePanelView" />
                        </b-button-group>
                    </div>
                </nav>
            </div>
        </div>
        <div class="unified-panel-controls">
            <tool-search
                :current-panel-view="currentPanelView"
                :placeholder="titleSearchTools"
                :query="query"
                @onQuery="onQuery"
                @onResults="onResults" />
            <upload-button />
            <div v-if="hasResults" class="pb-2">
                <b-button size="sm" class="w-100" @click="onToggle">
                    <span :class="buttonIcon" />
                    <span class="mr-1">{{ buttonText }}</span>
                </b-button>
            </div>
            <div v-else-if="queryTooShort" class="pb-2">
                <b-badge class="alert-danger w-100">Search string too short!</b-badge>
            </div>
            <div v-else-if="queryFinished" class="pb-2">
                <b-badge class="alert-danger w-100">No results found!</b-badge>
            </div>
        </div>
        <div class="unified-panel-body">
            <div class="toolMenuContainer">
                <div class="toolMenu">
                    <tool-section
                        v-for="(section, key) in sections"
                        :key="key"
                        :category="section"
                        :query-filter="queryFilter"
                        @onClick="onOpen" />
                </div>
                <tool-section :category="{ text: workflowTitle }" />
                <div id="internal-workflows" class="toolSectionBody">
                    <div class="toolSectionBg" />
                    <div v-for="wf in workflows" :key="wf.id" class="toolTitle">
                        <a class="title-link" :href="wf.href">{{ wf.title }}</a>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import _l from "utils/localization";

export default {
    props: {
        versionMajor: {
            type: String,
            default: "",
        },
        enable_quotas: {
            type: Boolean,
            default: false,
        },
    },
    data() {
        return {
            categories: [
                {
                    title: _l("Server"),
                    items: [
                        {
                            title: _l("Data Types"),
                            url: "admin/data_types",
                            target: "__use_router__",
                            id: "admin-link-datatypes",
                        },
                        {
                            title: _l("Data Tables"),
                            url: "admin/data_tables",
                            target: "__use_router__",
                            id: "admin-link-data-tables",
                        },
                        {
                            title: _l("Display Applications"),
                            url: "admin/display_applications",
                            target: "__use_router__",
                            id: "admin-link-display-applications",
                        },
                        {
                            title: _l("Jobs"),
                            url: "admin/jobs",
                            target: "__use_router__",
                            id: "admin-link-jobs",
                        },
                        {
                            title: _l("Workflow Invocations"),
                            url: "admin/invocations",
                            target: "__use_router__",
                            id: "admin-link-invocations",
                        },
                        {
                            title: _l("Local Data"),
                            url: "admin/data_manager",
                            target: "__use_router__",
                            id: "admin-link-local-data",
                        },
                    ],
                },
                {
                    title: _l("User Management"),
                    items: [
                        {
                            title: _l("Users"),
                            url: "admin/users",
                            target: "__use_router__",
                            id: "admin-link-users",
                        },
                        {
                            title: _l("Quotas"),
                            url: "admin/quotas",
                            target: "__use_router__",
                            enabled: this.config.enable_quotas,
                            id: "admin-link-quotas",
                        },
                        {
                            title: _l("Groups"),
                            url: "admin/groups",
                            target: "__use_router__",
                            id: "admin-link-groups",
                        },
                        {
                            title: _l("Roles"),
                            url: "admin/roles",
                            target: "__use_router__",
                            id: "admin-link-roles",
                        },
                        {
                            title: _l("Forms"),
                            url: "admin/forms",
                            target: "__use_router__",
                            id: "admin-link-forms",
                        },
                    ],
                },
                {
                    title: _l("Tool Management"),
                    items: [
                        {
                            title: _l("Install and Uninstall"),
                            url: "admin/toolshed",
                            target: "__use_router__",
                            id: "admin-link-toolshed",
                            enabled: this.settings.is_tool_shed_installed,
                        },
                        {
                            title: _l("Manage Metadata"),
                            url: "admin/reset_metadata",
                            id: "admin-link-metadata",
                            enabled: this.settings.is_repo_installed,
                            target: "__use_router__",
                        },
                        {
                            title: _l("Manage Allowlist"),
                            url: "admin/sanitize_allow",
                            id: "admin-link-allowlist",
                            target: "__use_router__",
                        },
                        {
                            title: _l("Manage Dependencies"),
                            url: "admin/toolbox_dependencies",
                            target: "__use_router__",
                            id: "admin-link-manage-dependencies",
                        },
                        {
                            title: _l("Manage Dependencies (legacy)"),
                            url: "admin/manage_tool_dependencies",
                        },
                        {
                            title: _l("View Lineage"),
                            url: "admin/tool_versions",
                            target: "__use_router__",
                            id: "admin-link-tool-versions",
                        },
                        {
                            title: _l("View Error Logs"),
                            url: "admin/error_stack",
                            id: "admin-link-error-stack",
                            target: "__use_router__",
                        },
                    ],
                },
            ],
        };
    },
    computed: {},
};
</script>
