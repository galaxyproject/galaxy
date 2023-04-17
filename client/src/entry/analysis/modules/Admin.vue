<script setup>
import { computed } from "vue";
import { getGalaxyInstance } from "app";
import AdminPanel from "@/components/admin/AdminPanel.vue";
import FlexPanel from "@/components/Panels/FlexPanel.vue";

const panelProperties = computed(() => {
    const config = getGalaxyInstance().config;
    return {
        enableQuotas: config.enable_quotas,
        isToolshedInstalled: config.tool_shed_urls && config.tool_shed_urls.length > 0,
        versionMajor: config.version_major,
    };
});
</script>

<template>
    <div id="columns" class="d-flex">
        <FlexPanel side="left">
            <AdminPanel v-bind="panelProperties" />
        </FlexPanel>
        <div id="center" class="overflow-auto p-3 w-100">
            <router-view :key="$route.fullPath" />
        </div>
    </div>
</template>
