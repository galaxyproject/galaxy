<template>
    <div class="p-2">
        <ConfigureHeader @cancel="$emit('cancel')" />
        <BAlert v-if="errorMessage" variant="warning" show>{{ errorMessage }}</BAlert>
        <BAlert v-else-if="!requiredObject || requirementFulfilled" v-localize variant="info" show>
            No inputs required for <b>`{{ contentName }}`</b>.
        </BAlert>
        <ConfigureSelector v-else :labels="labels" :object-type="requiredObject" @change="onChange" />
    </div>
</template>

<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { computed, type Ref, ref, watch } from "vue";

import type { WorkflowLabel } from "@/components/Markdown/Editor/types";
import { getArgs } from "@/components/Markdown/parse";
import { getRequiredObject } from "@/components/Markdown/Utilities/requirements";
import type { OptionType } from "@/components/SelectionField/types";

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

const requiredObject = computed(() => getRequiredObject(contentName.value));

const requirementFulfilled = computed(
    () =>
        hasLabels.value &&
        requiredObject.value &&
        ["history_id", "invocation_id", "workflow_id"].includes(requiredObject.value)
);

function onChange(option: OptionType) {
    if (contentName.value) {
        if (hasLabels.value && option.data && option.data.label) {
            const values = Object.entries(option.data.label)
                .filter(([_, value]) => !!value)
                .map(([key, value]) => `${key}="${value}"`)
                .join(", ");
            emit("change", `${contentName.value}(${values})`);
        } else if (option.id) {
            emit("change", `${contentName.value}(${requiredObject.value}=${option.id})`);
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
