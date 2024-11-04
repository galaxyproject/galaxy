<template>
    <div>
        <div v-if="isConfigLoaded">
            <BAlert v-if="!canRunOnHistory" variant="warning" show>
                <span v-localize>
                    The workflow cannot run because the current history is immutable. Please select a different history
                    or send the results to a new one using the run settings ⚙️
                </span>
            </BAlert>
            <div class="ui-portlet-section">
                <div class="d-flex portlet-header">
                    <div class="flex-grow-1">
                        <div class="px-1">
                            <span class="fa fa-sitemap" />
                            <b class="mx-1">Workflow: {{ model.name }}</b>
                            <i>(version: {{ model.runData.version + 1 }})</i>
                        </div>
                    </div>
                    <div class="d-flex align-items-end flex-nowrap">
                        <b-dropdown
                            v-if="showRuntimeSettings(currentUser)"
                            id="dropdown-form"
                            ref="dropdown"
                            class="workflow-run-settings"
                            style="margin-right: 10px"
                            title="Workflow Run Settings"
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
                                    :invocation-intermediate-preferred-object-store-id="
                                        preferredIntermediateObjectStoreId
                                    "
                                    @updated="onStorageUpdate">
                                </WorkflowStorageConfiguration>
                            </b-dropdown-form>
                        </b-dropdown>
                        <!-- waitingForRequest:{{ waitingForRequest }}<br> -->
                        <!-- hasValidationErrors:{{ hasValidationErrors }}<br> -->
                        <!-- !canRunOnHistory:{{ !canRunOnHistory }}<br> -->
                        <ButtonSpinner
                            id="run-workflow"
                            :wait="waitingForRequest"
                            :disabled="hasValidationErrors || !canRunOnHistory"
                            title="Run Workflow"
                            @onClick="onExecute" />
                    </div>
                </div>
            </div>
        </div>
        



            <div class="ui-portlet-section w-100">
                <div
                    class="portlet-header cursor-pointer"
                    role="button"
                    :tabindex="0"
                    @keyup.enter="expandAnnotations = !expandAnnotations"
                    @click="expandAnnotations = !expandAnnotations">
                    <b class="portlet-operations portlet-title-text">
                        <span v-localize class="font-weight-bold">About This Workflow</span>
                    </b>
                    <span v-b-tooltip.hover.bottom title="Collapse/Expand" variant="link" size="sm" class="float-right">
                        <FontAwesomeIcon :icon="expandAnnotations ? 'fa fa-chevron-up' : 'fa fa-chevron-up'" fixed-width />
                    </span>
                </div>
                <div class="portlet-content" :style="expandAnnotations ? 'display: none;' : ''">
                    <!-- TODO confirm timezone consistency -->
                    <!-- <UtcDate :date="model.runData.annotation.update_time" mode="elapsed" /> -->
                    <!-- <UtcDate :date="invocation.update_time" mode="elapsed" /> -->
                    <WorkflowAnnotation 
                        v-if="true" 
                        :workflow-id="model.workflowId"
                        :update-time="model.runData.annotation.update_time"
                        :history-id="model.historyId"
                        :from-panel="false" 
                        :target-history="'current'" />
                    {{ model.runData.annotation.annotation }}
                    <br>
                    <StatelessTags
                        :value="workflowTags"
                        :disabled="true" />
                </div>
            </div>



        

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
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import ButtonSpinner from "components/Common/ButtonSpinner";
import FormDisplay from "components/Form/FormDisplay";
import { allowCachedJobs } from "components/Tool/utilities";
import { isWorkflowInput } from "components/Workflow/constants";
import { mapActions,storeToRefs  } from "pinia";
import { errorMessageAsString } from "utils/simple-error";
import Vue from "vue";

import { useConfig } from "@/composables/config";
import { useUserStore } from "@/stores/userStore";
import { useWorkflowStore } from "@/stores/workflowStore";

import { invokeWorkflow } from "./services";
import WorkflowStorageConfiguration from "./WorkflowStorageConfiguration";

import WorkflowAnnotation from "../../Workflow/WorkflowAnnotation.vue";
import StatelessTags from "@/components/TagsMultiselect/StatelessTags.vue";


export default {
    components: {
        ButtonSpinner,
        FormDisplay,
        WorkflowStorageConfiguration,
        FontAwesomeIcon,
        WorkflowAnnotation,
        StatelessTags,
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
            expandAnnotations: true,
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
        // workflowVersions() {
        //     return this.getStoredWorkflowByInstanceId(this.workflowID);
        // },
        workflowTags() {
            return this.model.runData.annotation.tags.map((t) => t.user_tname);
            //TODO remove after confirming new structure:
            // return {
            //     id: props.model.runData.id,
            //     name: props.model.runData.name,
            //     owner: props.model.runData.owner,
            //     tags: props.model.runData.annotation.tags.map((t: { user_tname: string }) => t.user_tname),
            //     annotations: [props.model.runData.annotation.annotation],
            //     update_time: props.model.runData.annotation.update_time,
            // };
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
        ...mapActions(useWorkflowStore, ["getStoredWorkflowByInstanceId", "fetchWorkflowForInstanceId"]),
    },
};
</script>
