<script setup lang="ts">
import { useWorkflowInstance } from "@/composables/useWorkflowInstance";

import ParameterStep from "./ParameterStep.vue";
import WorkflowInvocationStep from "./WorkflowInvocationStep.vue";
import GenericHistoryItem from "components/History/Content/GenericItem.vue";

const props = defineProps({
    invocation: {
        type: Object,
        required: true,
    },
});

interface HasSrc {
    src: string;
}

const { workflow } = useWorkflowInstance(props.invocation.workflow_id);

function dataInputStepLabel(key: number, input: HasSrc) {
    const invocationStep = props.invocation.steps[key];
    let label = invocationStep && invocationStep.workflow_step_label;
    if (!label) {
        if (input.src === "hda" || input.src === "ldda") {
            label = "Input dataset";
        } else if (input.src === "hdca") {
            label = "Input dataset collection";
        }
    }
    return label;
}
</script>
<template>
    <div v-if="invocation">
        <b-tabs lazy>
            <b-tab v-if="Object.keys(invocation.input_step_parameters).length" title="Parameters">
                <ParameterStep :parameters="Object.values(invocation.input_step_parameters)" />
            </b-tab>
            <b-tab v-if="Object.keys(invocation.inputs).length" title="Inputs">
                <div
                    v-for="(input, key) in invocation.inputs"
                    :key="input.id"
                    :data-label="dataInputStepLabel(key, input)">
                    <b>{{ dataInputStepLabel(key, input) }}</b>
                    <GenericHistoryItem :item-id="input.id" :item-src="input.src" />
                </div>
            </b-tab>
            <b-tab v-if="Object.keys(invocation.outputs).length" title="Outputs">
                <div v-for="(output, key) in invocation.outputs" :key="output.id">
                    <b>{{ key }}:</b>
                    <GenericHistoryItem :item-id="output.id" :item-src="output.src" />
                </div>
            </b-tab>
            <b-tab v-if="Object.keys(invocation.output_collections).length" title="Output Collections">
                <div v-for="(output, key) in invocation.output_collections" :key="output.id">
                    <b>{{ key }}:</b>
                    <GenericHistoryItem :item-id="output.id" :item-src="output.src" />
                </div>
            </b-tab>
            <b-tab v-if="workflow" title="Steps">
                <WorkflowInvocationStep
                    v-for="step in Object.values(workflow.steps)"
                    :key="step.id"
                    :invocation="invocation"
                    :workflow="workflow"
                    :workflow-step="step" />
            </b-tab>
        </b-tabs>
    </div>
</template>
