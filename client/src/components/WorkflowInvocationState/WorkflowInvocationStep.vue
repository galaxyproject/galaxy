<template>
    <div class="d-flex">
        <div class="ui-portlet-section" style="width: 100%">
            <div class="portlet-header portlet-title portlet-operations" v-on:click="toggleStep">
                <i :class="'portlet-title-icon fa mr-1 ' + stepIcon"></i>
                <span class="portlet-title-text">
                    <u>{{stepLabel}}</u>
                </span>
            </div>
            <div class="portlet-content" v-if="expanded">
                <div style="min-width: 1;"/>
                <div v-if="!stepDetails">
                    This invocation has not been scheduled yet, step information is unavailable
                    <!-- Probably a subworkflow invocation, could walk back to parent and show
                         why step is not scheduled, but that's not necessary for a forst pass, I think
                    -->
                </div>
                <div v-else>
                    <details v-if="Object.values(stepDetails.outputs).length > 0"><summary><b>Step Output Datasets</b></summary>
                       <div v-for="(value, name) in stepDetails.outputs" v-bind:key="value.id">
                            <b>{{name}}</b>
                        <workflow-invocation-data-contents v-bind:data_item="value" />
                        </div>
                    </details>
                    <details v-if="Object.values(stepDetails.output_collections).length > 0"><summary><b>Step Output Dataset Collections</b></summary>
                       <div v-for="(value, name) in stepDetails.output_collections" v-bind:key="value.id">
                            <b>{{name}}</b>
                        <workflow-invocation-data-contents v-bind:data_item="value" />
                    </div>
                    </details>
                    <div class="portlet-body" style="width: 100%; overflow-x: auto;">
                        <step-jobs :jobs="stepDetails.jobs" v-if="stepDetails && stepDetails.jobs.length > 0"/>
                        <div v-else-if="!stepDetails.subworkflow_invocation_id">
                            Jobs for this step are not yet scheduled.
                            <p></p>
                            This step consumes outputs from these steps:
                            <ul v-if="workflowStep">
                                <li v-for="stepInput in Object.values(workflowStep.input_steps)" :key="stepInput.source_step">{{labelForWorkflowStep(stepInput.source_step)}}</li>
                            </ul>
                        </div>
                        <workflow-invocation-state :invocationId="stepDetails.subworkflow_invocation_id" v-if="stepDetails && stepDetails.subworkflow_invocation_id"/>
                    </div>
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
        orderedSteps: Array,
        workflowStep: Object,
        workflow: Object,
    },
    data() {
        return {
            expanded: false,
            polling: null,

        };
    },
    created() {
        this.fetchTool();
        this.fetchSubworkflow();
        this.pollStepDetailsUntilTerminal();
    },
    computed: {
        ...mapGetters(["getToolForId", "getToolNameById", "getWorkflowByInstanceId", "getInvocationStepById"]),
        invocationSteps() {
            return this.orderedSteps;
        },
        invocationStepId() {
            if (this.step) {
                return this.step.id
            }
        },
        workflowStepType() {
            return this.workflowStep.type;
        },
        step() {
            return this.invocationSteps[this.workflowStep.id];
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
            if (this.step) {
                return this.getInvocationStepById(this.step.id);
            }
        },
        stepLabel() {
            return this.labelForWorkflowStep(this.workflowStep.id);
        },
        stepIsTerminal() {
            return (this.stepDetails && ['scheduled', 'cancelled', 'failed'].includes(this.stepDetails.state))
        }

    },
    methods: {
        ...mapCacheActions(["fetchToolForId", 'fetchWorkflowForInstanceId']),
        ...mapActions(["fetchInvocationStepById"]),
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
        pollStepDetailsUntilTerminal: function () {
            clearInterval(this.polling);
            if (!this.stepIsTerminal) {
                if (this.step) {
                    this.fetchInvocationStepById(this.step.id);
                }
                this.polling = setInterval(this.pollStepDetailsUntilTerminal, 3000);
            }
        },
        beforeDestroy () {
            clearInterval(this.polling)
        },
        toggleStep() {
            this.expanded = !this.expanded;
        },
        labelForWorkflowStep(stepIndex) {
            const invocationStep = this.invocationSteps[stepIndex];
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
                    const subworkflow = this.getWorkflowByInstanceId(workflowStep.workflow_id)
                    const label = subworkflow ? subworkflow.name : 'Subworkflow'
                    return `Step ${oneBasedStepIndex}: ${label}`;
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