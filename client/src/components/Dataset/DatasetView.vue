<script setup lang="ts">
import { BTab, BTabs } from "bootstrap-vue";
import { computed, ref } from "vue";

import { STATES } from "@/components/History/Content/model/states";
import { useDatasetStore } from "@/stores/datasetStore";

import Heading from "../Common/Heading.vue";
import DatasetAttributes from "@/components/DatasetInformation/DatasetAttributes.vue";
import DatasetDetails from "@/components/DatasetInformation/DatasetDetails.vue";
import VisualizationsList from "@/components/Visualizations/Index.vue";

const datasetStore = useDatasetStore();

const props = defineProps({
    datasetId: {
        type: String,
        required: true,
    },
    // Move toplevel routes to this component with subrouting
});

const dataset = computed(() => datasetStore.getDataset(props.datasetId));
const isLoading = computed(() => datasetStore.isLoadingDataset(props.datasetId));

const stateText = computed(() => dataset.value && STATES[dataset.value.state] && STATES[dataset.value.state].text);
const activeTab = ref("activeTab");
const displayUrl = computed(() => `/datasets/${props.datasetId}/display/?preview=true`);
</script>
<template>
    <div v-if="dataset && !isLoading">
        <header class="dataset-header">
            <Heading h2>{{ dataset.name }}</Heading>
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
                <BLink class="value" data-label="Database/Build" @click.stop="activeTab = 'edit'">{{
                    dataset.genome_build
                }}</BLink>
            </span>
            <div v-if="dataset.misc_info" class="info">
                <span class="value">{{ dataset.misc_info }}</span>
            </div>
        </header>
        <div class="dataset-tabs h-100">
            <BTabs pills card>
                <BTab title="Preview" active class="h-100">
                    <iframe
                        :src="displayUrl"
                        title="galaxy dataset display frame"
                        class="center-frame h-100"
                        width="100%"
                        height="100%"
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
            </BTabs>
        </div>
    </div>
</template>

<style scoped>
.dataset-header {
    margin-bottom: 1.5rem;
}
</style>
