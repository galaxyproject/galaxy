<template>
    <StatelessTags :value="tags" @input="onInput" @tag-click="onTagClick" :disabled="disabled" />
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
        disabled: {
            type: Boolean,
            default: false,
        },
    },
    methods: {
        onInput(tags) {
            this.$emit("input", tags, this.index);
        },
        onTagClick(tag) {
            this.$emit("tag-click", tag);
        },
    },
};
</script>
