<script setup lang="ts">
import { faCaretDown } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";

import { useToolStore } from "@/stores/toolStore";
import localize from "@/utils/localization";
import { errorMessageAsString, rethrowSimple } from "@/utils/simple-error";

import { types_to_icons } from "./utilities";

import LoadingSpan from "../LoadingSpan.vue";
import FavoritesButton from "./Buttons/FavoritesButton.vue";
import PanelViewMenu from "./Menus/PanelViewMenu.vue";
import ToolBox from "./ToolBox.vue";
import Heading from "@/components/Common/Heading.vue";

const props = defineProps({
    workflow: { type: Boolean, default: false },
    dataManagers: { type: Array, default: null },
    moduleSections: { type: Array, default: null },
    useSearchWorker: { type: Boolean, default: true },
});

const emit = defineEmits<{
    (e: "onInsertTool", toolId: string, toolName: string): void;
    (e: "onInsertModule", moduleName: string, moduleTitle: string | undefined): void;
    (e: "onInsertWorkflow", workflowLatestId: string | undefined, workflowName: string): void;
    (e: "onInsertWorkflowSteps", workflowId: string, workflowStepCount: number | undefined): void;
}>();

const arePanelsFetched = ref(false);
const toolStore = useToolStore();
const { currentPanelView, defaultPanelView, isPanelPopulated, loading, panel, panelViews, currentPanel } =
    storeToRefs(toolStore);

const loadingView = ref<string | undefined>(undefined);
const query = ref("");
const showAdvanced = ref(false);
const errorMessage = ref<string | undefined>(undefined);

const showFavorites = computed({
    get() {
        return query.value.includes("#favorites");
    },
    set(value) {
        if (value) {
            if (!query.value.includes("#favorites")) {
                query.value = `#favorites ${query.value}`.trim();
            }
        } else {
            query.value = query.value.replace("#favorites", "").trim();
        }
    },
});

const toolPanelHeader = computed(() => {
    if (showAdvanced.value) {
        return localize("Advanced Tool Search");
    } else if (loading.value && loadingView.value) {
        return localize(loadingView.value);
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

async function initializeToolPanel() {
    try {
        await toolStore.fetchPanelViews();
        await initializeTools();
    } catch (error) {
        console.error(error);
        errorMessage.value = errorMessageAsString(error);
    } finally {
        arePanelsFetched.value = true;
    }
}

async function initializeTools() {
    try {
        await toolStore.fetchTools();
        await toolStore.initCurrentPanelView(defaultPanelView.value);
    } catch (error: any) {
        console.error("ToolPanel - Intialize error:", error);
        errorMessage.value = errorMessageAsString(error);
        rethrowSimple(error);
    }
}

async function updatePanelView(panelView: string) {
    loadingView.value = panelViews.value[panelView]?.name;
    await toolStore.setCurrentPanelView(panelView);
    loadingView.value = undefined;
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

watch(
    () => query.value,
    (newQuery) => {
        showFavorites.value = newQuery.includes("#favorites");
    }
);

// if currentPanelView ever becomes null || "", load tools
watch(
    () => currentPanelView.value,
    async (newVal) => {
        query.value = "";
        if ((!newVal || !panel.value[newVal]) && arePanelsFetched.value) {
            await initializeTools();
        }
    }
);

initializeToolPanel();
</script>

<template>
    <div v-if="arePanelsFetched" id="toolbox-panel" class="unified-panel" aria-labelledby="toolbox-heading">
        <div unselectable="on">
            <div class="unified-panel-header-inner mx-3 my-2 d-flex justify-content-between">
                <PanelViewMenu
                    v-if="panelViews && Object.keys(panelViews).length > 1"
                    :panel-views="panelViews"
                    :current-panel-view="currentPanelView"
                    :show-advanced.sync="showAdvanced"
                    :store-loading="loading"
                    @updatePanelView="updatePanelView">
                    <template v-slot:panel-view-selector>
                        <div class="d-flex justify-content-between panel-view-selector">
                            <div>
                                <span
                                    v-if="viewIcon && !loading"
                                    :class="['fas', `fa-${viewIcon}`, 'mr-1']"
                                    data-description="panel view header icon" />
                                <Heading
                                    id="toolbox-heading"
                                    :class="!showAdvanced && toolPanelHeader !== 'Tools' && 'font-italic'"
                                    h2
                                    inline
                                    size="sm">
                                    <span v-if="loading && loadingView">
                                        <LoadingSpan :message="toolPanelHeader" />
                                    </span>
                                    <span v-else>{{ toolPanelHeader }}</span>
                                </Heading>
                            </div>
                            <div v-if="!showAdvanced" class="panel-header-buttons">
                                <FontAwesomeIcon :icon="faCaretDown" />
                            </div>
                        </div>
                    </template>
                </PanelViewMenu>
                <div v-if="!showAdvanced" class="panel-header-buttons">
                    <FavoritesButton v-model="showFavorites" />
                </div>
            </div>
        </div>
        <ToolBox
            v-if="isPanelPopulated"
            :workflow="props.workflow"
            :panel-query.sync="query"
            :panel-view="currentPanelView"
            :show-advanced.sync="showAdvanced"
            :data-managers="dataManagers"
            :module-sections="moduleSections"
            :use-search-worker="useSearchWorker"
            @updatePanelView="updatePanelView"
            @onInsertTool="onInsertTool"
            @onInsertModule="onInsertModule"
            @onInsertWorkflow="onInsertWorkflow"
            @onInsertWorkflowSteps="onInsertWorkflowSteps" />
        <div v-else-if="errorMessage" data-description="tool panel error message">
            <b-alert class="m-2" variant="danger" show>
                {{ errorMessage }}
            </b-alert>
        </div>
        <div v-else>
            <b-badge class="alert-info w-100">
                <LoadingSpan message="Loading Toolbox" />
            </b-badge>
        </div>
    </div>
    <b-alert v-else-if="currentPanel" class="m-2" variant="info" show>
        <LoadingSpan message="Loading Toolbox" />
    </b-alert>
</template>

<style lang="scss" scoped>
@import "theme/blue.scss";

.panel-view-selector {
    color: $panel-header-text-color;
}
</style>
