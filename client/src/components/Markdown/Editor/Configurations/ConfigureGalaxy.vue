<template>
    <b-alert v-if="errorMessage" variant="danger" show>{{ errorMessage }}</b-alert>
    <ConfigureSelector
        v-else-if="requirement"
        :object-id="contentObject?.args[requirement]"
        :object-type="requirement"
        @change="onChange($event)" />
    <b-alert v-else v-localize variant="info" show>No input requirements.</b-alert>
</template>

<script setup lang="ts">
import { computed, type Ref, ref, watch } from "vue";

import type { OptionType } from "@/components/Markdown/Editor/Configurations/types";
import { getArgs } from "@/components/Markdown/parse";

import REQUIREMENTS from "./requirements";

import ConfigureSelector from "./ConfigureSelector.vue";

const props = defineProps<{
    content: string;
}>();

const emit = defineEmits<{
    (e: "change", content: string): void;
}>();

interface contentType {
    args: Record<string, any>;
    name: string;
}

const contentObject: Ref<contentType | undefined> = ref();
const errorMessage = ref("");

const requirement = computed(() => {
    const name = contentObject.value?.name || "";
    if (name) {
        for (const [key, values] of Object.entries(REQUIREMENTS)) {
            if (values.includes(name)) {
                return key;
            }
        }
    }
    return null;
});

function onChange(newValue: OptionType) {
    if (requirement.value) {
        const newValues = { ...contentObject.value?.args };
        newValues[requirement.value] = newValue.id;
        const newContent = Object.entries(newValues)
            .map(([key, value]) => `${key}=${value}`)
            .join(" ");
        emit("change", `${contentObject.value?.name}(${newContent})`);
    }
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
