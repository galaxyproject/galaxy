<script setup lang="ts">
import { faReadme } from "@fortawesome/free-brands-svg-icons";
import { faArrowRight, faCog, faSitemap } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BFormCheckbox, BOverlay } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";

import type { WorkflowInvocationRequestInputs } from "@/api/invocations";
import type { ServiceCredentialsDefinition } from "@/api/users";
import type { DataOption } from "@/components/Form/Elements/FormData/types";
import type { FormParameterTypes } from "@/components/Form/parameterTypes";
import { isWorkflowInput } from "@/components/Workflow/constants";
import { useConfig } from "@/composables/config";
import { usePersistentToggle } from "@/composables/persistentToggle";
import { usePanels } from "@/composables/usePanels";
import { useWorkflowInstance } from "@/composables/useWorkflowInstance";
import { provideScopedWorkflowStores } from "@/composables/workflowStores";
import { useHistoryStore } from "@/stores/historyStore";
import { errorMessageAsString } from "@/utils/simple-error";

import { invokeWorkflow } from "./services";

import WorkflowAnnotation from "../WorkflowAnnotation.vue";
import WorkflowNavigationTitle from "../WorkflowNavigationTitle.vue";
import WorkflowHelpDisplay from "./WorkflowHelpDisplay.vue";
import WorkflowRunGraph from "./WorkflowRunGraph.vue";
import WorkflowStorageConfiguration from "./WorkflowStorageConfiguration.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import GButtonGroup from "@/components/BaseComponents/GButtonGroup.vue";
import Heading from "@/components/Common/Heading.vue";
import WorkflowCredentialsManagement from "@/components/Common/WorkflowCredentialsManagement.vue";
import FormDisplay from "@/components/Form/FormDisplay.vue";
import HelpText from "@/components/Help/HelpText.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface Props {
    model: Record<string, any>;
    targetHistory?: string;
    useJobCache?: boolean;
    canMutateCurrentHistory: boolean;
    requestState?: WorkflowInvocationRequestInputs;
    isRerun?: boolean;
    landingUuid?: string;
}

const props = withDefaults(defineProps<Props>(), {
    targetHistory: "current",
    useJobCache: false,
    requestState: undefined,
    isRerun: false,
    landingUuid: undefined,
});

const emit = defineEmits<{
    (e: "showAdvanced"): void;
    (e: "submissionSuccess", invocations: any): void;
    (e: "submissionError", error: string): void;
}>();

const { stateStore } = provideScopedWorkflowStores(props.model.workflowId);
const { activeNodeId } = storeToRefs(stateStore);

const { config, isConfigLoaded } = useConfig(true);
const { showPanels } = usePanels();

const formData = ref<Record<string, any>>({});
const inputTypes = ref<Record<string, string>>({});
const stepValidation = ref<[string, string] | null>(null);
const sendToNewHistory = ref(props.targetHistory === "new" || props.targetHistory === "prefer_new");
const useCachedJobs = ref(props.useJobCache);
const splitObjectStore = ref(false);
const preferredObjectStoreId = ref<string | null>(null);
const preferredIntermediateObjectStoreId = ref<string | null>(null);
const waitingForRequest = ref(false);
const showRightPanel = ref<"help" | "graph" | null>(null);
const checkInputMatching = ref(props.requestState !== undefined);

const showGraph = computed(() => showRightPanel.value === "graph");
const showHelp = computed(() => showRightPanel.value === "help");

const { toggled: showRuntimeSettingsPanel, toggle: toggleRuntimeSettings } =
    usePersistentToggle("workflow-run-settings-panel");

const { changingCurrentHistory } = storeToRefs(useHistoryStore());

// Workflow REAME/help panel setup
const { workflow, loading: workflowLoading } = useWorkflowInstance(props.model.runData.workflow_id);
watch(
    () => workflow.value,
    (workflow) => {
        if (workflow) {
            // once the workflow loads, and if we are not showing panels, show the help if it exists by default
            showRightPanel.value = !showPanels.value && workflow.readme ? "help" : null;
        }
    },
    { immediate: true },
);

watch(
    () => showGraph.value,
    (show) => {
        if (!show) {
            activeNodeId.value = null;
        }
    },
);
const computedActiveNodeId = computed<number | undefined>(() => {
    if (showGraph.value) {
        if (activeNodeId.value !== null && activeNodeId.value !== undefined) {
            return activeNodeId.value;
        }
    }
    return undefined;
});

