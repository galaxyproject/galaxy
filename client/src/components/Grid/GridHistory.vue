<template>
    <div ref="target" />
</template>

<script>
import HistoryList from "mvc/history/history-list";
export default {
    props: {
        actionId: {
            type: String,
            default: null,
        },
    },
    mounted() {
        new HistoryList.View({
            action_id: this.actionId,
        }).$el.appendTo(this.$refs.target);
    },
};
</script>
