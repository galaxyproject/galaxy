<template>
    <b-alert v-if="errorMessage" variant="danger" show>{{ errorMessage }}</b-alert>
    <ConfigureSelector
        v-else
        :id="contentObject.dataset_id"
        :name="contentObject.dataset_name"
        type="datasets"
        @change="onChange($event)" />
</template>

<script setup lang="ts">
import { ref, watch } from "vue";

import type { OptionType } from "@/components/Markdown/Editor/Configurations/types";

import ConfigureSelector from "./ConfigureSelector.vue";

const props = defineProps<{
    content: string;
}>();

const emit = defineEmits<{
    (e: "change", content: string): void;
}>();

const contentObject = ref();
const errorMessage = ref("");

function onChange(newValue: OptionType) {
    const newValues = { ...contentObject.value, dataset_id: newValue.id, dataset_name: newValue.name };
    emit("change", JSON.stringify(newValues, null, 4));
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
