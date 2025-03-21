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
                        <LoadingSpan v-if="loading" :message="`加载调用步骤详情`"> </LoadingSpan>
                        <div v-else>
                            <div
                                v-if="!isDataStep && Object.values(stepDetails.outputs).length > 0"
                                class="invocation-step-output-details">
                                <Heading size="md" separator>输出数据集</Heading>
                                <div v-for="(value, name) in stepDetails.outputs" :key="value.id">
                                    <b>{{ name }}</b>
                                    <GenericHistoryItem :item-id="value.id" :item-src="value.src" />
                                </div>
                            </div>
                            <div
                                v-if="!isDataStep && Object.values(stepDetails.output_collections).length > 0"
                                class="invocation-step-output-collection-details">
                                <Heading size="md" separator>输出数据集集合</Heading>
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
                                    <b-alert v-else v-localize variant="info" show>此步骤没有任务</b-alert>
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
                                        此步骤的工作流调用尚未安排。
                                        <br />
                                        该步骤消耗以下步骤的输出：
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
                    :message="`此调用尚未安排，步骤信息不可用`">
                    <!-- 可能是子工作流调用，可能需要回到父工作流并显示步骤未安排的原因，
                         但我认为对于第一次的实现来说，这不是必需的
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
                return "任务（点击任何任务查看其详情）";
            } else if (stepDetails.jobs?.length === 1) {
                return "任务";
            } else {
                return "没有任务";
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
