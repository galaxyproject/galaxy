<template>
    <FormElement
        :id="id"
        :value="label"
        :error="error"
        :title="title"
        type="text"
        help="Provide a short, unique name to describe this output."
        @input="onInput" />
</template>

<script>
import FormElement from "components/Form/FormElement";

export default {
    components: {
        FormElement,
    },
    props: {
        name: {
            type: String,
            required: true,
        },
        showDetails: {
            type: Boolean,
            default: false,
        },
        activeOutputs: {
            type: Object,
            default: null,
        },
    },
    data() {
        return {
            error: null,
        };
    },
    computed: {
        id() {
            return `__label__${this.name}`;
        },
        title() {
            if (this.showDetails) {
                return `Label for: '${this.name}'`;
            } else {
                return "Label";
            }
        },
        label() {
            const activeOutput = this.activeOutputs.get(this.name);
            return activeOutput && activeOutput.label;
        },
    },
    methods: {
        onInput(newLabel) {
            if (this.activeOutputs.labelOutput(this.name, newLabel)) {
                this.error = null;
            } else {
                this.error = `Duplicate output label '${newLabel}' will be ignored.`;
            }
        },
    },
};
</script>
