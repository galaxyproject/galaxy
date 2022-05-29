<template>
    <div id="columns">
        <SidePanel side="left" :currentPanel="getToolBox()" :currentPanelProperties="toolBoxProperties" />
        <div id="center">
            <div class="center-container">
                <iframe
                    v-if="src"
                    id="galaxy_main"
                    name="galaxy_main"
                    frameborder="0"
                    class="center-frame"
                    title="galaxy main frame"
                    :src="srcWithRoot" />
                <div class="center-panel" style="display: block;">
                    <router-view :key="$route.fullPath" />
                </div>
            </div>
        </div>
        <SidePanel side="right" :currentPanel="getHistoryIndex()" :currentPanelProperties="{}" />
    </div>
</template>
<script>
import { getAppRoot } from "onload";
import store from "store";
import { urlData } from "utils/url";
import Query from "utils/query-string-parsing";
import { getGalaxyInstance } from "app";
import HistoryIndex from "components/History/Index";
import ToolBox from "components/Panels/ProviderAwareToolBox";
import SidePanel from "components/Panels/SidePanel";

export default {
    components: {
        HistoryIndex,
        SidePanel,
    },
    props: {
        src: {
            type: String,
            default: null,
        },
    },
    data() {
        return {};
    },
    computed: {
        toolBoxProperties() {
            const Galaxy = getGalaxyInstance();
            return {
                storedWorkflowMenuEntries: Galaxy.config.stored_workflow_menu_entries,
            };
        },
        srcWithRoot() {
            return `${getAppRoot()}${this.src}`;
        },
    },
    methods: {
        getHistoryIndex() {
            return HistoryIndex;
        },
        getToolBox() {
            return ToolBox;
        },
    },
};
</script>
