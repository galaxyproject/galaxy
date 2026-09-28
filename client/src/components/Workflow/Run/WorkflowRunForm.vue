<template>
    <div v-if="currentUser && currentHistoryId" class="workflow-expanded-form">
        <BAlert v-if="!canRunOnHistory" variant="warning" show>
            <span v-localize>
                The workflow cannot run because the current history is immutable. Please select a different history or
                send the results to a new one.
            </span>
        </BAlert>
        <div class="h4 clearfix mb-3">
            <b>Workflow: {{ model.name }}</b> <i>(version: {{ model.runData.version + 1 }})</i>
            <div class="float-right d-flex flex-gapx-1">
                <GButton
                    v-if="!disableSimpleForm"
                    v-g-tooltip.hover
                    transparent
                    color="blue"
                    class="text-decoration-none"
                    title="Use simplified run form instead"
                    @click="emit('showSimple')">
                    <span class="fas fa-arrow-left" /> Simple Form
                </GButton>
                <ButtonSpinner
                    id="run-workflow"
                    title="Run Workflow"
                    :tooltip="runButtonTooltip"
                    :disabled="!canRunOnHistory || hasCredentialErrors"
                    :wait="showExecuting"
                    @onClick="onExecute" />
            </div>
        </div>

        <BAlert v-if="disableSimpleFormReason" show variant="warning">
            This is the legacy workflow run form.
            <span v-if="disableSimpleFormReason === 'hasReplacementParameters'">
                This workflow contains parameters in tool steps that require advanced handling. The simplified form does
                not support these parameters.
            </span>
            <span v-else-if="disableSimpleFormReason === 'hasDisconnectedInputs'">
                One or more tools in this workflow have required inputs that are not connected to other steps. The
                simplified form cannot handle disconnected runtime inputs.
            </span>
            <span v-else-if="disableSimpleFormReason === 'hasWorkflowResourceParameters'">
                This workflow is configured with resource request parameters. The simplified form does not support
                workflows with resource options.
            </span>
        </BAlert>

        <WorkflowCredentials v-if="credentialTools.length" :tool-identifiers="credentialTools" />

        <FormCard v-if="wpInputsAvailable" title="Workflow Parameters">
            <template v-slot:body>
                <FormDisplay :inputs="wpInputs" @onChange="onWpInputs" />
            </template>
        </FormCard>
        <FormCard title="History Options">
            <template v-slot:body>
                <FormDisplay :inputs="historyInputs" @onChange="onHistoryInputs" />
            </template>
        </FormCard>
        <FormCard title="Job re-use Options">
            <template v-slot:body>
                <FormElement
                    v-model="useCachedJobs"
                    title="Attempt to re-use jobs with identical parameters?"
                    help="This may skip executing jobs that you have already run."
                    type="boolean" />
            </template>
        </FormCard>
        <OnCompleteActions v-model="onCompleteActions" />
        <FormCard v-if="resourceInputsAvailable" title="Workflow Resource Options">
            <template v-slot:body>
                <FormDisplay :inputs="resourceInputs" @onChange="onResourceInputs" />
            </template>
        </FormCard>
        <div v-for="step in model.steps" :key="step.index">
            <WorkflowRunDefaultStep
                v-if="step.step_type == 'tool' || step.step_type == 'subworkflow'"
                :model="step"
                :replace-params="getReplaceParams(step.inputs)"
                :validation-scroll-to="getValidationScrollTo(step.index)"
                :history-id="currentHistoryId"
                @onChange="onToolStepInputs"
                @onValidation="onValidation" />
            <WorkflowRunInputStep
                v-else
                :model="step"
                :validation-scroll-to="getValidationScrollTo(step.index)"
                :history-id="currentHistoryId"
                @onChange="onDefaultStepInputs"
                @onValidation="onValidation" />
        </div>
    </div>
</template>

<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";

import type { WorkflowInvocation } from "@/api/invocations";
import type { ServiceCredentialsDefinition } from "@/api/userCredentials";
import type { FormData, FormInputNode } from "@/components/Form/composables/useFormState";
import { useUserMultiToolCredentials } from "@/composables/userMultiToolCredentials";
import { useHistoryStore } from "@/stores/historyStore";
import { useToolsServiceCredentialsDefinitionsStore } from "@/stores/toolsServiceCredentialsDefinitionsStore";
import { useUserStore } from "@/stores/userStore";

