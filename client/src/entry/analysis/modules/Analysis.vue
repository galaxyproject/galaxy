<template>
    <div id="columns">
        <SidePanel side="left" :currentPanel="getToolBox()" :currentPanelProperties="toolBoxProperties" />
        <div id="center">
            <div class="center-container">
                <CenterPanel v-show="showCenter" id="galaxy_main" @load="onLoad" />
                <div v-show="!showCenter" class="center-panel" style="display: block">
                    <router-view :key="$route.fullPath" />
                </div>
            </div>
        </div>
        <SidePanel side="right" :currentPanel="getHistoryIndex()" :currentPanelProperties="{}" />
    </div>
</template>
<script>
import { getGalaxyInstance } from "app";
import HistoryIndex from "components/History/Index";
import ToolBox from "components/Panels/ProviderAwareToolBox";
import SidePanel from "components/Panels/SidePanel";
import CenterPanel from "./CenterPanel";

export default {
    components: {
        CenterPanel,
        SidePanel,
    },
    data() {
        return {
            showCenter: false,
        };
    },
    mounted() {
        // Using a custom event here which, in contrast to watching $route,
        // always fires when a route is pushed instead of validating it first.
        this.$router.app.$on("router-push", () => {
            this.showCenter = false;
        });
    },
    computed: {
        toolBoxProperties() {
            const Galaxy = getGalaxyInstance();
            return {
                storedWorkflowMenuEntries: Galaxy.config.stored_workflow_menu_entries,
            };
        },
    },
    methods: {
        getHistoryIndex() {
            return HistoryIndex;
        },
        getToolBox() {
            return ToolBox;
        },
        onLoad() {
            this.showCenter = true;
        },
    },
};
</script>
