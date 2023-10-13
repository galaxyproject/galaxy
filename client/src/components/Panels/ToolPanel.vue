<script setup lang="ts">
import { storeToRefs } from "pinia";
import { ref, watch } from "vue";

import { useConfig } from "@/composables/config";
import { useToolStore } from "@/stores/toolStore";
import localize from "@/utils/localization";

import LoadingSpan from "../LoadingSpan.vue";
import FavoritesButton from "./Buttons/FavoritesButton.vue";
import PanelViewButton from "./Buttons/PanelViewButton.vue";
import ToolBox from "./ToolBox.vue";
import Heading from "@/components/Common/Heading.vue";

const props = defineProps({
    workflow: { type: Boolean, default: false },
    editorWorkflows: { type: Array, default: null },
    dataManagers: { type: Array, default: null },
    moduleSections: { type: Array, default: null },
});

const emit = defineEmits<{
    (e: "onInsertTool", toolId: string, toolName: string): void;
    (e: "onInsertModule", moduleName: string, moduleTitle: string | undefined): void;
    (e: "onInsertWorkflow", workflowLatestId: string | undefined, workflowName: string): void;
    (e: "onInsertWorkflowSteps", workflowId: string, workflowStepCount: number | undefined): void;
}>();

const { isConfigLoaded, config } = useConfig();
const toolStore = useToolStore();
const { currentPanelView, isPanelPopulated } = storeToRefs(toolStore);

const query = ref("");
const panelViews = ref(null);
const showAdvanced = ref(false);

watch(
    () => currentPanelView.value,
    () => {
        query.value = "";
    }
);

// as soon as config is loaded, load tools
watch(
    () => isConfigLoaded.value,
    async (newVal) => {
        if (newVal) {
            await loadTools();
        }
    },
    { immediate: true }
);

// if currentPanelView ever becomes null || "", load tools
watch(
    () => currentPanelView.value,
    async (newVal) => {
        if (!newVal && isConfigLoaded.value) {
            await loadTools();
        }
    }
);

async function loadTools() {
    panelViews.value = panelViews.value === null ? config.value.panel_views : panelViews.value;
    try {
        await toolStore.fetchTools();
        await toolStore.initCurrentPanelView(config.value.default_panel_view);
    } catch (error: any) {
        console.error("ToolPanel - Load tools error:", error);
    }
}

async function updatePanelView(panelView: string) {
    await toolStore.setCurrentPanelView(panelView);
}

function onInsertTool(toolId: string, toolName: string) {
    emit("onInsertTool", toolId, toolName);
}

function onInsertModule(moduleName: string, moduleTitle: string | undefined) {
    emit("onInsertModule", moduleName, moduleTitle);
}

function onInsertWorkflow(workflowId: string | undefined, workflowName: string) {
    emit("onInsertWorkflow", workflowId, workflowName);
}

function onInsertWorkflowSteps(workflowId: string, workflowStepCount: number | undefined) {
    emit("onInsertWorkflowSteps", workflowId, workflowStepCount);
}
</script>

<template>
    <div v-if="isConfigLoaded" class="unified-panel" aria-labelledby="toolbox-heading">
        <div unselectable="on">
            <div class="unified-panel-header-inner">
                <nav class="d-flex justify-content-between mx-3 my-2">
                    <Heading v-if="!showAdvanced" id="toolbox-heading" h2 inline size="sm">{{
                        localize("Tools")
                    }}</Heading>
                    <Heading v-else id="toolbox-heading" h2 inline size="sm">{{
                        localize("Advanced Tool Search")
                    }}</Heading>
                    <div class="panel-header-buttons">
                        <b-button-group>
                            <FavoritesButton v-if="!showAdvanced" :query="query" @onFavorites="(q) => (query = q)" />
                            <PanelViewButton
                                v-if="panelViews && Object.keys(panelViews).length > 1"
                                :panel-views="panelViews"
                                :current-panel-view="currentPanelView"
                                @updatePanelView="updatePanelView" />
                        </b-button-group>
                    </div>
                </nav>
            </div>
        </div>
        <ToolBox
            v-if="isPanelPopulated"
            :workflow="props.workflow"
            :panel-query.sync="query"
            :panel-view="currentPanelView"
            :show-advanced.sync="showAdvanced"
            :editor-workflows="editorWorkflows"
            :data-managers="dataManagers"
            :module-sections="moduleSections"
            @updatePanelView="updatePanelView"
            @onInsertTool="onInsertTool"
            @onInsertModule="onInsertModule"
            @onInsertWorkflow="onInsertWorkflow"
            @onInsertWorkflowSteps="onInsertWorkflowSteps" />
        <div v-else>
            <b-badge class="alert-info w-100">
                <LoadingSpan message="Loading Toolbox" />
            </b-badge>
        </div>
    </div>
</template>
