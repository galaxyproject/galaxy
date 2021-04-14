<template>
    <div v-if="node">
        ToolForm Content
        {{ node.id }}
        <FormElement id="_label" title="Label" />
        <Form :inputs=inputs />
    </div>
</template>

<script>
import Form from "components/Form/Form";
import FormElement from "components/Form/FormElement";

export default {
    components: {
        Form,
        FormElement,
    },
    props: {
        datatypes: {
            type: Array,
            required: true,
        },
        getManager: {
            type: Function,
            required: true,
        },
        getNode: {
            type: Function,
            required: true,
        },
    },
    data() {
        return {
        };
    },
    computed: {
        node() {
            return this.getNode();
        },
        inputs() {
            return this.getNode().config_form.inputs;
        },
    },
    methods: {
    },
};
</script>
