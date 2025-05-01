<script setup lang="ts">
import { BLink, BTab, BTabs } from "bootstrap-vue";
import { computed } from "vue";

import { STATES } from "@/components/History/Content/model/states";
import { useDatasetStore } from "@/stores/datasetStore";

import Heading from "../Common/Heading.vue";
import DatasetError from "../DatasetInformation/DatasetError.vue";
import DatasetAttributes from "@/components/DatasetInformation/DatasetAttributes.vue";
import DatasetDetails from "@/components/DatasetInformation/DatasetDetails.vue";
import VisualizationsList from "@/components/Visualizations/Index.vue";

const datasetStore = useDatasetStore();

const props = defineProps({
    datasetId: {
        type: String,
        required: true,
    },
});

const dataset = computed(() => datasetStore.getDataset(props.datasetId));
const isLoading = computed(() => datasetStore.isLoadingDataset(props.datasetId));

const stateText = computed(() => dataset.value && STATES[dataset.value.state] && STATES[dataset.value.state].text);
const displayUrl = computed(() => `/datasets/${props.datasetId}/display/?preview=true`);

const showError = computed(
    () => dataset.value && (dataset.value.state === "error" || dataset.value.state === "failed_metadata")
);

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
                <span class="value">{{ dataset.file_ext }}</span>
            </span>
            <span v-if="dataset.genome_build" class="dbkey">
                <span v-localize class="prompt">database</span>
                <!-- Consider making this link actually switch to the Edit tab -->
                <BLink class="value" data-label="Database/Build">{{ dataset.genome_build }}</BLink>
            </span>
            <div v-if="dataset.misc_info" class="info">
                <span class="value">{{ dataset.misc_info }}</span>
            </div>
        </header>

        <!-- Tab container - make it grow to fill remaining space and handle overflow -->
        <div class="dataset-tabs-container flex-grow-1 overflow-hidden">
            <!-- Make BTabs fill its container and use flex column layout internally -->
            <BTabs pills card lazy class="h-100 d-flex flex-column">
                <BTab title="Preview" active class="iframe-card">
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
