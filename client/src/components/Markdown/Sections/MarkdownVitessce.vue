<script setup lang="ts">
import { computed } from "vue";
import VisualizationWrapper from "@/components/Visualizations/VisualizationWrapper.vue";

const props = defineProps<{
    content: string;
}>();

const dataIncoming = computed(() => ({
    visualization_config: {
        dataset_content: { ...JSON.parse(props.content) },
    },
}));
</script>

<template>
    <div>
        <visualization-wrapper name="vitessce" :data-incoming="dataIncoming" height="500px" />
    </div>
</template>