const formInputs = computed(() => {
    const inputs = [] as any[];
    // Add workflow parameters.
    Object.values(props.model.wpInputs).forEach((input) => {
        const inputCopy = Object.assign({}, input) as any;
        // do we want to keep the color if we're not showing steps?
        inputCopy.color = undefined;
        inputs.push(inputCopy);
        inputTypes.value[inputCopy.name] = "replacement_parameter";
    });
    // Add actual input modules.
    props.model.steps.forEach((step: any, i: number) => {
        if (isWorkflowInput(step.step_type)) {
            const stepName = new String(step.step_index) as any;
            const stepLabel = step.step_label || new String(step.step_index + 1);

            // For the `WorkflowInvocationRequestModel`, (used in `WorkflowRerun`) if there is no step_label, it does not have
            // `step.step_index + 1` as a label, and has `step.step_index` instead.
            const rerunStateIndex = !step.step_label ? new String(step.step_index) : stepLabel;

            const stepType = step.step_type;
            const help = step.annotation;
            const longFormInput = step.inputs[0];
            const stepAsInput = Object.assign({}, longFormInput, {
                name: stepName,
                help: help,
                label: stepLabel,
            });

            if (props.requestState) {
                if (props.isRerun) {
                    const requestStateKeys = Object.keys(props.requestState);

                    let value;
                    if (props.requestState[rerunStateIndex]) {
                        // request state has the step_label as key
                        value = props.requestState[rerunStateIndex];
                    } else if (requestStateKeys[i] !== undefined && requestStateKeys[i] === "") {
                        // request state has "" as key on the `i` position
                        value = Object.values(props.requestState)[i];
                    }

                    if (value) {
                        if (stepType === "data_input" || stepType === "data_collection_input") {
                            // Note: This is different from workflow landings because `WorkflowInvocationRequestModel`
                            //       does not provide an object with `values` property.
                            stepAsInput.value = {
                                values: !Array.isArray(value) ? [value] : value,
                            };
                        } else {
                            stepAsInput.value = value;
                        }
                    }
                } else if (props.requestState[stepLabel]) {
                    const value = props.requestState[stepLabel];
                    stepAsInput.value = value;
                }
            }

            // disable collection mapping...
            stepAsInput.flavor = "module";
            inputs.push(stepAsInput);
            inputTypes.value[stepName] = stepType;
        }
    });
    return inputs;
});

/**
 * Returns the list of steps that do not match the workflow rerun `props.requestState`.
 *
 * TODO: Until form elements are typed better, this is a little shady.
 * We do not compare values for the types in the last `else if` statement.
 * And for the `select` type, we assume that the values are arrays of strings or numbers.
 * @returns {string[]} The list of steps indices that do not match the request state.
 */
const stepsNotMatchingRequest = computed<string[]>(() => {
    if (!props.isRerun || !checkInputMatching.value || !props.requestState) {
        return [];
    }

    const inputs = formInputs.value;
    const data = formData.value;
    const notMatching: string[] = [];

    for (const input of inputs) {
        if (input.name in data) {
            const type = input.type as FormParameterTypes;

            if ((type === "data" || type === "data_collection") && input.value?.values && data[input.name]?.values) {
                const expectedValues = input.value.values as DataOption[];
                const actualValues = data[input.name].values as DataOption[];

                const matches =
                    Array.isArray(expectedValues) &&
                    Array.isArray(actualValues) &&
                    expectedValues?.length === actualValues?.length &&
                    expectedValues.every((value, index) => {
                        return value.src === actualValues[index]?.src && value.id === actualValues[index].id;
                    });

                if (!matches) {
                    notMatching.push(input.name as string);
                }
            } else if (type === "select") {
                const expectedValues = (Array.isArray(input.value) ? input.value : [input.value]) as (
                    | string
                    | number
                )[];
                const actualValues = (Array.isArray(data[input.name]) ? data[input.name] : [data[input.name]]) as (
                    | string
                    | number
                )[];

                const matches =
                    expectedValues.length === actualValues.length &&
                    expectedValues.every((value, index) => {
                        return value === actualValues[index];
                    });

                if (!matches) {
                    notMatching.push(input.name as string);
                }
            } else if (
                !["drill_down", "group_tag", "ftpfile", "upload", "rules", "tags"].includes(type) &&
                input.value !== data[input.name]
            ) {
                notMatching.push(input.name as string);
            }
        }
    }
    return notMatching;
});

const isValidRerun = computed(
    () => Boolean(props.isRerun) && checkInputMatching.value && stepsNotMatchingRequest.value.length === 0,
);

const hasValidationErrors = computed(() => stepValidation.value !== null);

const canRunOnHistory = computed(() => props.canMutateCurrentHistory || sendToNewHistory.value);

function onValidation(validation: [string, string] | null) {
    if (validation && validation.length == 2) {
        stepValidation.value = [validation[0], validation[1]];
    } else {
        stepValidation.value = null;
    }
}

function onChange(data: any) {
    formData.value = data;
}