import { getReplacements } from "./model";
import { invokeWorkflow } from "./services";

import WorkflowRunDefaultStep from "./WorkflowRunDefaultStep.vue";
import WorkflowRunInputStep from "./WorkflowRunInputStep.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import ButtonSpinner from "@/components/Common/ButtonSpinner.vue";
import FormCard from "@/components/Form/FormCard.vue";
import FormDisplay from "@/components/Form/FormDisplay.vue";
import FormElement from "@/components/Form/FormElement.vue";
import OnCompleteActions from "@/components/Workflow/Run/OnCompleteActions.vue";
import WorkflowCredentials from "@/components/Workflow/Run/WorkflowCredentials.vue";

type ValidationScrollTo = [string, string] | [];

interface CredentialStep {
    id: string;
    version: string;
    step_type: string;
    credentials?: ServiceCredentialsDefinition[];
}

interface Props {
    /**
     * Whether the current history accepts new datasets
     */
    canMutateCurrentHistory: boolean;
    /**
     * Parsed run data, a ``WorkflowRunModel``
     */
    model: Record<string, any>;
    /**
     * Hide the button that switches to the simple run form
     * @default false
     */
    disableSimpleForm?: boolean;
    /**
     * Why the simple run form is unavailable, if it is
     * @default undefined
     */
    disableSimpleFormReason?: string;
}

const props = withDefaults(defineProps<Props>(), {
    disableSimpleForm: false,
    disableSimpleFormReason: undefined,
});

const emit = defineEmits<{
    (e: "showSimple"): void;
    (e: "submissionSuccess", invocations: WorkflowInvocation[]): void;
    (e: "submissionError", error: any): void;
}>();

const { currentUser } = storeToRefs(useUserStore());
const { currentHistoryId } = storeToRefs(useHistoryStore());

const showExecuting = ref(false);
const stepScrollTo = ref<{ stepId?: string; stepError?: ValidationScrollTo }>({});
const wpData = ref<FormData>({});
const historyData = ref<FormData>({});
const useCachedJobs = ref(false);
const onCompleteActions = ref<Record<string, unknown>[]>([]);
// Plain objects: step updates must not re-render the form, as with the untracked keys before.
const stepData: Record<string, FormData> = {};
const stepValidations: Record<string, [string, string] | null> = {};
const inputs: Record<string, unknown> = {};
let resourceData: FormData | undefined;

const historyInputs = [
    {
        type: "conditional",
        name: "new_history",
        test_param: {
            name: "check",
            label: "Send results to a new history",
            type: "boolean",
            value: "false",
            help: "",
        },
        cases: [
            {
                value: "true",
                inputs: [
                    {
                        name: "name",
                        label: "History name",
                        type: "text",
                        value: props.model.name,
                    },
                ],
            },
            {
                value: "false",
                inputs: [],
            },
        ],
    },
];

const credentialTools = computed(() => {
    return props.model.steps
        .filter((step: CredentialStep) => step.step_type === "tool" && step.credentials?.length)
        .map((step: CredentialStep) => {
            const { setToolServiceCredentialsDefinitionFor } = useToolsServiceCredentialsDefinitionsStore();
            setToolServiceCredentialsDefinitionFor(step.id, step.version, step.credentials!);

            return {
                toolId: step.id,
                toolVersion: step.version,
            };
        });
});

const resourceInputs = computed(() => toArray(props.model.workflowResourceParameters));

const resourceInputsAvailable = computed(() => resourceInputs.value.length > 0);

const wpInputs = computed(() => toArray(props.model.wpInputs));

const wpInputsAvailable = computed(() => wpInputs.value.length > 0);

const shouldRunOnNewHistory = computed(() => Boolean(historyData.value["new_history|name"]));

const canRunOnHistory = computed(() => shouldRunOnNewHistory.value || props.canMutateCurrentHistory);

