<script setup>
import { computed } from "vue";
import { useConfig } from "@/composables/config";
import AdminPanel from "@/components/admin/AdminPanel.vue";
import FlexPanel from "@/components/Panels/FlexPanel.vue";

const { config, isLoaded } = useConfig();

const panelProperties = computed(() => {
    return {
        enableQuotas: config.value.enable_quotas,
        isToolshedInstalled: config.value.tool_shed_urls && config.value.tool_shed_urls.length > 0,
        versionMajor: config.value.version_major,
    };
});
</script>

<template>
    <div v-if="isLoaded" id="columns" class="d-flex">
        <FlexPanel side="left">
            <AdminPanel v-bind="panelProperties" />
        </FlexPanel>
        <div id="center" class="overflow-auto p-3 w-100">
            <router-view :key="$route.fullPath" />
        </div>
    </div>
</template>
