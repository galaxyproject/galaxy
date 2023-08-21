<template>
    <ToolPanelViewProvider
        v-if="isConfigLoaded && config.default_panel_view"
        v-slot="{ currentPanel, currentPanelView }"
        class="d-flex flex-column"
        :panel-view="config.default_panel_view">
        <ToolBox
            v-if="currentPanelView"
            :toolbox="currentPanel"
            :panel-views="config.panel_views"
            :current-panel-view="currentPanelView"
            @updatePanelView="updatePanelView">
        </ToolBox>
    </ToolPanelViewProvider>
</template>

<script>
import ToolPanelViewProvider from "components/providers/ToolPanelViewProvider";
import { mapActions } from "vuex";

import { useConfig } from "@/composables/config";

import ToolBox from "./ToolBox";

export default {
    components: {
        ToolBox,
        ToolPanelViewProvider,
    },
    setup() {
        const { config, isConfigLoaded } = useConfig(true);
        return { config, isConfigLoaded };
    },
    methods: {
        updatePanelView(panelView) {
            this.setCurrentPanelView(panelView);
        },
        ...mapActions("panels", ["setCurrentPanelView"]),
    },
};
</script>
