<script setup lang="ts">
import { faCaretDown } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";

import { useToolStore } from "@/stores/toolStore";
import { useUserStore } from "@/stores/userStore";
import localize from "@/utils/localization";
import { errorMessageAsString } from "@/utils/simple-error";

import { types_to_icons } from "./utilities";

import LoadingSpan from "../LoadingSpan.vue";
import FavoritesButton from "./Buttons/FavoritesButton.vue";
import PanelViewMenu from "./Menus/PanelViewMenu.vue";
import ToolBox from "./ToolBox.vue";
import Heading from "@/components/Common/Heading.vue";

const toolStore = useToolStore();

const userStore = useUserStore();
const props = defineProps({
    dataManagers: { type: Array, default: null },
    moduleSections: { type: Array, default: null },
    useSearchWorker: { type: Boolean, default: true },
    workflow: { type: Boolean, default: false },
});

const emit = defineEmits<{
    (e: "onInsertModule", moduleName: string, moduleTitle: string | undefined): void;
    (e: "onInsertTool", toolId: string, toolName: string): void;
    (e: "onInsertWorkflow", workflowLatestId: string | undefined, workflowName: string): void;
    (e: "onInsertWorkflowSteps", workflowId: string, workflowStepCount: number | undefined): void;
}>();

const { currentPanelView, currentToolSections, isPanelPopulated, loading, panels, toolSections } =
    storeToRefs(toolStore);

const errorMessage = ref("");
const panelName = ref("");
const panelsFetched = ref(false);
const query = ref("");
const showAdvanced = ref(false);

const panelIcon = computed(() => {
    if (showAdvanced.value) {
        return "search";
    } else if (
        currentPanelView.value !== "default" &&
        panels.value &&
        typeof panels.value[currentPanelView.value]?.view_type === "string"
    ) {
        const viewType = panels.value[currentPanelView.value]?.view_type;
        return viewType ? types_to_icons[viewType] : null;
    } else {
        return null;
    }
});

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
    } else if (loading.value && panelName.value) {
        return localize(panelName.value);
    } else if (currentPanelView.value !== "default" && panels.value && panels.value[currentPanelView.value]?.name) {
        return localize(panels.value[currentPanelView.value]?.name);
    } else {
        return localize("Tools");
    }
});

async function initializePanel() {
    try {
        await userStore.loadUser(false);
        await toolStore.fetchPanels();
        await toolStore.fetchTools();
        await toolStore.initializePanel();
    } catch (error) {
        console.error(`ToolPanel::initializePanel - ${error}`);
        errorMessage.value = errorMessageAsString(error);
    } finally {
        panelsFetched.value = true;
    }
}

async function updatePanelView(panelView: string) {
    panelName.value = panels.value[panelView]?.name || "";
    await toolStore.setPanel(panelView);
    panelName.value = "";
}

function onInsertModule(moduleName: string, moduleTitle: string | undefined) {
    emit("onInsertModule", moduleName, moduleTitle);
}

function onInsertTool(toolId: string, toolName: string) {
    emit("onInsertTool", toolId, toolName);
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
        if ((!newVal || !toolSections.value[newVal]) && panelsFetched.value) {
            await initializePanel();
        }
    }
);

initializePanel();
</script>

<template>
    <div v-if="panelsFetched" id="toolbox-panel" class="unified-panel" aria-labelledby="toolbox-heading">
        <div unselectable="on">
            <div class="unified-panel-header-inner mx-3 my-2 d-flex justify-content-between">
                <PanelViewMenu
                    v-if="panels && Object.keys(panels).length > 1"
                    :panel-views="panels"
                    :current-panel-view="currentPanelView"
                    :show-advanced.sync="showAdvanced"
                    :store-loading="loading"
                    @updatePanelView="updatePanelView">
                    <template v-slot:panel-view-selector>
                        <div class="d-flex justify-content-between panel-view-selector">
                            <div>
                                <span
                                    v-if="panelIcon && !loading"
                                    :class="['fas', `fa-${panelIcon}`, 'mr-1']"
                                    data-description="panel view header icon" />
                                <Heading
                                    id="toolbox-heading"
                                    :class="!showAdvanced && toolPanelHeader !== 'Tools' && 'font-italic'"
                                    h2
                                    inline
                                    size="sm">
                                    <span v-if="loading && panelName">
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
            :show-advanced.sync="showAdvanced"
            :data-managers="dataManagers"
            :module-sections="moduleSections"
            :use-search-worker="useSearchWorker"
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
    <b-alert v-else-if="currentToolSections" class="m-2" variant="info" show>
        <LoadingSpan message="Loading Toolbox" />
    </b-alert>
</template>

<style lang="scss" scoped>
@import "theme/blue.scss";

.panel-view-selector {
    color: $panel-header-text-color;
}
</style>
