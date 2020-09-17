<template>
    <div ref="form"></div>
</template>

<script>
import Form from "mvc/form/form-view";
import { invokeWorkflow } from "./services";
import { isWorkflowInput } from "components/Workflow/constants";

export default {
    props: {
        model: {
            type: Object,
            required: true,
        },
        setRunButtonStatus: {
            type: Function,
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
        return {
            form: null,
            inputTypes: {},
        };
    },
    computed: {},
    created() {
        this.form = new Form(this.formDefinition());
        this.$nextTick(() => {
            const el = this.$refs["form"];
            el.appendChild(this.form.$el[0]);
        });
    },
    methods: {
        formDefinition() {
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

            const def = {
                inputs: inputs,
            };
            return def;
        },
        execute() {
            const replacementParams = {};
            const inputs = {};
            const formData = this.form.data.create();
            for (const inputName in formData) {
                const value = formData[inputName];
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
                use_cached_job: this.useJobCache,
            };
            if (this.targetHistory == "current") {
                data.history_id = this.model.historyId;
            } else {
                data.new_history_name = this.model.name;
            }
            invokeWorkflow(this.model.workflowId, data)
                .then((invocations) => {
                    this.$emit("submissionSuccess", invocations);
                })
                .catch((error) => {
                    console.log(error);
                });
        },
    },
};
</script>
