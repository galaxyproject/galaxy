<template>
    <CurrentUser v-slot="{ user }">
        <div>
            <div class="h4 clearfix mb-3">
                <b>Workflow: {{ model.name }}</b>
                <ButtonSpinner id="run-workflow" class="float-right" title="Run Workflow" @onClick="onExecute" />
                <b-dropdown
                    v-if="showRuntimeSettings(user)"
                    id="dropdown-form"
                    ref="dropdown"
                    class="workflow-run-settings float-right"
                    style="margin-right: 10px"
                    title="Workflow Run Settings"
                    no-caret>
                    <template v-slot:button-content>
                        <span class="fa fa-cog" />
                    </template>
                    <b-dropdown-form>
                        <b-form-checkbox v-model="sendToNewHistory" class="workflow-run-settings-target"
                            >Send results to a new history</b-form-checkbox
                        >
                        <b-form-checkbox
                            v-if="reuseAllowed(user)"
                            v-model="useCachedJobs"
                            title="This may skip executing jobs that you have already run."
                            >Attempt to re-use jobs with identical parameters?</b-form-checkbox
                        >
                    </b-dropdown-form>
                </b-dropdown>
            </div>
            <FormDisplay :inputs="formInputs" @onChange="onChange" />
            <!-- Options to default one way or the other, disable if admins want, etc.. -->
            <a href="#" class="workflow-expand-form-link" @click="$emit('showAdvanced')"
                >Expand to full workflow form.</a
            >
        </div>
    </CurrentUser>
</template>

<script>
import CurrentUser from "components/providers/CurrentUser";
import FormDisplay from "components/Form/FormDisplay";
import ButtonSpinner from "components/Common/ButtonSpinner";
import { invokeWorkflow } from "./services";
import { isWorkflowInput } from "components/Workflow/constants";
import { errorMessageAsString } from "utils/simple-error";
import { allowCachedJobs } from "components/Tool/utilities";

export default {
    components: {
        ButtonSpinner,
        CurrentUser,
        FormDisplay,
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
    },
    data() {
        const newHistory = this.targetHistory == "new" || this.targetHistory == "prefer_new";
        return {
            formData: {},
            inputTypes: {},
            sendToNewHistory: newHistory,
            useCachedJobs: this.useJobCache, // TODO:
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
                if (!isWorkflowInput(step.step_type)) {
                    return;
                }
                const stepName = new String(step.step_index);
                const stepLabel = step.step_label || new String(step.step_index + 1);
                const help = step.annotation;
                const longFormInput = step.inputs[0];
                const stepAsInput = Object.assign({}, longFormInput, { name: stepName, help: help, label: stepLabel });
                // disable collection mapping...
                stepAsInput.flavor = "module";
                inputs.push(stepAsInput);
                this.inputTypes[stepName] = step.step_type;
            });
            return inputs;
        },
    },
    methods: {
        reuseAllowed(user) {
            return allowCachedJobs(user.preferences);
        },
        showRuntimeSettings(user) {
            return this.targetHistory.indexOf("prefer") >= 0 || this.reuseAllowed(user);
        },
        onChange(data) {
            this.formData = data;
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
            };
            if (this.sendToNewHistory) {
                data.new_history_name = this.model.name;
            } else {
                data.history_id = this.model.historyId;
            }
            invokeWorkflow(this.model.workflowId, data)
                .then((invocations) => {
                    this.$emit("submissionSuccess", invocations);
                })
                .catch((error) => {
                    this.$emit("submissionError", errorMessageAsString(error));
                });
        },
    },
};
</script>

<style scoped>
.workflow-settings-botton {
    margin-right: 10px;
}
</style>
