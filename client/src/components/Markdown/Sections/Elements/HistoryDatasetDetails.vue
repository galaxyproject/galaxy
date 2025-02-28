<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

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

const getClass = computed(() => `dataset-${ATTRIBUTES[props.name || ""]}`);

const attributeValue = ref<string>();

const dataset = computed(() => getDataset(props.datasetId) as Dataset);
const error = computed(() => getDatasetError(props.datasetId));

async function fetchAttribute() {
    if (dataset.value) {
        const attributeName = ATTRIBUTES[props.name] || "";
        if (attributeName) {
            attributeValue.value = dataset.value[attributeName] || `Dataset attribute '${attributeName}' unavailable.`;
        }
    }
}

watch(
    () => dataset.value,
    () => fetchAttribute(),
    { immediate: true }
);
</script>

<template>
    <BAlert v-if="error" show variant="warning">{{ error }}</BAlert>
    <pre v-else><code :class="getClass">{{ attributeValue }}</code></pre>
</template>
