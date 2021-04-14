<template>
    <div v-if="node">
        ToolForm Content
        {{ node.id }}
        <FormDefault />
    </div>
</template>

<script>
import FormDefault from "./FormDefault";

export default {
    components: {
        FormDefault,
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
        return {};
    },
    computed: {
        node() {
            return this.getNode();
        },
    },
    methods: {},
};
</script>
