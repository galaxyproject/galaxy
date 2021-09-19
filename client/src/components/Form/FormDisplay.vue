<template>
    <FormInputs
        :id="id"
        :inputs="inputs"
        :prefix="prefix"
        :sustain-repeats="sustainRepeats"
        :sustain-conditionals="sustainConditionals"
        :text-enable="textEnable"
        :text-disable="textDisable"
        :validation-scroll-to="validationScrollTo"
        :replace-params="replaceParams"
        :errors="errors"
        :add-parameters="addParameters"
        :remove-parameters="removeParameters"
        :update-parameters="updateParameters"
    />
</template>

<script>
import FormInputs from "./FormInputs";

export default {
    components: {
        FormInputs,
    },
    props: {
        id: {
            type: String,
            default: null,
        },
        inputs: {
            type: Array,
            required: true,
        },
        errors: {
            type: Object,
            default: null,
        },
        prefix: {
            type: String,
            default: "",
        },
        sustainRepeats: {
            type: Boolean,
            default: false,
        },
        sustainConditionals: {
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
        validationScrollTo: {
            type: Array,
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
        validationScrollTo() {
            //this.onHighlight(this.validationScrollTo);
        },
        validation() {
            //this.onHighlight(this.validation, true);
            //this.$emit("onValidation", this.validation);
        },
        errors() {
            /*this.$nextTick(() => {
                this.form.errors(this.errors);
            });*/
        },
        replaceParams() {
            this.onReplaceParams();
        },
    },
    computed: {
        validation() {
            /*let batch_n = -1;
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
            }*/
            return null;
        },
    },
    methods: {
        onReplaceParams() {
            Object.keys(this.formData).forEach((key) => {
                const newValue = this.replaceParams[key];
                if (newValue != undefined) {
                    this.formData[key] = newValue;
                }
            });
            this.updateParameters();
        },
        addParameters(value, identifier, requiresRequest) {
            const currentValueString = JSON.stringify(this.formData[identifier]);
            if (currentValueString != JSON.stringify(value)) {
                this.formData[identifier] = value;
                this.updateParameters(requiresRequest);
            }
        },
        removeParameters(prefix, cacheId) {
            const filtered = {};
            Object.keys(this.formData).forEach((key) => {
                let currentKey = key;
                if (cacheId != undefined) {
                    const regstr = `^${prefix}_(\\d+)\\|(\\S+)$`;
                    const regex = new RegExp(regstr);
                    const match = regex.exec(key);
                    if (match) {
                        const groupId = parseInt(match[1]);
                        if (groupId == cacheId) {
                            currentKey = undefined;
                        } else if (groupId > cacheId) {
                            currentKey = `${prefix}_${groupId - 1}|${match[2]}`;
                        }
                    }
                } else if (key.startsWith(`${prefix}|`)) {
                    currentKey = undefined;
                }
                if (currentKey !== undefined) {
                    filtered[currentKey] = this.formData[key];
                }
            });
            this.formData = filtered;
            console.log(filtered);
            if (cacheId != undefined) {
                //this.updateParameters();
            }
        },
        updateParameters(requiresRequest = true) {
            this.$nextTick(() => {
                const formDataCopy = Object.assign({}, this.formData);
                this.$emit("onChange", formDataCopy, requiresRequest);
                console.log(this.formData, requiresRequest);
            });
        },
        onHighlight(validation, silent = false) {
            /*this.form.trigger("reset");
            if (validation && validation.length == 2) {
                const input_id = this.form.data.match(validation[0]);
                this.form.highlight(input_id, validation[1], silent);
            }*/
        },
    },
};
</script>
