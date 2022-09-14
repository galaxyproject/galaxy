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
                    :ordered-steps="orderedSteps"
                    :workflow="workflow"
                    :workflow-step="step" />
            </b-tab>
        </b-tabs>
    </div>
</template>
<script>
import ParameterStep from "./ParameterStep";
import GenericHistoryItem from "components/History/Content/GenericItem";
import WorkflowInvocationStep from "./WorkflowInvocationStep";

import { mapGetters } from "vuex";
import { mapCacheActions } from "vuex-cache";

export default {
    components: {
        GenericHistoryItem,
        WorkflowInvocationStep,
        ParameterStep,
    },
    props: {
        invocation: {
            type: Object,
            required: true,
        },
    },
    computed: {
        ...mapGetters(["getWorkflowByInstanceId"]),
        orderedSteps() {
            return [...this.invocation.steps].sort((a, b) => a.order_index - b.order_index);
        },
        workflow() {
            return this.getWorkflowByInstanceId(this.invocation.workflow_id);
        },
    },
    created: function () {
        this.fetchWorkflowForInstanceId(this.invocation.workflow_id);
    },
    methods: {
        ...mapCacheActions(["fetchWorkflowForInstanceId"]),
        dataInputStepLabel(key, input) {
            const invocationStep = this.orderedSteps[key];
            let label = invocationStep && invocationStep.workflow_step_label;
            if (!label) {
                if (input.src === "hda" || input.src === "ldda") {
                    label = "Input dataset";
                } else if (input.src === "hdca") {
                    label = "Input dataset collection";
                }
            }
            return label;
        },
    },
};
</script>
