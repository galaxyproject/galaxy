<template>
    <FormElement
        :id="id"
        :value="label"
        :error="error"
        :title="title"
        type="text"
        help="This will provide a short name to describe the output - this must be unique across workflows."
        @input="onInput"
    />
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
        label: {
            type: String,
            default: null,
        },
        error: {
            type: String,
            required: null,
        },
    },
    computed: {
        id() {
            return `__label__${this.name}`;
        },
        title() {
            if (this.showDetails) {
                return `Set Label for: ${this.name}`;
            } else {
                return "Label";
            }
        },
    },
    methods: {
        onInput(newLabel) {
            this.$emit("onLabel", this.id, this.name, newLabel);
        },
    },
};
</script>
