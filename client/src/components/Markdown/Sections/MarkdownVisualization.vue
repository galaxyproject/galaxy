<script setup lang="ts">
import { ref, watch } from "vue";

import VisualizationWrapper from "@/components/Visualizations/VisualizationWrapper.vue";

const props = defineProps<{
    attribute?: string;
    content: string;
    name: string;
}>();

const HEIGHT = "400px";

const errorMessage = ref("");
const visualizationConfig = ref();
const visualizationKey = ref(0);

watch(
    () => props.content,
    () => {
        try {
            errorMessage.value = "";
            const parsedContent = { ...JSON.parse(props.content) };
            if (props.attribute) {
                visualizationConfig.value = {};
                visualizationConfig.value[props.attribute] = parsedContent;
            } else {
                visualizationConfig.value = parsedContent;
            }
            visualizationKey.value++;
        } catch (e) {
            errorMessage.value = String(e);
        }
    },
    { immediate: true }
);
</script>

<template>
    <b-alert v-if="errorMessage" variant="danger" show :height="HEIGHT">
        {{ errorMessage }}
    </b-alert>
    <VisualizationWrapper
        v-else-if="visualizationConfig"
        :key="visualizationKey"
        :config="visualizationConfig"
        :height="HEIGHT"
        :name="name" />
</template>
