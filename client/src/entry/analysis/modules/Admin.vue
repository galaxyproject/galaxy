<script setup>
import { computed } from "vue";
import { getGalaxyInstance } from "app";
import AdminPanel from "@/components/admin/AdminPanel.vue";
import SidePanel from "@/components/Panels/SidePanel.vue";

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
    <div id="columns">
        <SidePanel side="left" :current-panel="AdminPanel" :current-panel-properties="panelProperties" />
        <div id="center" class="center-style">
            <div class="center-container">
                <div class="center-panel" style="display: block">
                    <router-view :key="$route.fullPath" />
                </div>
            </div>
        </div>
    </div>
</template>
