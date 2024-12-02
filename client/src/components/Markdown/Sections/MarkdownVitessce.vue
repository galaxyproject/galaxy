<script setup lang="ts">
import { computed } from "vue";
import VisualizationWrapper from "@/components/Visualizations/VisualizationWrapper.vue";

const props = defineProps<{
    content: string;
}>();

const pluginData = computed(() => ({
    visualization_config: {
        dataset_content: { ...JSON.parse(props.content) },
    },
}));
</script>

<template>
    <div>
        <visualization-wrapper name="vitessce" :data-incoming="pluginData" height="500px" />
    </div>
</template>
