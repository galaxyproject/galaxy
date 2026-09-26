<template>
    <div>
        <DisplayApplications v-if="datasetId" :dataset-id="datasetId" />
        <VisualizationPanel :dataset-id="datasetId" />
    </div>
</template>

<script setup lang="ts">
import DisplayApplications from "./DisplayApplications.vue";
import VisualizationPanel from "@/components/Visualizations/VisualizationPanel.vue";

defineProps<{
    datasetId: string;
}>();
</script>
