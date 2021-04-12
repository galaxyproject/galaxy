<template>
    <div v-if="node">
        ToolForm Content
        {{ node.id }}
        <Form :inputs=inputs />
    </div>
</template>

<script>
import Form from "components/Form/Form";

export default {
    components: {
        Form,
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
