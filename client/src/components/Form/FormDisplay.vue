<template>
    <FormInputs
        :key="id"
        :inputs="formInputs"
        :prefix="prefix"
        :sustain-repeats="sustainRepeats"
        :sustain-conditionals="sustainConditionals"
        :collapsed-enable-text="collapsedEnableText"
        :collapsed-enable-icon="collapsedEnableIcon"
        :collapsed-disable-text="collapsedDisableText"
        :collapsed-disable-icon="collapsedDisableIcon"
        :replace-params="replaceParams"
        :errors="errors"
        :on-change="onChange"
        :on-change-form="onChangeForm"
    />
</template>

<script>
import FormInputs from "./FormInputs";
import { visitInputs, matchErrors } from "./utilities";
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
        collapsedEnableText: {
            type: String,
            default: "Enable",
        },
        collapsedDisableText: {
            type: String,
            default: "Disable",
        },
        collapsedEnableIcon: {
            type: String,
            default: "fa fa-caret-square-o-down",
        },
        collapsedDisableIcon: {
            type: String,
            default: "fa fa-caret-square-o-up",
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
    created() {
        this.onCloneInputs();
    },
    data() {
        return {
            formData: {},
            formIndex: {},
            formInputs: [],
        };
    },
    watch: {
        id() {
            this.onCloneInputs();
        },
        inputs() {
            const newAttributes = {};
            visitInputs(this.inputs, (input, name) => {
                newAttributes[name] = input;
            });
            visitInputs(this.formInputs, (input, name) => {
                const newValue = newAttributes[name];
                if (newValue != undefined) {
                    input.attributes = newValue;
                }
            });
            this.onChangeForm();
        },
        validationScrollTo() {
            this.onHighlight(this.validationScrollTo);
        },
        validation() {
            this.onHighlight(this.validation, true);
            this.$emit("onValidation", this.validation);
        },
        errors() {
            this.resetError();
            if (this.errors) {
                const errorMessages = matchErrors(this.errors, this.formIndex);
                for (const inputId in errorMessages) {
                    this.setError(inputId, errorMessages[inputId]);
                }
            }
        },
        replaceParams() {
            this.onReplaceParams();
        },
    },
    computed: {
        validation() {
            let batchN = -1;
            let batchSrc = null;
            for (const inputId in this.formData) {
                const inputValue = this.formData[inputId];
                const inputDef = this.formIndex[inputId];
                if (!inputDef || inputDef.step_linked) {
                    continue;
                }
                if (
                    inputValue &&
                    Array.isArray(inputValue.values) &&
                    inputValue.values.length == 0 &&
                    !inputDef.optional
                ) {
                    return [inputId, "Please provide data for this input."];
                }
                if (inputValue == null && !inputDef.optional && inputDef.type != "hidden") {
                    return [inputId, "Please provide a value for this option."];
                }
                if (inputDef.wp_linked && inputDef.text_value == inputValue) {
                    return [inputId, "Please provide a value for this workflow parameter."];
                }
                /*if (input_field.validate) {
                    const message = input_field.validate();
                    if (message) {
                        return [inputId, message];
                    }
                }*/
                if (inputValue && inputValue.batch) {
                    const n = inputValue.values.length;
                    const src = n > 0 && inputValue.values[0] && inputValue.values[0].src;
                    if (src) {
                        if (batchSrc === null) {
                            batchSrc = src;
                        } else if (batchSrc !== src) {
                            return [
                                inputId,
                                "Please select either dataset or dataset list fields for all batch mode fields.",
                            ];
                        }
                    }
                    if (batchN === -1) {
                        batchN = n;
                    } else if (batchN !== n) {
                        return [
                            inputId,
                            `Please make sure that you select the same number of inputs for all batch mode fields. This field contains <b>${n}</b> selection(s) while a previous field contains <b>${batchN}</b>.`,
                        ];
                    }
                }
            }
            return null;
        },
    },
    methods: {
        onReplaceParams() {
            let refreshOnChange = false;
            Object.entries(this.replaceParams).forEach(([key, value]) => {
                const input = this.formIndex[key];
                if (input) {
                    input.value = value;
                    refreshOnChange = refreshOnChange || input.refresh_on_change;
                }
            });
            this.onChange(refreshOnChange);
        },
        onCreateIndex() {
            this.formIndex = {};
            visitInputs(this.formInputs, (input, name) => {
                this.formIndex[name] = input;
            });
        },
        onChangeForm() {
            this.formInputs = JSON.parse(JSON.stringify(this.formInputs));
            this.onChange();
        },
        onCloneInputs() {
            this.formInputs = JSON.parse(JSON.stringify(this.inputs));
            this.onCreateIndex();
        },
        onChange(refreshOnChange) {
            this.onCreateIndex();
            const params = {};
            Object.entries(this.formIndex).forEach(([key, input]) => {
                params[key] = input.value;
            });
            if (JSON.stringify(params) != JSON.stringify(this.formData)) {
                this.formData = params;
                this.resetError();
                this.$emit("onChange", params, refreshOnChange);
            }
        },
        onHighlight(validation, silent = false) {
            if (validation && validation.length == 2) {
                const inputId = validation[0];
                const message = validation[1];
                this.setError(inputId, message);
                if (!silent) {
                    var element = document.querySelector(`#form-element-${inputId}`);
                    if (element) {
                        document.querySelector(".center-panel").scrollTo(0, element.offsetTop);
                    }
                }
            }
        },
        setError(inputId, message) {
            const input = this.formIndex[inputId];
            if (input) {
                input.error = message;
            }
        },
        resetError() {
            Object.values(this.formIndex).forEach((input) => {
                input.error = null;
            });
        },
    },
};
</script>