function onStorageUpdate(objectStoreId: string, intermediate: boolean) {
    if (intermediate) {
        preferredIntermediateObjectStoreId.value = objectStoreId;
    } else {
        preferredObjectStoreId.value = objectStoreId;
    }
}

function updateActiveNodeId(nodeId: number | null) {
    activeNodeId.value = nodeId;
}

async function onExecute() {
    waitingForRequest.value = true;

    const replacementParams: Record<string, any> = {};
    const inputs: Record<string, any> = {};
    for (const inputName in formData.value) {
        const value = formData.value[inputName];
        const inputType = inputTypes.value[inputName];
        if (inputType == "replacement_parameter") {
            replacementParams[inputName] = value;
        } else if (inputType && isWorkflowInput(inputType)) {
            inputs[inputName] = value;
        }
    }
    const data: Record<string, any> = {
        replacement_dict: replacementParams,
        inputs: inputs,
        inputs_by: "step_index",
        batch: true,
        use_cached_job: useCachedJobs.value,
        require_exact_tool_versions: false,
        version: props.model.runData.version,
    };
    if (props.landingUuid) {
        data.landing_uuid = props.landingUuid;
    }
    if (sendToNewHistory.value) {
        data.new_history_name = props.model.name;
    } else {
        data.history_id = props.model.historyId;
    }
    if (splitObjectStore.value) {
        if (preferredObjectStoreId.value != null) {
            data.preferred_outputs_object_store_id = preferredObjectStoreId.value;
        }
        if (preferredIntermediateObjectStoreId.value != null && splitObjectStore.value) {
            data.preferred_intermediate_object_store_id = preferredIntermediateObjectStoreId.value;
        }
    } else {
        if (preferredObjectStoreId.value != null) {
            data.preferred_object_store_id = preferredObjectStoreId.value;
        }
    }

    try {
        const invocations = await invokeWorkflow(props.model.workflowId, data);
        emit("submissionSuccess", invocations);
    } catch (error) {
        emit("submissionError", errorMessageAsString(error));
    } finally {
        waitingForRequest.value = false;
    }
}

type ToolsCredentialInfo = {
    id: string;
    name: string;
    label: string;
    version: string;
    credentialsDefinition: ServiceCredentialsDefinition[];
};

const credentialTools = computed<ToolsCredentialInfo[]>(() => {
    return props.model.steps
        .filter((step: any) => step.step_type === "tool" && step.credentials?.length)
        .map((step: any) => ({
            id: step.id,
            name: step.name,
            label: step.label,
            version: step.version,
            credentialsDefinition: step.credentials,
        }));
});
</script>

