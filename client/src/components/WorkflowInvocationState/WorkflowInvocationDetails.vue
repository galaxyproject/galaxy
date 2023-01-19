<script setup>
import { useWorkflowInstance } from "@/composables/useWorkflowInstance";
import ParameterStep from "./ParameterStep";
import GenericHistoryItem from "components/History/Content/GenericItem";
import WorkflowInvocationStep from "./WorkflowInvocationStep";

const props = defineProps({
    invocation: {
        type: Object,
        required: true,
    },
});

const { workflow } = useWorkflowInstance(props.invocation.workflow_id);

function dataInputStepLabel(key, input) {
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
                <parameter-step :parameters="Object.values(invocation.input_step_parameters)" />
            </b-tab>
            <b-tab v-if="Object.keys(invocation.inputs).length" title="Inputs">
                <div
                    v-for="(input, key) in invocation.inputs"
                    :key="input.id"
                    :data-label="dataInputStepLabel(key, input)">
                    <b>{{ dataInputStepLabel(key, input) }}</b>
                    <generic-history-item :item-id="input.id" :item-src="input.src" />
                </div>
            </b-tab>
            <b-tab v-if="Object.keys(invocation.outputs).length" title="Outputs">
                <div v-for="(output, key) in invocation.outputs" :key="output.id">
                    <b>{{ key }}:</b>
                    <generic-history-item :item-id="output.id" :item-src="output.src" />
                </div>
            </b-tab>
            <b-tab v-if="Object.keys(invocation.output_collections).length" title="Output Collections">
                <div v-for="(output, key) in invocation.output_collections" :key="output.id">
                    <b>{{ key }}:</b>
                    <generic-history-item :item-id="output.id" :item-src="output.src" />
                </div>
            </b-tab>
            <b-tab v-if="workflow" title="Steps">
                <workflow-invocation-step
                    v-for="step in Object.values(workflow.steps)"
                    :key="step.id"
                    :invocation="invocation"
                    :workflow="workflow"
                    :workflow-step="step" />
            </b-tab>
        </b-tabs>
    </div>
</template>
