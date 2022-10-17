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
        :on-change="onChange"
        :on-change-form="onChangeForm"
        :workflow-building-mode="workflowBuildingMode" />
</template>

<script>
import Vue from "vue";
import FormInputs from "./FormInputs";
import { visitInputs, validateInputs, matchErrors } from "./utilities";
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
        workflowBuildingMode: {
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
            return validateInputs(this.formIndex, this.formData);
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
                const errorMessages = matchErrors(this.formIndex, this.errors);
                for (const inputId in errorMessages) {
                    this.setError(inputId, errorMessages[inputId]);
                }
            }
        },
        replaceParams() {
            this.onReplaceParams();
        },
    },
    created() {
        this.onCloneInputs();
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
        getOffsetTop(element, padding = 100) {
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
                        const centerPanel = document.querySelector(".center-panel");
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
        resetError() {
            Object.values(this.formIndex).forEach((input) => {
                input.error = null;
            });
        },
    },
};
</script>
