<script setup lang="ts">
import { computed } from "vue";

import { useConfig } from "@/composables/config";

import ActivityPanel from "@/components/Panels/ActivityPanel.vue";

const { config, isConfigLoaded } = useConfig();

const adminProperties = computed(() => {
    return {
        enableQuotas: config.value.enable_quotas,
        isToolshedInstalled: config.value.tool_shed_urls?.length > 0,
        versionMajor: config.value.version_major,
    };
});

const sections = computed(() => {
    return [
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
                {
                    id: "admin-link-notifications",
                    title: "Notifications and Broadcasts",
                    route: "/admin/notifications",
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
                    disabled: !adminProperties.value.enableQuotas,
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
                    disabled: !adminProperties.value.isToolshedInstalled,
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
                    id: "admin-link-error-stack",
                    title: "View Error Logs",
                    route: "/admin/error_stack",
                },
            ],
        },
    ];
});
</script>

<template>
    <ActivityPanel v-if="isConfigLoaded" title="Administration" go-to-all-title="Admin Home" href="/admin">
        <template v-slot:header>
            <h3>Galaxy Version {{ adminProperties.versionMajor }}</h3>
        </template>
        <div class="unified-panel-body">
            <div class="toolMenuContainer">
                <div class="toolSectionWrapper">
                    <div v-for="(section, sectionIndex) in sections" :key="sectionIndex" class="toolSectionTitle pt-2">
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
    </ActivityPanel>
</template>
