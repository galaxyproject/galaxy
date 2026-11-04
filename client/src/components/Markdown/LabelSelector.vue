<script setup lang="ts">
import { computed } from "vue";

import { useUid } from "@/composables/utils/uid";

import type { WorkflowLabel } from "./Editor/types";

import GAlert from "@/components/BaseComponents/GAlert.vue";
import GRadio from "@/components/BaseComponents/GRadio.vue";
import GRadioGroup from "@/components/BaseComponents/GRadioGroup.vue";

interface LabelSelectorProps {
    hasLabels: boolean;
    labels: Array<WorkflowLabel>;
    value?: WorkflowLabel;
    labelTitle: string;
}

const props = withDefaults(defineProps<LabelSelectorProps>(), {
    value: undefined,
});

const emit = defineEmits<{
    (e: "input", value: WorkflowLabel | undefined): void;
}>();

const headingId = useUid("label-selector-heading-");

const selectedIndex = computed(() => (props.value ? props.labels.indexOf(props.value) : undefined));

function update(index: number) {
    const label: WorkflowLabel | undefined = props.labels[index] || undefined;
    emit("input", label);
}
</script>

<template>
    <div>
        <h2 :id="headingId" class="mb-3 h-text">Select {{ labelTitle }} Label:</h2>
        <GRadioGroup
            v-if="hasLabels"
            stacked
            class="label-selector-options"
            :aria-labelledby="headingId"
            :model-value="selectedIndex"
            @update:model-value="update">
            <GRadio v-for="(label, index) in labels" :key="index" :value="index">
                {{ label.label }}
            </GRadio>
        </GRadioGroup>
        <GAlert v-else show variant="info"> No labels found. Please specify labels in the Workflow Editor. </GAlert>
        <p class="mt-3 text-muted">
            You may add new labels by selecting a step in the workflow editor and then editing the corresponding label
            field in the step form.
        </p>
    </div>
</template>

<style scoped lang="scss">
.label-selector-options :deep(.g-radio-group-options) {
    row-gap: var(--spacing-2, 0.5rem);
}
</style>
