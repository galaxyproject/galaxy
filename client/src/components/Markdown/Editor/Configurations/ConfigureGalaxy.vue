<template>
    <b-alert v-if="errorMessage" variant="warning" show>{{ errorMessage }}</b-alert>
    <MarkdownDialog
        v-else-if="requirement"
        :argument-type="requirement"
        :argument-name="contentObject?.name"
        :argument-payload="contentObject?.args"
        :labels="labels"
        @onInsert="$emit('change', $event)"
        @onCancel="$emit('cancel')" />
    <b-alert v-else v-localize variant="info" show>
        No inputs available for <b>`{{ contentObject?.name }}`</b>.
    </b-alert>
</template>

<script setup lang="ts">
import { computed, type Ref, ref, watch } from "vue";

import type { WorkflowLabel } from "@/components/Markdown/Editor/types";
import { getArgs } from "@/components/Markdown/parse";

import REQUIREMENTS from "./requirements.yml";

import MarkdownDialog from "@/components/Markdown/MarkdownDialog.vue";

const props = defineProps<{
    content: string;
    labels?: Array<WorkflowLabel>;
}>();

defineEmits<{
    (e: "cancel"): void;
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
            if (Array.isArray(values) && values.includes(name)) {
                return key;
            }
        }
    }
    return null;
});

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
