<template>
    <div>
        ToolForm Content
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
        getActiveNode: {
            type: Function,
            required: true,
        }
    },
    data() {
        return {
        };
    },
    methods: {
    },
};
</script>
