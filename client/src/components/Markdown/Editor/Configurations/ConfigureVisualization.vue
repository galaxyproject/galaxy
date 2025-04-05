<template>
    <BAlert v-if="errorMessage" variant="warning" show>{{ errorMessage }}</BAlert>
    <div v-else class="p-2">
        <ConfigureHeader @cancel="$emit('cancel')" />
        <ConfigureSelector :labels="labels" object-type="history_dataset_id" @change="onChange" />
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
    [key: string]: unknown;
}

const contentObject: Ref<contentType | undefined> = ref();
const errorMessage = ref("");

const hasLabels = computed(() => props.labels !== undefined);

function onChange(option: OptionType) {
    if (contentObject.value) {
        if (hasLabels.value) {
            contentObject.value.dataset_label = option.label;
            contentObject.value.dataset_id = undefined;
            contentObject.value.dataset_url = undefined;
        } else {
            contentObject.value.dataset_id = option.id;
            contentObject.value.dataset_label = undefined;
            contentObject.value.dataset_url = undefined;
        }
        emit("change", stringify(contentObject.value));
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
