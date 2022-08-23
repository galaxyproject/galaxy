<template>
    <div id="columns">
        <SidePanel side="left" :currentPanel="getAdminPanel()" :current-panel-properties="panelProperties" />
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
            const Galaxy = getGalaxyInstance();
            return {
                versionMajor: Galaxy.config.version_major,
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
