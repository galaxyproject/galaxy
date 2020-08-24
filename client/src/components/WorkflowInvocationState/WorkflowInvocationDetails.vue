<template>
    <div v-if="invocation">
        <div v-if="Object.keys(invocation.input_step_parameters).length > 0">
            <details
                ><summary><b>Invocation Parameters</b></summary>
                <b-table small caption-top :fields="['label', 'parameter_value']" :items="Object.values(invocation.input_step_parameters)"/>
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
        <div v-if="Object.keys(invocation.steps).length > 0">
            <details
                ><summary><b>Invocation Steps</b></summary>
                <div v-for="step in this.orderedSteps" v-bind:key="step.id">
                    Step {{step.order_index + 1}}: {{getToolNameByInstanceId(workflow.steps[step.order_index].tool_id)}}
                    <p>
                    {{ step }}
                    </p>
                    Workflow:
                    <p>{{workflow}}</p>
                </div>
            </details>
        </div>
    </div>
</template>
<script>
import WorkflowInvocationDataContents from "./WorkflowInvocationDataContents";
import ListMixin from "components/History/ListMixin";

import { getAppRoot } from "onload/loadConfig";
import _ from 'lodash';

import { getRootFromIndexLink } from "onload";
import { mapCacheActions } from "vuex-cache";
import { mapGetters, mapActions } from "vuex";

const getUrl = (path) => getRootFromIndexLink() + path;

export default {
    mixins: [ListMixin],
    components: {
        WorkflowInvocationDataContents,
    },
    props: {
        invocation: {
            required: true,
        },
    },
    computed: {
        ...mapGetters(["getWorkflowByInstanceId", "getToolForId", "getToolNameByInstanceId"]),
        orderedSteps() {
            return _.orderBy(this.invocation.steps, ['order_index']);
        },
        workflow() {
            return this.getWorkflowByInstanceId(this.invocation.workflow_id)
        },

    },
    mounted() {
        this.fetchTools();
    },
    methods: {
        ...mapCacheActions(["fetchWorkflowForInstanceId", "fetchToolForId"]),
        fetchTools() {
            Object.values(this.workflow.steps).map((step) => {
                console.log(step);
                if (step.tool_id) {
                    this.fetchToolForId(step.tool_id)
                }
            })
        },
        stepLabel(step) {
            const stepIndex = step.order_index + 1;
            if (step.workflow_step_label) {
                return `Step ${stepIndex}: ${step.workflow_step_label}`;
            }
            const workflowStepType = this.workflow.steps[step.order_index].type;
            switch (workflowStepType) {
                case "tool":
                    return this.toolStepLabel(step);
                case "subworkflow":
                    return this.subWorkflowStepLabel(step);
                case "parameter_input":
                    return `Step ${stepIndex}: Parameter input`;
                case "data_input":
                    `Step ${stepIndex}: Data input`
                case "data_collection_input":
                    return `Step ${stepIndex}: Data collection input`
                default:
                    return `Step ${stepIndex}: Unknown step type '${workflowStepType}'`;
            }
        },
        subWorkflowStepLabel(step) {
            const subworkflow = this.getWorkflowByInstanceId(this.workflow.steps[step.order_index].workflow_id)
            return `Step ${step.order_index + 1}: ${subworkflow.name}`
        },
        dataInputStepLabel(key, input) {
            let label = this.orderedSteps[key].workflow_step_label;
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
