<template>
    <div v-if="invocation">
        <div v-if="Object.keys(invocation.input_step_parameters).length > 0">
            <details
                ><summary><b>Invocation Parameters</b></summary>
                <parameter-step :parameters="Object.values(invocation.input_step_parameters)"/>
            </details>
        </div>
        <div v-if="Object.keys(invocation.inputs).length > 0">
            <details
                ><summary><b>Invocation Inputs</b></summary>
                <div v-for="(input, key) in invocation.inputs" v-bind:key="input.id">
                    <b>{{dataInputStepLabel(key, input)}}</b>
                    <workflow-invocation-data-contents v-bind:data_item="input" />
                </div>
            </details>
        </div>
        <div v-if="Object.keys(invocation.outputs).length > 0">
            <details
                ><summary><b>Invocation Outputs</b></summary>
                <div v-for="(output, key) in invocation.outputs" v-bind:key="output.id">
                    <b>{{key}}:</b>
                    <workflow-invocation-data-contents v-bind:data_item="output" />
                </div>
            </details>
        </div>
        <div v-if="Object.keys(invocation.output_collections).length > 0">
            <details
                ><summary><b>Invocation Output Collections</b></summary>
                <div v-for="(output, key) in invocation.output_collections" v-bind:key="output.id">
                    <b>{{key}}:</b>
                    <workflow-invocation-data-contents v-bind:data_item="output" />
                </div>
            </details>
        </div>
        <div v-if="workflow">
            <details v-if="workflow"><summary><b>Invocation Steps</b></summary>
                <workflow-invocation-step v-for="step in Object.values(workflow.steps)" :invocation="invocation" :orderedSteps="orderedSteps" :key="step.id" :workflow="workflow" :workflowStep="step"/>
            </details>
        </div>
    </div>
</template>
<script>
import ParameterStep from './ParameterStep.vue';
import WorkflowInvocationDataContents from "./WorkflowInvocationDataContents";
import WorkflowInvocationStep from "./WorkflowInvocationStep";
import ListMixin from "components/History/ListMixin";

import { getAppRoot } from "onload/loadConfig";

import { getRootFromIndexLink } from "onload";
import { mapCacheActions } from "vuex-cache";
import { mapGetters, mapActions } from "vuex";

const getUrl = (path) => getRootFromIndexLink() + path;

export default {
    mixins: [ListMixin],
    components: {
        WorkflowInvocationDataContents,
        WorkflowInvocationStep,
        ParameterStep,
    },
    props: {
        invocation: {
            required: true,
        },
    },
    created: function() {
        this.fetchWorkflowForInstanceId(this.invocation.workflow_id);
    },
    computed: {
        ...mapGetters(["getWorkflowByInstanceId"]),
        orderedSteps() {
            return this.invocation.steps.sort((a, b) =>  a.order_index - b.order_index);
        },
        workflow() {
            return this.getWorkflowByInstanceId(this.invocation.workflow_id)
        },

    },
    methods: {
        ...mapCacheActions(['fetchWorkflowForInstanceId']),
        dataInputStepLabel(key, input) {
            const invocationStep = this.orderedSteps[key]
            let label = invocationStep && invocationStep.workflow_step_label;
            if (!label) {
                if (input.src === 'hda' || input.src === 'ldda') {
                    label = 'Input dataset'
                } else if (input.src === 'hdca') {
                    label = 'Input dataset collection'
                }
            }
            return label
        }
    },
};
</script>