<template>
    <div class="d-flex flex-column h-100 workflow-run-form-simple" data-galaxy-file-drop-target>
        <div v-if="!showRightPanel" class="ui-form-header-underlay sticky-top" />
        <div v-if="isConfigLoaded" :class="{ 'sticky-top': !showRightPanel }">
            <BAlert v-if="!canRunOnHistory" variant="warning" show>
                <span v-localize>
                    The workflow cannot run because the current history is immutable. Please select a different history
                    or send the results to a new one using the run settings ⚙️
                </span>
            </BAlert>
            <div class="mb-2">
                <WorkflowNavigationTitle
                    :workflow-id="model.runData.workflow_id"
                    :run-disabled="hasValidationErrors || !canRunOnHistory"
                    :run-waiting="waitingForRequest"
                    :valid-rerun="isValidRerun"
                    @on-execute="onExecute">
                    <template v-slot:workflow-title-actions>
                        <GButtonGroup>
                            <GButton
                                tooltip
                                size="small"
                                :title="!showGraph ? 'Show workflow graph' : 'Hide workflow graph'"
                                transparent
                                color="blue"
                                :pressed="showGraph"
                                @click="showRightPanel = showGraph ? null : 'graph'">
                                <FontAwesomeIcon :icon="faSitemap" fixed-width />
                            </GButton>
                            <GButton
                                v-if="workflow?.readme || workflow?.help"
                                tooltip
                                size="small"
                                :title="!showHelp ? 'Show workflow help' : 'Hide workflow help'"
                                transparent
                                color="blue"
                                :pressed="showHelp"
                                @click="showRightPanel = showHelp ? null : 'help'">
                                <FontAwesomeIcon :icon="faReadme" fixed-width />
                            </GButton>
                        </GButtonGroup>
                        <GButton
                            tooltip
                            size="small"
                            title="Workflow Run Settings"
                            transparent
                            color="blue"
                            class="workflow-run-settings"
                            :pressed="showRuntimeSettingsPanel"
                            @click="toggleRuntimeSettings">
                            <FontAwesomeIcon :icon="faCog" fixed-width />
                        </GButton>
                    </template>
                </WorkflowNavigationTitle>

                <!-- Runtime Settings Panel -->
                <div v-if="showRuntimeSettingsPanel" class="workflow-runtime-settings-panel p-2 rounded-bottom">
                    <div class="d-flex flex-wrap align-items-center">
                        <div class="mr-4">
                            <BFormCheckbox v-model="sendToNewHistory" class="workflow-run-settings-target">
                                <HelpText
                                    uri="galaxy.workflows.runtimeSettings.sendToNewHistory"
                                    text="Send results to a new history" />
                            </BFormCheckbox>
                        </div>
                        <div class="mr-4">
                            <BFormCheckbox
                                v-model="useCachedJobs"
                                title="This may skip executing jobs that you have already run.">
                                <HelpText
                                    uri="galaxy.workflows.runtimeSettings.useCachedJobs"
                                    text="Attempt to re-use jobs with identical parameters?" />
                            </BFormCheckbox>
                        </div>

                        <template v-if="isConfigLoaded && config.object_store_allows_id_selection">
                            <div class="mr-4">
                                <BFormCheckbox v-model="splitObjectStore">
                                    <HelpText
                                        uri="galaxy.workflows.runtimeSettings.splitObjectStore"
                                        text="Send outputs and intermediate to different Galaxy storage?" />
                                </BFormCheckbox>
                            </div>
                            <div class="mr-4">
                                <WorkflowStorageConfiguration
                                    :split-object-store="splitObjectStore"
                                    :invocation-preferred-object-store-id="preferredObjectStoreId ?? undefined"
                                    :invocation-intermediate-preferred-object-store-id="
                                        preferredIntermediateObjectStoreId
                                    "
                                    @updated="onStorageUpdate">
                                </WorkflowStorageConfiguration>
                            </div>
                        </template>

                        <div class="mr-4">
                            <GButton
                                tooltip
                                transparent
                                color="blue"
                                size="small"
                                class="workflow-expand-form-link"
                                title="Switch to the legacy workflow form"
                                @click="$emit('showAdvanced')">
                                Expanded workflow form <FontAwesomeIcon :icon="faArrowRight" />
                            </GButton>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <WorkflowAnnotation
            :workflow-id="model.runData.workflow_id"
            :history-id="model.historyId"
            show-details
            :hide-hr="Boolean(showRightPanel)" />

        <WorkflowCredentialsManagement v-if="credentialTools.length" :tools="credentialTools" full />

        <div class="overflow-auto h-100">
            <div class="d-flex h-100">
                <div
                    :class="showRightPanel ? 'w-50 flex-grow-1' : 'w-100'"
                    :style="{ 'overflow-y': 'auto', 'overflow-x': 'hidden' }">
                    <div v-if="showRightPanel" class="ui-form-header-underlay sticky-top" />
                    <Heading v-if="showRightPanel" class="sticky-top" h2 separator bold size="sm"> Parameters </Heading>
                    <BOverlay :show="changingCurrentHistory" no-fade rounded="sm" opacity="0.5">
                        <template v-slot:overlay>
                            <LoadingSpan message="Changing your current history" />
                        </template>
                        <FormDisplay
                            :inputs="formInputs"
                            :allow-empty-value-on-required-input="true"
                            :sync-with-graph="showGraph"
                            :active-node-id="computedActiveNodeId"
                            workflow-run
                            :steps-not-matching-request="stepsNotMatchingRequest"
                            @onChange="onChange"
                            @onValidation="onValidation"
                            @stop-flagging="checkInputMatching = false"
                            @update:active-node-id="updateActiveNodeId" />
                    </BOverlay>
                </div>
                <div v-if="showRightPanel" class="h-100 w-50 d-flex flex-shrink-0">
                    <WorkflowRunGraph
                        v-if="isConfigLoaded && showGraph"
                        :workflow-id="model.workflowId"
                        :step-validation="stepValidation || undefined"
                        :stored-id="model.runData.workflow_id"
                        :version="model.runData.version"
                        :inputs="formData"
                        :form-inputs="formInputs" />
                    <div v-else-if="showHelp" class="d-flex flex-column">
                        <Heading class="sticky-top" h2 separator bold size="sm"> Help </Heading>
                        <WorkflowHelpDisplay :workflow="workflow" :loading="workflowLoading" />
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";

.workflow-runtime-settings-panel {
    background-color: $brand-light;
    border-left: 1px solid $gray-200;
    border-right: 1px solid $gray-200;
    border-bottom: 1px solid $gray-200;
    transition: all 0.2s ease-in-out;
    opacity: 1;
    transform-origin: top;
    animation: slideDown 0.2s ease-in-out;
}

@keyframes slideDown {
    from {
        opacity: 0;
        transform: scaleY(0);
        max-height: 0;
    }
    to {
        opacity: 1;
        transform: scaleY(1);
        max-height: 200px;
    }
}
</style>
