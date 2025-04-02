<template>
    <BAlert v-if="errorMessage" variant="warning" show>{{ errorMessage }}</BAlert>
    <div v-else-if="requirement" class="p-2">
        <ConfigureHeader @cancel="$emit('cancel')" />
        <ConfigureSelector :labels="labels" :object-type="requirement" @change="onChange" />
    </div>
    <BAlert v-else v-localize variant="info" show>
        No inputs available for <b>`{{ contentObject?.name }}`</b>.
    </BAlert>
</template>

<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { computed, type Ref, ref, watch } from "vue";

import type { OptionType, WorkflowLabel } from "@/components/Markdown/Editor/types";
import { getArgs } from "@/components/Markdown/parse";

import REQUIREMENTS from "./requirements.yml";

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
    args: Record<string, any>;
    name: string;
}

const contentObject: Ref<contentType | undefined> = ref();
const errorMessage = ref("");

const hasLabels = computed(() => props.labels !== undefined);

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

function onChange(option: OptionType) {
    if (hasLabels.value && option.label) {
        const values = Object.entries(option.label)
            .filter(([_, value]) => !!value)
            .map(([key, value]) => `${key}="${value}"`)
            .join(", ");
        emit("change", `${contentObject.value.name}(${values})`);
    } else if (option.id) {
        emit("change", `${contentObject.value.name}(${requirement.value}=${option.id})`);
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
