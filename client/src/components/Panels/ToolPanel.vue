<script setup lang="ts">
import { BAlert, BBadge } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";

import { useToolStore } from "@/stores/toolStore";
import { useUserStore } from "@/stores/userStore";
import { errorMessageAsString } from "@/utils/simple-error";

import LoadingSpan from "../LoadingSpan.vue";
import ActivityPanel from "./ActivityPanel.vue";
import FavoritesButton from "./Buttons/FavoritesButton.vue";
import PanelViewMenu from "./Menus/PanelViewMenu.vue";
import ToolBox from "./ToolBox.vue";

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

const { currentPanelView, currentToolSections, isPanelPopulated, toolSections } = storeToRefs(toolStore);

const errorMessage = ref("");
const panelsFetched = ref(false);
const query = ref("");

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
            <PanelViewMenu />
        </template>
        <template v-slot:header-buttons>
            <FavoritesButton v-model="showFavorites" />
        </template>
        <ToolBox
            v-if="isPanelPopulated"
            :workflow="props.workflow"
            :panel-query.sync="query"
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
.toolbox-panel {
    padding: 0.5rem 0rem !important;

    :deep(.activity-panel-header) {
        margin-right: 1rem;
        margin-left: 1rem;
    }
}
</style>
