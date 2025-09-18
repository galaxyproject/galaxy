<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { computed, onUnmounted, ref, watch } from "vue";

import type { WorkflowInvocationElementView } from "@/api/invocations";
import type { WorkflowStepTyped } from "@/api/workflows";
import type { GraphStep } from "@/composables/useInvocationGraph";
import { useInvocationStore } from "@/stores/invocationStore";

import Heading from "../Common/Heading.vue";
import JobStep from "./JobStep.vue";
import ParameterStep from "./ParameterStep.vue";
import SubworkflowAlert from "./SubworkflowAlert.vue";
import WorkflowInvocationStepHeader from "./WorkflowInvocationStepHeader.vue";
import WorkflowStepTitle from "./WorkflowStepTitle.vue";
import GenericHistoryItem from "@/components/History/Content/GenericItem.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const TERMINAL_JOB_STATES = ["ok", "error", "deleted", "paused"];

const props = defineProps<{
    /** The invocation the step belongs to */
    invocation: WorkflowInvocationElementView;
    /** The workflow step being displayed */
    workflowStep: WorkflowStepTyped;
    /** The invocation graph step being displayed (if any) */
    graphStep?: GraphStep;
    /** Whether the step details are expanded (if undefined, component manages expansion state) */
    expanded?: boolean;
    /** Whether the step is being displayed in the graph view (affects styling) */
    inGraphView?: boolean;
}>();

const emit = defineEmits<{
    (e: "update:expanded", value: boolean): void;
}>();

const invocationStore = useInvocationStore();

const localExpanded = ref(Boolean(props.expanded));
const stepFetchInterval = ref<any>(undefined);

const computedExpanded = computed({
    get() {
        return props.expanded === undefined ? localExpanded.value : props.expanded;
    },
    set(value) {
        if (props.expanded === undefined) {
            localExpanded.value = value;
        } else {
            emit("update:expanded", value);
        }
    },
});

const workflowStepType = computed(() => props.workflowStep.type);

const isDataStep = computed(() => ["data_input", "data_collection_input"].includes(workflowStepType.value));

const invocationInput = computed(() => props.invocation.inputs[props.workflowStep.id]);

const invocationStep = computed(() => props.invocation.steps[props.workflowStep.id]);

const invocationStepId = computed(() => invocationStep.value?.id);

const stepDetails = computed(() =>
    invocationStepId.value ? invocationStore.getInvocationStepById(invocationStepId.value) : null,
);

const isReady = computed(() => props.invocation.steps.length > 0);

const loading = computed(() => {
    if (!isReady.value || !invocationStepId.value) {
        return true;
    }
    if (!stepDetails.value && invocationStep.value) {
        return invocationStore.isLoadingInvocationStep(invocationStepId.value);
    }
    return false;
});

const paramInput = computed(() => {
    if (stepDetails.value) {
        return Object.values(props.invocation.input_step_parameters).find(
            (param) => param.workflow_step_id === stepDetails.value?.workflow_step_id,
        );
    }
    return undefined;
});

/** Whether the step has a terminal state or jobs.
 *
 * If null, step state is unknown (e.g. step details not loaded yet) and we
 * do not poll. If false, we poll until it becomes terminal (true).
 */
const stepIsTerminal = computed<boolean | null>(() => {
    if (!stepDetails.value || !stepDetails.value.state) {
        return null;
    }
    const isTerminal =
        ["scheduled", "cancelled", "failed"].includes(stepDetails.value.state) &&
        stepDetails.value.jobs.every((job) => TERMINAL_JOB_STATES.includes(job.state));
    return isTerminal;
});

watch(
    () => stepIsTerminal.value,
    (newVal) => {
        if (newVal === false) {
            pollStepUntilTerminal();
        }
    },
    { immediate: true },
);

async function pollStepUntilTerminal() {
    if (!stepIsTerminal.value && invocationStepId.value) {
        await invocationStore.fetchInvocationStepById({ id: invocationStepId.value });
        stepFetchInterval.value = setTimeout(pollStepUntilTerminal, 3000);
    }
}

const jobStepHeading = computed(() => {
    if (stepDetails.value?.jobs && stepDetails.value.jobs.length > 1) {
        return "Jobs (Click on any job to view its details)";
    } else if (stepDetails.value?.jobs?.length === 1) {
        return "Job";
    } else {
        return "No jobs";
    }
});

function toggleStep() {
    computedExpanded.value = !computedExpanded.value;
}

onUnmounted(() => {
    if (stepFetchInterval.value) {
        clearTimeout(stepFetchInterval.value);
    }
});
</script>

<template>
    <div class="d-flex" :data-step="props.workflowStep.id">
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
                    :workflow-step="props.workflowStep"
                    :graph-step="graphStep"
                    :invocation-step="invocationStep"
                    can-expand
                    :expanded="computedExpanded" />
            </div>

            <div v-if="computedExpanded" class="portlet-content">
                <div v-if="isReady && invocationStepId !== undefined">
                    <div style="min-width: 1">
                        <BAlert v-if="loading" variant="info" show>
                            <LoadingSpan message="Loading invocation step details" />
                        </BAlert>

                        <BAlert v-else-if="!stepDetails" variant="info" show> Unable to load step details. </BAlert>

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
                                    <Heading size="md" separator>{{ jobStepHeading }}</Heading>
                                    <JobStep v-if="stepDetails.jobs?.length" class="mt-1" :jobs="stepDetails.jobs" />
                                    <BAlert v-else v-localize variant="info" show>This step has no jobs</BAlert>
                                </div>

                                <ParameterStep
                                    v-else-if="workflowStepType == 'parameter_input'"
                                    :parameters="paramInput ? [paramInput] : []" />

                                <GenericHistoryItem
                                    v-else-if="
                                        isDataStep && props.invocation.inputs && invocationInput && invocationInput.id
                                    "
                                    :item-id="invocationInput.id"
                                    :item-src="invocationInput.src" />

                                <div v-else-if="workflowStepType == 'subworkflow'">
                                    <div v-if="!stepDetails.subworkflow_invocation_id">
                                        Workflow invocation for this step is not yet scheduled.
                                        <template v-if="props.workflowStep">
                                            <div class="mt-1">This step consumes outputs from these steps:</div>
                                            <ul>
                                                <li
                                                    v-for="stepInput in Object.values(props.workflowStep.input_steps)"
                                                    :key="stepInput.source_step">
                                                    <WorkflowStepTitle
                                                        :step-index="stepInput.source_step"
                                                        :step-label="
                                                            props.invocation.steps[stepInput.source_step]
                                                                ?.workflow_step_label ||
                                                            `Step ${stepInput.source_step + 1}`
                                                        "
                                                        :step-type="props.workflowStep.type"
                                                        :step-tool-id="props.workflowStep.tool_id"
                                                        :step-tool-uuid="props.workflowStep.tool_uuid"
                                                        :step-subworkflow-id="
                                                            'workflow_id' in props.workflowStep
                                                                ? props.workflowStep.workflow_id
                                                                : null
                                                        " />
                                                </li>
                                            </ul>
                                        </template>
                                    </div>

                                    <SubworkflowAlert v-else :invocation-id="stepDetails.subworkflow_invocation_id" />
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

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

<style scoped lang="scss">
.portlet-header {
    &:hover {
        opacity: 0.8;
    }
}
</style>
