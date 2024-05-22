<script setup lang="ts">
import { computed } from "vue";

import { hasDetails } from "@/api";
import { type PathDestination, useDatasetPathDestination } from "@/composables/datasetPathDestination";
import { useDatasetStore } from "@/stores/datasetStore";

interface Props {
    historyDatasetId: string;
    path?: string;
    label?: string;
}

const { datasetPathDestination } = useDatasetPathDestination();
const { getDataset } = useDatasetStore();

const props = defineProps<Props>();

const pathDestination = computed<PathDestination | null>(() =>
    datasetPathDestination.value(props.historyDatasetId, props.path)
);

const dataset = computed(() => getDataset(props.historyDatasetId));

const fileLink = computed(() => {
    if (props.path === undefined || props.path === "undefined") {
        // Download whole dataset
        if (dataset.value && hasDetails(dataset.value)) {
            return `${dataset.value.download_url}?to_ext=${dataset.value.file_ext}`;
        }
    }

    // Download individual file from composite dataset
    return pathDestination.value?.fileLink;
});

const linkLabel = computed(() => {
    if (pathDestination.value?.isDirectory) {
        return `Path: ${props.path} is a directory!`;
    }

    if (!fileLink.value) {
        return `Path: ${props.path} was not found!`;
    }

    if (props.label && props.label !== "undefined") {
        return props.label;
    }
    return `${props.historyDatasetId}`;
});

const linkTitle = computed(() => `Download ${dataset.value?.name ?? props.historyDatasetId}`);
</script>

<template>
    <div>
        <a :href="fileLink" :title="linkTitle" target="_blank">{{ linkLabel }}</a>
    </div>
</template>
