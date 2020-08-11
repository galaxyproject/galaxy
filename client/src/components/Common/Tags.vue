<template>
    <StatelessTags :value="tags" @input="onInput" />
</template>
<script>
import StatelessTags from "components/Tags/StatelessTags";
export default {
    components: {
        StatelessTags,
    },
    props: {
        index: {
            type: Number,
        },
        tags: {
            type: Array,
        },
    },
    methods: {
        onInput(tags) {
            this.$emit("input", tags, this.index);
        },
    },
};
</script>
