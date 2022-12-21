<template>
    <div id="columns">
        <SidePanel side="left" :current-panel="getAdminPanel()" :current-panel-properties="panelProperties" />
        <div id="center">
            <div class="center-container">
                <div class="center-panel" style="display: block">
                    <router-view :key="$route.fullPath" />
                </div>
            </div>
        </div>
    </div>
</template>
<script>
import { getGalaxyInstance } from "app";
import AdminPanel from "components/admin/AdminPanel";
import SidePanel from "components/Panels/SidePanel";

export default {
    components: {
        SidePanel,
    },
    computed: {
        panelProperties() {
            const config = getGalaxyInstance().config;
            return {
                enableQuotas: config.enable_quotas,
                isToolshedInstalled: config.tool_shed_urls && config.tool_shed_urls.length > 0,
                versionMajor: config.version_major,
            };
        },
    },
    methods: {
        getAdminPanel() {
            return AdminPanel;
        },
    },
};
</script>
