<script setup lang="ts">
import { ref, watch } from "vue";

import VisualizationWrapper from "@/components/Visualizations/VisualizationWrapper.vue";

const props = defineProps<{
    attribute?: string;
    content: string;
    name?: string;
}>();

const emit = defineEmits(["change"]);

const errorMessage = ref("");
const visualizationConfig = ref();
const visualizationKey = ref(0);
const visualizationName = ref();
const visualizationTitle = ref("");

const currentContent = ref(props.content);

function onChange(incomingData: Record<string, any>) {
    const newContent = {
        visualization_name: visualizationName.value,
        visualization_title: incomingData.visualization_title,
        ...incomingData.visualization_config,
    };
    currentContent.value = JSON.stringify(newContent, null, 4);
    emit("change", currentContent.value);
}

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
                visualizationConfig.value = {
                    dataset_id: parsedContent.dataset_id,
                    settings: parsedContent.settings,
                    tracks: parsedContent.tracks,
                };
                visualizationTitle.value = parsedContent.visualization_title || "";
            }
            visualizationName.value = props.name || parsedContent.visualization_name;
            if (!visualizationName.value) {
                throw new Error("Please add a 'visualization_name` to the dictionary.");
            }
            if (currentContent.value !== props.content) {
                currentContent.value = props.content;
                visualizationKey.value++;
            }
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
        :name="visualizationName"
        :title="visualizationTitle"
        @change="onChange" />
</template>

<style>
.markdown-visualization {
    min-height: 400px;
}
</style>
