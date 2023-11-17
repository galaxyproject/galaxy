<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCaretDown } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import axios from "axios";
import { storeToRefs } from "pinia";
import { computed, onMounted, ref, watch } from "vue";

import { getAppRoot } from "@/onload";
import { type PanelView, useToolStore } from "@/stores/toolStore";
import localize from "@/utils/localization";

import { types_to_icons } from "./utilities";

import LoadingSpan from "../LoadingSpan.vue";
import FavoritesButton from "./Buttons/FavoritesButton.vue";
import PanelViewMenu from "./Menus/PanelViewMenu.vue";
import ToolBox from "./ToolBox.vue";
import Heading from "@/components/Common/Heading.vue";

library.add(faCaretDown);

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

const arePanelsFetched = ref(false);
const defaultPanelView = ref("");
const toolStore = useToolStore();
const { currentPanelView, isPanelPopulated } = storeToRefs(toolStore);

const query = ref("");
const panelViews = ref<Record<string, PanelView> | null>(null);
const showAdvanced = ref(false);

onMounted(async () => {
    await axios
        .get(`${getAppRoot()}api/tool_panels`)
        .then(async ({ data }) => {
            const { default_panel_view, views } = data;
            defaultPanelView.value = default_panel_view;
            panelViews.value = views;
            await initializeTools();
        })
        .catch((error) => {
            console.error(error);
        })
        .finally(() => {
            arePanelsFetched.value = true;
        });
});

watch(
    () => currentPanelView.value,
    () => {
        query.value = "";
    }
);

// if currentPanelView ever becomes null || "", load tools
watch(
    () => currentPanelView.value,
    async (newVal) => {
        if (!newVal && arePanelsFetched.value) {
            await initializeTools();
        }
    }
);

const toolPanelHeader = computed(() => {
    if (showAdvanced.value) {
        return localize("Advanced Tool Search");
    } else if (
        currentPanelView.value !== "default" &&
        panelViews.value &&
        panelViews.value[currentPanelView.value]?.name
    ) {
        return localize(panelViews.value[currentPanelView.value]?.name);
    } else {
        return localize("Tools");
    }
});

const viewIcon = computed(() => {
    if (showAdvanced.value) {
        return "search";
    } else if (
        currentPanelView.value !== "default" &&
        panelViews.value &&
        typeof panelViews.value[currentPanelView.value]?.view_type === "string"
    ) {
        const viewType = panelViews.value[currentPanelView.value]?.view_type;
        return viewType ? types_to_icons[viewType] : null;
    } else {
        return null;
    }
});

async function initializeTools() {
    try {
        await toolStore.fetchTools();
        await toolStore.initCurrentPanelView(defaultPanelView.value);
    } catch (error: any) {
        console.error("ToolPanel - Intialize error:", error);
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
    <div v-if="arePanelsFetched" class="unified-panel" aria-labelledby="toolbox-heading">
        <div unselectable="on">
            <div class="unified-panel-header-inner mx-3 my-2 d-flex justify-content-between">
                <PanelViewMenu
                    v-if="panelViews && Object.keys(panelViews).length > 1"
                    :panel-views="panelViews"
                    :current-panel-view="currentPanelView"
                    @updatePanelView="updatePanelView">
                    <template v-slot:panel-view-selector>
                        <div class="d-flex justify-content-between panel-view-selector">
                            <div>
                                <span
                                    v-if="viewIcon"
                                    :class="['fas', `fa-${viewIcon}`, 'mr-1']"
                                    data-description="panel view header icon" />
                                <Heading
                                    id="toolbox-heading"
                                    :class="!showAdvanced && toolPanelHeader !== 'Tools' && 'font-italic'"
                                    h2
                                    inline
                                    size="sm"
                                    >{{ toolPanelHeader }}
                                </Heading>
                            </div>
                            <div v-if="!showAdvanced" class="panel-header-buttons">
                                <FontAwesomeIcon icon="caret-down" />
                            </div>
                        </div>
                    </template>
                </PanelViewMenu>
                <div v-if="!showAdvanced" class="panel-header-buttons">
                    <FavoritesButton :query="query" @onFavorites="(q) => (query = q)" />
                </div>
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

<style lang="scss" scoped>
@import "theme/blue.scss";

.panel-view-selector {
    color: $panel-header-text-color;
}
</style>
