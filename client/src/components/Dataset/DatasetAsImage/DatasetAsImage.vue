<script setup lang="ts">
import { computedAsync } from "@vueuse/core";
import { BAlert, BImg } from "bootstrap-vue";
import { computed } from "vue";

import { type PathDestination, useDatasetPathDestination } from "@/composables/datasetPathDestination";
import { getAppRoot } from "@/onload/loadConfig";

interface Props {
    historyDatasetId: string;
    path?: string;
}

const { datasetPathDestination } = useDatasetPathDestination();

const props = defineProps<Props>();

const pathDestination = computed<PathDestination | null>(() =>
    datasetPathDestination.value(props.historyDatasetId, props.path)
);

const imageUrl = computed(() => {
    if (props.path === undefined || props.path === "undefined") {
        return `${getAppRoot()}dataset/display?dataset_id=${props.historyDatasetId}`;
    }
    return pathDestination.value?.fileLink;
});

const isImage = computedAsync(async () => {
    if (!imageUrl.value) {
        return null;
    }
    const res = await fetch(imageUrl.value);
    const buff = await res.blob();
    return buff.type.startsWith("image/");
}, true);
</script>

<template>
    <div v-if="imageUrl" class="w-100">
        <BAlert v-if="!isImage" variant="warning" show>
            This dataset does not appear to be an image: {{ imageUrl }}.
        </BAlert>
        <BImg v-else :src="imageUrl" fluid />
    </div>
    <BAlert v-else variant="warning" show>Image not found: {{ imageUrl }}.</BAlert>
</template>
