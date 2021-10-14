<template>
    <div>
        {{ outputName }}
    </div>
</template>

<script>
import FormElement from "components/Form/FormElement";

export default {
    components: {
        FormElement,
    },
    props: {
        outputName: {
            type: String,
            required: true,
        },
        getNode: {
            type: Function,
            required: true,
        },
        datatypes: {
            type: Array,
            default: null,
        },
    },
    computed: {
        node() {
            return this.getNode();
        },
        postJobActions() {
            return this.node.postJobActions;
        },
    },
    methods: {
        onChange(values) {
            this.$emit("onChange", values);
        },
    },
};
</script>
