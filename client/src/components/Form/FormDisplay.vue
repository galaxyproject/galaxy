<template>
    <FormInputs
        :key="id"
        :inputs="formInputs"
        :loading="loading"
        :prefix="prefix"
        :sustain-repeats="sustainRepeats"
        :sustain-conditionals="sustainConditionals"
        :collapsed-enable-text="collapsedEnableText"
        :collapsed-enable-icon="collapsedEnableIcon"
        :collapsed-disable-text="collapsedDisableText"
        :collapsed-disable-icon="collapsedDisableIcon"
        :on-change="onChange"
        :on-change-form="onChangeForm"
        :workflow-building-mode="workflowBuildingMode" />
</template>

<script>
import Vue from "vue";

import FormInputs from "./FormInputs";
import { matchInputs, validateInputs, visitInputs } from "./utilities";

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
        loading: {
            type: Boolean,
            default: false,
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
            default: "far fa-caret-square-down",
        },
        collapsedDisableIcon: {
            type: String,
            default: "far fa-caret-square-up",
        },
        validationScrollTo: {
            type: Array,
            default: null,
        },
        replaceParams: {
            type: Object,
            default: null,
        },
        warnings: {
            type: Object,
            default: null,
        },
        workflowBuildingMode: {
            type: Boolean,
            default: false,
        },
        allowEmptyValueOnRequiredInput: {
            type: Boolean,
            default: false,
        },
    },
    data() {
        return {
            formData: {},
            formIndex: {},
            formInputs: [],
        };
    },
    computed: {
        validation() {
            return validateInputs(this.formIndex, this.formData, this.allowEmptyValueOnRequiredInput);
        },
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
                    Vue.set(input, "attributes", newValue);
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
            this.onErrors();
        },
        replaceParams() {
            this.onReplaceParams();
        },
        warnings() {
            this.onWarnings();
        },
    },
    created() {
        this.onCloneInputs();
        this.onChange();
        // highlight initial warnings
        this.onWarnings();
        // highlight initial errors
        this.onErrors();
    },
    methods: {
        buildFormData() {
            const params = {};
            Object.entries(this.formIndex).forEach(([key, input]) => {
                params[key] = input.value;
            });
            return params;
        },
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
            this.onChange(true);
        },
        onCloneInputs() {
            this.formInputs = JSON.parse(JSON.stringify(this.inputs));
            visitInputs(this.formInputs, (input) => {
                Vue.set(input, "error", null);
            });
            this.onCreateIndex();
        },
        onChange(refreshOnChange) {
            this.onCreateIndex();
            const params = this.buildFormData();
            if (JSON.stringify(params) != JSON.stringify(this.formData)) {
                this.formData = params;
                this.resetErrors();
                this.$emit("onChange", params, refreshOnChange);
            }
        },
        onErrors() {
            this.resetErrors();
            if (this.errors) {
                const errorMessages = matchInputs(this.formIndex, this.errors);
                for (const inputId in errorMessages) {
                    this.setError(inputId, errorMessages[inputId]);
                }
            }
        },
        onWarnings() {
            if (this.warnings) {
                const warningMessages = matchInputs(this.formIndex, this.warnings);
                for (const inputId in warningMessages) {
                    this.setWarning(inputId, warningMessages[inputId]);
                }
            }
        },
        getOffsetTop(element, padding = 200) {
            let offsetTop = 0;
            while (element) {
                offsetTop += element.offsetTop;
                element = element.offsetParent;
            }
            return offsetTop - padding;
        },
        onHighlight(validation, silent = false) {
            if (validation && validation.length == 2) {
                const inputId = validation[0];
                const message = validation[1];
                this.setError(inputId, message);
                if (!silent && inputId) {
                    const element = this.$el.querySelector(`[id='form-element-${inputId}']`);
                    if (element) {
                        const centerPanel = document.querySelector("#center");
                        if (centerPanel) {
                            centerPanel.scrollTo(0, this.getOffsetTop(element));
                        }
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
        setWarning(inputId, message) {
            const input = this.formIndex[inputId];
            if (input) {
                input.warning = message;
            }
        },
        resetErrors() {
            Object.values(this.formIndex).forEach((input) => {
                input.error = null;
            });
        },
    },
};
</script>
