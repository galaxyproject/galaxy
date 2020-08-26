<template>
    <div class="d-flex">
        <div class="ui-portlet-section" style="width: 100%">
            <div class="portlet-header portlet-title portlet-operations" v-on:click="toggleStep">
                <i :class="'portlet-title-icon fa mr-1 ' + stepIcon"></i>
                <span class="portlet-title-text">
                    <u>{{stepLabel}}</u>
                </span>
            </div>
            <div class="portlet-content" v-show="expanded">
                <div style="min-width: 1;"/>
                <details v-if="stepDetails && Object.values(stepDetails.outputs).length > 0"><summary><b>Step Output Datasets</b></summary>
                   <div v-for="(value, name) in stepDetails.outputs" v-bind:key="value.id">
                        <b>{{name}}</b>
                    <workflow-invocation-data-contents v-bind:data_item="value" />
                    </div>
                </details>
                <details v-if="stepDetails && Object.values(stepDetails.output_collections).length > 0"><summary><b>Step Output Dataset Collections</b></summary>
                   <div v-for="(value, name) in stepDetails.output_collections" v-bind:key="value.id">
                        <b>{{name}}</b>
                    <workflow-invocation-data-contents v-bind:data_item="value" />
                </div>
                </details>
                <div class="portlet-body" style="width: 100%; overflow-x: auto;">
                    <step-jobs :jobs="stepDetails.jobs" v-if="stepDetails && stepDetails.jobs.length > 0"/>
                    <workflow-invocation-state :invocationId="stepDetails.subworkflow_invocation_id" v-if="stepDetails && stepDetails.subworkflow_invocation_id"/>
                </div>
                <div style="min-width: 1;"/>
            </div>
        </div>
    </div>
</template>
<script>
import { mapCacheActions } from "vuex-cache";
import { mapGetters, mapActions } from "vuex";
import WorkflowInvocationDataContents from "./WorkflowInvocationDataContents";
import StepJobs from "./StepJobs";

export default {
    components: {
        StepJobs,
        WorkflowInvocationDataContents,
        WorkflowInvocationState: () => import("components/WorkflowInvocationState/WorkflowInvocationState"),
    },
    props: {
        step: Object,
        workflow: Object,
    },
    data() {
        return {
            expanded: false,
        };
    },
    mounted() {
        this.fetchTool();
        this.fetchInvocationStepById(this.step.id)
    },
    computed: {
        ...mapGetters(["getToolForId", "getToolNameById", "getWorkflowByInstanceId", "getInvocationStepById"]),
        workflowStep() {
            return this.workflow.steps[this.step.order_index];
        },
        workflowStepType() {
            return this.workflowStep.type;
        },
        isDataStep() {
            return ['data_input', 'data_collection_input'].includes(this.workflowStepType);
        },
        stepIcon() {
            switch (this.workflowStepType) {
                case "data_input":
                    return 'fa-file';
                case "data_collection_input":
                    return 'fa-folder-o';
                case "parameter_input":
                    return 'fa-pencil';
                default:
                    return 'fa-wrench';
            }
        },
        stepDetails() {
            return this.getInvocationStepById(this.step.id)
        },
        stepLabel() {
            const stepIndex = this.step.order_index + 1;
            if (this.step.workflow_step_label) {
                return `Step ${stepIndex}: ${this.step.workflow_step_label}`;
            }
            const workflowStep = this.workflow.steps[this.step.order_index]
            const workflowStepType = workflowStep.type;
            switch (workflowStepType) {
                case "tool":
                    return this.toolStepLabel(workflowStep);
                case "subworkflow":
                    return this.subWorkflowStepLabel(workflowStep);
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
    },
    methods: {
        ...mapCacheActions(["fetchToolForId", "fetchInvocationStepById"]),
        fetchTool() {
            if (this.workflowStep.tool_id && !this.getToolForId(this.workflowStep.tool_id)) {
                    this.fetchToolForId(this.workflowStep.tool_id)
                }
        },
        toggleStep() {
            this.expanded = !this.expanded;
        },
        toolStepLabel(workflowStep) {
            const name = this.getToolNameById(workflowStep.tool_id);
            return `Step ${this.step.order_index +1}: ${name}`;
        },
        subWorkflowStepLabel(workflowStep) {
            const subworkflow = this.getWorkflowByInstanceId(workflowStep.workflow_id)
            return `Step ${this.step.order_index + 1}: ${subworkflow.name}`
        },
    },    
}
</script>