<script setup lang="ts">
import { ref, watch } from "vue";

import VisualizationWrapper from "@/components/Visualizations/VisualizationWrapper.vue";

const props = defineProps<{
    content: string;
    name: string;
}>();

const visualizationConfig = ref();
const errorMessage = ref("");

watch(
    () => props.content,
    () => {
        try {
            visualizationConfig.value = { ...JSON.parse(props.content) };
            errorMessage.value = "";
        } catch (e) {
            errorMessage.value = String(e);
        }
    },
    { immediate: true }
);
</script>

<template>
    <b-alert v-if="errorMessage" variant="danger" show>
        {{ errorMessage }}
    </b-alert>
    <VisualizationWrapper v-else-if="visualizationConfig" :name="name" :config="visualizationConfig" height="500px" />
</template>
