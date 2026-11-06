<script setup lang="ts">
import { onMounted, ref } from "vue";

import { GalaxyApi } from "@/api";

import GAlert from "@/components/BaseComponents/GAlert.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import VisualizationFrame from "@/components/Visualizations/VisualizationFrame.vue";

const props = defineProps<{
    visualizationId: string;
}>();

const errorMessage = ref("");
const visualization = ref<{ type: string; title: string; config: object }>();

onMounted(async () => {
    const { data, error } = await GalaxyApi().GET("/api/visualizations/{id}", {
        params: { path: { id: props.visualizationId } },
    });
    if (error) {
        errorMessage.value = error.err_msg;
    } else if (data.latest_revision?.config) {
        visualization.value = { type: data.type, title: data.title, config: data.latest_revision.config };
    } else {
        errorMessage.value = "This visualization has no saved configuration.";
    }
});
</script>

<template>
    <GAlert v-if="errorMessage" variant="danger" show>{{ errorMessage }}</GAlert>
    <VisualizationFrame
        v-else-if="visualization"
        :name="visualization.type"
        :title="visualization.title"
        :config="visualization.config" />
    <LoadingSpan v-else message="Loading visualization" />
</template>
