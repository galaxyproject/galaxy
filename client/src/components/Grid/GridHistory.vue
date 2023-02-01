<template>
    <div ref="target" />
</template>

<script>
import HistoryList from "./history-list";
export default {
    mounted() {
        new HistoryList.View().$el.appendTo(this.$refs.target);
    },
};
</script>
