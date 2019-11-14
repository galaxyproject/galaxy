<template>
    <StatelessTags :value="item.tags" @input="onInput" />
</template>
<script>
import StatelessTags from "components/Tags/StatelessTags";
export default {
    components: {
        StatelessTags
    },
    props: {
        item: {
            type: Object,
            required: true
        }
    },
    methods: {
        onInput: function(tags) {
            this.item.tags = tags;
            this.$emit("input", item);
        }
    }
};
</script>
