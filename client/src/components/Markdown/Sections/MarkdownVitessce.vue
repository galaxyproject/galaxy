<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { ref, watch } from "vue";

import type { DatasetLabel, Invocation } from "@/components/Markdown/Editor/types";
import { parseInput, parseOutput } from "@/components/Markdown/Utilities/parseInvocation";
import { getAppRoot } from "@/onload";
import { useInvocationStore } from "@/stores/invocationStore";

import LoadingSpan from "@/components/LoadingSpan.vue";
import VisualizationWrapper from "@/components/Visualizations/VisualizationWrapper.vue";

const props = defineProps<{
    content: string;
}>();

const errorMessage = ref("");
const loading = ref(false);
const visualizationConfig = ref();
const visualizationKey = ref(0);
const visualizationName = ref("");
const visualizationTitle = ref("");

const { fetchInvocationById } = useInvocationStore();

const currentContent = ref(props.content);

async function processContent() {
    try {
        errorMessage.value = "";
        const parsedContent = { ...JSON.parse(props.content) };

        // Remove gxy_dataset_label entries before parsing to vitessce
        if (Array.isArray(parsedContent.datasets)) {
            for (const dataset of parsedContent.datasets) {
                if (Array.isArray(dataset.files)) {
                    for (const file of dataset.files) {
                        if ("gxy_dataset_label" in file) {
                            const gxyDatasetLabel = file.gxy_dataset_label;
                            const invocationId = gxyDatasetLabel.invocation_id;
                            const invocation = await fetchInvocationById(invocationId);
                            const datasetId = getDatasetId(invocation as Invocation, gxyDatasetLabel);
                            if (datasetId) {
                                const datasetId = getDatasetId(invocation as Invocation, gxyDatasetLabel);
                                file.url = `${getAppRoot()}api/datasets/${datasetId}/display`;
                                delete file.gxy_dataset_label;
                            } else {
                                throw new Error(`Failed to retrieve dataset id from ${invocationId}.`);
                            }
                        }
                    }
                }
            }
        }

        // Build visualization config for vitessce
        visualizationConfig.value = {};
        visualizationConfig.value["dataset_content"] = parsedContent;
        visualizationName.value = "vitessce";

        // Trigger update counter
        if (currentContent.value !== props.content) {
            currentContent.value = props.content;
            visualizationKey.value++;
        }
    } catch (e) {
        errorMessage.value = String(e);
    }
}

function getDatasetId(invocation: Invocation, datasetLabel: DatasetLabel) {
    const inputId = parseInput(invocation, datasetLabel?.input);
    const outputId = parseOutput(invocation, datasetLabel?.output);
    return inputId || outputId;
}

watch(
    () => props.content,
    () => processContent(),
    { immediate: true }
);
</script>

<template>
    <div class="markdown-visualization">
        <BAlert v-if="errorMessage" v-localize class="m-0" variant="danger" show>
            {{ errorMessage }}
        </BAlert>
        <LoadingSpan v-else-if="loading" />
        <VisualizationWrapper
            v-else-if="visualizationConfig"
            :key="visualizationKey"
            class="markdown-vitessce"
            :config="visualizationConfig"
            :name="visualizationName"
            :title="visualizationTitle" />
    </div>
</template>

<style>
.markdown-vitessce {
    min-height: 400px;
    max-height: 400px;
}
</style>
