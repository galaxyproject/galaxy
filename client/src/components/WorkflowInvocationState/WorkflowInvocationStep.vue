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
                    <div v-if="stepDetails && workflowStep">
                        <p></p>
                        {{stepDetails}}
                        <p></p>
                        {{workflowStep}}
                    </div>
                    <div v-else-if="stepDetails && !stepDetails.subworkflow_invocation_id">
                        Jobs for this step are not yet scheduled.
                        <p></p>
                        This step consumes outputs from these Steps:
                        <ul v-if="workflowStep">
                            <li v-for="stepInput in Object.values(workflowStep.input_steps)" :key="stepInput.source_step">{{labelForWorkflowStep(stepInput.source_step)}}</li>
                        </ul>
                    </div>
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
        invocation: Object,
        step: Object,
        workflow: Object,
    },
    data() {
        return {
            expanded: false,
        };
    },
    created() {
        this.fetchTool();
        this.fetchSubworkflow();
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
            return this.labelForWorkflowStep(this.step.order_index);
        },

    },
    methods: {
        ...mapCacheActions(["fetchToolForId", "fetchInvocationStepById", 'fetchWorkflowForInstanceId']),
        fetchTool() {
            if (this.workflowStep.tool_id && !this.getToolForId(this.workflowStep.tool_id)) {
                    this.fetchToolForId(this.workflowStep.tool_id)
                }
        },
        fetchSubworkflow() {
            if (this.workflowStep.workflow_id) {
                this.fetchWorkflowForInstanceId(this.workflowStep.workflow_id);
            }
        },
        toggleStep() {
            this.expanded = !this.expanded;
        },
        labelForWorkflowStep(stepIndex) {
            const invocationStep = this.invocation.steps[stepIndex];
            const workflowStep = this.workflow.steps[stepIndex]
            const oneBasedStepIndex = stepIndex + 1;
            if (invocationStep && invocationStep.workflow_step_label) {
                return `Step ${oneBasedStepIndex}: ${invocationStep.workflow_step_label}`;
            }
            const workflowStepType = workflowStep.type;
            switch (workflowStepType) {
                case "tool":
                    return `Step ${oneBasedStepIndex}: ${this.getToolNameById(workflowStep.tool_id)}`;
                case "subworkflow":
                    return `Step ${oneBasedStepIndex}: ${this.getWorkflowByInstanceId(workflowStep.workflow_id).name}`;
                case "parameter_input":
                    return `Step ${oneBasedStepIndex}: Parameter input`;
                case "data_input":
                    `Step ${oneBasedStepIndex}: Data input`
                case "data_collection_input":
                    return `Step ${oneBasedStepIndex}: Data collection input`
                default:
                    return `Step ${oneBasedStepIndex}: Unknown step type '${workflowStepType}'`;
            }
        },
    },    
}
</script>