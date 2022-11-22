<template>
    <div class="d-flex" :data-step="workflowStep.id">
        <div class="ui-portlet-section" style="width: 100%">
            <div class="portlet-header portlet-title portlet-operations" @click="toggleStep">
                <i :class="'portlet-title-icon fa mr-1 ' + stepIcon"></i>
                <span class="portlet-title-text">
                    <u class="step-title">{{ stepLabel }}</u>
                </span>
            </div>
            <div v-if="expanded" class="portlet-content">
                <InvocationStepProvider
                    v-if="isReady && invocationStepId !== undefined"
                    :id="invocationStepId"
                    v-slot="{ result: stepDetails, loading }"
                    auto-refresh>
                    <div style="min-width: 1">
                        <loading-span v-if="loading" :message="`Loading invocation step details`"> </loading-span>
                        <div v-else>
                            <details
                                v-if="Object.values(stepDetails.outputs).length > 0"
                                class="invocation-step-output-details">
                                <summary><b>Output Datasets</b></summary>
                                <div v-for="(value, name) in stepDetails.outputs" :key="value.id">
                                    <b>{{ name }}</b>
                                    <generic-history-item :item-id="value.id" :item-src="value.src" />
                                </div>
                            </details>
                            <details
                                v-if="Object.values(stepDetails.output_collections).length > 0"
                                class="invocation-step-output-collection-details">
                                <summary><b>Output Dataset Collections</b></summary>
                                <div v-for="(value, name) in stepDetails.output_collections" :key="value.id">
                                    <b>{{ name }}</b>
                                    <generic-history-item :item-id="value.id" :item-src="value.src" />
                                </div>
                            </details>
                            <div class="portlet-body" style="width: 100%; overflow-x: auto">
                                <details v-if="workflowStepType == 'tool'" class="invocation-step-job-details">
                                    <summary><b>Jobs</b></summary>
                                    <job-step :jobs="stepDetails.jobs" />
                                </details>
                                <parameter-step
                                    v-else-if="workflowStepType == 'parameter_input'"
                                    :parameters="[invocation.input_step_parameters[stepDetails.workflow_step_label]]" />
                                <generic-history-item
                                    v-else-if="
                                        isDataStep &&
                                        invocation &&
                                        invocation.inputs &&
                                        invocation.inputs[workflowStep.id]
                                    "
                                    :item-id="invocation.inputs[workflowStep.id].id"
                                    :item-src="invocation.inputs[workflowStep.id].src" />
                                <div v-else-if="workflowStepType == 'subworkflow'">
                                    <div v-if="!stepDetails.subworkflow_invocation_id">
                                        Workflow invocation for this step is not yet scheduled.
                                        <br />
                                        This step consumes outputs from these steps:
                                        <ul v-if="workflowStep">
                                            <li
                                                v-for="stepInput in Object.values(workflowStep.input_steps)"
                                                :key="stepInput.source_step">
                                                {{ labelForWorkflowStep(stepInput.source_step) }}
                                            </li>
                                        </ul>
                                    </div>
                                    <workflow-invocation-state
                                        v-else
                                        :invocation-id="stepDetails.subworkflow_invocation_id" />
                                </div>
                            </div>
                        </div>
                    </div>
                </InvocationStepProvider>
                <loading-span
                    v-else
                    :message="`This invocation has not been scheduled yet, step information is unavailable`">
                    <!-- Probably a subworkflow invocation, could walk back to parent and show
                         why step is not scheduled, but that's not necessary for a first pass, I think
                    -->
                </loading-span>
            </div>
        </div>
    </div>
</template>
<script>
import { useWorkflowStore } from "stores/workflowStore";
import { mapCacheActions } from "vuex-cache";
import { mapGetters, mapActions as vuexMapActions } from "vuex";
import { mapState, mapActions } from "pinia";
import WorkflowIcons from "components/Workflow/icons";
import JobStep from "./JobStep";
import ParameterStep from "./ParameterStep";
import GenericHistoryItem from "components/History/Content/GenericItem";
import { InvocationStepProvider } from "components/providers";
import LoadingSpan from "components/LoadingSpan";

export default {
    components: {
        LoadingSpan,
        JobStep,
        ParameterStep,
        InvocationStepProvider,
        GenericHistoryItem,
        WorkflowInvocationState: () => import("components/WorkflowInvocationState/WorkflowInvocationState"),
    },
    props: {
        invocation: Object,
        workflowStep: Object,
        workflow: Object,
    },
    data() {
        return {
            expanded: false,
            polling: null,
        };
    },
    computed: {
        ...mapState(useWorkflowStore, ["getWorkflowByInstanceId"]),
        ...mapGetters(["getToolForId", "getToolNameById", "getInvocationStepById"]),
        isReady() {
            return this.invocation.steps.length > 0;
        },
        invocationStepId() {
            return this.step?.id;
        },
        workflowStepType() {
            return this.workflowStep.type;
        },
        step() {
            return this.invocation.steps[this.workflowStep.id];
        },
        isDataStep() {
            return ["data_input", "data_collection_input"].includes(this.workflowStepType);
        },
        stepIcon() {
            return WorkflowIcons[this.workflowStepType];
        },
        stepLabel() {
            return this.labelForWorkflowStep(this.workflowStep.id);
        },
    },
    created() {
        this.fetchTool();
        this.fetchSubworkflow();
    },
    methods: {
        ...mapCacheActions(["fetchToolForId"]),
        ...mapActions(useWorkflowStore, ["fetchWorkflowForInstanceId"]),
        ...vuexMapActions(["fetchInvocationStepById"]),
        fetchTool() {
            if (this.workflowStep.tool_id && !this.getToolForId(this.workflowStep.tool_id)) {
                this.fetchToolForId(this.workflowStep.tool_id);
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
            const workflowStep = this.workflow.steps[stepIndex];
            const oneBasedStepIndex = stepIndex + 1;
            if (invocationStep && invocationStep.workflow_step_label) {
                return `Step ${oneBasedStepIndex}: ${invocationStep.workflow_step_label}`;
            }
            const workflowStepType = workflowStep.type;
            switch (workflowStepType) {
                case "tool":
                    return `Step ${oneBasedStepIndex}: ${this.getToolNameById(workflowStep.tool_id)}`;
                case "subworkflow": {
                    const subworkflow = this.getWorkflowByInstanceId(workflowStep.workflow_id);
                    const label = subworkflow ? subworkflow.name : "Subworkflow";
                    return `Step ${oneBasedStepIndex}: ${label}`;
                }
                case "parameter_input":
                    return `Step ${oneBasedStepIndex}: Parameter input`;
                case "data_input":
                    return `Step ${oneBasedStepIndex}: Data input`;
                case "data_collection_input":
                    return `Step ${oneBasedStepIndex}: Data collection input`;
                default:
                    return `Step ${oneBasedStepIndex}: Unknown step type '${workflowStepType}'`;
            }
        },
    },
};
</script>
