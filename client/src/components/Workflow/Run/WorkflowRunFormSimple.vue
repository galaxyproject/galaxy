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
                    <b-dropdown
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
                        <b-dropdown-form>
                            <b-form-checkbox v-model="sendToNewHistory" class="workflow-run-settings-target">
                                Send results to a new history
                            </b-form-checkbox>
                            <b-form-checkbox
                                v-if="reuseAllowed(currentUser)"
                                v-model="useCachedJobs"
                                title="This may skip executing jobs that you have already run.">
                                Attempt to re-use jobs with identical parameters?
                            </b-form-checkbox>
                            <b-form-checkbox
                                v-if="isConfigLoaded && config.object_store_allows_id_selection"
                                v-model="splitObjectStore">
                                Send outputs and intermediate to different storage locations?
                            </b-form-checkbox>
                            <WorkflowStorageConfiguration
                                v-if="isConfigLoaded && config.object_store_allows_id_selection"
                                :split-object-store="splitObjectStore"
                                :invocation-preferred-object-store-id="preferredObjectStoreId"
                                :invocation-intermediate-preferred-object-store-id="preferredIntermediateObjectStoreId"
                                @updated="onStorageUpdate">
                            </WorkflowStorageConfiguration>
                        </b-dropdown-form>
                    </b-dropdown>
                </template>
            </WorkflowNavigationTitle>
        </div>

        <WorkflowAnnotation :workflow-id="model.runData.workflow_id" :history-id="model.historyId" show-details />
        <FormDisplay
            :inputs="formInputs"
            :allow-empty-value-on-required-input="true"
            @onChange="onChange"
            @onValidation="onValidation" />
        <!-- Options to default one way or the other, disable if admins want, etc.. -->
        <a href="#" class="workflow-expand-form-link" @click="$emit('showAdvanced')">Expand to full workflow form.</a>
    </div>
</template>

<script>
import FormDisplay from "components/Form/FormDisplay";
import { allowCachedJobs } from "components/Tool/utilities";
import { isWorkflowInput } from "components/Workflow/constants";
import { storeToRefs } from "pinia";
import { errorMessageAsString } from "utils/simple-error";
import Vue from "vue";

import { useConfig } from "@/composables/config";
import { useUserStore } from "@/stores/userStore";

import { invokeWorkflow } from "./services";
import WorkflowStorageConfiguration from "./WorkflowStorageConfiguration";

import WorkflowAnnotation from "../../Workflow/WorkflowAnnotation.vue";
import WorkflowNavigationTitle from "../WorkflowNavigationTitle.vue";

export default {
    components: {
        FormDisplay,
        WorkflowAnnotation,
        WorkflowNavigationTitle,
        WorkflowStorageConfiguration,
    },
    props: {
        model: {
            type: Object,
            required: true,
        },
        targetHistory: {
            type: String,
            default: "current",
        },
        useJobCache: {
            type: Boolean,
            default: false,
        },
        canMutateCurrentHistory: {
            type: Boolean,
            required: true,
        },
        requestState: {
            type: Object,
            required: false,
        },
    },
    setup() {
        const { config, isConfigLoaded } = useConfig(true);
        const { currentUser } = storeToRefs(useUserStore());
        return { config, isConfigLoaded, currentUser };
    },
    data() {
        const newHistory = this.targetHistory == "new" || this.targetHistory == "prefer_new";
        return {
            formData: {},
            inputTypes: {},
            stepValidations: {},
            sendToNewHistory: newHistory,
            useCachedJobs: this.useJobCache, // TODO:
            splitObjectStore: false,
            preferredObjectStoreId: null,
            preferredIntermediateObjectStoreId: null,
            waitingForRequest: false,
        };
    },
    computed: {
        formInputs() {
            const inputs = [];
            // Add workflow parameters.
            Object.values(this.model.wpInputs).forEach((input) => {
                const inputCopy = Object.assign({}, input);
                // do we want to keep the color if we're not showing steps?
                inputCopy.color = undefined;
                inputs.push(inputCopy);
                this.inputTypes[inputCopy.name] = "replacement_parameter";
            });
            // Add actual input modules.
            this.model.steps.forEach((step, i) => {
                if (isWorkflowInput(step.step_type)) {
                    const stepName = new String(step.step_index);
                    const stepLabel = step.step_label || new String(step.step_index + 1);
                    const stepType = step.step_type;
                    const help = step.annotation;
                    const longFormInput = step.inputs[0];
                    const stepAsInput = Object.assign({}, longFormInput, {
                        name: stepName,
                        help: help,
                        label: stepLabel,
                    });
                    if (this.requestState && this.requestState[stepLabel]) {
                        const value = this.requestState[stepLabel];
                        stepAsInput.value = value;
                    }
                    // disable collection mapping...
                    stepAsInput.flavor = "module";
                    inputs.push(stepAsInput);
                    this.inputTypes[stepName] = stepType;
                }
            });
            return inputs;
        },
        hasValidationErrors() {
            return Boolean(Object.values(this.stepValidations).find((value) => value !== null && value !== undefined));
        },
        canRunOnHistory() {
            return this.canMutateCurrentHistory || this.sendToNewHistory;
        },
    },
    methods: {
        onValidation(validation) {
            if (validation) {
                Vue.set(this.stepValidations, validation[0], validation[1]);
            } else {
                this.stepValidations = {};
            }
        },
        reuseAllowed(user) {
            return user && allowCachedJobs(user.preferences);
        },
        showRuntimeSettings(user) {
            return this.targetHistory.indexOf("prefer") >= 0 || (user && this.reuseAllowed(user));
        },
        onChange(data) {
            this.formData = data;
        },
        onStorageUpdate: function (objectStoreId, intermediate) {
            if (intermediate) {
                this.preferredIntermediateObjectStoreId = objectStoreId;
            } else {
                this.preferredObjectStoreId = objectStoreId;
            }
        },
        onExecute() {
            const replacementParams = {};
            const inputs = {};
            for (const inputName in this.formData) {
                const value = this.formData[inputName];
                const inputType = this.inputTypes[inputName];
                if (inputType == "replacement_parameter") {
                    replacementParams[inputName] = value;
                } else if (isWorkflowInput(inputType)) {
                    inputs[inputName] = value;
                }
            }
            const data = {
                replacement_dict: replacementParams,
                inputs: inputs,
                inputs_by: "step_index",
                batch: true,
                use_cached_job: this.useCachedJobs,
                require_exact_tool_versions: false,
                version: this.model.runData.version,
            };
            if (this.sendToNewHistory) {
                data.new_history_name = this.model.name;
            } else {
                data.history_id = this.model.historyId;
            }
            if (this.splitObjectStore) {
                if (this.preferredObjectStoreId != null) {
                    data.preferred_outputs_object_store_id = this.preferredObjectStoreId;
                }
                if (this.preferredIntermediateObjectStoreId != null && this.splitObjectStore) {
                    data.preferred_intermediate_object_store_id = this.preferredIntermediateObjectStoreId;
                }
            } else {
                if (this.preferredObjectStoreId != null) {
                    data.preferred_object_store_id = this.preferredObjectStoreId;
                }
            }
            this.waitingForRequest = true;
            invokeWorkflow(this.model.workflowId, data)
                .then((invocations) => {
                    this.$emit("submissionSuccess", invocations);
                })
                .catch((error) => {
                    this.$emit("submissionError", errorMessageAsString(error));
                })
                .finally(() => (this.waitingForRequest = false));
        },
    },
};
</script>
