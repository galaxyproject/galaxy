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
        onInput(tags) {
            this.item.tags = tags;
            this.$emit("input", this.item);
        }
    }
};
</script>
