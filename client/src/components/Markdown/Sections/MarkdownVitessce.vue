<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { ref, watch } from "vue";

import type { DatasetLabel, Invocation } from "@/components/Markdown/Editor/types";
import { parseInput, parseOutput } from "@/components/Markdown/Utilities/parseInvocation";
import { getAppRoot } from "@/onload";
import { useInvocationStore } from "@/stores/invocationStore";

import LoadingSpan from "@/components/LoadingSpan.vue";
import VisualizationWrapper from "@/components/Visualizations/VisualizationWrapper.vue";

const DEFAULT_HEIGHT = 400;

const props = defineProps<{
    content: string;
}>();

const errorMessage = ref("");
const loading = ref(false);
const missingInvocation = ref(false);
const visualizationConfig = ref();
const visualizationHeight = ref(DEFAULT_HEIGHT);
const visualizationKey = ref(0);
const visualizationName = ref("");
const visualizationTitle = ref("");

const { fetchInvocationById } = useInvocationStore();

const currentContent = ref(props.content);

async function processContent() {
    try {
        errorMessage.value = "";
        const parsedContent = { ...JSON.parse(props.content) };

        // Evaluate __gx_dataset entries before rendering vitessce
        missingInvocation.value = false;
        if (Array.isArray(parsedContent.datasets)) {
            for (const dataset of parsedContent.datasets) {
                if (Array.isArray(dataset.files)) {
                    for (const file of dataset.files) {
                        if ("__gx_dataset_id" in file) {
                            file.url = `${getAppRoot()}api/datasets/${file.__gx_dataset_id}/display`;
                            delete file.__gx_dataset_id;
                        }
                        if ("__gx_dataset_label" in file) {
                            const datasetLabel = file.__gx_dataset_label;
                            const invocationId = datasetLabel.invocation_id;
                            if (invocationId) {
                                const invocation = await fetchInvocationById(invocationId);
                                const datasetId = getDatasetId(invocation as Invocation, datasetLabel);
                                if (datasetId) {
                                    const datasetId = getDatasetId(invocation as Invocation, datasetLabel);
                                    file.url = `${getAppRoot()}api/datasets/${datasetId}/display`;
                                    delete file.__gx_dataset_label;
                                } else {
                                    throw new Error(`Failed to retrieve dataset id for '${invocationId}'.`);
                                }
                            } else {
                                missingInvocation.value = true;
                                break;
                            }
                        }
                        if ("__gx_dataset_name" in file) {
                            delete file.__gx_dataset_name;
                        }
                    }
                }
            }
        }

        // Determine height
        if ("__gx_height" in parsedContent) {
            visualizationHeight.value = parsedContent.__gx_height;
            delete parsedContent.__gx_height;
        } else {
            visualizationHeight.value = DEFAULT_HEIGHT;
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

defineExpose({ visualizationConfig });
</script>

<template>
    <BAlert v-if="missingInvocation" v-localize class="m-0" variant="info" show>
        Data for rendering this <b>Vitessce Dashboard</b> is not yet available.
    </BAlert>
    <div v-else class="markdown-visualization">
        <BAlert v-if="errorMessage" v-localize class="m-0" variant="danger" show>
            {{ errorMessage }}
        </BAlert>
        <LoadingSpan v-else-if="loading" />
        <VisualizationWrapper
            v-else-if="visualizationConfig"
            :key="visualizationKey"
            class="markdown-vitessce"
            :config="visualizationConfig"
            :height="visualizationHeight"
            :name="visualizationName"
            :title="visualizationTitle" />
    </div>
</template>
