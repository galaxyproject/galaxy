<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { computed, type Ref, ref, watch } from "vue";

import type { DatasetLabel, Invocation } from "@/components/Markdown/Editor/types";
import { parseInput, parseOutput } from "@/components/Markdown/Utilities/parseInvocation";
import { stringify } from "@/components/Markdown/Utilities/stringify";
import { useInvocationStore } from "@/stores/invocationStore";

import LoadingSpan from "@/components/LoadingSpan.vue";
import VisualizationWrapper from "@/components/Visualizations/VisualizationWrapper.vue";

const props = defineProps<{
    content: string;
    name?: string;
}>();

const emit = defineEmits(["change"]);

const datasetLabel: Ref<DatasetLabel | undefined> = ref();
const errorMessage = ref("");
const visualizationConfig = ref();
const visualizationKey = ref(0);
const visualizationName = ref();
const visualizationTitle = ref("");

const { getInvocationById, getInvocationLoadError, isLoadingInvocation } = useInvocationStore();

const currentContent = ref(props.content);

const invocation = computed(() => invocationId.value && getInvocationById(invocationId.value));
const invocationId = computed(() => datasetLabel.value?.invocation_id || "");
const invocationLoading = computed(() => isLoadingInvocation(invocationId.value));
const invocationLoadError = computed(() => getInvocationLoadError(invocationId.value));

function onChange(incomingData: Record<string, any>) {
    const newContent = {
        visualization_name: visualizationName.value,
        visualization_title: incomingData.visualization_title,
        dataset_label: datasetLabel.value,
        ...incomingData.visualization_config,
    };
    currentContent.value = stringify(newContent);
    emit("change", currentContent.value);
}

function processContent() {
    try {
        errorMessage.value = "";
        const parsedContent = { ...JSON.parse(props.content) };
        datasetLabel.value = parsedContent.dataset_label;
        visualizationConfig.value = {
            dataset_id: parsedContent.dataset_id,
            dataset_url: parsedContent.dataset_url,
            settings: parsedContent.settings,
            tracks: parsedContent.tracks,
        };
        visualizationTitle.value = parsedContent.visualization_title || "";
        visualizationName.value = props.name || parsedContent.visualization_name;
        if (!visualizationName.value) {
            throw new Error("Please add a 'visualization_name` to the dictionary.");
        }
        processInvocation();
        if (currentContent.value !== props.content) {
            currentContent.value = props.content;
            visualizationKey.value++;
        }
    } catch (e) {
        errorMessage.value = String(e);
    }
}

function processInvocation() {
    if (invocation.value) {
        const inputId = parseInput(invocation.value as Invocation, datasetLabel.value?.input);
        const outputId = parseOutput(invocation.value as Invocation, datasetLabel.value?.output);
        const datasetId = inputId || outputId;
        visualizationConfig.value.dataset_id = datasetId;
    }
}

watch(
    () => props.content,
    () => processContent(),
    { immediate: true }
);

watch(
    () => invocation.value,
    () => processInvocation()
);
</script>

<template>
    <div class="markdown-visualization">
        <BAlert v-if="errorMessage" v-localize class="m-0" variant="danger" show>
            {{ errorMessage }}
        </BAlert>
        <BAlert v-else-if="invocationLoadError" v-localize class="m-0" variant="danger" show>
            {{ invocationLoadError }}
        </BAlert>
        <LoadingSpan v-else-if="invocationLoading" />
        <VisualizationWrapper
            v-else-if="visualizationConfig"
            :key="visualizationKey"
            class="markdown-visualization"
            :config="visualizationConfig"
            :name="visualizationName"
            :title="visualizationTitle"
            @change="onChange" />
    </div>
</template>
