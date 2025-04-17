<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { onMounted, ref } from "vue";

import { fetchPlugin } from "@/api/plugins";

import VisualizationHeader from "./VisualizationHeader.vue";
import SelectionField from "@/components/SelectionField/SelectionField.vue";

const props = defineProps<{
    visualization: string;
}>();

const errorMessage = ref("");
const isLoading = ref(false);
const plugin = ref();

async function getPlugin() {
    plugin.value = await fetchPlugin(props.visualization);
    isLoading.value = false;
}

onMounted(() => {
    getPlugin();
});
</script>

<template>
    <div v-if="errorMessage">
        <BAlert v-if="errorMessage" variant="danger" show>{{ errorMessage }}</BAlert>
    </div>
    <div v-else>
        <LoadingSpan v-if="isLoading" message="Loading visualization" />
        <VisualizationHeader :plugin="plugin" />
        <SelectionField object-title="Dataset" object-type="history_dataset_id" />
    </div>
</template>
