<template>
    <div class="p-2">
        <ConfigureHeader @cancel="$emit('cancel')" />
        <BAlert v-if="errorMessage" variant="warning" show>{{ errorMessage }}</BAlert>
        <BAlert v-else-if="!requirement || requirementFulfilled" v-localize variant="info" show>
            No inputs required for <b>`{{ contentName }}`</b>.
        </BAlert>
        <ConfigureSelector v-else :labels="labels" :object-type="requirement" @change="onChange" />
    </div>
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
const contentName: Ref<string | undefined> = ref();
const errorMessage = ref("");

const hasLabels = computed(() => props.labels !== undefined);

const requirement = computed(() => {
    if (contentName.value) {
        for (const [key, values] of Object.entries(REQUIREMENTS)) {
            if (Array.isArray(values) && values.includes(contentName.value)) {
                return key;
            }
        }
    }
    return null;
});

const requirementFulfilled = computed(
    () =>
        hasLabels.value &&
        requirement.value &&
        ["history_id", "invocation_id", "workflow_id"].includes(requirement.value)
);

function onChange(option: OptionType) {
    if (contentName.value) {
        if (hasLabels.value && option.label) {
            const values = Object.entries(option.label)
                .filter(([_, value]) => !!value)
                .map(([key, value]) => `${key}="${value}"`)
                .join(", ");
            emit("change", `${contentName.value}(${values})`);
        } else if (option.id) {
            emit("change", `${contentName.value}(${requirement.value}=${option.id})`);
        }
    }
}

function parseContent() {
    try {
        contentObject.value = getArgs(props.content);
        contentName.value = contentObject.value.name;
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
