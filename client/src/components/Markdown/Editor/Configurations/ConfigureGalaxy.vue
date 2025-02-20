<template>
    <b-alert v-if="errorMessage" variant="danger" show>{{ errorMessage }}</b-alert>
    <ConfigureSelector v-else type="datasets" @change="onChange($event)" />
</template>

<script setup lang="ts">
import { type Ref, ref, watch } from "vue";

import type { OptionType } from "@/components/Markdown/Editor/Configurations/types";
import { getArgs } from "@/components/Markdown/parse";

import ConfigureSelector from "./ConfigureSelector.vue";

const props = defineProps<{
    content: string;
}>();

const emit = defineEmits<{
    (e: "change", content: string): void;
}>();

interface ObjectType {
    args: Record<string, any>;
    name: string;
}

const contentObject: Ref<ObjectType | undefined> = ref();
const errorMessage = ref("");

function onChange(newValue: OptionType) {
    const newValues = { ...contentObject.value?.args, history_dataset_id: newValue.id };
    const newContent = Object.entries(newValues)
        .map(([key, value]) => `${key}=${value}`)
        .join(" ");
    emit("change", `${contentObject.value?.name}(${newContent})`);
}

function parseContent() {
    try {
        contentObject.value = getArgs(props.content);
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
