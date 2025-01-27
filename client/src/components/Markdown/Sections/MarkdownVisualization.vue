<script setup lang="ts">
import { ref, watch } from "vue";

import VisualizationWrapper from "@/components/Visualizations/VisualizationWrapper.vue";

const props = defineProps<{
    content: string;
    name: string;
}>();

const HEIGHT = "500px";

const errorMessage = ref("");
const visualizationConfig = ref();
const visualizationKey = ref(0);

watch(
    () => props.content,
    () => {
        try {
            errorMessage.value = "";
            visualizationConfig.value = { ...JSON.parse(props.content) };
            visualizationKey.value++;
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
    <VisualizationWrapper
        v-else-if="visualizationConfig"
        :config="visualizationConfig"
        :height="HEIGHT"
        :key="visualizationKey"
        :name="name" />
</template>
