<template>
    <div v-if="node">
        ToolForm Content
        {{ node.id }}
    </div>
</template>

<script>
export default {
    props: {
        datatypes: {
            type: Array,
            required: true,
        },
        getManager: {
            type: Function,
            required: true,
        },
        node: {
            type: Object,
            required: false,
        },
    },
    data() {
        return {
        };
    },
    methods: {
    },
};
</script>
