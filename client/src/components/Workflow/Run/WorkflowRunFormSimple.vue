<script setup lang="ts">
import { faSitemap } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton, BFormCheckbox, BOverlay } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";

import { isWorkflowInput } from "@/components/Workflow/constants";
import { useConfig } from "@/composables/config";
import { usePanels } from "@/composables/usePanels";
import { provideScopedWorkflowStores } from "@/composables/workflowStores";
import { useHistoryStore } from "@/stores/historyStore";
import { errorMessageAsString } from "@/utils/simple-error";

import { invokeWorkflow } from "./services";

import WorkflowAnnotation from "../WorkflowAnnotation.vue";
import WorkflowNavigationTitle from "../WorkflowNavigationTitle.vue";
import WorkflowRunGraph from "./WorkflowRunGraph.vue";
import WorkflowStorageConfiguration from "./WorkflowStorageConfiguration.vue";
import Heading from "@/components/Common/Heading.vue";
import FormDisplay from "@/components/Form/FormDisplay.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface Props {
    model: Record<string, any>;
    targetHistory?: string;
    useJobCache?: boolean;
    canMutateCurrentHistory: boolean;
    requestState?: Record<string, any>;
}

const props = withDefaults(defineProps<Props>(), {
    targetHistory: "current",
    useJobCache: false,
    requestState: undefined,
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
const showGraph = ref(!showPanels.value);
const showRuntimeSettingsPanel = ref(false);

const { changingCurrentHistory } = storeToRefs(useHistoryStore());

watch(
    () => showGraph.value,
    (show) => {
        if (!show) {
            activeNodeId.value = null;
        }
    }
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
            const stepType = step.step_type;
            const help = step.annotation;
            const longFormInput = step.inputs[0];
            const stepAsInput = Object.assign({}, longFormInput, {
                name: stepName,
                help: help,
                label: stepLabel,
            });
            if (props.requestState && props.requestState[stepLabel]) {
                const value = props.requestState[stepLabel];
                stepAsInput.value = value;
            }
            // disable collection mapping...
            stepAsInput.flavor = "module";
            inputs.push(stepAsInput);
            inputTypes.value[stepName] = stepType;
        }
    });
    return inputs;
});

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

function toggleRuntimeSettings() {
    showRuntimeSettingsPanel.value = !showRuntimeSettingsPanel.value;
}
</script>

<template>
    <div class="d-flex flex-column h-100 workflow-run-form-simple">
        <div v-if="!showGraph" class="ui-form-header-underlay sticky-top" />
        <div v-if="isConfigLoaded" :class="{ 'sticky-top': !showGraph }">
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
                    @on-execute="onExecute">
                    <template v-slot:workflow-title-actions>
                        <BButton
                            v-b-tooltip.hover.noninteractive.html
                            size="sm"
                            :title="!showGraph ? 'Show workflow graph' : 'Hide workflow graph'"
                            variant="link"
                            :pressed="showGraph"
                            @click="showGraph = !showGraph">
                            <FontAwesomeIcon :icon="faSitemap" fixed-width />
                        </BButton>
                        <BButton
                            v-b-tooltip.hover.noninteractive
                            size="sm"
                            title="Workflow Run Settings"
                            variant="link"
                            :pressed="showRuntimeSettingsPanel"
                            @click="toggleRuntimeSettings">
                            <span class="fa fa-cog" />
                        </BButton>
                    </template>
                </WorkflowNavigationTitle>

                <!-- Runtime Settings Panel -->
                <div
                    v-if="showRuntimeSettingsPanel"
                    class="workflow-runtime-settings-panel px-2 pt-2">
                    <div class="d-flex flex-wrap">
                        <div class="mr-4 mb-2">
                            <BFormCheckbox v-model="sendToNewHistory" class="workflow-run-settings-target">
                                Send results to a new history
                            </BFormCheckbox>
                        </div>
                        <div class="mr-4 mb-2">
                            <BFormCheckbox
                                v-model="useCachedJobs"
                                title="This may skip executing jobs that you have already run.">
                                Attempt to re-use jobs with identical parameters?
                            </BFormCheckbox>
                        </div>
                        <div v-if="isConfigLoaded && config.object_store_allows_id_selection" class="mr-4 mb-2">
                            <BFormCheckbox v-model="splitObjectStore">
                                Send outputs and intermediate to different storage locations?
                            </BFormCheckbox>
                        </div>
                        <div class="mr-4 mb-2">
                            <BFormCheckbox class="workflow-expand-form-link" @change="emit('showAdvanced')">
                                Expand to full workflow form.
                            </BFormCheckbox>
                        </div>
                    </div>
                    <WorkflowStorageConfiguration
                        v-if="isConfigLoaded && config.object_store_allows_id_selection"
                        :split-object-store="splitObjectStore"
                        :invocation-preferred-object-store-id="preferredObjectStoreId ?? undefined"
                        :invocation-intermediate-preferred-object-store-id="preferredIntermediateObjectStoreId"
                        @updated="onStorageUpdate">
                    </WorkflowStorageConfiguration>
                </div>
            </div>
        </div>

        <WorkflowAnnotation :workflow-id="model.runData.workflow_id" :history-id="model.historyId" show-details />

        <div class="overflow-auto h-100">
            <div class="d-flex h-100">
                <div
                    :class="showGraph ? 'w-50 flex-grow-1' : 'w-100'"
                    :style="{ 'overflow-y': 'auto', 'overflow-x': 'hidden' }">
                    <div v-if="showGraph" class="ui-form-header-underlay sticky-top" />
                    <Heading v-if="showGraph" class="sticky-top" h2 separator bold size="sm"> Parameters </Heading>
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
                            @onChange="onChange"
                            @onValidation="onValidation"
                            @update:active-node-id="($event) => (activeNodeId = $event)" />
                    </BOverlay>
                </div>
                <div v-if="showGraph" class="h-100 w-50 d-flex flex-shrink-0">
                    <WorkflowRunGraph
                        v-if="isConfigLoaded"
                        :workflow-id="model.workflowId"
                        :step-validation="stepValidation || undefined"
                        :stored-id="model.runData.workflow_id"
                        :version="model.runData.version"
                        :inputs="formData"
                        :form-inputs="formInputs" />
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped lang="scss">
.workflow-runtime-settings-panel {
    background-color: #f8f9fa;
    border-left: 1px solid #dee2e6;
    border-right: 1px solid #dee2e6;
    border-bottom: 1px solid #dee2e6;
    border-radius: 0 0 0.25rem 0.25rem;
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
        max-height: 100px;
    }
}
</style>
