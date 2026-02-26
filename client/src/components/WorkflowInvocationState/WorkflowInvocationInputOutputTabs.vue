<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

import type { WorkflowInvocationElementView } from "@/api/invocations";
import { useWorkflowInstance } from "@/composables/useWorkflowInstance";
import type { Step } from "@/stores/workflowStepStore";
import { useWorkflowStore } from "@/stores/workflowStore";

import Heading from "../Common/Heading.vue";
import LoadingSpan from "../LoadingSpan.vue";
import WorkflowInvocationInputs from "./WorkflowInvocationInputs.vue";
import GenericHistoryItem from "@/components/History/Content/GenericItem.vue";

const OUTPUTS_NOT_AVAILABLE_YET_MSG =
    "Either no outputs have been produced yet, or no steps were checked to " +
    "mark their outputs as primary workflow outputs.";

const props = defineProps<{
    invocation: WorkflowInvocationElementView;
    tab?: "steps" | "inputs" | "outputs" | "report" | "export" | "metrics" | "debug";
    terminal?: boolean;
}>();

// Fetching full workflow to get the workflow output labels (for when invocation is not terminal)
const workflowOutputLabels = ref<string[]>([]);
const workflow = computed(() => {
    if (!props.terminal) {
        const { workflow } = useWorkflowInstance(props.invocation.workflow_id);
        return workflow.value;
    }
    return undefined;
});
const workflowStore = useWorkflowStore();
watch(
    workflow,
    async (newWorkflow) => {
        if (newWorkflow) {
            try {
                const wf = await workflowStore.getFullWorkflowCached(newWorkflow.id, newWorkflow.version);
                if (wf) {
                    const fullWorkflowSteps = (wf.steps ? Object.values(wf.steps) : []) as Step[];
                    workflowOutputLabels.value = fullWorkflowSteps
                        .flatMap((step) => step.workflow_outputs || [])
                        .map((output) => output.label)
                        .filter((label) => label !== null && label !== undefined);
                }
            } catch (error) {
                console.error("Error fetching full workflow:", error);
            }
        }
    },
    { immediate: true },
);

const inputData = computed(() => Object.entries(props.invocation.inputs));

const outputs = computed(() => {
    const outputEntries = Object.entries(props.invocation.outputs);
    const outputCollectionEntries = Object.entries(props.invocation.output_collections);
    return [...outputEntries, ...outputCollectionEntries];
});

const parameters = computed(() => Object.values(props.invocation.input_step_parameters));
</script>
<template>
    <div v-if="props.tab === 'inputs'">
        <div v-if="parameters.length || inputData.length">
            <WorkflowInvocationInputs :invocation="props.invocation" />
        </div>
        <BAlert v-else show variant="info"> No input data was provided for this workflow invocation. </BAlert>
    </div>
    <div v-else-if="props.tab === 'outputs'">
        <div v-if="outputs.length">
            <div v-for="([key, output], index) in outputs" :key="index" data-description="terminal invocation output">
                <Heading size="text" bold separator>{{ key }}</Heading>
                <GenericHistoryItem
                    :item-id="output.id ?? ''"
                    :item-src="output.src"
                    data-description="terminal invocation output item" />
            </div>
        </div>
        <div v-else-if="workflowOutputLabels.length">
            <div
                v-for="(label, index) in workflowOutputLabels"
                :key="index"
                data-description="non-terminal invocation output">
                <Heading size="text" bold separator>{{ label }}</Heading>
                <BAlert
                    v-if="!props.terminal"
                    class="m-1 py-2"
                    show
                    variant="info"
                    data-description="non-terminal invocation output loading">
                    <LoadingSpan message="Output not created yet" />
                </BAlert>
                <BAlert v-else class="m-1 py-2" show variant="danger">
                    <LoadingSpan message="Output not available" />
                </BAlert>
            </div>
        </div>
        <BAlert v-else show variant="info">
            <p>
                <LoadingSpan v-if="!props.terminal" :message="OUTPUTS_NOT_AVAILABLE_YET_MSG" />
                <span v-else v-localize>
                    No steps were checked to mark their outputs as primary workflow outputs.
                </span>
            </p>
            <p>
                To get outputs from a workflow in this tab, you need to check the
                <i>
                    "Checked outputs will become primary workflow outputs and are available as subworkflow outputs."
                </i>
                option on individual outputs on individual steps in the workflow.
            </p>
        </BAlert>
    </div>
</template>
