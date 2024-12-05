<script setup lang="ts">
import { BAlert, BDropdown, BDropdownForm, BFormCheckbox } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref, set } from "vue";

import { allowCachedJobs } from "@/components/Tool/utilities";
import { isWorkflowInput } from "@/components/Workflow/constants";
import { useConfig } from "@/composables/config";
import { provideScopedWorkflowStores } from "@/composables/workflowStores";
import { useUserStore } from "@/stores/userStore";
import { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";
import { errorMessageAsString } from "@/utils/simple-error";

import { invokeWorkflow } from "./services";

import WorkflowAnnotation from "../WorkflowAnnotation.vue";
import WorkflowNavigationTitle from "../WorkflowNavigationTitle.vue";
import WorkflowRunInfo from "./WorkflowRunInfo.vue";
import WorkflowStorageConfiguration from "./WorkflowStorageConfiguration.vue";
import FormDisplay from "@/components/Form/FormDisplay.vue";
import FlexPanel from "@/components/Panels/FlexPanel.vue";

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

provideScopedWorkflowStores(props.model.workflowId);

const { activeNodeId } = storeToRefs(useWorkflowStateStore(props.model.workflowId));

const { config, isConfigLoaded } = useConfig(true);
const { currentUser } = storeToRefs(useUserStore());

const formData = ref<Record<string, any>>({});
const inputTypes = ref<Record<string, string>>({});
const stepValidations = ref<Record<string, string | null>>({});
const sendToNewHistory = ref(props.targetHistory === "new" || props.targetHistory === "prefer_new");
const useCachedJobs = ref(props.useJobCache);
const splitObjectStore = ref(false);
const preferredObjectStoreId = ref<string | null>(null);
const preferredIntermediateObjectStoreId = ref<string | null>(null);
const waitingForRequest = ref(false);

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

const hasValidationErrors = computed(() => {
    return Boolean(Object.values(stepValidations.value).find((value) => value !== null && value !== undefined));
});

const canRunOnHistory = computed(() => props.canMutateCurrentHistory || sendToNewHistory.value);

function onValidation(validation: any) {
    if (validation) {
        set(stepValidations.value, validation[0], validation[1]);
    } else {
        stepValidations.value = {};
    }
}

function reuseAllowed(user: any) {
    return user && allowCachedJobs(user.preferences);
}

function showRuntimeSettings(user: any) {
    return props.targetHistory && (props.targetHistory.indexOf("prefer") >= 0 || (user && reuseAllowed(user)));
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
</script>

<template>
    <div>
        <div class="ui-form-header-underlay sticky-top" />
        <div v-if="isConfigLoaded" class="sticky-top">
            <BAlert v-if="!canRunOnHistory" variant="warning" show>
                <span v-localize>
                    The workflow cannot run because the current history is immutable. Please select a different history
                    or send the results to a new one using the run settings ⚙️
                </span>
            </BAlert>
            <WorkflowNavigationTitle
                :workflow-id="model.runData.workflow_id"
                :run-disabled="hasValidationErrors || !canRunOnHistory"
                :run-waiting="waitingForRequest"
                @on-execute="onExecute">
                <template v-slot:workflow-title-actions>
                    <BDropdown
                        v-if="showRuntimeSettings(currentUser)"
                        id="dropdown-form"
                        ref="dropdown"
                        class="workflow-run-settings"
                        title="Workflow Run Settings"
                        size="sm"
                        variant="link"
                        no-caret>
                        <template v-slot:button-content>
                            <span class="fa fa-cog" />
                        </template>
                        <BDropdownForm>
                            <BFormCheckbox v-model="sendToNewHistory" class="workflow-run-settings-target">
                                Send results to a new history
                            </BFormCheckbox>
                            <BFormCheckbox
                                v-if="reuseAllowed(currentUser)"
                                v-model="useCachedJobs"
                                title="This may skip executing jobs that you have already run.">
                                Attempt to re-use jobs with identical parameters?
                            </BFormCheckbox>
                            <BFormCheckbox
                                v-if="isConfigLoaded && config.object_store_allows_id_selection"
                                v-model="splitObjectStore">
                                Send outputs and intermediate to different storage locations?
                            </BFormCheckbox>
                            <WorkflowStorageConfiguration
                                v-if="isConfigLoaded && config.object_store_allows_id_selection"
                                :split-object-store="splitObjectStore"
                                :invocation-preferred-object-store-id="preferredObjectStoreId"
                                :invocation-intermediate-preferred-object-store-id="preferredIntermediateObjectStoreId"
                                @updated="onStorageUpdate">
                            </WorkflowStorageConfiguration>
                        </BDropdownForm>
                    </BDropdown>
                </template>
            </WorkflowNavigationTitle>
        </div>

        <WorkflowAnnotation :workflow-id="model.runData.workflow_id" :history-id="model.historyId" show-details />

        <div ref="runFormContainer" class="d-flex">
            <div class="w-100 overflow-auto">
                <FormDisplay
                    :inputs="formInputs"
                    :allow-empty-value-on-required-input="true"
                    :active-node-id.sync="activeNodeId"
                    @onChange="onChange"
                    @onValidation="onValidation" />
                <!-- Options to default one way or the other, disable if admins want, etc.. -->
                <a href="#" class="workflow-expand-form-link" @click="emit('showAdvanced')">
                    Expand to full workflow form.
                </a>
            </div>
            <FlexPanel side="right">
                <WorkflowRunInfo
                    v-if="isConfigLoaded"
                    :workflow-id="model.workflowId"
                    :stored-id="model.runData.workflow_id"
                    :version="model.runData.version" />
            </FlexPanel>
        </div>
    </div>
</template>
