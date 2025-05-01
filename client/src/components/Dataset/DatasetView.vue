<script setup lang="ts">
import { BLink, BTab, BTabs } from "bootstrap-vue";
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router/composables";

import { STATES } from "@/components/History/Content/model/states";
import { useDatasetStore } from "@/stores/datasetStore";

import Heading from "../Common/Heading.vue";
import DatasetError from "../DatasetInformation/DatasetError.vue";
import DatasetAttributes from "@/components/DatasetInformation/DatasetAttributes.vue";
import DatasetDetails from "@/components/DatasetInformation/DatasetDetails.vue";
import VisualizationsList from "@/components/Visualizations/Index.vue";

const datasetStore = useDatasetStore();
const route = useRoute();
const router = useRouter();

const props = defineProps({
    datasetId: {
        type: String,
        required: true,
    },
});

// Map tab names to their index positions
const tabNameToIndex = {
    "preview": 0,
    "details": 1,
    "visualize": 2,
    "edit": 3,
    "error": 4
};

// Track the currently active tab
const activeTab = ref(0);

const dataset = computed(() => datasetStore.getDataset(props.datasetId));
const isLoading = computed(() => datasetStore.isLoadingDataset(props.datasetId));

const stateText = computed(() => dataset.value && STATES[dataset.value.state] && STATES[dataset.value.state].text);
const displayUrl = computed(() => `/datasets/${props.datasetId}/display/?preview=true`);

const showError = computed(
    () => dataset.value && (dataset.value.state === "error" || dataset.value.state === "failed_metadata")
);

// Handle tab changes
function onTabChange(tabIndex: number) {
    const tabNames = ["preview", "details", "visualize", "edit", "error"];
    const tabName = tabNames[tabIndex];
    
    // Only navigate to error tab if it's available
    if (tabName === "error" && !showError.value) {
        return;
    }
    
    // Update the URL without reloading the page
    if (tabName === "preview") {
        router.push(`/datasets/${props.datasetId}`);
    } else {
        router.push(`/datasets/${props.datasetId}/${tabName}`);
    }
}

// Set the active tab based on the current route
function setActiveTabFromRoute() {
    const path = route.path;
    
    if (path.includes("/details")) {
        activeTab.value = tabNameToIndex.details;
    } else if (path.includes("/visualize")) {
        activeTab.value = tabNameToIndex.visualize;
    } else if (path.includes("/edit")) {
        activeTab.value = tabNameToIndex.edit;
    } else if (path.includes("/error") && showError.value) {
        activeTab.value = tabNameToIndex.error;
    } else {
        activeTab.value = tabNameToIndex.preview;
    }
}

// Watch for route changes
watch(() => route.path, setActiveTabFromRoute);

// Set initial active tab on mount
onMounted(() => {
    setActiveTabFromRoute();
});
</script>
<template>
    <div v-if="dataset && !isLoading" class="dataset-view d-flex flex-column">
        <header class="dataset-header flex-shrink-0">
            <Heading h1 separator>{{ dataset.name }}</Heading>
            <div v-if="stateText" class="mb-1">{{ stateText }}</div>
            <div v-else-if="dataset.misc_blurb" class="blurb">
                <span class="value">{{ dataset.misc_blurb }}</span>
            </div>
            <span v-if="dataset.file_ext" class="datatype">
                <span v-localize class="prompt">format</span>
                <span class="value font-weight-bold">{{ dataset.file_ext }}</span>
            </span>
            <span v-if="dataset.genome_build" class="dbkey">
                <span v-localize class="prompt">database</span>
                <!-- Consider making this link actually switch to the Edit tab -->
                <BLink class="value font-weight-bold" data-label="Database/Build" @click="onTabChange(3)">{{ dataset.genome_build }}</BLink>
            </span>
            <div v-if="dataset.misc_info" class="info">
                <span class="value">{{ dataset.misc_info }}</span>
            </div>
        </header>

        <!-- Tab container - make it grow to fill remaining space and handle overflow -->
        <div class="dataset-tabs-container flex-grow-1 overflow-hidden">
            <!-- Make BTabs fill its container and use flex column layout internally -->
            <BTabs 
                pills 
                card 
                lazy 
                class="h-100 d-flex flex-column" 
                :value="activeTab" 
                @input="onTabChange">
                <BTab title="Preview" class="iframe-card">
                    <!-- Iframe for dataset preview -->
                    <iframe
                        :src="displayUrl"
                        title="galaxy dataset display frame"
                        class="dataset-preview-iframe"
                        frameborder="0"></iframe>
                </BTab>
                <BTab title="Details">
                    <DatasetDetails :dataset-id="datasetId" />
                </BTab>
                <BTab title="Visualize">
                    <VisualizationsList :dataset-id="datasetId" />
                </BTab>
                <BTab title="Edit">
                    <DatasetAttributes :dataset-id="datasetId" />
                </BTab>
                <BTab v-if="showError" title="Error Report">
                    <DatasetError :dataset-id="datasetId" />
                </BTab>
            </BTabs>
        </div>
    </div>
    <!-- Loading state indicator -->
    <div v-else class="loading-message">Loading dataset details...</div>
</template>

<style scoped>
.dataset-view {
    height: 100%;
}

.dataset-header {
    margin-bottom: 1rem;
}

.dataset-tabs-container {
    min-height: 0; /* fix for flex-grow behavior in some contexts */
}

.dataset-tabs-container :deep(.nav-tabs) {
    flex-shrink: 0;
}

.dataset-tabs-container :deep(.tab-content) {
    flex-grow: 1;
    min-height: 0;
}

.dataset-tabs-container :deep(.tab-pane) {
    height: 100%;
    width: 100%;
    display: flex;
    flex-direction: column;
}

.dataset-tabs-container :deep(.iframe-card) {
    flex-grow: 1;
    display: flex;
    flex-direction: column;
    /* Remove padding for the iframe tab, we add back for others */
    padding: 0;
    overflow: hidden;
}

.dataset-preview-iframe {
    flex-grow: 1;
    border: none;
    width: 100%;
    height: 100%;
}

.loading-message {
    padding: 2rem;
    text-align: center;
    font-style: italic;
}
</style>