const hasCredentialErrors = computed(() => {
    if (credentialTools.value.length) {
        const { hasUserProvidedAllRequiredToolsServiceCredentials } = useUserMultiToolCredentials(
            credentialTools.value,
        );
        return !hasUserProvidedAllRequiredToolsServiceCredentials.value;
    }
    return false;
});

const runButtonTooltip = computed(() => {
    if (hasCredentialErrors.value) {
        return "Please provide all required credentials before running the workflow.";
    }
    return "Run workflow";
});

function getReplaceParams(stepInputs: FormInputNode[]) {
    return getReplacements(stepInputs, stepData, wpData.value) as Record<string, unknown>;
}

function getValidationScrollTo(stepId: string): ValidationScrollTo {
    if (stepScrollTo.value.stepId == stepId) {
        return stepScrollTo.value.stepError ?? [];
    }
    return [];
}

function onDefaultStepInputs(stepId: string, data: FormData) {
    inputs[stepId] = data.input;
}

function onToolStepInputs(stepId: string, data: FormData) {
    stepData[stepId] = data;
}

function onHistoryInputs(data: FormData) {
    historyData.value = data;
}

function onResourceInputs(data: FormData) {
    resourceData = data;
}

function onWpInputs(data: FormData) {
    wpData.value = data;
}

function onValidation(stepId: string, validation: [string, string] | null) {
    stepValidations[stepId] = validation;
}

function onExecute() {
    for (const [stepId, stepValidation] of Object.entries(stepValidations)) {
        if (stepValidation) {
            stepScrollTo.value = {
                stepId: stepId,
                stepError: stepValidation.slice() as [string, string],
            };
            return;
        }
    }

    const parameters: Record<string, FormData> = {};
    Object.entries(stepData).forEach(([stepId, stepValues]) => {
        const stepDataFiltered: FormData = {};
        Object.entries(stepValues).forEach(([inputName, inputValue]) => {
            if (!props.model.isConnected(stepId, inputName)) {
                stepDataFiltered[inputName] = inputValue;
            }
        });
        parameters[stepId] = stepDataFiltered;
    });

    const jobDef = {
        new_history_name: historyData.value["new_history|name"] ? historyData.value["new_history|name"] : null,
        history_id: !historyData.value["new_history|name"] ? props.model.historyId : null,
        resource_params: resourceData,
        replacement_params: wpData.value,
        use_cached_job: useCachedJobs.value,
        inputs: inputs,
        parameters: parameters,
        // Tool form will submit flat maps for each parameter
        // (e.g. "repeat_0|cond|param": "foo" instead of nested
        // data structures).
        parameters_normalized: true,
        // Tool form always wants a list of invocations back
        // so that inputs can be batched.
        batch: true,
        // the user is already warned if tool versions are wrong,
        // they can still choose to invoke the workflow anyway.
        require_exact_tool_versions: false,
        version: props.model.runData.version,
        // Completion actions to run when workflow finishes
        on_complete: onCompleteActions.value.length > 0 ? onCompleteActions.value : null,
    };

    console.debug("WorkflowRunForm::onExecute()", "Ready for submission.", jobDef);
    showExecuting.value = true;
    invokeWorkflow(props.model.workflowId, jobDef)
        .then((invocations) => {
            console.debug("WorkflowRunForm::onExecute()", "Submission successful.", invocations);
            showExecuting.value = false;
            emit("submissionSuccess", invocations);
        })
        .catch((e) => {
            console.debug("WorkflowRunForm::onExecute()", "Submission failed.", e);
            showExecuting.value = false;
            const errorData = e && e.response && e.response.data && e.response.data.err_data;
            if (errorData) {
                try {
                    const errorEntries = Object.entries(errorData);
                    stepScrollTo.value = {
                        stepId: errorEntries[0]![0],
                        stepError: Object.entries(errorEntries[0]![1] as object)[0] as [string, string],
                    };
                } catch (errorFormatting) {
                    console.debug(
                        errorFormatting,
                        "WorkflowRunForm::onExecute()",
                        "Invalid server error response format.",
                        errorData,
                    );
                    emit("submissionError", e);
                }
            } else {
                emit("submissionError", e);
            }
        });
}

function toArray(obj: Record<string, FormInputNode> | undefined): FormInputNode[] {
    return obj ? Object.values(obj) : [];
}
</script>
