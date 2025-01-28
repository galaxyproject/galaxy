<script setup lang="ts">
import { ref, watch } from "vue";

import VisualizationWrapper from "@/components/Visualizations/VisualizationWrapper.vue";

const props = defineProps<{
    attribute?: string;
    content: string;
    name?: string;
}>();

const errorMessage = ref("");
const visualizationConfig = ref();
const visualizationKey = ref(0);
const visualizationName = ref();

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
            visualizationName.value = props.name || visualizationConfig.value.visualization_name;
            if (!visualizationName.value) {
                throw new Error("Please add a 'visualization_name` to the dictionary.");
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
    <div v-if="errorMessage" class="markdown-visualization">
        <b-alert variant="danger" show>
            {{ errorMessage }}
        </b-alert>
    </div>
    <VisualizationWrapper
        v-else-if="visualizationConfig"
        :key="visualizationKey"
        class="markdown-visualization"
        :config="visualizationConfig"
        :name="visualizationName" />
</template>

<style>
.markdown-visualization {
    min-height: 400px;
}
</style>
