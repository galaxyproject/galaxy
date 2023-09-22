<template>
    <div ref="target" />
</template>

<script>
import HistoryList from "./history-list";
export default {
    props: {
        actionId: {
            type: String,
            required: true,
        },
    },
    mounted() {
        new HistoryList.View({
            action_id: this.actionId,
        }).$el.appendTo(this.$refs.target);
    },
};
</script>
