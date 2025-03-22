<template>
    <b-alert v-if="errorMessage" variant="warning" show>{{ errorMessage }}</b-alert>
    <MarkdownSelector v-else-if="labels !== undefined" argument-name="Dataset" :labels="labels" @onOk="onLabel" />
    <DataDialog
        v-else-if="currentHistoryId !== null"
        :history="currentHistoryId"
        format="id"
        @onOk="onData"
        @onCancel="$emit('cancel')" />
    <b-alert v-else v-localize variant="info" show> No history available to choose from. </b-alert>
</template>

<script setup lang="ts">
import { storeToRefs } from "pinia";
import { type Ref, ref, watch } from "vue";

import type { DatasetLabel, WorkflowLabel } from "@/components/Markdown/Editor/types";
import { stringify } from "@/components/Markdown/Utilities/stringify";
import { useHistoryStore } from "@/stores/historyStore";

import DataDialog from "@/components/DataDialog/DataDialog.vue";
import MarkdownSelector from "@/components/Markdown/MarkdownSelector.vue";

const { currentHistoryId } = storeToRefs(useHistoryStore());

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
const errorMessage = ref("");

function onData(datasetId: any) {
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
