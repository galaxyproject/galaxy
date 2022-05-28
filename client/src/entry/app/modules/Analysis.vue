<template>
    <div id="columns">
        <SidePanel side="left" :currentPanel="getToolBox()" :currentPanelProperties="ToolBoxProperties" />
        <div id="center" />
        <SidePanel side="right" :currentPanel="getHistoryIndex()" :currentPanelProperties="{}" />
    </div>
</template>
<script>
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
    data() {
        return {};
    },
    computed: {
        ToolBoxProperties() {
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
    },
};
</script>
