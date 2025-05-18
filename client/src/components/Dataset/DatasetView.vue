<script setup lang="ts">
import { BNav, BNavItem } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

import { useDatasetStore } from "@/stores/datasetStore";
import { useDatatypeVisualizationsStore } from "@/stores/datatypeVisualizationsStore";

import DatasetError from "../DatasetInformation/DatasetError.vue";
import DatasetState from "./DatasetState.vue";
import LoadingSpan from "../LoadingSpan.vue";
import Heading from "@/components/Common/Heading.vue";
import DatasetAttributes from "@/components/DatasetInformation/DatasetAttributes.vue";
import DatasetDetails from "@/components/DatasetInformation/DatasetDetails.vue";
import VisualizationsList from "@/components/Visualizations/Index.vue";
import VisualizationFrame from "@/components/Visualizations/VisualizationFrame.vue";
import CenterFrame from "@/entry/analysis/modules/CenterFrame.vue";

const datasetStore = useDatasetStore();
const datatypeVisualizationsStore = useDatatypeVisualizationsStore();

interface Props {
    datasetId: string;
    tab?: "details" | "edit" | "error" | "preview" | "visualize";
}

const props = withDefaults(defineProps<Props>(), {
    tab: "preview",
});

const dataset = computed(() => datasetStore.getDataset(props.datasetId));
const isLoading = computed(() => datasetStore.isLoadingDataset(props.datasetId));
const preferredVisualization = ref<string>();

const showError = computed(
    () => dataset.value && (dataset.value.state === "error" || dataset.value.state === "failed_metadata")
);

// Check if the dataset has a preferred visualization by datatype
async function checkPreferredVisualization() {
    if (dataset.value && dataset.value.file_ext) {
        try {
            const mapping = await datatypeVisualizationsStore.getPreferredVisualizationForDatatype(
                dataset.value.file_ext
            );
            if (mapping) {
                preferredVisualization.value = mapping.visualization;
            } else {
                preferredVisualization.value = undefined;
            }
        } catch (error) {
            preferredVisualization.value = undefined;
        }
    } else {
        preferredVisualization.value = undefined;
    }
}

// Watch for changes to the dataset to check for preferred visualizations
watch(() => dataset.value?.file_ext, checkPreferredVisualization, { immediate: true });
</script>

<template>
    <LoadingSpan v-if="isLoading"></LoadingSpan>
    <div v-else class="d-flex flex-column h-100">
        <div class="d-flex">
            <Heading h1 separator inline size="lg" class="flex-grow-1 mb-2">
                {{ dataset?.hid }}: <span class="font-weight-bold">{{ dataset?.name }}</span>
            </Heading>
            <DatasetState :dataset-id="datasetId" />
        </div>
        <BNav pills justified class="mb-2">
            <BNavItem :active="tab === 'preview'" :to="`/datasets/${datasetId}/preview`"> Preview</BNavItem>
            <BNavItem v-if="!showError" :active="tab === 'visualize'" :to="`/datasets/${datasetId}/visualize`"> Visualize </BNavItem>
            <BNavItem :active="tab === 'details'" :to="`/datasets/${datasetId}/details`"> Details </BNavItem>
            <BNavItem :active="tab === 'edit'" :to="`/datasets/${datasetId}/edit`"> Edit </BNavItem>
            <BNavItem v-if="showError" :active="tab === 'error'" :to="`/datasets/${datasetId}/error`"> Error </BNavItem>
        </BNav>
        <div v-if="tab === 'preview'" class="h-100">
            <VisualizationFrame
                v-if="preferredVisualization"
                :dataset-id="datasetId"
                :visualization="preferredVisualization" />
            <CenterFrame v-else :src="`/datasets/${datasetId}/display/?preview=True`" :is_preview="true" />
        </div>
        <div v-else-if="tab === 'visualize'" class="d-flex flex-column overflow-auto">
            <VisualizationsList :dataset-id="datasetId" />
        </div>
        <div v-else-if="tab === 'edit'" class="d-flex flex-column overflow-auto">
            <DatasetAttributes :dataset-id="datasetId" />
        </div>
        <div v-else-if="tab === 'details'" class="d-flex flex-column overflow-auto">
            <DatasetDetails :dataset-id="datasetId" />
        </div>
        <div v-else-if="tab === 'error'" class="d-flex flex-column overflow-auto">
            <DatasetError :dataset-id="datasetId" />
        </div>
    </div>
</template>
