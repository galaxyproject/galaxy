<script setup lang="ts">
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
</script>

<template>
    <div>
        <div v-if="imageUrl" class="w-100 p-2">
            <b-card nobody body-class="p-1">
                <b-img :src="imageUrl" fluid />
            </b-card>
        </div>
        <div v-else>
            <b>Image is not found</b>
        </div>
    </div>
</template>
