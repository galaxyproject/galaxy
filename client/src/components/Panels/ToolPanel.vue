<script setup lang="ts">
import { faCaretDown } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BBadge } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";

import { useToolStore } from "@/stores/toolStore";
import { useUserStore } from "@/stores/userStore";
import localize from "@/utils/localization";
import { errorMessageAsString } from "@/utils/simple-error";

import { types_to_icons } from "./utilities";

import LoadingSpan from "../LoadingSpan.vue";
import ActivityPanel from "./ActivityPanel.vue";
import FavoritesButton from "./Buttons/FavoritesButton.vue";
import PanelViewMenu from "./Menus/PanelViewMenu.vue";
import ToolBox from "./ToolBox.vue";
import Heading from "@/components/Common/Heading.vue";

const toolStore = useToolStore();

const userStore = useUserStore();
const props = defineProps({
    useSearchWorker: { type: Boolean, default: true },
    workflow: { type: Boolean, default: false },
});

const emit = defineEmits<{
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
        if (process.env.NODE_ENV != "test") {
            console.error(`ToolPanel::initializePanel - ${error}`);
        }

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
    },
);

// if currentPanelView ever becomes null || "", load tools
watch(
    () => currentPanelView.value,
    async (newVal) => {
        query.value = "";
        if ((!newVal || !toolSections.value[newVal]) && panelsFetched.value) {
            await initializePanel();
        }
    },
);

initializePanel();
</script>

<template>
    <ActivityPanel
        v-if="panelsFetched"
        id="toolbox-panel"
        title="Tools"
        aria-labelledby="toolbox-heading"
        class="toolbox-panel"
        go-to-all-title="Discover Tools"
        href="/tools/list">
        <template v-slot:activity-panel-header-top>
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
        </template>
        <template v-if="!showAdvanced" v-slot:header-buttons>
            <FavoritesButton v-model="showFavorites" />
        </template>
        <ToolBox
            v-if="isPanelPopulated"
            :workflow="props.workflow"
            :panel-query.sync="query"
            :show-advanced.sync="showAdvanced"
            :use-search-worker="useSearchWorker"
            @onInsertTool="onInsertTool"
            @onInsertWorkflow="onInsertWorkflow"
            @onInsertWorkflowSteps="onInsertWorkflowSteps" />
        <div v-else-if="errorMessage" data-description="tool panel error message">
            <BAlert class="m-2" variant="danger" show>
                {{ errorMessage }}
            </BAlert>
        </div>
        <div v-else>
            <BBadge class="alert-info w-100">
                <LoadingSpan message="Loading Toolbox" />
            </BBadge>
        </div>
    </ActivityPanel>
    <BAlert v-else-if="currentToolSections" class="m-2" variant="info" show>
        <LoadingSpan message="Loading Toolbox" />
    </BAlert>
</template>

<style lang="scss" scoped>
@import "theme/blue.scss";

.panel-view-selector {
    color: $panel-header-text-color;
}

.toolbox-panel {
    padding: 0.5rem 0rem !important;

    :deep(.activity-panel-header) {
        margin-right: 1rem;
        margin-left: 1rem;
    }
}
</style>
