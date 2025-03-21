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
            title: "服务器",
            items: [
                {
                    id: "admin-link-datatypes",
                    title: "数据类型",
                    route: "/admin/data_types",
                },
                {
                    id: "admin-link-data-tables",
                    title: "数据表",
                    route: "/admin/data_tables",
                },
                {
                    id: "admin-link-display-applications",
                    title: "显示应用程序",
                    route: "/admin/display_applications",
                },
                {
                    id: "admin-link-jobs",
                    title: "作业",
                    route: "/admin/jobs",
                },
                {
                    id: "admin-link-invocations",
                    title: "工作流调用",
                    route: "/admin/invocations",
                },
                {
                    id: "admin-link-local-data",
                    title: "本地数据",
                    route: "/admin/data_manager",
                },
                {
                    id: "admin-link-notifications",
                    title: "通知和广播",
                    route: "/admin/notifications",
                },
            ],
        },
        {
            title: "用户管理",
            items: [
                {
                    id: "admin-link-users",
                    title: "用户",
                    route: "/admin/users",
                },
                {
                    id: "admin-link-quotas",
                    title: "配额",
                    route: "/admin/quotas",
                    disabled: !adminProperties.value.enableQuotas,
                },
                {
                    id: "admin-link-groups",
                    title: "用户组",
                    route: "/admin/groups",
                },
                {
                    id: "admin-link-roles",
                    title: "角色",
                    route: "/admin/roles",
                },
                {
                    id: "admin-link-forms",
                    title: "表单",
                    route: "/admin/forms",
                },
            ],
        },
        {
            title: "工具管理",
            items: [
                {
                    id: "admin-link-toolshed",
                    title: "安装和卸载",
                    route: "/admin/toolshed",
                    disabled: !adminProperties.value.isToolshedInstalled,
                },
                {
                    id: "admin-link-metadata",
                    title: "管理元数据",
                    route: "/admin/reset_metadata",
                },
                {
                    id: "admin-link-allowlist",
                    title: "管理白名单",
                    route: "/admin/sanitize_allow",
                },
                {
                    id: "admin-link-manage-dependencies",
                    title: "管理依赖项",
                    route: "/admin/toolbox_dependencies",
                },
                {
                    id: "admin-link-error-stack",
                    title: "查看错误日志",
                    route: "/admin/error_stack",
                },
            ],
        },
    ];
});
</script>

<template>
    <ActivityPanel v-if="isConfigLoaded" title="管理" go-to-all-title="管理员主页" href="/admin">
        <template v-slot:header>
            <h3>Galaxy 版本 {{ adminProperties.versionMajor }}</h3>
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
