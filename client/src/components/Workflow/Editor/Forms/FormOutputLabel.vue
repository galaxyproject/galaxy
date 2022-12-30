<template>
    <FormElement
        :id="id"
        :value="label"
        :error="error"
        :title="title"
        type="text"
        help="Provide a short, unique name to describe this output."
        @input="onInput" />
</template>

<script lang="ts" setup>
import FormElement from "@/components/Form/FormElement.vue";
import { useWorkflowStepStore } from "@/stores/workflowStepStore";
import { computed, ref } from "vue";
import type { Ref } from "vue";
import type { Step } from "@/stores/workflowStepStore";

const props = withDefaults(
    defineProps<{
        name: string;
        step: Step;
        showDetails?: boolean;
    }>(),
    {
        showDetails: false,
    }
);

const stepStore = useWorkflowStepStore();

const error: Ref<string | undefined> = ref(undefined);
const id = computed(() => `__label__${props.name}`);
const title = computed(() => (props.showDetails ? `Label for: '${props.name}'` : "Label"));
const label = computed(() => {
    if (props.step.workflow_outputs?.length) {
        const workflowOutput = props.step.workflow_outputs.find(
            (workflowOutput) => workflowOutput.output_name === props.name
        );
        if (workflowOutput) {
            return workflowOutput.label;
        }
    }
    return null;
});

function onInput(newLabel: string) {
    if (!stepStore.workflowOutputs[newLabel]) {
        const newWorkflowOutputs = [...(props.step.workflow_outputs || [])].filter(
            (workflowOutput) => workflowOutput.output_name !== props.name
        );
        newWorkflowOutputs.push({
            label: newLabel,
            output_name: props.name,
        });
        stepStore.updateStep({ ...props.step, workflow_outputs: newWorkflowOutputs });
        error.value = undefined;
    } else {
        error.value = `Duplicate output label '${newLabel}' will be ignored.`;
    }
}
</script>
