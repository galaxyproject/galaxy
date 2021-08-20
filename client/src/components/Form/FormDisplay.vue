<template>
    <div ref="form" />
</template>

<script>
import _ from "underscore";
import Form from "mvc/form/form-view";
import { visitInputs } from "components/Form/utilities";

export default {
    props: {
        id: {
            type: String,
            default: null,
        },
        inputs: {
            type: Array,
            required: true,
        },
        sustainRepeats: {
            type: Boolean,
            default: false,
        },
        sustainConditionals: {
            type: Boolean,
            default: false,
        },
        hideOperations: {
            type: Boolean,
            default: false,
        },
        textEnable: {
            type: String,
            default: null,
        },
        textDisable: {
            type: String,
            default: null,
        },
        initialErrors: {
            type: Boolean,
            default: false,
        },
        validationScrollTo: {
            type: Array,
            default: null,
        },
        formConfig: {
            type: Object,
            default: null,
        },
        replaceParams: {
            type: Object,
            default: null,
        },
    },
    data() {
        return {
            formData: {},
        };
    },
    watch: {
        id() {
            this.onRender();
        },
        validationScrollTo() {
            this.onHighlight(this.validationScrollTo);
        },
        validation() {
            this.onHighlight(this.validation, true);
            this.$emit("onValidation", this.validation);
        },
        formConfig() {
            this.$nextTick(() => {
                this.form.update(this.formConfig);
                if (this.initialErrors) {
                    this.form.errors(this.formConfig);
                }
            });
        },
        replaceParams() {
            this.onReplaceParams();
        },
    },
    mounted() {
        this.onRender();
    },
    beforeDestroy() {
        this.form.off();
    },
    computed: {
        validation() {
            let batch_n = -1;
            let batch_src = null;
            for (const job_input_id in this.formData) {
                const input_value = this.formData[job_input_id];
                const input_id = this.form.data.match(job_input_id);
                const input_field = this.form.field_list[input_id];
                const input_def = this.form.input_list[input_id];
                if (!input_id || !input_def || !input_field || input_def.step_linked) {
                    continue;
                }
                if (
                    input_value &&
                    Array.isArray(input_value.values) &&
                    input_value.values.length == 0 &&
                    !input_def.optional
                ) {
                    return [job_input_id, "Please provide data for this input."];
                }
                if (input_value == null && !input_def.optional && input_def.type != "hidden") {
                    return [job_input_id, "Please provide a value for this option."];
                }
                if (input_def.wp_linked && input_def.text_value == input_value) {
                    return [job_input_id, "Please provide a value for this workflow parameter."];
                }
                if (input_field.validate) {
                    const message = input_field.validate();
                    if (message) {
                        return [job_input_id, message];
                    }
                }
                if (input_value && input_value.batch) {
                    const n = input_value.values.length;
                    const src = n > 0 && input_value.values[0] && input_value.values[0].src;
                    if (src) {
                        if (batch_src === null) {
                            batch_src = src;
                        } else if (batch_src !== src) {
                            return [
                                job_input_id,
                                "Please select either dataset or dataset list fields for all batch mode fields.",
                            ];
                        }
                    }
                    if (batch_n === -1) {
                        batch_n = n;
                    } else if (batch_n !== n) {
                        return [
                            job_input_id,
                            `Please make sure that you select the same number of inputs for all batch mode fields. This field contains <b>${n}</b> selection(s) while a previous field contains <b>${batch_n}</b>.`,
                        ];
                    }
                }
            }
            return null;
        },
    },
    methods: {
        onReplaceParams() {
            if (this.replaceParams) {
                this.params = {};
                visitInputs(this.inputs, (input, name) => {
                    this.params[name] = input;
                });
                _.each(this.params, (input, name) => {
                    const newValue = this.replaceParams[name];
                    if (newValue) {
                        const field = this.form.field_list[this.form.data.match(name)];
                        field.value(newValue);
                    }
                });
                this.form.trigger("change");
            }
        },
        onChange() {
            this.formData = this.form.data.create();
            this.$emit("onChange", this.formData);
        },
        onRender() {
            this.$nextTick(() => {
                const el = this.$refs["form"];
                this.form = new Form({
                    el,
                    inputs: this.inputs,
                    initial_errors: this.initialErrors,
                    text_enable: this.textEnable,
                    text_disable: this.textDisable,
                    sustain_repeats: this.sustainRepeats,
                    sustain_conditionals: this.sustainConditionals,
                    onchange: () => {
                        this.onChange();
                    },
                });
                this.onChange();
            });
        },
        onHighlight(validation, silent = false) {
            this.form.trigger("reset");
            if (validation && validation.length == 2) {
                const input_id = this.form.data.match(validation[0]);
                this.form.highlight(input_id, validation[1], silent);
            }
        },
    },
};
</script>
