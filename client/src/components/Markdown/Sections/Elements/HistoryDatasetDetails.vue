<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { computed } from "vue";

import { useDatasetStore } from "@/stores/datasetStore";

type AttributeType = "name" | "info" | "peek" | "file_ext";

const ATTRIBUTES: Record<string, AttributeType> = {
    history_dataset_name: "name",
    history_dataset_info: "info",
    history_dataset_peek: "peek",
    history_dataset_type: "file_ext",
};

interface Dataset {
    name?: string;
    info?: string;
    peek?: string;
    file_ext?: string;
}

const { getDatasetError, getDataset } = useDatasetStore();

const props = defineProps<{
    datasetId: string;
    name: string;
}>();

const attributeValue = computed(() => {
    if (dataset.value) {
        const attributeName = ATTRIBUTES[props.name] || "";
        if (attributeName) {
            return dataset.value[attributeName] || `Dataset attribute '${attributeName}' unavailable.`;
        }
    }
    return "";
});

const dataset = computed(() => getDataset(props.datasetId) as Dataset);
const error = computed(() => getDatasetError(props.datasetId));
const getClass = computed(() => `dataset-${ATTRIBUTES[props.name || ""]}`);
</script>

<template>
    <BAlert v-if="error" show variant="warning">{{ error }}</BAlert>
    <pre v-else><code :class="getClass">{{ attributeValue }}</code></pre>
</template>
