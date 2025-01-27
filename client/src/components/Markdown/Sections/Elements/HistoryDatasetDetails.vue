<script setup lang="ts">
import axios from "axios";
import { computed, ref, watch } from "vue";

import { getAppRoot } from "@/onload/loadConfig";

const ATTRIBUTES: Record<string, string> = {
    history_dataset_name: "name",
    history_dataset_info: "info",
    history_dataset_peek: "peek",
    history_dataset_type: "file_ext",
};

const props = defineProps<{
    datasetId: string;
    name: string;
}>();

const getClass = computed(() => `dataset-${ATTRIBUTES[props.name || ""]}`);

const attributeValue = ref();

async function fetchAttribute(datasetId: string) {
    if (datasetId) {
        try {
            const attributeName = ATTRIBUTES[props.name] || "";
            if (attributeName) {
                const { data } = await axios.get(`${getAppRoot()}api/datasets/${datasetId}`);
                attributeValue.value = data[attributeName] || `Dataset attribute '${attributeName}' unavailable.`;
            }
        } catch (error) {
            console.error("Error fetching dataset attribute:", error);
            attributeValue.value = "";
        }
    }
}

watch(
    () => props.datasetId,
    () => fetchAttribute(props.datasetId),
    { immediate: true }
);
</script>

<template>
    <pre><code :class="getClass">{{ attributeValue }}</code></pre>
</template>
