<template>
    <div class="d-flex" :data-step="workflowStep.id">
        <div :class="{ 'ui-portlet-section': !inGraphView }" style="width: 100%">
            <div
                v-if="!inGraphView"
                class="portlet-header portlet-operations cursor-pointer"
                :class="graphStep?.headerClass"
                role="button"
                tabindex="0"
                @keyup.enter="toggleStep"
                @click="toggleStep">
                <WorkflowInvocationStepHeader
                    :workflow-step="workflowStep"
                    :graph-step="graphStep"
                    :invocation-step="step"
                    can-expand
                    :expanded="computedExpanded" />
            </div>
            <div v-if="computedExpanded" class="portlet-content">
                <InvocationStepProvider
                    v-if="isReady && invocationStepId !== undefined"
                    :id="invocationStepId"
                    v-slot="{ result: stepDetails, loading }"
                    auto-refresh>
                    <div style="min-width: 1">
                        <LoadingSpan v-if="loading" :message="`Loading invocation step details`"> </LoadingSpan>
                        <div v-else>
                            <div
                                v-if="!isDataStep && Object.values(stepDetails.outputs).length > 0"
                                class="invocation-step-output-details">
                                <Heading size="md" separator>Output Datasets</Heading>
                                <div v-for="(value, name) in stepDetails.outputs" :key="value.id">
                                    <b>{{ name }}</b>
                                    <GenericHistoryItem :item-id="value.id" :item-src="value.src" />
                                </div>
                            </div>
                            <div
                                v-if="!isDataStep && Object.values(stepDetails.output_collections).length > 0"
                                class="invocation-step-output-collection-details">
                                <Heading size="md" separator>Output Dataset Collections</Heading>
                                <div v-for="(value, name) in stepDetails.output_collections" :key="value.id">
                                    <b>{{ name }}</b>
                                    <GenericHistoryItem :item-id="value.id" :item-src="value.src" />
                                </div>
                            </div>
                            <div class="portlet-body" style="width: 100%; overflow-x: auto">
                                <div
                                    v-if="workflowStepType == 'tool'"
                                    class="invocation-step-job-details"
                                    :open="inGraphView">
                                    <Heading size="md" separator>{{ jobStepHeading(stepDetails) }}</Heading>
                                    <JobStep v-if="stepDetails.jobs?.length" class="mt-1" :jobs="stepDetails.jobs" />
                                    <b-alert v-else v-localize variant="info" show>This step has no jobs</b-alert>
                                </div>
                                <ParameterStep
                                    v-else-if="workflowStepType == 'parameter_input'"
                                    :parameters="[getParamInput(stepDetails)]" />
                                <GenericHistoryItem
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
                                                <WorkflowStepTitle v-bind="titleProps(stepInput.source_step)" />
                                            </li>
                                        </ul>
                                    </div>
                                    <WorkflowInvocationState
                                        v-else
                                        is-subworkflow
                                        :invocation-id="stepDetails.subworkflow_invocation_id" />
                                </div>
                            </div>
                        </div>
                    </div>
                </InvocationStepProvider>
                <LoadingSpan
                    v-else
                    :message="`This invocation has not been scheduled yet, step information is unavailable`">
                    <!-- Probably a subworkflow invocation, could walk back to parent and show
                         why step is not scheduled, but that's not necessary for a first pass, I think
                    -->
                </LoadingSpan>
            </div>
        </div>
    </div>
</template>
<script>
import GenericHistoryItem from "components/History/Content/GenericItem";
import LoadingSpan from "components/LoadingSpan";
import { InvocationStepProvider } from "components/providers";
import { mapActions, mapState } from "pinia";
import { useToolStore } from "stores/toolStore";
import { useWorkflowStore } from "stores/workflowStore";

import ParameterStep from "./ParameterStep";
import WorkflowStepTitle from "./WorkflowStepTitle";

import Heading from "../Common/Heading.vue";
import JobStep from "./JobStep.vue";
import WorkflowInvocationStepHeader from "./WorkflowInvocationStepHeader.vue";

export default {
    components: {
        LoadingSpan,
        Heading,
        JobStep,
        ParameterStep,
        InvocationStepProvider,
        GenericHistoryItem,
        WorkflowInvocationStepHeader,
        WorkflowStepTitle,
        WorkflowInvocationState: () => import("components/WorkflowInvocationState/WorkflowInvocationState"),
    },
    props: {
        invocation: Object,
        workflowStep: Object,
        workflow: Object,
        graphStep: { type: Object, default: undefined },
        expanded: { type: Boolean, default: undefined },
        inGraphView: { type: Boolean, default: false },
    },
    data() {
        return {
            polling: null,
            localExpanded: this.expanded === undefined ? false : this.expanded,
        };
    },
    computed: {
        ...mapState(useWorkflowStore, ["getStoredWorkflowByInstanceId"]),
        ...mapState(useToolStore, ["getToolForId", "getToolNameById"]),
        isReady() {
            return this.invocation.steps.length > 0;
        },
        // a computed property that assesses whether we have an expanded prop
        computedExpanded: {
            get() {
                return this.expanded === undefined ? this.localExpanded : this.expanded;
            },
            set(value) {
                if (this.expanded === undefined) {
                    this.localExpanded = value;
                } else {
                    this.$emit("update:expanded", value);
                }
            },
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
    },
    methods: {
        ...mapActions(useWorkflowStore, ["fetchWorkflowForInstanceId"]),
        ...mapActions(useToolStore, ["fetchToolForId"]),
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
        getParamInput(stepDetails) {
            return Object.values(this.invocation.input_step_parameters).find(
                (param) => param.workflow_step_id === stepDetails.workflow_step_id
            );
        },
        jobStepHeading(stepDetails) {
            if (stepDetails.jobs?.length > 1) {
                return "Jobs (Click on any job to view its details)";
            } else if (stepDetails.jobs?.length === 1) {
                return "Job";
            } else {
                return "No jobs";
            }
        },
        toggleStep() {
            this.computedExpanded = !this.computedExpanded;
        },
        titleProps(stepIndex) {
            const invocationStep = this.invocation.steps[stepIndex];
            const workflowStep = this.workflow.steps[stepIndex];
            const rval = {
                stepIndex: stepIndex,
                stepLabel: invocationStep && invocationStep.workflow_step_label,
                stepType: workflowStep.type,
                stepToolId: workflowStep.tool_id,
                stepSubworkflowId: workflowStep.workflow_id,
            };
            return rval;
        },
    },
};
</script>

<style scoped lang="scss">
.portlet-header {
    &:hover {
        opacity: 0.8;
    }
}
</style>
