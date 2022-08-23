<template>
    <div id="columns">
        <SidePanel side="left" :currentPanel="getAdminPanel()" />
        <div id="center">
            <div class="center-container m-2" style="overflow-y: auto">
                <router-view :key="$route.fullPath" />
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
    methods: {
        getAdminPanel() {
            return AdminPanel;
        },
    },
};
</script>
