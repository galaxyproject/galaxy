<template>
    <BAlert v-if="errorMessage" variant="warning" show>{{ errorMessage }}</BAlert>
    <div v-else class="p-2">
        <ConfigureHeader @cancel="$emit('cancel')" />
        <ConfigureSelector
            :labels="labels"
            object-type="history_dataset_id"
            @change="onChange" />
    </div>
</template>

<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { computed, type Ref, ref, watch } from "vue";

import type { DatasetLabel, OptionType, WorkflowLabel } from "@/components/Markdown/Editor/types";
import { stringify } from "@/components/Markdown/Utilities/stringify";

import ConfigureHeader from "./ConfigureHeader.vue";
import ConfigureSelector from "./ConfigureSelector.vue";

const props = defineProps<{
    content: string;
    labels?: Array<WorkflowLabel>;
}>();

const emit = defineEmits<{
    (e: "cancel"): void;
    (e: "change", content: string): void;
}>();

interface contentType {
    dataset_id?: string;
    dataset_label?: DatasetLabel;
    dataset_url?: string;
}

const contentObject: Ref<contentType | undefined> = ref();
const hasLabels = computed(() => props.labels !== undefined);
const errorMessage = ref("");

function onChange(newValue: OptionType) {
    if (hasLabels.value) {
        onLabel(newValue.value);
    } else {
        onDataset(newValue.id);
    }
}

function onDataset(datasetId: string) {
    if (contentObject.value) {
        contentObject.value.dataset_id = datasetId;
        contentObject.value.dataset_label = undefined;
        contentObject.value.dataset_url = undefined;
        emit("change", stringify(contentObject.value));
    }
}

function onLabel(selectedLabel: any) {
    if (selectedLabel !== undefined) {
        const labelType = selectedLabel.type;
        const label = selectedLabel.label;
        if (contentObject.value && label && labelType) {
            contentObject.value.dataset_label = {
                invocation_id: "",
                [labelType]: label,
            };
            contentObject.value.dataset_id = undefined;
            contentObject.value.dataset_url = undefined;
            emit("change", stringify(contentObject.value));
        }
    }
}

function parseContent() {
    try {
        contentObject.value = JSON.parse(props.content);
        errorMessage.value = "";
    } catch (e) {
        errorMessage.value = `Failed to parse: ${e}`;
    }
}

watch(
    () => props.content,
    () => parseContent(),
    { immediate: true }
);
</script>
