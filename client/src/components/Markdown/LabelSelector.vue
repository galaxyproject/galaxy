<script setup lang="ts">
import { type WorkflowLabel } from "./labels";

interface LabelSelectorProps {
    hasLabels: boolean;
    labels: WorkflowLabel[];
    value?: WorkflowLabel;
    labelTitle: string;
}

const props = withDefaults(defineProps<LabelSelectorProps>(), {
    value: undefined,
});

const emit = defineEmits<{
    (e: "input", value: WorkflowLabel | undefined): void;
}>();

function update(index: number) {
    const label: WorkflowLabel | undefined = props.labels[index] || undefined;
    emit("input", label);
}
</script>

<template>
    <div>
        <h2 class="mb-3 h-text">Select {{ labelTitle }} Label:</h2>
        <div v-if="hasLabels">
            <b-form-radio
                v-for="(label, index) in labels"
                :key="index"
                class="my-2"
                name="labels"
                :value="index"
                @change="update">
                {{ label.label }}
            </b-form-radio>
        </div>
        <b-alert v-else show variant="info"> No labels found. Please specify labels in the Workflow Editor. </b-alert>
        <p class="mt-3 text-muted">
            You may add new labels by selecting a step in the workflow editor and then editing the corresponding label
            field in the step form.
        </p>
    </div>
</template>
